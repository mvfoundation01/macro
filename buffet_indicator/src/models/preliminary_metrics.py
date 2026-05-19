"""Cross-variant agreement and PRELIMINARY conviction score.

Full conviction (Master Spec section 6.3) needs HAC t-stat, OOS R^2 and
historical hit rate from forward-return regressions, all of which come in
Spec v5. This module ships only the partial form.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from src.models.regime import classify


def cross_variant_agreement(variant_zs: dict[str, float]) -> dict[str, Any]:
    """Measure how well the 3 BI variants agree on the current z-score."""
    zs = np.array(list(variant_zs.values()), dtype="float64")
    mean_z = float(np.nanmean(zs))
    std_z = float(np.nanstd(zs, ddof=1)) if zs.size > 1 else 0.0
    agreement = float(max(0.0, 1.0 - std_z / max(abs(mean_z), 1.0)))
    same_sign = bool(np.all(zs > 0) or np.all(zs < 0))
    regimes = [classify(z)[0] for z in zs]
    same_regime = bool(len(set(regimes)) == 1)
    combined_regime = classify(mean_z)[0]
    return {
        "mean_z": mean_z,
        "std_z": std_z,
        "agreement": agreement,
        "same_sign": same_sign,
        "same_regime": same_regime,
        "combined_regime": combined_regime,
    }


def preliminary_conviction(
    mean_z: float,
    agreement: float,
    n_observations: int,
    *,
    w_magnitude: float = 0.30,
    w_agreement: float = 0.40,
    w_sample: float = 0.30,
) -> dict[str, Any]:
    """PARTIAL conviction per Master Spec section 6.3.

    Includes magnitude (|z|), cross-variant agreement, sample size. Missing
    pieces (HAC t-stat, OOS R^2, historical hit rate) require forward-return
    regressions and arrive in Spec v5. Scale: [1.0, 5.0].
    """
    assert abs((w_magnitude + w_agreement + w_sample) - 1.0) < 1e-9, "weights must sum to 1.0"

    c_mag = min(abs(mean_z) / 3.0, 1.0)
    c_agree = max(0.0, min(agreement, 1.0))
    c_sample = min(n_observations / 100.0, 1.0)
    raw = w_magnitude * c_mag + w_agreement * c_agree + w_sample * c_sample
    score = 1.0 + 4.0 * raw  # [0,1] -> [1,5]
    return {
        "score": float(score),
        "components": {
            "magnitude": c_mag,
            "agreement": c_agree,
            "sample_size": c_sample,
        },
        "weights": {
            "magnitude": w_magnitude,
            "agreement": w_agreement,
            "sample_size": w_sample,
        },
        "note": (
            "Preliminary -- partial of section 6.3. Full version (HAC t-stat, "
            "OOS R^2, hit rate) requires Spec v5."
        ),
    }


def dual_frame_conviction(
    *,
    long_run_mean_z: float,
    current_regime_mean_z: float,
    cross_variant_agreement_long_run: float,
    cross_variant_agreement_current_regime: float,
    z_spread_avg: float,
    n_observations: int,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Preliminary conviction with dual-frame awareness (Spec v4.2).

    Components (all clipped to [0, 1]):
      - long_run_magnitude        = min(|z_lr| / 3, 1)
      - current_regime_magnitude  = min(|z_cr| / 3, 1)
      - cross_variant_agreement_long_run        in [0, 1]
      - cross_variant_agreement_current_regime  in [0, 1]
      - frame_coherence           = max(0, 1 - z_spread_avg / 4)
      - sample_size               = min(n / 100, 1)

    Default weights (sum to 1.00):
        long_run_magnitude       0.20
        current_regime_magnitude 0.20
        xv_agreement_lr          0.15
        xv_agreement_cr          0.15
        frame_coherence          0.20
        sample_size              0.10

    Score = 1 + 4 * weighted_sum -> [1, 5].

    A ``BUBBLE_OR_SHIFT`` situation gets a moderate score because
    ``frame_coherence`` and ``current_regime_magnitude`` pull down even when
    ``long_run_magnitude`` and the cross-variant agreements are high. This is
    the intended behavior: when the two frames disagree, conviction in the
    final regime call SHOULD be lower.
    """
    default_w: dict[str, float] = {
        "long_run_magnitude": 0.20,
        "current_regime_magnitude": 0.20,
        "cross_variant_agreement_long_run": 0.15,
        "cross_variant_agreement_current_regime": 0.15,
        "frame_coherence": 0.20,
        "sample_size": 0.10,
    }
    w = dict(default_w) if weights is None else dict(weights)
    total_w = sum(w.values())
    assert abs(total_w - 1.0) < 1e-9, f"weights must sum to 1.0 (got {total_w})"

    c_lr = min(abs(long_run_mean_z) / 3.0, 1.0)
    c_cr = min(abs(current_regime_mean_z) / 3.0, 1.0)
    c_xv_lr = max(0.0, min(cross_variant_agreement_long_run, 1.0))
    c_xv_cr = max(0.0, min(cross_variant_agreement_current_regime, 1.0))
    c_coh = max(0.0, 1.0 - max(0.0, z_spread_avg) / 4.0)
    c_n = min(n_observations / 100.0, 1.0)

    components: dict[str, float] = {
        "long_run_magnitude": c_lr,
        "current_regime_magnitude": c_cr,
        "cross_variant_agreement_long_run": c_xv_lr,
        "cross_variant_agreement_current_regime": c_xv_cr,
        "frame_coherence": c_coh,
        "sample_size": c_n,
    }
    raw = sum(w[k] * components[k] for k in components)
    score = 1.0 + 4.0 * raw  # [0,1] -> [1,5]

    return {
        "score": float(score),
        "components": components,
        "weights": w,
        "note": (
            "Preliminary -- partial of section 6.3. Full version (HAC t-stat, "
            "OOS R^2, hit rate) requires Spec v5."
        ),
    }


__all__ = [
    "cross_variant_agreement",
    "preliminary_conviction",
    "dual_frame_conviction",
]
