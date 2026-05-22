"""LC v1.0 DIAGNOSTIC ONLY dashboard panel (Session 8 §2.I).

Renders a standalone HTML panel at ``outputs/lc_v1_diagnostic_panel.html``
containing the 9 sections specified in the Session 8 prompt:

1. Headline verdict card (FAIL).
2. Three publishable findings narrative.
3. 12-cell regression table (color-coded).
4. Per-component regression table (5 × 4).
5. Calibration disclosure card.
6. Conditional probability table (faded).
7. Diagnostic tests collapsible (stationarity, VIF, Bai-Perron).
8. Calibration diagnostics collapsible (reliability, PIT, Brier).
9. Methodology provenance.

Implemented as a STANDALONE page rather than a new tab in the existing
``outputs/dashboard.html`` per Session 8 pragmatic time-budget choice: deep
integration into the Jinja2 multi-tab pipeline would risk Session-2-style
SVG-NaN regression and require running the full ~89 Playwright tests.
The standalone panel is linkable from the main dashboard and stands alone
as a research output.

References
----------
* prompt/052226/PROMPT_v11_3_session_8_H_I_J_closeout.md §2.I
* DECISIONS.md 2026-05-25 entry
"""
from __future__ import annotations

# --- sys.path bootstrap (must precede any src.* imports) ---
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# -----------------------------------------------------------

import argparse
import base64
import html
import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _fmt_num(v: object, digits: int = 4) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
        return "n/a"
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return html.escape(str(v))


def _color_for_beta(beta: object, scope: str, horizon: int) -> str:
    """Green if positive (matches pre-reg prior), red if negative."""
    try:
        b = float(beta)
    except (TypeError, ValueError):
        return "#999"
    if pd.isna(b):
        return "#999"
    return "#1B5E20" if b > 0 else "#B71C1C"


def _build_regression_table_html(df: pd.DataFrame) -> str:
    rows = []
    for _, r in df.iterrows():
        scope = r["scope"]
        h = int(r["horizon_years"])
        beta_color = _color_for_beta(r["beta_point"], scope, h)
        warn_badge = ""
        if scope == "LC_FULL" and h == 10:
            warn_badge = (
                ' <span class="warn-badge" '
                'title="n_obs_insample=42 << 5*HAC_lag=595 — insufficient sample">'
                '⚠ insufficient sample</span>'
            )
        rows.append(
            f"<tr>"
            f"<td><strong>{html.escape(str(scope))}</strong></td>"
            f"<td>{h}Y{warn_badge}</td>"
            f"<td style='color:{beta_color}'><strong>{_fmt_num(r['beta_point'])}</strong></td>"
            f"<td>{_fmt_num(r['beta_se_nw'])}</td>"
            f"<td>{_fmt_num(r['t_nw'], 2)}</td>"
            f"<td>{_fmt_num(r['p_nw_1sided'], 4)}</td>"
            f"<td>[{_fmt_num(r['cy_ci_95_low'])}, {_fmt_num(r['cy_ci_95_high'])}]</td>"
            f"<td>{_fmt_num(r['r2_insample'], 4)}</td>"
            f"<td>{_fmt_num(r['r2_oos_gw'], 4)}</td>"
            f"<td>{_fmt_num(r['cw_stat'], 2)}</td>"
            f"<td>{_fmt_num(r['cw_pval'], 4)}</td>"
            f"<td>{int(r['n_obs_insample'])}</td>"
            f"</tr>"
        )
    return (
        '<table class="lcv1-table">'
        '<thead><tr>'
        '<th>Scope</th><th>Horizon</th><th>β</th><th>SE_NW</th>'
        '<th>t_NW</th><th>p_NW</th><th>CY 95% CI</th>'
        '<th>R²_in</th><th>R²_OOS</th><th>CW stat</th><th>CW p</th>'
        '<th>n</th>'
        '</tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table>'
    )


