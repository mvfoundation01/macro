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
    underwater_curves: list[dict[str, Any]] = []  # v11.2.3 Surface 2 chart
    for label, sr in strategies.items():
        r = sr.monthly.dropna()
        # v11.2.3 — underwater curve time series for the Plotly chart
        # (one trace per strategy; nullable for any pre-history months).
        if not r.empty:
            eq_series = (1.0 + r).cumprod() * 10_000.0
            running_max_series = eq_series.cummax()
            dd_series = (eq_series - running_max_series) / running_max_series
            underwater_curves.append({
                "label": label,
                "is_v2": _is_v2(label),
                "dates": [d.strftime("%Y-%m-%d") for d in dd_series.index],
                "dd_values": [None if pd.isna(v) else float(v) for v in dd_series],
            })

        episodes = find_drawdown_episodes(r, min_depth=min_depth)
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
        "underwater_curves": underwater_curves,  # v11.2.3 Surface 2 chart
        "meta": {
            "macro_overlay_available": mvci_z is not None,
        },
    }


# ── Surface 3 — Rolling Metrics ─────────────────────────────────────────


def compute_rolling_metrics(
    returns: pd.Series, window: int = 60
) -> pd.DataFrame:
    """60-month rolling CAGR, Vol, Sharpe, Sortino. Returns DataFrame indexed by date."""
    if returns.empty:
        return pd.DataFrame()
    r = returns.dropna()

    def _roll_cagr(s: pd.Series) -> float:
        prod = float((1.0 + s).prod())
        if prod <= 0:
            return float("nan")
        years = len(s) / 12.0
        if years <= 0:
            return float("nan")
        return prod ** (1.0 / years) - 1.0

    def _roll_sharpe(s: pd.Series) -> float:
        sd = s.std(ddof=1)
        if sd == 0 or not np.isfinite(sd):
            return float("nan")
        return float(s.mean() / sd * math.sqrt(12.0))

    def _roll_sortino(s: pd.Series) -> float:
        downside = s[s < 0]
        if downside.empty:
            return float("nan")
        dsd = downside.std(ddof=1)
        if dsd == 0 or not np.isfinite(dsd):
            return float("nan")
        return float(s.mean() / dsd * math.sqrt(12.0))

    out = pd.DataFrame({
        "rolling_cagr": r.rolling(window).apply(_roll_cagr, raw=False),
        "rolling_vol": r.rolling(window).std() * math.sqrt(12.0),
        "rolling_sharpe": r.rolling(window).apply(_roll_sharpe, raw=False),
        "rolling_sortino": r.rolling(window).apply(_roll_sortino, raw=False),
    })
    return out.dropna(how="all")


