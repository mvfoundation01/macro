"""Load orchestrator outputs and assemble the dashboard data dict."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.viz.captions import REGIME_COLORS, all_captions_for
from src.viz.chart_specs import (
    make_hero_chart,
    make_mean_reversion_hero,
    make_panel_a,
    make_panel_b,
    make_panel_c,
    make_pca_loadings_bar,
    make_sparkline,
)


# ---------------------------------------------------------------------------
# Headline loader
# ---------------------------------------------------------------------------


def load_headline(headline_path: Path) -> dict[str, Any]:
    with open(headline_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # headline.json contains {"headline": {...}, "backtest_view": {...}}.
    return data.get("headline", data)


def load_chart_parquets(charts_dir: Path) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for fname in (
        "z_history.parquet",
        "value_history.parquet",
        "sp500_with_regime.parquet",
        "scatter_data.parquet",
    ):
        path = charts_dir / fname
        if path.exists():
            df = pd.read_parquet(path)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            key = fname.replace(".parquet", "")
            out[key] = df
    return out


# ---------------------------------------------------------------------------
# Variant chart-spec builder
# ---------------------------------------------------------------------------


def build_variant_charts(
    variant_key: str,
    z_history: pd.DataFrame | None,
    sp500_df: pd.DataFrame | None,
    scatter_df: pd.DataFrame | None,
    regression: dict[str, float],
    current_z: float,
    horizon: int = 120,
) -> dict[str, Any]:
    """Build the 3 Plotly specs (Panels A/B/C) for one variant."""
    panel_a_spec: dict[str, Any] | None = None
    panel_b_spec: dict[str, Any] | None = None
    panel_c_spec: dict[str, Any] | None = None

    if z_history is not None and not z_history.empty:
        mask = (z_history["variant"] == variant_key) & (z_history["frame"] == "long_run")
        sub = z_history[mask]
        if not sub.empty:
            z_series = pd.Series(
                sub["z_score"].astype("float64").values,
                index=pd.DatetimeIndex(sub["date"]),
                name=f"{variant_key}_z",
            )
            panel_a_spec = make_panel_a(
                z_series, title=f"{variant_key} z-score (long-run)"
            )

    if scatter_df is not None and not scatter_df.empty:
        sub = scatter_df[scatter_df["variant"] == variant_key]
        col = f"forward_{horizon}m_cagr"
        if not sub.empty and col in sub.columns:
            panel_b_spec = make_panel_b(
                sub[["date", "z_score_long_run", col]].rename(
                    columns={col: col}
                ),
                current_z=current_z,
                regression=regression,
                title=f"{variant_key} z-score vs {horizon // 12}Y forward CAGR",
                horizon_col=col,
            )

    if sp500_df is not None and not sp500_df.empty:
        panel_c_spec = make_panel_c(sp500_df)

    return {
        "panel_a": panel_a_spec,
        "panel_b": panel_b_spec,
        "panel_c": panel_c_spec,
        "captions": all_captions_for(variant_key),
    }


def build_sparkline_for(variant_key: str, z_history: pd.DataFrame | None) -> dict[str, Any]:
    if z_history is None or z_history.empty:
        return {"data": [], "layout": {}}
    mask = (z_history["variant"] == variant_key) & (z_history["frame"] == "long_run")
    sub = z_history[mask]
    if sub.empty:
        return {"data": [], "layout": {}}
    s = pd.Series(
        sub["z_score"].astype("float64").values, index=pd.DatetimeIndex(sub["date"])
    )
    return make_sparkline(s)


# ---------------------------------------------------------------------------
# Aggregate builder
# ---------------------------------------------------------------------------


_DASHBOARD_VARIANTS = (
    "mvci",
    "bi_allequity_pct",
    "bi_wilshire_pct",
    "bi_spx_proxy",
    "cape",
    "qratio",
    "ey_deficit",
    "mean_reversion",
)
_OVERVIEW_VARIANTS = (
    "bi_allequity_pct",
    "bi_wilshire_pct",
    "bi_spx_proxy",
    "cape",
    "qratio",
    "ey_deficit",
    "mean_reversion",
    "mvci",
)


def _extract_regression_h120(variant_entry: dict[str, Any]) -> dict[str, float]:
    """Pull (alpha, beta, t_nw, r_squared) out of the 10Y forward outlook."""
    try:
        h120 = variant_entry["long_run"]["forward_outlook"]["primary"]["h_120m"]
        if h120.get("available"):
            reg = h120["regression"]
            return {
                "alpha": float(reg["alpha"]),
                "beta": float(reg["beta"]),
                "t_nw": float(reg["t_nw"]),
                "r_squared": float(reg["r_squared"]),
            }
    except (KeyError, TypeError):
        pass
    return {"alpha": 0.0, "beta": 0.0, "t_nw": 0.0, "r_squared": 0.0}


def _z_series_for(z_history: pd.DataFrame, variant_key: str) -> pd.Series:
    """Pull the long-run z-score series for ``variant_key`` from z_history."""
    if z_history is None or z_history.empty:
        return pd.Series(dtype="float64")
    mask = (z_history["variant"] == variant_key) & (z_history["frame"] == "long_run")
    sub = z_history[mask]
    if sub.empty:
        return pd.Series(dtype="float64")
    return pd.Series(
        sub["z_score"].astype("float64").values,
        index=pd.DatetimeIndex(sub["date"]),
        name=f"{variant_key}_z",
    )


def build_hero_specs(
    headline: dict[str, Any],
    z_history: pd.DataFrame | None,
    value_history: pd.DataFrame | None,
) -> dict[str, Any]:
    """Build the per-tab hero chart specs (Spec v8a.1 deliverable A).

    Returns a dict keyed by tab name (overview, mvci, buffett, cape,
    mean_reversion). Each value is either a Plotly figure spec dict, or
    None if the underlying data isn't available.

    For ``buffett`` the value is itself a dict keyed by sub-tab so the
    JS layer can pick the active sub-tab at render time.
    """
    import statsmodels.api as sm
    import numpy as np

    out: dict[str, Any] = {}

    mvci_z = _z_series_for(z_history, "mvci") if z_history is not None else pd.Series(dtype="float64")
    if not mvci_z.empty:
        hero = make_hero_chart(
            mvci_z,
            title="MV Composite Index (MVCI)",
        )
        out["mvci"] = hero
        # v8b.1 D bundle-size optimization: overview and mvci share the same
        # MVCI hero spec — sentinel-reference instead of inlining twice.
        out["overview"] = "__HERO_MVCI__"
    else:
        out["overview"] = None
        out["mvci"] = None

    cape_z = _z_series_for(z_history, "cape") if z_history is not None else pd.Series(dtype="float64")
    out["cape"] = (
        make_hero_chart(cape_z, title="CAPE / Shiller P/E10", chart_name="cape_hero")
        if not cape_z.empty
        else None
    )

    # v8b: Q-Ratio and EY-Deficit get dedicated hero charts too.
    qratio_z = _z_series_for(z_history, "qratio") if z_history is not None else pd.Series(dtype="float64")
    out["qratio"] = (
        make_hero_chart(qratio_z, title="Tobin's Q-Ratio", chart_name="qratio_hero")
        if not qratio_z.empty
        else None
    )

    ey_z = _z_series_for(z_history, "ey_deficit") if z_history is not None else pd.Series(dtype="float64")
    out["ey_deficit"] = (
        make_hero_chart(ey_z, title="Equity Yield Deficit", chart_name="ey_deficit_hero")
        if not ey_z.empty
        else None
    )

    buffett_subs: dict[str, Any] = {}
    for k in ("bi_allequity_pct", "bi_wilshire_pct", "bi_spx_proxy"):
        zs = _z_series_for(z_history, k) if z_history is not None else pd.Series(dtype="float64")
        if not zs.empty:
            label, _ = (
                ("Buffett (All Equity)", "%")
                if k == "bi_allequity_pct"
                else ("Buffett (Wilshire)", "%")
                if k == "bi_wilshire_pct"
                else ("Buffett (SPX proxy)", "%")
            )
            buffett_subs[k] = make_hero_chart(zs, title=label, chart_name=f"buffett_{k}_hero")
    out["buffett"] = buffett_subs or None

    # Mean Reversion: real S&P 500 + exp trend (log scale).
    mr_hero = None
    if value_history is not None and not value_history.empty:
        mr_mask = value_history["variant"] == "mean_reversion"
        mr_sub = value_history[mr_mask]
        if not mr_sub.empty:
            mr_series = pd.Series(
                mr_sub["value"].astype("float64").values,
                index=pd.DatetimeIndex(mr_sub["date"]),
                name="real_sp",
            ).dropna()
            mr_series = mr_series[mr_series > 0]
            if len(mr_series) >= 60:
                # Fit log-linear trend.
                log_y = np.log(mr_series.values)
                t = np.arange(len(log_y), dtype="float64")
                X = sm.add_constant(t)
                model = sm.OLS(log_y, X).fit()
                fitted_log = model.predict(X)
                trend = pd.Series(np.exp(fitted_log), index=mr_series.index)
                latest_ratio = float(mr_series.iloc[-1] / trend.iloc[-1])
                current_dev_pct = (latest_ratio - 1.0) * 100.0
                mr_hero = make_mean_reversion_hero(
                    real_sp_series=mr_series,
                    trend_series=trend,
                    current_deviation_pct=current_dev_pct,
                )
    out["mean_reversion"] = mr_hero

    return out


def assemble_dashboard_data(
    headline: dict[str, Any],
    parquets: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """Build the JSON payload embedded in dashboard.html."""
    z_history = parquets.get("z_history")
    sp500_df = parquets.get("sp500_with_regime")
    scatter_df = parquets.get("scatter_data")

    variants = headline.get("variants", {})

    # Per-variant chart specs.
    # v8b.1 D bundle-size optimization: Panel C (S&P 500 by MVCI regime) is
    # identical across every variant tab. Build it once and reference it via
    # a sentinel string so the JS layer can deduplicate.
    variant_specs: dict[str, Any] = {}
    sparklines: dict[str, Any] = {}
    for vkey in _DASHBOARD_VARIANTS:
        if vkey not in variants:
            continue
        current_z = float(variants[vkey].get("long_run", {}).get("z_score", 0.0))
        reg = _extract_regression_h120(variants[vkey])
        variant_specs[vkey] = build_variant_charts(
            vkey,
            z_history=z_history,
            sp500_df=sp500_df,
            scatter_df=scatter_df,
            regression=reg,
            current_z=current_z,
        )
        # Replace the duplicated panel_c with a pointer to the shared spec.
        if variant_specs[vkey].get("panel_c") is not None:
            variant_specs[vkey]["panel_c"] = "__SHARED_PANEL_C__"
    for vkey in _OVERVIEW_VARIANTS:
        if vkey in variants:
            sparklines[vkey] = build_sparkline_for(vkey, z_history)

    # MVCI PCA loadings (long_run frame) for the bar chart.
    # v8b.1 fix B.3: prefer loadings_full (raw PC1 eigenvector on balanced
    # panel) over weights_current (availability-rebased) so every variant
    # appears with non-zero contribution. weights_current would zero out
    # any variant that has NaN in the latest month — misleading display.
    mvci = variants.get("mvci", {})
    mvci_scheme = (
        mvci.get("long_run", {}).get("schemes", {}).get("pca_pc1", {})
    )
    mvci_pca = mvci_scheme.get("loadings_full") or mvci_scheme.get(
        "weights_current", {}
    )
    pca_loadings_chart = make_pca_loadings_bar(
        {
            k: float(v)
            for k, v in mvci_pca.items()
            if v is not None and not (isinstance(v, float) and v != v)  # drop NaN
        }
    )

    # Spec v8a.1: build hero chart specs per tab.
    hero_specs = build_hero_specs(
        headline,
        z_history=parquets.get("z_history"),
        value_history=parquets.get("value_history"),
    )

    # v8b.1 D bundle-size optimization: build Panel C once and share across
    # variants. Per-variant entries reference it via "__SHARED_PANEL_C__".
    shared_panel_c = None
    if sp500_df is not None and not sp500_df.empty:
        from src.viz.chart_specs import make_panel_c as _build_pc
        shared_panel_c = _build_pc(sp500_df)

    return {
        "asof": headline.get("asof"),
        "view": headline.get("view"),
        "interpretation": headline.get("interpretation", {}),
        "cross_variant_long_run": headline.get("cross_variant_long_run", {}),
        "cross_variant_current_regime": headline.get("cross_variant_current_regime", {}),
        "variants": variants,
        "variant_charts": variant_specs,
        "shared_panel_c": shared_panel_c,
        "sparklines": sparklines,
        "hero_specs": hero_specs,
        "mvci_pca_loadings_chart": pca_loadings_chart,
        "regime_colors": REGIME_COLORS,
    }


def parquet_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Compact records-style list for JSON embedding (dates -> isoformat)."""
    out: list[dict[str, Any]] = []
    for row in df.to_dict("records"):
        clean: dict[str, Any] = {}
        for k, v in row.items():
            if isinstance(v, pd.Timestamp):
                clean[k] = v.isoformat()
            elif hasattr(v, "item"):
                try:
                    clean[k] = v.item()
                except Exception:
                    clean[k] = v
            else:
                clean[k] = v
        out.append(clean)
    return out


__all__ = [
    "load_headline",
    "load_chart_parquets",
    "build_variant_charts",
    "build_sparkline_for",
    "assemble_dashboard_data",
    "parquet_to_records",
]
