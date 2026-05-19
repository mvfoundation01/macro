"""Tests for src.models.zscore."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.zscore import empirical_percentile, expanding_zscore, full_sample_zscore


def _series(values: list[float]) -> pd.Series:
    idx = pd.date_range("2000-01-31", periods=len(values), freq="ME")
    return pd.Series(values, index=idx, name="resid")


def test_Z1_expanding_zscore_first_59_nan() -> None:
    s = _series(list(np.random.RandomState(0).randn(120)))
    z = expanding_zscore(s, min_periods=60)
    assert z.iloc[:59].isna().all()
    assert pd.notna(z.iloc[59])


def test_Z2_full_sample_zscore_mean_std() -> None:
    rng = np.random.RandomState(42)
    s = _series(list(rng.randn(500)))
    # Use std scale to test the classical "mean=0, std=1" property; the new
    # default (huber) gives a robust mean/scale that won't exactly match.
    z = full_sample_zscore(s, scale_method="std")
    assert z.mean() == pytest.approx(0.0, abs=1e-12)
    assert z.std(ddof=1) == pytest.approx(1.0, abs=1e-10)


def test_Z3_expanding_zscore_iid_near_normal_in_tail() -> None:
    rng = np.random.RandomState(7)
    s = _series(list(rng.randn(2000)))
    z = expanding_zscore(s, min_periods=60).dropna()
    # In the tail of a large iid sample the expanding mean/std converge to truth.
    assert z.iloc[-1] == pytest.approx(s.iloc[-1], abs=0.05)


def test_Z4_percentile_at_max_is_100() -> None:
    s = _series([1.0, 2.0, 3.0, 4.0, 5.0])
    p = empirical_percentile(s, value=float(s.max()))
    assert p == pytest.approx(100.0)


def test_Z5_percentile_at_median_is_50() -> None:
    s = _series([1.0, 2.0, 3.0, 4.0, 5.0])
    p = empirical_percentile(s, value=float(s.median()))
    # 3.0 is the median; (s <= 3.0).mean() = 3/5 = 60
    assert p == pytest.approx(60.0)


def test_Z6_empirical_percentile_value_none_returns_series() -> None:
    s = _series([3.0, 1.0, 2.0, 5.0, 4.0])
    out = empirical_percentile(s, value=None)
    assert isinstance(out, pd.Series)
    assert len(out) == len(s)
    # Last entry is the rank of s.iloc[-1] in the full series.
    assert out.iloc[-1] == pytest.approx(80.0)  # 4 of 5 <= 4.0
