"""v11.1 Stage D — Strategy Engine tab DOM probe + structural acceptance tests."""
from __future__ import annotations

import re
from pathlib import Path

import pytest


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"
EXPECTED_SHEET_COUNT = 35  # 17 core + 7 robustness + 6 inst + 3 gap-closers + 2 extras
V1_NA_SHEETS = ["ETF-Rotation History", "ETF Protection", "ETF Episode Audit"]


def _read_dashboard() -> str:
    if not DASHBOARD_HTML.exists():
        pytest.skip(f"Dashboard not built: {DASHBOARD_HTML}")
    return DASHBOARD_HTML.read_text(encoding="utf-8")


def _extract_se_tab(html: str) -> str:
    """Extract just the Strategy Engine tab section to scope grep-style assertions."""
    m = re.search(
        r'<section data-tab="strategy_engine"[^>]*>(.*?)</section>\s*(?=<section|<footer|</main>)',
        html,
        re.DOTALL,
    )
    assert m is not None, "Strategy Engine <section data-tab=\"strategy_engine\"> not found"
    return m.group(0)


def test_strategy_engine_tab_renders():
    html = _read_dashboard()
    assert 'data-tab="strategy_engine"' in html


def test_strategy_engine_has_expected_section_count():
    """Stage D test: each declared sheet renders as one <details data-sheet="...">."""
    html = _read_dashboard()
    se = _extract_se_tab(html)
    sheets = re.findall(r'<details[^>]*data-sheet="([^"]+)"', se)
    assert len(sheets) == EXPECTED_SHEET_COUNT, (
        f"Expected exactly {EXPECTED_SHEET_COUNT} sheet sections, got {len(sheets)}: {sheets}"
    )


def test_sub_tab_nav_has_4_or_5_groups():
    """Stage D test: sub-tab nav contains buttons for each group."""
    html = _read_dashboard()
    se = _extract_se_tab(html)
    nav_btns = re.findall(r'data-se-group="(\w+)"', se)
    # 4 spec'd groups + 1 extras = 5 expected
    expected = {"core", "robustness", "institutional", "gap_closers", "extras"}
    found = set(nav_btns)
    assert expected.issubset(found), f"Missing groups: {expected - found}"


def test_kpi_cards_show_numeric_values():
    """Stage D test: 4 KPI cards show parsable numeric values (not 'n/a')."""
    html = _read_dashboard()
    se = _extract_se_tab(html)
    # The 4 KPI cards are: Sharpe, MaxDD, CAGR, Scorecard
    # Look for the Sharpe value pattern
    sharpe_m = re.search(r'DD-TARGET Sharpe.*?<div class="text-2xl[^"]*">([^<]+)</div>', se, re.DOTALL)
    assert sharpe_m is not None, "DD-TARGET Sharpe card not found"
    sharpe_text = sharpe_m.group(1).strip()
    assert sharpe_text != "n/a", "Sharpe KPI shows 'n/a' — V1 data not flowing"
    # Should be a signed float like "+1.069"
    assert re.match(r"[+\-]?\d+\.\d+", sharpe_text), f"Sharpe '{sharpe_text}' not a number"


def test_refresh_button_exists():
    """Stage D test: refresh button with onclick handler."""
    html = _read_dashboard()
    se = _extract_se_tab(html)
    assert 'onclick="refreshQuantEngine()"' in se
    assert 'id="se-refresh-button"' in se


def test_download_xlsx_link_present():
    """Stage D test: download link points into outputs/quant_engine/latest/."""
    html = _read_dashboard()
    se = _extract_se_tab(html)
    assert 'outputs/quant_engine/latest/latest.xlsx' in se
    assert 'download=' in se


