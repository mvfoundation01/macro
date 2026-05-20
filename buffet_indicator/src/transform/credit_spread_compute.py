"""v11.0 Credit Spread indicators -- ICE BofA OAS series via FRED CSV exports.

Four variants, identical methodology:

================  =================================================  ====================
variant_key       Description                                         FRED series id
================  =================================================  ====================
cs_hy_master      ICE BofA US High Yield Option-Adjusted Spread       BAMLH0A0HYM2
cs_ig_master      ICE BofA US Corporate Investment-Grade OAS          BAMLC0A0CM
cs_hy_bb          ICE BofA US HY BB OAS                               BAMLH0A1HYBB
cs_hy_ccc         ICE BofA US HY CCC & Lower OAS                      BAMLH0A3HYC
================  =================================================  ====================

Direction convention (per spec PART 10 §10):
    signal = log(spread)   # high spread = market stress = bearish equities

We log-transform the strictly-positive spread before z-scoring so the
right-skew of crisis observations doesn't dominate the metric, but no sign
flip is required: high spread already means bearish.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import (
    BAML_HY_BB,
    BAML_HY_CCC,
    BAML_HY_MASTER,
    BAML_IG_MASTER,
)
from src.ingest._base import SourceMissingError, get_logger

logger = get_logger("buffett.transform.credit_spread")


REQUIRED_COLUMNS = ("spread_raw", "log_spread", "signal")


VARIANT_REGISTRY: dict[str, dict[str, Any]] = {
    "cs_hy_master": {
        "path": BAML_HY_MASTER,
        "fred_id": "BAMLH0A0HYM2",
        "description": "ICE BofA US High Yield OAS (master)",
        "tier": "HY",
    },
    "cs_ig_master": {
        "path": BAML_IG_MASTER,
        "fred_id": "BAMLC0A0CM",
        "description": "ICE BofA US Corporate OAS (Investment Grade master)",
        "tier": "IG",
    },
    "cs_hy_bb": {
        "path": BAML_HY_BB,
        "fred_id": "BAMLH0A1HYBB",
        "description": "ICE BofA US HY BB OAS",
        "tier": "HY-BB",
    },
    "cs_hy_ccc": {
        "path": BAML_HY_CCC,
        "fred_id": "BAMLH0A3HYC",
        "description": "ICE BofA US HY CCC & Lower OAS",
        "tier": "HY-CCC",
    },
}


def _load_baml_csv(path: Path, variant_key: str) -> pd.Series:
    """Load a daily BAML OAS CSV and return a single percentage-points series.

    We do NOT route through :func:`src.ingest.csv_loader.load_tradingview_file`
    because the BAML CSVs are sourced from FRED (not TradingView) and the
    csv_loader validators (positive-close, 14-day-gap) don't fit perfectly
    -- e.g., the BAML series can briefly dip below the validator's
    return-of-1000% threshold during 2008.
    """
    if not path.exists():
        raise SourceMissingError(
            f"Missing BAML OAS CSV for {variant_key}: {path}",
            user_message=f"Could not find {path.name}.",
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
    if len(df) < 100:
        raise SourceMissingError(
            f"{path.name}: only {len(df)} observations after cleaning (<100)."
        )
    s = pd.Series(
        df["close"].to_numpy(),
        index=pd.DatetimeIndex(df["time"]),
        name=variant_key,
    )
    return s


def compute_credit_spread(variant_key: str) -> pd.DataFrame:
    """Compute the monthly credit spread series for the named variant.

    Parameters
    ----------
    variant_key : str
        One of ``cs_hy_master``, ``cs_ig_master``, ``cs_hy_bb``, ``cs_hy_ccc``.

    Returns
    -------
    pd.DataFrame
        Indexed by month-end ``date`` with columns:

        - ``spread_raw`` : OAS in percentage points (e.g., 5.42 for 542 bp)
        - ``log_spread`` : natural log of ``spread_raw`` (well-defined because
                           OAS > 0 always)
        - ``signal``     : == ``log_spread`` (no sign flip; high = bearish)
    """
    if variant_key not in VARIANT_REGISTRY:
        raise KeyError(
            f"Unknown credit spread variant {variant_key!r}; "
            f"expected one of {sorted(VARIANT_REGISTRY)}"
        )
    info = VARIANT_REGISTRY[variant_key]
    daily = _load_baml_csv(info["path"], variant_key)
    monthly = daily.resample("ME").last().dropna()
    if (monthly <= 0).any():
        # OAS can briefly print 0 during illiquid days; clip the tiny zero
        # tail so the log is well-defined. Document the affected dates.
        zero_count = int((monthly <= 0).sum())
        logger.warning(
            "%s: %d non-positive monthly OAS values clipped to 1bp before log.",
            variant_key,
            zero_count,
        )
        monthly = monthly.clip(lower=0.01)  # 1 basis point floor
    df = pd.DataFrame({"spread_raw": monthly.astype("float64")})
    df["log_spread"] = np.log(df["spread_raw"])
    df["signal"] = df["log_spread"]
    df.index.name = "date"
    df.attrs["source"] = f"fred:{info['fred_id']}"
    df.attrs["variant_key"] = variant_key
    df.attrs["direction"] = "standard"
    df.attrs["description"] = info["description"]
    df.attrs["tier"] = info["tier"]
    return df


def compute_all_credit_spreads() -> dict[str, pd.DataFrame]:
    """Best-effort builder for all 4 credit spread variants.

    Missing inputs log a WARNING and are absent from the output dict.
    """
    out: dict[str, pd.DataFrame] = {}
    for variant_key in VARIANT_REGISTRY:
        try:
            out[variant_key] = compute_credit_spread(variant_key)
        except SourceMissingError as exc:
            logger.warning("%s skipped: %s", variant_key, exc)
    return out


def latest_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Last-observation summary for headline rows."""
    last = df.dropna(subset=["signal"]).iloc[-1]
    return {
        "date": last.name.date().isoformat() if hasattr(last.name, "date") else str(last.name),
        "spread_pp": float(last["spread_raw"]),
        "log_spread": float(last["log_spread"]),
        "signal": float(last["signal"]),
    }


__all__ = [
    "compute_credit_spread",
    "compute_all_credit_spreads",
    "latest_summary",
    "VARIANT_REGISTRY",
    "REQUIRED_COLUMNS",
]