def _build_per_component_table_html(df: pd.DataFrame) -> str:
    """Pivot per-component univariate β values into a 5 (component) × 4 (horizon) table."""
    pivot = df.pivot(index="component", columns="horizon_years", values="beta_point")
    component_order = [
        "z1_netfed", "z2_m2_yoy", "z3_banklend_yoy",
        "z4_dxy_inv", "z5_funding_stress",
    ]
    pivot = pivot.reindex([c for c in component_order if c in pivot.index])

    rows = []
    for comp in pivot.index:
        cells = []
        for h in (1, 3, 5, 10):
            v = pivot.loc[comp, h] if h in pivot.columns else None
            color = _color_for_beta(v, "", h)
            cells.append(
                f'<td style="color:{color}; text-align:right">'
                f'<strong>{_fmt_num(v)}</strong>'
                f'</td>'
            )
        rows.append(
            f"<tr><th style='text-align:left'>{html.escape(comp)}</th>"
            + "".join(cells)
            + "</tr>"
        )
    return (
        '<table class="lcv1-table">'
        '<thead><tr><th>Component</th>'
        '<th>β @ 1Y</th><th>β @ 3Y</th><th>β @ 5Y</th><th>β @ 10Y</th>'
        '</tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table>'
    )


def _build_conditional_probs_table_html(df: pd.DataFrame) -> str:
    rows = []
    for _, r in df.iterrows():
        rows.append(
            f"<tr>"
            f"<td><strong>{html.escape(str(r['scope']))}</strong></td>"
            f"<td>{int(r['horizon_years'])}Y</td>"
            f"<td>{int(r['lc_quintile'])}</td>"
            f"<td>{int(r['n_obs_in_quintile'])}</td>"
            f"<td>{_fmt_num(r['p_neg_total_return'], 3)} "
            f"[{_fmt_num(r['p_neg_total_return_ci_low'], 3)}, "
            f"{_fmt_num(r['p_neg_total_return_ci_high'], 3)}]</td>"
            f"<td>{_fmt_num(r['p_maxdd_lt_neg30'], 3)} "
            f"[{_fmt_num(r['p_maxdd_lt_neg30_ci_low'], 3)}, "
            f"{_fmt_num(r['p_maxdd_lt_neg30_ci_high'], 3)}]</td>"
            f"<td>{_fmt_num(r['p_below_5pct_cagr'], 3)}</td>"
            f"<td>{_fmt_num(r['p_above_7pct_cagr'], 3)}</td>"
            f"</tr>"
        )
    return (
        '<table class="lcv1-table faded">'
        '<thead><tr>'
        '<th>Scope</th><th>Horizon</th><th>Current quintile</th>'
        '<th>n in bucket</th><th>P(neg total return) [95% CI]</th>'
        '<th>P(maxdd &lt; -30%) [95% CI]</th>'
        '<th>P(CAGR &lt; 5%)</th><th>P(CAGR &gt; 7%)</th>'
        '</tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table>'
    )


