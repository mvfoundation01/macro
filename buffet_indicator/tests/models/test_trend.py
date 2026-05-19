"""Tests for src.models.trend."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models import trend as tr


def _synthetic_exponential(
    n: int = 240, slope: float = 0.01, sigma: float = 0.005, seed: int = 0
) -> pd.Series:
    """Exponential trend with small lognormal-ish noise so SSR is non-degenerate."""
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    t = np.arange(n, dtype="float64")
    rng = np.random.RandomState(seed)
    log_trend = slope * t + sigma * rng.randn(n)
    return pd.Series(np.exp(log_trend), index=idx, name="s")


def test_T1_loglinear_on_exp_recovers_slope() -> None:
    s = _synthetic_exponential(n=240, slope=0.01, sigma=0.0, seed=0)
    # sigma=0 -> exact exponential, slope and r-squared recovered to machine precision.
    res = tr.log_linear_trend(s)
    assert res["beta"] == pytest.approx(0.01, abs=1e-6)
    assert res["r_squared"] > 0.999


def test_T2_hp_filter_sums_back() -> None:
    s = _synthetic_exponential(n=240, slope=0.008)
    res = tr.hp_filter_trend(s)
    # In log space, trend + cycle should reconstruct log(s) exactly.
    recon = np.log(res["fitted"].values) + res["residuals"].values
    np.testing.assert_allclose(recon, np.log(s.values), atol=1e-10)


def test_T3_hp_default_lambda_is_14400() -> None:
    s = _synthetic_exponential(120)
    res = tr.hp_filter_trend(s)
    assert res["lambda"] == 14400.0


def test_T4_trend_battery_keys() -> None:
    s = _synthetic_exponential(240)
    res = tr.trend_battery(s)
    assert "loglinear" in res
    assert "hp" in res
    assert "bai_perron" in res
    assert "agreement" in res
    assert "primary" in res
    assert "primary_residuals" in res
    # Spec v4.1 -- Bai-Perron is the primary trend.
    assert res["primary"] == "bai_perron"


def test_T5_trend_battery_agreement_high_on_exponential() -> None:
    # Long-enough sample with moderate noise so BIC unambiguously prefers m=0.
    s = _synthetic_exponential(n=720, slope=0.012, sigma=0.02, seed=11)
    res = tr.trend_battery(s)
    assert res["agreement"] > 0.95
    # No structural break -> Bai-Perron reduces to log-linear.
    assert res["bai_perron"]["n_breaks"] == 0
    np.testing.assert_allclose(
        res["primary_residuals"].values,
        res["loglinear"]["residuals"].values,
        atol=1e-8,
    )


def test_loglinear_empty_raises() -> None:
    s = pd.Series([], dtype="float64")
    with pytest.raises(ValueError):
        tr.log_linear_trend(s)


def test_loglinear_non_positive_raises() -> None:
    s = pd.Series([1.0, -2.0, 3.0], index=pd.date_range("2020-01-31", periods=3, freq="ME"))
    with pytest.raises(ValueError):
        tr.log_linear_trend(s)


def test_hp_empty_raises() -> None:
    s = pd.Series([], dtype="float64")
    with pytest.raises(ValueError):
        tr.hp_filter_trend(s)


def test_hp_non_positive_raises() -> None:
    s = pd.Series([1.0, 0.0, 3.0], index=pd.date_range("2020-01-31", periods=3, freq="ME"))
    with pytest.raises(ValueError):
        tr.hp_filter_trend(s)


def test_bai_perron_empty_raises() -> None:
    s = pd.Series([], dtype="float64")
    with pytest.raises(ValueError):
        tr.bai_perron_trend(s)


def test_bai_perron_non_positive_raises() -> None:
    s = pd.Series([1.0, -1.0], index=pd.date_range("2020-01-31", periods=2, freq="ME"))
    with pytest.raises(ValueError):
        tr.bai_perron_trend(s)


def test_trend_agreement_handles_short_overlap() -> None:
    # Series too short to give 5 overlapping points -> agreement returns 0.
    idx1 = pd.date_range("2020-01-31", periods=3, freq="ME")
    idx2 = pd.date_range("2021-01-31", periods=3, freq="ME")
    s1 = pd.Series([1.0, 2.0, 3.0], index=idx1)
    s2 = pd.Series([1.0, 2.0, 3.0], index=idx2)
    assert tr._trend_agreement([s1, s2]) == 0.0


def test_T6_break_detected_on_regime_shift() -> None:
    # Two regimes of 240 obs each so the min_segment_size default (15% of 480 = 72)
    # can comfortably place a break at the boundary.
    n1, n2 = 240, 240
    seg1 = np.exp(0.005 * np.arange(n1))
    seg2 = np.exp(0.005 * np.arange(n1, n1 + n2) + 0.5)  # level shift up
    vals = np.concatenate([seg1, seg2])
    idx = pd.date_range("2000-01-31", periods=n1 + n2, freq="ME")
    s = pd.Series(vals, index=idx, name="s")
    res = tr.bai_perron_trend(s, max_breaks=3)
    assert res["method"].startswith("bai_perron_")
    assert len(res["break_dates"]) >= 1