def build_rolling_metrics_surface(
    strategies: dict[str, StrategyReturns] | None = None,
    window: int = 60,
) -> dict[str, Any]:
    """Surface 3: rolling 60-month summary stats per strategy (min/median/max of rolling Sharpe etc.)."""
    if strategies is None:
        strategies = load_all_strategy_returns()
    if not strategies:
        return {"available": False, "reason": "no strategy returns available", "per_strategy": []}

    per_strategy: list[dict[str, Any]] = []
    rolling_series: list[dict[str, Any]] = []  # v11.2.3 Surface 3 chart
    for label, sr in strategies.items():
        r = sr.monthly.dropna()
        if len(r) < window + 1:
            per_strategy.append({
                "label": label, "is_v2": _is_v2(label),
                "available": False,
                "reason": f"only {len(r)} months; need {window + 1} for rolling {window}-mo metrics",
            })
            continue
        roll = compute_rolling_metrics(r, window=window)
        if roll.empty:
            per_strategy.append({
                "label": label, "is_v2": _is_v2(label),
                "available": False,
                "reason": "rolling computation returned empty",
            })
            continue
        # v11.2.3 — expose rolling time series so the chart can plot
        # 3 sub-panels (sharpe / vol / sortino) per strategy.
        rolling_series.append({
            "label": label,
            "is_v2": _is_v2(label),
            "dates": [d.strftime("%Y-%m-%d") for d in roll.index],
            "sharpe": [None if pd.isna(v) else float(v) for v in roll["rolling_sharpe"]],
            "vol": [None if pd.isna(v) else float(v) for v in roll["rolling_vol"]],
            "sortino": [None if pd.isna(v) else float(v) for v in roll["rolling_sortino"]],
        })
        per_strategy.append({
            "label": label,
            "is_v2": _is_v2(label),
            "available": True,
            "n_observations": int(roll.shape[0]),
            "cagr": {
                "min_fmt": _fmt_pct(float(roll["rolling_cagr"].min()), digits=2),
                "median_fmt": _fmt_pct(float(roll["rolling_cagr"].median()), digits=2),
                "max_fmt": _fmt_pct(float(roll["rolling_cagr"].max()), digits=2),
                "pct_positive_fmt": f"{(roll['rolling_cagr'] > 0).mean() * 100:.1f}%",
            },
            "vol": {
                "min_fmt": _fmt_pct(float(roll["rolling_vol"].min()), digits=2),
                "median_fmt": _fmt_pct(float(roll["rolling_vol"].median()), digits=2),
                "max_fmt": _fmt_pct(float(roll["rolling_vol"].max()), digits=2),
            },
            "sharpe": {
                "min_fmt": _fmt_signed(float(roll["rolling_sharpe"].min()), digits=3),
                "median_fmt": _fmt_signed(float(roll["rolling_sharpe"].median()), digits=3),
                "max_fmt": _fmt_signed(float(roll["rolling_sharpe"].max()), digits=3),
                "pct_positive_fmt": f"{(roll['rolling_sharpe'] > 0).mean() * 100:.1f}%",
            },
            "sortino": {
                "min_fmt": _fmt_signed(float(roll["rolling_sortino"].min()), digits=3),
                "median_fmt": _fmt_signed(float(roll["rolling_sortino"].median()), digits=3),
                "max_fmt": _fmt_signed(float(roll["rolling_sortino"].max()), digits=3),
            },
        })

    return {
        "available": True,
        "window_months": window,
        "per_strategy": per_strategy,
        "rolling_series": rolling_series,  # v11.2.3 Surface 3 chart
    }


# ── Surface 4 — Risk Metrics deep dive ──────────────────────────────────