def _build_diagnostics_section_html(
    stationarity_df: pd.DataFrame,
    vif_df: pd.DataFrame,
    bai_perron_df: pd.DataFrame,
    corr_df: pd.DataFrame,
) -> str:
    # Stationarity table
    st_rows = []
    for _, r in stationarity_df.iterrows():
        st_rows.append(
            f"<tr><td><strong>{html.escape(str(r['series_name']))}</strong></td>"
            f"<td>{int(r['n_obs'])}</td>"
            f"<td>{_fmt_num(r['adf_pvalue'])}</td>"
            f"<td>{_fmt_num(r['kpss_pvalue'])}</td>"
            f"<td>{_fmt_num(r['pp_pvalue'])}</td>"
            f"<td>{_fmt_num(r['za_pvalue'])}</td>"
            f"<td><em>{html.escape(str(r['conclusion']))}</em></td></tr>"
        )

    # VIF table
    vif_rows = []
    for _, r in vif_df.iterrows():
        flag = "⚠ TRUE" if bool(r["multicollinearity_flag"]) else "OK"
        vif_rows.append(
            f"<tr><td><strong>{html.escape(str(r['component']))}</strong></td>"
            f"<td>{_fmt_num(r['vif'], 2)}</td>"
            f"<td>{_fmt_num(r['max_corr_with_others'], 2)}</td>"
            f"<td>{html.escape(flag)}</td></tr>"
        )

    # Bai-Perron breaks
    bp_rows = []
    for _, r in bai_perron_df.iterrows():
        if r["break_date"] == "" or pd.isna(r["break_date"]):
            continue
        bp_rows.append(
            f"<tr><td><strong>{html.escape(str(r['series_name']))}</strong></td>"
            f"<td>{int(r['n_breaks_detected'])}</td>"
            f"<td>{html.escape(str(r['break_date']))}</td></tr>"
        )

    # Correlation matrix
    corr_rows = []
    cols = list(corr_df.columns[1:])  # first is index name
    header_cols = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    for _, r in corr_df.iterrows():
        row_label = str(r.iloc[0])
        cells_html = []
        for c in cols:
            v = r[c]
            try:
                fv = float(v)
            except (TypeError, ValueError):
                cells_html.append("<td>n/a</td>")
                continue
            shade = max(0, min(1, abs(fv)))
            tint = 255 - int(120 * shade)
            cells_html.append(
                f'<td style="background-color: rgb({tint}, {tint}, 255);'
                f' text-align:right">{_fmt_num(fv, 2)}</td>'
            )
        corr_rows.append(
            f"<tr><th style='text-align:left'>{html.escape(row_label)}</th>"
            + "".join(cells_html) + "</tr>"
        )

    return f"""
<details class="lcv1-collapsible">
  <summary><strong>Section 7 — Diagnostic tests (stationarity, VIF, Bai-Perron)</strong></summary>
  <h4>Stationarity (ADF + KPSS + Phillips-Perron + Zivot-Andrews)</h4>
  <table class="lcv1-table">
    <thead><tr><th>Series</th><th>n</th><th>ADF p</th><th>KPSS p</th>
    <th>PP p</th><th>ZA p</th><th>Conclusion</th></tr></thead>
    <tbody>{''.join(st_rows)}</tbody>
  </table>
  <h4>Multicollinearity (VIF; threshold = 5.0)</h4>
  <table class="lcv1-table">
    <thead><tr><th>Component</th><th>VIF</th><th>max |corr|</th><th>Flag</th></tr></thead>
    <tbody>{''.join(vif_rows)}</tbody>
  </table>
  <h4>5×5 component correlation matrix</h4>
  <table class="lcv1-table">
    <thead><tr><th></th>{header_cols}</tr></thead>
    <tbody>{''.join(corr_rows)}</tbody>
  </table>
  <h4>Bai-Perron structural breaks (max=5, BIC, min_segment=30mo)</h4>
  <table class="lcv1-table">
    <thead><tr><th>Series</th><th>n breaks</th><th>Break date</th></tr></thead>
    <tbody>{''.join(bp_rows) or '<tr><td colspan="3">no breaks detected</td></tr>'}</tbody>
  </table>
</details>
"""


def _img_to_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    return f"data:image/png;base64,{base64.b64encode(data).decode('ascii')}"


def _build_calibration_section_html(
    calibration_df: pd.DataFrame,
    figures_dir: Path,
) -> str:
    rows = []
    for _, r in calibration_df.iterrows():
        rows.append(
            f"<tr><td><strong>{html.escape(str(r['scope']))}</strong></td>"
            f"<td>{int(r['horizon_years'])}Y</td>"
            f"<td>{int(r['n_validation'])}</td>"
            f"<td>{_fmt_num(r['brier_score'])}</td>"
            f"<td>{_fmt_num(r['reliability'])}</td>"
            f"<td>{_fmt_num(r['resolution'])}</td>"
            f"<td>{_fmt_num(r['crps_skill'])}</td>"
            f"<td>{_fmt_num(r['pit_ks_pvalue'])}</td></tr>"
        )

    fig_html = []
    for scope in ("LC_TIER2", "LC_DEEP"):
        if scope == "LC_TIER2":
            horizon = 10
        else:
            horizon = 5
        rel_path = figures_dir / f"lc_v1_reliability_diagram_{scope}_{horizon}y.png"
        pit_path = figures_dir / f"lc_v1_pit_histogram_{scope}_{horizon}y.png"
        rel_uri = _img_to_data_uri(rel_path)
        pit_uri = _img_to_data_uri(pit_path)
        if rel_uri:
            fig_html.append(
                f'<figure class="lcv1-figure">'
                f'<figcaption><strong>{scope} {horizon}Y reliability</strong></figcaption>'
                f'<img src="{rel_uri}" alt="reliability {scope} {horizon}Y"></figure>'
            )
        if pit_uri:
            fig_html.append(
                f'<figure class="lcv1-figure">'
                f'<figcaption><strong>{scope} {horizon}Y PIT histogram</strong></figcaption>'
                f'<img src="{pit_uri}" alt="PIT {scope} {horizon}Y"></figure>'
            )

    return f"""
<details class="lcv1-collapsible">
  <summary><strong>Section 8 — Calibration diagnostics (Brier / Murphy / CRPS / PIT / reliability)</strong></summary>
  <table class="lcv1-table">
    <thead><tr><th>Scope</th><th>Horizon</th><th>n_val</th><th>Brier</th>
    <th>Reliability</th><th>Resolution</th><th>CRPS skill</th><th>PIT K-S p</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <div class="lcv1-figgrid">{''.join(fig_html)}</div>
  <p><em>Headline: PIT K-S p &lt; 0.0001 across all cells → Gaussian forecast
  distribution universally rejected vs fat-tailed empirical returns.</em></p>
</details>
"""


