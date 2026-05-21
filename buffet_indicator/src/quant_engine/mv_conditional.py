"""v11.2 — MV-Conditional V2 backtest core.

This module implements the pre-registered MV-Conditional rule R-PRIMARY plus
two alternatives R-ALT1 and R-ALT2 (see specs/MV_CONDITIONAL_RULE_PREREGISTER.md).

Architecture (per PROMPT_v11_2 §3):

    load_mvci_mrc_zscores_monthly()
        → DataFrame[date → z_mvci, z_mrc]  (PIT)
    rule_r_primary / rule_r_alt1 / rule_r_alt2
        → Series[date → weight in V1 Combination]  (0.5 or 1.0; or continuous)
    apply_mv_conditional(combo_monthly_returns, weight_series, tbill_monthly)
        → V2 monthly return series

PIT discipline:
- ``compute_pit_zscore`` matches PROMPT_v11_2 §3.2 literally (uses
  ``series.shift(1)`` so that z at date t derives from observations through
  t-1 only).
- ``load_mvci_mrc_zscores_monthly`` returns the mvci_mrc_joint.parquet
  z-scores AS-IS; those are already expanding-window z-scores computed at
  each month-end using data through that month-end (no future leakage).
- ``apply_mv_conditional`` shifts the weight series by 1 month so that the
  weight chosen at end-of-month T-1 governs the return for month T.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
JOINT_PARQUET = REPO_ROOT / "outputs" / "cross_composite" / "mvci_mrc_joint.parquet"
QE_LATEST_DIR = REPO_ROOT / "outputs" / "quant_engine" / "latest"
QUANT_PIPELINE_RESULTS = REPO_ROOT.parent / "quant_pipeline" / "results"


def compute_pit_zscore(series: pd.Series, min_periods: int = 60) -> pd.Series:
    """Expanding-window z-score with ``.shift(1)`` PIT discipline.

    At date t, uses only observations available up to t-1 (month-end of
    prior month). Matches PROMPT_v11_2 §3.2 verbatim.

    Parameters
    ----------
    series : pd.Series
        Monthly time series (e.g., MVCI or MRC), indexed by month-end.
    min_periods : int
        Minimum observations before a z-score is emitted (default 60).
    """
    shifted = series.shift(1)
    mu = shifted.expanding(min_periods=min_periods).mean()
    sd = shifted.expanding(min_periods=min_periods).std()
    return (shifted - mu) / sd


def load_mvci_mrc_zscores_monthly(
    joint_path: Path | None = None,
) -> pd.DataFrame:
    """Load MVCI and MRC PIT z-scores from the cross-composite joint parquet.

    The joint parquet (``outputs/cross_composite/mvci_mrc_joint.parquet``) is
    produced by the v11.0 orchestrator with expanding-window z-scores at
    each month-end (no future leakage).

    Returns
    -------
    DataFrame indexed by month-end with columns ``z_mvci``, ``z_mrc``.
    """
    if joint_path is None:
        joint_path = JOINT_PARQUET
    if not joint_path.exists():
        raise FileNotFoundError(
            f"{joint_path} missing — run v11.0 orchestrator first."
        )
    df = pd.read_parquet(joint_path)
    if "date" not in df.columns:
        raise ValueError(f"{joint_path} missing 'date' column")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    out = pd.DataFrame(
        {
            "z_mvci": df["mvci_z"].astype("float64"),
            "z_mrc": df["mrc_z"].astype("float64"),
        }
    ).dropna(how="all")
    return out


def rule_r_primary(z_mvci: pd.Series, z_mrc: pd.Series) -> pd.Series:
    """R-PRIMARY (pre-registered): fire if MVCI > +1.5σ AND MRC > +0.5σ.

    Returns the weight series for V1 Combination (0.50 when fire, 1.00 otherwise).
    The complement weight goes to T-bills.
    """
    aligned = pd.concat([z_mvci, z_mrc], axis=1, keys=["mvci", "mrc"]).dropna()
    fire = (aligned["mvci"] > 1.5) & (aligned["mrc"] > 0.5)
    return pd.Series(np.where(fire, 0.5, 1.0), index=aligned.index, name="w_combination")


def rule_r_alt1(z_mvci: pd.Series, z_mrc: pd.Series | None = None) -> pd.Series:
    """R-ALT1 (alternative): fire if MVCI > +2.0σ alone (MRC ignored)."""
    z = z_mvci.dropna()
    fire = z > 2.0
    return pd.Series(np.where(fire, 0.5, 1.0), index=z.index, name="w_combination")


def rule_r_alt2(z_mvci: pd.Series, z_mrc: pd.Series) -> pd.Series:
    """R-ALT2 (alternative): continuous gradient on joint MVCI+MRC stress.

        w_combination(t) = clamp(1.0 - 0.25 × max(0, z_mvci + z_mrc - 1.0), 0.50, 1.00)

    Smooth de-leveraging without a binary threshold.
    """
    aligned = pd.concat([z_mvci, z_mrc], axis=1, keys=["mvci", "mrc"]).dropna()
    joint = aligned["mvci"] + aligned["mrc"]
    w = 1.0 - 0.25 * np.maximum(0.0, joint - 1.0)
    return pd.Series(np.clip(w, 0.50, 1.00), index=aligned.index, name="w_combination")


def apply_mv_conditional(
    combo_monthly_returns: pd.Series,
    weight_series: pd.Series,
    tbill_monthly_return: pd.Series,
    rebal_cost_bps: float = 3.0,
) -> pd.Series:
    """Combine V1 Combination returns with T-bill returns per weight series.

    Algorithm:
      1. Align all three series on month-end.
      2. Shift weight by 1 month: r_v2[t] = w[t-1] * r_combo[t] + (1-w[t-1]) * r_tbill[t]
      3. Deduct ``rebal_cost_bps`` from r_v2[t] when w[t-1] ≠ w[t-2] (weight changed).

    The 1-month shift implements the pre-registration's "z observed at end of
    month t-1 governs allocation for month t" semantic.

    Parameters
    ----------
    combo_monthly_returns : pd.Series
        V1 Combination strategy monthly returns, indexed by month-end.
    weight_series : pd.Series
        Output of one of the rule_r_* functions (weight in V1 Combination).
    tbill_monthly_return : pd.Series
        Monthly nominal T-bill return.
    rebal_cost_bps : float
        Per-transition cost in basis points (default 3).

    Returns
    -------
    pd.Series of V2 monthly returns indexed by month-end.
    """
    aligned = pd.concat(
        [
            combo_monthly_returns.rename("r_combo"),
            weight_series.shift(1).rename("w"),
            tbill_monthly_return.rename("r_tbill"),
        ],
        axis=1,
    ).dropna()
    if aligned.empty:
        return pd.Series(dtype="float64", name="r_v2")

    # Detect weight changes; no cost on first month.
    w_prev = aligned["w"].shift(1)
    changed = (aligned["w"] != w_prev).astype(int)
    changed.iloc[0] = 0
    cost = changed * (rebal_cost_bps / 10_000.0)

    r_v2 = aligned["w"] * aligned["r_combo"] + (1.0 - aligned["w"]) * aligned["r_tbill"] - cost
    r_v2.name = "r_v2"
    return r_v2


# ─────────────────────────────────────────────────────────────────────────
# Data loaders for combo monthly returns (from v50 v11.2 export) and T-bills.
# ─────────────────────────────────────────────────────────────────────────

def load_combo_monthly_returns(
    period_label: str = "FULL",
    costbps: int = 15,
    results_dir: Path | None = None,
) -> pd.Series:
    """Load V1 Combination monthly returns CSV emitted by v50 v11.2 hook.

    Filename pattern: ``v50_v11_2_combo_monthly_returns_<period>_<bps>bps.csv``.
    Requires v50 to have been run with ``V11_2_EXPORT_RETURNS=1``.
    """
    if results_dir is None:
        results_dir = QUANT_PIPELINE_RESULTS
    fname = results_dir / f"v50_v11_2_combo_monthly_returns_{period_label}_{int(costbps)}bps.csv"
    if not fname.exists():
        raise FileNotFoundError(
            f"{fname} missing — re-run v50 with V11_2_EXPORT_RETURNS=1 and "
            f"V11_1_DROP_STRATEGIES=1 to emit combo monthly returns."
        )
    df = pd.read_csv(fname, parse_dates=[0], index_col=0)
    s = df["combo_return"].astype("float64").sort_index()
    s.name = "combo_return"
    return s


def load_tbill_monthly_return(start: str | None = None, end: str | None = None) -> pd.Series:
    """Load monthly nominal T-bill return derived from Shiller's GS10 series.

    Per ``src/backtest/data.py``: short rate = long_rate_gs10 × 0.6, then
    monthly log return ≈ log1p(short_rate)/12. This is the NOMINAL form (no
    CPI subtraction) so it composites with v50's nominal combo returns.
    """
    from src.ingest.shiller_loader import load_shiller

    sh = load_shiller()
    df = sh.data
    if "long_rate_gs10" not in df.columns:
        raise ValueError("Shiller data missing 'long_rate_gs10'")
    yld = df["long_rate_gs10"].astype("float64").dropna().sort_index()
    yld.index = pd.DatetimeIndex(yld.index).to_period("M").to_timestamp(how="end").normalize()
    yld = yld[~yld.index.duplicated(keep="last")]
    short_rate_annual = yld * 0.6
    monthly_log = np.log1p(short_rate_annual) / 12.0
    # Convert log return to simple return so it composites with combo simple returns.
    rf_simple = np.expm1(monthly_log)
    if start is not None:
        rf_simple = rf_simple[rf_simple.index >= pd.Timestamp(start)]
    if end is not None:
        rf_simple = rf_simple[rf_simple.index <= pd.Timestamp(end)]
    rf_simple.name = "rf_return"
    return rf_simple


# ─────────────────────────────────────────────────────────────────────────
# Top-level orchestration
# ─────────────────────────────────────────────────────────────────────────

RULE_REGISTRY: dict[str, Callable] = {
    "R-PRIMARY": rule_r_primary,
    "R-ALT1": rule_r_alt1,
    "R-ALT2": rule_r_alt2,
}


def compute_v2_returns_all_rules(
    period_label: str = "FULL",
    costbps: int = 15,
) -> dict[str, pd.Series]:
    """Compute V2 monthly returns for R-PRIMARY, R-ALT1, R-ALT2.

    Returns dict keyed by rule label.
    """
    z = load_mvci_mrc_zscores_monthly()
    combo = load_combo_monthly_returns(period_label=period_label, costbps=costbps)
    tbill = load_tbill_monthly_return()

    out: dict[str, pd.Series] = {}
    for name, rule_fn in RULE_REGISTRY.items():
        weights = rule_fn(z["z_mvci"], z["z_mrc"])
        v2 = apply_mv_conditional(combo, weights, tbill)
        v2.name = f"V2_{name}"
        out[f"V2_{name}"] = v2
    return out


__all__ = [
    "compute_pit_zscore",
    "load_mvci_mrc_zscores_monthly",
    "rule_r_primary",
    "rule_r_alt1",
    "rule_r_alt2",
    "apply_mv_conditional",
    "load_combo_monthly_returns",
    "load_tbill_monthly_return",
    "compute_v2_returns_all_rules",
    "RULE_REGISTRY",
]
