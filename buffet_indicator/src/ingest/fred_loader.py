"""FRED API loader for Buffett Indicator inputs."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import requests

from src.config import RAW_CACHE
from src.ingest._base import (
    APIKeyError,
    DataValidationError,
    IngestError,
    NetworkError,
    SourceMissingError,
    atomic_write_json,
    atomic_write_parquet,
    file_lock,
    get_logger,
    register_secret,
    retryable,
    sha256_bytes,
    utcnow,
)

logger = get_logger("buffett.ingest.fred")

FRED_BASE = "https://api.stlouisfed.org/fred/series"
FRED_OBS_URL = f"{FRED_BASE}/observations"
FRED_META_URL = f"{FRED_BASE}"

_API_KEY_RE = re.compile(r"^[a-z0-9]{32}$")

# Public catalog -----------------------------------------------------------------

FRED_CATALOG: dict[str, dict[str, str]] = {
    "gdp": {
        "series_id": "GDP",
        "frequency": "Q",
        "units": "Billions USD SAAR",
        "role": "Denominator for all BI variants",
    },
    "equities_all": {
        "series_id": "BOGZ1LM883164105Q",
        "frequency": "Q",
        "units": "Millions USD NSA",
        "role": "BI-AllEquity numerator (public + private)",
    },
    "equities_public": {
        "series_id": "BOGZ1LM883164115Q",
        "frequency": "Q",
        "units": "Millions USD NSA",
        "role": "Public-only counterpart",
    },
    "equities_nonfin": {
        "series_id": "NCBEILQ027S",
        "frequency": "Q",
        "units": "Millions USD NSA",
        "role": "Nonfinancial robustness",
    },
}

# Spec v7: optional FRED series for Q-Ratio and EY-Deficit. Loaded best-effort
# (skipped on 404 / network failure with a WARNING) so the core pipeline keeps
# working when a series is decommissioned or temporarily unavailable.
FRED_OPTIONAL_CATALOG: dict[str, dict[str, str]] = {
    "nonfin_net_worth": {
        "series_id": "TNWMVBSNNCB",
        "frequency": "Q",
        "units": "Billions USD NSA",
        "role": "Q-Ratio denominator (replacement cost net worth)",
    },
    "tips_10y": {
        "series_id": "DFII10",
        "frequency": "D",
        "units": "Percent",
        "role": "Real 10Y yield (TIPS), 2003+",
    },
}

BuffettFredKey = Literal["gdp", "equities_all", "equities_public", "equities_nonfin"]


# ---------------------------------------------------------------------------
# Dataclass result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FredSeries:
    series_id: str
    data: pd.Series
    frequency: Literal["D", "M", "Q", "A"]
    units: str
    last_updated_at_fred: datetime
    retrieval_timestamp: datetime
    sha256: str
    cache_path: Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_api_key(api_key: str) -> None:
    if not api_key or not _API_KEY_RE.match(api_key):
        raise APIKeyError(
            "FRED api_key must be 32 lowercase alphanumeric characters",
            user_message=(
                "Your FRED API key looks malformed. Request or copy one from "
                "https://fredaccount.stlouisfed.org/apikeys (32 lowercase hex chars)."
            ),
        )
    register_secret(api_key)


def _cache_paths(series_id: str, cache_dir: Path) -> tuple[Path, Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{series_id}.parquet", cache_dir / f"{series_id}.meta.json"


def _is_cache_fresh(meta_path: Path, ttl_hours: int) -> bool:
    if not meta_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text())
        ts = datetime.fromisoformat(meta["retrieval_timestamp"])
    except (KeyError, ValueError, OSError):
        return False
    return utcnow() - ts < timedelta(hours=ttl_hours)


@retryable(max_attempts=5)
def _http_get_json(url: str, params: dict[str, str], *, timeout: int = 30) -> dict[str, Any]:
    """Wrap requests.get with retry-on-network and explicit handling for known status codes."""
    try:
        resp = requests.get(url, params=params, timeout=timeout)
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise NetworkError(
            f"FRED network error: {exc}",
            user_message="Could not reach FRED; check your connection and try again.",
        ) from exc

    status = resp.status_code
    if status == 200:
        try:
            return resp.json()
        except ValueError as exc:
            raise NetworkError(f"FRED returned non-JSON 200: {exc}") from exc
    if status in (400, 403):
        raise APIKeyError(
            f"FRED rejected request ({status})",
            user_message=(
                "FRED rejected the API key. Verify it at "
                "https://fredaccount.stlouisfed.org/apikeys."
            ),
        )
    if status == 404:
        raise DataValidationError(
            "FRED returned 404 (unknown series)",
            user_message="That FRED series id does not exist.",
        )
    if status in (429,) or 500 <= status < 600:
        # Trigger retry by raising NetworkError (covered by retry_if_exception_type).
        raise NetworkError(
            f"FRED transient error {status}",
            user_message="FRED is throttling or temporarily unavailable; retrying.",
        )
    raise NetworkError(
        f"FRED returned unexpected status {status}",
        user_message=f"Unexpected FRED status {status}.",
    )


def _parse_observations(obs: list[dict[str, str]]) -> pd.Series:
    if not obs:
        return pd.Series(dtype="float64")
    rows = []
    for o in obs:
        dt = pd.to_datetime(o["date"])
        v = o.get("value", ".")
        if v in (".", "", None):
            val = float("nan")
        else:
            try:
                val = float(v)
            except ValueError:
                val = float("nan")
        rows.append((dt, val))
    idx = pd.DatetimeIndex([r[0] for r in rows])
    s = pd.Series([r[1] for r in rows], index=idx, dtype="float64")
    s = s.sort_index()
    return s


def _normalize_eop(series: pd.Series, frequency: str) -> pd.Series:
    """Reindex to end-of-period for monthly/quarterly/annual series."""
    if frequency not in ("M", "Q", "A"):
        return series
    period_alias = {"M": "M", "Q": "Q", "A": "Y"}[frequency]
    new_index = (
        series.index.to_period(period_alias).to_timestamp(how="end").normalize()
    )
    # Strip the inherited freq attribute so live and parquet-read series compare equal.
    new_index = pd.DatetimeIndex(new_index.values)
    out = pd.Series(series.values, index=new_index, name=series.name)
    return out


def _validate_series(s: pd.Series, frequency: str) -> None:
    if not s.index.is_monotonic_increasing:
        raise DataValidationError("FRED series index not monotonic")
    if s.index.has_duplicates:
        raise DataValidationError("FRED series has duplicate dates")
    if len(s) < 10:
        raise DataValidationError(
            f"FRED series too short: {len(s)} obs (<10)",
            user_message="FRED returned suspiciously few observations.",
        )
    # Gap check (quarterly => ~92 days; allow some slack)
    max_gap_days = {"D": 7, "M": 35, "Q": 100, "A": 380}.get(frequency, 100)
    deltas = s.index.to_series().diff().dt.days.dropna()
    if (deltas > max_gap_days).any():
        bad = deltas[deltas > max_gap_days]
        raise DataValidationError(
            f"FRED series has gaps > {max_gap_days} days (e.g., {bad.iloc[0]} days)",
        )
    # Missingness -- count only INTERNAL NaN (between first and last valid obs).
    # Leading NaN means the series hadn't started yet; trailing NaN means the
    # latest period hasn't been published. Neither is a data-quality issue.
    # Threshold is 10% (not 5%) because the FRB Z.1 flow-of-funds series
    # report Q4-only for ~5 years before going full quarterly, which adds ~5%
    # of structural NaN over the full 1945-2025 window. 10% still catches
    # genuine data-quality issues without rejecting legitimate FRED series.
    first_valid = s.first_valid_index()
    last_valid = s.last_valid_index()
    if first_valid is None or last_valid is None:
        raise DataValidationError("FRED series is all NaN")
    interior = s.loc[first_valid:last_valid]
    missing = float(interior.isna().mean())
    if missing > 0.10:
        raise DataValidationError(
            f"FRED series has {missing:.1%} interior missing observations (>10%)",
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_fred_series(
    series_id: str,
    api_key: str,
    *,
    cache_dir: Path = RAW_CACHE,
    cache_ttl_hours: int = 24,
    observation_start: str = "1945-01-01",
    force_refresh: bool = False,
) -> FredSeries:
    """Fetch (or read from cache) one FRED series."""
    _validate_api_key(api_key)

    cache_path, meta_path = _cache_paths(series_id, cache_dir)

    with file_lock(cache_path):
        if not force_refresh and _is_cache_fresh(meta_path, cache_ttl_hours):
            logger.info("FRED cache HIT for %s", series_id)
            meta = json.loads(meta_path.read_text())
            data = pd.read_parquet(cache_path)["value"]
            data.index = pd.DatetimeIndex(data.index)
            data.name = series_id
            return FredSeries(
                series_id=series_id,
                data=data,
                frequency=meta["frequency"],
                units=meta["units"],
                last_updated_at_fred=datetime.fromisoformat(meta["last_updated_at_fred"]),
                retrieval_timestamp=datetime.fromisoformat(meta["retrieval_timestamp"]),
                sha256=meta["sha256"],
                cache_path=cache_path,
            )

        logger.info("FRED cache MISS for %s -- fetching", series_id)

        # Metadata first (lightweight, gives us last_updated)
        meta_payload = _http_get_json(
            FRED_META_URL,
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
            },
        )
        try:
            series_meta = meta_payload["seriess"][0]
        except (KeyError, IndexError) as exc:
            raise DataValidationError(
                f"FRED meta missing for {series_id}: {meta_payload}",
            ) from exc

        last_updated_str = series_meta.get("last_updated", "").split(" ")[0] or "1970-01-01"
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
        except ValueError:
            last_updated = datetime(1970, 1, 1)
        fred_frequency = series_meta.get("frequency_short", "")
        units = series_meta.get("units_short") or series_meta.get("units") or ""

        # Observations
        obs_payload = _http_get_json(
            FRED_OBS_URL,
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "observation_start": observation_start,
            },
        )
        observations = obs_payload.get("observations", [])
        raw_series = _parse_observations(observations)

        # Decide canonical frequency for normalization. Prefer FRED's report.
        freq_map = {"D": "D", "W": "D", "M": "M", "Q": "Q", "A": "A", "SA": "M"}
        frequency: Literal["D", "M", "Q", "A"] = freq_map.get(fred_frequency, "Q")  # type: ignore[assignment]

        if frequency in ("M", "Q", "A"):
            raw_series = _normalize_eop(raw_series, frequency)
        else:
            raw_series.index = raw_series.index.normalize()

        raw_series.name = series_id

        _validate_series(raw_series, frequency)

        retrieval_ts = utcnow()
        payload_bytes = json.dumps(observations, sort_keys=True).encode("utf-8")
        sha = sha256_bytes(payload_bytes)

        df = pd.DataFrame({"value": raw_series.values}, index=raw_series.index)
        df.index.name = "date"
        atomic_write_parquet(cache_path, df)
        atomic_write_json(
            meta_path,
            {
                "series_id": series_id,
                "frequency": frequency,
                "units": units,
                "last_updated_at_fred": last_updated.isoformat(),
                "retrieval_timestamp": retrieval_ts.isoformat(),
                "sha256": sha,
                "n_observations": int(len(raw_series)),
                "source_tier": 2,
            },
        )

        return FredSeries(
            series_id=series_id,
            data=raw_series,
            frequency=frequency,
            units=units,
            last_updated_at_fred=last_updated,
            retrieval_timestamp=retrieval_ts,
            sha256=sha,
            cache_path=cache_path,
        )


def load_buffett_fred(
    api_key: str,
    *,
    cache_dir: Path = RAW_CACHE,
    cache_ttl_hours: int = 24,
    force_refresh: bool = False,
    observation_start: str = "1945-01-01",
    skip_freshness_check: bool = False,
) -> dict[str, FredSeries]:
    """Load all FRED series needed for the Buffett Indicator pipeline."""
    out: dict[str, FredSeries] = {}
    for key, info in FRED_CATALOG.items():
        out[key] = load_fred_series(
            info["series_id"],
            api_key,
            cache_dir=cache_dir,
            cache_ttl_hours=cache_ttl_hours,
            observation_start=observation_start,
            force_refresh=force_refresh,
        )

    # Cross-series sanity checks
    tol = 1.05  # 5% slack for noisy quarterly data
    last_all = out["equities_all"].data.dropna().iloc[-1]
    last_pub = out["equities_public"].data.dropna().iloc[-1]
    last_nonfin = out["equities_nonfin"].data.dropna().iloc[-1]
    if not (last_pub <= last_all * tol):
        raise DataValidationError(
            f"equities_public ({last_pub:.0f}) > equities_all ({last_all:.0f}) "
            "beyond tolerance"
        )
    if not (last_nonfin <= last_all * tol):
        raise DataValidationError(
            f"equities_nonfin ({last_nonfin:.0f}) > equities_all ({last_all:.0f}) "
            "beyond tolerance"
        )

    if not skip_freshness_check:
        cutoff = utcnow() - timedelta(days=370)
        for key, s in out.items():
            if s.data.index.max() < cutoff:
                logger.warning(
                    "FRED series %s last obs %s is older than 12 months",
                    key,
                    s.data.index.max().date(),
                )

    logger.warning(
        "Latest-vintage data; descriptive use only. Predictive backtests require "
        "ALFRED real-time vintages (future module)."
    )
    return out


def load_fred_optional(
    api_key: str,
    *,
    cache_dir: Path = RAW_CACHE,
    cache_ttl_hours: int = 24,
    force_refresh: bool = False,
    observation_start: str = "1945-01-01",
    keys: tuple[str, ...] | None = None,
) -> dict[str, FredSeries]:
    """Best-effort loader for optional Spec v7 FRED series.

    Each key is independently retried; failures are logged as WARNING and the
    series is omitted from the output dict.
    """
    _validate_api_key(api_key)
    out: dict[str, FredSeries] = {}
    selected = keys if keys is not None else tuple(FRED_OPTIONAL_CATALOG.keys())
    for key in selected:
        info = FRED_OPTIONAL_CATALOG.get(key)
        if info is None:
            logger.warning("Unknown optional FRED key: %s", key)
            continue
        # TIPS daily series needs a different observation_start (no pre-2003 data).
        start = "2003-01-01" if info.get("frequency") == "D" else observation_start
        try:
            out[key] = load_fred_series(
                info["series_id"],
                api_key,
                cache_dir=cache_dir,
                cache_ttl_hours=cache_ttl_hours,
                observation_start=start,
                force_refresh=force_refresh,
            )
        except IngestError as exc:
            logger.warning(
                "Optional FRED series '%s' (%s) skipped: %s",
                key,
                info["series_id"],
                exc,
            )
    return out


# Re-export so tests can patch easily.
__all__ = [
    "FredSeries",
    "FRED_OPTIONAL_CATALOG",
    "load_fred_optional",
    "load_fred_series",
    "load_buffett_fred",
    "FRED_CATALOG",
    "BuffettFredKey",
    "SourceMissingError",
    "IngestError",
]
