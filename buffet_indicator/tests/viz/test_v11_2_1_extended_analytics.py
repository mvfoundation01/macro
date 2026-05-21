"""v11.2.1 — Extended Analytics surface tests (Stages 4-8).

One file per spec, growing as surfaces ship. Per spec §B.4: each surface
ships ≥ 2 tests — 1 structural (HTML elements exist, data binding works)
and 1 numerical (KPI value matches expected).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.quant_engine.extended_analytics import (
    V2_LABELS,
    _swr_survival_pct,
    build_drawdowns_surface,
    build_lump_sum_surface,
    build_returns_surface,
    build_risk_metrics_surface,
    build_risk_vs_return_surface,
    build_rolling_metrics_surface,
    build_seasonality_surface,
    build_summary_surface,
    build_withdrawal_surface,
    compute_rolling_metrics,
    find_drawdown_episodes,
    tag_episodes_with_macro_regime,
)
from src.quant_engine.analytics_core import StrategyReturns


def _two_strategy_fixture(seed: int = 17, n: int = 80) -> dict[str, StrategyReturns]:
    rng = np.random.default_rng(seed=seed)
    idx = pd.date_range("2015-01-31", periods=n, freq="ME")
    return {
        "V1_Combination": StrategyReturns(
            monthly=pd.Series(rng.normal(0.01, 0.04, n), index=idx),
            name="V1_Combination", color="#1f77b4",
        ),
        "V2_R-PRIMARY": StrategyReturns(
            monthly=pd.Series(rng.normal(0.008, 0.04, n), index=idx),
            name="V2_R-PRIMARY", color="#ff7f0e",
        ),
    }

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_HTML = REPO_ROOT / "outputs" / "dashboard.html"


def _read_dashboard() -> str:
    if not DASHBOARD_HTML.exists():
        pytest.skip(f"{DASHBOARD_HTML} not built yet — run `python -m src.cli dashboard`")
    return DASHBOARD_HTML.read_text(encoding="utf-8")


# ── Surface 1: Summary ───────────────────────────────────────────────────

def test_ea_surface_1_summary_structural_in_dashboard():
    """Surface 1 summary <details> block + headers + V1_Combination row exist."""
    html = _read_dashboard()
    assert 'id="ea-surface-1-summary"' in html, "Surface 1 <details> block missing"
    # Headers: must include CAGR + Sharpe + MaxDD columns (the bootstrap-CI ones).
    assert ">CAGR " in html or ">CAGR<" in html
    assert ">Sharpe " in html or ">Sharpe<" in html
    assert ">MaxDD " in html or ">MaxDD<" in html
    # V1 row must be present.
    assert "V1_Combination" in html, "V1_Combination row missing from Surface 1 table"
    # V2 DIAGNOSTIC tag must appear on V2 rows.
    assert "DIAGNOSTIC" in html, "DIAGNOSTIC tag missing on V2 rows in Surface 1"


def test_ea_surface_1_summary_numerical_synthetic():
    """build_summary_surface() on a synthetic 1-strategy fixture gives
    expected CAGR (within bootstrap tolerance) for that strategy."""
    rng = np.random.default_rng(seed=42)
    n = 120  # 10 years monthly
    idx = pd.date_range("2010-01-31", periods=n, freq="ME")
    # 1% monthly mean, 4% monthly vol → expected CAGR ≈ 12.7%, Sharpe ≈ 0.87
    monthly = rng.normal(0.01, 0.04, n)
    sr = StrategyReturns(monthly=pd.Series(monthly, index=idx), name="TEST_V1", color="#000")

    out = build_summary_surface(strategies={"TEST_V1": sr}, n_bootstrap=200, seed=42)
    assert out["available"] is True
    assert len(out["rows"]) == 1
    row = out["rows"][0]
    assert row["label"] == "TEST_V1"
    assert row["is_v2"] is False
    # CAGR ≈ (1+0.01)^12 - 1 = 12.68% (point), broad CI tolerance.
    assert 0.05 < row["cagr"] < 0.20, f"unexpected CAGR {row['cagr']:.4f}"
    # Sharpe ≈ (0.01/0.04) * sqrt(12) ≈ 0.866; broad tolerance.
    assert 0.4 < row["sharpe"] < 1.3, f"unexpected Sharpe {row['sharpe']:.4f}"
    # n_months exact match.
    assert row["n_months"] == n
    # Ending value reasonable.
    assert row["ending_value"] > 10_000  # positive total return


def test_ea_surface_1_v2_rows_tagged_diagnostic():
    """When V2_R-* strategies are present, their is_v2 flag must be True."""
    rng = np.random.default_rng(seed=7)
    idx = pd.date_range("2010-01-31", periods=60, freq="ME")
    fake_returns = pd.Series(rng.normal(0.008, 0.04, 60), index=idx)
    strats = {
        "V1_Combination": StrategyReturns(monthly=fake_returns, name="V1_Combination", color="#1f77b4"),
        "V2_R-PRIMARY":   StrategyReturns(monthly=fake_returns, name="V2_R-PRIMARY", color="#ff7f0e"),
        "V2_R-ALT2":      StrategyReturns(monthly=fake_returns, name="V2_R-ALT2", color="#d62728"),
    }
    out = build_summary_surface(strategies=strats, n_bootstrap=100, seed=42)
    by_label = {r["label"]: r for r in out["rows"]}
    assert by_label["V1_Combination"]["is_v2"] is False
    assert by_label["V2_R-PRIMARY"]["is_v2"] is True
    assert by_label["V2_R-ALT2"]["is_v2"] is True
    # All V2 labels recognized.
    assert all(label in V2_LABELS for label in ("V2_R-PRIMARY", "V2_R-ALT1", "V2_R-ALT2"))


# ── Surface 2: Drawdowns ─────────────────────────────────────────────────

def test_ea_surface_2_drawdowns_structural_in_dashboard():
    """Surface 2 <details> block + per-strategy episode tables + regime-overlay column."""
    html = _read_dashboard()
    assert 'id="ea-surface-2-drawdowns"' in html, "Surface 2 <details> block missing"
    assert "MVCI z@peak" in html, "Surface 2 missing MVCI z@peak column"
    assert "MRC z@peak" in html, "Surface 2 missing MRC z@peak column"
    assert "Regime @peak" in html, "Surface 2 missing Regime @peak column header"


def test_find_drawdown_episodes_numerical():
    """Synthetic returns with a known drawdown produce ≥ 1 recovered episode."""
    # 10 months of +1% → peak ~1.105.
    # 10 months of -3% → trough ~0.815 (-26.2% from peak).
    # 60 months of +2% → final ~0.815 × 1.02^60 = 2.674 (recovers ~ at month 16).
    rets = pd.Series(
        [0.01] * 10 + [-0.03] * 10 + [0.02] * 60,
        index=pd.date_range("2010-01-31", periods=80, freq="ME"),
    )
    episodes = find_drawdown_episodes(rets, min_depth=0.05)
    assert len(episodes) >= 1, "should detect at least one drawdown episode"
    deepest = episodes["depth_pct"].min()
    assert deepest < -0.15, f"deepest dd {deepest:.4f} should be < -15%"
    recovered = episodes[episodes["recovered"]]
    assert len(recovered) >= 1, "episode should have recovered within the +2% growth window"


# ── Surface 3: Rolling Metrics ───────────────────────────────────────────

def test_ea_surface_3_rolling_structural_in_dashboard():
    """Surface 3 rolling block + 60-month label + V1_Combination row."""
    html = _read_dashboard()
    assert 'id="ea-surface-3-rolling"' in html, "Surface 3 <details> block missing"
    # Title should mention the 60-mo window.
    assert "Rolling 60-Month" in html or "60-mo" in html or "60-month" in html.lower()
    # CAGR / Sharpe column headers present in surface 3 context.
    assert "Rolling CAGR" in html or "rolling_cagr" in html


def test_compute_rolling_metrics_numerical():
    """A steady +1%/mo series has rolling 60-mo Sharpe in a sensible range."""
    # 120 months of constant 1% returns means rolling vol is zero → Sharpe NaN.
    # Use slightly noisy series so vol > 0.
    rng = np.random.default_rng(seed=11)
    n = 120
    idx = pd.date_range("2010-01-31", periods=n, freq="ME")
    rets = pd.Series(0.01 + rng.normal(0, 0.001, n), index=idx)
    out = compute_rolling_metrics(rets, window=60)
    # Should have n - 60 + 1 = 61 non-NaN rolling rows.
    assert len(out) >= 60, f"expected ≥ 60 rolling rows, got {len(out)}"
    # Rolling Sharpe should be very high (near-deterministic positive returns).
    assert out["rolling_sharpe"].dropna().median() > 5, (
        f"rolling Sharpe should be very high for near-constant +1% series; got median "
        f"{out['rolling_sharpe'].dropna().median():.2f}"
    )


def test_build_rolling_metrics_surface_short_series_marks_unavailable():
    """Strategies with < 61 months should be marked unavailable with a reason."""
    rng = np.random.default_rng(seed=13)
    idx = pd.date_range("2020-01-31", periods=40, freq="ME")
    short = pd.Series(rng.normal(0.01, 0.04, 40), index=idx)
    strats = {
        "V1_Short": StrategyReturns(monthly=short, name="V1_Short", color="#000"),
    }
    out = build_rolling_metrics_surface(strategies=strats, window=60)
    assert out["available"] is True  # surface itself is available...
    assert out["per_strategy"][0]["available"] is False  # ...but this strategy is too short
    assert "need 61" in out["per_strategy"][0]["reason"]


def test_tag_episodes_with_macro_regime_columns_added():
    """tag_episodes_with_macro_regime adds the three Upgrade-5 columns."""
    rets = pd.Series(
        [0.01] * 5 + [-0.04] * 5 + [0.01] * 20,
        index=pd.date_range("2010-01-31", periods=30, freq="ME"),
    )
    episodes = find_drawdown_episodes(rets, min_depth=0.05)
    # Synthetic z-series: deterministic monthly index, increasing values.
    idx = pd.date_range("2010-01-31", periods=30, freq="ME")
    mvci_z = pd.Series(np.linspace(-1, 2, 30), index=idx)
    mrc_z = pd.Series(np.linspace(2, -1, 30), index=idx)
    tagged = tag_episodes_with_macro_regime(episodes, mvci_z=mvci_z, mrc_z=mrc_z)
    assert "mvci_z_at_peak" in tagged.columns
    assert "mrc_z_at_peak" in tagged.columns
    assert "regime_at_peak" in tagged.columns
    # Regime must be one of the 4 known labels (or "unknown" for NaN z's).
    valid_regimes = {
        "high_val_high_stress", "high_val_low_stress",
        "low_val_high_stress", "low_val_low_stress",
        "unknown",
    }
    assert set(tagged["regime_at_peak"]).issubset(valid_regimes)


# ── Surfaces 4-9 — omnibus structural + per-surface numerical ───────────

def test_all_9_surfaces_present_in_dashboard():
    """All 9 Extended Analytics surfaces must appear in the built dashboard."""
    html = _read_dashboard()
    for i in range(1, 10):
        assert f'id="ea-surface-{i}-' in html, f"Surface {i} <details> block missing from dashboard"


def test_build_risk_metrics_surface_emits_higher_moments():
    """Surface 4: each row carries skew + kurt + VaR/CVaR fields."""
    out = build_risk_metrics_surface(strategies=_two_strategy_fixture())
    assert out["available"] is True
    for row in out["rows"]:
        for k in ("skew_fmt", "excess_kurt_fmt", "var_5_fmt", "cvar_5_fmt", "beta_fmt", "up_capture_fmt"):
            assert k in row, f"missing key {k}"


def test_build_returns_surface_emits_annual_and_monthly_stats():
    """Surface 5: best/worst year + monthly p5/p95 + % positive months."""
    out = build_returns_surface(strategies=_two_strategy_fixture())
    assert out["available"] is True
    for row in out["rows"]:
        for k in ("worst_year_fmt", "best_year_fmt", "monthly_p05_fmt", "monthly_p95_fmt", "pct_positive_months_fmt"):
            assert k in row


def test_build_lump_sum_surface_horizons():
    """Surface 6: each non-benchmark strategy gets the 3 default horizons (3/12/36 mo)."""
    out = build_lump_sum_surface(strategies=_two_strategy_fixture())
    assert out["available"] is True
    non_bench = [r for r in out["rows"] if r.get("available")]
    assert len(non_bench) >= 1
    horizons = {h["horizon_months"] for h in non_bench[0]["horizons"]}
    assert horizons == {3, 12, 36}


def test_build_risk_vs_return_surface_pairs():
    """Surface 7: each row has Vol, CAGR, Sharpe, MaxDD, UPI."""
    out = build_risk_vs_return_surface(strategies=_two_strategy_fixture())
    assert out["available"] is True
    for row in out["rows"]:
        for k in ("vol_fmt", "cagr_fmt", "sharpe_fmt", "maxdd_fmt", "upi_fmt"):
            assert k in row


def test_swr_survival_pct_known_case():
    """SWR survival: a series of +1% monthly returns easily survives a 4% annual draw at 10y horizon."""
    monthly = np.full(150, 0.01, dtype=np.float64)  # 12.5 years of +1%/mo
    surv = _swr_survival_pct(monthly, withdrawal_rate=0.04, horizon_years=10)
    assert surv is not None and surv >= 99.0, f"expected ≥ 99% survival, got {surv}"

    # If returns are 0%, withdrawal of 4%/yr depletes $1 in 25 years — should die at 10y? 
    # Actually 4%/yr * 10yr = 40% drawn, balance ≈ 0.6 → survives.
    monthly_zero = np.zeros(150, dtype=np.float64)
    surv_zero = _swr_survival_pct(monthly_zero, withdrawal_rate=0.04, horizon_years=10)
    assert surv_zero is not None and surv_zero >= 90.0, f"zero-return SWR 10yr/4% should mostly survive (40% drawn vs $1 base), got {surv_zero}"


def test_build_withdrawal_surface_horizon_rate_grid():
    """Surface 8: each strategy gets a horizon x rate cell grid."""
    out = build_withdrawal_surface(strategies=_two_strategy_fixture(n=200))
    assert out["available"] is True
    for row in out["rows"]:
        # 3 horizons × 3 rates = 9 cells per strategy
        assert len(row["cells"]) == 9


def test_build_seasonality_surface_emits_12_months_per_strategy():
    """Surface 9: every strategy has 12 by_month entries + 2 allocation pies."""
    out = build_seasonality_surface(strategies=_two_strategy_fixture())
    assert out["available"] is True
    for row in out["rows"]:
        assert len(row["by_month"]) == 12
    # Pies (decorative) present and well-formed.
    assert "v1_combination" in out["pies"]
    assert "v2_r_primary_when_fire" in out["pies"]
    for slice in out["pies"]["v1_combination"]:
        assert "label" in slice and "weight" in slice and "color" in slice
