"""Tests for src.models.bai_perron."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models import bai_perron as bp_mod
from src.models.bai_perron import bai_perron


def _monthly(values: np.ndarray, start: str = "1947-01-31") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="ME")
    return pd.Series(values, index=idx, name="y")


def _pure_log_linear(n: int = 720, slope: float = 0.01, sigma: float = 0.01, seed: int = 0) -> pd.Series:
    rng = np.random.RandomState(seed)
    t = np.arange(n, dtype="float64")
    return _monthly(slope * t + sigma * rng.randn(n))


def _one_break(n1: int = 500, n2: int = 500, slope1: float = 0.01, slope2: float = 0.05, sigma: float = 0.01, seed: int = 1) -> pd.Series:
    rng = np.random.RandomState(seed)
    t1 = np.arange(n1, dtype="float64")
    seg1 = slope1 * t1
    seg2 = seg1[-1] + slope2 * np.arange(1, n2 + 1, dtype="float64")
    vals = np.concatenate([seg1, seg2]) + sigma * rng.randn(n1 + n2)
    return _monthly(vals)


def _two_breaks(n: int = 720, b1: int = 240, b2: int = 480, slopes=(0.01, 0.05, 0.02), sigma: float = 0.01, seed: int = 2) -> pd.Series:
    rng = np.random.RandomState(seed)
    boundaries = [0, b1, b2, n]
    vals = np.zeros(n)
    last = 0.0
    for k in range(3):
        a, b = boundaries[k], boundaries[k + 1]
        slope = slopes[k]
        seg_t = np.arange(b - a, dtype="float64")
        vals[a:b] = last + slope * seg_t
        last = vals[b - 1]
    return _monthly(vals + sigma * rng.randn(n))


# ---------------------------------------------------------------------------
# BP1 -- pure log-linear -> m_optimal == 0
# ---------------------------------------------------------------------------


def test_BP1_pure_loglinear_no_breaks() -> None:
    s = _pure_log_linear(n=720, slope=0.01, sigma=0.005)
    res = bai_perron(s, max_breaks=3)
    assert res["m_optimal"] == 0
    # Single segment should recover slope ~ 0.01.
    seg = res["segments"][0]
    assert seg["beta"] == pytest.approx(0.01, abs=1e-3)


# ---------------------------------------------------------------------------
# BP2 -- one break detected within +/-10 obs of truth
# ---------------------------------------------------------------------------


def test_BP2_one_break_detected() -> None:
    s = _one_break(n1=400, n2=400, slope1=0.005, slope2=0.05, sigma=0.01)
    res = bai_perron(s, max_breaks=3, min_segment_size=60)
    assert res["m_optimal"] >= 1
    # Closest detected break should be near index 400.
    detected = res["break_indices"]
    assert min(abs(b - 400) for b in detected) <= 15


# ---------------------------------------------------------------------------
# BP3 -- two breaks detected
# ---------------------------------------------------------------------------


def test_BP3_two_breaks_detected() -> None:
    s = _two_breaks(n=720, b1=240, b2=480, slopes=(0.005, 0.05, 0.01), sigma=0.01)
    res = bai_perron(s, max_breaks=5, min_segment_size=60)
    assert res["m_optimal"] >= 2
    detected = res["break_indices"]
    # Each true break should have *some* detected break within 20 obs.
    for true_b in (240, 480):
        assert min(abs(b - true_b) for b in detected) <= 20


# ---------------------------------------------------------------------------
# BP4 -- m=0 fitted matches log-linear OLS exactly
# ---------------------------------------------------------------------------


def test_BP4_m0_matches_log_linear() -> None:
    s = _pure_log_linear(n=300, slope=0.008, sigma=0.005)
    res = bai_perron(s, max_breaks=2)
    assert res["m_optimal"] == 0
    # Compare with statsmodels OLS log-linear from src.models.trend
    import statsmodels.api as sm
    t = np.arange(1, len(s) + 1, dtype="float64")
    X = sm.add_constant(t)
    fit = sm.OLS(s.values, X).fit()
    expected_fitted = fit.predict(X)
    np.testing.assert_allclose(res["fitted"].values, expected_fitted, atol=1e-8)


# ---------------------------------------------------------------------------
# BP5 -- series too short -> ValueError
# ---------------------------------------------------------------------------


def test_BP5_too_short_raises() -> None:
    s = _monthly(np.linspace(0, 1, 100))
    with pytest.raises(ValueError):
        bai_perron(s, min_segment_size=60)  # need T >= 120


# ---------------------------------------------------------------------------
# BP6 -- all-NaN -> ValueError after dropna
# ---------------------------------------------------------------------------


def test_BP6_all_nan_raises() -> None:
    s = _monthly(np.full(300, np.nan))
    with pytest.raises(ValueError):
        bai_perron(s)


# ---------------------------------------------------------------------------
# BP7 -- constant series -> m=0, beta~=0
# ---------------------------------------------------------------------------


def test_BP7_constant_series() -> None:
    s = _monthly(np.full(300, 3.14))
    res = bai_perron(s, max_breaks=2, min_segment_size=60)
    assert res["m_optimal"] == 0
    seg = res["segments"][0]
    assert seg["beta"] == pytest.approx(0.0, abs=1e-9)
    assert seg["alpha"] == pytest.approx(3.14, abs=1e-9)


# ---------------------------------------------------------------------------
# BP8 -- min_segment_size enforced
# ---------------------------------------------------------------------------


def test_BP8_min_segment_size_enforced() -> None:
    s = _two_breaks(n=720, b1=300, b2=320, slopes=(0.01, 0.05, 0.01))
    # Force min_segment_size=80 so two breaks 20 obs apart can't coexist.
    res = bai_perron(s, max_breaks=5, min_segment_size=80)
    # Any pair of detected breaks must be >= 80 obs apart.
    bs = res["break_indices"]
    for i in range(len(bs) - 1):
        assert bs[i + 1] - bs[i] >= 80


# ---------------------------------------------------------------------------
# BP9 -- lwz selects fewer-or-equal breaks vs bic
# ---------------------------------------------------------------------------


def test_BP9_lwz_more_conservative() -> None:
    s = _two_breaks(n=720, b1=240, b2=480, slopes=(0.005, 0.03, 0.01), sigma=0.02)
    res_bic = bai_perron(s, max_breaks=5, criterion="bic")
    res_lwz = bai_perron(s, max_breaks=5, criterion="lwz")
    assert res_lwz["m_optimal"] <= res_bic["m_optimal"]


# ---------------------------------------------------------------------------
# BP10 -- fitted has same DatetimeIndex as input (dropna'd)
# ---------------------------------------------------------------------------


def test_BP10_fitted_index_matches_input() -> None:
    s = _pure_log_linear(n=200, slope=0.01)
    res = bai_perron(s, max_breaks=2, min_segment_size=60)
    assert res["fitted"].index.equals(s.index)
    assert res["residuals"].index.equals(s.index)


# ---------------------------------------------------------------------------
# BP11 -- per-segment residuals sum to ~0
# ---------------------------------------------------------------------------


def test_BP11_segment_residuals_sum_near_zero() -> None:
    s = _two_breaks(n=600, b1=200, b2=400)
    res = bai_perron(s, max_breaks=5, min_segment_size=60)
    for seg in res["segments"]:
        seg_resid = res["residuals"].loc[seg["start"] : seg["end"]]
        assert abs(seg_resid.sum()) < 1e-6


# ---------------------------------------------------------------------------
# BP12 -- reproducibility (deterministic DP)
# ---------------------------------------------------------------------------


def test_BP12_reproducible() -> None:
    s = _one_break(n1=300, n2=300, sigma=0.01)
    a = bai_perron(s, max_breaks=3, min_segment_size=60)
    b = bai_perron(s, max_breaks=3, min_segment_size=60)
    assert a["m_optimal"] == b["m_optimal"]
    assert a["break_indices"] == b["break_indices"]
    np.testing.assert_array_equal(a["fitted"].values, b["fitted"].values)
