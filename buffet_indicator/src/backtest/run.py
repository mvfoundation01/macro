"""End-to-end backtest runner (Spec v10.0 §3).

CLI entry: ``python -m src.cli backtest``.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any


from src.backtest.data import load_backtest_inputs
from src.backtest.engine import BacktestConfig, run_backtest
from src.backtest.metrics import compute_performance

logger = logging.getLogger(__name__)


def run_real_data_backtest(
    seed: int = 42,
    bootstrap_reps: int = 10_000,
    outdir: Path | None = None,
) -> dict[str, Any]:
    """Run the full 1876-2026 tactical backtest on live data and persist outputs.

    Persists to ``outputs/backtest/``:
      - equity_curve.parquet      (date, strategy_nav, benchmark_nav)
      - drawdown.parquet          (date, drawdown_strategy, drawdown_benchmark)
      - weights.parquet           (date, applied_weight, z)
      - rebalance_log.parquet     (date, weight_change, cost_bps)
      - performance.json          (strategy + benchmark PerformanceMetrics)

    Returns a summary dict with headline metrics.
    """
    if outdir is None:
        outdir = Path("outputs/backtest")
    outdir.mkdir(parents=True, exist_ok=True)

    mvci_z, equity_return, rf_return = load_backtest_inputs()
    config = BacktestConfig()
    df = run_backtest(mvci_z, equity_return, rf_return, config)
    perf = compute_performance(df, bootstrap_reps=bootstrap_reps, rng_seed=seed)

    # 1. equity_curve
    equity_curve = df[["strategy_nav", "benchmark_nav"]].copy()
    equity_curve.index.name = "date"
    equity_curve.reset_index().to_parquet(outdir / "equity_curve.parquet", index=False)

    # 2. drawdown
    dd = df[["drawdown_strategy", "drawdown_benchmark"]].copy()
    dd.index.name = "date"
    dd.reset_index().to_parquet(outdir / "drawdown.parquet", index=False)

    # 3. weights
    weights = df[["applied_weight", "z", "target_weight"]].copy()
    weights.index.name = "date"
    weights.reset_index().to_parquet(outdir / "weights.parquet", index=False)

    # 4. rebalance log
    fired = df["rebalance_cost"].abs() > 1e-9
    rebalances = df.loc[fired, ["applied_weight", "rebalance_cost"]].copy()
    rebalances["weight_change"] = df.loc[fired, "applied_weight"].diff()
    rebalances["cost_bps"] = rebalances["rebalance_cost"] * 10_000
    rebalances.index.name = "date"
    rebalances.reset_index().to_parquet(
        outdir / "rebalance_log.parquet", index=False
    )

    # 5. performance.json
    perf_json = {
        "strategy": asdict(perf["strategy"]),
        "benchmark": asdict(perf["benchmark"]),
        "config": {
            "upper_threshold": config.upper_threshold,
            "lower_threshold": config.lower_threshold,
            "mid_weight": config.mid_weight,
            "transaction_cost_bps": config.transaction_cost_bps,
            "rebalance_threshold": config.rebalance_threshold,
        },
        "window": {
            "start": str(df.index.min().date()),
            "end": str(df.index.max().date()),
            "n_months": int(len(df)),
        },
        "n_rebalances": int(fired.sum()),
        "bootstrap_reps": bootstrap_reps,
        "seed": seed,
    }
    (outdir / "performance.json").write_text(
        json.dumps(perf_json, indent=2, default=str), encoding="utf-8"
    )

    # 6. Headline summary log
    s = perf["strategy"]
    b = perf["benchmark"]
    logger.info(
        "Backtest results: %d months from %s to %s; %d rebalances",
        len(df),
        df.index.min().date(),
        df.index.max().date(),
        int(fired.sum()),
    )

    summary = {
        "n_months": int(len(df)),
        "start": str(df.index.min().date()),
        "end": str(df.index.max().date()),
        "n_rebalances": int(fired.sum()),
        "strategy_cagr": s.cagr,
        "benchmark_cagr": b.cagr,
        "strategy_sharpe": s.sharpe,
        "strategy_sharpe_ci": [s.sharpe_ci_lower, s.sharpe_ci_upper],
        "benchmark_sharpe": b.sharpe,
        "benchmark_sharpe_ci": [b.sharpe_ci_lower, b.sharpe_ci_upper],
        "strategy_max_dd": s.max_drawdown,
        "benchmark_max_dd": b.max_drawdown,
        "strategy_calmar": s.calmar,
        "benchmark_calmar": b.calmar,
        "hit_rate_vs_benchmark": s.hit_rate_vs_benchmark,
    }
    return summary


def _format_pct(x: float, digits: int = 2) -> str:
    if x is None or x != x:
        return "n/a"
    return f"{x * 100:+.{digits}f}%"


def _format_float(x: float, digits: int = 2) -> str:
    if x is None or x != x:
        return "n/a"
    return f"{x:+.{digits}f}"


def print_summary(summary: dict[str, Any]) -> None:
    """Pretty-print the backtest summary to stdout."""
    print("=" * 72)
    print(
        f"Backtest window: {summary['start']} -> {summary['end']} "
        f"({summary['n_months']} months, {summary['n_rebalances']} rebalances)"
    )
    print("=" * 72)
    print(f"{'Metric':<28}{'Strategy':>22}{'Benchmark':>22}")
    print("-" * 72)
    print(
        f"{'CAGR (real)':<28}"
        f"{_format_pct(summary['strategy_cagr']):>22}"
        f"{_format_pct(summary['benchmark_cagr']):>22}"
    )
    s_ci = summary["strategy_sharpe_ci"]
    b_ci = summary["benchmark_sharpe_ci"]
    print(
        f"{'Sharpe (annualized)':<28}"
        f"{_format_float(summary['strategy_sharpe']) + f' [{s_ci[0]:+.2f},{s_ci[1]:+.2f}]':>22}"
        f"{_format_float(summary['benchmark_sharpe']) + f' [{b_ci[0]:+.2f},{b_ci[1]:+.2f}]':>22}"
    )
    print(
        f"{'Max drawdown':<28}"
        f"{_format_pct(summary['strategy_max_dd']):>22}"
        f"{_format_pct(summary['benchmark_max_dd']):>22}"
    )
    print(
        f"{'Calmar ratio':<28}"
        f"{_format_float(summary['strategy_calmar']):>22}"
        f"{_format_float(summary['benchmark_calmar']):>22}"
    )
    print(
        f"{'Hit rate vs benchmark':<28}"
        f"{_format_pct(summary['hit_rate_vs_benchmark'], 1):>22}"
        f"{'—':>22}"
    )
    print("=" * 72)


__all__ = ["run_real_data_backtest", "print_summary"]
