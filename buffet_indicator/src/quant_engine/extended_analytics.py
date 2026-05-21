"""v11.2.1 — Extended Analytics surfaces (Stages 4-8 of PROMPT_v11_2 mega-spec).

Implements 9 surfaces over the 6 target strategies (V1_Combination,
V2_R-PRIMARY, V2_R-ALT1, V2_R-ALT2, SPY, EW). Each ``build_<surface>_surface()``
returns a context dict consumable by the matching Jinja partial template.

PIT discipline + bootstrap CIs (Politis-Romano stationary bootstrap) inherited
from ``analytics_core``. V2 strategies are tagged DIAGNOSTIC at the source —
templates render the inline disclaimer pointing to the top-of-tab banner.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.quant_engine.analytics_core import (
    StrategyReturns,
    compute_bootstrap_ci,
    load_all_strategy_returns,
)
from src.quant_engine.v2_metrics import (
    compute_cagr,
    compute_calmar,
    compute_maxdd,
    compute_sharpe,
    compute_sortino,
)


# ── Common helpers ───────────────────────────────────────────────────────

V2_LABELS = ("V2_R-PRIMARY", "V2_R-ALT1", "V2_R-ALT2")


def _is_v2(label: str) -> bool:
    return label in V2_LABELS


def _fmt_pct(v: float | None, digits: int = 2) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v * 100:+.{digits}f}%"


def _fmt_signed(v: float | None, digits: int = 3) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "n/a"
    return f"{v:+.{digits}f}"


def _ulcer_index(returns: pd.Series) -> float:
    """Martin's Ulcer Index: sqrt(mean(drawdown^2)) * 100."""
    if returns.empty:
        return float("nan")
    eq = (1.0 + returns).cumprod()
    peak = eq.cummax()
    dd = (eq - peak) / peak
    return float(math.sqrt((dd ** 2).mean()) * 100.0)


def _ann_vol(returns: pd.Series, ann_factor: float = 12.0) -> float:
    if returns.empty:
        return float("nan")
    sd = returns.std(ddof=1)
    if sd == 0 or not np.isfinite(sd):
        return float("nan")
    return float(sd * math.sqrt(ann_factor))


def _ending_value(returns: pd.Series, start: float = 10_000.0) -> float:
    if returns.empty:
        return float("nan")
    return float(start * float((1.0 + returns).prod()))


# ── Surface 1 — Summary ─────────────────────────────────────────────────


@dataclass
class SummaryRow:
    label: str
    is_v2: bool
    ending_value_fmt: str
    cagr_fmt: str
    cagr_ci_fmt: str
    vol_fmt: str
    sharpe_fmt: str
    sharpe_ci_fmt: str
    sortino_fmt: str
    maxdd_fmt: str
    maxdd_ci_fmt: str
    calmar_fmt: str
    ulcer_fmt: str
    n_months: int


def _sharpe_metric_fn(arr: np.ndarray, ann_factor: float = 12.0) -> float:
    sd = arr.std(ddof=1)
    if sd == 0 or not np.isfinite(sd):
        return float("nan")
    return float(arr.mean() / sd * math.sqrt(ann_factor))


def _cagr_metric_fn(arr: np.ndarray, n_per_year: float = 12.0) -> float:
    if len(arr) == 0:
        return float("nan")
    prod = float((1.0 + arr).prod())
    if prod <= 0:
        return float("nan")
    years = len(arr) / n_per_year
    if years <= 0:
        return float("nan")
    return float(prod ** (1.0 / years) - 1.0)


def _maxdd_metric_fn(arr: np.ndarray) -> float:
    if len(arr) == 0:
        return float("nan")
    eq = np.cumprod(1.0 + arr)
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    return float(dd.min())


def build_summary_surface(
    strategies: dict[str, StrategyReturns] | None = None,
    n_bootstrap: int = 2_000,  # 2K for build speed; lift to 10K in batch jobs
    block_length: int = 6,
    seed: int = 42,
) -> dict[str, Any]:
    """Surface 1: KPI table (per PROMPT_v11_2 §6.3, thin slice — 8 of 16 metrics).

    Returns a context dict with key ``rows`` holding SummaryRow dicts and
    ``meta`` describing the bootstrap configuration.
    """
    if strategies is None:
        strategies = load_all_strategy_returns()
    if not strategies:
        return {"available": False, "reason": "no strategy returns available", "rows": []}

    rows: list[dict[str, Any]] = []
    for label, sr in strategies.items():
        r = sr.monthly.dropna()
        if r.empty:
            continue
        arr = r.to_numpy(dtype=np.float64)

        # Bootstrap CIs for CAGR, Sharpe, MaxDD.
        cagr, cagr_lo, cagr_hi = compute_bootstrap_ci(
            arr, n_reps=n_bootstrap, block_length=block_length, seed=seed,
            metric_fn=_cagr_metric_fn,
        )
        sharpe, sh_lo, sh_hi = compute_bootstrap_ci(
            arr, n_reps=n_bootstrap, block_length=block_length, seed=seed,
            metric_fn=_sharpe_metric_fn,
        )
        maxdd, mdd_lo, mdd_hi = compute_bootstrap_ci(
            arr, n_reps=n_bootstrap, block_length=block_length, seed=seed,
            metric_fn=_maxdd_metric_fn,
        )
        vol = _ann_vol(r)
        sortino = compute_sortino(r)
        calmar = compute_calmar(r)
        ulcer = _ulcer_index(r)
        ending_val = _ending_value(r)

        rows.append({
            "label": label,
            "is_v2": _is_v2(label),
            "ending_value": ending_val,
            "ending_value_fmt": f"${ending_val:,.0f}" if np.isfinite(ending_val) else "n/a",
            "cagr": cagr,
            "cagr_fmt": _fmt_pct(cagr, digits=2),
            "cagr_ci_fmt": f"[{_fmt_pct(cagr_lo)}, {_fmt_pct(cagr_hi)}]" if np.isfinite(cagr_lo) else "n/a",
            "vol_fmt": _fmt_pct(vol, digits=2),
            "sharpe": sharpe,
            "sharpe_fmt": _fmt_signed(sharpe, digits=3),
            "sharpe_ci_fmt": f"[{_fmt_signed(sh_lo)}, {_fmt_signed(sh_hi)}]" if np.isfinite(sh_lo) else "n/a",
            "sortino_fmt": _fmt_signed(sortino, digits=3),
            "maxdd": maxdd,
            "maxdd_fmt": _fmt_pct(maxdd, digits=2),
            "maxdd_ci_fmt": f"[{_fmt_pct(mdd_lo)}, {_fmt_pct(mdd_hi)}]" if np.isfinite(mdd_lo) else "n/a",
            "calmar_fmt": _fmt_signed(calmar, digits=3),
            "ulcer_fmt": f"{ulcer:.2f}" if np.isfinite(ulcer) else "n/a",
            "n_months": int(len(r)),
        })

    return {
        "available": True,
        "rows": rows,
        "meta": {
            "n_strategies": len(rows),
            "n_bootstrap": n_bootstrap,
            "block_length": block_length,
            "seed": seed,
            "starting_value": 10_000,
        },
    }


__all__ = [
    "V2_LABELS",
    "build_summary_surface",
]
