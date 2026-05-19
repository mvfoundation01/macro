"""Wilshire index-points -> USD trillions via the documented anchor schedule.

Anchors (Master Spec section 4.2):
    1985-01-01: 1 index point ~= $1.00 B
    2020-01-01: 1 index point ~= $1.05 B
Linear interpolation between; linear extrapolation outside (both directions).
"""
from __future__ import annotations

import pandas as pd

ANCHORS: dict[pd.Timestamp, float] = {
    pd.Timestamp("1985-01-01"): 1.00,
    pd.Timestamp("2020-01-01"): 1.05,
}


def _year_fraction(t: pd.Timestamp) -> float:
    """Return the fractional year of a timestamp (e.g. 2020-07-01 -> 2020.498...)."""
    t = pd.Timestamp(t)
    # Use the year's actual day count so leap years are handled correctly.
    days_in_year = 366.0 if pd.Timestamp(year=t.year, month=12, day=31).dayofyear == 366 else 365.0
    return t.year + (t.dayofyear - 1) / days_in_year


def wilshire_multiplier(date: pd.Timestamp) -> float:
    """USD billions per Wilshire index point on the given date.

    Linear interpolation between the 1985 and 2020 anchors;
    linear extrapolation outside the anchor range using the same slope.
    """
    t_anchors = sorted(ANCHORS.keys())
    y_anchors = [ANCHORS[t] for t in t_anchors]
    slope = (y_anchors[1] - y_anchors[0]) / (
        _year_fraction(t_anchors[1]) - _year_fraction(t_anchors[0])
    )
    return y_anchors[0] + slope * (_year_fraction(date) - _year_fraction(t_anchors[0]))


def points_to_trillions(index_series: pd.Series) -> pd.Series:
    """Apply per-date multiplier to convert Wilshire points -> USD trillions."""
    if index_series.empty:
        return index_series.copy()
    multipliers_b = pd.Series(
        [wilshire_multiplier(d) for d in index_series.index],
        index=index_series.index,
        dtype="float64",
    )
    usd_billions = index_series * multipliers_b
    out = usd_billions / 1_000.0
    out.name = index_series.name
    return out


# Sanity guard executed at import time (cheap arithmetic, no I/O).
_mult_2026 = wilshire_multiplier(pd.Timestamp("2026-05-15"))
assert 1.057 < _mult_2026 < 1.060, (
    f"2026 multiplier {_mult_2026:.6f} outside expected band [1.057, 1.060]"
)


__all__ = ["ANCHORS", "wilshire_multiplier", "points_to_trillions"]
