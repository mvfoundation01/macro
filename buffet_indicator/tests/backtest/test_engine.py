"""Spec v10.0 §1.3 — backtest engine unit tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.backtest.engine import (  # noqa: E402
    BacktestConfig,
    compute_target_weight,
    run_backtest,
)


def test_compute_target_weight_thresholds() -> None:
    cfg = BacktestConfig()
    assert compute_target_weight(3.0, cfg) == 0.0
    assert compute_target_weight(2.0, cfg) == 0.5  # boundary → mid
    assert compute_target_weight(0.0, cfg) == 0.5
    assert compute_target_weight(-1.0, cfg) == 0.5  # boundary → mid
    assert compute_target_weight(-2.0, cfg) == 1.0
    assert np.isnan(compute_target_weight(float("nan"), cfg))


def test_run_backtest_returns_required_columns() -> None:
    rng = np.random.RandomState(42)
    idx = pd.date_range("2010-01-31", periods=60, freq="ME")
    z = pd.Series(rng.randn(60), index=idx)
    eq = pd.Series(rng.randn(60) * 0.04, index=idx)
    rf = pd.Series(np.ones(60) * 0.001, index=idx)
    result = run_backtest(z, eq, rf)
    required = {
        "z",
        "target_weight",
        "applied_weight",
        "equity_return",
        "rf_return",
        "rebalance_cost",
        "strategy_return",
        "strategy_nav",
        "benchmark_nav",
        "drawdown_strategy",
        "drawdown_benchmark",
    }
    assert required.issubset(result.columns)
    assert len(result) == 60


def test_run_backtest_no_lookahead() -> None:
    """Truncate the input → first len(truncated) rows of the truncated result
    must equal the corresponding rows of the full-sample result, exactly."""
    idx = pd.date_range("2010-01-31", periods=60, freq="ME")
    z = pd.Series(np.linspace(-2, 2, 60), index=idx)
    eq = pd.Series(np.ones(60) * 0.005, index=idx)
    rf = pd.Series(np.ones(60) * 0.001, index=idx)
    full = run_backtest(z, eq, rf)
    truncated = run_backtest(z.iloc[:40], eq.iloc[:40], rf.iloc[:40])
    # Strategy NAV and applied weight on overlap must match
    pd.testing.assert_series_equal(
        full["strategy_nav"].iloc[:40],
        truncated["strategy_nav"],
        check_names=False,
        atol=1e-9,
    )
    pd.testing.assert_series_equal(
        full["applied_weight"].iloc[:40],
        truncated["applied_weight"],
        check_names=False,
        atol=1e-9,
    )


def test_run_backtest_target_weight_lagged_one_month() -> None:
    """Weight in force during month t derives from z at end of month t-1."""
    idx = pd.date_range("2010-01-31", periods=4, freq="ME")
    z = pd.Series([+3.0, -2.0, 0.0, +3.0], index=idx)
    eq = pd.Series([0.01, 0.01, 0.01, 0.01], index=idx)
    rf = pd.Series([0.001, 0.001, 0.001, 0.001], index=idx)
    df = run_backtest(z, eq, rf)
    assert pd.isna(df["applied_weight"].iloc[0])  # no prior z
    assert df["applied_weight"].iloc[1] == 0.0  # z[0]=+3 → cash
    assert df["applied_weight"].iloc[2] == 1.0  # z[1]=-2 → full eq
    assert df["applied_weight"].iloc[3] == 0.5  # z[2]=0 → mid


def test_run_backtest_transaction_cost_charged_on_change() -> None:
    """Cost fires when |Δw| > rebalance_threshold."""
    idx = pd.date_range("2010-01-31", periods=5, freq="ME")
    z = pd.Series([+3.0, -2.0, +3.0, -2.0, +3.0], index=idx)
    eq = pd.Series([0.0] * 5, index=idx)
    rf = pd.Series([0.0] * 5, index=idx)
    df = run_backtest(z, eq, rf, BacktestConfig(transaction_cost_bps=10.0))
    fired = (df["rebalance_cost"].abs() > 1e-6).sum()
    # Each toggle of z creates a w-toggle; 5 z values give 4 transitions, but
    # the first row has NaN applied_weight, so we expect at least 2 fired
    # cost events (z[1]→z[2], z[2]→z[3], etc.).
    assert fired >= 2


def test_run_backtest_drawdown_computed_correctly() -> None:
    """Drawdown = nav / cummax(nav) - 1; always ≤ 0."""
    idx = pd.date_range("2010-01-31", periods=10, freq="ME")
    eq = pd.Series(
        [0.1, -0.2, 0.05, -0.1, 0.0, 0.05, 0.05, 0.05, 0.05, 0.05], index=idx
    )
    z = pd.Series([-2.0] * 10, index=idx)  # always full equity → strategy ≈ benchmark
    rf = pd.Series([0.0] * 10, index=idx)
    df = run_backtest(z, eq, rf)
    # Benchmark must show a notable drawdown after -0.2 month
    assert df["drawdown_benchmark"].min() < -0.1
    # All drawdowns ≤ 0 (allowing small float epsilon)
    assert (df["drawdown_benchmark"].dropna() <= 1e-9).all()
    assert (df["drawdown_strategy"].dropna() <= 1e-9).all()


# ===========================================================================
# v10.0 §2 — performance metrics + bootstrap CI tests
# ===========================================================================


def test_performance_metrics_all_fields_populated() -> None:
    from src.backtest.metrics import compute_performance

    rng = np.random.RandomState(7)
    idx = pd.date_range("2000-01-31", periods=240, freq="ME")
    z = pd.Series(rng.randn(240), index=idx)
    eq = pd.Series(rng.randn(240) * 0.04 + 0.005, index=idx)  # ~6%/yr drift
    rf = pd.Series(rng.randn(240) * 0.001 + 0.002, index=idx)
    df = run_backtest(z, eq, rf)
    perf = compute_performance(df, bootstrap_reps=1000)
    assert "strategy" in perf and "benchmark" in perf
    for label in ("strategy", "benchmark"):
        m = perf[label]
        assert isinstance(m.sharpe, float)
        # CI brackets the point estimate
        assert m.sharpe_ci_lower <= m.sharpe <= m.sharpe_ci_upper
        assert m.max_drawdown <= 0
        assert 0 <= m.hit_rate_vs_benchmark <= 1
        assert m.n_months <= 240


def test_sharpe_bootstrap_ci_contains_point_estimate() -> None:
    from src.backtest.metrics import stationary_bootstrap_sharpe_ci

    rng = np.random.default_rng(42)
    returns = rng.normal(loc=0.005, scale=0.04, size=300)
    point_sharpe = (returns.mean() / returns.std(ddof=1)) * np.sqrt(12)
    lo, hi = stationary_bootstrap_sharpe_ci(
        returns, block_length=12, n_reps=2000, rng=rng
    )
    assert lo <= point_sharpe <= hi


# ===========================================================================
# v10.0 §3.1 — data loader integration test
# ===========================================================================


def test_load_backtest_inputs_returns_aligned_series() -> None:
    """The live Shiller-derived backtest inputs are aligned, dense, sized > 60 mo."""
    from src.backtest.data import load_backtest_inputs

    try:
        z, eq, rf = load_backtest_inputs()
    except FileNotFoundError:
        # Skip if z_history.parquet doesn't exist (haven't run orchestrator yet)
        import pytest
        pytest.skip("z_history.parquet not available — run orchestrator first.")
    assert z.index.equals(eq.index)
    assert eq.index.equals(rf.index)
    assert len(z) >= 60
    assert not z.isna().any()
    assert not eq.isna().any()
    assert not rf.isna().any()


def test_real_data_backtest_acceptance_gates() -> None:
    """Real-data backtest produces finite/sensible headline metrics."""
    from pathlib import Path

    import pytest

    perf_path = Path("outputs/backtest/performance.json")
    if not perf_path.exists():
        pytest.skip("outputs/backtest/performance.json missing — run `cli backtest`.")
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    n = perf["window"]["n_months"]
    assert n >= 800, f"n_months {n} below spec target 800"
    assert perf["n_rebalances"] < n / 6, "Over-trading: too many rebalances"
    s = perf["strategy"]
    b = perf["benchmark"]
    assert -2 < s["sharpe"] < 3
    assert -2 < b["sharpe"] < 3
    assert s["max_drawdown"] < 0
    assert b["max_drawdown"] < 0
    # Strategy max DD should be LESS NEGATIVE than benchmark (the whole point)
    assert s["max_drawdown"] >= b["max_drawdown"], (
        f"Strategy MaxDD {s['max_drawdown']:.3f} should be >= benchmark "
        f"{b['max_drawdown']:.3f} (less negative)"
    )
