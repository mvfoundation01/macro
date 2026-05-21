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


# ── Surface 2 — Drawdowns + episode enumeration + macro regime overlay ──


def find_drawdown_episodes(
    returns: pd.Series, min_depth: float = 0.05
) -> pd.DataFrame:
    """Enumerate ALL drawdown episodes ≥ ``min_depth`` on a monthly return series.

    Episode = peak → bottom → recovery (back to peak). For episodes that
    have not yet recovered at series end, ``recovery_date`` is NaT and
    ``recovered=False`` (still underwater).

    Returns DataFrame indexed by episode number with columns:
        peak_date, bottom_date, recovery_date,
        depth_pct, depth_dollar (from $10K base),
        time_to_bottom_months, time_to_recover_months, time_underwater_months,
        recovered (bool)
    """
    if returns.empty:
        return pd.DataFrame(
            columns=[
                "peak_date", "bottom_date", "recovery_date",
                "depth_pct", "depth_dollar",
                "time_to_bottom_months", "time_to_recover_months",
                "time_underwater_months", "recovered",
            ]
        )
    eq = (1.0 + returns).cumprod() * 10_000.0
    running_max = eq.cummax()
    drawdown = (eq - running_max) / running_max

    episodes: list[dict[str, Any]] = []
    in_dd = False
    peak_date: pd.Timestamp | None = None
    bottom_date: pd.Timestamp | None = None
    bottom_value: float = 0.0
    peak_equity_at_episode: float = 0.0
    EPS = 1e-6
    for date, dd_val in drawdown.items():
        eq_val = float(eq.loc[date])
        if not in_dd:
            if dd_val < -EPS:
                in_dd = True
                # The peak was the previous month-end's running_max value.
                # Approximate by walking backward to the last running_max.
                peak_date = running_max.loc[:date].idxmax()
                peak_equity_at_episode = float(running_max.loc[date])
                bottom_value = float(dd_val)
                bottom_date = date
        else:
            if dd_val < bottom_value:
                bottom_value = float(dd_val)
                bottom_date = date
            if dd_val >= -EPS:
                # Recovered.
                if abs(bottom_value) >= min_depth:
                    months_to_bottom = ((bottom_date - peak_date).days / 30.4375)
                    months_to_recover = ((date - bottom_date).days / 30.4375)
                    episodes.append({
                        "peak_date": peak_date,
                        "bottom_date": bottom_date,
                        "recovery_date": date,
                        "depth_pct": float(bottom_value),
                        "depth_dollar": float(peak_equity_at_episode * bottom_value),
                        "time_to_bottom_months": float(months_to_bottom),
                        "time_to_recover_months": float(months_to_recover),
                        "time_underwater_months": float(months_to_bottom + months_to_recover),
                        "recovered": True,
                    })
                in_dd = False
                peak_date = bottom_date = None
                bottom_value = 0.0

    # Open (not-yet-recovered) episode at series end.
    if in_dd and abs(bottom_value) >= min_depth:
        months_to_bottom = ((bottom_date - peak_date).days / 30.4375)
        months_underwater = ((returns.index[-1] - peak_date).days / 30.4375)
        episodes.append({
            "peak_date": peak_date,
            "bottom_date": bottom_date,
            "recovery_date": pd.NaT,
            "depth_pct": float(bottom_value),
            "depth_dollar": float(peak_equity_at_episode * bottom_value),
            "time_to_bottom_months": float(months_to_bottom),
            "time_to_recover_months": float("nan"),
            "time_underwater_months": float(months_underwater),
            "recovered": False,
        })

    return pd.DataFrame(episodes)


def tag_episodes_with_macro_regime(
    episodes: pd.DataFrame,
    mvci_z: pd.Series | None = None,
    mrc_z: pd.Series | None = None,
) -> pd.DataFrame:
    """Upgrade 5: attach MVCI z, MRC z, and regime label at each episode's peak date.

    Uses as-of-lookup (pandas ``Series.asof``) — if z is unavailable at peak
    date, returns NaN.
    """
    out = episodes.copy()
    if mvci_z is None and mrc_z is None:
        # Lazy import to avoid cycles when called outside the orchestrator.
        from src.quant_engine.mv_conditional import load_mvci_mrc_zscores_monthly
        try:
            z = load_mvci_mrc_zscores_monthly()
            mvci_z = z["z_mvci"]
            mrc_z = z["z_mrc"]
        except Exception:
            out["mvci_z_at_peak"] = float("nan")
            out["mrc_z_at_peak"] = float("nan")
            out["regime_at_peak"] = "unknown"
            return out

    if "peak_date" not in out.columns or out.empty:
        out["mvci_z_at_peak"] = []
        out["mrc_z_at_peak"] = []
        out["regime_at_peak"] = []
        return out

    def _asof(s: pd.Series | None, d: pd.Timestamp) -> float:
        if s is None or s.empty or pd.isna(d):
            return float("nan")
        try:
            v = s.asof(d)
            return float(v) if pd.notna(v) else float("nan")
        except Exception:
            return float("nan")

    out["mvci_z_at_peak"] = out["peak_date"].apply(lambda d: _asof(mvci_z, d))
    out["mrc_z_at_peak"] = out["peak_date"].apply(lambda d: _asof(mrc_z, d))

    def _regime(row: pd.Series) -> str:
        mv, mr = row["mvci_z_at_peak"], row["mrc_z_at_peak"]
        if pd.isna(mv) or pd.isna(mr):
            return "unknown"
        if mv > 0.5 and mr > 0.5:
            return "high_val_high_stress"
        if mv > 0.5 and mr <= 0.5:
            return "high_val_low_stress"
        if mv <= 0.5 and mr > 0.5:
            return "low_val_high_stress"
        return "low_val_low_stress"

    out["regime_at_peak"] = out.apply(_regime, axis=1)
    return out


