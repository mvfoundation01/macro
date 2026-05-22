"""v11.2.3 Stage 2.1 — regression test for Surface 3 (Rolling metrics) chart.

Verifies:
- ``build_rolling_metrics_surface`` exposes ``rolling_series`` with the
  expected shape (dates + sharpe/vol/sortino arrays per strategy).
- Rendered ``outputs/dashboard.html`` contains the chart container with a
  parseable ``data-series`` JSON attribute and uses ``MV_PlotlyConfig.renderChart``.

Spec ref: PROMPT_v11_2_3_stage_2 §3.1 sub-stage 2.1.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.quant_engine.extended_analytics import build_rolling_metrics_surface


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"


@pytest.fixture(scope="module")
def rolling_surface() -> dict:
    out = build_rolling_metrics_surface()
    if not out.get("available"):
        pytest.skip(f"rolling_metrics surface not available: {out.get('reason')}")
    return out


def test_rolling_series_present(rolling_surface: dict) -> None:
    series = rolling_surface.get("rolling_series")
    assert series is not None
    assert isinstance(series, list)
    assert len(series) >= 1


def test_rolling_series_shape(rolling_surface: dict) -> None:
    for s in rolling_surface["rolling_series"]:
        assert {"label", "is_v2", "dates", "sharpe", "vol", "sortino"}.issubset(s)
        n = len(s["dates"])
        assert n == len(s["sharpe"]) == len(s["vol"]) == len(s["sortino"]), (
            f"{s['label']}: length mismatch across series fields"
        )
        # All sharpe values are either None or finite floats.
        for arr_name in ("sharpe", "vol", "sortino"):
            for v in s[arr_name]:
                assert v is None or isinstance(v, float)


def test_dashboard_html_has_chart_container() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    assert 'id="ea-surface-3-rolling-chart"' in html, (
        "Surface 3 chart container missing"
    )
    m = re.search(
        r'id="ea-surface-3-rolling-chart"[^>]*data-series=\'([^\']+)\'',
        html,
    )
    assert m, "data-series attribute missing"
    payload_html = m.group(1).replace("&quot;", '"').replace("&#39;", "'")
    parsed = json.loads(payload_html)
    assert isinstance(parsed, list)
    assert len(parsed) >= 1
    for s in parsed:
        assert {"label", "dates", "sharpe", "vol", "sortino"}.issubset(s)


def test_dashboard_html_chart_uses_render_pipeline() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    idx = html.find('id="ea-surface-3-rolling-chart"')
    assert idx > 0
    end = html.find("</script>", idx)
    assert end > 0
    window = html[idx:end]
    assert "cfg.renderChart" in window or "MV_PlotlyConfig.renderChart" in window


def test_bundle_size_under_ceiling() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    size_mb = DASHBOARD_HTML.stat().st_size / (1024 * 1024)
    assert size_mb < 14.0, f"bundle {size_mb:.2f} MB exceeds 14 MB"
