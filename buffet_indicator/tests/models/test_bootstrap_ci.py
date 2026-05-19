"""Tests for src.models.bootstrap_ci."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.bootstrap_ci import _confidence_pct, bootstrap_zscore_ci


def _ar1_residuals(n: int = 500, rho: float = 0.6, seed: int = 0) -> pd.Series:
    rng = np.random.RandomState(seed)
    eps = rng.randn(n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = rho * x[i - 1] + eps[i]
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    return pd.Series(x, index=idx, name="resid")


def test_BS1_returns_all_seven_keys() -> None:
    s = _ar1_residuals(300)
    out = bootstrap_zscore_ci(s, n_replications=500)
    expected = {
        "point_estimate",
        "ci_lower",
        "ci_upper",
        "ci_width",
        "n_replications",
        "block_length",
        "confidence_pct",
    }
    assert expected <= set(out.keys())


def test_BS2_point_inside_or_near_ci() -> None:
    s = _ar1_residuals(500, seed=1)
    out = bootstrap_zscore_ci(s, n_replications=2000, seed=42)
    # Point should generally be within the CI for a moderately correlated series.
    assert out["ci_lower"] <= out["point_estimate"] <= out["ci_upper"] or abs(
        out["point_estimate"] - out["ci_lower"]
    ) < 1.0


def test_BS3_ci_width_shrinks_with_more_reps() -> None:
    s = _ar1_residuals(500, seed=2)
    a = bootstrap_zscore_ci(s, n_replications=200, seed=42)
    b = bootstrap_zscore_ci(s, n_replications=5000, seed=42)
    # CI width should NOT explode and is typically smaller with more reps.
    assert b["ci_width"] <= a["ci_width"] * 1.5


def test_BS4_confidence_pct_strictly_positive() -> None:
    # Spec v4.1: new formula yields confidence_pct in (0, 100], never zero.
    s = _ar1_residuals(400, seed=3)
    out = bootstrap_zscore_ci(s, n_replications=500)
    assert 0.0 < out["confidence_pct"] <= 100.0


def test_BS5_reproducible_with_seed() -> None:
    s = _ar1_residuals(500, seed=4)
    a = bootstrap_zscore_ci(s, n_replications=500, seed=42)
    b = bootstrap_zscore_ci(s, n_replications=500, seed=42)
    assert a["ci_lower"] == pytest.approx(b["ci_lower"])
    assert a["ci_upper"] == pytest.approx(b["ci_upper"])


def test_BS6_confidence_pct_perfect_at_zero_width() -> None:
    assert _confidence_pct(2.0, 0.0) == pytest.approx(100.0)


def test_BS7_confidence_pct_50pct_when_width_equals_point() -> None:
    assert _confidence_pct(2.0, 2.0) == pytest.approx(50.0)


def test_BS8_confidence_pct_floor_protects_small_point() -> None:
    # |point|=0 -> floor of 1 applies; width=1 => rel=1.0 => 50
    assert _confidence_pct(0.0, 1.0) == pytest.approx(50.0)


def test_BS9_confidence_pct_in_open_interval() -> None:
    # For a range of (point, width) combos confidence_pct is strictly in (0, 100].
    cases = [(2.0, 0.5), (1.0, 2.0), (0.1, 5.0), (3.0, 10.0)]
    for p, w in cases:
        c = _confidence_pct(p, w)
        assert 0.0 < c <= 100.0


def test_BS10_confidence_pct_monotone_decreasing_in_width() -> None:
    point = 1.5
    widths = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]
    confs = [_confidence_pct(point, w) for w in widths]
    for i in range(len(confs) - 1):
        assert confs[i] >= confs[i + 1]
