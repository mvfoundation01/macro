"""v11.2.3 Stage 2.5 — regression test for Surface 7 (Risk vs Return scatter).

Spec ref: PROMPT_v11_2_3_stage_2 §3.1 sub-stage 2.5.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.quant_engine.extended_analytics import build_risk_vs_return_surface


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"


@pytest.fixture(scope="module")
def rvr_surface() -> dict:
    out = build_risk_vs_return_surface()
    if not out.get("available"):
        pytest.skip(f"risk_vs_return not available: {out.get('reason')}")
    return out


def test_scatter_points_present(rvr_surface: dict) -> None:
    pts = rvr_surface.get("scatter_points")
    assert pts is not None
    assert isinstance(pts, list)
    assert len(pts) >= 1
    for p in pts:
        assert {"label", "is_v2", "vol_pct", "cagr_pct", "sharpe"}.issubset(p)
        assert p["vol_pct"] >= 0


def test_dashboard_html_has_chart_container() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    assert 'id="ea-surface-7-scatter"' in html
    m = re.search(
        r'id="ea-surface-7-scatter"[^>]*data-points=\'([^\']+)\'',
        html,
    )
    assert m
    parsed = json.loads(m.group(1).replace("&quot;", '"').replace("&#39;", "'"))
    assert isinstance(parsed, list)


def test_dashboard_html_chart_uses_render_pipeline() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    idx = html.find('id="ea-surface-7-scatter"')
    end = html.find("</script>", idx)
    window = html[idx:end]
    assert "cfg.renderChart" in window or "MV_PlotlyConfig.renderChart" in window


def test_bundle_size_under_ceiling() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    size_mb = DASHBOARD_HTML.stat().st_size / (1024 * 1024)
    assert size_mb < 14.0
