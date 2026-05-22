"""v11.2.3 Stage 2.2 — regression test for Surface 4 (Risk metrics) chart.

Spec ref: PROMPT_v11_2_3_stage_2 §3.1 sub-stage 2.2.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.quant_engine.extended_analytics import build_risk_metrics_surface


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"


@pytest.fixture(scope="module")
def risk_surface() -> dict:
    out = build_risk_metrics_surface()
    if not out.get("available"):
        pytest.skip(f"risk_metrics not available: {out.get('reason')}")
    return out


def test_metric_chart_data_present(risk_surface: dict) -> None:
    data = risk_surface.get("metric_chart_data")
    assert data is not None
    assert isinstance(data, list)
    assert len(data) >= 1


def test_metric_chart_data_shape(risk_surface: dict) -> None:
    keys = {"label", "is_v2", "mean_pct", "std_pct", "downside_dev_pct", "var_5_pct", "cvar_5_pct", "skew", "beta"}
    for s in risk_surface["metric_chart_data"]:
        assert keys.issubset(s)
        # std should be positive (or None) — sanity check
        if s["std_pct"] is not None:
            assert s["std_pct"] >= 0


def test_dashboard_html_has_chart_container() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    assert 'id="ea-surface-4-risk-chart"' in html
    m = re.search(
        r'id="ea-surface-4-risk-chart"[^>]*data-strategies=\'([^\']+)\'',
        html,
    )
    assert m
    payload_html = m.group(1).replace("&quot;", '"').replace("&#39;", "'")
    parsed = json.loads(payload_html)
    assert isinstance(parsed, list)
    assert len(parsed) >= 1


def test_dashboard_html_chart_uses_render_pipeline() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    idx = html.find('id="ea-surface-4-risk-chart"')
    assert idx > 0
    end = html.find("</script>", idx)
    assert end > 0
    window = html[idx:end]
    assert "cfg.renderChart" in window or "MV_PlotlyConfig.renderChart" in window


def test_bundle_size_under_ceiling() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    size_mb = DASHBOARD_HTML.stat().st_size / (1024 * 1024)
    assert size_mb < 14.0
