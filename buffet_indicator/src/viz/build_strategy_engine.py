"""v11.1: Build the Strategy Engine tab context for the dashboard.

This module is the glue between ``src.quant_engine`` (which reads + parses
v50 outputs) and ``templates/tab_strategy_engine.html`` (which renders them).
It returns a dict keyed for the template: header KPIs in formatted strings,
a SPY head-to-head ranking, the period heatmap as inline HTML, and the
``groups`` dict containing per-sheet body_html ready for the template's
``{% for sheet in sheets %}`` loop.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.quant_engine import (
    ALL_EXCEL_GROUPS,
    V1_ACTIVE_STRATEGIES,
    V1_BENCHMARK_STOCKS,
    check_norgate_available,
    compute_dashboard_metrics,
    parse_governance_txt,
    parse_v50_csv,
    parse_v50_xlsx,
)
from src.quant_engine.strategy_engine_config import (
    QE_LATEST_DIR,
    SHEET_DESCRIPTIONS,
)
from src.viz.strategy_engine_renderers import (
    render_period_heatmap_extra,
    render_sheet,
)


def _fmt_pct(v: Optional[float], digits: int = 2) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v * 100:+.{digits}f}%"


def _fmt_signed(v: Optional[float], digits: int = 3) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v:+.{digits}f}"


def _fmt_years(v: Optional[float]) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v:.1f}"


def _days_since_refresh(last_refresh_ts: str) -> int:
    """Parse a v50 timestamp like ``20260429_1053`` → days since today."""
    try:
        d = datetime.strptime(last_refresh_ts.strip(), "%Y%m%d_%H%M")
    except ValueError:
        return -1
    return max(0, (datetime.now() - d).days)


def _last_refresh_label(last_refresh_ts: str) -> str:
    try:
        d = datetime.strptime(last_refresh_ts.strip(), "%Y%m%d_%H%M")
    except ValueError:
        return last_refresh_ts or "(unknown)"
    return d.strftime("%Y-%m-%d %H:%M")


def build_strategy_engine_context() -> Optional[Dict[str, Any]]:
    """Build the full Strategy Engine tab context.

    Returns ``None`` if no v50 outputs are synced yet (the dashboard build
    then skips the tab — but the spec mandates the tab be rendered, so we
    actually return a degraded stub rather than None in practice).
    """
    df = parse_v50_csv()
    metrics = compute_dashboard_metrics(df)
    sheets_map = parse_v50_xlsx()
    governance_txt = parse_governance_txt()
    norgate_available = check_norgate_available()

    # Header KPIs
    headline = metrics.get("headline", {})

    # v11.1.1 I2 fix: V1 lineup table now shows ALL 17 entities (4 strategies +
    # 2 indices + 11 stocks), not just the top 8 by Sharpe. Build from
    # ranking_full (already sorted Sharpe desc) and join in the delta-vs-SPY
    # columns from spy_h2h. SPY itself is included with delta=0.
    h2h_by_label = {e["label"]: e for e in metrics.get("spy_h2h", [])}
    ranking_full = metrics.get("ranking_full", [])
    # Determine tier from the row's existing tier field; build the full table.
    spy_lineup_table: list[dict] = []
    for row in ranking_full:
        label = row.get("label")
        if label is None:
            continue
        h2h = h2h_by_label.get(label, {})
        # SPY is excluded from spy_h2h (it's the baseline) — delta is 0 by definition
        delta_sh = h2h.get("delta_sharpe_vs_spy", 0.0 if label == "SPY" else None)
        delta_dd = h2h.get("delta_maxdd_vs_spy", 0.0 if label == "SPY" else None)
        spy_lineup_table.append({
            "label": label,
            "tier": row.get("tier", "Stock"),
            "sharpe": row.get("sharpe"),
            "cagr": row.get("cagr"),
            "maxdd": row.get("maxdd"),
            "delta_sharpe_vs_spy": delta_sh,
            "delta_maxdd_vs_spy": delta_dd,
        })

    # Period heatmap as inline Plotly div
    period_heatmap_html = render_period_heatmap_extra(metrics.get("period_heatmap", {}))

    # Build the groups dict: each sheet gets {name, description, body_html}
    groups: Dict[str, List[Dict[str, str]]] = {}
    group_counts: Dict[str, int] = {}
    for group_key, sheet_names in ALL_EXCEL_GROUPS.items():
        rendered_sheets: List[Dict[str, str]] = []
        for name in sheet_names:
            df_sheet = sheets_map.get(name)
            body_html = render_sheet(name, df_sheet, governance_txt=governance_txt)
            rendered_sheets.append({
                "name": name,
                "description": SHEET_DESCRIPTIONS.get(name, ""),
                "body_html": body_html,
            })
        groups[group_key] = rendered_sheets
        group_counts[group_key] = len(rendered_sheets)

    # last_refresh.txt holds the timestamp string written by sync_latest_outputs()
    last_refresh_path = QE_LATEST_DIR / "last_refresh.txt"
    last_refresh_ts = (
        last_refresh_path.read_text(encoding="utf-8").strip()
        if last_refresh_path.exists()
        else ""
    )

    n_sheets_total = sum(group_counts.values())

    # v11.2.1: Extended Analytics surfaces (Stages 4-8 of mega-spec).
    # Each surface returns a self-contained context dict; failures are
    # demoted to "unavailable" so V1 35 sections always render even if a
    # surface's data isn't there yet.
    extended_analytics: Dict[str, Any] = {}
    try:
        from src.quant_engine.extended_analytics import build_summary_surface
        extended_analytics["summary"] = build_summary_surface()
    except Exception as exc:  # noqa: BLE001
        print(f"[v11.2.1 surface 1 summary] failed to build: {exc}")
        extended_analytics["summary"] = {"available": False, "reason": str(exc), "rows": []}
    try:
        from src.quant_engine.extended_analytics import build_drawdowns_surface
        extended_analytics["drawdowns"] = build_drawdowns_surface()
    except Exception as exc:  # noqa: BLE001
        print(f"[v11.2.1 surface 2 drawdowns] failed to build: {exc}")
        extended_analytics["drawdowns"] = {"available": False, "reason": str(exc), "per_strategy": []}
    try:
        from src.quant_engine.extended_analytics import build_rolling_metrics_surface
        extended_analytics["rolling_metrics"] = build_rolling_metrics_surface()
    except Exception as exc:  # noqa: BLE001
        print(f"[v11.2.1 surface 3 rolling] failed to build: {exc}")
        extended_analytics["rolling_metrics"] = {"available": False, "reason": str(exc), "per_strategy": []}
    try:
        from src.quant_engine.extended_analytics import build_risk_metrics_surface
        extended_analytics["risk_metrics"] = build_risk_metrics_surface()
    except Exception as exc:  # noqa: BLE001
        print(f"[v11.2.1 surface 4 risk_metrics] failed to build: {exc}")
        extended_analytics["risk_metrics"] = {"available": False, "reason": str(exc), "rows": []}
    try:
        from src.quant_engine.extended_analytics import build_returns_surface
        extended_analytics["returns_dist"] = build_returns_surface()
    except Exception as exc:  # noqa: BLE001
        print(f"[v11.2.1 surface 5 returns] failed to build: {exc}")
        extended_analytics["returns_dist"] = {"available": False, "reason": str(exc), "rows": []}
    try:
        from src.quant_engine.extended_analytics import build_lump_sum_surface
        extended_analytics["lump_sum"] = build_lump_sum_surface()
    except Exception as exc:  # noqa: BLE001
        print(f"[v11.2.1 surface 6 lump_sum] failed to build: {exc}")
        extended_analytics["lump_sum"] = {"available": False, "reason": str(exc), "rows": []}
    try:
        from src.quant_engine.extended_analytics import build_risk_vs_return_surface
        extended_analytics["risk_vs_return"] = build_risk_vs_return_surface()
    except Exception as exc:  # noqa: BLE001
        print(f"[v11.2.1 surface 7 risk_vs_return] failed to build: {exc}")
        extended_analytics["risk_vs_return"] = {"available": False, "reason": str(exc), "rows": []}
    try:
        from src.quant_engine.extended_analytics import build_withdrawal_surface
        extended_analytics["withdrawal"] = build_withdrawal_surface()
    except Exception as exc:  # noqa: BLE001
        print(f"[v11.2.1 surface 8 withdrawal] failed to build: {exc}")
        extended_analytics["withdrawal"] = {"available": False, "reason": str(exc), "rows": []}
    try:
        from src.quant_engine.extended_analytics import build_seasonality_surface
        extended_analytics["seasonality"] = build_seasonality_surface()
    except Exception as exc:  # noqa: BLE001
        print(f"[v11.2.1 surface 9 seasonality] failed to build: {exc}")
        extended_analytics["seasonality"] = {"available": False, "reason": str(exc), "rows": []}

    return {
        "headline_sharpe_fmt": _fmt_signed(headline.get("sharpe")),
        "headline_cagr_fmt": _fmt_pct(headline.get("cagr"), digits=2),
        "headline_maxdd_fmt": _fmt_pct(headline.get("maxdd"), digits=2),
        "headline_calmar_fmt": _fmt_signed(headline.get("calmar")),
        "headline_years_fmt": _fmt_years(headline.get("years")),
        # v11.1 alias kept for back-compat; new code reads spy_lineup_table.
        "spy_h2h_top": spy_lineup_table,
        "spy_lineup_table": spy_lineup_table,
        "period_heatmap_html": period_heatmap_html,
        "groups": groups,
        "group_counts": group_counts,
        "n_strategies": len(V1_ACTIVE_STRATEGIES),
        "n_benchmark_stocks": len(V1_BENCHMARK_STOCKS),
        "n_sheets": n_sheets_total,
        "last_refresh_label": _last_refresh_label(last_refresh_ts),
        "days_since_refresh": _days_since_refresh(last_refresh_ts),
        "norgate_available": norgate_available,
        "extended_analytics": extended_analytics,
    }
