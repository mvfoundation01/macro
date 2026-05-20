"""v11.0b — assemble Jinja2 contexts for the 8 new macro-risk tabs and the
Overview Macro Risk Snapshot section.

Reads from the parquets produced by:

- v11.0a: ``outputs/charts/{key}_value_history.parquet``,
          ``outputs/charts/mrc_value_history.parquet``,
          ``outputs/charts/mrc_pca_loadings_full.parquet``
- v11.0b: ``outputs/indicators/{key}/dual_frame_summary.parquet``,
          ``outputs/cross_composite/current_state.json``,
          ``outputs/cross_composite/mvci_mrc_quadrant_summary.parquet``

Defensive: if a parquet is missing the variant is omitted from the context
and the template renders an empty-state placeholder. No exception bubbles up
to the dashboard build.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.viz.captions import REGIME_COLORS, WHY_IT_MATTERS, PANEL_A_CAPTIONS


HORIZON_ORDER = (1, 3, 12, 36, 60, 84, 120)
HORIZON_LABEL = {
    1: "1MO", 3: "3MO", 12: "1YR",
    36: "3YR", 60: "5YR", 84: "7YR", 120: "10YR",
}


# Map a quadrant label to a human-friendly display string.
QUADRANT_DISPLAY = {
    "high_val_high_stress": "High Valuation × High Stress",
    "high_val_low_stress": "High Valuation × Low Stress",
    "low_val_high_stress": "Low Valuation × High Stress",
    "low_val_low_stress": "Low Valuation × Low Stress",
}


VARIANT_LABEL = {
    "yc_10y3m": "Yield Curve 10Y-3M",
    "yc_10y2y": "Yield Curve 10Y-2Y",
    "cs_hy_master": "HY OAS (master)",
    "cs_ig_master": "IG OAS (master)",
    "cs_hy_bb": "HY BB OAS",
    "cs_hy_ccc": "HY CCC OAS",
    "margin_debt_growth": "Margin Debt 12M Growth",
    "mrc": "MV Macro Risk Composite",
}


def _classify_regime(z: float) -> tuple[str, str]:
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


def _load_dual_frame_summary(variant_key: str) -> pd.DataFrame:
    pq = Path(f"outputs/indicators/{variant_key}/dual_frame_summary.parquet")
    if not pq.exists():
        return pd.DataFrame()
    return pd.read_parquet(pq)


def _regression_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Per-horizon rows (long_run frame) for the regression table."""
    if df.empty:
        return []
    sub = df[df["frame"] == "long_run"].copy()
    if "horizon_months" not in sub.columns:
        return []
    sub = sub.dropna(subset=["horizon_months"])
    sub["horizon_months"] = sub["horizon_months"].astype(int)
    sub = sub.set_index("horizon_months").reindex(HORIZON_ORDER).dropna(how="all")
    rows = []
    for h, row in sub.iterrows():
        rows.append(
            {
                "horizon_label": HORIZON_LABEL[h],
                "beta_fmt": _fmt_signed(row.get("beta_hat")),
                "se_hh_fmt": _fmt_signed(row.get("se_hh"), digits=3),
                "t_hh_fmt": _fmt_signed(row.get("t_hh")),
                "p_fmt": f"{row.get('p_nw', float('nan')):.3f}"
                if np.isfinite(row.get("p_nw", float("nan")))
                else "n/a",
                "r2_in_fmt": f"{row.get('r2_in', float('nan')):.3f}"
                if np.isfinite(row.get("r2_in", float("nan")))
                else "n/a",
                "r2_oos_fmt": f"{row.get('r2_oos_gw', float('nan')):.3f}"
                if np.isfinite(row.get("r2_oos_gw", float("nan")))
                else "n/a",
                "n_obs": int(row.get("n_observations", 0)),
                "conviction_fmt": f"{row.get('conviction', float('nan')):.2f}"
                if np.isfinite(row.get("conviction", float("nan")))
                else "n/a",
            }
        )
    return rows


