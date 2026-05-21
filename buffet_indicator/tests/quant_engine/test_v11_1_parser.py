"""v11.1 Stage C — Parser + dashboard-metrics acceptance tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.quant_engine import (
    ALL_EXCEL_GROUPS,
    V1_ACTIVE_STRATEGIES,
    V1_BENCHMARK_INDICES,
    V1_DROPPED_STRATEGIES,
    check_norgate_available,
    compute_dashboard_metrics,
    parse_governance_txt,
    parse_v50_csv,
    parse_v50_xlsx,
)
from src.quant_engine.strategy_engine_config import QE_LATEST_CSV, QE_LATEST_XLSX


@pytest.mark.skipif(not QE_LATEST_CSV.exists(), reason="No v50 CSV synced yet")
def test_parse_v50_csv_filters_to_v1_lineup():
    """Stage C.4: parse_v50_csv() returns only V1 labels (no dropped strategies)."""
    df = parse_v50_csv()
    labels = set(df["label"].unique())
    for dropped in V1_DROPPED_STRATEGIES:
        assert dropped not in labels, f"{dropped} should be filtered out (V1 lineup)"
    # V1 entities (or subset thereof if Path B fallback used)
    v1_set = set(V1_ACTIVE_STRATEGIES + V1_BENCHMARK_INDICES) | {
        "BLK", "BRK.B", "TROW", "BEN", "IVZ", "STT", "NTRS", "RJF", "GS", "JPM", "MS",
    }
    assert labels.issubset(v1_set), f"Unexpected labels: {labels - v1_set}"


@pytest.mark.skipif(not QE_LATEST_CSV.exists(), reason="No v50 CSV synced yet")
def test_parse_v50_csv_has_tier_column():
    """Stage C.1: tier column added with valid values."""
    df = parse_v50_csv()
    assert "tier" in df.columns
    assert set(df["tier"].unique()).issubset({"Strategy", "Index", "Stock"})


@pytest.mark.skipif(not QE_LATEST_CSV.exists(), reason="No v50 CSV synced yet")
def test_compute_dashboard_metrics_headline_dd_target():
    """Stage C.4: DD-TARGET headline Sharpe in plausible range [0.5, 2.0]."""
    df = parse_v50_csv()
    metrics = compute_dashboard_metrics(df)
    sharpe = metrics["headline"].get("sharpe")
    if sharpe is None:
        pytest.skip("DD-TARGET headline not present (Path B fallback?)")
    assert 0.5 <= sharpe <= 2.0, f"DD-TARGET Sharpe outlier: {sharpe}"


@pytest.mark.skipif(not QE_LATEST_CSV.exists(), reason="No v50 CSV synced yet")
def test_compute_dashboard_metrics_spy_h2h_sorted():
    """Stage C.4: spy_h2h top entry has highest delta_sharpe_vs_spy."""
    df = parse_v50_csv()
    metrics = compute_dashboard_metrics(df)
    h2h = metrics["spy_h2h"]
    if len(h2h) < 2:
        pytest.skip("SPY h2h has < 2 rows (Path B fallback?)")
    deltas = [e["delta_sharpe_vs_spy"] for e in h2h if e["delta_sharpe_vs_spy"] is not None]
    assert deltas == sorted(deltas, reverse=True), "spy_h2h not sorted by delta desc"


def test_parse_governance_txt_returns_4_keys():
    """Stage C.4: parse_governance_txt() returns dict with 4 expected keys."""
    g = parse_governance_txt()
    assert set(g.keys()) == {"model_card", "config_snapshot", "environment_lock", "change_log"}


@pytest.mark.skipif(not QE_LATEST_XLSX.exists(), reason="No v50 XLSX synced yet")
def test_parse_v50_xlsx_has_all_expected_sheets():
    """Stage C.4: parse_v50_xlsx() returns dict with all configured sheets."""
    sheets = parse_v50_xlsx()
    expected_count = sum(len(g) for g in ALL_EXCEL_GROUPS.values())
    assert len(sheets) >= expected_count, (
        f"Expected ≥{expected_count} sheets, got {len(sheets)}"
    )
    # Each declared sheet name must be present (may be __missing__ marker)
    for group_sheets in ALL_EXCEL_GROUPS.values():
        for sheet_name in group_sheets:
            assert sheet_name in sheets


@pytest.mark.skipif(not QE_LATEST_CSV.exists(), reason="No v50 CSV synced yet")
def test_period_heatmap_dimensions():
    """Stage C.4: period_heatmap covers V1 actives + indices × 8 periods."""
    df = parse_v50_csv()
    metrics = compute_dashboard_metrics(df)
    heatmap = metrics["period_heatmap"]
    expected_rows = set(V1_ACTIVE_STRATEGIES + V1_BENCHMARK_INDICES)
    # Allow a subset (if some strategies missing in Path B fallback)
    assert set(heatmap.keys()).issubset(expected_rows), (
        f"Unexpected heatmap rows: {set(heatmap.keys()) - expected_rows}"
    )
    for label, periods in heatmap.items():
        assert len(periods) == 8, f"{label} should have 8 periods, has {len(periods)}"


def test_check_norgate_available_returns_bool():
    """Stage C.4: check_norgate_available() returns bool without raising."""
    result = check_norgate_available()
    assert isinstance(result, bool)


def test_compute_dashboard_metrics_empty_df_safe():
    """Stage C.4: empty DataFrame returns sentinel structure (no crash)."""
    import pandas as pd

    metrics = compute_dashboard_metrics(pd.DataFrame(columns=["label", "period", "_costbps"]))
    assert metrics == {
        "headline": {},
        "spy_h2h": [],
        "ranking_full": [],
        "cost_retention": {},
        "period_heatmap": {},
    }
