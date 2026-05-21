"""v11.2 — V2 metrics computation (CAGR, Sharpe, Sortino, MaxDD, Calmar) per cycle.

Emits ``outputs/quant_engine/latest/v2_latest.csv`` with 3 rules × 8 cycles × 5
cost levels = 120 rows.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.quant_engine.mv_conditional import (
    QE_LATEST_DIR,
    QUANT_PIPELINE_RESULTS,
    RULE_REGISTRY,
    apply_mv_conditional,
    load_mvci_mrc_zscores_monthly,
    load_tbill_monthly_return,
)


# v50 USER-EXPLICIT CYCLES (matches quant_engine_v50_FINAL.py line 225-233)
CYCLES: dict[str, tuple[str, str]] = {
    "Dotcom":    ("2000-03-24", "2003-03-12"),
    "Bull03-07": ("2003-03-12", "2007-10-11"),
    "GFC":       ("2007-10-11", "2009-03-09"),
    "LongBull":  ("2009-03-09", "2020-02-19"),
    "COVID":     ("2020-02-19", "2022-01-04"),
    "Bear22":    ("2022-01-04", "2022-10-12"),
    "AIBull":    ("2022-10-12", "2026-01-28"),
}
FULL_PERIOD = ("FULL", ("2000-01-03", None))
COST_LEVELS = [15, 30, 45, 75, 100]
PERIODS_ALL: list[tuple[str, tuple[str, str | None]]] = [FULL_PERIOD] + list(CYCLES.items())


def _annualization_factor(returns: pd.Series) -> float:
    """Heuristic: monthly returns → factor=12; daily → factor=252."""
    if len(returns) < 2:
        return 12.0
    dt = (returns.index[-1] - returns.index[0]).days / max(len(returns) - 1, 1)
    return 12.0 if dt > 20 else 252.0


def compute_cagr(returns: pd.Series) -> float:
    if returns.empty:
        return float("nan")
    cum = (1.0 + returns).prod()
    years = (returns.index[-1] - returns.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    return float(cum ** (1.0 / years) - 1.0)


def compute_sharpe(returns: pd.Series, rf_return: pd.Series | None = None) -> float:
    if returns.empty:
        return float("nan")
    if rf_return is None:
        excess = returns
    else:
        rf_aligned = rf_return.reindex(returns.index).fillna(0.0)
        excess = returns - rf_aligned
    sd = excess.std(ddof=1)
    if sd is None or sd == 0 or np.isnan(sd):
        return float("nan")
    ann = _annualization_factor(returns)
    return float(excess.mean() / sd * np.sqrt(ann))


def compute_sortino(returns: pd.Series, rf_return: pd.Series | None = None) -> float:
    if returns.empty:
        return float("nan")
    if rf_return is None:
        excess = returns
    else:
        rf_aligned = rf_return.reindex(returns.index).fillna(0.0)
        excess = returns - rf_aligned
    downside = excess[excess < 0]
    if downside.empty:
        return float("nan")
    dsd = downside.std(ddof=1)
    if dsd is None or dsd == 0 or np.isnan(dsd):
        return float("nan")
    ann = _annualization_factor(returns)
    return float(excess.mean() / dsd * np.sqrt(ann))


def compute_maxdd(returns: pd.Series) -> float:
    if returns.empty:
        return float("nan")
    eq = (1.0 + returns).cumprod()
    peak = eq.cummax()
    dd = (eq - peak) / peak
    return float(dd.min())


def compute_calmar(returns: pd.Series) -> float:
    cagr = compute_cagr(returns)
    maxdd = compute_maxdd(returns)
    if not np.isfinite(cagr) or not np.isfinite(maxdd) or maxdd == 0:
        return float("nan")
    return float(cagr / abs(maxdd))


def compute_metrics_row(
    returns: pd.Series, label: str, period: str, costbps: int,
    rf_return: pd.Series | None = None,
) -> dict[str, object]:
    """Compute (CAGR, Sharpe, Sortino, MaxDD, Calmar) for one (label, period, cost)."""
    if returns.empty:
        return {
            "label": label, "period": period, "_costbps": costbps,
            "cagr": float("nan"), "sharpe": float("nan"),
            "sortino": float("nan"), "maxdd": float("nan"),
            "calmar": float("nan"),
            "n_months": 0, "years": float("nan"),
        }
    years = (returns.index[-1] - returns.index[0]).days / 365.25
    return {
        "label": label,
        "period": period,
        "_costbps": costbps,
        "cagr": compute_cagr(returns),
        "sharpe": compute_sharpe(returns, rf_return),
        "sortino": compute_sortino(returns, rf_return),
        "maxdd": compute_maxdd(returns),
        "calmar": compute_calmar(returns),
        "n_months": int(len(returns)),
        "years": float(years),
    }


def _slice_to_period(returns: pd.Series, start: str, end: str | None) -> pd.Series:
    s = pd.Timestamp(start)
    if end is None:
        return returns[returns.index >= s]
    return returns[(returns.index >= s) & (returns.index <= pd.Timestamp(end))]


def build_v2_metrics_table(
    results_dir: Path | None = None,
    out_path: Path | None = None,
    cost_levels: list[int] | None = None,
) -> pd.DataFrame:
    """Build 3 rules × 8 periods × 5 costs = 120-row metrics table.

    Returns the DataFrame and writes ``outputs/quant_engine/latest/v2_latest.csv``.
    """
    from src.quant_engine.mv_conditional import load_combo_monthly_returns

    if results_dir is None:
        results_dir = QUANT_PIPELINE_RESULTS
    if out_path is None:
        out_path = QE_LATEST_DIR / "v2_latest.csv"
    if cost_levels is None:
        cost_levels = COST_LEVELS

    z = load_mvci_mrc_zscores_monthly()
    tbill = load_tbill_monthly_return()

    rows: list[dict[str, object]] = []
    for cost in cost_levels:
        # Try both common period_label conventions used by v50.
        combo = None
        for plabel in ("FULL", "FULL_2000"):
            try:
                combo = load_combo_monthly_returns(
                    period_label=plabel, costbps=cost, results_dir=results_dir
                )
                break
            except FileNotFoundError:
                continue
        if combo is None:
            # No combo CSV available for this cost level — emit NaN rows so
            # the row count is preserved (120 rows guarantee for the spec).
            for rule_name in RULE_REGISTRY.keys():
                for plabel, (start, end) in PERIODS_ALL:
                    rows.append({
                        "label": f"V2_{rule_name}",
                        "period": plabel,
                        "_costbps": cost,
                        "cagr": float("nan"),
                        "sharpe": float("nan"),
                        "sortino": float("nan"),
                        "maxdd": float("nan"),
                        "calmar": float("nan"),
                        "n_months": 0,
                        "years": float("nan"),
                    })
            continue

        for rule_name, rule_fn in RULE_REGISTRY.items():
            weights = rule_fn(z["z_mvci"], z["z_mrc"])
            v2_full = apply_mv_conditional(combo, weights, tbill)
            for plabel, (start, end) in PERIODS_ALL:
                sliced = _slice_to_period(v2_full, start, end)
                row = compute_metrics_row(
                    sliced,
                    label=f"V2_{rule_name}",
                    period=plabel,
                    costbps=cost,
                    rf_return=tbill,
                )
                rows.append(row)

    df = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df


__all__ = [
    "CYCLES",
    "FULL_PERIOD",
    "PERIODS_ALL",
    "COST_LEVELS",
    "compute_cagr",
    "compute_sharpe",
    "compute_sortino",
    "compute_maxdd",
    "compute_calmar",
    "compute_metrics_row",
    "build_v2_metrics_table",
]
