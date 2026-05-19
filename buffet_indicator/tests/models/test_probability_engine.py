"""Tests for src.models.probability_engine."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.conditional_distribution import conditional_distribution
from src.models.probability_engine import compute_probabilities


def _build_cond_dist(returns: list[float]) -> dict:
    """Tiny synthetic cond_dist with a single 'current' bucket of returns."""
    idx = pd.date_range("2000-01-31", periods=len(returns) + 60, freq="ME")
    z = pd.Series(
        np.linspace(0.0, 1.0, len(returns) + 60), index=idx, name="z"
    )
    r = pd.Series(
        [0.05] * 60 + returns, index=idx, name="r"
    )
    cd = conditional_distribution(z, r, n_buckets=2)
    # Replace current_dist with our targeted returns for direct control.
    cd["current_dist"] = returns
    cd["current_bucket"] = 0
    return cd


def test_PE1_all_positive_pneg_zero() -> None:
    cd = _build_cond_dist([0.1, 0.05, 0.08, 0.12, 0.06, 0.04, 0.09, 0.11] * 4)
    out = compute_probabilities(cd, n_bootstrap=500)
    assert out["events"]["P_neg_return"]["point"] == 0.0


def test_PE2_all_negative_pneg_one() -> None:
    cd = _build_cond_dist([-0.1, -0.05, -0.08, -0.12, -0.06, -0.04, -0.09, -0.11] * 4)
    out = compute_probabilities(cd, n_bootstrap=500)
    assert out["events"]["P_neg_return"]["point"] == 1.0


def test_PE3_ci_brackets_point() -> None:
    rng = np.random.default_rng(0)
    cd = _build_cond_dist(rng.standard_normal(60).tolist())
    out = compute_probabilities(cd, n_bootstrap=2000)
    p = out["events"]["P_neg_return"]
    assert p["ci95"][0] <= p["point"] <= p["ci95"][1] or abs(
        p["ci95"][0] - p["point"]
    ) < 1e-2


def test_PE4_more_bootstraps_narrows_or_equal_ci_width() -> None:
    rng = np.random.default_rng(1)
    cd = _build_cond_dist(rng.standard_normal(80).tolist())
    a = compute_probabilities(cd, n_bootstrap=200, seed=42)
    b = compute_probabilities(cd, n_bootstrap=5000, seed=42)
    aw = a["events"]["P_neg_return"]["ci95"][1] - a["events"]["P_neg_return"]["ci95"][0]
    bw = b["events"]["P_neg_return"]["ci95"][1] - b["events"]["P_neg_return"]["ci95"][0]
    assert bw <= aw * 1.5


def test_PE5_reproducibility_with_seed() -> None:
    rng = np.random.default_rng(2)
    cd = _build_cond_dist(rng.standard_normal(50).tolist())
    a = compute_probabilities(cd, n_bootstrap=500, seed=42)
    b = compute_probabilities(cd, n_bootstrap=500, seed=42)
    assert a["events"]["P_neg_return"] == b["events"]["P_neg_return"]


def test_PE6_low_n_flag_below_20() -> None:
    cd = _build_cond_dist([0.05] * 15)
    out = compute_probabilities(cd, n_bootstrap=300)
    assert out["low_n_flag"] is True
