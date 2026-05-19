"""CAPE valuation indicator extraction from Shiller data (Spec v6.0).

CAPE = Cyclically Adjusted P/E ratio = P / (10-year-trailing real earnings).
Shiller (1996) introduced this as the canonical long-horizon valuation
predictor. Note that CAPE is undefined for the first ~10 years of the
Shiller series (1871-1880) because the trailing-real-earnings window has
insufficient history; NaN values are dropped at this layer.
"""
from __future__ import annotations

import pandas as pd

from src.ingest.shiller_loader import ShillerData


def compute_cape_variants(shiller_data: ShillerData) -> dict[str, pd.Series]:
    """Extract CAPE-based valuation series from ``shiller_data``.

    Returns dict with key ``cape`` (Shiller's standard P/E10).
    Series has a monthly DatetimeIndex starting around 1881-01 and ends at
    the latest Shiller publication date.
    """
    out: dict[str, pd.Series] = {}
    if "cape" in shiller_data.data.columns:
        cape = shiller_data.data["cape"].dropna()
        cape.name = "cape"
        out["cape"] = cape
    return out


__all__ = ["compute_cape_variants"]
