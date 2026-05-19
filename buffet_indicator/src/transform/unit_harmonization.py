"""Harmonize $-denominated series to USD trillions and rates to decimal."""
from __future__ import annotations

import pandas as pd


def to_trillions_from_millions(s: pd.Series) -> pd.Series:
    """FRED Z.1 series (millions of USD) -> trillions of USD."""
    return s / 1_000_000.0


def to_trillions_from_billions(s: pd.Series) -> pd.Series:
    """FRED GDP (billions SAAR) -> trillions."""
    return s / 1_000.0


def rate_to_decimal(s: pd.Series) -> pd.Series:
    """Idempotent: if first non-NaN > 1, treat as percent and divide by 100."""
    nz = s.dropna()
    if nz.empty:
        return s.copy()
    first = nz.iloc[0]
    if abs(first) > 1.0:
        return s / 100.0
    return s.copy()


__all__ = [
    "to_trillions_from_millions",
    "to_trillions_from_billions",
    "rate_to_decimal",
]
