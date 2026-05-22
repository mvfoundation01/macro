"""v11.2.3 Stage 2.6 — Surface 8 SWR heatmap regression test.

Verifies the heatmap renders cleanly. Critical: confirms the
v11.2.3-svgnan heatmap-skip in `MV_PlotlyConfig.applyUniversalDefaults`
still suppresses the categorical-y-axis NaN bug for this new heatmap.

Spec ref: PROMPT_v11_2_3_stage_2 §3.1 sub-stage 2.6, §3.3 stop conditions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.quant_engine.extended_analytics import build_withdrawal_surface


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"


@pytest.fixture(scope="module")
def withdrawal_surface() -> dict:
    out = build_withdrawal_surface()
    if not out.get("available"):
        pytest.skip(f"withdrawal not available: {out.get('reason')}")
    return out


def test_heatmap_present(withdrawal_surface: dict) -> None:
    hm = withdrawal_surface.get("heatmap")
    assert hm is not None
    assert {"x_labels", "y_labels", "by_strategy", "primary_label"}.issubset(hm)
    assert len(hm["by_strategy"]) >= 1


def test_heatmap_matrix_shape(withdrawal_surface: dict) -> None:
    hm = withdrawal_surface["heatmap"]
    n_rates = len(hm["y_labels"])
    n_horiz = len(hm["x_labels"])
    for entry in hm["by_strategy"]:
        assert entry["z"] is not None
        assert len(entry["z"]) == n_rates, f"{entry['label']}: row count mismatch"
        for row in entry["z"]:
            assert len(row) == n_horiz, f"{entry['label']}: col count mismatch"


def test_dashboard_html_has_heatmap_container() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    assert 'id="ea-surface-8-heatmap"' in html
    m = re.search(
        r'id="ea-surface-8-heatmap"[^>]*data-heatmap=\'([^\']+)\'',
        html,
    )
    assert m
    parsed = json.loads(m.group(1).replace("&quot;", '"').replace("&#39;", "'"))
    assert "by_strategy" in parsed
    assert parsed["by_strategy"]


def test_dashboard_html_chart_uses_render_pipeline() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    idx = html.find('id="ea-surface-8-heatmap"')
    end = html.find("</script>", idx)
    window = html[idx:end]
    # Heatmap must go through MV_PlotlyConfig.renderChart so the
    # heatmap-skip in applyUniversalDefaults applies (otherwise we'd
    # regress to the SVG NaN bug from Session 1).
    assert "cfg.renderChart" in window or "MV_PlotlyConfig.renderChart" in window


def test_heatmap_uses_category_axis() -> None:
    """Critical regression check: y-axis MUST be categorical (type:'category'),
    not 'linear'. The v11.2.3-svgnan fix sets the universal defaults to skip
    heatmaps; this test verifies the surface's local layout also uses 'category'.
    """
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    idx = html.find('id="ea-surface-8-heatmap"')
    end = html.find("</script>", idx)
    window = html[idx:end]
    assert 'type: "category"' in window or "type:'category'" in window, (
        "Surface 8 heatmap must specify type:'category' on its y axis"
    )


def test_bundle_size_under_ceiling() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    size_mb = DASHBOARD_HTML.stat().st_size / (1024 * 1024)
    assert size_mb < 14.0
