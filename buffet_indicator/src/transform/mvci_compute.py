"""MV Composite Index (MVCI): aggregate constituent z-scores into one signal.

Three weighting schemes, all per-frame (long_run and current_regime computed
separately):

    equal_weight     : MVCI_t = mean(z_i,t)
    inv_variance     : MVCI_t = sum(w_i * z_i,t),  w_i ~ 1/Var_expanding(z_i)
    pca_pc1          : MVCI_t = sum(loadings_t[i] * z_i,t), first PC normalized

PCA loadings are recomputed monthly on expanding windows (min 60 obs) to
avoid look-ahead. Sign is fixed so the first PC is positive (matching the
HIGH-OV convention of all constituent z-scores).
"""
from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd


Scheme = Literal["equal_weight", "inv_variance", "pca_pc1"]


def _equal_weight_series(z_panel: pd.DataFrame) -> pd.DataFrame:
    """Each row is the equal-weight mean across constituents."""
    return pd.DataFrame(
        {
            "mvci": z_panel.mean(axis=1).astype("float64"),
        }
    )


def equal_weight_mvci(z_panel: pd.DataFrame) -> dict[str, Any]:
    """Equal-weight average across constituents.

    Returns dict with ``z_score_series``, ``z_score`` (latest), ``weights_current``,
    ``n_constituents``, ``scheme``.
    """
    if z_panel.empty or z_panel.shape[1] == 0:
        raise ValueError("equal_weight_mvci: panel is empty")
    n = z_panel.shape[1]
    weight = 1.0 / n
    series = z_panel.mean(axis=1).astype("float64")
    series.name = "mvci_equal_weight"
    weights = {c: weight for c in z_panel.columns}
    return {
        "scheme": "equal_weight",
        "z_score_series": series,
        "z_score": float(series.dropna().iloc[-1]) if not series.dropna().empty else float("nan"),
        "weights_current": weights,
        "n_constituents": int(n),
        "explained_variance": None,
    }


def inv_variance_mvci(
    z_panel: pd.DataFrame, *, min_periods: int = 60
) -> dict[str, Any]:
    """Inverse-variance-weighted MVCI with expanding-window variance estimates."""
    if z_panel.empty:
        raise ValueError("inv_variance_mvci: panel is empty")
    n_constituents = z_panel.shape[1]
    out_idx = z_panel.index
    out_vals = np.full(len(out_idx), np.nan)
    weights_path: dict[str, list[float]] = {c: [] for c in z_panel.columns}

    arr = z_panel.to_numpy(dtype="float64")
    for i in range(len(out_idx)):
        if i + 1 < min_periods:
            for c in z_panel.columns:
                weights_path[c].append(np.nan)
            continue
        window = arr[: i + 1]
        if np.isnan(window).any(axis=0).all():
            for c in z_panel.columns:
                weights_path[c].append(np.nan)
            continue
        var = np.nanvar(window, axis=0, ddof=1)
        var = np.where(var <= 0, np.nan, var)
        inv = 1.0 / var
        if np.isnan(inv).all():
            for c in z_panel.columns:
                weights_path[c].append(np.nan)
            continue
        inv_sum = np.nansum(inv)
        if inv_sum <= 0:
            for c in z_panel.columns:
                weights_path[c].append(np.nan)
            continue
        weights = inv / inv_sum
        latest = arr[i]
        # Use 0 weight where the latest value is NaN; renormalize.
        mask = ~np.isnan(latest) & ~np.isnan(weights)
        if not mask.any():
            for c in z_panel.columns:
                weights_path[c].append(np.nan)
            continue
        w_eff = np.where(mask, weights, 0.0)
        w_eff = w_eff / w_eff.sum()
        out_vals[i] = float(np.nansum(w_eff * latest))
        for j, c in enumerate(z_panel.columns):
            weights_path[c].append(float(w_eff[j]))

    series = pd.Series(out_vals, index=out_idx, name="mvci_inv_variance")
    weights_df = pd.DataFrame(weights_path, index=out_idx)
    last_weights = weights_df.dropna().iloc[-1] if not weights_df.dropna().empty else pd.Series(dtype="float64")
    return {
        "scheme": "inv_variance",
        "z_score_series": series,
        "z_score": float(series.dropna().iloc[-1]) if not series.dropna().empty else float("nan"),
        "weights_current": {c: float(last_weights.get(c, np.nan)) for c in z_panel.columns},
        "weights_history": weights_df,
        "n_constituents": int(n_constituents),
        "explained_variance": None,
    }