def build_risk_metrics_surface(
    strategies: dict[str, StrategyReturns] | None = None,
    benchmark_label: str = "V1_Combination",
) -> dict[str, Any]:
    """Surface 4: 15+ risk metrics per strategy (skew, kurtosis, VaR/CVaR, capture, etc.)."""
    if strategies is None:
        strategies = load_all_strategy_returns()
    if not strategies:
        return {"available": False, "reason": "no strategy returns available", "rows": []}

    benchmark_r = strategies[benchmark_label].monthly.dropna() if benchmark_label in strategies else None

    rows: list[dict[str, Any]] = []
    metric_chart_data: list[dict[str, Any]] = []  # v11.2.3 Surface 4 chart
    for label, sr in strategies.items():
        r = sr.monthly.dropna()
        if r.empty:
            continue
        arr = r.to_numpy(dtype=np.float64)

        # Higher moments.
        mean = float(arr.mean())
        std = float(arr.std(ddof=1)) if len(arr) > 1 else float("nan")
        skew = float(pd.Series(arr).skew()) if len(arr) > 2 else float("nan")
        kurt = float(pd.Series(arr).kurt()) if len(arr) > 3 else float("nan")  # excess kurtosis

        # Downside.
        downside = arr[arr < 0]
        dsd = float(downside.std(ddof=1)) if len(downside) > 1 else float("nan")

        # VaR / CVaR (monthly, historical).
        var_1 = float(np.percentile(arr, 1)) if len(arr) > 100 else float("nan")
        var_5 = float(np.percentile(arr, 5)) if len(arr) > 20 else float("nan")
        var_10 = float(np.percentile(arr, 10)) if len(arr) > 10 else float("nan")
        cvar_5 = float(arr[arr <= var_5].mean()) if np.isfinite(var_5) and (arr <= var_5).any() else float("nan")
        cvar_10 = float(arr[arr <= var_10].mean()) if np.isfinite(var_10) and (arr <= var_10).any() else float("nan")

        # Capture ratios vs benchmark.
        up_cap = down_cap = float("nan")
        beta = float("nan")
        if benchmark_r is not None and label != benchmark_label:
            common = r.index.intersection(benchmark_r.index)
            if len(common) >= 24:
                r_aligned = r.loc[common]
                b_aligned = benchmark_r.loc[common]
                up_mask = b_aligned > 0
                dn_mask = b_aligned < 0
                if up_mask.sum() >= 3:
                    up_cap = float(r_aligned[up_mask].mean() / b_aligned[up_mask].mean())
                if dn_mask.sum() >= 3:
                    down_cap = float(r_aligned[dn_mask].mean() / b_aligned[dn_mask].mean())
                # Beta = cov(r, b) / var(b)
                if b_aligned.var(ddof=1) > 0:
                    beta = float(r_aligned.cov(b_aligned) / b_aligned.var(ddof=1))

        rows.append({
            "label": label,
            "is_v2": _is_v2(label),
            "mean_monthly_fmt": _fmt_pct(mean, digits=3),
            "std_monthly_fmt": _fmt_pct(std, digits=3),
            "downside_dev_fmt": _fmt_pct(dsd, digits=3),
            "skew_fmt": _fmt_signed(skew, digits=3),
            "excess_kurt_fmt": _fmt_signed(kurt, digits=3),
            "var_1_fmt": _fmt_pct(var_1, digits=2),
            "var_5_fmt": _fmt_pct(var_5, digits=2),
            "var_10_fmt": _fmt_pct(var_10, digits=2),
            "cvar_5_fmt": _fmt_pct(cvar_5, digits=2),
            "cvar_10_fmt": _fmt_pct(cvar_10, digits=2),
            "beta_fmt": _fmt_signed(beta, digits=3),
            "up_capture_fmt": _fmt_signed(up_cap, digits=3),
            "down_capture_fmt": _fmt_signed(down_cap, digits=3),
        })
        # v11.2.3 — raw scalar metrics for the grouped bar chart.
        # All values returned in *percent* (e.g. 0.012 → 1.2) so the
        # chart axis can display % consistently.
        def _pct(x: float) -> float | None:
            return None if (x is None or not np.isfinite(x)) else float(x) * 100.0

        def _raw(x: float) -> float | None:
            return None if (x is None or not np.isfinite(x)) else float(x)

        metric_chart_data.append({
            "label": label,
            "is_v2": _is_v2(label),
            "mean_pct": _pct(mean),
            "std_pct": _pct(std),
            "downside_dev_pct": _pct(dsd),
            "var_5_pct": _pct(var_5),
            "cvar_5_pct": _pct(cvar_5),
            "skew": _raw(skew),
            "beta": _raw(beta),
        })

    return {
        "available": True,
        "benchmark_label": benchmark_label,
        "rows": rows,
        "metric_chart_data": metric_chart_data,  # v11.2.3 Surface 4 chart
    }


# ── Surface 5 — Returns (annual + monthly distributions) ────────────────


