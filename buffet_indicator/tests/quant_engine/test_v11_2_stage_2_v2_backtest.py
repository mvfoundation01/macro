"""v11.2 Stage 2 — V2 backtest unit + integration tests."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.quant_engine.mv_conditional import (
    QE_LATEST_DIR,
    apply_mv_conditional,
    compute_pit_zscore,
    rule_r_alt1,
    rule_r_alt2,
    rule_r_primary,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
V2_LATEST_CSV = QE_LATEST_DIR / "v2_latest.csv"


# 1. PIT z-score: at date t, output uses only data ≤ t-1
def test_pit_zscore_no_lookahead():
    # Two series identical up to index t, then diverging — z at index t must match.
    idx = pd.date_range("2000-01-31", periods=120, freq="ME")
    base = pd.Series(np.linspace(0.0, 1.0, 120), index=idx)
    diverged = base.copy()
    # Mutate everything AT and AFTER index t. PIT z at index t should be unchanged
    # (because compute_pit_zscore uses shift(1), so z[t] depends only on values 0..t-1).
    t = 80
    diverged.iloc[t:] = diverged.iloc[t:] + 100.0

    z_base = compute_pit_zscore(base, min_periods=12)
    z_div = compute_pit_zscore(diverged, min_periods=12)
    assert pd.isna(z_base.iloc[t]) == pd.isna(z_div.iloc[t]), "both should be NaN/non-NaN equally"
    if not pd.isna(z_base.iloc[t]):
        assert abs(z_base.iloc[t] - z_div.iloc[t]) < 1e-9, (
            "PIT z at date t leaks future data — should depend only on values < t"
        )


# 2. R-PRIMARY fires only when BOTH MVCI > 1.5 AND MRC > 0.5
def test_rule_r_primary_fires_on_combined_threshold():
    idx = pd.date_range("2020-01-31", periods=6, freq="ME")
    z_mvci = pd.Series([2.0,  2.0, 1.0, 1.0,  -0.5, 1.6], index=idx)
    z_mrc  = pd.Series([1.0, -0.5, 1.0, -0.5,  1.5, 0.6], index=idx)
    w = rule_r_primary(z_mvci, z_mrc)
    expected = pd.Series([0.5, 1.0, 1.0, 1.0, 1.0, 0.5], index=idx, dtype="float64")
    pd.testing.assert_series_equal(w.astype("float64"), expected, check_names=False)


# 3. R-ALT1 single-signal threshold (MVCI > 2.0 alone)
def test_rule_r_alt1_fires_on_mvci_alone():
    idx = pd.date_range("2020-01-31", periods=4, freq="ME")
    z_mvci = pd.Series([2.5, 2.01, 1.99, -1.0], index=idx)
    w = rule_r_alt1(z_mvci)
    assert list(w.values) == [0.5, 0.5, 1.0, 1.0]


# 4. R-ALT2 continuous gradient stays in [0.5, 1.0] bounds
def test_rule_r_alt2_continuous_gradient():
    rng = np.random.default_rng(seed=42)
    idx = pd.date_range("1990-01-31", periods=400, freq="ME")
    z_mvci = pd.Series(rng.normal(0, 1, 400), index=idx)
    z_mrc = pd.Series(rng.normal(0, 1, 400), index=idx)
    # Inject extreme stress.
    z_mvci.iloc[100] = 5.0
    z_mrc.iloc[100] = 5.0
    z_mvci.iloc[200] = -5.0
    z_mrc.iloc[200] = -5.0
    w = rule_r_alt2(z_mvci, z_mrc)
    assert (w >= 0.50 - 1e-9).all(), "R-ALT2 below 0.50 lower bound"
    assert (w <= 1.00 + 1e-9).all(), "R-ALT2 above 1.00 upper bound"
    # Calm regime → w ≈ 1.0; extreme stress → w → 0.50.
    calm_w = w.iloc[50]
    stress_w = w.iloc[100]
    assert calm_w > 0.9, f"calm regime weight {calm_w} unexpectedly low"
    assert stress_w <= 0.55, f"extreme-stress weight {stress_w} unexpectedly high"


# 5. V2 returns alignment — no NaN in final series
def test_v2_returns_alignment():
    rng = np.random.default_rng(seed=1)
    idx = pd.date_range("2010-01-31", periods=60, freq="ME")
    combo = pd.Series(rng.normal(0.01, 0.03, 60), index=idx)
    tbill = pd.Series(0.002, index=idx)
    weights = pd.Series(1.0, index=idx)
    weights.iloc[10:20] = 0.5
    v2 = apply_mv_conditional(combo, weights, tbill, rebal_cost_bps=3.0)
    assert not v2.isna().any(), f"V2 series has NaNs:\n{v2[v2.isna()]}"
    assert (v2.index == v2.index.to_period("M").to_timestamp(how="end").normalize()).all() or \
           v2.index.freq is not None, "V2 index not month-end-aligned"


# 6. Rebal cost applied on weight changes — 3 bps deduction visible
def test_v2_rebal_cost_applied_on_weight_change():
    idx = pd.date_range("2020-01-31", periods=6, freq="ME")
    combo = pd.Series(0.01, index=idx)   # 1% per month
    tbill = pd.Series(0.01, index=idx)   # same, so cost-free portion would yield 0.01
    weights = pd.Series([1.0, 0.5, 0.5, 1.0, 1.0, 0.5], index=idx)
    v2 = apply_mv_conditional(combo, weights, tbill, rebal_cost_bps=3.0)
    # In every aligned month, w*r_combo + (1-w)*r_tbill = 0.01 (since both = 1%).
    # When weight transitions, V2 should be 0.01 - 0.0003 = 0.0097.
    # No-cost month value should equal 0.01.
    nominal = 0.01
    cost = 3.0 / 10_000.0
    transitions = (weights.shift(1) != weights.shift(2)).fillna(False)
    # V2 is indexed starting from aligned[1] (because shift(1) drops first row).
    for i, t in enumerate(v2.index):
        expected_cost = cost if transitions.get(t, False) else 0.0
        # First row of aligned (i==0): cost forced to 0 in our impl.
        if i == 0:
            expected_cost = 0.0
        expected = nominal - expected_cost
        assert abs(v2.iloc[i] - expected) < 1e-9, (
            f"month {t}: v2={v2.iloc[i]:.6f} expected={expected:.6f}"
        )


# 7. V2 CSV emitted with 3 rules × 8 cycles × 5 costs = 120 rows.
@pytest.mark.skipif(not V2_LATEST_CSV.exists(),
                    reason="v2_latest.csv not yet emitted (v50 EXPORT_RETURNS run pending)")
def test_v2_csv_emitted():
    df = pd.read_csv(V2_LATEST_CSV)
    assert len(df) == 120, f"expected 120 rows (3 rules × 8 periods × 5 costs), got {len(df)}"
    assert set(df["label"].unique()) == {"V2_R-PRIMARY", "V2_R-ALT1", "V2_R-ALT2"}, (
        f"unexpected label set: {sorted(df['label'].unique())}"
    )
    assert set(df["_costbps"].unique()) == {15, 30, 45, 75, 100}, (
        f"unexpected cost set: {sorted(df['_costbps'].unique())}"
    )
    # 8 periods: 1 FULL + 7 cycles.
    assert df["period"].nunique() == 8, f"expected 8 periods, got {df['period'].nunique()}"


# 8. V2 metrics in sanity ranges.
@pytest.mark.skipif(not V2_LATEST_CSV.exists(),
                    reason="v2_latest.csv not yet emitted")
def test_v2_metrics_within_sanity_ranges():
    df = pd.read_csv(V2_LATEST_CSV)
    # Drop NaN rows (when underlying combo CSV missing for a cost level — they're
    # placeholders and shouldn't be sanity-checked).
    df = df.dropna(subset=["cagr", "sharpe", "maxdd"])
    if df.empty:
        pytest.skip("all rows NaN — combo monthly returns CSV missing")
    assert (df["cagr"].between(-0.50, 0.50)).all(), \
        f"CAGR out of [-50%, 50%]:\n{df[~df['cagr'].between(-0.50, 0.50)][['label','period','_costbps','cagr']]}"
    assert (df["sharpe"].between(-3.0, 3.0)).all(), \
        f"Sharpe out of [-3, 3]:\n{df[~df['sharpe'].between(-3.0, 3.0)][['label','period','_costbps','sharpe']]}"
    assert (df["maxdd"].between(-0.95, 0.0)).all(), \
        f"MaxDD out of [-95%, 0]:\n{df[~df['maxdd'].between(-0.95, 0.0)][['label','period','_costbps','maxdd']]}"
