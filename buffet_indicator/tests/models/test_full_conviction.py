"""Tests for src.models.full_conviction."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.full_conviction import (
    DEFAULT_WEIGHTS,
    full_conviction,
    historical_hit_rate,
)


def test_FC1_all_strong_inputs_score_near_5() -> None:
    out = full_conviction(
        abs_z=3.0,
        cross_variant_agreement=1.0,
        t_hac=-6.0,
        r2_oos=0.30,
        hit_rate=0.95,
    )
    assert out["score"] >= 4.7


def test_FC2_all_weak_inputs_score_near_1() -> None:
    out = full_conviction(
        abs_z=0.0,
        cross_variant_agreement=0.0,
        t_hac=0.0,
        r2_oos=0.0,
        hit_rate=0.0,
    )
    assert out["score"] == pytest.approx(1.0, abs=1e-9)


def test_FC3_default_weights_sum_to_one() -> None:
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


def test_FC4_hit_rate_returns_zero_when_no_matches() -> None:
    idx = pd.date_range("2000-01-31", periods=200, freq="ME")
    z = pd.Series(np.linspace(-3.0, 3.0, 200), index=idx, name="z")
    r = pd.Series(np.zeros(200), index=idx, name="r")
    out = historical_hit_rate(
        z, r, current_z=10.0, horizon_months=12, z_window=0.5
    )
    assert out["n_matches"] == 0
    assert np.isnan(out["hit_rate"])


def test_FC_score_clipped_to_5() -> None:
    out = full_conviction(
        abs_z=10.0,
        cross_variant_agreement=1.0,
        t_hac=100.0,
        r2_oos=1.0,
        hit_rate=1.0,
    )
    assert out["score"] == pytest.approx(5.0, abs=1e-9)


def test_FC_frame_disagreement_penalty_subtracts() -> None:
    base = full_conviction(
        abs_z=2.0,
        cross_variant_agreement=0.8,
        t_hac=-3.0,
        r2_oos=0.20,
        hit_rate=0.80,
    )
    pen = full_conviction(
        abs_z=2.0,
        cross_variant_agreement=0.8,
        t_hac=-3.0,
        r2_oos=0.20,
        hit_rate=0.80,
        frame_disagreement_penalty=0.5,
    )
    assert base["score"] - pen["score"] == pytest.approx(0.5, abs=1e-9)


def test_FC_weights_assertion_raises_on_bad_sum() -> None:
    with pytest.raises(AssertionError):
        full_conviction(
            abs_z=1.0,
            cross_variant_agreement=1.0,
            t_hac=1.0,
            r2_oos=0.1,
            hit_rate=0.5,
            weights={
                "magnitude": 0.5,
                "agreement": 0.2,
                "significance": 0.2,
                "oos_r2": 0.1,
                "hit_rate": 0.1,
            },
        )


def test_historical_hit_rate_overvalued_direction() -> None:
    idx = pd.date_range("2000-01-31", periods=300, freq="ME")
    rng = np.random.default_rng(42)
    z = pd.Series(rng.standard_normal(300), index=idx, name="z")
    # Construct r so high z -> low r.
    r = pd.Series(-0.05 * z.values + 0.01 * rng.standard_normal(300), index=idx, name="r")
    out = historical_hit_rate(
        z, r, current_z=2.0, horizon_months=12, z_window=0.5, threshold_5pct=0.05
    )
    assert out["direction"] == "overvalued_to_low_return"
    assert out["n_matches"] > 0
