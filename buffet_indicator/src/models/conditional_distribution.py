"""Empirical conditional distribution of forward returns given z-bucket."""
from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd


def _bucket_stats(returns: np.ndarray, risk_free_rate: float = 0.043) -> dict[str, Any]:
    if returns.size == 0:
        return {
            "n": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "std": float("nan"),
            "q05": float("nan"),
            "q25": float("nan"),
            "q75": float("nan"),
            "q95": float("nan"),
            "p_neg": float("nan"),
            "p_below_5": float("nan"),
            "p_above_7": float("nan"),
            "p_below_rf": float("nan"),
        }
    arr = returns.astype("float64")
    qs = np.quantile(arr, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "median": float(qs[2]),
        "std": float(arr.std(ddof=1)) if arr.size > 1 else float("nan"),
        "q05": float(qs[0]),
        "q25": float(qs[1]),
        "q75": float(qs[3]),
        "q95": float(qs[4]),
        "p_neg": float((arr < 0).mean()),
        "p_below_5": float((arr < 0.05).mean()),
        "p_above_7": float((arr > 0.07).mean()),
        "p_below_rf": float((arr < risk_free_rate).mean()),
    }


def conditional_distribution(
    z: pd.Series,
    r_fwd: pd.Series,
    *,
    n_buckets: int = 5,
    method: Literal["quintile", "decile", "kde", "kernel_smooth"] = "quintile",
    min_obs_per_bucket: int = 20,
    risk_free_rate: float = 0.043,
) -> dict[str, Any]:
    """Empirical conditional distribution of ``r_fwd`` given the bucket of ``z``.

    Returns dict with bucket edges, per-bucket stats, the bucket containing
    the latest z observation, the raw returns in that bucket, and a low-n flag.
    """
    if method == "decile":
        n_buckets = 10
    aligned = pd.concat([z, r_fwd], axis=1).dropna()
    aligned.columns = ["z", "r"]
    if aligned.empty:
        return {
            "buckets": [],
            "bucket_stats": {},
            "current_bucket": None,
            "current_dist": [],
            "low_n_flag": True,
            "n_total": 0,
        }

    latest_idx = z.dropna().index.max()
    latest_z = float(z.loc[latest_idx]) if latest_idx in z.index else float("nan")

    try:
        cats, edges = pd.qcut(
            aligned["z"], q=n_buckets, retbins=True, duplicates="drop"
        )
    except ValueError:
        return {
            "buckets": [],
            "bucket_stats": {},
            "current_bucket": None,
            "current_dist": [],
            "low_n_flag": True,
            "n_total": int(len(aligned)),
        }
    edges_list = [float(e) for e in edges]
    actual_buckets = len(edges_list) - 1

    bucket_stats: dict[int, dict[str, Any]] = {}
    low_n_flag = False
    for b in range(actual_buckets):
        mask = cats.cat.codes == b
        bucket_returns = aligned.loc[mask, "r"].to_numpy(dtype="float64")
        stats = _bucket_stats(bucket_returns, risk_free_rate=risk_free_rate)
        bucket_stats[b] = stats
        if stats["n"] < min_obs_per_bucket:
            low_n_flag = True

    # Locate current bucket (clamp to last bucket if z is above the upper edge).
    current_bucket: int | None = None
    current_returns: np.ndarray = np.empty(0, dtype="float64")
    if not np.isnan(latest_z):
        for b in range(actual_buckets):
            lo = edges_list[b]
            hi = edges_list[b + 1]
            if (b == 0 and latest_z <= hi) or (lo < latest_z <= hi) or (b == actual_buckets - 1 and latest_z >= hi):
                current_bucket = b
                break
        if current_bucket is None:
            current_bucket = actual_buckets - 1 if latest_z > edges_list[-1] else 0
        mask = cats.cat.codes == current_bucket
        current_returns = aligned.loc[mask, "r"].to_numpy(dtype="float64")

    return {
        "buckets": edges_list,
        "n_buckets_actual": actual_buckets,
        "bucket_stats": bucket_stats,
        "current_bucket": int(current_bucket) if current_bucket is not None else None,
        "current_z": latest_z,
        "current_dist": current_returns.tolist(),
        "current_dist_stats": _bucket_stats(current_returns, risk_free_rate=risk_free_rate)
        if current_returns.size
        else None,
        "low_n_flag": bool(low_n_flag),
        "n_total": int(len(aligned)),
    }


__all__ = ["conditional_distribution"]
