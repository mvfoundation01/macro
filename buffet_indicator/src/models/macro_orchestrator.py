"""v11.0b Macro orchestrator -- plumb the 7 macro indicators + 3 MRC variants
through the existing predictive-regression / Bayesian / conviction pipeline.

Key contract differences vs. ``_analyze_dual_frame()`` in
:mod:`src.models.orchestrator_modeling`:

1. Input is the **canonical signal** series (already direction-encoded so
   high → bearish equities, per the v11.0a banned-anti-pattern §7). The
   existing analyse function expects a raw level series and decomposes via
   log-linear trend / Bai-Perron; for stationary signals (yield-curve
   spread, log credit spread, 12M margin-debt growth) the trend is
   essentially flat and the residuals ≈ signal − mean, so we feed
   ``exp(signal)`` to ``_analyze_dual_frame`` and let the existing logic
   recover ``signal`` as ``log(exp(signal))`` inside ``log_linear_trend``.

2. Sample-size penalty per master spec §6.2: conviction is multiplied by
   ``min(1, n_obs / 100)``. Credit spreads and MRC only start 1996-12, so
   their 10-year forward returns observation count is small; this gates
   conviction honestly.

3. Cross-composite analysis: in addition to per-indicator output, we
   compute the (MVCI, MRC) joint quadrant classification and persist it to
   ``outputs/cross_composite/mvci_mrc_joint.parquet``.

References
----------
* Hansen, L.P., Hodrick, R.J. (1980). "Forward exchange rates as optimal
  predictors of future spot rates." JPE 88.
* Newey, W.K., West, K.D. (1987). HAC standard errors.
* Stambaugh, R.F. (1999). "Predictive regressions." JFE 54.
* Goyal, A., Welch, I. (2008). RFS 21.
* Clark, T.E., West, K.D. (2007). "Approximately normal tests for equal
  predictive accuracy in nested models." J. Econometrics.
* Politis, D.N., Romano, J.P. (1994). "The stationary bootstrap." JASA 89.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


_MACRO_HORIZONS_MONTHS = (1, 3, 12, 36, 60, 84, 120)
_SAMPLE_PENALTY_FLOOR = 100  # n_obs at which sample-size penalty == 1.0


def _signal_to_positive(signal: pd.Series) -> pd.Series:
    """Map a possibly-negative direction-encoded signal to strictly positive
    input for the existing trend-decomposition pipeline.

    Uses ``exp(signal)``: positive, monotonic in signal, log-linear-trend
    will recover ``signal`` exactly as its log-residual (with a small bias
    absorbed by the trend's intercept). Z-score is scale-invariant.
    """
    s = pd.Series(np.exp(signal.astype("float64")), index=signal.index)
    s.name = signal.name
    return s


def analyze_macro_indicator(
    variant_key: str,
    signal: pd.Series,
    *,
    forward_returns: dict[str, pd.DataFrame] | None,
    bootstrap_n: int = 2000,
    n_bootstrap_prob: int = 2000,
    risk_free_rate_decimal: float = 0.045,
    sample_floor: int = _SAMPLE_PENALTY_FLOOR,
) -> dict[str, Any]:
    """Run a macro indicator through the full dual-frame pipeline.

    Returns the same nested dict shape as
    :func:`src.models.orchestrator_modeling._analyze_dual_frame`, with an
    additional ``sample_size_penalty`` field at the root.
    """
    from src.models.orchestrator_modeling import _analyze_dual_frame

    if signal is None or signal.dropna().empty:
        return {"available": False, "reason": "empty signal"}

    # Translate signal to positive input for the existing analyse function.
    positive_input = _signal_to_positive(signal.dropna())
    out = _analyze_dual_frame(
        positive_input,
        forward_returns=forward_returns,
        bootstrap_n=bootstrap_n,
        risk_free_rate_decimal=risk_free_rate_decimal,
        n_bootstrap_prob=n_bootstrap_prob,
        include_forward_outlook=forward_returns is not None,
        variant_key=variant_key,
    )

    n_obs = int(signal.dropna().shape[0])
    out["n_observations"] = n_obs
    out["sample_size_penalty"] = min(1.0, n_obs / sample_floor)

    # Apply the sample-size penalty multiplicatively to conviction scores per
    # master spec §6.2. We keep the raw conviction visible alongside.
    for frame_name in ("long_run", "current_regime"):
        frame_blk = out.get(frame_name)
        if not isinstance(frame_blk, dict):
            continue
        fc = frame_blk.get("full_conviction")
        if not fc:
            continue
        for h_key, conviction in fc.items():
            if isinstance(conviction, dict) and "score" in conviction:
                raw = float(conviction["score"])
                penalized = raw * out["sample_size_penalty"]
                conviction["score_raw_unpenalized"] = raw
                conviction["score"] = float(np.clip(penalized, 0.0, 5.0))
                conviction["sample_size_penalty_applied"] = out["sample_size_penalty"]

    return out


# ---------------------------------------------------------------------------
# Cross-composite analysis (MVCI × MRC quadrants)
# ---------------------------------------------------------------------------


def classify_quadrant(mvci_z: float, mrc_z: float) -> str:
    """Quadrant label for a (MVCI, MRC) pair. Threshold = 0 σ."""
    if mvci_z >= 0 and mrc_z >= 0:
        return "high_val_high_stress"
    if mvci_z >= 0 and mrc_z < 0:
        return "high_val_low_stress"
    if mvci_z < 0 and mrc_z >= 0:
        return "low_val_high_stress"
    return "low_val_low_stress"


def quadrant_history(
    mvci_series: pd.Series,
    mrc_series: pd.Series,
    forward_returns: pd.DataFrame | None = None,
    *,
    horizon_col: str = "r_120m",
) -> pd.DataFrame:
    """Build a per-month quadrant classification table.

    Optionally joins the chosen forward-return horizon for downstream
    quadrant-conditional return distributions.
    """
    mvci = mvci_series.dropna()
    mrc = mrc_series.dropna()
    common = mvci.index.intersection(mrc.index)
    df = pd.DataFrame(
        {
            "mvci_z": mvci.loc[common].astype("float64"),
            "mrc_z": mrc.loc[common].astype("float64"),
        }
    )
    df["quadrant"] = [
        classify_quadrant(float(a), float(b))
        for a, b in zip(df["mvci_z"], df["mrc_z"])
    ]
    if forward_returns is not None and horizon_col in forward_returns.columns:
        df = df.join(forward_returns[horizon_col].rename("forward_return"))
    df.index.name = "date"
    return df


def quadrant_summary(quadrant_df: pd.DataFrame) -> pd.DataFrame:
    """Summary statistics of forward returns by quadrant."""
    if "forward_return" not in quadrant_df.columns:
        return quadrant_df.groupby("quadrant").size().to_frame("n_months")
    grp = quadrant_df.dropna(subset=["forward_return"]).groupby("quadrant")
    return grp["forward_return"].agg(
        n_months="count", mean="mean", median="median", std="std",
        p10=lambda s: s.quantile(0.10), p90=lambda s: s.quantile(0.90),
    )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _serialise_outlook(outlook: dict[str, Any]) -> dict[str, Any]:
    """Strip non-serialisable series, keep scalar metrics for parquet."""
    out: dict[str, Any] = {}
    for k, v in outlook.items():
        if isinstance(v, dict):
            out[k] = _serialise_outlook(v)
        elif isinstance(v, (int, float, str, bool, type(None))):
            out[k] = v
        elif isinstance(v, (np.integer, np.floating)):
            out[k] = float(v)
        # series/dataframes are dropped (too heavy for parquet rows)
    return out


def persist_indicator_block(
    variant_key: str,
    block: dict[str, Any],
    *,
    out_dir: Path = Path("outputs/indicators"),
) -> Path:
    """Write the full dual-frame block to a per-indicator JSON parquet.

    We write one parquet row per (frame, horizon) for downstream tabs to
    consume cleanly.
    """
    out_dir = Path(out_dir) / variant_key
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for frame_name in ("long_run", "current_regime"):
        frame_blk = block.get(frame_name)
        if not isinstance(frame_blk, dict):
            continue
        row_base = {
            "variant_key": variant_key,
            "frame": frame_name,
            "z_score": float(frame_blk.get("z_score", float("nan"))),
            "regime": str(frame_blk.get("regime", "")),
            "n_observations": int(frame_blk.get("n_observations", 0)),
            "confidence_pct": float(frame_blk.get("confidence_pct", float("nan"))),
            "sample_size_penalty": float(block.get("sample_size_penalty", 1.0)),
        }
        forward = frame_blk.get("forward_outlook") or {}
        primary = forward.get("primary") or {}
        if not primary:
            rows.append({**row_base, "horizon_months": None})
            continue
        for h_key, h_blk in primary.items():
            if not h_blk.get("available"):
                continue
            reg = h_blk.get("regression") or {}
            oos = h_blk.get("oos") or {}
            prob = h_blk.get("probabilities") or {}
            bayes = h_blk.get("bayesian") or {}
            fc = (frame_blk.get("full_conviction") or {}).get(h_key) or {}
            rows.append(
                {
                    **row_base,
                    "horizon_months": int(h_blk["horizon_months"]),
                    "alpha": float(reg.get("alpha", float("nan"))),
                    "beta_hat": float(reg.get("beta", float("nan"))),
                    "se_hh": float(reg.get("beta_se_hh", float("nan"))),
                    "se_nw": float(reg.get("beta_se_nw", float("nan"))),
                    "t_hh": float(reg.get("t_hh", float("nan"))),
                    "t_nw": float(reg.get("t_nw", float("nan"))),
                    "p_nw": float(reg.get("pvalue_nw", float("nan"))),
                    "r2_in": float(reg.get("r_squared", float("nan"))),
                    "beta_stambaugh": float(
                        reg.get("beta_stambaugh", float("nan"))
                    ),
                    "rho_ar1": float(reg.get("rho_ar1", float("nan"))),
                    "r2_oos_gw": float(
                        (oos.get("goyal_welch") or {}).get("r2_oos", float("nan"))
                    ),
                    "cw_stat": float(
                        (oos.get("clark_west") or {}).get("statistic", float("nan"))
                    ),
                    "p_neg_return": float(
                        prob.get("p_negative_return", float("nan"))
                    ),
                    "bayesian_mean": float(
                        bayes.get("posterior_mean", float("nan"))
                    ),
                    "conviction": float(fc.get("score", float("nan"))),
                }
            )
    if not rows:
        rows = [{"variant_key": variant_key, "frame": "long_run", "horizon_months": None}]
    df = pd.DataFrame(rows)
    out_path = out_dir / "dual_frame_summary.parquet"
    df.to_parquet(out_path)
    return out_path


__all__ = [
    "analyze_macro_indicator",
    "classify_quadrant",
    "quadrant_history",
    "quadrant_summary",
    "persist_indicator_block",
]
