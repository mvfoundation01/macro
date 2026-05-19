"""Tests for src.transform.huber_scale."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.transform.huber_scale import robust_scale


def test_H1_huber_on_normal_recovers_sigma() -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal(10_000)
    _, sc = robust_scale(x, method="huber")
    assert sc == pytest.approx(1.0, abs=0.05)


def test_H2_huber_with_outliers_smaller_than_std() -> None:
    rng = np.random.default_rng(1)
    base = rng.standard_normal(900)
    outliers = rng.standard_normal(100) * 8.0
    x = np.concatenate([base, outliers])
    _, sc_huber = robust_scale(x, method="huber")
    _, sc_std = robust_scale(x, method="std")
    assert sc_huber < sc_std * 0.6  # Huber strongly down-weights outliers


def test_H3_mad_on_normal_within_5pct() -> None:
    rng = np.random.default_rng(2)
    x = rng.standard_normal(5_000)
    _, sc = robust_scale(x, method="mad")
    assert sc == pytest.approx(1.0, abs=0.05)


def test_H4_huber_tiny_sample_falls_back_to_mad() -> None:
    x = np.array([0.1, -0.2, 0.3])
    loc, sc = robust_scale(x, method="huber")
    assert np.isfinite(loc)
    assert np.isfinite(sc) and sc > 0


def test_H5_returns_two_floats_with_positive_scale() -> None:
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    loc, sc = robust_scale(x, method="huber")
    assert isinstance(loc, float)
    assert isinstance(sc, float)
    assert sc > 0


def test_H6_huber_smaller_on_fat_tail_residuals() -> None:
    """Synthetic 'BI-residuals' with fat negative tail: Huber sigma < std sigma."""
    rng = np.random.default_rng(3)
    bulk = rng.standard_normal(1_000) * 0.1
    crashes = rng.standard_normal(50) * 0.4 - 0.6  # large negative residuals
    x = np.concatenate([bulk, crashes])
    _, sc_huber = robust_scale(x, method="huber")
    _, sc_std = robust_scale(x, method="std")
    assert sc_huber < sc_std