def test_each_section_passes_dom_content_gate():
    """Stage D test (CRITICAL — v11.0c failure-pattern guard):
    Each <details> body must contain ≥1 <tr>, OR a Plotly div, OR ≥100 chars of prose.
    """
    html = _read_dashboard()
    se = _extract_se_tab(html)
    # Match each <details data-sheet=...> ... </details>
    sections = re.findall(
        r'<details[^>]*data-sheet="([^"]+)"[^>]*>(.*?)</details>',
        se,
        re.DOTALL,
    )
    assert len(sections) == EXPECTED_SHEET_COUNT
    failures: list[str] = []
    for sheet_name, body in sections:
        has_tr = "<tr" in body
        has_plotly = "se-plotly-chart" in body or "data-plotly-data" in body
        # Strip tags to count prose chars
        text_only = re.sub(r"<[^>]+>", "", body)
        text_only = re.sub(r"\s+", " ", text_only).strip()
        has_prose = len(text_only) >= 100
        if not (has_tr or has_plotly or has_prose):
            failures.append(f"{sheet_name} (text len={len(text_only)})")
    assert not failures, (
        f"Sections failed DOM content gate (no <tr>, no Plotly div, <100 char prose): {failures}"
    )


def test_at_least_4_plotly_figures_in_strategy_engine():
    """Stage D test: at least 4 Plotly figure divs render across the 32+ sections."""
    html = _read_dashboard()
    se = _extract_se_tab(html)
    # Period heatmap bonus + cost stress + correlations + holdings overlap + DSR
    n_plotly = se.count("se-plotly-chart")
    assert n_plotly >= 4, f"Expected ≥4 Plotly divs, got {n_plotly}"


def test_v1_na_sheets_show_banner():
    """Stage D test: sheets in V1_NA_SHEETS show the "Not applicable in V1" banner."""
    html = _read_dashboard()
    se = _extract_se_tab(html)
    sections = re.findall(
        r'<details[^>]*data-sheet="([^"]+)"[^>]*>(.*?)</details>',
        se,
        re.DOTALL,
    )
    sec_map = dict(sections)
    for name in V1_NA_SHEETS:
        assert name in sec_map, f"V1-NA sheet '{name}' missing from rendered tab"
        body = sec_map[name]
        assert "se-na-banner" in body, f"'{name}' should show N/A banner but didn't"
        assert "Not applicable in V1" in body


def test_all_5_group_keys_appear_in_rendered_html():
    """Stage D test: all 5 group keys appear in data-se-group-content attrs."""
    html = _read_dashboard()
    se = _extract_se_tab(html)
    found = set(re.findall(r'data-se-group-content="(\w+)"', se))
    assert found == {"core", "robustness", "institutional", "gap_closers", "extras"}, (
        f"Group content divs incomplete: {found}"
    )


def test_strategy_engine_in_analysis_nav_group():
    """Stage D test: Strategy Engine nav button is in the Analysis group."""
    html = _read_dashboard()
    # Find the Analysis group section in nav
    m = re.search(
        r'data-group-tabs="analysis">.*?</div>',
        html,
        re.DOTALL,
    )
    assert m is not None, "Analysis group nav not found"
    analysis_nav = m.group(0)
    assert 'data-tab="strategy_engine"' in analysis_nav, (
        "Strategy Engine button not in Analysis nav group"
    )


def test_legacy_backtest_renamed():
    """Stage E test: legacy Backtest nav button labeled 'Backtest (legacy)'."""
    html = _read_dashboard()
    assert "Backtest (legacy)" in html, "Legacy Backtest button not renamed"


def test_governance_tabs_present():
    """Stage D test: Governance section includes all 4 govrnance .txt files as tabbed panels."""
    html = _read_dashboard()
    se = _extract_se_tab(html)
    # Find the Governance section
    gov_match = re.search(
        r'<details[^>]*data-sheet="Governance"[^>]*>(.*?)</details>',
        se,
        re.DOTALL,
    )
    assert gov_match is not None
    gov_body = gov_match.group(1)
    for kind in ("model_card", "config_snapshot", "environment_lock", "change_log"):
        assert f'data-gov-tab="{kind}"' in gov_body, f"Gov tab {kind} missing"


def test_bundle_under_13mb():
    """Stage G test: dashboard bundle ≤ 13 MB."""
    if not DASHBOARD_HTML.exists():
        pytest.skip("Dashboard not built")
    size_mb = DASHBOARD_HTML.stat().st_size / (1024 * 1024)
    assert size_mb <= 13.0, f"Bundle {size_mb:.2f} MB exceeds 13 MB ceiling"