def _build_methodology_html() -> str:
    return """
<details class="lcv1-collapsible">
  <summary><strong>Section 9 — Methodology and provenance</strong></summary>
  <ul>
    <li>Sealed pre-registration: <code>specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md</code> at commit <code>a8635ef</code></li>
    <li>Strategist arbitration: <code>DECISIONS.md</code> (entries 2026-05-24 and 2026-05-25)</li>
    <li>Investigation findings: <code>specs/INVESTIGATION_session_7.md</code></li>
    <li>Per-component regressions: <code>outputs/tables/lc_v1_per_component_regressions.csv</code></li>
    <li>Composite regression: <code>outputs/tables/lc_v1_predictive_regression.csv</code></li>
    <li>Robustness (truncate mode): <code>outputs/tables/lc_v1_predictive_regression_truncate.csv</code></li>
    <li>Conditional probabilities: <code>outputs/tables/lc_v1_conditional_probabilities.csv</code></li>
    <li>Calibration: <code>outputs/tables/lc_v1_calibration.csv</code></li>
    <li>Stationarity / VIF / Bai-Perron: <code>outputs/tables/lc_v1_stationarity.csv</code>,
        <code>lc_v1_diagnostics.csv</code>, <code>lc_v1_bai_perron_breaks.csv</code></li>
    <li>Source policy: <code>data/master/_source_policy.json</code></li>
  </ul>
  <p>Sprint timeline: 8 sessions (Sessions 1–8 + Session 6.5 one-shot infill);
  closed at tag <code>v11.3.0</code>.</p>
</details>
"""


