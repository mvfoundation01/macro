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
    build_drawdowns_surface,
    build_summary_surface,
    find_drawdown_episodes,
    tag_episodes_with_macro_regime,
)
from src.quant_engine.analytics_core import StrategyReturns

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
