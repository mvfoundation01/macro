"""Tobin's Q-Ratio = Market Value of Equities / Net Worth (Replacement Cost).

Sources (FRED Z.1, table B.103):
    - ``NCBEILQ027S`` -- Nonfinancial corporate equities, market value (numerator).
                          (Already loaded in v1.0; reused.)
    - ``TNWMVBSNNCB`` -- Nonfinancial corporate net worth (denominator).
                          (Optional v7 addition; loader logs WARNING if absent.)

Between Z.1 publications (~10-week lag) the daily VTI total-market ETF price
acts as a surrogate for market-value movement. Net worth is held constant
within the post-release tail.

References
----------
Tobin (1969) "A General Equilibrium Approach to Monetary Theory" JMCB 1(1).
Smithers & Wright (2000) Valuing Wall Street, McGraw-Hill.
"""
from __future__ import annotations

import pandas as pd

from src.ingest._base import IngestError, get_logger
from src.ingest.fred_loader import FredSeries

logger = get_logger("buffett.transform.qratio")


class QRatioInputMissingError(IngestError):
    """Required Z.1 inputs for Q-Ratio are unavailable."""


def compute_qratio(
    equities_nonfin: FredSeries,
    nonfin_net_worth: FredSeries | None,
    vti_series: pd.Series | None = None,
) -> pd.Series:
    """Return Tobin's Q-Ratio at monthly resolution.

    ``equities_nonfin`` is the market value of nonfinancial-corporate equities
    (FRED ``NCBEILQ027S``, millions of USD). ``nonfin_net_worth`` is FRED
    ``TNWMVBSNNCB`` (replacement-cost net worth, billions of USD).

    Returns a monthly Series of dimensionless Q-Ratio values (~0.3-2.5 over
    the 1952-present sample).
    """
    if nonfin_net_worth is None:
        raise QRatioInputMissingError(
            "Q-Ratio requires FRED TNWMVBSNNCB (nonfinancial net worth) which is "
            "not loaded. Pass load_fred_optional(api_key, keys=('nonfin_net_worth',))."
        )

    # Both FRED series are published in MILLIONS of USD (the API metadata
    # reports "Mil. of U.S. $" for both NCBEILQ027S and TNWMVBSNNCB despite
    # the FRED webpage sometimes labeling the latter "Billions"). No unit
    # conversion needed; the ratio is dimensionless.
    equities = equities_nonfin.data.dropna().astype("float64")
    net_worth = nonfin_net_worth.data.dropna().astype("float64")

    common = equities.index.intersection(net_worth.index)
    if common.empty:
        raise QRatioInputMissingError(
            "Q-Ratio: numerator and denominator share no overlapping quarter-ends"
        )

    q_quarterly = (equities.loc[common] / net_worth.loc[common]).dropna()
    q_quarterly.name = "qratio"

    if (q_quarterly <= 0).any():
        raise QRatioInputMissingError("Q-Ratio: non-positive quarterly values detected")

    # Quarter-end index already normalized by fred_loader.
    # Resample to monthly grid; forward-fill within a quarter (max 2 months).
    monthly_idx = pd.date_range(
        q_quarterly.index.min(), q_quarterly.index.max(), freq="ME"
    )
    q_monthly = q_quarterly.reindex(monthly_idx, method="ffill", limit=2).dropna()
    q_monthly.name = "qratio"

    # Tail extrapolation via VTI ratio (assume net_worth approximately constant).
    if vti_series is not None and not vti_series.empty:
        last_z1_date = q_quarterly.index.max()
        vti = vti_series.dropna().astype("float64")
        vti_monthly = vti.resample("ME").last().dropna()
        if last_z1_date in vti_monthly.index:
            vti_anchor = float(vti_monthly.loc[last_z1_date])
        else:
            # Use the latest VTI value at or before last_z1_date.
            pos = vti_monthly.index.searchsorted(last_z1_date, side="right") - 1
            if pos < 0:
                vti_anchor = None  # no anchor available
            else:
                vti_anchor = float(vti_monthly.iloc[pos])
        if vti_anchor is not None and vti_anchor > 0:
            q_anchor = float(q_quarterly.loc[last_z1_date])
            tail = vti_monthly.loc[vti_monthly.index > last_z1_date]
            extrapolated = q_anchor * (tail / vti_anchor)
            extrapolated.name = "qratio"
            # Append + dedupe.
            q_monthly = pd.concat([q_monthly, extrapolated])
            q_monthly = q_monthly[~q_monthly.index.duplicated(keep="last")].sort_index()
    return q_monthly


def compute_qratio_variant(
    equities_nonfin: FredSeries,
    nonfin_net_worth: FredSeries | None,
    vti_series: pd.Series | None = None,
) -> dict[str, pd.Series]:
    """Variant builder following the convention of compute_bi_variants."""
    try:
        q = compute_qratio(equities_nonfin, nonfin_net_worth, vti_series)
    except QRatioInputMissingError as exc:
        logger.warning("Q-Ratio variant skipped: %s", exc)
        return {}
    return {"qratio": q}


__all__ = [
    "QRatioInputMissingError",
    "compute_qratio",
    "compute_qratio_variant",
]
