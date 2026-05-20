"""v11.0c — assemble Plotly chart specs for the 8 macro-risk tabs +
the Overview Macro Risk Snapshot, and the MRC tab's 5 special elements.

Returns a dict structured for direct injection into the dashboard JSON
payload, consumed by ``dashboard.js::renderMacroChartsForTab()``.

Output shape::

    {
        "macro_hero_specs": {
            "yc_10y3m": {<plotly spec>},
            ...,
            "mrc": {<plotly spec>},
        },
        "macro_variant_charts": {
            "<key>": {"panel_a": {...}, "panel_b": {...},
                      "panel_c": "__SHARED_PANEL_C__", "cond_dist": {...}},
            ...,
        },
        "mrc_extras": {
            "constituent_contributions": {...},
            "correlation_heatmap": {...},
            "pca_scree": {...},
            "cross_composite_quadrant": {...},
        },
        "overview_mvci_mrc_mini": {<plotly spec>},
        "macro_metrics": {
            "<key>": {"z_fmt": "+0.42σ", "p_neg_fmt": "12%",
                      "p_neg_ci_fmt": "[5%, 19%]", "confidence_fmt": "60%",
                      "conviction_fmt": "2.3", "regime": "Fair Value",
                      "regime_color": "#9AA0A6"},
            ...,
        },
    }
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.viz.captions import REGIME_COLORS
from src.viz.chart_specs import (
    make_conditional_distribution,
    make_constituent_contributions,
    make_correlation_heatmap,
    make_cross_composite_quadrant,
    make_dual_z_overlay,
    make_hero_chart,
    make_panel_a,
    make_panel_b,
    make_pca_scree,
)


MACRO_KEYS = (
    "yc_10y3m",
    "yc_10y2y",
    "cs_hy_master",
    "cs_ig_master",
    "cs_hy_bb",
    "cs_hy_ccc",
    "margin_debt_growth",
    # v11.0.1 — 6 derived spreads
    "spread_hy_ig",
    "spread_ccc_bb",
    "spread_hy_reach_for_yield",
    "spread_hy_treasury_traditional",
    "spread_equity_credit_rp",
    "spread_hy_oas_3m_delta",
)

VARIANT_LABEL = {
    "yc_10y3m": "Yield Curve 10Y-3M",
    "yc_10y2y": "Yield Curve 10Y-2Y",
    "cs_hy_master": "HY OAS (master)",
    "cs_ig_master": "IG OAS (master)",
    "cs_hy_bb": "HY BB OAS",
    "cs_hy_ccc": "HY CCC OAS",
    "margin_debt_growth": "Margin Debt 12M Growth",
    "spread_hy_ig": "HY-IG Spread",
    "spread_ccc_bb": "CCC-BB Distress",
    "spread_hy_reach_for_yield": "HY Reach-for-Yield",
    "spread_hy_treasury_traditional": "HY-Treasury (Trad.)",
    "spread_equity_credit_rp": "Equity-Credit Risk Premium",
    "spread_hy_oas_3m_delta": "HY OAS 3M Δ",
}


def _classify_regime(z: float, *, convention: str = "trend") -> tuple[str, str]:
    """Map z-score to (label, color).

    Trend indicators (most valuation; yield curve; margin debt): high z =
    bearish equities → red callout. Label uses 'overvalued'/'undervalued'
    terminology.

    Contrarian indicators (credit spreads where empirical β > 0): high z =
    stress widening → contrarian buy signal → expected forward returns
    above average → GREEN callout. Label uses 'stressed'/'tight' terminology.
    The COLOR encodes the expected-forward-return direction (red=below
    average, green=above), so a user can always read it as "is this good
    or bad for stocks?" without knowing the convention.
    """
    if convention == "contrarian":
        # Map z to "expected forward return" direction inverted relative to
        # trend: high z = above-average forward (green); low z = below.
        if z >= 2.0:
            label = "Strongly Stressed"
            color_key = "Strongly Undervalued"  # green
        elif z >= 1.0:
            label = "Stressed"
            color_key = "Undervalued"  # light green
        elif z >= -1.0:
            label = "Fair Value"
            color_key = "Fair Value"
        elif z >= -2.0:
            label = "Tight"
            color_key = "Overvalued"  # orange
        else:
            label = "Strongly Tight"
            color_key = "Strongly Overvalued"  # red
        return label, REGIME_COLORS.get(color_key, "#9AA0A6")
    # Trend convention (default).
    if z >= 2.0:
        label = "Strongly Overvalued"
    elif z >= 1.0:
        label = "Overvalued"
    elif z >= -1.0:
        label = "Fair Value"
    elif z >= -2.0:
        label = "Undervalued"
    else:
        label = "Strongly Undervalued"
    return label, REGIME_COLORS.get(label, "#9AA0A6")


def _fmt_signed(x: float | None, digits: int = 2, suffix: str = "") -> str:
    if x is None or not np.isfinite(x):
        return "n/a"
    return f"{x:+.{digits}f}{suffix}"


def _fmt_pct(p: float | None, digits: int = 0) -> str:
    if p is None or not np.isfinite(p):
        return "n/a"
    return f"{p * 100:.{digits}f}%"


def _fmt_ci(low: float | None, high: float | None) -> str:
    if low is None or high is None or not (np.isfinite(low) and np.isfinite(high)):
        return ""
    return f"[{low * 100:.0f}%, {high * 100:.0f}%]"


def _load_value_history(key: str) -> pd.DataFrame | None:
    pq = Path(f"outputs/charts/{key}_value_history.parquet")
    if not pq.exists():
        return None
    return pd.read_parquet(pq).set_index("date")


def _load_dual_frame(key: str) -> pd.DataFrame | None:
    pq = Path(f"outputs/indicators/{key}/dual_frame_summary.parquet")
    if not pq.exists():
        return None
    return pd.read_parquet(pq)


def _load_mrc_series(scheme: str = "equal_weight") -> pd.Series:
    pq = Path("outputs/charts/mrc_value_history.parquet")
    if not pq.exists():
        return pd.Series(dtype="float64")
    df = pd.read_parquet(pq)
    sub = df[df["scheme"] == scheme].set_index("date")["mrc_z"].dropna().sort_index()
    return sub


def _signal_z_series(key: str) -> pd.Series:
    """Return the expanding-window Huber z-score of the indicator's signal."""
    if key == "mrc":
        return _load_mrc_series("equal_weight")
    df = _load_value_history(key)
    if df is None or "signal" not in df.columns:
        return pd.Series(dtype="float64")
    sig = df["signal"].astype("float64").dropna()
    # Re-derive z directly here (orchestrator already used Huber expanding
    # z-scoring; we mirror that math via expanding_zscore).
    from src.models.zscore import expanding_zscore  # local import (circular safety)
    z = expanding_zscore(sig, min_periods=60, scale_method="huber")
    return z.dropna()


