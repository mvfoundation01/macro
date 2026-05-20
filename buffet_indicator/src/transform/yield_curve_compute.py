"""v11.0 Yield Curve indicators -- 10Y-3M and 10Y-2Y spreads.

Direction convention (per spec PART 10 §10):
    signal = -(spread)   # high signal = bearish equities (curve inversion)

The negation is done HERE so all downstream pipelines (z-score, predictive
regression, Bayesian outlook, conviction) can use the canonical
"HIGH = OVERVALUED / BEARISH" convention without per-indicator sign handling.

Data sources
------------
- 10Y-3M : ``TVC_US10Y`` daily yield - ``TVC_US03MY`` (3-month) daily yield.
- 10Y-2Y : FRED ``T10Y2Y`` daily series (already the spread). Loaded via the
           existing :func:`src.ingest.fred_loader.load_fred_series` helper
           when an API key is available; otherwise this function raises
           :class:`SourceMissingError` so the orchestrator can record the
           absence and continue. (No 2Y TradingView CSV exists in the raw
           data directory at the time of writing.)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import TV_US03M, TV_US10Y
from src.ingest._base import SourceMissingError, get_logger

logger = get_logger("buffett.transform.yield_curve")


REQUIRED_COLUMNS = ("us10y_yield", "short_yield", "spread_raw", "signal")


YIELD_MIN_PCT = -1.5
YIELD_MAX_PCT = 25.0


class YieldValidationError(ValueError):
    """Raised when a yield series violates a yield-aware validator."""


def _validate_yield_series(s: pd.Series, label: str) -> None:
    """v11.0b yield-aware validator suite (replaces the v11.0a bypass).

    Each validator is intentionally small and named so a failing test points
    at the specific contract that broke.

    Rules:

    - **monotonic**: index must be strictly increasing
    - **no duplicates**: a duplicated date is a data error (ingest layer
      should dedupe upstream)
    - **min_rows**: at least 100 observations after cleaning
    - **nan_fraction**: no more than 5% missing values across the cleaned
      window
    - **range**: closing yields must lie in [-1.5%, 25.0%]. The lower bound
      accommodates briefly-negative short-dated T-bills (2015 stress); the
      upper bound covers the 1981 yield-curve peak (~16% on 10Y, ~20% on
      short-dated). Anything outside this is almost certainly a unit error
      (e.g., decimal vs percent) or a corrupted row.
    """
    if not s.index.is_monotonic_increasing:
        raise YieldValidationError(
            f"{label}: index not monotonic increasing"
        )
    if s.index.duplicated().any():
        n_dup = int(s.index.duplicated().sum())
        raise YieldValidationError(
            f"{label}: {n_dup} duplicate dates in series"
        )
    if len(s) < 100:
        raise YieldValidationError(
            f"{label}: only {len(s)} rows after cleaning (<100)"
        )
    nan_frac = float(s.isna().mean())
    if nan_frac > 0.05:
        raise YieldValidationError(
            f"{label}: NaN fraction {nan_frac:.2%} exceeds 5% ceiling"
        )
    clean = s.dropna()
    bad_mask = (clean < YIELD_MIN_PCT) | (clean > YIELD_MAX_PCT)
    if bad_mask.any():
        n_bad = int(bad_mask.sum())
        sample = clean[bad_mask].head(3).to_dict()
        raise YieldValidationError(
            f"{label}: {n_bad} values outside "
            f"[{YIELD_MIN_PCT}, {YIELD_MAX_PCT}]% range; first: {sample}"
        )


def _load_daily_yield(path: Path, label: str) -> pd.Series:
    """Load a TradingView daily yield CSV with yield-aware validation.

    The v11.0a bypass of :func:`src.ingest.csv_loader.load_tradingview_file`
    was driven by two real constraints (T-bill yields can dip to 0 during
    ZIRP eras; TV yield CSVs blend sparse quarterly early-history into a
    later daily series with > 14-day gaps). v11.0b replaces the bypass
    with the explicit :func:`_validate_yield_series` checks below.
    """
    if not path.exists():
        raise SourceMissingError(
            f"Missing raw yield file for {label}: {path}",
            user_message=f"Could not find {label} CSV at {path.name}.",
        )
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    if not {"time", "close"}.issubset(df.columns):
        raise SourceMissingError(
            f"{path.name}: required columns 'time' and 'close' missing; "
            f"got {list(df.columns)}"
        )
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert(None).dt.normalize()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = (
        df.dropna(subset=["time", "close"])
        .drop_duplicates(subset="time", keep="last")
        .sort_values("time")
    )
    s = pd.Series(
        df["close"].to_numpy(), index=pd.DatetimeIndex(df["time"]), name=label
    )
    _validate_yield_series(s, label)
    return s


def _resample_month_end(s: pd.Series) -> pd.Series:
    """Take last observation of each month."""
    return s.resample("ME").last().dropna()


def _build_yc_dataframe(
    long_yield_monthly: pd.Series,
    short_yield_monthly: pd.Series,
) -> pd.DataFrame:
    """Align two monthly yield series and compute spread + (negated) signal."""
    df = pd.DataFrame(
        {
            "us10y_yield": long_yield_monthly,
            "short_yield": short_yield_monthly,
        }
    ).dropna()
    df["spread_raw"] = df["us10y_yield"] - df["short_yield"]
    # Inverted: higher signal = curve inversion = bearish for equities.
    df["signal"] = -df["spread_raw"]
    df.index.name = "date"
    return df


def compute_yield_curve_10y3m(
    *,
    long_path: Path = TV_US10Y,
    short_path: Path = TV_US03M,
) -> pd.DataFrame:
    """Compute the 10Y-3M Treasury yield curve spread.

    Returns
    -------
    pd.DataFrame
        Indexed by month-end ``date`` with columns:

        - ``us10y_yield`` : 10-year yield in percentage points
        - ``short_yield`` : 3-month yield in percentage points
        - ``spread_raw``  : ``us10y_yield - short_yield`` (pp); negative = inverted
        - ``signal``      : ``-spread_raw`` (high signal = bearish equities)
    """
    s10y = _load_daily_yield(long_path, "us10y_yield")
    s3m = _load_daily_yield(short_path, "us3m_yield")
    s10y_m = _resample_month_end(s10y)
    s3m_m = _resample_month_end(s3m)
    df = _build_yc_dataframe(s10y_m, s3m_m)
    df.attrs["source"] = "tradingview:US10Y-US3M"
    df.attrs["variant_key"] = "yc_10y3m"
    df.attrs["direction"] = "inverted"
    return df


def compute_yield_curve_10y2y(
    *,
    api_key: str | None = None,
    series_id: str = "T10Y2Y",
) -> pd.DataFrame:
    """Compute the 10Y-2Y Treasury yield curve spread (FRED T10Y2Y).

    The series is published directly as a spread, so ``spread_raw`` equals the
    raw FRED value and ``us10y_yield`` / ``short_yield`` are filled with NaN
    (we never receive them as standalone columns from this endpoint).

    Parameters
    ----------
    api_key : str | None
        FRED API key. If ``None``, raises :class:`SourceMissingError`.
    """
    if not api_key:
        raise SourceMissingError(
            "compute_yield_curve_10y2y requires a FRED api_key (T10Y2Y endpoint).",
            user_message=(
                "Pass --config with a config.yaml containing fred_api_key, or "
                "set FRED_API_KEY in the environment."
            ),
        )
    from src.ingest.fred_loader import load_fred_series

    fs = load_fred_series(series_id, api_key)
    s = fs.data.astype("float64").dropna()
    s.name = "spread_raw"
    # Resample daily to month-end.
    if isinstance(s.index, pd.DatetimeIndex):
        s_m = s.resample("ME").last().dropna()
    else:
        s_m = s
    df = pd.DataFrame(
        {
            "us10y_yield": pd.Series(np.nan, index=s_m.index),
            "short_yield": pd.Series(np.nan, index=s_m.index),
            "spread_raw": s_m,
        }
    )
    df["signal"] = -df["spread_raw"]
    df.index.name = "date"
    df.attrs["source"] = f"fred:{series_id}"
    df.attrs["variant_key"] = "yc_10y2y"
    df.attrs["direction"] = "inverted"
    return df


def compute_all_yield_curves(
    *,
    api_key: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Best-effort builder for both yield curve variants.

    Returns a dict keyed by variant. Missing inputs (e.g., no FRED key) cause
    a WARNING but never raise; the corresponding key is simply absent.
    """
    out: dict[str, pd.DataFrame] = {}
    try:
        out["yc_10y3m"] = compute_yield_curve_10y3m()
    except SourceMissingError as exc:
        logger.warning("yc_10y3m skipped: %s", exc)
    if api_key:
        try:
            out["yc_10y2y"] = compute_yield_curve_10y2y(api_key=api_key)
        except SourceMissingError as exc:
            logger.warning("yc_10y2y skipped: %s", exc)
    else:
        logger.warning("yc_10y2y skipped: no FRED api_key supplied")
    return out


def latest_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Convenience: last-observation summary for downstream HEADLINE rows."""
    last = df.dropna(subset=["signal"]).iloc[-1]
    return {
        "date": last.name.date().isoformat() if hasattr(last.name, "date") else str(last.name),
        "spread_raw_pp": float(last["spread_raw"]),
        "signal": float(last["signal"]),
        "is_inverted": bool(last["spread_raw"] < 0),
    }


__all__ = [
    "compute_yield_curve_10y3m",
    "compute_yield_curve_10y2y",
    "compute_all_yield_curves",
    "latest_summary",
    "REQUIRED_COLUMNS",
]
