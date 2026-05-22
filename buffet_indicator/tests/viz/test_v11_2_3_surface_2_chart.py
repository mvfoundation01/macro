"""v11.2.3 Stage 2.0 — regression test for Surface 2 (Drawdowns) Plotly chart.

Verifies:
- ``build_drawdowns_surface`` exposes ``underwater_curves`` with the
  expected shape (label, dates, dd_values per strategy).
- Rendered ``outputs/dashboard.html`` contains the chart container and
  the ``data-curves`` attribute carrying the underwater-curve JSON.
- The SVG NaN capture (run separately) reports 0 errors for the
  ``strategy_engine`` tab; this is enforced indirectly via the layout
  semantics (the chart goes through ``MV_PlotlyConfig.renderChart``
  which applies the heatmap-skip set up in v11.2.3-svgnan).

Spec ref: PROMPT_v11_2_3_stage_2 §3.1 sub-stage 2.0.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.quant_engine.extended_analytics import build_drawdowns_surface


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"


@pytest.fixture(scope="module")
def drawdowns_surface() -> dict:
    out = build_drawdowns_surface()
    if not out.get("available"):
        pytest.skip(f"drawdowns surface not available: {out.get('reason')}")
    return out


def test_underwater_curves_present(drawdowns_surface: dict) -> None:
    curves = drawdowns_surface.get("underwater_curves")
    assert curves is not None, "underwater_curves field missing"
    assert isinstance(curves, list)
    assert len(curves) >= 1, "expected ≥1 strategy"


def test_underwater_curve_shape(drawdowns_surface: dict) -> None:
    for c in drawdowns_surface["underwater_curves"]:
        assert {"label", "is_v2", "dates", "dd_values"}.issubset(c)
        assert isinstance(c["label"], str)
        assert isinstance(c["is_v2"], bool)
        assert isinstance(c["dates"], list)
        assert isinstance(c["dd_values"], list)
        assert len(c["dates"]) == len(c["dd_values"]), (
            f"{c['label']}: dates and dd_values length mismatch"
        )
        # First non-null dd value should be ≤ 0 (drawdown is non-positive).
        non_null = [v for v in c["dd_values"] if v is not None]
        assert non_null, f"{c['label']}: no non-null dd values"
        assert all(v <= 0 + 1e-9 for v in non_null), (
            f"{c['label']}: drawdown values must be non-positive"
        )


def test_dashboard_html_has_chart_container() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip(f"dashboard.html not built at {DASHBOARD_HTML}")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    assert 'id="ea-surface-2-underwater"' in html, (
        "Surface 2 chart container missing from dashboard.html"
    )
    # data-curves payload must be present and parseable as JSON.
    m = re.search(
        r'id="ea-surface-2-underwater"[^>]*data-curves=\'([^\']+)\'',
        html,
    )
    assert m, "data-curves attribute not found on chart container"
    payload = m.group(1)
    # The attribute uses HTML entity encoding; un-encode the minimum needed for json.
    payload_html = payload.replace("&quot;", '"').replace("&#39;", "'")
    parsed = json.loads(payload_html)
    assert isinstance(parsed, list)
    assert len(parsed) >= 1
    for c in parsed:
        assert "label" in c
        assert "dates" in c
        assert "dd_values" in c


def test_dashboard_html_chart_uses_render_pipeline() -> None:
    """Chart must go through MV_PlotlyConfig.renderChart so the
    universal-defaults heatmap skip from v11.2.3-svgnan applies.
    """
    if not DASHBOARD_HTML.exists():
        pytest.skip(f"dashboard.html not built at {DASHBOARD_HTML}")
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    # Find the script block that follows the chart container.
    # The data-curves JSON payload can be >10 KB, so search from the start
    # of the surface container to the closing </script> after it.
    idx = html.find('id="ea-surface-2-underwater"')
    assert idx > 0
    end = html.find("</script>", idx)
    assert end > 0, "no </script> found after chart container"
    window = html[idx : end]
    assert "cfg.renderChart" in window or "MV_PlotlyConfig.renderChart" in window, (
        "Surface 2 chart should call MV_PlotlyConfig.renderChart"
    )


def test_bundle_size_under_ceiling() -> None:
    if not DASHBOARD_HTML.exists():
        pytest.skip("dashboard.html not built")
    size_mb = DASHBOARD_HTML.stat().st_size / (1024 * 1024)
    assert size_mb < 14.0, f"bundle {size_mb:.2f} MB exceeds 14 MB ceiling"