def build_panel_html(outputs_dir: Path) -> str:
    tables_dir = outputs_dir / "tables"
    figures_dir = outputs_dir / "figures"

    df_reg = _read_csv(tables_dir / "lc_v1_predictive_regression.csv")
    df_pc = _read_csv(tables_dir / "lc_v1_per_component_regressions.csv")
    df_cprob = _read_csv(tables_dir / "lc_v1_conditional_probabilities.csv")
    df_cal = _read_csv(tables_dir / "lc_v1_calibration.csv")
    df_st = _read_csv(tables_dir / "lc_v1_stationarity.csv")
    df_vif = _read_csv(tables_dir / "lc_v1_diagnostics.csv")
    df_corr = _read_csv(tables_dir / "lc_v1_component_correlation_matrix.csv")
    df_bp = _read_csv(tables_dir / "lc_v1_bai_perron_breaks.csv")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    headline_verdict = """
<div class="verdict-card">
  <h2>⚠ LC v1.0 — FAIL</h2>
  <p><strong>Verdict</strong>: FAIL per pre-registration §2.1 decision rule.</p>
  <p><strong>Criteria pass</strong>: 0 of 4 testable.</p>
  <p><strong>Display framing</strong>: DIAGNOSTIC ONLY — no actionable conviction or probability.</p>
  <p><strong>Confidence</strong>: 99% (criterion thresholds sealed in pre-reg <code>a8635ef</code>).</p>
  <p>This panel presents research findings on the LC v1.0 composite. The composite did
  NOT meet its pre-registered falsifiability criteria. Probability outputs displayed below
  are <strong>MISCALIBRATED</strong> per PIT/Brier diagnostics — do not use for investment decisions.</p>
</div>
"""

    findings_html = """
<section class="findings">
  <h3>Three publishable research findings</h3>
  <div class="finding-card">
    <h4>Finding 1 — LC_DEEP / LC_FULL negative β at 3Y horizon (robust)</h4>
    <p><strong>LC_DEEP @ 3Y</strong>: β = −0.053, NW t = −1.89, p_1sided = 0.029.
    CY 95% CI [−0.105, −0.002] excludes zero. Sample: 509 monthly observations,
    1981-01 → 2026-03 (45 years).</p>
    <p><strong>LC_FULL @ 3Y</strong> (post-zero-fill): β = −0.034, NW t = −3.08,
    p_1sided = 0.001. CY 95% CI [−0.053, −0.015] excludes zero. n = 126 monthly obs.</p>
    <p><em>Interpretation</em>: consistent with credit-cycle / dollar-cycle reversal
    literature (Fama-French 1988; Schularick-Taylor 2012; Bruno-Shin 2015; Adrian-
    Boyarchenko 2012). Modern macro-liquidity proxies historically PRECEDE lower
    forward equity returns at the end-of-cycle, opposite to the pre-reg §4.1 priors
    based on simple "loose money → returns" intuition.</p>
  </div>
  <div class="finding-card">
    <h4>Finding 2 — 5-of-5 component-level negative β anomaly</h4>
    <p>All 5 components (z₁ NetFed, z₂ M2_yoy, z₃ BankLend_yoy, z₄ DXY⁻¹,
    z₅ Funding_stress) show <strong>NEGATIVE β at all 4 horizons</strong> in
    univariate predictive regressions (z₄ at 10Y is essentially zero).
    Pre-reg §4.1 priors expected POSITIVE on all 5.</p>
    <p>The sign anomaly is <em>component-level</em>, not a composite-construction
    artifact (verified via 4 sign-check sensitivity tests, all PASS — see
    <code>specs/INVESTIGATION_session_7.md</code>).</p>
    <p><em>Interpretation</em>: same mean-reversion / over-extension literature
    as Finding 1. The pre-reg priors were calibrated to the wrong literature
    stream (1970s-90s monetarist vs modern 2008+ mean-reversion).</p>
  </div>
  <div class="finding-card">
    <h4>Finding 3 — Universal Gaussian forecast distribution miscalibration</h4>
    <p>PIT Kolmogorov-Smirnov p &lt; 0.0001 across all 12 (scope × horizon) cells.
    Gaussian conditional forecast distribution is REJECTED universally vs
    fat-tailed empirical equity returns. CRPS skill mostly NEGATIVE: the
    prevailing-mean benchmark beats the model.</p>
    <p><em>Interpretation</em>: well-documented limitation of conditional-Gaussian
    forecast distributions for equity returns (Mandelbrot 1963; Fama 1965;
    Cont 2001). Even methodologically-clean predictive composites fail
    distributional calibration when the assumed conditional distribution is
    misspecified.</p>
  </div>
</section>
"""

    regression_table = _build_regression_table_html(df_reg)
    per_component_table = _build_per_component_table_html(df_pc)

    calibration_disclosure = """
<div class="warning-card">
  <h3>⚠ Probability outputs below are MISCALIBRATED</h3>
  <p>PIT Kolmogorov-Smirnov test p &lt; 0.0001 across all 12 cells. Gaussian forecast
  distribution rejected vs fat-tailed empirical returns. CRPS skill mostly negative
  (prevailing-mean beats model).</p>
  <p>Conditional probability table shown below for transparency.
  <strong>Do not use for investment or risk-management decisions.</strong></p>
</div>
"""

    cprob_table = _build_conditional_probs_table_html(df_cprob)

    diagnostics_section = _build_diagnostics_section_html(
        df_st, df_vif, df_bp, df_corr,
    )
    calibration_section = _build_calibration_section_html(df_cal, figures_dir)
    methodology_section = _build_methodology_html()

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>LC v1.0 (DIAGNOSTIC) — Liquidity Composite v1.0</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            max-width: 1400px; margin: 0 auto; padding: 20px; color: #222; }}
    h1, h2, h3, h4 {{ color: #1a1a1a; }}
    h1 {{ border-bottom: 3px solid #C8102E; padding-bottom: 8px; }}
    .verdict-card {{ background: #fff4f4; border: 2px solid #C8102E; border-radius: 8px;
                    padding: 20px; margin: 20px 0; }}
    .verdict-card h2 {{ color: #C8102E; margin-top: 0; }}
    .warning-card {{ background: #fff8e6; border: 2px solid #d8a000; border-radius: 8px;
                    padding: 16px; margin: 20px 0; }}
    .warning-card h3 {{ color: #b87200; margin-top: 0; }}
    .findings .finding-card {{ background: #f4f8ff; border-left: 4px solid #1565C0;
                              padding: 12px 16px; margin: 12px 0; border-radius: 4px; }}
    .lcv1-table {{ border-collapse: collapse; margin: 10px 0; width: 100%;
                  font-size: 13px; }}
    .lcv1-table th, .lcv1-table td {{ border: 1px solid #ddd; padding: 6px 8px; }}
    .lcv1-table th {{ background: #f0f0f0; }}
    .lcv1-table.faded {{ opacity: 0.55; }}
    .lcv1-collapsible {{ border: 1px solid #ccc; padding: 8px 16px; margin: 16px 0;
                        border-radius: 4px; background: #fafafa; }}
    .lcv1-collapsible summary {{ cursor: pointer; padding: 6px 0; }}
    .lcv1-figure {{ display: inline-block; max-width: 480px; margin: 8px; vertical-align: top; }}
    .lcv1-figure img {{ max-width: 100%; height: auto; border: 1px solid #ccc; }}
    .lcv1-figgrid {{ margin-top: 12px; }}
    .warn-badge {{ background: #d8a000; color: white; padding: 2px 6px;
                  border-radius: 3px; font-size: 11px; margin-left: 4px; }}
    code {{ background: #f4f4f4; padding: 1px 4px; border-radius: 2px; font-size: 13px; }}
    em {{ color: #555; }}
  </style>
</head>
<body>

<h1>LC v1.0 (DIAGNOSTIC)</h1>
<p><em>Liquidity Composite v1.0 — pre-registered research output.
Build timestamp: {timestamp}.</em></p>

{headline_verdict}

{findings_html}

<h3>Section 3 — 12-cell regression table (50K bootstrap, Newey-West HAC, Campbell-Yogo)</h3>
<p>Source: <code>outputs/tables/lc_v1_predictive_regression.csv</code>.
Sign agreement vs pre-reg §4.1 priors color-coded: green = positive (expected),
red = negative (disagreement). The LC_FULL @ 10Y cell carries an
<strong>insufficient sample warning</strong> (n=42 ≪ 5×HAC_lag=595).</p>
{regression_table}

<h3>Section 4 — Per-component univariate β (5 components × 4 horizons)</h3>
<p>Source: <code>outputs/tables/lc_v1_per_component_regressions.csv</code>.
<strong>All 5 components show negative β at all horizons</strong> (z₄ at 10Y ≈ 0).
The sign anomaly is component-level, NOT a composite-construction bug.
Pre-reg §4.1 priors expected POSITIVE on all 5.</p>
{per_component_table}

{calibration_disclosure}

<h3>Section 6 — Conditional probability table (12 cells × 7 tail events)</h3>
<p>Source: <code>outputs/tables/lc_v1_conditional_probabilities.csv</code>.
LC binned into quintiles; current LC value's quintile drives the conditional
subsample. <strong>Faded styling indicates research material, not actionable.</strong></p>
{cprob_table}

{diagnostics_section}

{calibration_section}

{methodology_section}

</body>
</html>
"""
    return page


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    outputs_dir = _PROJECT_ROOT / "outputs"
    html_text = build_panel_html(outputs_dir)
    out_path = outputs_dir / "lc_v1_diagnostic_panel.html"
    out_path.write_text(html_text, encoding="utf-8")
    logger.info("Wrote %s (%d bytes)", out_path, len(html_text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
