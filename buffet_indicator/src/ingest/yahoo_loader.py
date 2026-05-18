"""Yahoo Finance loader for live (tail-update) data.

Used to extend the Wilshire 5000 master series past 2023-05-30 (when the
TradingView FRED:WILL5000PRFC mirror stopped publishing).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from src.config import RAW_CACHE
from src.ingest._base import (
    DataValidationError,
    NetworkError,
    atomic_write_json,
    atomic_write_parquet,
    file_lock,
    get_logger,
    sha256_bytes,
    utcnow,
)

logger = get_logger("buffett.ingest.yahoo")


WILSHIRE_FALLBACK_CHAIN = ("^W5000", "^FTW5000", "^W5000FLT")


@dataclass(frozen=True)
class YahooSeries:
    symbol: str
    canonical_name: str
    data: pd.DataFrame
    frequency: Literal["D", "W", "M"]
    retrieval_timestamp: datetime
    sha256: str
    cache_path: Path


# ---------------------------------------------------------------------------
# yfinance import is wrapped so tests can monkeypatch.
# ---------------------------------------------------------------------------


def _fetch_yf(symbol: str, *, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """Real yfinance fetch -- separated for easy monkeypatching in tests."""
    import yfinance as yf

    try:
        kwargs: dict[str, Any] = {
            "interval": "1d",
            "auto_adjust": False,
            "actions": False,
        }
        if start is not None or end is not None:
            kwargs["start"] = start
            kwargs["end"] = end
        else:
            kwargs["period"] = "max"
        df = yf.Ticker(symbol).history(**kwargs)
    except Exception as exc:  # noqa: BLE001 -- yfinance raises various concrete types
        msg = str(exc).lower()
        if "rate" in msg or "throttle" in msg:
            raise NetworkError(f"yfinance rate-limited: {exc}") from exc
        raise NetworkError(f"yfinance error for {symbol}: {exc}") from exc
    return df


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _safe_symbol(symbol: str) -> str:
    return symbol.replace("^", "CARET_")


def _cache_paths(symbol: str, cache_dir: Path) -> tuple[Path, Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = _safe_symbol(symbol)
    return cache_dir / f"{safe}.parquet", cache_dir / f"{safe}.meta.json"


def _is_cache_fresh(meta_path: Path, ttl_hours: int) -> bool:
    if not meta_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text())
        ts = datetime.fromisoformat(meta["retrieval_timestamp"])
    except (KeyError, ValueError, OSError):
        return False
    return utcnow() - ts < timedelta(hours=ttl_hours)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate(df: pd.DataFrame, symbol: str) -> None:
    if df.empty:
        raise DataValidationError(
            f"{symbol}: yfinance returned empty dataframe",
            user_message=f"Yahoo Finance returned no data for {symbol}.",
        )
    if "Close" not in df.columns:
        raise DataValidationError(
            f"{symbol}: missing Close column (got {list(df.columns)})"
        )
    close = df["Close"]
    if len(close) < 100:
        raise DataValidationError(f"{symbol}: only {len(close)} rows")
    if float(close.notna().mean()) < 0.95:
        raise DataValidationError(f"{symbol}: >5% NaN in Close column")
    if (close.dropna() <= 0).any():
        raise DataValidationError(f"{symbol}: non-positive close values")
    deltas = pd.Series(df.index).diff().dt.days.dropna()
    if not deltas.empty and float(deltas.max()) > 14:
        raise DataValidationError(
            f"{symbol}: gap of {int(deltas.max())} days > 14"
        )


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    df = df.copy()
    df.index = idx.normalize()
    df.index.name = "date"
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_yahoo_series(
    symbol: str,
    *,
    cache_dir: Path = RAW_CACHE,
    cache_ttl_hours: int = 24,
    force_refresh: bool = False,
    start: str | None = None,
    end: str | None = None,
) -> YahooSeries:
    """Fetch a single Yahoo Finance series, cache it, return a YahooSeries."""
    cache_path, meta_path = _cache_paths(symbol, cache_dir)
    with file_lock(cache_path):
        if not force_refresh and _is_cache_fresh(meta_path, cache_ttl_hours):
            logger.info("Yahoo cache HIT for %s", symbol)
            df = pd.read_parquet(cache_path)
            meta = json.loads(meta_path.read_text())
            return YahooSeries(
                symbol=symbol,
                canonical_name=symbol,
                data=df,
                frequency=meta.get("frequency", "D"),
                retrieval_timestamp=datetime.fromisoformat(meta["retrieval_timestamp"]),
                sha256=meta["sha256"],
                cache_path=cache_path,
            )

        logger.info("Yahoo cache MISS for %s -- fetching", symbol)
        df = _fetch_yf(symbol, start=start, end=end)
        df = _normalize_index(df)
        _validate(df, symbol)

        retrieval_ts = utcnow()
        sha = sha256_bytes(df.to_csv().encode("utf-8"))
        atomic_write_parquet(cache_path, df)
        atomic_write_json(
            meta_path,
            {
                "symbol": symbol,
                "frequency": "D",
                "retrieval_timestamp": retrieval_ts.isoformat(),
                "sha256": sha,
                "n_observations": int(len(df)),
                "source_tier": 4,
            },
        )
        return YahooSeries(
            symbol=symbol,
            canonical_name=symbol,
            data=df,
            frequency="D",
            retrieval_timestamp=retrieval_ts,
            sha256=sha,
            cache_path=cache_path,
        )


def load_wilshire_yahoo(
    *,
    chain: tuple[str, ...] = WILSHIRE_FALLBACK_CHAIN,
    min_observations: int = 250,
    cache_dir: Path = RAW_CACHE,
    cache_ttl_hours: int = 24,
    force_refresh: bool = False,
    start: str | None = None,
    end: str | None = None,
) -> YahooSeries:
    """Try each Wilshire ticker; return the one with the LONGEST valid history."""
    candidates: list[YahooSeries] = []
    errors: list[str] = []

    for sym in chain:
        try:
            s = load_yahoo_series(
                sym,
                cache_dir=cache_dir,
                cache_ttl_hours=cache_ttl_hours,
                force_refresh=force_refresh,
                start=start,
                end=end,
            )
            if len(s.data) >= min_observations:
                candidates.append(s)
            else:
                errors.append(f"{sym}: only {len(s.data)} obs (<{min_observations})")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{sym}: {type(exc).__name__}: {exc}")
            continue

    if not candidates:
        raise NetworkError(
            "All Wilshire fallback symbols failed: " + "; ".join(errors),
            user_message=(
                "Could not retrieve any Wilshire 5000 ticker from Yahoo. "
                "Last errors: " + "; ".join(errors[:3])
            ),
        )

    best = max(candidates, key=lambda s: len(s.data))
    logger.info(
        "Wilshire chain: selected %s with %d obs (candidates: %s)",
        best.symbol,
        len(best.data),
        {c.symbol: len(c.data) for c in candidates},
    )
    return best


__all__ = [
    "YahooSeries",
    "WILSHIRE_FALLBACK_CHAIN",
    "load_yahoo_series",
    "load_wilshire_yahoo",
]
