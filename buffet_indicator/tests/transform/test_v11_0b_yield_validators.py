"""v11.0b — tests for the yield-aware validator suite that replaced the
v11.0a csv_loader bypass.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.transform.yield_curve_compute import (
    YIELD_MAX_PCT,
    YIELD_MIN_PCT,
    YieldValidationError,
    _validate_yield_series,
)


def _good_series(n: int = 250, start: float = 2.0) -> pd.Series:
    idx = pd.date_range("2010-01-01", periods=n, freq="B")
    return pd.Series(np.linspace(start, start + 0.5, n), index=idx, name="y")


def test_good_series_passes() -> None:
    s = _good_series()
    _validate_yield_series(s, "test")  # no exception


def test_monotonic_check_fires_on_out_of_order_data() -> None:
    s = _good_series()
    bad = s.copy()
    # Swap first two index values to break monotonicity.
    bad.index = bad.index.tolist()
    new_index = list(bad.index)
    new_index[0], new_index[1] = new_index[1], new_index[0]
    bad.index = pd.DatetimeIndex(new_index)
    with pytest.raises(YieldValidationError, match="monotonic"):
        _validate_yield_series(bad, "test")


def test_duplicate_check_fires_on_repeated_dates() -> None:
    s = _good_series()
    dup_index = s.index.tolist()
    dup_index[0] = dup_index[1]  # introduce a duplicate
    bad = pd.Series(s.values, index=pd.DatetimeIndex(dup_index), name="y")
    with pytest.raises(YieldValidationError, match="duplicate"):
        _validate_yield_series(bad, "test")


def test_min_rows_check_fires_on_tiny_input() -> None:
    s = _good_series(n=50)
    with pytest.raises(YieldValidationError, match="(<100|rows)"):
        _validate_yield_series(s, "test")


def test_nan_fraction_check_fires_when_above_5pct() -> None:
    s = _good_series(n=200)
    # Inject 20% NaN.
    s = s.copy()
    s.iloc[:40] = np.nan
    with pytest.raises(YieldValidationError, match="NaN fraction"):
        _validate_yield_series(s, "test")


def test_range_check_fires_on_absurd_high_value() -> None:
    s = _good_series()
    s.iloc[10] = 50.0  # way above 25%
    with pytest.raises(YieldValidationError, match=r"outside.*range"):
        _validate_yield_series(s, "test")


def test_range_check_fires_on_absurd_low_value() -> None:
    s = _good_series()
    s.iloc[10] = -10.0  # well below -1.5%
    with pytest.raises(YieldValidationError, match=r"outside.*range"):
        _validate_yield_series(s, "test")


def test_zirp_zero_yield_does_not_fail() -> None:
    """T-bill yields legitimately fell to 0 during ZIRP; must pass."""
    s = _good_series()
    s.iloc[20:40] = 0.0
    _validate_yield_series(s, "test")  # no exception


def test_briefly_negative_yield_within_band_passes() -> None:
    """2015 short-dated T-bills briefly printed negative; allowed within -1.5%."""
    s = _good_series()
    s.iloc[20:25] = -0.1
    _validate_yield_series(s, "test")


def test_range_constants_match_spec() -> None:
    """Range constants must match what the spec documents."""
    assert YIELD_MIN_PCT == -1.5
    assert YIELD_MAX_PCT == 25.0