def build_returns_surface(
    strategies: dict[str, StrategyReturns] | None = None,
) -> dict[str, Any]:
    """Surface 5: annual returns + monthly distribution summary per strategy."""
    if strategies is None:
        strategies = load_all_strategy_returns()
    if not strategies:
        return {"available": False, "reason": "no strategy returns available", "rows": []}

    rows: list[dict[str, Any]] = []
    cum_log_curves: list[dict[str, Any]] = []  # v11.2.3 Surface 5 panel (a)
    annual_returns_by_strategy: list[dict[str, Any]] = []  # panel (b)
    for label, sr in strategies.items():
        r = sr.monthly.dropna()
        if r.empty:
            continue
        # Annual returns (year-end compounding).
        annual = r.resample("YE").apply(lambda s: float((1.0 + s).prod() - 1.0))
        annual_arr = annual.to_numpy(dtype=np.float64)
        arr_m = r.to_numpy(dtype=np.float64)

        # v11.2.3 — cumulative log-equity series for panel (a).
        cum = (1.0 + r).cumprod()
        log_eq = np.log(cum.to_numpy(dtype=np.float64))
        cum_log_curves.append({
            "label": label,
            "is_v2": _is_v2(label),
            "dates": [d.strftime("%Y-%m-%d") for d in cum.index],
            "log_eq": [None if not np.isfinite(v) else float(v) for v in log_eq],
        })
        # v11.2.3 — per-year returns for panel (b) grouped bar.
        annual_returns_by_strategy.append({
            "label": label,
            "is_v2": _is_v2(label),
            "years": [int(d.year) for d in annual.index],
            "values": [None if pd.isna(v) else float(v) * 100.0 for v in annual_arr],
        })

        rows.append({
            "label": label,
            "is_v2": _is_v2(label),
            "n_years": int(len(annual)),
            "best_year_fmt": _fmt_pct(float(annual_arr.max()), digits=2) if len(annual_arr) else "n/a",
            "worst_year_fmt": _fmt_pct(float(annual_arr.min()), digits=2) if len(annual_arr) else "n/a",
            "median_year_fmt": _fmt_pct(float(np.median(annual_arr)), digits=2) if len(annual_arr) else "n/a",
            "pct_positive_years_fmt": f"{(annual_arr > 0).mean() * 100:.1f}%" if len(annual_arr) else "n/a",
            "monthly_p05_fmt": _fmt_pct(float(np.percentile(arr_m, 5)), digits=2) if len(arr_m) > 20 else "n/a",
            "monthly_p95_fmt": _fmt_pct(float(np.percentile(arr_m, 95)), digits=2) if len(arr_m) > 20 else "n/a",
            "monthly_min_fmt": _fmt_pct(float(arr_m.min()), digits=2) if len(arr_m) else "n/a",
            "monthly_max_fmt": _fmt_pct(float(arr_m.max()), digits=2) if len(arr_m) else "n/a",
            "pct_positive_months_fmt": f"{(arr_m > 0).mean() * 100:.1f}%" if len(arr_m) else "n/a",
        })

    return {
        "available": True,
        "rows": rows,
        "cum_log_curves": cum_log_curves,  # v11.2.3 Surface 5 panel (a)
        "annual_returns": annual_returns_by_strategy,  # v11.2.3 panel (b)
    }


# ── Surface 6 — Lump Sum (win rate vs benchmark) ────────────────────────


