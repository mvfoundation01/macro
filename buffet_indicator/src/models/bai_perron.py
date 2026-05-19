"""Pure-NumPy Bai-Perron multiple-structural-break estimation.

Reference: Bai & Perron, "Computation and Analysis of Multiple Structural
Change Models" (J. Applied Econometrics, 2003). Implements the dynamic-
programming algorithm of section 3.3 with BIC (or LWZ) selection.

No external dependencies beyond NumPy + pandas; specifically does NOT require
the ``ruptures`` package (which fails to wheel-build on Python 3.14).
"""
from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Pre-compute: per-segment SSR matrix
# ---------------------------------------------------------------------------


def _compute_ssr_matrix(y: np.ndarray, T: int, min_seg: int) -> np.ndarray:
    """SSR[i, j] = OLS SSR of y[i:j+1] regressed on [1, t].

    Uses online recursive least squares so the full matrix is O(T^2) time and
    memory. Short segments (length < ``min_seg``) and the strict diagonal are
    left at +inf so the DP automatically rejects them.
    """
    SSR = np.full((T, T), np.inf, dtype=np.float64)
    for i in range(T):
        n = 0
        sum_x = 0.0
        sum_y = 0.0
        sum_xx = 0.0
        sum_xy = 0.0
        sum_yy = 0.0
        for j in range(i, T):
            n += 1
            x = float(j - i + 1)  # 1-indexed time within segment
            yj = float(y[j])
            sum_x += x
            sum_y += yj
            sum_xx += x * x
            sum_xy += x * yj
            sum_yy += yj * yj
            if n >= max(2, min_seg):
                denom = n * sum_xx - sum_x * sum_x
                if denom > 1e-12:
                    beta = (n * sum_xy - sum_x * sum_y) / denom
                    alpha = (sum_y - beta * sum_x) / n
                    ssr = sum_yy - alpha * sum_y - beta * sum_xy
                    SSR[i, j] = max(ssr, 0.0)
                else:
                    # Degenerate: all x identical (impossible for n>=2 in this setup).
                    SSR[i, j] = sum_yy - (sum_y * sum_y) / n
    return SSR


# ---------------------------------------------------------------------------
# DP over number of breaks
# ---------------------------------------------------------------------------


def _dp_breaks(
    SSR: np.ndarray, T: int, max_breaks: int, min_seg: int
) -> tuple[np.ndarray, np.ndarray]:
    """Dynamic programming over the number of breaks and their placements.

    Returns
    -------
    V  : shape ``(max_breaks+1, T)`` -- min total SSR using exactly ``m`` breaks
         and ending at index ``t``. ``+inf`` for infeasible (m, t).
    BT : shape ``(max_breaks+1, T)`` -- backtrack: for the (m, t) optimum, the
         index ``s`` such that breaks are ``[..., s]`` and the last segment is
         ``s+1 .. t``. ``-1`` if infeasible.
    """
    V = np.full((max_breaks + 1, T), np.inf, dtype=np.float64)
    BT = np.full((max_breaks + 1, T), -1, dtype=np.int64)

    # m = 0: single segment 0..t.
    V[0, :] = SSR[0, :]

    for m in range(1, max_breaks + 1):
        # ``t`` must accommodate (m+1) segments each at least min_seg long.
        t_lo = (m + 1) * min_seg - 1
        for t in range(t_lo, T):
            s_lo = m * min_seg - 1
            s_hi = t - min_seg
            if s_lo > s_hi:
                continue
            best = np.inf
            best_s = -1
            for s in range(s_lo, s_hi + 1):
                cand = V[m - 1, s] + SSR[s + 1, t]
                if cand < best:
                    best = cand
                    best_s = s
            V[m, t] = best
            BT[m, t] = best_s

    return V, BT


def _backtrack_breaks(BT: np.ndarray, m: int, T: int) -> list[int]:
    """Recover break indices for the m-break optimum (last index of each segment)."""
    if m == 0:
        return []
    breaks: list[int] = []
    t = T - 1
    for k in range(m, 0, -1):
        s = int(BT[k, t])
        if s < 0:
            # Infeasible; treat as fewer breaks.
            break
        breaks.append(s)
        t = s
    return sorted(breaks)


# ---------------------------------------------------------------------------
# Criterion (BIC or LWZ)
# ---------------------------------------------------------------------------


def _criterion(ssr: float, T: int, m: int, criterion: str) -> float:
    """Selection criterion. Lower is better."""
    if ssr <= 0 or T <= 0:
        return np.inf
    n_params = 3 * m + 2  # 2 OLS params per segment * (m+1) segments + m break dates
    if criterion == "bic":
        return T * np.log(ssr / T) + n_params * np.log(T)
    if criterion == "lwz":
        # Liu, Wu & Zidek (1997) modified BIC for segmented regression.
        c0 = 0.299
        return T * np.log(ssr / T) + c0 * n_params * (np.log(T)) ** 2.1
    raise ValueError(f"Unknown criterion: {criterion!r}")


# ---------------------------------------------------------------------------
# Per-segment OLS fit
# ---------------------------------------------------------------------------


