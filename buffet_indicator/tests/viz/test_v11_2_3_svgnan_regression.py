"""v11.2.3 Stage 1 regression tests — SVG NaN render-error guards.

The actual SVG NaN diagnostic lives in `reviews/diagnostic_artifacts/`
(requires headless Chromium + the built dashboard). These tests verify
the *source-level fixes* so the bug cannot regress silently:

1. dashboard.js declares window.mvRenderWhenReady helper.
2. dashboard.js renderPlot uses mvRenderWhenReady (defers Plotly.newPlot
   until host div has dimensions).
3. dashboard.js renderPlot skips applyUniversalDefaults for heatmap traces
   (universal yaxis.type='linear' breaks heatmap categorical y axis).
4. tab_strategy_engine.html DOMContentLoaded handler uses mvRenderWhenReady.
5. _ea_surface_9_seasonality.html IIFE uses mvRenderWhenReady.
"""
from __future__ import annotations

import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DASHBOARD_JS = REPO_ROOT / "src" / "viz" / "static" / "dashboard.js"
TAB_SE = REPO_ROOT / "src" / "viz" / "templates" / "tab_strategy_engine.html"
SEASONALITY = REPO_ROOT / "src" / "viz" / "templates" / "_ea_surface_9_seasonality.html"


def test_dashboard_js_declares_mv_render_when_ready():
    """window.mvRenderWhenReady must be declared in dashboard.js."""
    src = DASHBOARD_JS.read_text(encoding="utf-8")
    assert "window.mvRenderWhenReady" in src, (
        "window.mvRenderWhenReady helper missing from dashboard.js — "
        "the v11.2.3 SVG NaN fix depends on this helper deferring "
        "Plotly.newPlot() until the host div has valid dimensions."
    )
    assert "IntersectionObserver" in src, (
        "mvRenderWhenReady must fall back to IntersectionObserver for "
        "tabs that activate long after the initial polling window."
    )


def test_render_plot_uses_mv_render_when_ready():
    """renderPlot must wrap Plotly.newPlot inside mvRenderWhenReady."""
    src = DASHBOARD_JS.read_text(encoding="utf-8")
    # Find the renderPlot function body
    start = src.find("function renderPlot(")
    assert start > -1, "renderPlot function not found"
    end = src.find("\n  }", start)
    body = src[start:end]
    assert "mvRenderWhenReady" in body, (
        "renderPlot must call mvRenderWhenReady to defer Plotly.newPlot() "
        "into a frame where the host div has non-zero dimensions."
    )


def test_render_plot_skips_universal_defaults_for_heatmap():
    """renderPlot must NOT call applyUniversalDefaults on heatmap traces.

    Universal defaults force yaxis.type='linear' which conflicts with a
    heatmap's categorical y-axis and produces NaN SVG coordinates for
    every cell label + the colorbar image (this was the 82-error
    diagnostics-tab bug found in v11.2.2-p1).
    """
    src = DASHBOARD_JS.read_text(encoding="utf-8")
    start = src.find("function renderPlot(")
    end = src.find("\n  }", start)
    body = src[start:end]
    # The guard pattern: hasHeatmap check + && !hasHeatmap on the call
    assert 'type === "heatmap"' in body, (
        "renderPlot must detect heatmap traces to skip applyUniversalDefaults."
    )
    assert "!hasHeatmap" in body, (
        "renderPlot must skip applyUniversalDefaults when hasHeatmap is true."
    )


def test_tab_strategy_engine_uses_mv_render_when_ready():
    """Strategy-engine details[open] init renderer must defer via helper."""
    src = TAB_SE.read_text(encoding="utf-8")
    assert "mvRenderWhenReady" in src, (
        "tab_strategy_engine.html DOMContentLoaded handler must use "
        "mvRenderWhenReady — direct Plotly.newPlot into the hidden "
        "strategy_engine tab emits NaN SVG coordinates."
    )


def test_seasonality_uses_mv_render_when_ready():
    """Seasonality heatmap IIFE must defer via helper."""
    src = SEASONALITY.read_text(encoding="utf-8")
    assert "mvRenderWhenReady" in src, (
        "_ea_surface_9_seasonality.html IIFE must use mvRenderWhenReady — "
        "the heatmap div lives in the hidden strategy_engine tab at "
        "page-load time and direct render produces NaN SVG coordinates."
    )


def test_built_dashboard_inlines_the_helper():
    """The built dashboard.html must contain window.mvRenderWhenReady inline."""
    dashboard = REPO_ROOT / "buffet_indicator" / "outputs" / "dashboard.html"
    if not dashboard.exists():
        # When tests run from inside buffet_indicator/ the path is different
        dashboard = REPO_ROOT / "outputs" / "dashboard.html"
    if not dashboard.exists():
        # Final fallback — locate by walking from this file
        dashboard = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "dashboard.html"
    assert dashboard.exists(), f"built dashboard.html not found (looked at {dashboard})"
    src = dashboard.read_text(encoding="utf-8")
    assert "window.mvRenderWhenReady" in src, (
        "built dashboard.html does not inline window.mvRenderWhenReady — "
        "either dashboard.js was not bundled, or the build step did not "
        "pick up the v11.2.3 SVG NaN fix."
    )
