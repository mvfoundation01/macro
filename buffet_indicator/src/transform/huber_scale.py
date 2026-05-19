"""Robust scale estimators (Huber M, MAD, std) for z-score computation.

Per Spec v5 section 2, the default scale for expanding/full-sample z-scores
is now the Huber M-estimator. Huber down-weights observations with |z| > c
during scale estimation, so a few large negative residuals (Depression,
GFC, COVID) no longer inflate sigma and compress the headline z-score.
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd


def robust_scale(
    x: np.ndarray | pd.Series,
    method: Literal["huber", "mad", "std"] = "huber",
    c: float = 1.345,
    maxiter: int = 50,
    tol: float = 1e-6,
) -> tuple[float, float]:
    """Return ``(location, scale)`` using the requested estimator.

    - ``"huber"``: Huber M-estimator. Iteratively reweighted location + scale.
    - ``"mad"``:   median + MAD = 1.4826 * median(|x - median|).
    - ``"std"``:   mean + sample std (ddof=1).

    Huber falls back to MAD if the iterative solver fails (small samples,
    perfectly constant data, etc.).
    """
    x_arr = pd.Series(np.asarray(x)).dropna().to_numpy()
    if x_arr.size == 0:
        return 0.0, 0.0

    if method == "huber":
        try:
            from statsmodels.robust.scale import Huber

            huber_est = Huber(c=c, maxiter=maxiter, tol=tol)
            loc, sc = huber_est(x_arr)
            loc_f, sc_f = float(loc), float(sc)
            if np.isfinite(loc_f) and np.isfinite(sc_f) and sc_f > 0:
                return loc_f, sc_f
        except Exception:  # noqa: BLE001
            pass
        method = "mad"

    if method == "mad":
        med = float(np.median(x_arr))
        sc = float(_mad(x_arr))
        if not np.isfinite(sc) or sc <= 0:
            sc = float(np.std(x_arr, ddof=1)) if x_arr.size > 1 else 0.0
        return med, sc

    return float(np.mean(x_arr)), float(np.std(x_arr, ddof=1)) if x_arr.size > 1 else 0.0


def _mad(x: np.ndarray) -> float:
    """Median absolute deviation, scaled to match Normal sigma at the limit."""
    if x.size == 0:
        return 0.0
    med = np.median(x)
    return 1.4826 * float(np.median(np.abs(x - med)))


__all__ = ["robust_scale"]