def _segment_fit(
    y: np.ndarray, start: int, end_inclusive: int
) -> tuple[float, float, float, np.ndarray]:
    """Fit OLS on a single segment. Returns (alpha, beta, ssr, fitted)."""
    n = end_inclusive - start + 1
    x = np.arange(1, n + 1, dtype=np.float64)
    yv = y[start : end_inclusive + 1].astype(np.float64)
    sum_x = float(x.sum())
    sum_y = float(yv.sum())
    sum_xx = float((x * x).sum())
    sum_xy = float((x * yv).sum())
    sum_yy = float((yv * yv).sum())
    denom = n * sum_xx - sum_x * sum_x
    if denom > 1e-12:
        beta = (n * sum_xy - sum_x * sum_y) / denom
        alpha = (sum_y - beta * sum_x) / n
    else:
        # Degenerate (n=1 or identical x); use mean as intercept, beta=0.
        beta = 0.0
        alpha = sum_y / n if n > 0 else 0.0
    fitted = alpha + beta * x
    ssr = float(((yv - fitted) ** 2).sum())
    return alpha, beta, ssr, fitted


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def bai_perron(
    y: pd.Series,
    *,
    max_breaks: int = 5,
    min_segment_size: int | None = None,
    criterion: Literal["bic", "lwz"] = "bic",
) -> dict[str, Any]:
    """Bai-Perron multiple-structural-break estimation (pure NumPy DP).

    Models the series as piecewise-linear in time within each of ``m+1`` segments
    separated by ``m`` unknown break dates: ``y_t = alpha_j + beta_j * t + eps_t``
    for ``t`` in segment ``j``. Selects ``m`` by minimizing the chosen criterion
    over ``{0, 1, ..., max_breaks}``.

    Parameters
    ----------
    y : pd.Series
        Target series. Typically ``log(BI_t)``. NaN entries are dropped before
        fitting.
    max_breaks : int
        Upper bound on number of breaks considered.
    min_segment_size : int | None
        Minimum observations per segment. Defaults to ``max(60, int(0.15 * T))``.
        Bai-Perron (2003) recommend 15%% of sample.
    criterion : {"bic", "lwz"}
        ``"bic"`` is standard BIC; ``"lwz"`` is the Liu-Wu-Zidek modification,
        more conservative (penalizes breaks more).

    Returns a dict with keys:
        ``m_optimal``, ``break_dates``, ``break_indices``, ``segments``,
        ``fitted``, ``residuals``, ``criterion_values``, ``method``.
    """
    if not isinstance(y, pd.Series):
        raise TypeError("y must be a pandas Series")

    y_clean = y.dropna()
    T = len(y_clean)
    if T == 0:
        raise ValueError("bai_perron: series is empty after dropna")

    if min_segment_size is None:
        min_segment_size = max(60, int(0.15 * T))
    min_seg = int(min_segment_size)
    if min_seg < 2:
        raise ValueError(f"min_segment_size must be >= 2 (got {min_seg})")
    if T < 2 * min_seg:
        raise ValueError(
            f"bai_perron: series too short for min_segment_size={min_seg}; "
            f"need T >= {2 * min_seg}, got T={T}"
        )

    y_np = y_clean.to_numpy(dtype=np.float64)

    SSR = _compute_ssr_matrix(y_np, T, min_seg)
    V, BT = _dp_breaks(SSR, T, max_breaks, min_seg)

    # Score each candidate m by criterion on the total in-sample SSR.
    criterion_values: dict[int, float] = {}
    breaks_by_m: dict[int, list[int]] = {}
    for m in range(max_breaks + 1):
        ssr_m = float(V[m, T - 1])
        if not np.isfinite(ssr_m):
            criterion_values[m] = np.inf
            breaks_by_m[m] = []
            continue
        criterion_values[m] = _criterion(ssr_m, T, m, criterion)
        breaks_by_m[m] = _backtrack_breaks(BT, m, T)

    m_optimal = int(min(criterion_values, key=lambda k: criterion_values[k]))
    breaks = breaks_by_m[m_optimal]

    # Build segments: each (start, end_inclusive).
    boundaries = [-1] + breaks + [T - 1]
    segments: list[dict[str, Any]] = []
    fitted_np = np.empty(T, dtype=np.float64)
    for k in range(len(boundaries) - 1):
        seg_start = boundaries[k] + 1
        seg_end = boundaries[k + 1]
        alpha, beta, ssr_seg, fitted_seg = _segment_fit(y_np, seg_start, seg_end)
        fitted_np[seg_start : seg_end + 1] = fitted_seg
        segments.append(
            {
                "start": y_clean.index[seg_start],
                "end": y_clean.index[seg_end],
                "alpha": float(alpha),
                "beta": float(beta),
                "n": int(seg_end - seg_start + 1),
                "ssr": float(ssr_seg),
            }
        )

    fitted = pd.Series(fitted_np, index=y_clean.index, name="trend")
    residuals = pd.Series(
        y_np - fitted_np, index=y_clean.index, name="resid"
    )

    break_dates = [y_clean.index[i] for i in breaks]

    return {
        "m_optimal": m_optimal,
        "break_dates": break_dates,
        "break_indices": list(breaks),
        "segments": segments,
        "fitted": fitted,
        "residuals": residuals,
        "criterion_values": criterion_values,
        "method": f"bai_perron_{criterion}",
    }


__all__ = ["bai_perron"]
