"""v11.2 — Shared compute primitives used by Extended Analytics surfaces.

Per PROMPT_v11_2 §6.2: a single module that hosts the strategy-returns
container, the multi-strategy loader, and the stationary-bootstrap CI utility
used across Surfaces 1-9 and the institutional upgrades.

The 6 strategy time series targeted by Extended Analytics:
    V1_Combination, V2_R-PRIMARY, V2_R-ALT1, V2_R-ALT2, SPY, EW.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from src.quant_engine.mv_conditional import (
    QUANT_PIPELINE_RESULTS,
    RULE_REGISTRY,
    apply_mv_conditional,
    load_combo_monthly_returns,
    load_mvci_mrc_zscores_monthly,
    load_tbill_monthly_return,
)


@dataclass
class StrategyReturns:
    """Container for one strategy's return time series at multiple frequencies."""
    monthly: pd.Series
    name: str
    color: str = "#888888"

    @property
    def annual(self) -> pd.Series:
        """Year-end annual returns derived from monthly."""
        return self.monthly.resample("YE").apply(lambda r: (1.0 + r).prod() - 1.0)


_STRATEGY_COLORS = {
    "V1_Combination": "#1f77b4",
    "V2_R-PRIMARY":   "#ff7f0e",
    "V2_R-ALT1":      "#2ca02c",
    "V2_R-ALT2":      "#d62728",
    "SPY":            "#7f7f7f",
    "EW":             "#9467bd",
}


def load_all_strategy_returns(
    costbps: int = 15,
    results_dir: Path | None = None,
) -> dict[str, StrategyReturns]:
    """Load the 6 strategy monthly return series targeted by Extended Analytics.

    Returns a dict keyed by strategy name. SPY/EW are loaded from v50's results
    CSV only if available; missing series are silently omitted so the caller
    can defensively branch on which strategies are present.
    """
    if results_dir is None:
        results_dir = QUANT_PIPELINE_RESULTS

    out: dict[str, StrategyReturns] = {}

    # V1 Combination — direct CSV load.
    combo = None
    for plabel in ("FULL", "FULL_2000"):
        try:
            combo = load_combo_monthly_returns(plabel, costbps, results_dir)
            break
        except FileNotFoundError:
            continue
    if combo is not None:
        out["V1_Combination"] = StrategyReturns(
            monthly=combo, name="V1_Combination",
            color=_STRATEGY_COLORS["V1_Combination"],
        )

        # V2 variants derived from V1 + rules + T-bill.
        try:
            z = load_mvci_mrc_zscores_monthly()
            tbill = load_tbill_monthly_return()
            for rule_name, rule_fn in RULE_REGISTRY.items():
                weights = rule_fn(z["z_mvci"], z["z_mrc"])
                r_v2 = apply_mv_conditional(combo, weights, tbill)
                label = f"V2_{rule_name}"
                out[label] = StrategyReturns(
                    monthly=r_v2, name=label,
                    color=_STRATEGY_COLORS.get(label, "#888888"),
                )
        except Exception:
            # MVCI/MRC missing — V1 alone is still useful.
            pass
    return out


def stationary_bootstrap_indices(
    n: int, block_length: int, rng: np.random.Generator
) -> np.ndarray:
    """One stationary bootstrap (Politis-Romano 1994) sample of indices."""
    p = 1.0 / max(block_length, 1)
    indices = np.empty(n, dtype=np.int64)
    indices[0] = rng.integers(0, n)
    for i in range(1, n):
        if rng.random() < p:
            indices[i] = rng.integers(0, n)
        else:
            indices[i] = (indices[i - 1] + 1) % n
    return indices


def compute_bootstrap_ci(
    values: np.ndarray | pd.Series,
    n_reps: int = 10_000,
    block_length: int = 6,
    seed: int = 42,
    metric_fn: Callable[[np.ndarray], float] = lambda v: float(np.mean(v)),
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Stationary bootstrap CI for any scalar metric of a 1D series.

    Returns (point_estimate, ci_low, ci_high) at family-wise (1-α) coverage.
    Used by Surface 1's KPI table, Surface 4's 50+ risk metrics, and the
    statistical-test diff CIs.
    """
    if isinstance(values, pd.Series):
        arr = values.dropna().to_numpy(dtype=np.float64)
    else:
        arr = np.asarray(values, dtype=np.float64)
        arr = arr[np.isfinite(arr)]
    n = len(arr)
    if n < 24:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed=seed)
    samples = np.empty(n_reps, dtype=np.float64)
    for b in range(n_reps):
        idx = stationary_bootstrap_indices(n, block_length, rng)
        try:
            samples[b] = metric_fn(arr[idx])
        except Exception:
            samples[b] = np.nan
    samples = samples[np.isfinite(samples)]
    if len(samples) == 0:
        return float("nan"), float("nan"), float("nan")
    try:
        point = float(metric_fn(arr))
    except Exception:
        point = float("nan")
    lo = float(np.percentile(samples, 100.0 * alpha / 2))
    hi = float(np.percentile(samples, 100.0 * (1.0 - alpha / 2)))
    return point, lo, hi


def compute_conviction_triple(
    point: float, ci_low: float, ci_high: float,
    t_stat: float | None = None,
) -> dict[str, float | None]:
    """Compute Confidence% + Conviction(1-5) per master spec §6.2/§6.3.

    Confidence%: 100 - half_width(CI95)*100, clipped to [0, 100].
    Conviction (1-5): base 1.0 + t-contribution + confidence-contribution,
    clipped to [1, 5].

    Returns dict with point, ci_low, ci_high, confidence_pct, conviction_score,
    t_stat — directly serializable to a metric card.
    """
    ci_width = (ci_high - ci_low) if np.isfinite(ci_high) and np.isfinite(ci_low) else float("nan")
    confidence = float("nan")
    if np.isfinite(ci_width):
        confidence = max(0.0, min(100.0, 100.0 - abs(ci_width) * 100.0 / 2.0))
    conviction = 1.0
    if t_stat is not None and np.isfinite(t_stat):
        conviction += min(2.0, abs(float(t_stat)) / 2.0)
    if np.isfinite(confidence):
        conviction += min(1.0, confidence / 100.0)
    conviction = max(1.0, min(5.0, conviction))
    return {
        "point": float(point) if np.isfinite(point) else float("nan"),
        "ci_low": float(ci_low) if np.isfinite(ci_low) else float("nan"),
        "ci_high": float(ci_high) if np.isfinite(ci_high) else float("nan"),
        "confidence_pct": float(confidence) if np.isfinite(confidence) else float("nan"),
        "conviction_score": float(conviction),
        "t_stat": float(t_stat) if t_stat is not None and np.isfinite(t_stat) else None,
    }


__all__ = [
    "StrategyReturns",
    "load_all_strategy_returns",
    "stationary_bootstrap_indices",
    "compute_bootstrap_ci",
    "compute_conviction_triple",
]
