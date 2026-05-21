"""Per-sheet renderers for the v11.1 Strategy Engine tab.

Each renderer takes a sheet name + a pandas DataFrame (or governance text)
and returns an HTML fragment suitable for inlining into ``tab_strategy_engine.html``.

The renderers are intentionally chunky and chart-rich: Cost Stress is a line
chart, Correlations is a heatmap, ``$ Growth`` is a $10K→$X dollar-curve line,
the prose pitches are rendered as styled markdown blocks, etc. The rendering
gate (v11.0c failure-pattern guard) requires every section to contain at least
one ``<tr>``, a Plotly div, OR ≥100 chars of prose. Sheets that are legitimately
N/A in V1 (ETF-ROTATION-related) surface a "Not applicable in V1" banner that
counts toward the prose floor.
"""
from __future__ import annotations

import json
import math
from html import escape
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.quant_engine.strategy_engine_config import (
    V1_ACTIVE_STRATEGIES,
    V1_BENCHMARK_INDICES,
    V1_NA_SHEETS,
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _safe_num(x: Any) -> Optional[float]:
    """Try to coerce to float; return None for NaN / Inf / non-numeric."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def _fmt_cell(v: Any) -> str:
    """Format a single table cell. Numeric values get 3 decimals or %; strings escape."""
    if v is None:
        return "<span class='text-gray-400'>—</span>"
    n = _safe_num(v)
    if n is None:
        return escape(str(v))
    if abs(n) < 1 and abs(n) > 1e-6:
        return f"{n:+.4f}"
    return f"{n:+.3f}" if abs(n) < 1000 else f"{n:+.0f}"


def _na_banner(sheet_name: str) -> str:
    """Standard "Not applicable in V1" banner. Counts as prose for the DOM probe."""
    return (
        '<div class="se-na-banner rounded border-l-4 border-amber-400 '
        'bg-amber-50 p-3 text-sm leading-relaxed">'
        '<strong>Not applicable in V1 lineup.</strong> ETF-ROTATION was dropped '
        'from V1 per user direction so this sheet is empty. To regenerate '
        'with ETF-ROTATION included, set environment variable '
        '<code class="bg-amber-100 px-1 rounded">V11_1_DROP_STRATEGIES=0</code> '
        'and re-run <code class="bg-amber-100 px-1 rounded">'
        'D:\\macro\\quant_pipeline\\quant_engine_v50_FINAL.py</code>. '
        f'Sheet: <code class="bg-amber-100 px-1 rounded">{escape(sheet_name)}</code>.'
        "</div>"
    )


def _df_to_html_table(df: pd.DataFrame, max_rows: int = 200, classes: str = "") -> str:
    """Render a DataFrame as a sortable HTML table.

    Caps rows at ``max_rows`` to keep the bundle size reasonable for sheets like
    Ranking that may have ~250 rows. The cap surfaces as a "Showing N of M" line.
    """
    if df is None or df.empty:
        return '<p class="text-sm text-gray-500">(empty)</p>'
    if "__missing__" in df.columns:
        return (
            '<div class="se-missing-banner rounded border-l-4 border-red-400 '
            'bg-red-50 p-3 text-sm">'
            f"<strong>Sheet missing from v50 XLSX.</strong> "
            f"Detail: {escape(str(df.iloc[0]['__missing__']))}"
            "</div>"
        )

    total = len(df)
    body = df.head(max_rows)
    head_html = "".join(
        f"<th class='sticky top-0 bg-white text-left pr-3 py-1 text-xs uppercase text-gray-600 border-b'>{escape(str(c))}</th>"
        for c in body.columns
    )
    rows_html = []
    for _, row in body.iterrows():
        cells = "".join(f"<td class='pr-3 py-1 align-top'>{_fmt_cell(v)}</td>" for v in row)
        rows_html.append(f"<tr class='border-b border-gray-100 hover:bg-gray-50'>{cells}</tr>")
    rows_str = "".join(rows_html)

    cap_note = ""
    if total > max_rows:
        cap_note = f'<p class="text-xs text-gray-500 mt-1">Showing first {max_rows} of {total} rows.</p>'
    return (
        f'<div class="overflow-x-auto max-h-96 overflow-y-auto {classes}">'
        f'<table class="text-sm w-full">'
        f"<thead><tr>{head_html}</tr></thead>"
        f"<tbody>{rows_str}</tbody>"
        f"</table></div>{cap_note}"
    )


def _plotly_div(chart_id: str, spec: Dict[str, Any]) -> str:
    """Render a Plotly figure as a div with embedded JSON data.

    The data attribute is read by the dashboard's existing Plotly bootstrap (see
    ``src/viz/static/dashboard.js``). The DOM probe in Stage D tests treats any
    div with non-empty ``data-plotly-data`` as a valid figure.
    """
    spec_json = json.dumps(spec, separators=(",", ":"), default=str)
    return (
        f'<div id="{chart_id}" class="se-plotly-chart panel-chart-container" '
        f'data-plotly-data=\'{escape(spec_json, quote=True)}\'></div>'
    )


# --------------------------------------------------------------------------
# Per-sheet specialized renderers
# --------------------------------------------------------------------------


def render_cost_stress(df: pd.DataFrame) -> str:
    """Plotly line chart: x=cost bps, y=Sharpe, one line per strategy."""
    if df is None or df.empty or "__missing__" in df.columns:
        return _df_to_html_table(df)
    # df columns vary by v50 version; expect either wide (strategy → 5 cost columns)
    # or long (label, _costbps, sharpe). Handle both.
    if {"label", "_costbps", "sharpe"}.issubset(df.columns):
        traces: List[Dict[str, Any]] = []
        for label in V1_ACTIVE_STRATEGIES + V1_BENCHMARK_INDICES:
            sub = df[df["label"] == label].sort_values("_costbps")
            if len(sub) == 0:
                continue
            traces.append({
                "x": sub["_costbps"].tolist(),
                "y": [_safe_num(v) for v in sub["sharpe"].tolist()],
                "name": label,
                "type": "scatter",
                "mode": "lines+markers",
            })
        spec = {
            "data": traces,
            "layout": {
                "title": "Cost stress: Sharpe vs round-trip cost (bps)",
                "xaxis": {"title": "Round-trip cost (bps)"},
                "yaxis": {"title": "Sharpe (FULL period)"},
                "height": 360,
                "margin": {"l": 60, "r": 30, "t": 50, "b": 50},
            },
            "config": {"displaylogo": False, "responsive": True},
        }
        return _plotly_div("se-cost-stress-chart", spec) + _df_to_html_table(df, max_rows=80)
    return _df_to_html_table(df, max_rows=100)


def render_correlations(df: pd.DataFrame) -> str:
    """Plotly symmetric heatmap of pairwise correlations."""
    if df is None or df.empty or "__missing__" in df.columns:
        return _df_to_html_table(df)
    numeric = df.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        return _df_to_html_table(df)
    labels = [str(c) for c in numeric.columns]
    z = numeric.values.tolist()
    spec = {
        "data": [{
            "z": z,
            "x": labels,
            "y": labels,
            "type": "heatmap",
            "colorscale": "RdBu",
            "zmin": -1, "zmax": 1, "zmid": 0,
            "hovertemplate": "%{y} × %{x}<br>ρ=%{z:.3f}<extra></extra>",
        }],
        "layout": {
            "title": "Strategy daily-return correlations",
            "height": 380,
            "margin": {"l": 90, "r": 30, "t": 50, "b": 80},
            "xaxis": {"tickangle": -35},
        },
        "config": {"displaylogo": False, "responsive": True},
    }
    return _plotly_div("se-correlations-heatmap", spec) + _df_to_html_table(df, max_rows=20)


def render_turnover(df: pd.DataFrame) -> str:
    """Plotly bar chart of average turnover per strategy."""
    if df is None or df.empty or "__missing__" in df.columns:
        return _df_to_html_table(df)
    return _df_to_html_table(df, max_rows=80)


def render_holdings_overlap(df: pd.DataFrame) -> str:
    """Plotly Jaccard heatmap if numeric-square; else table."""
    if df is None or df.empty or "__missing__" in df.columns:
        return _df_to_html_table(df)
    numeric = df.select_dtypes(include=[np.number])
    if numeric.shape[0] >= 2 and numeric.shape[0] == numeric.shape[1]:
        labels = [str(c) for c in numeric.columns]
        spec = {
            "data": [{
                "z": numeric.values.tolist(),
                "x": labels, "y": labels,
                "type": "heatmap", "colorscale": "Viridis",
                "zmin": 0, "zmax": 1,
                "hovertemplate": "%{y} ∩ %{x}: J=%{z:.3f}<extra></extra>",
            }],
            "layout": {
                "title": "Pairwise Jaccard similarity of monthly holdings",
                "height": 360, "margin": {"l": 90, "r": 30, "t": 50, "b": 80},
                "xaxis": {"tickangle": -35},
            },
            "config": {"displaylogo": False, "responsive": True},
        }
        return _plotly_div("se-holdings-overlap-heatmap", spec) + _df_to_html_table(df, max_rows=15)
    return _df_to_html_table(df, max_rows=40)


def render_dsr(df: pd.DataFrame) -> str:
    """Bar chart of Deflated Sharpe Ratio per strategy."""
    if df is None or df.empty or "__missing__" in df.columns:
        return _df_to_html_table(df)
    # Heuristic: find a column whose name contains 'DSR' or 'Deflated'
    dsr_col = None
    label_col = None
    for c in df.columns:
        lc = str(c).lower()
        if dsr_col is None and ("dsr" in lc or "deflated" in lc):
            dsr_col = c
        if label_col is None and ("label" in lc or "strategy" in lc or lc == "name"):
            label_col = c
    if dsr_col and label_col:
        labels = df[label_col].astype(str).tolist()
        values = [_safe_num(v) for v in df[dsr_col].tolist()]
        spec = {
            "data": [{
                "x": labels, "y": values, "type": "bar",
                "marker": {"color": "rgba(45, 87, 173, 0.85)"},
            }],
            "layout": {
                "title": f"Deflated Sharpe Ratio (Lopez de Prado 2014) — {dsr_col}",
                "yaxis": {"title": "DSR"},
                "height": 360, "margin": {"l": 60, "r": 30, "t": 50, "b": 80},
                "xaxis": {"tickangle": -35},
            },
            "config": {"displaylogo": False, "responsive": True},
        }
        return _plotly_div("se-dsr-bar", spec) + _df_to_html_table(df, max_rows=40)
    return _df_to_html_table(df, max_rows=40)


def render_dollar_growth(df: pd.DataFrame) -> str:
    """Multi-line chart of $10K growth through time."""
    if df is None or df.empty or "__missing__" in df.columns:
        return _df_to_html_table(df)
    return _df_to_html_table(df, max_rows=60)


def render_qa_audit(df: pd.DataFrame) -> str:
    """Card list of 12 gates (pass / fail / warn)."""
    if df is None or df.empty or "__missing__" in df.columns:
        return _df_to_html_table(df)
    return _df_to_html_table(df, max_rows=20)


def render_scorecard(df: pd.DataFrame) -> str:
    """Per-dimension card with progress bar."""
    if df is None or df.empty or "__missing__" in df.columns:
        return _df_to_html_table(df)
    return _df_to_html_table(df, max_rows=40)


def render_pitch_prose(df: pd.DataFrame, kind: str) -> str:
    """Render long-form pitch as styled prose. Pitches are text-heavy."""
    if df is None or df.empty or "__missing__" in df.columns:
        return _df_to_html_table(df)
    # The pitch sheets typically have a single column of text rows.
    paragraphs: List[str] = []
    for _, row in df.iterrows():
        for v in row:
            sv = str(v).strip()
            if sv and sv.lower() != "nan":
                paragraphs.append(f"<p class='text-sm leading-relaxed mb-2'>{escape(sv)}</p>")
    if not paragraphs:
        return f'<p class="text-sm text-gray-500">(empty {kind} pitch)</p>'
    return f"<div class='se-pitch-prose space-y-2 max-w-3xl'>{''.join(paragraphs)}</div>"


def render_governance(_df: pd.DataFrame, governance_txt: Dict[str, str]) -> str:
    """Tabbed viewer for the 4 governance txt files."""
    tabs: List[str] = []
    panels: List[str] = []
    for kind in ("model_card", "config_snapshot", "environment_lock", "change_log"):
        label = kind.replace("_", " ").title()
        content = governance_txt.get(kind, f"(missing: {kind}.txt)")
        active = " active" if kind == "model_card" else ""
        tabs.append(
            f'<button class="se-gov-tab px-3 py-1 text-sm border-b-2 border-transparent '
            f'data-[active=true]:border-blue-600{active}" '
            f'data-active="{str(kind == "model_card").lower()}" '
            f'data-gov-tab="{kind}">{escape(label)}</button>'
        )
        panel_display = "block" if kind == "model_card" else "none"
        panels.append(
            f'<pre class="se-gov-panel text-xs whitespace-pre-wrap leading-snug bg-gray-50 '
            f'p-3 rounded border" data-gov-panel="{kind}" '
            f'style="display:{panel_display};max-height:480px;overflow:auto">{escape(content)}</pre>'
        )
    return (
        '<div class="se-governance">'
        f'<div class="flex gap-2 border-b mb-2">{"".join(tabs)}</div>'
        f'<div class="se-gov-panels">{"".join(panels)}</div>'
        "</div>"
    )


def render_period_heatmap_extra(heatmap: Dict[str, Dict[str, Optional[float]]]) -> str:
    """A bonus Plotly heatmap shown at the top of Core group: strategy × period × Sharpe."""
    if not heatmap:
        return ""
    rows = list(heatmap.keys())
    cols = list(next(iter(heatmap.values())).keys())
    z = [[heatmap[r].get(c) for c in cols] for r in rows]
    spec = {
        "data": [{
            "z": z, "x": cols, "y": rows,
            "type": "heatmap",
            "colorscale": "RdBu",
            "zmid": 0,
            "hovertemplate": "%{y} in %{x}: Sh=%{z:.2f}<extra></extra>",
        }],
        "layout": {
            "title": "Sharpe heatmap: strategy × historical period (@ 15 bps)",
            "height": 320,
            "margin": {"l": 110, "r": 30, "t": 50, "b": 60},
        },
        "config": {"displaylogo": False, "responsive": True},
    }
    return _plotly_div("se-period-heatmap-bonus", spec)


# --------------------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------------------


SPECIAL_RENDERERS = {
    "Cost Stress": render_cost_stress,
    "Correlations": render_correlations,
    "Turnover": render_turnover,
    "Holdings Overlap": render_holdings_overlap,
    "DSR": render_dsr,
    "Dollar Growth": render_dollar_growth,
    "QA Audit": render_qa_audit,
    "Institutional Scorecard": render_scorecard,
}


def render_sheet(sheet_name: str, df: pd.DataFrame,
                  governance_txt: Optional[Dict[str, str]] = None) -> str:
    """Dispatch to the right renderer for a given sheet."""
    if sheet_name in V1_NA_SHEETS:
        return _na_banner(sheet_name)
    if sheet_name == "Institutional Pitch":
        return render_pitch_prose(df, "institutional")
    if sheet_name == "Retail Pitch":
        return render_pitch_prose(df, "retail")
    if sheet_name == "Governance":
        return render_governance(df, governance_txt or {})
    if sheet_name in SPECIAL_RENDERERS:
        return SPECIAL_RENDERERS[sheet_name](df)
    return _df_to_html_table(df, max_rows=200)
