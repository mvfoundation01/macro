"""v11.1.1 — acceptance tests for the 4 hotfixes (C1, C2, I1, I2)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_HTML = REPO_ROOT / "outputs" / "dashboard.html"
CHART_SPECS = REPO_ROOT / "src" / "viz" / "chart_specs.py"
DASHBOARD_JS = REPO_ROOT / "src" / "viz" / "static" / "dashboard.js"


def _read_dashboard() -> str:
    if not DASHBOARD_HTML.exists():
        pytest.skip(f"Dashboard not built: {DASHBOARD_HTML}")
    return DASHBOARD_HTML.read_text(encoding="utf-8")


# ============================================================
# C1 — Plotly bad-format string fixes
# ============================================================


# v11.2.2-p1 SUPERSEDES v11.2.2-p0's `+.Nf` revert. Empirical evidence from
# Playwright DevTools captures (Investigation Report + Phase 2 diagnosis,
# 2026-05-21) showed Plotly 2.35.2 ALSO rejects `+.Nf` (one ``WARN: encountered
# bad format`` per unique placeholder per session). Both `+,.Nf` (v11.1.1
# attempt) AND `+.Nf` (v11.2.2-p0 attempt) emit warnings — only `.Nf` (plain
# decimal, no sign-modifier) is silent. v11.2.2-p1 strips ``+`` from every
# Plotly hovertemplate placeholder source-side.


def test_c1_no_bad_comma_format_in_source():
    """`+,.Nf` patterns (v11.1.1 attempt) remain absent in chart_specs.py."""
    src = CHART_SPECS.read_text(encoding="utf-8")
    bad = re.findall(r'%\{[a-z]:\+,\.\d+f\}', src)
    bad_escaped = re.findall(r'%\{\{[a-z]:\+,\.\d+f\}\}', src)
    total = bad + bad_escaped
    assert not total, (
        f"v11.1.1's '+,.Nf' patterns still present in chart_specs.py: {total}"
    )


def test_c1_no_signed_format_in_source():
    """v11.2.2-p1: `+.Nf` Plotly hovertemplate placeholders are absent.

    Plotly 2.35.2 emits ``encountered bad format`` warnings for ANY `+` sign-
    modifier in hovertemplate placeholders. Use `.Nf` (plain) or pre-format via
    the ``text`` field.
    """
    src = CHART_SPECS.read_text(encoding="utf-8")
    signed = re.findall(r'%\{[a-z]:\+\.\d+f\}', src)
    signed_escaped = re.findall(r'%\{\{[a-z]:\+\.\d+f\}\}', src)
    total = signed + signed_escaped
    assert not total, (
        f"v11.2.2-p0's '+.Nf' patterns still present in chart_specs.py: {total}. "
        f"v11.2.2-p1 strips them; use ':.Nf' instead."
    )


def test_c1_no_bad_comma_format_in_rendered_html():
    """Rendered HTML has 0 `+,.Nf` patterns (v11.1.1 attempt remains reverted)."""
    html = _read_dashboard()
    bad = re.findall(r'%\{[a-z]:\+,\.\d+f\}', html)
    assert not bad, f"v11.1.1's '+,.Nf' patterns leaked into rendered HTML: {len(bad)}"


# ============================================================
# C2 — file:// blocked navigation
# ============================================================


def test_c2_no_window_location_href_assignments_in_js():
    """Source dashboard.js + rendered HTML have NO `window.location.href = ...`
    pattern (only `.hash` allowed for internal routing)."""
    js_src = DASHBOARD_JS.read_text(encoding="utf-8")
    html = _read_dashboard()
    # window.location.href = "..." is the bad pattern
    bad_js = re.findall(r'window\.location\.href\s*=', js_src)
    bad_html = re.findall(r'window\.location\.href\s*=', html)
    assert not bad_js, f"window.location.href assignment in dashboard.js: {bad_js}"
    assert not bad_html, f"window.location.href assignment in rendered HTML: {bad_html}"


def test_c2_internal_anchors_use_hash_or_relative():
    """Anchors pointing inside the dashboard use either `#tab=...` hash form
    OR a relative path (no absolute `file://` URLs in HTML)."""
    html = _read_dashboard()
    # Any href starting with file:// is a bug
    bad = re.findall(r'href=["\']file://', html)
    assert not bad, f"Found file:// hrefs in HTML: {bad[:3]}"


def test_c2_download_links_use_relative_paths():
    """Download links in the Strategy Engine tab use RELATIVE paths,
    not absolute file:// URLs."""
    html = _read_dashboard()
    # Find <a ... download> tags pointing to the quant_engine outputs
    m = re.search(
        r'<a[^>]*href="([^"]+)"[^>]*download',
        html,
    )
    assert m is not None, "No download link found in dashboard"
    # First match should be relative (starts with "outputs/" not "/" or "file://" or "D:")
    href = m.group(1)
    assert not href.startswith("file://"), f"Download href absolute: {href}"
    assert not href.startswith("/"), f"Download href absolute: {href}"
    assert not re.match(r"[A-Za-z]:", href), f"Download href absolute: {href}"


# ============================================================
# I1 — Overview MVCI+MRC chart wire-up
# ============================================================


def test_i1_dashboard_js_renders_overview_mvci_mrc_chart():
    """dashboard.js's overview branch calls renderPlot for the
    cross-composite-mini div (v11.1.1 wire-up fix)."""
    js_src = DASHBOARD_JS.read_text(encoding="utf-8")
    assert 'renderPlot("overview-cross-composite-mini"' in js_src, (
        "Overview cross-composite-mini chart wire-up missing in dashboard.js"
    )
    assert "DATA.overview_mvci_mrc_mini" in js_src, (
        "DATA.overview_mvci_mrc_mini reference missing"
    )