def build_lump_sum_surface(
    strategies: dict[str, StrategyReturns] | None = None,
    benchmark_label: str = "V1_Combination",
    horizons_months: tuple[int, ...] = (3, 12, 36),
) -> dict[str, Any]:
    """Surface 6: Lump-sum win rate / mean lump-sum advantage (MLSA) vs benchmark.

    For each rolling N-month window, compute (1+r).prod() for strategy and
    benchmark. Strategy "wins" when its cumulative return > benchmark's.
    """
    if strategies is None:
        strategies = load_all_strategy_returns()
    if not strategies or benchmark_label not in strategies:
        return {
            "available": False,
            "reason": f"benchmark {benchmark_label} not available",
            "rows": [],
        }
    benchmark_r = strategies[benchmark_label].monthly.dropna()

    rows: list[dict[str, Any]] = []
    for label, sr in strategies.items():
        if label == benchmark_label:
            continue
        r = sr.monthly.dropna()
        common = r.index.intersection(benchmark_r.index)
        if len(common) < max(horizons_months) + 5:
            rows.append({
                "label": label, "is_v2": _is_v2(label),
                "available": False,
                "reason": f"only {len(common)} common months",
                "horizons": [],
            })
            continue
        r_a = r.loc[common].to_numpy(dtype=np.float64)
        b_a = benchmark_r.loc[common].to_numpy(dtype=np.float64)

        horizon_rows = []
        for h in horizons_months:
            wins = 0
            total = 0
            advantages = []
            for start in range(len(r_a) - h + 1):
                r_cum = float(np.prod(1.0 + r_a[start:start + h])) - 1.0
                b_cum = float(np.prod(1.0 + b_a[start:start + h])) - 1.0
                if r_cum > b_cum:
                    wins += 1
                advantages.append(r_cum - b_cum)
                total += 1
            wr = (wins / total * 100.0) if total else float("nan")
            mlsa = float(np.mean(advantages)) if advantages else float("nan")
            horizon_rows.append({
                "horizon_months": h,
                "win_rate_fmt": f"{wr:.1f}%" if np.isfinite(wr) else "n/a",
                "mlsa_fmt": _fmt_pct(mlsa, digits=2),
                "n_windows": total,
            })

        rows.append({
            "label": label, "is_v2": _is_v2(label),
            "available": True,
            "horizons": horizon_rows,
        })

    # v11.2.3 — terminal wealth of $10k at series end, per strategy, for
    # the Surface 6 bar chart. Sorted descending so the leader is leftmost.
    terminal_wealth: list[dict[str, Any]] = []
    for label, sr in strategies.items():
        r = sr.monthly.dropna()
        if r.empty:
            continue
        cum = float((1.0 + r).prod())
        terminal_wealth.append({
            "label": label,
            "is_v2": _is_v2(label),
            "is_benchmark": label == benchmark_label,
            "terminal_value": cum * 10_000.0,
            "cagr_pct": (cum ** (12.0 / len(r)) - 1.0) * 100.0 if len(r) > 0 else None,
            "n_months": int(len(r)),
        })
    terminal_wealth.sort(key=lambda d: d["terminal_value"], reverse=True)

    return {
        "available": True,
        "benchmark_label": benchmark_label,
        "rows": rows,
        "terminal_wealth": terminal_wealth,  # v11.2.3 Surface 6 chart
    }


# ── Surface 7 — Risk vs Return scatter (as table) ───────────────────────


def build_risk_vs_return_surface(
    strategies: dict[str, StrategyReturns] | None = None,
) -> dict[str, Any]:
    """Surface 7: scatter pairs (Vol, CAGR) etc. — table form pending Plotly chart."""
    if strategies is None:
        strategies = load_all_strategy_returns()
    if not strategies:
        return {"available": False, "reason": "no strategy returns available", "rows": []}

    rows: list[dict[str, Any]] = []
    scatter_points: list[dict[str, Any]] = []  # v11.2.3 Surface 7 chart
    for label, sr in strategies.items():
        r = sr.monthly.dropna()
        if r.empty:
            continue
        cagr = compute_cagr(r)
        vol = _ann_vol(r)
        sharpe = compute_sharpe(r)
        sortino = compute_sortino(r)
        maxdd = compute_maxdd(r)
        ulcer = _ulcer_index(r)
        upi = float(cagr / (ulcer / 100.0)) if (np.isfinite(cagr) and np.isfinite(ulcer) and ulcer > 0) else float("nan")
        rows.append({
            "label": label,
            "is_v2": _is_v2(label),
            "vol_fmt": _fmt_pct(vol, digits=2),
            "cagr_fmt": _fmt_pct(cagr, digits=2),
            "sharpe_fmt": _fmt_signed(sharpe, digits=3),
            "sortino_fmt": _fmt_signed(sortino, digits=3),
            "maxdd_fmt": _fmt_pct(maxdd, digits=2),
            "ulcer_fmt": f"{ulcer:.2f}" if np.isfinite(ulcer) else "n/a",
            "upi_fmt": _fmt_signed(upi, digits=3),
        })
        # v11.2.3 — annualized vol on x, CAGR on y, both in %.
        if np.isfinite(vol) and np.isfinite(cagr):
            scatter_points.append({
                "label": label,
                "is_v2": _is_v2(label),
                "vol_pct": float(vol) * 100.0,
                "cagr_pct": float(cagr) * 100.0,
                "sharpe": float(sharpe) if np.isfinite(sharpe) else None,
            })

    return {
        "available": True,
        "rows": rows,
        "scatter_points": scatter_points,  # v11.2.3 Surface 7 chart
    }


