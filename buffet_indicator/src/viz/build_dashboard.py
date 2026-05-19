"""Render outputs/dashboard.html from pipeline outputs (Spec v8b polish)."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import OUTPUTS_DIR
from src.viz.captions import (
    REGIME_COLORS,
    all_captions_for,
    all_interpretations_for,
)
from src.viz.data_extraction import (
    assemble_dashboard_data,
    load_chart_parquets,
    load_headline,
)


_TEMPLATE_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"


# ---------------------------------------------------------------------------
# Spec v8a.3: JSON sanitizer (preserves correctness of empty-chart fix)
# ---------------------------------------------------------------------------


def _clean_for_json(obj: Any) -> Any:
    """Replace NaN/Infinity with ``None`` and convert numpy types to native
    Python types so ``json.dumps`` emits strict, browser-parseable JSON."""
    if isinstance(obj, np.generic):
        try:
            obj = obj.item()
        except Exception:  # noqa: BLE001
            return None
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean_for_json(x) for x in obj]
    if isinstance(obj, np.ndarray):
        return _clean_for_json(obj.tolist())
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:  # noqa: BLE001
            pass
    return obj


# ---------------------------------------------------------------------------
# Number formatting helpers
# ---------------------------------------------------------------------------


def _fmt_z(z: float | None) -> str:
    if z is None or (isinstance(z, float) and (math.isnan(z) or math.isinf(z))):
        return "n/a"
    return f"{z:+.2f} σ"


def _fmt_pct(p: float | None, scale: int = 100, digits: int = 1) -> str:
    if p is None or (isinstance(p, float) and (math.isnan(p) or math.isinf(p))):
        return "n/a"
    return f"{p * scale:.{digits}f}%"


def _fmt_pct_already_percent(p: float | None, digits: int = 1) -> str:
    if p is None or (isinstance(p, float) and (math.isnan(p) or math.isinf(p))):
        return "n/a"
    return f"{p:.{digits}f}%"


def _fmt_float(x: float | None, digits: int = 2) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    return f"{x:.{digits}f}"


def _fmt_signed(x: float | None, digits: int = 4) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    return f"{x:+.{digits}f}"


def _headline_value_fmt(variant: dict[str, Any]) -> str:
    value = variant.get("headline_value")
    unit = variant.get("headline_unit", "")
    if value is None:
        return "n/a"
    if unit == "%":
        return f"{value:.2f}%"
    if unit == "sigma":
        return f"{value:+.2f} σ"
    return f"{value:.2f}"


# ---------------------------------------------------------------------------
# Template context builders
# ---------------------------------------------------------------------------


_SERIES_KEYS_TO_STRIP = {
    "z_score_series",
    "weights_history",
    "loadings_history",
    "trend_series",
    "fitted_series",
    "residuals",
    "z_history",
    "scatter_data",
    # v8b.1 D: sample distributions inside forward_outlook are large
    # (~7KB × 7 variants × 4 horizons × 3 robustness × 2 frames) and only
    # summary scalars (mean / quantile-based events) are read by the dashboard.
    "current_dist",
    "bucket_centers",
    "bucket_samples",
}


def _strip_series_for_json_viewer(obj: Any) -> Any:
    """Recursively drop large series fields from a headline-like dict.

    Used by the Data tab JSON viewer (v8b.1 D bundle-size optimization).
    Keeps the structural shape but replaces each stripped value with the
    placeholder ``"<series omitted from viewer — download CSV instead>"``.
    """
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k in _SERIES_KEYS_TO_STRIP:
                out[k] = "<series omitted from viewer — download CSV instead>"
            else:
                out[k] = _strip_series_for_json_viewer(v)
        return out
    if isinstance(obj, list):
        return [_strip_series_for_json_viewer(x) for x in obj]
    return obj


def _slim_variants_for_inline(variants: dict[str, Any]) -> dict[str, Any]:
    """Slim the embedded `variants` payload — drop heavy fields not used by JS.

    The dashboard runtime only reads scalar headline values
    (z_score / regime / forward_outlook scalars / regression / full_conviction)
    from ``DATA.variants``. Sample distributions, full z-score series, and PCA
    weight histories are not consumed and can be safely stripped to shrink
    the inline JSON payload.
    """
    return _strip_series_for_json_viewer(variants)


def _safe_get(d: dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def _build_header_context(headline: dict[str, Any]) -> dict[str, Any]:
    mvci = headline.get("variants", {}).get("mvci", {})
    lr = mvci.get("long_run", {})
    regime = lr.get("regime", "Insufficient Data")
    regime_color = REGIME_COLORS.get(regime, "#000000")
    z_score = lr.get("z_score")

    h120 = _safe_get(lr, "forward_outlook", "primary", "h_120m") or {}
    p_below5 = _safe_get(h120, "probabilities", "events", "P_below_5pct", "point")
    confidence = lr.get("confidence_pct")
    conviction = _safe_get(lr, "full_conviction", "h_120m", "score")

    return {
        "asof_label": str(headline.get("asof", "n/a"))[:10],
        "regime_label": regime,
        "regime_color": regime_color,
        "mvci_z_fmt": _fmt_z(z_score),
        "p_below5_fmt": _fmt_pct(p_below5) if p_below5 is not None else "n/a",
        "confidence_fmt": _fmt_pct(
            (confidence / 100.0) if confidence is not None else None
        ),
        "conviction_fmt": _fmt_float(conviction, digits=2),
    }


def _build_overview_context(headline: dict[str, Any]) -> dict[str, Any]:
    variants = headline.get("variants", {})
    # v8b: every variant has its own tab now — no more "coming soon" cards.
    order = (
        ("mvci", "mvci"),
        ("bi_allequity_pct", "buffett"),
        ("bi_wilshire_pct", "buffett"),
        ("bi_spx_proxy", "buffett"),
        ("cape", "cape"),
        ("qratio", "qratio"),
        ("ey_deficit", "ey_deficit"),
        ("mean_reversion", "mean_reversion"),
    )
    cards = []
    for vkey, target in order:
        if vkey not in variants:
            continue
        v = variants[vkey]
        lr = v.get("long_run", {})
        regime = lr.get("regime", "Insufficient Data")
        cards.append(
            {
                "variant_key": vkey,
                "label": v.get("headline_label", vkey),
                "value_fmt": _headline_value_fmt(v),
                "z_fmt": _fmt_z(lr.get("z_score")),
                "percentile_fmt": (
                    f"{lr['empirical_percentile']:.0f}th pct"
                    if "empirical_percentile" in lr
                    else "n/a"
                ),
                "regime": regime,
                "regime_color": REGIME_COLORS.get(regime, "#000000"),
                "tab_target": target,
            }
        )

    # Hero interpretation (uses MVCI values)
    mvci_v = variants.get("mvci", {})
    mvci_lr = mvci_v.get("long_run", {})
    hero_interp = all_interpretations_for(
        "mvci",
        z=mvci_lr.get("z_score"),
        percentile=mvci_lr.get("empirical_percentile"),
        regime=mvci_lr.get("regime", "Insufficient Data"),
    )

    xv = headline.get("cross_variant_long_run", {})
    return {
        "overview_cards": cards,
        "xv_mean_z_fmt": _fmt_float(xv.get("mean_z"), digits=2),
        "xv_agreement_fmt": _fmt_float(xv.get("agreement"), digits=2),
        "xv_combined_regime": xv.get("combined_regime", "n/a"),
        "xv_same_sign": "Yes" if xv.get("same_sign") else "No",
        "interpretation_narrative": _safe_get(
            headline, "interpretation", "narrative", default=""
        ),
        "interpretation_code": _safe_get(
            headline, "interpretation", "narrative_code", default="n/a"
        ),
        "hero_interpretation": hero_interp["hero"],
        "why_mvci": hero_interp["why_it_matters"],
    }


def _build_variant_block(headline: dict[str, Any], vkey: str) -> dict[str, Any]:
    v = headline.get("variants", {}).get(vkey, {})
    lr = v.get("long_run", {})
    h120 = _safe_get(lr, "forward_outlook", "primary", "h_120m") or {}
    reg = h120.get("regression") or {}
    oos = _safe_get(h120, "oos", "goyal_welch") or {}
    events = _safe_get(h120, "probabilities", "events") or {}
    bay = h120.get("bayesian") or {}
    fc = _safe_get(lr, "full_conviction", "h_120m") or {}

    captions = all_captions_for(vkey)
    regime = lr.get("regime", "Insufficient Data")
    z = lr.get("z_score")
    percentile = lr.get("empirical_percentile")
    value = v.get("headline_value")
    beta = reg.get("beta")
    r_squared = reg.get("r_squared")
    t_nw = reg.get("t_nw")

    interpretations = all_interpretations_for(
        vkey,
        value=value,
        z=z,
        percentile=percentile,
        regime=regime,
        beta=beta,
        r_squared=r_squared,
        t_nw=t_nw,
        buffett_label=v.get("headline_label", ""),
    )

    block: dict[str, Any] = {
        "variant_key": vkey,
        "label": v.get("headline_label", vkey),
        "value_fmt": _headline_value_fmt(v),
        "z_fmt": _fmt_z(z),
        "pct_fmt": (
            f"{percentile:.1f}th pct" if percentile is not None else "n/a"
        ),
        "regime": regime,
        "regime_color": REGIME_COLORS.get(regime, "#000000"),
        "confidence_fmt": (
            _fmt_pct(lr["confidence_pct"] / 100.0)
            if "confidence_pct" in lr
            else "n/a"
        ),
        "captions": captions,
        "interpretation": interpretations,
        "beta_fmt": _fmt_signed(beta),
        "se_nw_fmt": _fmt_signed(reg.get("beta_se_nw")),
        "t_nw_fmt": _fmt_signed(t_nw, digits=2),
        "beta_stambaugh_fmt": _fmt_signed(reg.get("beta_stambaugh")),
        "r2_in_fmt": _fmt_float(r_squared, digits=3),
        "r2_oos_fmt": _fmt_float(oos.get("r2_oos"), digits=3),
        "conviction_fmt": _fmt_float(fc.get("score"), digits=2),
    }

    p_neg = events.get("P_neg_return", {})
    p_below5 = events.get("P_below_5pct", {})
    p_above7 = events.get("P_above_7pct", {})
    block.update(
        {
            "p_neg_fmt": _fmt_pct(p_neg.get("point")),
            "p_neg_lo_fmt": _fmt_pct(_safe_get(p_neg, "ci95")[0]) if p_neg.get("ci95") else "n/a",
            "p_neg_hi_fmt": _fmt_pct(_safe_get(p_neg, "ci95")[1]) if p_neg.get("ci95") else "n/a",
            "p_below5_fmt": _fmt_pct(p_below5.get("point")),
            "p_below5_lo_fmt": _fmt_pct(_safe_get(p_below5, "ci95")[0]) if p_below5.get("ci95") else "n/a",
            "p_below5_hi_fmt": _fmt_pct(_safe_get(p_below5, "ci95")[1]) if p_below5.get("ci95") else "n/a",
            "p_above7_fmt": _fmt_pct(p_above7.get("point")),
            "bayes_mean_fmt": _fmt_pct(bay.get("posterior_mean")) if bay else "n/a",
            "bayes_lo_fmt": _fmt_pct(bay.get("ci95")[0]) if bay.get("ci95") else "n/a",
            "bayes_hi_fmt": _fmt_pct(bay.get("ci95")[1]) if bay.get("ci95") else "n/a",
        }
    )

    if vkey == "mvci":
        schemes = lr.get("schemes", {})
        rows = []
        for name in ("equal_weight", "inv_variance", "pca_pc1"):
            s = schemes.get(name, {})
            note = ""
            if name == "equal_weight":
                note = "Default (headline)"
            elif name == "pca_pc1":
                ev = s.get("explained_variance")
                if ev is not None:
                    note = f"PC1 explains {ev * 100:.1f}% variance"
            rows.append(
                {
                    "name": name.replace("_", " "),
                    "z_fmt": _fmt_z(s.get("z_score")),
                    "note": note,
                }
            )
        block["schemes_table"] = rows
        components = fc.get("components", {}) if fc else {}
        block["conviction_score_fmt"] = _fmt_float(fc.get("score"), digits=2)
        block["conviction_components"] = [
            {"name": name.replace("_", " "), "value_fmt": _fmt_float(val, digits=3)}
            for name, val in components.items()
        ]

    return block


def _build_buffett_context(headline: dict[str, Any]) -> dict[str, Any]:
    sub_keys = ("bi_allequity_pct", "bi_wilshire_pct", "bi_spx_proxy")
    subs = []
    for k in sub_keys:
        if k in headline.get("variants", {}):
            block = _build_variant_block(headline, k)
            block["key"] = k
            subs.append(block)
    return {"buffett_subtabs": subs}


# ---------------------------------------------------------------------------
# v8b: Diagnostics context (statistical health metrics)
# ---------------------------------------------------------------------------


def _build_diagnostics_context(
    headline: dict[str, Any],
    parquets: dict[str, pd.DataFrame],
    charts_dir: Path,
) -> dict[str, Any]:
    """Read the v8b diagnostics parquets and build template context.

    Diagnostics are persisted by ``src.models.diagnostics.emit_diagnostics``;
    this function consumes those files and falls back to live computation if
    they're missing (e.g. during dev when only the 4 standard parquets exist).
    """
    z_history = parquets.get("z_history")
    stationarity_rows: list[dict[str, Any]] = []
    corr_matrix: pd.DataFrame | None = None
    oos_evolution: pd.DataFrame | None = None

    stat_path = charts_dir / "diagnostics_stationarity.parquet"
    corr_path = charts_dir / "diagnostics_correlation_matrix.parquet"
    oos_path = charts_dir / "diagnostics_oos_r2_evolution.parquet"

    # ---- Stationarity ----
    stat_df: pd.DataFrame | None = None
    if stat_path.exists():
        try:
            stat_df = pd.read_parquet(stat_path)
        except Exception:  # noqa: BLE001
            stat_df = None
    if stat_df is None or stat_df.empty:
        try:
            from src.models.diagnostics import compute_stationarity
            stat_df = compute_stationarity(z_history if z_history is not None else pd.DataFrame())
        except Exception:  # noqa: BLE001
            stat_df = pd.DataFrame()

    if stat_df is not None and not stat_df.empty:
        for _, row in stat_df.iterrows():
            if row.get("frame") != "long_run":
                continue
            adf_p = float(row.get("adf_pvalue", float("nan")))
            kpss_p = float(row.get("kpss_pvalue", float("nan")))
            pp_p = float(row.get("pp_pvalue", float("nan")))
            za_p = float(row.get("za_pvalue", float("nan")))
            adf_pass = (not math.isnan(adf_p)) and adf_p < 0.05
            kpss_pass = (not math.isnan(kpss_p)) and kpss_p > 0.05
            pp_pass = (not math.isnan(pp_p)) and pp_p < 0.05
            za_pass = (not math.isnan(za_p)) and za_p < 0.05
            # v8b.1 spec A.1: PASS iff at least 2 of the 4 tests agree on
            # stationarity (each test has different power profile against
            # different alternatives, so agreement strengthens the signal).
            n_pass = sum([adf_pass, kpss_pass, pp_pass, za_pass])
            stationarity_rows.append(
                {
                    "variant": row["variant"],
                    "n_obs": int(row.get("n_obs", 0)),
                    "adf_p_fmt": f"{adf_p:.3f}" if not math.isnan(adf_p) else "n/a",
                    "adf_pass": adf_pass,
                    "kpss_p_fmt": f"{kpss_p:.3f}" if not math.isnan(kpss_p) else "n/a",
                    "kpss_pass": kpss_pass,
                    "pp_p_fmt": f"{pp_p:.3f}" if not math.isnan(pp_p) else "n/a",
                    "pp_pass": pp_pass,
                    "za_p_fmt": f"{za_p:.3f}" if not math.isnan(za_p) else "n/a",
                    "za_pass": za_pass,
                    "overall_pass": n_pass >= 2,
                }
            )

    # ---- Correlation ----
    if corr_path.exists():
        try:
            corr_matrix = pd.read_parquet(corr_path)
            if corr_matrix.empty:
                corr_matrix = None
        except Exception:  # noqa: BLE001
            corr_matrix = None
    if corr_matrix is None and z_history is not None and not z_history.empty:
        try:
            from src.models.diagnostics import compute_correlation_matrix
            corr_matrix = compute_correlation_matrix(z_history)
            if corr_matrix is not None and corr_matrix.empty:
                corr_matrix = None
        except Exception:  # noqa: BLE001
            corr_matrix = None

    # ---- OOS R² evolution ----
    if oos_path.exists():
        try:
            oos_evolution = pd.read_parquet(oos_path)
        except Exception:  # noqa: BLE001
            oos_evolution = None

    # ---- PCA explained variance from headline ----
    mvci_pca = (
        headline.get("variants", {})
        .get("mvci", {})
        .get("long_run", {})
        .get("schemes", {})
        .get("pca_pc1", {})
    )
    pc1_explained = mvci_pca.get("explained_variance")

    # ---- v8b.1 A.2: Bai-Perron break dates ----
    break_dates_rows: list[dict[str, Any]] = []
    bd_path = charts_dir / "diagnostics_break_dates.parquet"
    if bd_path.exists():
        try:
            bd_df = pd.read_parquet(bd_path)
            for variant, sub in bd_df.groupby("variant"):
                breaks = []
                for _, row in sub.iterrows():
                    breaks.append(
                        {
                            "break_idx": int(row["break_idx"]),
                            "break_date_fmt": pd.Timestamp(row["break_date"]).strftime(
                                "%Y-%m"
                            ),
                            "ci_lower_fmt": pd.Timestamp(row["ci_lower"]).strftime("%Y-%m"),
                            "ci_upper_fmt": pd.Timestamp(row["ci_upper"]).strftime("%Y-%m"),
                        }
                    )
                break_dates_rows.append({"variant": variant, "breaks": breaks})
        except Exception:  # noqa: BLE001
            break_dates_rows = []

    # ---- v8b.1 A.3: residuals (for ACF/PACF) ----
    residuals: pd.Series | None = None
    res_path = charts_dir / "diagnostics_mvci_residuals.parquet"
    if res_path.exists():
        try:
            res_df = pd.read_parquet(res_path)
            if not res_df.empty and "residual" in res_df.columns:
                residuals = res_df["residual"].astype("float64")
        except Exception:  # noqa: BLE001
            residuals = None

    # ---- v8b.1 A.4: calibration metrics ----
    calib_dict: dict[str, Any] | None = None
    calib_path = charts_dir.parent / "tables" / "calibration_metrics.json"
    if calib_path.exists():
        try:
            calib_dict = json.loads(calib_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            calib_dict = None

    calibration_summary: dict[str, str] | None = None
    if calib_dict and calib_dict.get("available"):
        calibration_summary = {
            "brier_fmt": f"{calib_dict['brier_score']:.3f}",
            "reliability_fmt": f"{calib_dict['reliability']:.3f}",
            "resolution_fmt": f"{calib_dict['resolution']:.3f}",
            "uncertainty_fmt": f"{calib_dict['uncertainty']:.3f}",
            "n_obs": str(calib_dict.get("n_observations", "?")),
        }

    return {
        "stationarity_rows": stationarity_rows,
        "corr_matrix": corr_matrix,
        "oos_evolution": oos_evolution,
        "break_dates_rows": break_dates_rows,
        "residuals": residuals,
        "calibration_dict": calib_dict,
        "calibration_summary": calibration_summary,
        "pc1_explained_fmt": (
            f"{pc1_explained * 100:.1f}%" if pc1_explained is not None else "n/a"
        ),
    }


# ---------------------------------------------------------------------------
# v8b: Data tab context (CSV exports + bibliography)
# ---------------------------------------------------------------------------


def _build_data_context(
    headline: dict[str, Any],
    parquets: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """Inline CSV strings for client-side downloads + data-source bibliography.

    v8b.1 D — bundle size: scatter_data CSV (~1.5 MB) and z_history CSV (~1 MB)
    are the dominant byte contributors. We keep z_history + value_history +
    sp500_with_regime fully inlined (≤ 1 MB combined) and store
    scatter_data lazily — surfaced as a thin pointer that triggers an
    on-demand re-CSV from the inline JSON variant arrays instead of pre-stringifying.
    """
    csv_exports: dict[str, str] = {}

    for key, df in parquets.items():
        if df is None or df.empty:
            continue
        # Skip the largest export to keep bundle below the 8 MB target.
        # scatter_data is reconstructible from variant_charts panel B data,
        # which is already inlined; users can rebuild the CSV via the JSON viewer.
        if key == "scatter_data":
            continue
        try:
            csv_exports[key] = df.to_csv(index=False)
        except Exception:  # noqa: BLE001
            continue

    # v8b.1 D — strip large series arrays from the headline-JSON viewer.
    # The dashboard chart layer carries the actual time-series data; the
    # viewer is a structured-record viewer, not a data export. Series fields
    # remain available via the per-parquet CSV downloads.
    try:
        slim = _strip_series_for_json_viewer(headline)
        headline_json_str = json.dumps(slim, default=str, indent=2)
    except Exception:  # noqa: BLE001
        headline_json_str = "{}"

    # Bibliography of data sources used (curated)
    bibliography = [
        {
            "name": "Robert Shiller's data archive",
            "url": "http://www.econ.yale.edu/~shiller/data.htm",
            "what": "Long-run S&P 500 price, dividends, earnings, CPI (1871+)",
            "used_for": "CAPE, Mean Reversion, SPX spliced series",
        },
        {
            "name": "Federal Reserve Z.1 Financial Accounts",
            "url": "https://www.federalreserve.gov/releases/z1/",
            "what": "Nonfinancial corporate equity and asset replacement values",
            "used_for": "Tobin's Q-Ratio, Buffett (All-Equity)",
        },
        {
            "name": "FRED — Federal Reserve Economic Data",
            "url": "https://fred.stlouisfed.org/",
            "what": "GDP, real 10Y Treasury yield, Wilshire 5000, CPI updates",
            "used_for": "Buffett (Wilshire), Equity Yield Deficit, inflation adjustment",
        },
        {
            "name": "Yahoo Finance",
            "url": "https://finance.yahoo.com/",
            "what": "Daily total-return-adjusted S&P 500 (^GSPCTR) for monthly forward returns",
            "used_for": "Forward-return targets in predictive regressions",
        },
        {
            "name": "Norgate Data (Diamond subscription)",
            "url": "https://norgatedata.com/",
            "what": "Survivorship-bias-free total return series back to 1900",
            "used_for": "Spliced primary forward-return series (Shiller × Norgate)",
        },
    ]

    return {
        "csv_exports": csv_exports,
        "headline_json_str": headline_json_str,
        "bibliography": bibliography,
    }


# ---------------------------------------------------------------------------
# Main build function
# ---------------------------------------------------------------------------


def _read_static(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def build_dashboard(
    headline_path: Path | None = None,
    charts_dir: Path | None = None,
    output_path: Path | None = None,
    template_dir: Path | None = None,
) -> Path:
    """Render the dashboard HTML and write it to ``output_path``."""
    if headline_path is None:
        headline_path = OUTPUTS_DIR / "tables" / "headline.json"
    if charts_dir is None:
        charts_dir = OUTPUTS_DIR / "charts"
    if output_path is None:
        output_path = OUTPUTS_DIR / "dashboard.html"
    if template_dir is None:
        template_dir = _TEMPLATE_DIR

    if not headline_path.exists():
        raise FileNotFoundError(
            f"Required headline.json not found at {headline_path}. "
            "Run `python -m src.cli model` first."
        )

    headline = load_headline(headline_path)
    parquets = load_chart_parquets(charts_dir)
    dashboard_data = assemble_dashboard_data(headline, parquets)

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    header_ctx = _build_header_context(headline)
    overview_ctx = _build_overview_context(headline)
    mvci_block = _build_variant_block(headline, "mvci")
    cape_block = _build_variant_block(headline, "cape")
    buffett_ctx = _build_buffett_context(headline)

    header_html = env.get_template("_header.html").render(**header_ctx)
    overview_html = env.get_template("tab_overview.html").render(**overview_ctx)
    mvci_html = env.get_template("tab_mvci.html").render(mvci=mvci_block)
    buffett_html = env.get_template("tab_buffett.html").render(**buffett_ctx)
    cape_html = env.get_template("tab_cape.html").render(cape=cape_block)

    # Mean Reversion tab (v8a.1). Build only if variant exists.
    variants = headline.get("variants", {})
    if "mean_reversion" in variants:
        mr_block = _build_variant_block(headline, "mean_reversion")
        mean_reversion_html = env.get_template("tab_mean_reversion.html").render(
            mr=mr_block
        )
    else:
        mean_reversion_html = ""

    # v8b: Q-Ratio dedicated tab
    if "qratio" in variants:
        q_block = _build_variant_block(headline, "qratio")
        qratio_html = env.get_template("tab_qratio.html").render(q=q_block)
    else:
        qratio_html = ""

    # v8b: EY-Deficit dedicated tab
    if "ey_deficit" in variants:
        ey_block = _build_variant_block(headline, "ey_deficit")
        ey_deficit_html = env.get_template("tab_ey_deficit.html").render(ey=ey_block)
    else:
        ey_deficit_html = ""

    # v8b: Diagnostics tab
    diag_ctx = _build_diagnostics_context(headline, parquets, charts_dir)
    diagnostics_html = env.get_template("tab_diagnostics.html").render(**diag_ctx)

    # v8b: Data tab
    data_ctx = _build_data_context(headline, parquets)
    data_html = env.get_template("tab_data.html").render(**data_ctx)

    # v8b: Methodology tab
    methodology_html = env.get_template("tab_methodology.html").render()

    inline_css = _read_static(_STATIC_DIR / "dashboard.css")
    inline_js = _read_static(_STATIC_DIR / "dashboard.js")

    # v8b.1 D bundle-size optimization: strip sample arrays / series from the
    # embedded variants dict before JSON serialization. The dashboard runtime
    # only reads scalar fields from DATA.variants; variant_charts carries the
    # plotting data.
    if "variants" in dashboard_data:
        dashboard_data["variants"] = _slim_variants_for_inline(
            dashboard_data["variants"]
        )

    # Spec v8a.3 sanitizer: scrub NaN/Infinity *before* serialization, then
    # ask json.dumps to refuse stragglers. Guarantees browser JSON.parse works.
    sanitized = _clean_for_json(dashboard_data)

    # v8b: pass diagnostics correlation matrix + OOS R² evolution as chart specs.
    corr_matrix = diag_ctx.get("corr_matrix")
    if corr_matrix is not None and not corr_matrix.empty:
        from src.viz.chart_specs import make_correlation_heatmap
        corr_spec = make_correlation_heatmap(corr_matrix)
        sanitized["diagnostics_correlation_chart"] = _clean_for_json(corr_spec)

    oos_df = diag_ctx.get("oos_evolution")
    if oos_df is not None and not oos_df.empty:
        from src.viz.chart_specs import make_oos_r2_chart
        oos_spec = make_oos_r2_chart(
            dates=[d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d) for d in oos_df["date"]],
            r2_values=[float(v) for v in oos_df["r2_oos"].astype("float64")],
        )
        sanitized["diagnostics_oos_r2_chart"] = _clean_for_json(oos_spec)

    # v8b.1 A.3 — ACF/PACF chart from residuals
    residuals = diag_ctx.get("residuals")
    if residuals is not None and not residuals.empty:
        from src.viz.chart_specs import make_acf_pacf_charts
        acf_spec = make_acf_pacf_charts(residuals)
        sanitized["diagnostics_acf_pacf_chart"] = _clean_for_json(acf_spec)

    # v8b.1 A.4 — calibration plot
    calib_dict = diag_ctx.get("calibration_dict")
    if calib_dict and calib_dict.get("available"):
        from src.viz.chart_specs import make_calibration_plot
        calib_spec = make_calibration_plot(
            buckets=calib_dict["buckets"],
            brier_score=calib_dict["brier_score"],
            reliability=calib_dict["reliability"],
            resolution=calib_dict["resolution"],
            uncertainty=calib_dict["uncertainty"],
        )
        sanitized["diagnostics_calibration_chart"] = _clean_for_json(calib_spec)

    # v8b: inline CSV exports in payload for client-side downloads.
    sanitized["csv_exports"] = data_ctx.get("csv_exports", {})
    sanitized["headline_json_str"] = data_ctx.get("headline_json_str", "{}")

    dashboard_json = json.dumps(
        sanitized, default=str, separators=(",", ":"), allow_nan=False
    )

    base = env.get_template("base.html")
    html = base.render(
        asof_label=header_ctx["asof_label"],
        header_html=header_html,
        tab_overview_html=overview_html,
        tab_mvci_html=mvci_html,
        tab_buffett_html=buffett_html,
        tab_cape_html=cape_html,
        tab_qratio_html=qratio_html,
        tab_ey_deficit_html=ey_deficit_html,
        tab_mean_reversion_html=mean_reversion_html,
        tab_diagnostics_html=diagnostics_html,
        tab_data_html=data_html,
        tab_methodology_html=methodology_html,
        inline_css=inline_css,
        inline_js=inline_js,
        dashboard_json=dashboard_json,
        build_timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


__all__ = ["build_dashboard"]
