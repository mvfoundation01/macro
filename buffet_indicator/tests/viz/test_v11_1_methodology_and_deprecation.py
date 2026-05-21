"""v11.1 Stage E — Methodology + Backtest-deprecation acceptance tests."""
from __future__ import annotations

from pathlib import Path

import pytest


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"


def _read_dashboard() -> str:
    if not DASHBOARD_HTML.exists():
        pytest.skip(f"Dashboard not built: {DASHBOARD_HTML}")
    return DASHBOARD_HTML.read_text(encoding="utf-8")


def test_methodology_has_strategy_engine_section():
    html = _read_dashboard()
    assert "Strategy Engine v50 (V1" in html
    assert "v50 is a 7,032-line institutional-grade" in html


def test_methodology_mentions_all_4_v1_strategies():
    html = _read_dashboard()
    for name in ("DD-TARGET", "ENS-Ultra", "LowBeta", "Combination"):
        assert name in html, f"Methodology missing {name}"


def test_methodology_references_all_4_robustness_layers():
    html = _read_dashboard()
    for layer in ("Block Bootstrap CI", "Path MC MaxDD", "Parametric Tail",
                  "Walk-Forward OOS Distribution"):
        assert layer in html, f"Methodology missing robustness layer: {layer}"


def test_old_backtest_has_deprecation_banner():
    html = _read_dashboard()
    assert "Deprecated as of v11.1" in html
    # The banner must reference Strategy Engine as the replacement
    assert 'href="#tab=strategy_engine"' in html or "strategy_engine" in html


def test_strategy_engine_appears_in_analysis_nav():
    html = _read_dashboard()
    # The nav has data-tab="strategy_engine" within the Analysis group
    import re
    analysis_match = re.search(
        r'data-group-tabs="analysis">(.*?)</div>',
        html,
        re.DOTALL,
    )
    assert analysis_match is not None
    assert 'data-tab="strategy_engine"' in analysis_match.group(1)


def test_methodology_mentions_v50_paths():
    html = _read_dashboard()
    assert "D:" in html  # the path appears
    assert "quant_pipeline" in html


def test_methodology_lists_v11_2_deferrals():
    """Methodology should disclose what is NOT in V1 to set expectations."""
    html = _read_dashboard()
    assert "MV-Conditional V2" in html
    assert "v11.2" in html