# ── Surface 8 — Withdrawal Stats (SWR survival analysis) ────────────────


def _swr_survival_pct(monthly_returns: np.ndarray, withdrawal_rate: float,
                      horizon_years: int) -> float | None:
    """% of rolling horizon-year windows where $10K survives a withdrawal_rate annual draw.

    Returns None if not enough data for any window of the given horizon.
    """
    h_months = horizon_years * 12
    if len(monthly_returns) < h_months + 1:
        return None
    monthly_withdrawal = withdrawal_rate / 12.0
    survivors = 0
    total = 0
    for start in range(len(monthly_returns) - h_months + 1):
        balance = 1.0
        survived = True
        for i in range(h_months):
            balance = balance * (1.0 + float(monthly_returns[start + i])) - monthly_withdrawal
            if balance <= 0:
                survived = False
                break
        if survived:
            survivors += 1
        total += 1
    if total == 0:
        return None
    return survivors / total * 100.0


def build_withdrawal_surface(
    strategies: dict[str, StrategyReturns] | None = None,
    horizons_years: tuple[int, ...] = (10, 20, 30),
    rates: tuple[float, ...] = (0.03, 0.04, 0.05),
) -> dict[str, Any]:
    """Surface 8: % of rolling N-year windows that survived various withdrawal rates."""
    if strategies is None:
        strategies = load_all_strategy_returns()
    if not strategies:
        return {"available": False, "reason": "no strategy returns available", "rows": []}

    rows: list[dict[str, Any]] = []
    # v11.2.3 — heatmap matrices per strategy: rows=rates, cols=horizons.
    heatmap_by_strategy: list[dict[str, Any]] = []
    rates_pct = [f"{rate * 100:.0f}%" for rate in rates]
    horizons_lbl = [str(h) for h in horizons_years]  # categorical x-axis
    for label, sr in strategies.items():
        r = sr.monthly.dropna()
        if r.empty:
            continue
        arr = r.to_numpy(dtype=np.float64)
        cells: list[dict[str, Any]] = []
        z_matrix: list[list[float | None]] = []
        for rate in rates:
            z_row: list[float | None] = []
            for h in horizons_years:
                surv = _swr_survival_pct(arr, rate, h)
                z_row.append(surv if surv is None else float(surv))
                cells.append({
                    "horizon_years": h,
                    "rate_fmt": f"{rate * 100:.0f}%",
                    "survival_fmt": f"{surv:.1f}%" if surv is not None else "n/a",
                })
            z_matrix.append(z_row)
        rows.append({
            "label": label, "is_v2": _is_v2(label),
            "n_months": int(len(r)),
            "cells": cells,
        })
        heatmap_by_strategy.append({
            "label": label,
            "is_v2": _is_v2(label),
            "z": z_matrix,  # [rate_idx][horizon_idx]
        })

    # Pick the primary V1 strategy if present, else the first non-V2 strategy,
    # else the first strategy. Used as the default heatmap shown in the UI.
    primary_label = None
    for cand in ("V1_Combination", "SPY"):
        if any(h["label"] == cand for h in heatmap_by_strategy):
            primary_label = cand
            break
    if primary_label is None:
        non_v2 = [h for h in heatmap_by_strategy if not h["is_v2"]]
        if non_v2:
            primary_label = non_v2[0]["label"]
        elif heatmap_by_strategy:
            primary_label = heatmap_by_strategy[0]["label"]

    return {
        "available": True,
        "horizons_years": list(horizons_years),
        "rates_fmt": rates_pct,
        "rows": rows,
        "heatmap": {  # v11.2.3 Surface 8 chart
            "x_labels": horizons_lbl,
            "y_labels": rates_pct,
            "x_axis_title": "Horizon (years)",
            "y_axis_title": "Annual withdrawal rate",
            "z_unit": "% survival",
            "primary_label": primary_label,
            "by_strategy": heatmap_by_strategy,
        },
    }


