"""Tactical backtest engine for MVCI signal validation (Spec v10.0).

Implements the master spec §13 binary allocation rule with proper look-ahead
discipline, transaction costs, and risk-free rate handling.

References
----------
Master spec §13 — "Backtest a simple tactical allocation that goes 100%
T-bills when AMVI > 2 SD and 100% equities when AMVI < −1 SD."
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    """All knobs for a single backtest run.

    Attributes
    ----------
    upper_threshold : float, default +2.0
        z strictly above this → 0% equities (full T-bills).
    lower_threshold : float, default -1.0
        z strictly below this → 100% equities.
    mid_weight : float, default 0.5
        Equity weight when z is in [lower_threshold, upper_threshold] band.
    transaction_cost_bps : float, default 10.0
        Round-trip cost in basis points, charged per unit of weight change.
    rebalance_threshold : float, default 0.01
        Minimum |Δw| to trigger a costed rebalance (1% band).
    """

    upper_threshold: float = 2.0
    lower_threshold: float = -1.0
    mid_weight: float = 0.5
    transaction_cost_bps: float = 10.0
    rebalance_threshold: float = 0.01


def compute_target_weight(z: float, config: BacktestConfig) -> float:
    """Map MVCI z-score to target equity weight per the master spec §13 rule.

    Parameters
    ----------
    z : float
        Long-run frame z-score of MVCI composite at month-end t.
        NaN propagates to NaN.
    config : BacktestConfig

    Returns
    -------
    float
        Equity weight in {0.0, ``mid_weight``, 1.0}. NaN if input is NaN.

    Examples
    --------
    >>> compute_target_weight(3.0, BacktestConfig())
    0.0
    >>> compute_target_weight(2.0, BacktestConfig())
    0.5
    >>> compute_target_weight(0.0, BacktestConfig())
    0.5
    >>> compute_target_weight(-1.0, BacktestConfig())
    0.5
    >>> compute_target_weight(-2.0, BacktestConfig())
    1.0
    """
    if pd.isna(z):
        return float("nan")
    if z > config.upper_threshold:
        return 0.0
    if z < config.lower_threshold:
        return 1.0
    return float(config.mid_weight)


def run_backtest(
    mvci_z: pd.Series,
    equity_returns: pd.Series,
    rf_returns: pd.Series,
    config: BacktestConfig | None = None,
) -> pd.DataFrame:
    """Run the tactical backtest with look-ahead-free signal lag.

    Parameters
    ----------
    mvci_z : pd.Series
        Month-end MVCI long-run z-score, indexed by month-end date. Must be
        expanding-window standardized upstream (no full-sample look-ahead).
    equity_returns : pd.Series
        Month-end log returns of S&P 500 total return index.
    rf_returns : pd.Series
        Month-end log returns of 3-month T-bill (DGS3MO with Shiller splice
        pre-1934).
    config : BacktestConfig, optional
        Default config matches master spec §13.

    Returns
    -------
    pd.DataFrame indexed by month-end date with columns:
        z, target_weight, applied_weight, equity_return, rf_return,
        rebalance_cost, strategy_return, strategy_nav, benchmark_nav,
        drawdown_strategy, drawdown_benchmark.

    Algorithm
    ---------
    1. Align the three series on the inner-join of indices.
    2. Compute ``target_weight_t`` at each month-end t from z_t (per rule).
    3. **Lag target_weight by 1 month** → ``applied_weight_t = target_weight_{t-1}``.
       This is the look-ahead guard: weight in force during month t is
       the target computed from z observed at end of month t-1.
    4. ``rebalance_cost_t = bps * |applied_weight_t - applied_weight_{t-1}|``
       only when |Δw| > ``rebalance_threshold``; else 0.
    5. ``strategy_return_t = w_t * eq_t + (1-w_t) * rf_t - cost_t`` (log space).
    6. NAV = exp(cumsum(returns)), starts at 1.0 on first valid row.
    7. Drawdown = NAV / cummax(NAV) - 1.

    Look-ahead audit
    ----------------
    Each row's ``strategy_return`` uses ONLY:
      - ``applied_weight_t`` (derived from ``z_{t-1}``),
      - ``equity_return_t`` (return DURING month t),
      - ``rf_return_t`` (return DURING month t),
      - ``rebalance_cost_t`` (charged at transition into month t).
    Verified by ``test_run_backtest_no_lookahead``.
    """
    cfg = config or BacktestConfig()

    # Align on inner-join.
    common = mvci_z.index.intersection(equity_returns.index).intersection(
        rf_returns.index
    )
    if len(common) == 0:
        raise ValueError(
            "run_backtest: no common dates across mvci_z, equity_returns, rf_returns."
        )
    z = mvci_z.loc[common].astype("float64").copy()
    eq = equity_returns.loc[common].astype("float64").copy()
    rf = rf_returns.loc[common].astype("float64").copy()

    # Target weight from current z (would be applied next month).
    target_weight = z.map(lambda v: compute_target_weight(v, cfg))

    # Look-ahead guard: weight in force at t is the target from t-1.
    applied_weight = target_weight.shift(1)
    # NaN target propagates → applied stays NaN until z lands.

    # Cost: charged on the transition into month t. The transition is from
    # applied_weight_{t-1} to applied_weight_t.
    weight_change = applied_weight.diff().abs()
    bps_decimal = cfg.transaction_cost_bps / 10_000.0
    fired = weight_change > cfg.rebalance_threshold
    rebalance_cost = weight_change.where(fired, 0.0) * bps_decimal
    rebalance_cost = rebalance_cost.fillna(0.0)

    # Strategy return: weighted sum minus cost. NaN where applied_weight is NaN.
    strategy_return = applied_weight * eq + (1.0 - applied_weight) * rf - rebalance_cost

    # Benchmark: always 100% equities.
    benchmark_return = eq

    # NAV from log returns: nav_t = exp(cumsum(r_t)).
    # First valid row anchored at 1.0; pre-NaN entries carry NaN.
    def _nav(r: pd.Series) -> pd.Series:
        r_clean = r.fillna(0.0)
        cum = r_clean.cumsum()
        nav = np.exp(cum)
        # Mask leading NaN (where applied_weight was NaN) with NaN nav, then
        # rebase so the first non-masked row is 1.0 (compounding-correct).
        mask = r.notna()
        if mask.any():
            first_valid = r.index[mask][0]
            anchor = float(np.exp(cum.loc[first_valid]))
            nav = nav / anchor
            # rows with NaN return get NaN nav
            nav.loc[~mask] = np.nan
        return nav

    strategy_nav = _nav(strategy_return)
    benchmark_nav = _nav(benchmark_return)

    def _drawdown(nav: pd.Series) -> pd.Series:
        running_max = nav.cummax()
        return nav / running_max - 1.0

    drawdown_strategy = _drawdown(strategy_nav)
    drawdown_benchmark = _drawdown(benchmark_nav)

    return pd.DataFrame(
        {
            "z": z,
            "target_weight": target_weight,
            "applied_weight": applied_weight,
            "equity_return": eq,
            "rf_return": rf,
            "rebalance_cost": rebalance_cost,
            "strategy_return": strategy_return,
            "strategy_nav": strategy_nav,
            "benchmark_nav": benchmark_nav,
            "drawdown_strategy": drawdown_strategy,
            "drawdown_benchmark": drawdown_benchmark,
        },
        index=common,
    )


__all__ = ["BacktestConfig", "compute_target_weight", "run_backtest"]