def test_i1_overview_chart_payload_present_in_dashboard():
    """The chart spec key `overview_mvci_mrc_mini` is present in the inline
    dashboard JSON payload (with non-empty data)."""
    import json
    html = _read_dashboard()
    m = re.search(
        r'<script id="dashboard-data" type="application/json">(.*?)</script>',
        html, re.DOTALL,
    )
    assert m is not None, "Dashboard JSON payload not found"
    payload = json.loads(m.group(1))
    mvci_mrc = payload.get("overview_mvci_mrc_mini")
    assert mvci_mrc is not None, "overview_mvci_mrc_mini missing from payload"
    assert "data" in mvci_mrc, "overview_mvci_mrc_mini has no 'data' key"
    # Should have 2 traces: MVCI line + MRC line
    assert len(mvci_mrc["data"]) >= 2, (
        f"Expected ≥2 traces (MVCI+MRC), got {len(mvci_mrc['data'])}"
    )


def test_i1_overview_chart_div_present_in_html():
    """The target div for the chart is still in the Overview tab."""
    html = _read_dashboard()
    assert 'id="overview-cross-composite-mini"' in html


# ============================================================
# I2 — V1 lineup table truncation
# ============================================================


def test_i2_v1_lineup_table_has_17_rows():
    """V1 lineup table contains all 17 entities (4 strategies + 2 indices + 11 stocks),
    not the previously-truncated 8."""
    html = _read_dashboard()
    # Match the V1 lineup section (h3 title with "V1 lineup")
    m = re.search(
        r'<h3[^>]*>V1 lineup.*?</h3>.*?<tbody>(.*?)</tbody>',
        html, re.DOTALL,
    )
    assert m is not None, "V1 lineup table not found"
    body = m.group(1)
    rows = re.findall(r'<tr', body)
    assert len(rows) == 17, f"Expected 17 V1 lineup rows, got {len(rows)}"


def test_i2_v1_lineup_includes_spy_and_all_stocks():
    """V1 lineup table contains SPY and all 11 buy-and-hold stock tickers."""
    html = _read_dashboard()
    m = re.search(
        r'<h3[^>]*>V1 lineup.*?</h3>.*?<tbody>(.*?)</tbody>',
        html, re.DOTALL,
    )
    assert m is not None
    body = m.group(1)
    required = ["SPY", "BLK", "BRK.B", "TROW", "BEN", "IVZ",
                "STT", "NTRS", "RJF", "GS", "JPM", "MS"]
    missing = [t for t in required if t not in body]
    assert not missing, f"V1 lineup missing entities: {missing}"


def test_i2_v1_lineup_includes_all_4_strategies():
    """All 4 V1 active strategies appear in the lineup table."""
    html = _read_dashboard()
    m = re.search(
        r'<h3[^>]*>V1 lineup.*?</h3>.*?<tbody>(.*?)</tbody>',
        html, re.DOTALL,
    )
    assert m is not None
    body = m.group(1)
    for name in ("DD-TARGET", "ENS-Ultra", "LowBeta", "Combination"):
        assert name in body, f"Strategy '{name}' missing from V1 lineup"


def test_i2_spy_lineup_table_in_build_context():
    """build_strategy_engine_context() returns spy_lineup_table with 17 entries."""
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from src.viz.build_strategy_engine import build_strategy_engine_context
    ctx = build_strategy_engine_context()
    if ctx is None:
        pytest.skip("Strategy engine context not built (no v50 outputs)")
    table = ctx.get("spy_lineup_table", [])
    assert len(table) == 17, f"Expected 17 lineup entries, got {len(table)}"
    # First row should have highest Sharpe (sorted desc)
    sharpes = [r["sharpe"] for r in table if r["sharpe"] is not None]
    assert sharpes == sorted(sharpes, reverse=True), (
        "spy_lineup_table not sorted by Sharpe descending"
    )


# ============================================================
# Regression — v11.1 didn't break
# ============================================================


def test_regression_strategy_engine_still_has_35_sections():
    """v11.1's 35-section Strategy Engine tab is unchanged."""
    html = _read_dashboard()
    se_match = re.search(
        r'<section data-tab="strategy_engine"[^>]*>(.*?)</section>\s*(?=<section|<footer|</main>)',
        html, re.DOTALL,
    )
    assert se_match is not None
    se = se_match.group(0)
    sheets = re.findall(r'<details[^>]*data-sheet="([^"]+)"', se)
    assert len(sheets) == 35, f"Strategy Engine sections regressed to {len(sheets)}"


def test_regression_methodology_section_present():
    """v11.1's methodology Strategy Engine section is unchanged."""
    html = _read_dashboard()
    assert "Strategy Engine v50 (V1" in html
    assert "v50 is a 7,032-line institutional-grade" in html


def test_regression_backtest_deprecation_banner():
    """v11.1's deprecation banner on the Backtest tab still present."""
    html = _read_dashboard()
    assert "Deprecated as of v11.1" in html


def test_bundle_size_within_acceptable_range():
    """Bundle stays within v11.2.2's 18 MB ceiling (raised from v11.1's 11.0)."""
    size_mb = DASHBOARD_HTML.stat().st_size / (1024 * 1024)
    assert 9.5 <= size_mb <= 18.0, (
        f"Bundle size {size_mb:.2f} MB outside v11.2.2 range [9.5, 18.0]"
    )
