"""Tests for src.models.preliminary_metrics."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.preliminary_metrics import (
    cross_variant_agreement,
    dual_frame_conviction,
    preliminary_conviction,
)


def test_P1_perfect_agreement() -> None:
    out = cross_variant_agreement({"a": 2.0, "b": 2.0, "c": 2.0})
    assert out["agreement"] == pytest.approx(1.0)
    assert out["same_sign"] is True
    assert out["same_regime"] is True
    assert out["combined_regime"] == "Overvalued"


def test_P2_divergent_zs() -> None:
    out = cross_variant_agreement({"a": +2.0, "b": -2.0, "c": 0.0})
    assert out["agreement"] < 0.3


def test_P3_same_sign_detection() -> None:
    out = cross_variant_agreement({"a": 0.5, "b": 1.0, "c": 1.5})
    assert out["same_sign"] is True
    out2 = cross_variant_agreement({"a": -0.5, "b": -1.0, "c": -1.5})
    assert out2["same_sign"] is True
    out3 = cross_variant_agreement({"a": -0.5, "b": 1.0, "c": 0.5})
    assert out3["same_sign"] is False


def test_P4_high_conviction_when_signal_strong() -> None:
    conv = preliminary_conviction(mean_z=2.5, agreement=0.95, n_observations=500)
    assert conv["score"] > 4.0


def test_P5_weights_sum_to_one() -> None:
    # Default weights add to 1.0 (assertion in code body).
    conv = preliminary_conviction(mean_z=0.0, agreement=0.0, n_observations=0)
    w = conv["weights"]
    assert w["magnitude"] + w["agreement"] + w["sample_size"] == pytest.approx(1.0)
    # Score floor: with all zero components, raw=0 -> score=1.0
    assert conv["score"] == pytest.approx(1.0)


def test_preliminary_conviction_invalid_weights_raises() -> None:
    with pytest.raises(AssertionError):
        preliminary_conviction(
            mean_z=2.0,
            agreement=0.9,
            n_observations=100,
            w_magnitude=0.5,
            w_agreement=0.4,
            w_sample=0.4,
        )


# ---------------------------------------------------------------------------
# Spec v4.2: dual_frame_conviction
# ---------------------------------------------------------------------------


def test_P6_dual_frame_strong_agreement_high_score() -> None:
    """Strong signal + perfect frame coherence -> score above 4.5."""
    out = dual_frame_conviction(
        long_run_mean_z=3.0,
        current_regime_mean_z=3.0,
        cross_variant_agreement_long_run=0.95,
        cross_variant_agreement_current_regime=0.95,
        z_spread_avg=0.0,
        n_observations=1000,
    )
    assert out["score"] > 4.5


def test_P7_dual_frame_disagreement_lowers_score() -> None:
    """Frames diverge heavily -> frame_coherence approx 0 -> score drops."""
    base_kw = dict(
        cross_variant_agreement_long_run=0.95,
        cross_variant_agreement_current_regime=0.95,
        n_observations=1000,
    )
    high = dual_frame_conviction(
        long_run_mean_z=3.0,
        current_regime_mean_z=3.0,
        z_spread_avg=0.0,
        **base_kw,
    )
    low = dual_frame_conviction(
        long_run_mean_z=3.0,
        current_regime_mean_z=3.0,
        z_spread_avg=3.0,
        **base_kw,
    )
    assert low["score"] < high["score"]
    # frame_coherence should be near zero when z_spread_avg ~ 3 (out of 4 max).
    assert low["components"]["frame_coherence"] == pytest.approx(0.25, abs=1e-9)


def test_P8_weights_sum_to_one() -> None:
    out = dual_frame_conviction(
        long_run_mean_z=0.0,
        current_regime_mean_z=0.0,
        cross_variant_agreement_long_run=0.0,
        cross_variant_agreement_current_regime=0.0,
        z_spread_avg=0.0,
        n_observations=0,
    )
    w = out["weights"]
    assert sum(w.values()) == pytest.approx(1.0)
    # All components zero -> raw = w["frame_coherence"] * 1 = 0.20 -> score = 1.8
    assert out["score"] == pytest.approx(1.0 + 4.0 * w["frame_coherence"])


def test_P9_custom_weights_override_default() -> None:
    custom = {
        "long_run_magnitude": 0.50,
        "current_regime_magnitude": 0.10,
        "cross_variant_agreement_long_run": 0.10,
        "cross_variant_agreement_current_regime": 0.10,
        "frame_coherence": 0.10,
        "sample_size": 0.10,
    }
    out = dual_frame_conviction(
        long_run_mean_z=3.0,
        current_regime_mean_z=0.0,
        cross_variant_agreement_long_run=1.0,
        cross_variant_agreement_current_regime=1.0,
        z_spread_avg=4.0,
        n_observations=1000,
        weights=custom,
    )
    assert out["weights"] == custom
    # Mismatched weights should still raise on bad sum.
    bad = dict(custom)
    bad["sample_size"] = 0.5  # sum > 1.0
    with pytest.raises(AssertionError):
        dual_frame_conviction(
            long_run_mean_z=0.0,
            current_regime_mean_z=0.0,
            cross_variant_agreement_long_run=0.0,
            cross_variant_agreement_current_regime=0.0,
            z_spread_avg=0.0,
            n_observations=0,
            weights=bad,
        )
