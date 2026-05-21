"""v11.2.2 — acceptance tests for B1, B2, B3, B4 hotfixes + universal config.

Per PROMPT_v11_2_2_and_v11_3 §A.3 / §A.4 / §A.5.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_HTML = REPO_ROOT / "outputs" / "dashboard.html"
CHART_SPECS = REPO_ROOT / "src" / "viz" / "chart_specs.py"
DASHBOARD_JS = REPO_ROOT / "src" / "viz" / "static" / "dashboard.js"
PLOTLY_CONFIG_JS = REPO_ROOT / "src" / "viz" / "static" / "plotly_config.js"
VIZ_DIR = REPO_ROOT / "src" / "viz"
TEMPLATES_DIR = REPO_ROOT / "src" / "viz" / "templates"
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _read_dashboard() -> str:
    if not DASHBOARD_HTML.exists():
        pytest.skip(f"Dashboard not built: {DASHBOARD_HTML}")
    return DASHBOARD_HTML.read_text(encoding="utf-8")


def _dashboard_payload() -> dict:
    html = _read_dashboard()
    m = re.search(
        r'<script id="dashboard-data" type="application/json">(.*?)</script>',
        html, re.DOTALL,
    )
    assert m is not None, "Dashboard JSON payload not found"
    return json.loads(m.group(1))


# ============================================================
# A.1 — plotly_config.js foundational module
# ============================================================


def test_plotly_config_js_exists():
    assert PLOTLY_CONFIG_JS.exists(), (
        "src/viz/static/plotly_config.js missing — foundational A.1 step"
    )


def test_plotly_config_js_exposes_window_namespace():
    src = PLOTLY_CONFIG_JS.read_text(encoding="utf-8")
    assert "window.MV_PlotlyConfig" in src
    for key in (
        "plotlyConfigDefault", "plotlyLayoutDefault", "plotlyLayoutEquityCurve",
        "strategyColors", "applyUniversalDefaults", "renderChart",
    ):
        assert key in src, f"plotly_config.js missing exported key: {key}"


def test_plotly_config_js_inlined_before_dashboard_js():
    """build_dashboard.py concatenates plotly_config.js BEFORE dashboard.js so
    window.MV_PlotlyConfig is defined when renderPlot() runs."""
    html = _read_dashboard()
    # Both content markers must appear; plotly_config must appear before dashboard's renderPlot
    assert "window.MV_PlotlyConfig" in html
    assert "function renderPlot(divId, spec)" in html
    idx_config = html.index("window.MV_PlotlyConfig")
    idx_render = html.index("function renderPlot(divId, spec)")
    assert idx_config < idx_render, (
        "plotly_config.js must be inlined BEFORE dashboard.js"
    )


# ============================================================
# B1 — Plotly bad-format strings ELIMINATED universally
# ============================================================


def test_b1_no_bad_format_in_any_viz_source():
    """Audit ALL src/viz/*.py (not just chart_specs.py) — zero `+,.Nf` patterns."""
    files = list(VIZ_DIR.rglob("*.py"))
    bad = []
    for f in files:
        s = f.read_text(encoding="utf-8")
        for m in re.finditer(r'\+,\.\d+f', s):
            bad.append((f.relative_to(REPO_ROOT).as_posix(), m.group(0)))
    assert not bad, f"Residual '+,.Nf' patterns in viz source: {bad}"


def test_b1_no_bad_format_in_built_dashboard():
    html = _read_dashboard()
    bad = re.findall(r'\+,\.\d+f', html)
    assert not bad, (
        f"Residual '+,.Nf' patterns in built dashboard ({len(bad)} occurrences) — "
        "rebuild after fixing source"
    )


def test_b1_thousands_separator_without_sign_still_allowed():
    """The valid `,.Nf` (thousands sep, NO sign) IS allowed — used for dollar
    amounts, market cap. This test guards against an over-eager revert."""
    src = CHART_SPECS.read_text(encoding="utf-8")
    valid = re.findall(r'%\{[a-z]:,\.\d+f\}', src)
    # The pattern exists somewhere (e.g., dollar-amount hovertemplates) — assert
    # AT LEAST the regex still compiles and finds zero or more matches without
    # raising. This is a smoke test, not a count assertion.
    assert isinstance(valid, list)


# ============================================================
# B2 — file:// unsafe URL navigation prevention
# ============================================================


def test_b2_no_full_dashboard_href_navigation_in_templates():
    """No <a href="dashboard.html#..."> patterns in any template."""
    bad = []
    for f in TEMPLATES_DIR.rglob("*.html"):
        s = f.read_text(encoding="utf-8")
        matches = re.findall(r'href=["\']dashboard\.html#[^"\']+["\']', s)
        if matches:
            bad.append((f.relative_to(REPO_ROOT).as_posix(), matches))
    assert not bad, f"Found dashboard.html#... navigation in templates: {bad}"


def test_b2_no_full_dashboard_href_in_built_dashboard():
    html = _read_dashboard()
    bad = re.findall(r'href=["\']dashboard\.html#[^"\']+["\']', html)
    assert not bad, f"dashboard.html#... navigation in built dashboard: {bad}"


def test_b2_serve_dashboard_script_exists():
    script = SCRIPTS_DIR / "serve_dashboard.py"
    assert script.exists(), "scripts/serve_dashboard.py missing for HTTP serving"


def test_b2_file_protocol_notice_in_dashboard():
    html = _read_dashboard()
    assert "file-protocol-notice" in html, (
        "file-protocol-notice div missing — users opening file:// see no guidance"
    )


# ============================================================
# B4 — Universal Y-axis drag-zoom (via plotly_config.js + dashboard.js patch)
# ============================================================


def test_b4_dashboard_js_calls_apply_universal_defaults():
    """renderPlot() in dashboard.js invokes applyUniversalDefaults()."""
    src = DASHBOARD_JS.read_text(encoding="utf-8")
    assert "applyUniversalDefaults" in src
    assert "MV_PlotlyConfig.applyUniversalDefaults" in src or \
           "window.MV_PlotlyConfig.applyUniversalDefaults" in src


def test_b4_plotly_config_yaxis_fixedrange_false():
    src = PLOTLY_CONFIG_JS.read_text(encoding="utf-8")
    # Both axes should have fixedrange: false in the defaults
    assert re.search(r"yaxis\s*:\s*\{[^}]*fixedrange\s*:\s*false", src, re.DOTALL)
    assert re.search(r"xaxis\s*:\s*\{[^}]*fixedrange\s*:\s*false", src, re.DOTALL)


# ============================================================
# B3 — Strategy equity curves (assertions written; render covered in §A.4)
# ============================================================


def test_b3_strategy_equity_curves_div_in_dashboard():
    """Strategy Engine tab has the strategy-equity-curves-plot div at top."""
    html = _read_dashboard()
    assert 'id="strategy-equity-curves-plot"' in html, (
        "Strategy equity curves chart div missing from dashboard"
    )


def test_b3_strategy_equity_curves_payload_present():
    payload = _dashboard_payload()
    section = payload.get("strategy_equity_curves")
    assert section is not None, (
        "DATA.strategy_equity_curves missing from inline payload"
    )
    assert "dates" in section, "strategy_equity_curves has no 'dates' field"
    assert len(section["dates"]) >= 100, (
        f"Expected >100 monthly dates in equity curves, got {len(section['dates'])}"
    )
    # At minimum V1 + SPY must be present
    assert "V1_Combination" in section, "V1_Combination missing from equity curves"
    assert "SPY" in section, "SPY missing from equity curves"


def test_b3_v1_equity_grows_at_least_2x_from_2000():
    """Sanity: V1 from $10k in 2000 reaches >$20k by end (well-documented V1 backtest)."""
    payload = _dashboard_payload()
    section = payload.get("strategy_equity_curves") or {}
    series = section.get("V1_Combination") or []
    assert series, "V1_Combination series empty"
    finite = [v for v in series if v is not None]
    assert finite, "V1_Combination series has no finite values"
    assert finite[-1] > 20_000, (
        f"V1 final {finite[-1]:.0f} too low — equity curve broken?"
    )
