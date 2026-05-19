"""Tests for src.models.oos_validation."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.oos_validation import clark_west, goyal_welch_oos_r2


def _predictable_pair(n: int = 400, beta: float = -0.05, sigma: float = 0.01, seed: int = 0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    z = rng.standard_normal(n)
    r = beta * z + sigma * rng.standard_normal(n)
    return pd.Series(z, index=idx, name="z"), pd.Series(r, index=idx, name="r")


def _random_walk_pair(n: int = 400, sigma: float = 0.05, seed: int = 0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    z = rng.standard_normal(n)
    r = sigma * rng.standard_normal(n)  # no relationship to z
    return pd.Series(z, index=idx, name="z"), pd.Series(r, index=idx, name="r")


def test_OS1_predictable_positive_r2() -> None:
    z, r = _predictable_pair(n=400, beta=-0.05, sigma=0.005, seed=1)
    out = goyal_welch_oos_r2(z, r)
    assert out["r2_oos"] > 0.05


def test_OS2_random_walk_r2_near_zero_or_negative() -> None:
    z, r = _random_walk_pair(n=400, seed=2)
    out = goyal_welch_oos_r2(z, r)
    assert out["r2_oos"] < 0.05


def test_OS3_short_series_returns_nan() -> None:
    z, r = _predictable_pair(n=80, seed=3)
    out = goyal_welch_oos_r2(z, r, min_train=60)
    assert np.isnan(out["r2_oos"])


def test_OS4_clark_west_positive_when_predictive_beats() -> None:
    z, r = _predictable_pair(n=400, beta=-0.07, sigma=0.005, seed=4)
    out = clark_west(z, r)
    assert out["cw_stat"] > 0
    assert out["p_value"] < 0.10


def test_OS5_min_train_respected() -> None:
    z, r = _predictable_pair(n=200, seed=5)
    out = goyal_welch_oos_r2(z, r, min_train=120)
    assert out["n_oos_obs"] == 200 - 1 - 120


def test_OS6_output_dict_keys_stable() -> None:
    z, r = _predictable_pair(n=300, seed=6)
    out = goyal_welch_oos_r2(z, r)
    assert set(out.keys()) >= {
        "r2_oos",
        "n_oos_obs",
        "mse_model",
        "mse_benchmark",
        "oos_start_date",
    }
    cw = clark_west(z, r)
    assert set(cw.keys()) >= {"cw_stat", "p_value", "n_oos_obs"}
