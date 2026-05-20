"""Performance metrics with stationary block bootstrap CIs (Spec v10.0).

References
----------
Politis, D. N., & Romano, J. P. (1994). "The Stationary Bootstrap."
    Journal of the American Statistical Association, 89(428), 1303-1313.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

_MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class PerformanceMetrics:
    """Performance summary for one return stream (strategy or benchmark)."""

    cagr: float
    sharpe: float
    sharpe_ci_lower: float
    sharpe_ci_upper: float
    sortino: float
    max_drawdown: float
    calmar: float
    hit_rate_vs_benchmark: float
    n_months: int
    n_rebalances: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def stationary_bootstrap_sharpe_ci(
    excess_returns: np.ndarray,
    block_length: int,
    n_reps: int,
    rng: np.random.Generator,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Politis-Romano (1994) stationary block bootstrap for annualized Sharpe.

    Parameters
    ----------
    excess_returns : np.ndarray
        Monthly log excess returns (already net of risk-free).
    block_length : int
        Mean block length (geometric draw with p = 1/block_length).
    n_reps : int
        Number of bootstrap replications.
    rng : np.random.Generator
    alpha : float, default 0.05
        Two-sided CI level → 100(1-alpha)%.

    Returns
    -------
    (ci_lower, ci_upper) : tuple of float
    """
    excess_returns = np.asarray(excess_returns, dtype="float64")
    n = excess_returns.size
    if n < 2:
        return float("nan"), float("nan")
    p = 1.0 / max(block_length, 1)
    sharpes = np.empty(n_reps, dtype="float64")
    for r in range(n_reps):
        sample = np.empty(n, dtype="float64")
        idx = int(rng.integers(0, n))
        sample[0] = excess_returns[idx]
        # Vectorized restart mask: True where we should jump to a new block.
        restarts = rng.random(n - 1) < p
        new_starts = rng.integers(0, n, size=(n - 1,))
        for i in range(1, n):
            if restarts[i - 1]:
                idx = int(new_starts[i - 1])
            else:
                idx = (idx + 1) % n
            sample[i] = excess_returns[idx]
        sd = sample.std(ddof=1)
        sharpes[r] = (sample.mean() / sd) * np.sqrt(_MONTHS_PER_YEAR) if sd > 0 else 0.0
    lo = float(np.percentile(sharpes, 100 * alpha / 2))
    hi = float(np.percentile(sharpes, 100 * (1 - alpha / 2)))
    return lo, hi


def _annualized_cagr(log_returns: np.ndarray) -> float:
    """Log-mean × 12 (geometric annual mean of monthly log returns)."""
    if log_returns.size == 0:
        return float("nan")
    return float(np.exp(log_returns.mean() * _MONTHS_PER_YEAR) - 1.0)


def _annualized_sharpe(excess_log_returns: np.ndarray) -> float:
    if excess_log_returns.size < 2:
        return float("nan")
    sd = excess_log_returns.std(ddof=1)
    if sd <= 0:
        return float("nan")
    return float((excess_log_returns.mean() / sd) * np.sqrt(_MONTHS_PER_YEAR))


def _annualized_sortino(excess_log_returns: np.ndarray) -> float:
    downside = excess_log_returns[excess_log_returns < 0]
    if downside.size < 2:
        return float("nan")
    dd = downside.std(ddof=1)
    if dd <= 0:
        return float("nan")
    return float((excess_log_returns.mean() / dd) * np.sqrt(_MONTHS_PER_YEAR))


def _max_drawdown(nav: pd.Series) -> float:
    nav = nav.dropna()
    if nav.empty:
        return float("nan")
    dd = nav / nav.cummax() - 1.0
    return float(dd.min())


def _metrics_for(
    returns: pd.Series,
    rf_returns: pd.Series,
    nav: pd.Series,
    n_rebalances: int,
    benchmark_returns: pd.Series | None,
    bootstrap_reps: int,
    block_length_months: int,
    rng: np.random.Generator,
) -> PerformanceMetrics:
    r = returns.dropna()
    rf = rf_returns.reindex(r.index)
    excess = (r - rf).to_numpy()
    cagr = _annualized_cagr(r.to_numpy())
    sharpe = _annualized_sharpe(excess)
    if bootstrap_reps > 0 and excess.size >= 2:
        ci_lo, ci_hi = stationary_bootstrap_sharpe_ci(
            excess, block_length=block_length_months, n_reps=bootstrap_reps, rng=rng
        )
    else:
        ci_lo, ci_hi = float("nan"), float("nan")
    sortino = _annualized_sortino(excess)
    max_dd = _max_drawdown(nav)
    calmar = cagr / abs(max_dd) if max_dd and not np.isnan(max_dd) and max_dd != 0 else float("nan")

    if benchmark_returns is not None:
        bm = benchmark_returns.reindex(r.index).dropna()
        common = r.index.intersection(bm.index)
        if len(common) > 0:
            hit_rate = float((r.loc[common] > bm.loc[common]).mean())
        else:
            hit_rate = float("nan")
    else:
        hit_rate = float("nan")

    return PerformanceMetrics(
        cagr=cagr,
        sharpe=sharpe,
        sharpe_ci_lower=ci_lo,
        sharpe_ci_upper=ci_hi,
        sortino=sortino,
        max_drawdown=max_dd,
        calmar=calmar,
        hit_rate_vs_benchmark=hit_rate,
        n_months=int(r.size),
        n_rebalances=int(n_rebalances),
    )


def compute_performance(
    df: pd.DataFrame,
    bootstrap_reps: int = 10_000,
    block_length_months: int = 12,
    rng_seed: int = 42,
) -> dict[str, PerformanceMetrics]:
    """Compute strategy + benchmark PerformanceMetrics from a backtest DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Output of :func:`src.backtest.engine.run_backtest`.
    bootstrap_reps : int, default 10_000
        Stationary block bootstrap replications for Sharpe CI.
    block_length_months : int, default 12
        Mean block length in months (Politis-Romano).
    rng_seed : int, default 42

    Returns
    -------
    {"strategy": PerformanceMetrics, "benchmark": PerformanceMetrics}
    """
    rng = np.random.default_rng(rng_seed)
    # Use the same RNG draws so the two CIs are comparable; advance to different
    # streams internally by spawning child RNGs.
    rng_strat, rng_bench = rng.spawn(2)

    strategy_return = df["strategy_return"]
    equity_return = df["equity_return"]
    rf_return = df["rf_return"]
    strategy_nav = df["strategy_nav"]
    benchmark_nav = df["benchmark_nav"]
    n_rebalances = int((df["rebalance_cost"].abs() > 1e-9).sum())

    return {
        "strategy": _metrics_for(
            strategy_return,
            rf_return,
            strategy_nav,
            n_rebalances,
            benchmark_returns=equity_return,
            bootstrap_reps=bootstrap_reps,
            block_length_months=block_length_months,
            rng=rng_strat,
        ),
        "benchmark": _metrics_for(
            equity_return,
            rf_return,
            benchmark_nav,
            n_rebalances=0,
            benchmark_returns=equity_return,
            bootstrap_reps=bootstrap_reps,
            block_length_months=block_length_months,
            rng=rng_bench,
        ),
    }


__all__ = [
    "PerformanceMetrics",
    "stationary_bootstrap_sharpe_ci",
    "compute_performance",
]
