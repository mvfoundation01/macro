"""Tests for src.models.bayesian_posterior."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.bayesian_posterior import (
    DEFAULT_GORDON_PRIOR,
    bayesian_forward_return,
)


_REG = {
    "alpha": 0.07,
    "beta": -0.02,
    "beta_se_nw": 0.005,
    "n_obs": 200,
}


def test_BP_T1_closed_form_matches_conjugate_formula() -> None:
    out = bayesian_forward_return(
        z_current=1.0, regression_result=_REG, residual_sd_override=0.02
    )
    # Manual Normal-Normal: prior (0.07, 0.015), lik = (0.07 - 0.02*1.0, 0.02) = (0.05, 0.02)
    import numpy as np

    prior_mean, prior_sd = 0.07, 0.015
    mu_lik, sd_lik = 0.05, 0.02
    pp = 1.0 / prior_sd**2
    lp = 1.0 / sd_lik**2
    post_prec = pp + lp
    post_mean_expected = (pp * prior_mean + lp * mu_lik) / post_prec
    post_sd_expected = np.sqrt(1.0 / post_prec)
    assert out["posterior_mean"] == pytest.approx(post_mean_expected, abs=1e-9)
    assert out["posterior_sd"] == pytest.approx(post_sd_expected, abs=1e-9)


def test_BP_T2_strong_prior_pulls_posterior_to_prior() -> None:
    # Tiny prior SD vs huge likelihood SD -> posterior near prior mean.
    out = bayesian_forward_return(
        z_current=2.0,
        regression_result={**_REG, "alpha": 0.07, "beta": -0.05},
        gordon_growth_prior={"mean": 0.07, "sd": 0.001},
        residual_sd_override=1.0,
    )
    assert abs(out["posterior_mean"] - 0.07) < 0.005


def test_BP_T3_weak_prior_pulls_posterior_to_likelihood() -> None:
    # Huge prior SD vs tight likelihood -> posterior near likelihood mean.
    out = bayesian_forward_return(
        z_current=2.0,
        regression_result={**_REG, "alpha": 0.07, "beta": -0.04},
        gordon_growth_prior={"mean": 0.07, "sd": 1.0},
        residual_sd_override=0.001,
    )
    mu_lik = 0.07 - 0.04 * 2.0  # = -0.01
    assert abs(out["posterior_mean"] - mu_lik) < 0.005


def test_default_prior_constants() -> None:
    assert DEFAULT_GORDON_PRIOR == {"mean": 0.07, "sd": 0.015}


def test_posterior_intervals_present() -> None:
    out = bayesian_forward_return(z_current=0.0, regression_result=_REG)
    assert "ci50" in out and "ci80" in out and "ci95" in out
    for lo, hi in (out["ci50"], out["ci80"], out["ci95"]):
        assert lo <= out["posterior_mean"] <= hi
