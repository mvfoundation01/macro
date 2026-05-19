"""Tests for src.models.predictive_regression."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.predictive_regression import (
    InsufficientSampleError,
    _hansen_hodrick_se,
    _stambaugh_correction,
    predictive_regression,
)


def _monthly_pair(
    n: int = 240,
    beta_true: float = -0.05,
    sigma: float = 0.02,
    rho_z: float = 0.0,
    seed: int = 0,
) -> tuple[pd.Series, pd.Series]:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    z = np.zeros(n)
    for i in range(1, n):
        z[i] = rho_z * z[i - 1] + rng.standard_normal()
    eps = sigma * rng.standard_normal(n)
    r = beta_true * z + eps
    return pd.Series(z, index=idx, name="z"), pd.Series(r, index=idx, name="r")


def test_PR1_synthetic_recovers_beta() -> None:
    z, r = _monthly_pair(n=400, beta_true=-0.05, sigma=0.01, seed=1)
    res = predictive_regression(z, r, horizon_months=1)
    assert res["beta"] == pytest.approx(-0.05, abs=0.005)


def test_PR2_newey_west_se_finite_and_positive() -> None:
    z, r = _monthly_pair(n=300, beta_true=-0.04, sigma=0.02, seed=2)
    res = predictive_regression(z, r, horizon_months=12)
    assert np.isfinite(res["beta_se_nw"])
    assert res["beta_se_nw"] > 0


def test_PR3_hansen_hodrick_se_finite_or_nan() -> None:
    z, r = _monthly_pair(n=300, beta_true=-0.04, sigma=0.02, seed=3)
    res = predictive_regression(z, r, horizon_months=12)
    se = res["beta_se_hh"]
    assert (se > 0 and np.isfinite(se)) or np.isnan(se)


def test_PR4_stambaugh_correction_size_depends_on_rho() -> None:
    # Low-rho: tiny correction.
    z_lo, r_lo = _monthly_pair(n=400, rho_z=0.0, seed=4)
    # High-rho (near-unit-root): larger correction.
    z_hi, r_hi = _monthly_pair(n=400, rho_z=0.95, seed=4)
    res_lo = predictive_regression(z_lo, r_lo, horizon_months=12)
    res_hi = predictive_regression(z_hi, r_hi, horizon_months=12)
    assert abs(res_hi["beta_stambaugh_bias"]) >= abs(res_lo["beta_stambaugh_bias"])


def test_PR5_n_below_30_raises() -> None:
    z = pd.Series(
        np.arange(20, dtype="float64"),
        index=pd.date_range("2020-01-31", periods=20, freq="ME"),
    )
    r = z * -0.05
    with pytest.raises(InsufficientSampleError):
        predictive_regression(z, r, horizon_months=1)


def test_PR6_nans_dropped() -> None:
    z, r = _monthly_pair(n=200, seed=5)
    z.iloc[10:20] = np.nan
    res = predictive_regression(z, r, horizon_months=1)
    assert res["n_obs"] == 190


def test_PR7_rho_ar1_recovered() -> None:
    z, r = _monthly_pair(n=600, rho_z=0.8, seed=6)
    res = predictive_regression(z, r, horizon_months=1)
    assert res["rho_ar1"] == pytest.approx(0.8, abs=0.05)


def test_PR8_reproducibility() -> None:
    z, r = _monthly_pair(n=300, seed=7)
    a = predictive_regression(z, r, horizon_months=12)
    b = predictive_regression(z, r, horizon_months=12)
    assert a == b


def test_PR9_sign_of_beta_matches_truth() -> None:
    z, r = _monthly_pair(n=300, beta_true=-0.05, sigma=0.01, seed=8)
    res = predictive_regression(z, r, horizon_months=1)
    assert res["beta"] < 0
    z2, r2 = _monthly_pair(n=300, beta_true=+0.03, sigma=0.01, seed=9)
    res2 = predictive_regression(z2, r2, horizon_months=1)
    assert res2["beta"] > 0


def test_PR10_stambaugh_bias_opposite_sign_of_gamma_eu() -> None:
    """Bias = -(gamma_eu / gamma_uu) * (1 + 3*rho) / T, so sign opposite gamma_eu."""
    rng = np.random.default_rng(10)
    z = rng.standard_normal(300)
    eps = rng.standard_normal(300)
    bs = _stambaugh_correction(z, eps, beta_ols=0.0)
    # bias_estimate sign should be opposite to gamma_eu sign (or both ~0).
    if abs(bs["gamma_eu"]) > 1e-9 and abs(bs["bias_estimate"]) > 1e-9:
        assert np.sign(bs["bias_estimate"]) == -np.sign(bs["gamma_eu"])


def test_hansen_hodrick_se_helper_runs() -> None:
    rng = np.random.default_rng(11)
    x = rng.standard_normal(200)
    eps = rng.standard_normal(200)
    se = _hansen_hodrick_se(x, eps, max_lag=11)
    assert se > 0 or np.isnan(se)
