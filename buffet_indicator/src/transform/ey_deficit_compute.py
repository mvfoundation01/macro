"""Equity Yield Deficit = Real 10Y Yield - CAPE Earnings Yield.

Spec v7 introduces this as the 6th input variant. Sign convention:
    EYD > 0 -> bonds offer more yield than equities -> OVERvalued (HIGH = OV)
    EYD < 0 -> equities offer more yield than bonds -> UNDERvalued

This is the *negation* of CMV's "Earnings Yield Gap" so the HIGH-is-OV regime
classification works uniformly across all MV variants.

Real 10Y yield is spliced:
    pre-2003 : nominal GS10 - 12-month trailing CPI inflation (Shiller)
    2003+    : DFII10 (TIPS, FRED) when available

References
----------
Yardeni (1999) "Fed Model" (original positive-sign formulation).
Shiller (2018) "Excess CAPE Yield" (alternate variation in his recent papers).
"""
from __future__ import annotations

import pandas as pd

from src.ingest._base import IngestError, get_logger
from src.ingest.shiller_loader import ShillerData

logger = get_logger("buffett.transform.ey_deficit")


class EYDeficitInputMissingError(IngestError):
    """Required inputs for EY-Deficit (CAPE, GS10, CPI) are unavailable."""


def compute_real_10y_yield(
    nominal_gs10: pd.Series,
    cpi: pd.Series,
    tips_10y: pd.Series | None = None,
    *,
    splice_date: pd.Timestamp = pd.Timestamp("2003-01-31"),
) -> pd.Series:
    """Spliced real 10Y yield in PERCENT units (e.g., 1.5 for 1.5%)."""
    nominal_monthly = nominal_gs10.dropna().astype("float64")
    cpi_monthly = cpi.dropna().astype("float64")

    # Make sure both are at month-end.
    nominal_monthly = nominal_monthly.copy()
    nominal_monthly.index = (
        pd.DatetimeIndex(nominal_monthly.index)
        .to_period("M")
        .to_timestamp(how="end")
        .normalize()
    )
    cpi_monthly = cpi_monthly.copy()
    cpi_monthly.index = (
        pd.DatetimeIndex(cpi_monthly.index)
        .to_period("M")
        .to_timestamp(how="end")
        .normalize()
    )

    # nominal_gs10 from Shiller is already decimal (e.g. 0.043) when long_rate_gs10
    # is auto-detected; convert to percent units for arithmetic with CPI inflation.
    if nominal_monthly.dropna().abs().max() < 1.0:
        nominal_monthly = nominal_monthly * 100.0

    cpi_yoy = (cpi_monthly / cpi_monthly.shift(12) - 1.0) * 100.0
    common = nominal_monthly.index.intersection(cpi_yoy.index)
    real_pre = (nominal_monthly.loc[common] - cpi_yoy.loc[common]).dropna()
    real_pre.name = "real_yield_pct"

    if tips_10y is None or tips_10y.empty:
        return real_pre

    tips = tips_10y.dropna().astype("float64")
    tips.index = pd.DatetimeIndex(tips.index)
    tips_monthly = tips.resample("ME").last().dropna()
    if tips_monthly.empty:
        return real_pre

    pre = real_pre.loc[real_pre.index < splice_date]
    post = tips_monthly.loc[tips_monthly.index >= splice_date]

    # Continuity check: warn if the gap at the splice point is large.
    overlap = real_pre.index.intersection(tips_monthly.index)
    if len(overlap) >= 3:
        diff = (real_pre.loc[overlap] - tips_monthly.loc[overlap]).abs().mean()
        if diff > 1.0:
            logger.warning(
                "Real-yield splice discontinuity: |Shiller-derived - TIPS| ~ %.2f pp",
                diff,
            )

    combined = pd.concat([pre, post]).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]
    combined.name = "real_yield_pct"
    return combined


def compute_ey_deficit(
    shiller_data: ShillerData,
    gs10_series: pd.Series | None = None,
    tips_series: pd.Series | None = None,
) -> dict[str, pd.Series]:
    """Compute the Equity Yield Deficit variant.

    Returns dict with key ``ey_deficit``: monthly Series in PERCENT units
    (positive => bonds offer more yield than equities => overvalued).
    """
    df = shiller_data.data
    missing: list[str] = []
    if "cape" not in df.columns:
        missing.append("cape")
    if "long_rate_gs10" not in df.columns and gs10_series is None:
        missing.append("long_rate_gs10")
    if "cpi" not in df.columns:
        missing.append("cpi")
    if missing:
        raise EYDeficitInputMissingError(
            "EY-Deficit missing inputs: " + ", ".join(missing)
        )

    cape = df["cape"].dropna().astype("float64")
    cape_ey_pct = (1.0 / cape) * 100.0
    cape_ey_pct.name = "cape_earnings_yield_pct"
    cape_ey_pct.index = (
        pd.DatetimeIndex(cape_ey_pct.index)
        .to_period("M")
        .to_timestamp(how="end")
        .normalize()
    )

    nominal_gs10 = (
        gs10_series.dropna().astype("float64")
        if gs10_series is not None
        else df["long_rate_gs10"].dropna().astype("float64")
    )
    cpi = df["cpi"].dropna().astype("float64")

    real_yield = compute_real_10y_yield(nominal_gs10, cpi, tips_series)

    aligned = pd.concat(
        [cape_ey_pct, real_yield], axis=1, keys=["cape_ey", "real_yield"]
    ).dropna()
    eyd = (aligned["real_yield"] - aligned["cape_ey"]).rename("ey_deficit")
    return {"ey_deficit": eyd}


__all__ = [
    "EYDeficitInputMissingError",
    "compute_real_10y_yield",
    "compute_ey_deficit",
]
