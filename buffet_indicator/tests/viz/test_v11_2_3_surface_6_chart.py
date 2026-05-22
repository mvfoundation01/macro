"""v11.2.3 Stage 2.4 — regression test for Surface 6 (Lump sum / terminal wealth).

Spec ref: PROMPT_v11_2_3_stage_2 §3.1 sub-stage 2.4.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.quant_engine.extended_analytics import build_lump_sum_surface


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"


@pytest.fixture(scope="module")
def lump_surface() -> dict:
    out = build_lump_sum_surface()
    if not out.get("available"):
        pytest.skip(f"lump_sum surface not available: {out.get('reason')}")
    return out


def test_terminal_wealth_present(lump_surface: dict) -> None:
    tw = lump_surface.get("terminal_wealth")
    assert tw is not None
    assert isinstance(tw, list)
    assert len(tw) >= 1


def test_terminal_wealth_sorted_descending(lump_surface: dict) -> None:
    tw = lump_surface["terminal_wealth"]
    values = [r["terminal_value"] for r in tw]
    assert values == sorted(values, reverse=True), "terminal_wealth not sorted descending"
    # Positive values expected.
    for r in tw:
        assert r["terminal_value"] > 0


def test_terminal_wealth_marks_benchmark(lump_surface: dict) -> None:
    benchmark = lump_surface["benchmark_label"]
    tw = lump_surface["terminal_wealth"]
    matched = [r for r in tw if r["label"] == benchmark]
    assert len(matched) == 1
    assert matched[0]["is_benchmark"] is True


def test_dashboard_html_has_chart_container() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    assert 'id="ea-surface-6-terminal"' in html
    m = re.search(
        r'id="ea-surface-6-terminal"[^>]*data-strategies=\'([^\']+)\'',
        html,
    )
    assert m
    parsed = json.loads(m.group(1).replace("&quot;", '"').replace("&#39;", "'"))
    assert isinstance(parsed, list)


def test_dashboard_html_chart_uses_render_pipeline() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    idx = html.find('id="ea-surface-6-terminal"')
    end = html.find("</script>", idx)
    window = html[idx:end]
    assert "cfg.renderChart" in window or "MV_PlotlyConfig.renderChart" in window


def test_bundle_size_under_ceiling() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    size_mb = DASHBOARD_HTML.stat().st_size / (1024 * 1024)
    assert size_mb < 14.0
