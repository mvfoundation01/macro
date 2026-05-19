"""5-tier valuation regime classification with dashboard color palette."""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd


# Ordered most-extreme-first; each predicate returns True for its band.
REGIMES: list[tuple[str, Callable[[float], bool], str]] = [
    ("Strongly Overvalued",  lambda z: z > 2.0,    "#C8102E"),   # red
    ("Overvalued",           lambda z: z > 1.0,    "#E87722"),   # orange
    ("Fair Value",           lambda z: z >= -1.0,  "#9AA0A6"),   # gray
    ("Undervalued",          lambda z: z >= -2.0,  "#5DBB63"),   # light green
    ("Strongly Undervalued", lambda z: True,       "#1B7A3E"),   # dark green
]


def classify(z: float) -> tuple[str, str]:
    """Return ``(regime_label, hex_color)`` for a z-score. NaN -> Insufficient Data."""
    if z is None or (isinstance(z, float) and np.isnan(z)) or pd.isna(z):
        return ("Insufficient Data", "#000000")
    z_f = float(z)
    for label, predicate, color in REGIMES:
        if predicate(z_f):
            return (label, color)
    last = REGIMES[-1]
    return (last[0], last[2])


def classify_series(z_series: pd.Series) -> pd.DataFrame:
    """Map a z-series to columns ``z``, ``regime``, ``color``."""
    labels_colors = [classify(z) for z in z_series]
    return pd.DataFrame(
        {
            "z": z_series.values,
            "regime": [lc[0] for lc in labels_colors],
            "color": [lc[1] for lc in labels_colors],
        },
        index=z_series.index,
    )


__all__ = ["REGIMES", "classify", "classify_series"]
