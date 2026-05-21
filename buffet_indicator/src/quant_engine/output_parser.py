"""Parse v50 outputs → dashboard-ready structures.

The v50 engine writes a flat CSV (one row per strategy × period × cost) plus
a 32-sheet XLSX workbook plus 4 governance ``.txt`` files. This module reads
those artifacts and converts them into the per-section payloads the dashboard
renderer expects (a dict with headline KPIs, SPY head-to-head deltas, the
period heatmap, cost-retention ratios, and per-sheet DataFrames).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from .strategy_engine_config import (
    QE_LATEST_CSV,
    QE_LATEST_XLSX,
    QE_GOVERNANCE_DIR,
    V1_ACTIVE_STRATEGIES,
    V1_BENCHMARK_INDICES,
    V1_BENCHMARK_STOCKS,
    V50_CYCLES,
    V50_FULL,
    ALL_EXCEL_GROUPS,
)


def parse_v50_csv(path: Optional[Path] = None) -> pd.DataFrame:
    """Parse v50 CSV, filter to V1 entities, add ``tier`` column.

    The v50 engine writes the per-period rows in a wide-ish format with
    columns including ``label``, ``period``, ``_costbps`` plus the metric
    columns. V1 filters out LowRisk / FACTOR-ONLY / ETF-ROTATION which were
    dropped from the V1 dashboard lineup.

    The ``tier`` column is added for downstream rendering — it has values
    ``Strategy`` / ``Index`` / ``Stock`` and lets the sortable table group
    rows by entity type.

    Returns an empty DataFrame with the expected columns if the CSV is missing.
    """
    if path is None:
        path = QE_LATEST_CSV
    if not path.exists():
        return pd.DataFrame(columns=[
            "label", "period", "_costbps", "cagr", "sharpe", "sortino",
            "maxdd", "calmar", "years", "tier",
        ])
    df = pd.read_csv(path)
    v1_entities = V1_ACTIVE_STRATEGIES + V1_BENCHMARK_INDICES + V1_BENCHMARK_STOCKS
    df = df[df["label"].isin(v1_entities)].copy()
    for col in ("cagr", "sharpe", "sortino", "maxdd", "calmar", "years", "_costbps"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    def _tier(row: pd.Series) -> str:
        if row["label"] in V1_ACTIVE_STRATEGIES:
            return "Strategy"
        if row["label"] in V1_BENCHMARK_INDICES:
            return "Index"
        return "Stock"

    df["tier"] = df.apply(_tier, axis=1)
    return df.reset_index(drop=True)


def parse_governance_txt(directory: Optional[Path] = None) -> Dict[str, str]:
    """Read the 4 governance ``.txt`` files into a dict keyed by kind.

    Missing files surface as ``"(missing: filename)"`` so the renderer can
    show a placeholder without blowing up the page.
    """
    if directory is None:
        directory = QE_GOVERNANCE_DIR
    out: Dict[str, str] = {}
    for kind in ("model_card", "config_snapshot", "environment_lock", "change_log"):
        p = directory / f"{kind}.txt"
        out[kind] = p.read_text(encoding="utf-8") if p.exists() else f"(missing: {p.name})"
    return out


def parse_v50_xlsx(path: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
    """Parse all 32 Excel sheets.

    Returns a dict keyed by sheet name. Sheets that were declared in
    ALL_EXCEL_GROUPS but are missing from the workbook surface as a
    DataFrame with a ``__missing__`` column so the renderer can show
    a "sheet missing" banner instead of crashing.
    """
    if path is None:
        path = QE_LATEST_XLSX
    if not path.exists():
        return {}
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    out: Dict[str, pd.DataFrame] = {}
    for group_sheets in ALL_EXCEL_GROUPS.values():
        for sheet_name in group_sheets:
            if sheet_name in sheets:
                out[sheet_name] = sheets[sheet_name]
            else:
                out[sheet_name] = pd.DataFrame(
                    {"__missing__": [f"Sheet '{sheet_name}' not in xlsx — v50 did not emit it"]}
                )
    return out


def _safe_float(x: Any) -> Optional[float]:
    """Convert to float; return None for NaN / Inf / non-numeric."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def compute_dashboard_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Derive headline numbers + ranking + heatmaps from the parsed CSV.

    Returns:
        ``{'headline': {...}, 'spy_h2h': [...], 'ranking_full': [...],
           'cost_retention': {strategy: ratio}, 'period_heatmap': {...}}``
    """
    if df.empty:
        return {
            "headline": {},
            "spy_h2h": [],
            "ranking_full": [],
            "cost_retention": {},
            "period_heatmap": {},
        }
    full_15 = df[(df["period"] == "FULL") & (df["_costbps"] == 15)].copy()

    headline: Dict[str, Optional[float]] = {}
    dd = full_15[full_15["label"] == "DD-TARGET"]
    if len(dd) > 0:
        r = dd.iloc[0]
        headline = {
            "sharpe": _safe_float(r.get("sharpe")),
            "cagr": _safe_float(r.get("cagr")),
            "maxdd": _safe_float(r.get("maxdd")),
            "calmar": _safe_float(r.get("calmar")),
            "years": _safe_float(r.get("years")),
        }

    spy = full_15[full_15["label"] == "SPY"]
    spy_sharpe = _safe_float(spy.iloc[0]["sharpe"]) if len(spy) else None
    spy_maxdd = _safe_float(spy.iloc[0]["maxdd"]) if len(spy) else None

    spy_h2h = []
    if spy_sharpe is not None:
        for _, r in full_15.iterrows():
            if r["label"] == "SPY":
                continue
            s = _safe_float(r["sharpe"])
            m = _safe_float(r["maxdd"])
            if s is None or m is None:
                continue
            spy_h2h.append({
                "label": r["label"],
                "tier": r["tier"],
                "sharpe": s,
                "delta_sharpe_vs_spy": s - spy_sharpe,
                "delta_maxdd_vs_spy": (m - spy_maxdd) if spy_maxdd is not None else None,
            })
        spy_h2h.sort(
            key=lambda x: x["delta_sharpe_vs_spy"] if x["delta_sharpe_vs_spy"] is not None else -1e9,
            reverse=True,
        )

    cost_retention: Dict[str, float] = {}
    full_100 = df[(df["period"] == "FULL") & (df["_costbps"] == 100)]
    for label in V1_ACTIVE_STRATEGIES:
        r15 = full_15[full_15["label"] == label]
        r100 = full_100[full_100["label"] == label]
        if len(r15) and len(r100):
            s15 = _safe_float(r15.iloc[0]["sharpe"])
            s100 = _safe_float(r100.iloc[0]["sharpe"])
            if s15 is not None and s15 > 0 and s100 is not None:
                cost_retention[label] = s100 / s15

    heatmap: Dict[str, Dict[str, Optional[float]]] = {}
    for label in V1_ACTIVE_STRATEGIES + V1_BENCHMARK_INDICES:
        heatmap[label] = {}
        for period in V50_CYCLES + V50_FULL:
            sub = df[
                (df["label"] == label)
                & (df["period"] == period)
                & (df["_costbps"] == 15)
            ]
            heatmap[label][period] = _safe_float(sub.iloc[0]["sharpe"]) if len(sub) else None

    ranking_records = []
    for _, r in full_15.sort_values("sharpe", ascending=False).iterrows():
        ranking_records.append({
            k: _safe_float(r[k]) if k in ("cagr", "sharpe", "sortino", "maxdd", "calmar", "years")
            else r[k]
            for k in r.index
        })

    return {
        "headline": headline,
        "spy_h2h": spy_h2h,
        "ranking_full": ranking_records,
        "cost_retention": cost_retention,
        "period_heatmap": heatmap,
    }
