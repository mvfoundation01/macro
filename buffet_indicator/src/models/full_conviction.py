"""Master Spec section 6.3 'full' conviction score.

Replaces v4's preliminary / dual-frame conviction once forward-return
regressions are available (Spec v5). Components:

    magnitude    = min(|z| / 3, 1)
    agreement    = clip(cross_variant_agreement, [0, 1])
    significance = clip(|t_hac| / 4, [0, 1])         # |t| of 4 -> max
    oos_r2       = clip(R^2_OOS * 5, [0, 1])         # 20% OOS -> max
    hit_rate     = clip(hit_rate, [0, 1])

Default weights (Master Spec section 6.3):
    {magnitude: 0.25, agreement: 0.20, significance: 0.20,
     oos_r2: 0.15, hit_rate: 0.20}

``Score = 1 + 4 * weighted_sum - frame_disagreement_penalty``, clipped to
``[1, 5]``.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


DEFAULT_WEIGHTS: dict[str, float] = {
    "magnitude": 0.25,
    "agreement": 0.20,
    "significance": 0.20,
    "oos_r2": 0.15,
    "hit_rate": 0.20,
}


def full_conviction(
    *,
    abs_z: float,
    cross_variant_agreement: float,
    t_hac: float,
    r2_oos: float,
    hit_rate: float,
    weights: dict[str, float] | None = None,
    frame_disagreement_penalty: float = 0.0,
) -> dict[str, Any]:
    """Spec v5 / Master Spec section 6.3 conviction score."""
    if weights is None:
        weights = dict(DEFAULT_WEIGHTS)
    else:
        weights = dict(weights)
    total = sum(weights.values())
    assert abs(total - 1.0) < 1e-9, f"weights must sum to 1.0 (got {total})"

    c_mag = float(min(abs(abs_z) / 3.0, 1.0))
    c_agr = float(max(0.0, min(cross_variant_agreement, 1.0)))
    if np.isnan(t_hac):
        c_sig = 0.0
    else:
        c_sig = float(max(0.0, min(abs(t_hac) / 4.0, 1.0)))
    if np.isnan(r2_oos):
        c_r2 = 0.0
    else:
        c_r2 = float(max(0.0, min(r2_oos * 5.0, 1.0)))
    if np.isnan(hit_rate):
        c_hit = 0.0
    else:
        c_hit = float(max(0.0, min(hit_rate, 1.0)))

    components = {
        "magnitude": c_mag,
        "agreement": c_agr,
        "significance": c_sig,
        "oos_r2": c_r2,
        "hit_rate": c_hit,
    }
    raw = sum(weights[k] * components[k] for k in components)
    score = 1.0 + 4.0 * raw - float(frame_disagreement_penalty)
    score = float(max(1.0, min(5.0, score)))
    return {
        "score": score,
        "components": components,
        "weights": weights,
        "frame_disagreement_penalty": float(frame_disagreement_penalty),
    }


def historical_hit_rate(
    z_series: pd.Series,
    r_fwd: pd.Series,
    current_z: float,
    horizon_months: int,
    *,
    threshold_5pct: float = 0.05,
    threshold_7pct: float = 0.07,
    z_window: float = 0.5,
) -> dict[str, Any]:
    """Historical hit rate near the current z level.

    For overvalued (current_z > 0): fraction of past observations with z within
    +/- ``z_window`` of ``current_z`` whose subsequent ``horizon_months`` CAGR
    fell below ``threshold_5pct`` (the "overvalued -> bad return" hit).

    For undervalued (current_z < 0): fraction whose subsequent CAGR EXCEEDED
    ``threshold_7pct`` (the "undervalued -> good return" hit).
    """
    aligned = pd.concat([z_series, r_fwd], axis=1).dropna()
    aligned.columns = ["z", "r"]
    mask = (aligned["z"] >= current_z - z_window) & (
        aligned["z"] <= current_z + z_window
    )
    matches = aligned.loc[mask]
    n_matches = int(len(matches))
    if n_matches == 0:
        return {
            "hit_rate": float("nan"),
            "n_matches": 0,
            "direction": "none",
            "threshold": float("nan"),
        }
    if current_z >= 0:
        direction = "overvalued_to_low_return"
        threshold = threshold_5pct
        hit_rate = float((matches["r"] < threshold).mean())
    else:
        direction = "undervalued_to_high_return"
        threshold = threshold_7pct
        hit_rate = float((matches["r"] > threshold).mean())
    return {
        "hit_rate": hit_rate,
        "n_matches": n_matches,
        "direction": direction,
        "threshold": float(threshold),
    }


__all__ = ["full_conviction", "historical_hit_rate", "DEFAULT_WEIGHTS"]
