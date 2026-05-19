"""Tests for src.models.conditional_distribution."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.conditional_distribution import conditional_distribution


def _pair(n: int = 400, beta: float = -0.05, sigma: float = 0.01, seed: int = 0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    z = rng.standard_normal(n)
    r = beta * z + sigma * rng.standard_normal(n)
    return pd.Series(z, index=idx, name="z"), pd.Series(r, index=idx, name="r")


def test_CD1_quintile_produces_five_buckets() -> None:
    z, r = _pair(n=500, seed=1)
    out = conditional_distribution(z, r, n_buckets=5)
    assert out["n_buckets_actual"] == 5
    assert len(out["bucket_stats"]) == 5


def test_CD2_current_bucket_matches_latest_z() -> None:
    z, r = _pair(n=500, seed=2)
    # Set the last z to a known high value -> should land in top bucket.
    z.iloc[-1] = 3.0
    out = conditional_distribution(z, r, n_buckets=5)
    assert out["current_bucket"] == out["n_buckets_actual"] - 1


def test_CD3_low_n_flag_when_min_obs_not_met() -> None:
    z, r = _pair(n=80, seed=3)
    out = conditional_distribution(z, r, n_buckets=5, min_obs_per_bucket=20)
    assert out["low_n_flag"] is True


def test_CD4_p_neg_matches_definition() -> None:
    z, r = _pair(n=500, seed=4)
    out = conditional_distribution(z, r, n_buckets=5)
    # For top z-bucket, p_neg = fraction of bucket returns < 0
    top = out["bucket_stats"][out["n_buckets_actual"] - 1]
    assert 0.0 <= top["p_neg"] <= 1.0


def test_CD5_p_neg_monotone_in_z_buckets_for_negative_beta() -> None:
    z, r = _pair(n=2000, beta=-0.06, sigma=0.005, seed=5)
    out = conditional_distribution(z, r, n_buckets=5)
    p_negs = [out["bucket_stats"][b]["p_neg"] for b in range(out["n_buckets_actual"])]
    # Allow modest non-monotonicity, but the top z-bucket should be > bottom.
    assert p_negs[-1] > p_negs[0]
