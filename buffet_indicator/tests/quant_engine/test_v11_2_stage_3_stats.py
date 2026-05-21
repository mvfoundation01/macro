"""v11.2 Stage 3 — V1-vs-V2 statistical tests (Jobson-Korkie, Reality Check, Holm-Šidák)."""
from __future__ import annotations


import numpy as np
import pandas as pd
import pytest

from src.quant_engine.mv_conditional import QE_LATEST_DIR
from src.quant_engine.stats_v1_v2 import (
    holm_sidak_correction,
    jobson_korkie_test,
    whites_reality_check,
)

V2_STATS_CSV = QE_LATEST_DIR / "v2_statistical_tests.csv"


# 1. Jobson-Korkie + Memmel — synthetic known-result test.
def test_jobson_korkie_with_memmel_correction():
    """Verify the test detects clear Sharpe differences but does NOT
    over-reject when independent series have similar Sharpes."""
    rng = np.random.default_rng(seed=42)
    n = 240  # 20 years monthly
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")

    # Case A: INDEPENDENT series drawn from the same distribution.
    # Same Sharpe in expectation, no shared signal → high p-value expected.
    r1 = pd.Series(rng.normal(0.008, 0.04, n), index=idx)
    r2 = pd.Series(rng.normal(0.008, 0.04, n), index=idx)
    result_a = jobson_korkie_test(r1, r2)
    assert result_a["n_obs"] == n
    assert result_a["p_value"] > 0.05, (
        f"identical-Sharpe independent series should not reject H0, "
        f"got p={result_a['p_value']:.4f} (sharpe_diff={result_a['sharpe_diff']:.3f})"
    )

    # Case B: very different Sharpes (independent series).
    r3 = pd.Series(rng.normal(0.001, 0.06, n), index=idx)  # near-zero Sharpe, high vol
    r4 = pd.Series(rng.normal(0.025, 0.03, n), index=idx)  # high Sharpe, low vol
    result_b = jobson_korkie_test(r3, r4)
    assert result_b["sharpe_v2"] > result_b["sharpe_v1"], (
        f"r4 should have higher Sharpe (got v1={result_b['sharpe_v1']:.3f} v2={result_b['sharpe_v2']:.3f})"
    )
    assert result_b["p_value"] < 0.05, f"clearly different Sharpes should reject H0, got p={result_b['p_value']:.4f}"


# 2. White's Reality Check p-value in [0, 1].
def test_whites_reality_check_p_value_in_range():
    rng = np.random.default_rng(seed=7)
    n = 120
    idx = pd.date_range("2010-01-31", periods=n, freq="ME")
    benchmark = pd.Series(rng.normal(0.008, 0.04, n), index=idx)
    rules = {
        "Rule_A": pd.Series(rng.normal(0.008, 0.04, n), index=idx),
        "Rule_B": pd.Series(rng.normal(0.010, 0.04, n), index=idx),
        "Rule_C": pd.Series(rng.normal(0.005, 0.04, n), index=idx),
    }
    out = whites_reality_check(benchmark, rules, n_bootstrap=500, seed=42)
    assert 0.0 <= out["p_value_reality_check"] <= 1.0, (
        f"reality check p={out['p_value_reality_check']} out of [0,1]"
    )
    assert out["best_rule"] in rules


# 3. Holm-Šidák step-down on known values.
def test_holm_sidak_step_down():
    # 3 p-values: only the smallest should reject at family α=0.05.
    p_values = [0.001, 0.030, 0.500]
    rejected = holm_sidak_correction(p_values, alpha=0.05)
    # Smallest (0.001) vs threshold 1 - 0.95^(1/3) ≈ 0.0170 → reject.
    # Next (0.030) vs threshold 1 - 0.95^(1/2) ≈ 0.0253 → 0.030 > 0.0253 → no reject; stop.
    # Last → no reject.
    assert rejected[0] is True, f"p=0.001 should reject; got {rejected}"
    assert rejected[1] is False, f"p=0.030 should NOT reject (step-down stops); got {rejected}"
    assert rejected[2] is False, f"p=0.500 should NOT reject; got {rejected}"

    # All-significant case.
    all_low = [0.001, 0.005, 0.010]
    rejected_all = holm_sidak_correction(all_low, alpha=0.05)
    assert all(rejected_all), f"all three should reject; got {rejected_all}"


# 4. V2 statistical tests CSV emitted.
@pytest.mark.skipif(not V2_STATS_CSV.exists(),
                    reason="v2_statistical_tests.csv not yet emitted (Stage 3 orchestrator pending)")
def test_v2_statistical_tests_csv_emitted():
    df = pd.read_csv(V2_STATS_CSV)
    assert len(df) == 3, f"expected 3 rules (R-PRIMARY, R-ALT1, R-ALT2), got {len(df)}"
    expected_cols = {"rule", "jk_sharpe_diff", "jk_p_value", "reality_check_p",
                     "holm_sidak_reject", "bootstrap_ci_low", "bootstrap_ci_high"}
    assert expected_cols.issubset(df.columns), (
        f"missing columns: {expected_cols - set(df.columns)}"
    )
    # At least one row should have a Reality Check p (best rule).
    assert df["reality_check_p"].notna().sum() >= 1, (
        "no row carries reality_check_p (should be set on best rule)"
    )