def pca_pc1_mvci(
    z_panel: pd.DataFrame, *, min_periods: int = 60
) -> dict[str, Any]:
    """First-principal-component MVCI with expanding-window covariance."""
    if z_panel.empty:
        raise ValueError("pca_pc1_mvci: panel is empty")
    n_constituents = z_panel.shape[1]
    out_idx = z_panel.index
    out_vals = np.full(len(out_idx), np.nan)
    explained: list[float] = []
    weights_path: dict[str, list[float]] = {c: [] for c in z_panel.columns}

    arr = z_panel.to_numpy(dtype="float64")
    last_explained = np.nan
    # v8b.1 fix B.3: track the FULL PC1 loadings (before availability rebasing)
    # so the dashboard can display every variant's contribution to PC1, even
    # when the latest observation has NaN for some variants.
    last_full_loadings: dict[str, float] | None = None
    for i in range(len(out_idx)):
        if i + 1 < min_periods:
            for c in z_panel.columns:
                weights_path[c].append(np.nan)
            explained.append(np.nan)
            continue
        window = arr[: i + 1]
        # Drop rows with any NaN for the eigen-decomposition.
        valid_mask = ~np.isnan(window).any(axis=1)
        win = window[valid_mask]
        if win.shape[0] < min_periods or win.shape[0] < n_constituents:
            for c in z_panel.columns:
                weights_path[c].append(np.nan)
            explained.append(np.nan)
            continue
        # Center.
        centered = win - win.mean(axis=0)
        cov = np.cov(centered, rowvar=False)
        # Numerical guard: enforce symmetry.
        cov = (cov + cov.T) / 2.0
        try:
            eigvals, eigvecs = np.linalg.eigh(cov)
        except np.linalg.LinAlgError:
            for c in z_panel.columns:
                weights_path[c].append(np.nan)
            explained.append(np.nan)
            continue
        # Largest eigenvalue is last in eigh ordering.
        idx_max = int(np.argmax(eigvals))
        v1 = eigvecs[:, idx_max]
        # Sign fix: ensure overall positive (HIGH = OV convention).
        if np.sum(v1) < 0:
            v1 = -v1
        s = np.sum(v1)
        if abs(s) < 1e-12:
            loadings = np.full_like(v1, 1.0 / n_constituents)
        else:
            loadings = v1 / s
        # Capture the full balanced-panel loadings before any rebasing.
        last_full_loadings = {
            c: float(loadings[j]) for j, c in enumerate(z_panel.columns)
        }
        latest = arr[i]
        if np.isnan(latest).any():
            mask = ~np.isnan(latest)
            l_eff = np.where(mask, loadings, 0.0)
            denom = l_eff.sum()
            if abs(denom) < 1e-12:
                for c in z_panel.columns:
                    weights_path[c].append(np.nan)
                explained.append(np.nan)
                continue
            l_eff = l_eff / denom
            out_vals[i] = float(np.nansum(l_eff * latest))
            for j, c in enumerate(z_panel.columns):
                weights_path[c].append(float(l_eff[j]))
        else:
            out_vals[i] = float(np.dot(loadings, latest))
            for j, c in enumerate(z_panel.columns):
                weights_path[c].append(float(loadings[j]))
        total_var = float(eigvals.sum())
        if total_var > 0:
            last_explained = float(eigvals[idx_max] / total_var)
        explained.append(last_explained)

    series = pd.Series(out_vals, index=out_idx, name="mvci_pca_pc1")
    weights_df = pd.DataFrame(weights_path, index=out_idx)
    last_weights = weights_df.dropna().iloc[-1] if not weights_df.dropna().empty else pd.Series(dtype="float64")
    return {
        "scheme": "pca_pc1",
        "z_score_series": series,
        "z_score": float(series.dropna().iloc[-1]) if not series.dropna().empty else float("nan"),
        # v8b.1: weights_current = availability-rebased (renormalized over
        # currently-observed variants only); used internally for the actual
        # composite computation. loadings_full = raw PC1 loadings on the
        # balanced panel (no rebasing); used by the dashboard PCA loadings
        # chart so every constituent's contribution to PC1 is visible.
        "weights_current": {c: float(last_weights.get(c, np.nan)) for c in z_panel.columns},
        "loadings_full": last_full_loadings
        or {c: float("nan") for c in z_panel.columns},
        "weights_history": weights_df,
        "n_constituents": int(n_constituents),
        "explained_variance": float(last_explained) if np.isfinite(last_explained) else None,
    }


def compute_mvci_schemes(
    z_panel: pd.DataFrame, *, min_periods: int = 60
) -> dict[str, dict[str, Any]]:
    """Run all three schemes on the aligned constituent panel."""
    z_aligned = z_panel.dropna(how="all")
    return {
        "equal_weight": equal_weight_mvci(z_aligned),
        "inv_variance": inv_variance_mvci(z_aligned, min_periods=min_periods),
        "pca_pc1": pca_pc1_mvci(z_aligned, min_periods=min_periods),
    }


__all__ = [
    "equal_weight_mvci",
    "inv_variance_mvci",
    "pca_pc1_mvci",
    "compute_mvci_schemes",
]