def _probability_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Per-horizon probability table rows (placeholder fills until probability
    columns are persisted; for now we surface P(neg) and an empty CI95."""
    if df.empty:
        return []
    sub = df[df["frame"] == "long_run"].copy()
    sub = sub.dropna(subset=["horizon_months"]).copy()
    sub["horizon_months"] = sub["horizon_months"].astype(int)
    sub = sub.set_index("horizon_months").reindex(HORIZON_ORDER).dropna(how="all")
    rows = []
    for h, row in sub.iterrows():
        p_neg = row.get("p_neg_return")
        rows.append(
            {
                "horizon_label": HORIZON_LABEL[h],
                "p_neg_fmt": _fmt_pct(p_neg, digits=0),
                "p_neg_ci_fmt": "",
                "p_below_rf_fmt": "—",
                "p_below_5_fmt": "—",
                "p_above_7_fmt": "—",
            }
        )
    return rows


def _build_indicator_block(variant_key: str) -> dict[str, Any] | None:
    df = _load_dual_frame_summary(variant_key)
    if df.empty:
        return None
    # Long-run headline row (latest z lives at frame==long_run, horizon=null).
    lr = df[df["frame"] == "long_run"].copy()
    if lr.empty:
        return None
    head = lr.iloc[0]
    z = float(head.get("z_score", float("nan")))
    regime, color = _classify_regime(z)
    # Pull P(neg 10Y) from the long-run 120m row.
    p_neg_10y = float("nan")
    h120 = lr[lr["horizon_months"] == 120]
    if not h120.empty:
        p_neg_10y = float(h120.iloc[0].get("p_neg_return", float("nan")))
    # Conviction at 10Y horizon.
    conviction_10y = float("nan")
    if not h120.empty:
        conviction_10y = float(h120.iloc[0].get("conviction", float("nan")))
    return {
        "variant_key": variant_key,
        "label": VARIANT_LABEL.get(variant_key, variant_key),
        "regime": regime,
        "regime_color": color,
        "z_fmt": _fmt_signed(z, suffix="σ"),
        "p_neg_fmt": _fmt_pct(p_neg_10y),
        "p_neg_ci_fmt": "",
        "confidence_fmt": _fmt_pct(head.get("confidence_pct", 0) / 100.0)
        if head.get("confidence_pct") is not None
        else "n/a",
        "conviction_fmt": f"{conviction_10y:.2f}"
        if np.isfinite(conviction_10y)
        else "n/a",
        "interpretation": {
            "why_it_matters": WHY_IT_MATTERS.get(variant_key, ""),
            "panel_a": PANEL_A_CAPTIONS.get(variant_key, ""),
        },
        "regression_rows": _regression_rows(df),
        "probability_rows": _probability_rows(df),
    }


def _build_mrc_block() -> dict[str, Any] | None:
    """Assemble the MRC tab context, including cross-variant comparison table
    and quadrant-conditional forward returns."""
    # Equal-weight is the headline scheme.
    block = _build_indicator_block("mrc_equal_weight")
    if block is None:
        return None
    block["variant_key"] = "mrc"
    block["label"] = "MV Macro Risk Composite"
    block["interpretation"] = {
        "why_it_matters": WHY_IT_MATTERS.get("mrc", ""),
        "panel_a": PANEL_A_CAPTIONS.get("mrc", ""),
    }

    # Cross-variant table: equal_weight, inv_variance, pca_pc1 headline rows.
    mrc_rows = []
    for scheme, label in (
        ("mrc_equal_weight", "Equal weight"),
        ("mrc_inv_variance", "Inverse variance"),
        ("mrc_pca_pc1", "PCA PC1"),
    ):
        sub = _load_dual_frame_summary(scheme)
        if sub.empty:
            continue
        head = sub[sub["frame"] == "long_run"].iloc[0]
        z = float(head.get("z_score", float("nan")))
        h120 = sub[(sub["frame"] == "long_run") & (sub["horizon_months"] == 120)]
        p_neg = float(h120.iloc[0].get("p_neg_return", float("nan"))) if not h120.empty else float("nan")
        conv = float(h120.iloc[0].get("conviction", float("nan"))) if not h120.empty else float("nan")
        mrc_rows.append(
            {
                "scheme_label": label,
                "z_fmt": _fmt_signed(z, suffix="σ"),
                "p_neg_fmt": _fmt_pct(p_neg),
                "p_neg_ci_fmt": "",
                "confidence_fmt": _fmt_pct(head.get("confidence_pct", 0) / 100.0),
                "conviction_fmt": f"{conv:.2f}" if np.isfinite(conv) else "n/a",
            }
        )
    block["mrc_variants"] = mrc_rows

    # Cross-composite current state.
    cc_path = Path("outputs/cross_composite/current_state.json")
    if cc_path.exists():
        state = json.loads(cc_path.read_text())
        quadrant_label = QUADRANT_DISPLAY.get(state["quadrant"], state["quadrant"])
        # Conditional forward return for this quadrant.
        summary_path = Path("outputs/cross_composite/mvci_mrc_quadrant_summary.parquet")
        mean_ret_fmt = ""
        n_months = 0
        if summary_path.exists():
            qsum = pd.read_parquet(summary_path)
            if state["quadrant"] in qsum.index:
                row = qsum.loc[state["quadrant"]]
                mean_ret_fmt = _fmt_pct(row.get("mean"))
                n_months = int(row.get("n_months", 0))
        block["cross_composite_current"] = {
            "quadrant": state["quadrant"],
            "quadrant_label": quadrant_label,
            "mean_ret_fmt": mean_ret_fmt,
            "n_months": n_months,
        }
    return block


def build_macro_variants() -> dict[str, Any]:
    """Return a dict keyed by variant_key with each tab's render context."""
    out: dict[str, Any] = {}
    for vk in (
        "yc_10y3m",
        "yc_10y2y",
        "cs_hy_master",
        "cs_ig_master",
        "cs_hy_bb",
        "cs_hy_ccc",
        "margin_debt_growth",
    ):
        b = _build_indicator_block(vk)
        if b is not None:
            out[vk] = b
    mrc_block = _build_mrc_block()
    if mrc_block is not None:
        out["mrc"] = mrc_block
    return out


def build_macro_risk_snapshot(
    macro_variants: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build the Overview tab's Macro Risk Snapshot context block."""
    if macro_variants is None:
        macro_variants = build_macro_variants()
    if "mrc" not in macro_variants:
        return None
    mrc = macro_variants["mrc"]

    # Sort the 7 constituents by |z| to pick top-3 contributors.
    contributors: list[dict[str, Any]] = []
    for vk in (
        "yc_10y3m",
        "yc_10y2y",
        "cs_hy_master",
        "cs_ig_master",
        "cs_hy_bb",
        "cs_hy_ccc",
        "margin_debt_growth",
    ):
        if vk not in macro_variants:
            continue
        df = _load_dual_frame_summary(vk)
        if df.empty:
            continue
        z_val = df[df["frame"] == "long_run"].iloc[0].get("z_score", float("nan"))
        if not np.isfinite(z_val):
            continue
        contributors.append(
            {
                "variant_key": vk,
                "label": VARIANT_LABEL.get(vk, vk),
                "abs_z_fmt": f"{abs(z_val):.2f}",
                "z_fmt": _fmt_signed(z_val, suffix="σ"),
                "abs_z_val": abs(float(z_val)),
            }
        )
    contributors.sort(key=lambda d: d["abs_z_val"], reverse=True)
    top3 = contributors[:3]
    for d in top3:
        d.pop("abs_z_val", None)

    out: dict[str, Any] = {
        "regime": mrc["regime"],
        "regime_color": mrc["regime_color"],
        "z_fmt": mrc["z_fmt"],
        "p_neg_fmt": mrc["p_neg_fmt"],
        "p_neg_ci_fmt": mrc["p_neg_ci_fmt"],
        "confidence_fmt": mrc["confidence_fmt"],
        "conviction_fmt": mrc["conviction_fmt"],
        "top_contributors": top3,
    }
    # Cross-composite state.
    cc_path = Path("outputs/cross_composite/current_state.json")
    if cc_path.exists():
        state = json.loads(cc_path.read_text())
        out["quadrant"] = state["quadrant"]
        out["quadrant_label"] = QUADRANT_DISPLAY.get(state["quadrant"], state["quadrant"])
        out["corr_fmt"] = _fmt_signed(state.get("corr_mvci_mrc"))
        # Mean forward return per quadrant.
        sp = Path("outputs/cross_composite/mvci_mrc_quadrant_summary.parquet")
        if sp.exists():
            qsum = pd.read_parquet(sp)
            if state["quadrant"] in qsum.index:
                row = qsum.loc[state["quadrant"]]
                out["mean_forward_ret_fmt"] = _fmt_pct(row.get("mean"))
                out["quadrant_n_months"] = int(row.get("n_months", 0))
    return out


__all__ = [
    "build_macro_variants",
    "build_macro_risk_snapshot",
]