def build_drawdowns_surface(
    strategies: dict[str, StrategyReturns] | None = None,
    min_depth: float = 0.05,
) -> dict[str, Any]:
    """Surface 2: Drawdown episodes per strategy + macro regime overlay (Upgrade 5)."""
    if strategies is None:
        strategies = load_all_strategy_returns()
    if not strategies:
        return {"available": False, "reason": "no strategy returns available", "per_strategy": []}

    # Load z-scores once.
    mvci_z = mrc_z = None
    try:
        from src.quant_engine.mv_conditional import load_mvci_mrc_zscores_monthly
        z = load_mvci_mrc_zscores_monthly()
        mvci_z = z["z_mvci"]
        mrc_z = z["z_mrc"]
    except Exception:
        pass

    per_strategy: list[dict[str, Any]] = []
    for label, sr in strategies.items():
        episodes = find_drawdown_episodes(sr.monthly.dropna(), min_depth=min_depth)
        if not episodes.empty:
            episodes = tag_episodes_with_macro_regime(episodes, mvci_z, mrc_z)
            episodes = episodes.sort_values("depth_pct").reset_index(drop=True)

        # Format for HTML rendering.
        episode_rows: list[dict[str, Any]] = []
        for _, ep in episodes.iterrows():
            episode_rows.append({
                "peak_date_fmt": ep["peak_date"].strftime("%Y-%m") if pd.notna(ep["peak_date"]) else "n/a",
                "bottom_date_fmt": ep["bottom_date"].strftime("%Y-%m") if pd.notna(ep["bottom_date"]) else "n/a",
                "recovery_date_fmt": (
                    ep["recovery_date"].strftime("%Y-%m") if pd.notna(ep["recovery_date"]) else "underwater"
                ),
                "depth_pct_fmt": _fmt_pct(float(ep["depth_pct"]), digits=2),
                "depth_dollar_fmt": f"-${abs(float(ep['depth_dollar'])):,.0f}" if pd.notna(ep["depth_dollar"]) else "n/a",
                "time_to_bottom_fmt": f"{ep['time_to_bottom_months']:.1f}",
                "time_to_recover_fmt": (
                    f"{ep['time_to_recover_months']:.1f}" if pd.notna(ep["time_to_recover_months"]) else "n/a"
                ),
                "time_underwater_fmt": f"{ep['time_underwater_months']:.1f}",
                "recovered": bool(ep["recovered"]),
                "mvci_z_at_peak_fmt": (
                    f"{ep['mvci_z_at_peak']:+.2f}" if pd.notna(ep.get("mvci_z_at_peak", float("nan"))) else "n/a"
                ),
                "mrc_z_at_peak_fmt": (
                    f"{ep['mrc_z_at_peak']:+.2f}" if pd.notna(ep.get("mrc_z_at_peak", float("nan"))) else "n/a"
                ),
                "regime_at_peak": ep.get("regime_at_peak", "unknown"),
            })

        # Summary stats over recovered episodes.
        recovered = episodes[episodes["recovered"]] if not episodes.empty else episodes
        if not recovered.empty:
            summary = {
                "n_episodes": int(len(episodes)),
                "n_recovered": int(len(recovered)),
                "worst_dd_pct": _fmt_pct(float(recovered["depth_pct"].min()), digits=2),
                "median_dd_pct": _fmt_pct(float(recovered["depth_pct"].median()), digits=2),
                "median_time_to_recover_months_fmt": f"{float(recovered['time_to_recover_months'].median()):.1f}",
                "worst_time_to_recover_months_fmt": f"{float(recovered['time_to_recover_months'].max()):.1f}",
            }
        else:
            summary = {
                "n_episodes": int(len(episodes)),
                "n_recovered": 0,
                "worst_dd_pct": "n/a", "median_dd_pct": "n/a",
                "median_time_to_recover_months_fmt": "n/a",
                "worst_time_to_recover_months_fmt": "n/a",
            }

        per_strategy.append({
            "label": label,
            "is_v2": _is_v2(label),
            "episodes": episode_rows,
            "summary": summary,
        })

    return {
        "available": True,
        "min_depth_pct": _fmt_pct(min_depth, digits=0),
        "per_strategy": per_strategy,
        "meta": {
            "macro_overlay_available": mvci_z is not None,
        },
    }


__all__ = [
    "V2_LABELS",
    "build_summary_surface",
    "find_drawdown_episodes",
    "tag_episodes_with_macro_regime",
    "build_drawdowns_surface",
]