# ── Surface 9 — Seasonality + Allocation Pies ──────────────────────────


def build_seasonality_surface(
    strategies: dict[str, StrategyReturns] | None = None,
) -> dict[str, Any]:
    """Surface 9: month-by-month average return + allocation pies (declarative).

    Per spec §6.11 thin slice — emit average return per calendar month
    across all years for each strategy.
    """
    if strategies is None:
        strategies = load_all_strategy_returns()
    if not strategies:
        return {"available": False, "reason": "no strategy returns available", "rows": []}

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    rows: list[dict[str, Any]] = []
    for label, sr in strategies.items():
        r = sr.monthly.dropna()
        if r.empty:
            continue
        by_month: list[dict[str, Any]] = []
        for i, m_label in enumerate(months, start=1):
            mask = r.index.month == i
            if mask.any():
                vals = r[mask].to_numpy(dtype=np.float64)
                # v11.2.2.9 — also emit raw `mean` (decimal) so a Plotly heatmap
                # can plot numeric values without parsing formatted strings.
                by_month.append({
                    "month": m_label,
                    "mean": float(vals.mean()),
                    "mean_fmt": _fmt_pct(float(vals.mean()), digits=2),
                    "n": int(len(vals)),
                    "pct_positive_fmt": f"{(vals > 0).mean() * 100:.0f}%",
                })
            else:
                by_month.append({"month": m_label, "mean": None, "mean_fmt": "n/a", "n": 0, "pct_positive_fmt": "n/a"})
        rows.append({
            "label": label, "is_v2": _is_v2(label),
            "by_month": by_month,
            "n_years_observed": int(len(r) / 12),
        })

    # Allocation pies (decorative — V1 Combination + R-PRIMARY when fire).
    pies = {
        "v1_combination": [
            {"label": "DD-TARGET", "weight": 0.40, "color": "#1f77b4"},
            {"label": "ENS-Ultra", "weight": 0.30, "color": "#2ca02c"},
            {"label": "LowBeta",   "weight": 0.30, "color": "#ff7f0e"},
        ],
        "v2_r_primary_when_fire": [
            {"label": "V1 Combination", "weight": 0.50, "color": "#1f77b4"},
            {"label": "T-bills (3-mo)", "weight": 0.50, "color": "#7f7f7f"},
        ],
    }

    return {
        "available": True,
        "rows": rows,
        "pies": pies,
    }


__all__ = [
    "V2_LABELS",
    "build_summary_surface",
    "find_drawdown_episodes",
    "tag_episodes_with_macro_regime",
    "build_drawdowns_surface",
    "compute_rolling_metrics",
    "build_rolling_metrics_surface",
    "build_risk_metrics_surface",
    "build_returns_surface",
    "build_lump_sum_surface",
    "build_risk_vs_return_surface",
    "build_withdrawal_surface",
    "_swr_survival_pct",
    "build_seasonality_surface",
]
