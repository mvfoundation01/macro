"""Stationary block bootstrap CI on the latest z-score (for confidence_pct).

confidence_pct calibration (Spec v4.1):
    relative_width  = ci_width / max(|point_estimate|, 1.0)
    confidence_pct  = 100.0 / (1.0 + relative_width)

Examples:
    |point|=2.0, width=0.0  -> rel=0.00, conf=100.0
    |point|=2.0, width=0.5  -> rel=0.25, conf= 80.0
    |point|=2.0, width=1.0  -> rel=0.50, conf= 66.7
    |point|=2.0, width=2.0  -> rel=1.00, conf= 50.0
    |point|=2.0, width=4.0  -> rel=2.00, conf= 33.3
    |point|=0.5, width=0.2  -> rel=0.40, conf= 71.4
    |point|=0.0, width=1.0  -> rel=1.00, conf= 50.0  (floor of 1.0 prevents blow-up)

Properties: bounded in (0, 100]; scale-invariant; smooth and monotone-
decreasing in ``ci_width`` for fixed point.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _confidence_pct(point_estimate: float, ci_width: float) -> float:
    """Smooth, scale-invariant confidence proxy in (0, 100]."""
    denom = max(abs(point_estimate), 1.0)
    relative_width = max(0.0, ci_width) / denom
    return float(100.0 / (1.0 + relative_width))


def _optimal_block_length(values: np.ndarray) -> int:
    """Return the optimal stationary-bootstrap block length (Politis-White)."""
    from arch.bootstrap import optimal_block_length

    bl_df = optimal_block_length(values)
    # ``optimal_block_length`` may return a DataFrame indexed by series or a Series.
    if isinstance(bl_df, pd.DataFrame):
        if "stationary" in bl_df.columns:
            stat_col = bl_df["stationary"]
        else:
            stat_col = bl_df.iloc[:, 0]
        bl = float(stat_col.iloc[0])
    elif isinstance(bl_df, pd.Series):
        bl = float(bl_df.iloc[0])
    else:
        bl = float(bl_df)
    return max(1, int(round(bl)))


def bootstrap_zscore_ci(
    residuals: pd.Series,
    n_replications: int = 10_000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> dict[str, Any]:
    """Bootstrap a CI on the LATEST z-score using stationary block bootstrap.

    Returns dict with: point_estimate, ci_lower, ci_upper, ci_width,
    n_replications, block_length, confidence_pct.

    ``confidence_pct`` is a 0-100 proxy: 100 * max(0, 1 - CI_width / 4).
    """
    from arch.bootstrap import StationaryBootstrap

    r = residuals.dropna().to_numpy(dtype="float64")
    if r.size < 5:
        raise ValueError("bootstrap_zscore_ci: need at least 5 residuals")

    bl = _optimal_block_length(r)
    bs = StationaryBootstrap(bl, r, seed=seed)

    def _stat(data: np.ndarray) -> float:
        sd = float(data.std(ddof=1))
        if sd == 0:
            return 0.0
        return float((data[-1] - data.mean()) / sd)

    samples = np.empty(n_replications, dtype="float64")
    for i, (pos_args, _kw) in enumerate(bs.bootstrap(n_replications)):
        samples[i] = _stat(pos_args[0])

    alpha = (1.0 - confidence_level) / 2.0
    lo, hi = np.quantile(samples, [alpha, 1.0 - alpha])
    point_sd = float(r.std(ddof=1))
    point = 0.0 if point_sd == 0 else float((r[-1] - r.mean()) / point_sd)

    width = float(hi - lo)
    confidence_pct = _confidence_pct(point, width)

    return {
        "point_estimate": point,
        "ci_lower": float(lo),
        "ci_upper": float(hi),
        "ci_width": width,
        "n_replications": int(n_replications),
        "block_length": int(bl),
        "confidence_pct": confidence_pct,
    }


__all__ = ["bootstrap_zscore_ci", "_confidence_pct"]