def _quadrant_means(qsum_path: Path) -> dict[str, float]:
    if not qsum_path.exists():
        return {}
    df = pd.read_parquet(qsum_path)
    return {str(k): float(df.loc[k, "mean"]) for k in df.index if "mean" in df.columns}


def _compute_p_event_at_horizon(
    z_series: pd.Series,
    forward_returns: pd.Series,
    *,
    event: str = "lt_5pct",
    horizon_months: int = 120,
    risk_free_rate: float = 0.045,
    n_bootstrap: int = 10_000,
    seed: int = 42,
) -> dict[str, Any]:
    """Conditional P(event) at the current z-bucket + bootstrap CI.

    Master spec §3.6: 10,000 reps minimum for any reported bootstrap CI.
    Master spec §5.3: events include {lt_5pct, lt_rf, gt_7pct, lt_0pct}.

    Bucket = quintile of historical z; current observation falls in one bucket.
    """
    z = z_series.dropna()
    fr = forward_returns.dropna()
    common = z.index.intersection(fr.index)
    if len(common) < 60:
        return {"point": float("nan"), "ci_low": float("nan"),
                "ci_high": float("nan"), "n": 0, "bucket_returns": []}
    za = z.loc[common].astype("float64")
    ra = fr.loc[common].astype("float64")
    if za.iloc[-1] is None or not np.isfinite(za.iloc[-1]):
        return {"point": float("nan"), "ci_low": float("nan"),
                "ci_high": float("nan"), "n": 0, "bucket_returns": []}
    current_z = float(za.iloc[-1])
    # Quintile bucket boundaries (across all historical z).
    quintiles = np.quantile(za, [0.2, 0.4, 0.6, 0.8])
    bucket_idx = int(np.searchsorted(quintiles, current_z))
    bucket_idx = max(0, min(4, bucket_idx))
    lo = -np.inf if bucket_idx == 0 else quintiles[bucket_idx - 1]
    hi = np.inf if bucket_idx == 4 else quintiles[bucket_idx]
    mask = (za >= lo) & (za < hi)
    bucket_returns = ra.loc[mask].dropna().values
    if len(bucket_returns) < 20:
        # Fall back to the nearest two quintiles for a less brittle estimate.
        sorted_idx = np.argsort(np.abs(za.values - current_z))
        bucket_returns = ra.iloc[sorted_idx[:max(20, len(ra) // 5)]].dropna().values
    if len(bucket_returns) == 0:
        return {"point": float("nan"), "ci_low": float("nan"),
                "ci_high": float("nan"), "n": 0, "bucket_returns": []}

    # Event predicate per master spec §5.3.
    def _event_indicator(arr: np.ndarray) -> np.ndarray:
        if event == "lt_0pct":
            return arr < 0
        if event == "lt_rf":
            return arr < risk_free_rate
        if event == "lt_5pct":
            return arr < 0.05
        if event == "gt_7pct":
            return arr > 0.07
        raise ValueError(f"Unknown event {event!r}")

    point = float(np.mean(_event_indicator(bucket_returns)))
    # Politis-Romano stationary bootstrap (mean block length ~ sqrt(n)).
    rng = np.random.default_rng(seed)
    n = len(bucket_returns)
    mbl = max(4, int(np.sqrt(n)))
    p_prob = 1.0 / mbl
    boots = np.empty(n_bootstrap, dtype="float64")
    for b in range(n_bootstrap):
        idx = np.empty(n, dtype="int64")
        i = 0
        while i < n:
            start = int(rng.integers(0, n))
            block_len = int(rng.geometric(p_prob))
            for k in range(block_len):
                if i >= n:
                    break
                idx[i] = (start + k) % n
                i += 1
        sample = bucket_returns[idx]
        boots[b] = float(np.mean(_event_indicator(sample)))
    ci_low = float(np.quantile(boots, 0.025))
    ci_high = float(np.quantile(boots, 0.975))
    return {
        "point": point,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "n": int(len(bucket_returns)),
        "bucket_returns": [float(v) for v in bucket_returns],
        "event": event,
    }


# Backwards-compatible alias (v11.0c name) — defaults to the lt_5pct event so
# existing tests + dashboard binding default to the v11.0.1 spec-compliant
# computation.
def _compute_p_neg_at_horizon(
    z_series: pd.Series,
    forward_returns: pd.Series,
    horizon_months: int = 120,
    *,
    bucket_quantile: float = 0.20,
    n_bootstrap: int = 10_000,
    seed: int = 42,
    event: str = "lt_5pct",
) -> dict[str, Any]:
    """Backward-compatible wrapper. Default event switched to ``lt_5pct``
    per v11.0.1 spec (matches MVCI's headline pill label)."""
    return _compute_p_event_at_horizon(
        z_series, forward_returns,
        event=event, horizon_months=horizon_months,
        n_bootstrap=n_bootstrap, seed=seed,
    )


def build_macro_chart_payload(
    forward_returns: dict[str, pd.DataFrame],
    *,
    z_history: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Build the full macro chart payload.

    Parameters
    ----------
    forward_returns : dict
        Output of ``build_forward_returns()`` — must contain ``fr_spliced``.
    z_history : pd.DataFrame | None
        Used to source MVCI z-series for the cross-composite quadrant.
    """
    fr = forward_returns.get("fr_spliced")
    r_120 = fr["r_120m"].dropna() if fr is not None else pd.Series(dtype="float64")

    hero_specs: dict[str, Any] = {}
    variant_charts: dict[str, Any] = {}
    metrics: dict[str, Any] = {}

    # ---------- per-indicator (7 macro constituents) -----------
    for key in MACRO_KEYS:
        z = _signal_z_series(key)
        if z.empty:
            continue
        hero_specs[key] = make_hero_chart(
            z, title=VARIANT_LABEL[key], chart_name=f"{key}_hero"
        )
        panel_a = make_panel_a(z, title=f"{VARIANT_LABEL[key]} z-score")
        # Panel B (z vs forward return scatter): inner-join z with r_120
        scatter_pts = pd.DataFrame(
            {"z_score_long_run": z, "forward_120m_cagr": r_120}
        ).dropna()
        scatter_pts = scatter_pts.reset_index().rename(columns={"index": "date", "date": "date"})
        # Try to derive a quick OLS β / R² for annotation.
        beta = float("nan")
        r_squared = float("nan")
        t_nw = float("nan")
        if len(scatter_pts) >= 60:
            x = scatter_pts["z_score_long_run"].astype("float64").values
            y = scatter_pts["forward_120m_cagr"].astype("float64").values
            x_c = x - x.mean()
            denom = (x_c ** 2).sum()
            if denom > 0:
                beta = float((x_c * (y - y.mean())).sum() / denom)
                y_hat = beta * (x - x.mean()) + y.mean()
                ss_res = float(((y - y_hat) ** 2).sum())
                ss_tot = float(((y - y.mean()) ** 2).sum())
                r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        regression = {"beta": beta, "alpha": 0.0, "r_squared": r_squared, "t_nw": t_nw}
        current_z = float(z.iloc[-1])
        panel_b = make_panel_b(
            scatter_pts[["date", "z_score_long_run", "forward_120m_cagr"]],
            current_z=current_z,
            regression=regression,
            title=f"{VARIANT_LABEL[key]} z vs 10Y forward CAGR",
        )

        # Conditional distribution + P(<5% 10Y CAGR) at current z (v11.0.1
        # spec §A.2 — matches MVCI's headline pill convention).
        p_evt = _compute_p_event_at_horizon(
            z, r_120, event="lt_5pct", horizon_months=120, n_bootstrap=10_000,
        )
        # Per-horizon probability events (master spec §5.3) — wired to the
        # probability table on each tab (Stage B). Trim heavy bucket_returns
        # from each event dict before serialisation to keep the bundle small.
        per_horizon_events: dict[str, dict[str, Any]] = {}

        def _slim(ev: dict[str, Any]) -> dict[str, Any]:
            return {
                "point": ev.get("point"),
                "ci_low": ev.get("ci_low"),
                "ci_high": ev.get("ci_high"),
                "n": ev.get("n"),
            }

        for h_label, h_col in (
            ("h_12m", "r_12m"), ("h_36m", "r_36m"),
            ("h_60m", "r_60m"), ("h_120m", "r_120m"),
        ):
            if fr is None or h_col not in fr.columns:
                continue
            r_h = fr[h_col].dropna()
            per_horizon_events[h_label] = {
                "lt_0pct": _slim(_compute_p_event_at_horizon(
                    z, r_h, event="lt_0pct", horizon_months=int(h_col[2:-1]),
                    n_bootstrap=10_000,
                )),
                "lt_rf": _slim(_compute_p_event_at_horizon(
                    z, r_h, event="lt_rf", horizon_months=int(h_col[2:-1]),
                    n_bootstrap=10_000,
                )),
                "lt_5pct": _slim(_compute_p_event_at_horizon(
                    z, r_h, event="lt_5pct", horizon_months=int(h_col[2:-1]),
                    n_bootstrap=10_000,
                )),
                "gt_7pct": _slim(_compute_p_event_at_horizon(
                    z, r_h, event="gt_7pct", horizon_months=int(h_col[2:-1]),
                    n_bootstrap=10_000,
                )),
            }
        cond_dist = make_conditional_distribution(
            p_evt["bucket_returns"],
            bayesian_mean=float(np.mean(p_evt["bucket_returns"]))
            if p_evt["bucket_returns"] else None,
            var_5=float(np.quantile(p_evt["bucket_returns"], 0.05))
            if p_evt["bucket_returns"] else None,
            title=f"{VARIANT_LABEL[key]} — conditional 10Y return distribution",
            chart_name=f"{key}_cond_dist",
        )

        variant_charts[key] = {
            "panel_a": panel_a,
            "panel_b": panel_b,
            "panel_c": "__SHARED_PANEL_C__",
            "cond_dist": cond_dist,
            "per_horizon_events": per_horizon_events,
        }

        # Pull conviction + confidence from the dual_frame_summary.parquet.
        dframe = _load_dual_frame(key)
        confidence_pct = float("nan")
        conviction_10y = float("nan")
        if dframe is not None and not dframe.empty:
            lr = dframe[dframe["frame"] == "long_run"]
            if not lr.empty:
                confidence_pct = float(lr.iloc[0].get("confidence_pct", float("nan")))
            h120 = lr[lr["horizon_months"] == 120]
            if not h120.empty:
                conviction_10y = float(h120.iloc[0].get("conviction", float("nan")))

        # v11.0.1 §E: regime label + color use direction convention.
        from src.viz.data_extraction import VARIANT_REGISTRY  # local to avoid cycles
        direction_conv = VARIANT_REGISTRY.get(key, {}).get(
            "direction_convention", "trend"
        )
        regime, color = _classify_regime(current_z, convention=direction_conv)
        metrics[key] = {
            "z": current_z,
            "z_fmt": _fmt_signed(current_z, suffix="σ"),
            "p_neg": p_evt["point"],
            "p_neg_fmt": _fmt_pct(p_evt["point"]),
            "p_neg_ci_fmt": _fmt_ci(p_evt["ci_low"], p_evt["ci_high"]),
            "p_neg_label": "P(< 5% 10Y CAGR)",
            "confidence_fmt": _fmt_pct(confidence_pct / 100.0) if np.isfinite(confidence_pct) else "n/a",
            "conviction_fmt": f"{conviction_10y:.2f}" if np.isfinite(conviction_10y) else "n/a",
            "regime": regime,
            "regime_color": color,
            "direction_convention": direction_conv,
            "n_obs": int(p_evt["n"]),
        }

    # ---------- MRC composite -----------
    mrc_z = _signal_z_series("mrc")
    mrc_extras: dict[str, Any] = {}
    if not mrc_z.empty:
        hero_specs["mrc"] = make_hero_chart(
            mrc_z, title="MV Macro Risk Composite (MRC)", chart_name="mrc_hero"
        )
        panel_a = make_panel_a(mrc_z, title="MRC z-score (long-run)")
        scatter_pts = pd.DataFrame(
            {"z_score_long_run": mrc_z, "forward_120m_cagr": r_120}
        ).dropna()
        scatter_pts = scatter_pts.reset_index().rename(columns={"index": "date", "date": "date"})
        beta = float("nan")
        r_squared = float("nan")
        if len(scatter_pts) >= 60:
            x = scatter_pts["z_score_long_run"].values
            y = scatter_pts["forward_120m_cagr"].values
            x_c = x - x.mean()
            if (x_c ** 2).sum() > 0:
                beta = float((x_c * (y - y.mean())).sum() / (x_c ** 2).sum())
                y_hat = beta * (x - x.mean()) + y.mean()
                ss_res = float(((y - y_hat) ** 2).sum())
                ss_tot = float(((y - y.mean()) ** 2).sum())
                r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        regression = {"beta": beta, "alpha": 0.0, "r_squared": r_squared, "t_nw": float("nan")}
        current_mrc = float(mrc_z.iloc[-1])
        panel_b = make_panel_b(
            scatter_pts[["date", "z_score_long_run", "forward_120m_cagr"]],
            current_z=current_mrc, regression=regression,
            title="MRC z-score vs 10Y forward CAGR",
        )
        # v11.0.1 §A: P(<5% 10Y CAGR) for MRC tile.
        p_evt_mrc = _compute_p_event_at_horizon(
            mrc_z, r_120, event="lt_5pct", horizon_months=120, n_bootstrap=10_000,
        )
        per_horizon_events_mrc: dict[str, dict[str, Any]] = {}
        for h_label, h_col in (
            ("h_12m", "r_12m"), ("h_36m", "r_36m"),
            ("h_60m", "r_60m"), ("h_120m", "r_120m"),
        ):
            if fr is None or h_col not in fr.columns:
                continue
            r_h = fr[h_col].dropna()
            per_horizon_events_mrc[h_label] = {
                "lt_0pct": _compute_p_event_at_horizon(
                    mrc_z, r_h, event="lt_0pct",
                    horizon_months=int(h_col[2:-1]), n_bootstrap=10_000,
                ),
                "lt_rf": _compute_p_event_at_horizon(
                    mrc_z, r_h, event="lt_rf",
                    horizon_months=int(h_col[2:-1]), n_bootstrap=10_000,
                ),
                "lt_5pct": _compute_p_event_at_horizon(
                    mrc_z, r_h, event="lt_5pct",
                    horizon_months=int(h_col[2:-1]), n_bootstrap=10_000,
                ),
                "gt_7pct": _compute_p_event_at_horizon(
                    mrc_z, r_h, event="gt_7pct",
                    horizon_months=int(h_col[2:-1]), n_bootstrap=10_000,
                ),
            }
        cond_dist = make_conditional_distribution(
            p_evt_mrc["bucket_returns"],
            bayesian_mean=float(np.mean(p_evt_mrc["bucket_returns"]))
            if p_evt_mrc["bucket_returns"] else None,
            var_5=float(np.quantile(p_evt_mrc["bucket_returns"], 0.05))
            if p_evt_mrc["bucket_returns"] else None,
            title="MRC — conditional 10Y return distribution",
            chart_name="mrc_cond_dist",
        )
        variant_charts["mrc"] = {
            "panel_a": panel_a,
            "panel_b": panel_b,
            "panel_c": "__SHARED_PANEL_C__",
            "cond_dist": cond_dist,
            "per_horizon_events": per_horizon_events_mrc,
        }

        # MRC metrics (headline tile).
        dframe = _load_dual_frame("mrc_equal_weight")
        confidence_pct = float("nan")
        conviction_10y = float("nan")
        if dframe is not None and not dframe.empty:
            lr = dframe[dframe["frame"] == "long_run"]
            if not lr.empty:
                confidence_pct = float(lr.iloc[0].get("confidence_pct", float("nan")))
            h120 = lr[lr["horizon_months"] == 120]
            if not h120.empty:
                conviction_10y = float(h120.iloc[0].get("conviction", float("nan")))
        regime, color = _classify_regime(current_mrc)
        metrics["mrc"] = {
            "z": current_mrc,
            "z_fmt": _fmt_signed(current_mrc, suffix="σ"),
            "p_neg": p_evt_mrc["point"],
            "p_neg_fmt": _fmt_pct(p_evt_mrc["point"]),
            "p_neg_ci_fmt": _fmt_ci(p_evt_mrc["ci_low"], p_evt_mrc["ci_high"]),
            "p_neg_label": "P(< 5% 10Y CAGR)",
            "confidence_fmt": _fmt_pct(confidence_pct / 100.0) if np.isfinite(confidence_pct) else "n/a",
            "conviction_fmt": f"{conviction_10y:.2f}" if np.isfinite(conviction_10y) else "n/a",
            "regime": regime,
            "regime_color": color,
            "direction_convention": "trend",
            "n_obs": int(p_evt_mrc["n"]),
        }

        # ---------- MRC special elements -----------
        # B.1 Constituent contributions bar chart.
        z_by_variant: dict[str, float] = {}
        for k in MACRO_KEYS:
            z_k = _signal_z_series(k)
            if not z_k.empty:
                z_by_variant[k] = float(z_k.iloc[-1])
        mrc_extras["constituent_contributions"] = make_constituent_contributions(
            z_by_variant, labels=VARIANT_LABEL
        )

        # B.2 Rolling 60-month correlation heatmap.
        z_panel = pd.DataFrame(
            {k: _signal_z_series(k) for k in MACRO_KEYS if not _signal_z_series(k).empty}
        ).dropna()
        if len(z_panel) >= 60:
            rolling_corr = z_panel.tail(60).corr()
            # Rename to short labels.
            rolling_corr.index = [VARIANT_LABEL[k] for k in rolling_corr.index]
            rolling_corr.columns = [VARIANT_LABEL[k] for k in rolling_corr.columns]
            mrc_extras["correlation_heatmap"] = make_correlation_heatmap(rolling_corr)
        else:
            mrc_extras["correlation_heatmap"] = {"data": [], "layout": {"title": {"text": "Correlation — insufficient overlap"}}}

        # B.3 PCA scree (computed from constituent covariance directly).
        explained_variance = None
        if len(z_panel) >= 60:
            cov = np.cov(z_panel.values, rowvar=False)
            eigvals = sorted(np.linalg.eigvalsh(cov).tolist(), reverse=True)
            total = sum(eigvals) if sum(eigvals) > 0 else 1.0
            explained_variance = [v / total for v in eigvals]
        mrc_extras["pca_scree"] = make_pca_scree(explained_variance)

        # B.4 Cross-composite quadrant chart.
        mvci_z = pd.Series(dtype="float64")
        if z_history is not None and not z_history.empty:
            mask = (z_history["variant"] == "mvci") & (z_history["frame"] == "long_run")
            sub = z_history[mask]
            if not sub.empty:
                mvci_z = pd.Series(
                    sub["z_score"].astype("float64").values,
                    index=pd.DatetimeIndex(sub["date"]),
                )
        qsum_path = Path("outputs/cross_composite/mvci_mrc_quadrant_summary.parquet")
        mrc_extras["cross_composite_quadrant"] = make_cross_composite_quadrant(
            mvci_z, mrc_z, _quadrant_means(qsum_path)
        )

        # Overview mini chart.
        overview_mini = make_dual_z_overlay(
            mvci_z, mrc_z,
            name1="MVCI", name2="MRC",
            title="MVCI and MRC over time",
            chart_name="overview_mvci_mrc_mini",
        )
    else:
        overview_mini = {"data": [], "layout": {"title": {"text": "MVCI × MRC — n/a"}}}

    return {
        "macro_hero_specs": hero_specs,
        "macro_variant_charts": variant_charts,
        "mrc_extras": mrc_extras,
        "overview_mvci_mrc_mini": overview_mini,
        "macro_metrics": metrics,
    }


__all__ = ["build_macro_chart_payload", "MACRO_KEYS", "VARIANT_LABEL"]
