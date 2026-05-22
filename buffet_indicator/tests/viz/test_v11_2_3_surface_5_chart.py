"""v11.2.3 Stage 2.3 — regression test for Surface 5 (Returns) charts.

Spec ref: PROMPT_v11_2_3_stage_2 §3.1 sub-stage 2.3.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.quant_engine.extended_analytics import build_returns_surface


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"


@pytest.fixture(scope="module")
def returns_surface() -> dict:
    out = build_returns_surface()
    if not out.get("available"):
        pytest.skip(f"returns surface not available: {out.get('reason')}")
    return out


def test_cum_log_curves_present(returns_surface: dict) -> None:
    curves = returns_surface.get("cum_log_curves")
    assert curves is not None
    assert isinstance(curves, list)
    assert len(curves) >= 1
    for c in curves:
        assert {"label", "is_v2", "dates", "log_eq"}.issubset(c)
        assert len(c["dates"]) == len(c["log_eq"])


def test_annual_returns_present(returns_surface: dict) -> None:
    annual = returns_surface.get("annual_returns")
    assert annual is not None
    assert isinstance(annual, list)
    assert len(annual) >= 1
    for a in annual:
        assert {"label", "is_v2", "years", "values"}.issubset(a)
        assert len(a["years"]) == len(a["values"])
        # Years should be ints.
        for y in a["years"]:
            assert isinstance(y, int)


def test_dashboard_html_has_both_panels() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    assert 'id="ea-surface-5-logeq"' in html
    assert 'id="ea-surface-5-annual"' in html

    m1 = re.search(r'id="ea-surface-5-logeq"[^>]*data-curves=\'([^\']+)\'', html)
    assert m1, "panel A data-curves missing"
    json.loads(m1.group(1).replace("&quot;", '"').replace("&#39;", "'"))

    m2 = re.search(r'id="ea-surface-5-annual"[^>]*data-annual=\'([^\']+)\'', html)
    assert m2, "panel B data-annual missing"
    json.loads(m2.group(1).replace("&quot;", '"').replace("&#39;", "'"))


def test_dashboard_html_chart_uses_render_pipeline() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    idx = html.find('id="ea-surface-5-logeq"')
    assert idx > 0
    end = html.find("</script>", idx)
    window = html[idx:end]
    assert "cfg.renderChart" in window or "MV_PlotlyConfig.renderChart" in window


def test_bundle_size_under_ceiling() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    size_mb = DASHBOARD_HTML.stat().st_size / (1024 * 1024)
    assert size_mb < 14.0
