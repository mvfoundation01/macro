"""v11.0.1 MRC v2 — 13-constituent macro-risk composite with 3 weighting variants.

Expansion from v11.0a/b/c (7 inputs) to 13 inputs:

  Macro (2):        yc_10y3m, yc_10y2y
  Credit raw (4):   cs_hy_master, cs_ig_master, cs_hy_bb, cs_hy_ccc
  Credit derived (6): spread_hy_ig, spread_ccc_bb, spread_hy_reach_for_yield,
                      spread_hy_treasury_traditional, spread_equity_credit_rp,
                      spread_hy_oas_3m_delta
  Sentiment (1):    margin_debt_growth

3 weighting variants (REPLACING the v11.0a inv_variance scheme — kept for
back-compat as v2_inv_variance):

  1. group_weighted (NEW default per master spec §11.0.1 §G.2):
       Macro group share = 25%, Credit group share = 50%, Sentiment = 25%.
       Within each group, constituents weighted equally.

  2. pca_pc1 (RE-FIT with 13 inputs):
       Same algorithm as v11.0a, but covariance matrix is now 13×13.

  3. hierarchical (NEW per master spec §G.2):
       Ward linkage on (1 − |corr|) over a 60-month rolling window,
       cut at k=3 clusters. Each cluster gets 1/3 weight; within-cluster
       equal weighting.

Acceptance gates (§G.3):
  corr(MVCI, MRC_v2) < 0.85 (relaxed from 0.80 for cross-domain Equity-Credit RP)
  corr(MRC_v11.0c_equal_weight, MRC_v2_group_weighted) ∈ [0.80, 0.97]
  PC1 variance share ≥ 0.40 (relaxed from 0.50, master spec note §G.4)
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.models.zscore import expanding_zscore


MRC_V2_CONSTITUENTS: tuple[str, ...] = (
    # Macro (2)
    "yc_10y3m", "yc_10y2y",
    # Credit raw (4)
    "cs_hy_master", "cs_ig_master", "cs_hy_bb", "cs_hy_ccc",
    # Credit derived (6)
    "spread_hy_ig", "spread_ccc_bb", "spread_hy_reach_for_yield",
    "spread_hy_treasury_traditional", "spread_equity_credit_rp",
    "spread_hy_oas_3m_delta",
    # Sentiment (1)
    "margin_debt_growth",
)

GROUP_ASSIGNMENT: dict[str, str] = {
    "yc_10y3m": "macro", "yc_10y2y": "macro",
    "cs_hy_master": "credit", "cs_ig_master": "credit",
    "cs_hy_bb": "credit", "cs_hy_ccc": "credit",
    "spread_hy_ig": "credit", "spread_ccc_bb": "credit",
    "spread_hy_reach_for_yield": "credit",
    "spread_hy_treasury_traditional": "credit",
    "spread_equity_credit_rp": "credit",
    "spread_hy_oas_3m_delta": "credit",
    "margin_debt_growth": "sentiment",
}

GROUP_SHARES = {"macro": 0.25, "credit": 0.50, "sentiment": 0.25}


def _load_constituent_z(key: str) -> pd.Series:
    """Load the canonical signal series for one constituent and Huber-z-score it."""
    from pathlib import Path
    pq = Path(f"outputs/charts/{key}_value_history.parquet")
    if not pq.exists():
        return pd.Series(dtype="float64")
    df = pd.read_parquet(pq).set_index("date")
    if "signal" not in df.columns:
        return pd.Series(dtype="float64")
    sig = df["signal"].astype("float64").dropna()
    z = expanding_zscore(sig, min_periods=60, scale_method="huber")
    z.name = key
    return z.dropna()


def build_z_panel() -> pd.DataFrame:
    """Build the 13-column z-panel."""
    cols: dict[str, pd.Series] = {}
    for key in MRC_V2_CONSTITUENTS:
        z = _load_constituent_z(key)
        if not z.empty:
            cols[key] = z
    if not cols:
        return pd.DataFrame()
    return pd.concat(cols.values(), axis=1).sort_index()


def group_weighted_mrc(z_panel: pd.DataFrame) -> dict[str, Any]:
    """Variant 1: group-weighted equal-weight (new v11.0.1 default).

    Each constituent's contribution = GROUP_SHARES[group] * (1 / n_in_group)
    where n_in_group is the count of THAT group's members present in z_panel.
    """
    present = list(z_panel.columns)
    if not present:
        return {"scheme": "group_weighted", "z_score_series": pd.Series(dtype="float64"),
                "z_score": float("nan"), "weights_current": {}, "n_constituents": 0}
    # Tally present per group.
    by_group: dict[str, list[str]] = {"macro": [], "credit": [], "sentiment": []}
    for k in present:
        g = GROUP_ASSIGNMENT.get(k, "credit")
        by_group[g].append(k)
    weights = {}
    for g, members in by_group.items():
        if not members:
            continue
        share = GROUP_SHARES[g] / len(members)
        for m in members:
            weights[m] = share
    # Renormalise (handles missing groups gracefully).
    total_w = sum(weights.values())
    if total_w > 0:
        weights = {k: w / total_w for k, w in weights.items()}
    arr = z_panel.to_numpy(dtype="float64")
    w_arr = np.array([weights[c] for c in present])
    composite = np.zeros(len(z_panel))
    for i in range(len(z_panel)):
        row = arr[i]
        mask = ~np.isnan(row)
        if not mask.any():
            composite[i] = np.nan
            continue
        w_eff = np.where(mask, w_arr, 0.0)
        denom = float(w_eff.sum())
        if denom <= 0:
            composite[i] = np.nan
        else:
            composite[i] = float(np.nansum(w_eff * row) / denom)
    series = pd.Series(composite, index=z_panel.index, name="mrc_v2_group_weighted")
    return {
        "scheme": "group_weighted",
        "z_score_series": series,
        "z_score": float(series.dropna().iloc[-1]) if not series.dropna().empty else float("nan"),
        "weights_current": weights,
        "n_constituents": len(present),
        "group_shares": dict(GROUP_SHARES),
        "group_membership": {g: tuple(m) for g, m in by_group.items()},
    }


def pca_pc1_mrc_v2(z_panel: pd.DataFrame, *, min_periods: int = 60) -> dict[str, Any]:
    """Variant 2: PCA-PC1 re-fit on 13-column panel."""
    from src.transform.mvci_compute import pca_pc1_mvci
    z_aligned = z_panel.dropna(how="all")
    if z_aligned.empty:
        return {"scheme": "pca_pc1", "z_score_series": pd.Series(dtype="float64"),
                "z_score": float("nan"), "weights_current": {}, "n_constituents": 0}
    return pca_pc1_mvci(z_aligned, min_periods=min_periods)


def hierarchical_mrc(
    z_panel: pd.DataFrame, *, window: int = 60, k_clusters: int = 3
) -> dict[str, Any]:
    """Variant 3: Ward-linkage hierarchical clustering with 1 - |corr| distance.

    1. Compute Pearson correlation over the last ``window`` months.
    2. Build distance matrix d = 1 − |corr|.
    3. Ward linkage; cut at k clusters.
    4. Each cluster gets 1/k weight; equal weights within.
    """
    from scipy.cluster.hierarchy import fcluster, linkage  # type: ignore
    from scipy.spatial.distance import squareform  # type: ignore

    tail = z_panel.dropna(how="all").tail(window)
    if tail.shape[0] < window // 2 or tail.shape[1] < 3:
        return {"scheme": "hierarchical", "z_score_series": pd.Series(dtype="float64"),
                "z_score": float("nan"), "weights_current": {}, "n_constituents": 0,
                "clusters": {}}
    corr = tail.corr().fillna(0.0).values
    dist = 1 - np.abs(corr)
    # Make distance matrix symmetric (numerical) and zero diagonal.
    dist = (dist + dist.T) / 2.0
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    Z = linkage(condensed, method="ward")
    labels = fcluster(Z, t=k_clusters, criterion="maxclust")
    clusters: dict[int, list[str]] = {}
    for i, c in enumerate(labels):
        clusters.setdefault(int(c), []).append(z_panel.columns[i])
    # Each cluster gets 1/k weight; within-cluster equal share.
    cluster_share = 1.0 / max(len(clusters), 1)
    weights: dict[str, float] = {}
    for c, members in clusters.items():
        share = cluster_share / len(members) if members else 0.0
        for m in members:
            weights[m] = share
    total = sum(weights.values())
    if total > 0:
        weights = {k: w / total for k, w in weights.items()}
    arr = z_panel.to_numpy(dtype="float64")
    w_arr = np.array([weights[c] for c in z_panel.columns])
    composite = np.zeros(len(z_panel))
    for i in range(len(z_panel)):
        row = arr[i]
        mask = ~np.isnan(row)
        if not mask.any():
            composite[i] = np.nan
            continue
        w_eff = np.where(mask, w_arr, 0.0)
        denom = float(w_eff.sum())
        composite[i] = (
            float(np.nansum(w_eff * row) / denom) if denom > 0 else np.nan
        )
    series = pd.Series(composite, index=z_panel.index, name="mrc_v2_hierarchical")
    return {
        "scheme": "hierarchical",
        "z_score_series": series,
        "z_score": float(series.dropna().iloc[-1]) if not series.dropna().empty else float("nan"),
        "weights_current": weights,
        "n_constituents": len(weights),
        "clusters": {int(c): list(m) for c, m in clusters.items()},
    }


def compute_mrc_v2() -> dict[str, Any]:
    """Run all 3 weighting variants on the 13-column z-panel."""
    z_panel = build_z_panel()
    if z_panel.empty:
        return {"constituents": [], "z_panel": z_panel, "schemes": {}}
    z_aligned = z_panel.dropna(how="all")
    return {
        "constituents": list(z_aligned.columns),
        "z_panel": z_aligned,
        "schemes": {
            "group_weighted": group_weighted_mrc(z_aligned),
            "pca_pc1": pca_pc1_mrc_v2(z_aligned),
            "hierarchical": hierarchical_mrc(z_aligned),
        },
    }


__all__ = [
    "MRC_V2_CONSTITUENTS",
    "GROUP_ASSIGNMENT",
    "GROUP_SHARES",
    "compute_mrc_v2",
    "build_z_panel",
    "group_weighted_mrc",
    "pca_pc1_mrc_v2",
    "hierarchical_mrc",
]
