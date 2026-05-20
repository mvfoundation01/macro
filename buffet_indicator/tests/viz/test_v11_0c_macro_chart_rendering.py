"""v11.0c — verify the macro chart payload contains real Plotly specs for
every previously-empty container.

These are static-content tests: we inspect the in-memory chart payload
produced by ``build_macro_chart_payload()`` against real persisted data.
DOM-level render verification is handled by the screenshot capture suite.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
import pytest

from src.viz.build_macro_charts import (
    MACRO_KEYS,
    VARIANT_LABEL,
    build_macro_chart_payload,
)

warnings.filterwarnings("ignore")

ALL_TABS = MACRO_KEYS + ("mrc",)


@pytest.fixture(scope="module")
def payload() -> dict:
    """Build the macro chart payload once for the whole test module."""
    from src.config import TV_SPXTR
    from src.ingest.csv_loader import load_tradingview_file
    from src.ingest.shiller_loader import load_shiller
    from src.transform.forward_returns import build_forward_returns

    sh = load_shiller()
    try:
        spxtr_ts = load_tradingview_file(TV_SPXTR, expected_frequency="D")
        fr = build_forward_returns(
            sh, spxtr_ts.data["close"], check_continuity=False
        )
    except Exception:
        fr = build_forward_returns(sh, None, check_continuity=False)
    zh_path = Path("outputs/charts/z_history.parquet")
    zh = pd.read_parquet(zh_path) if zh_path.exists() else None
    return build_macro_chart_payload(fr, z_history=zh)


# ---------------------------------------------------------------------------
# 1) Each macro tab has a hero chart with real data (Stage A.1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tab", ALL_TABS)
def test_hero_chart_has_data(tab: str, payload: dict) -> None:
    hero = payload["macro_hero_specs"].get(tab)
    assert hero is not None, f"{tab}: no hero spec"
    assert hero.get("data"), f"{tab}: hero has no data traces"
    # Plotly traces should each carry x and y arrays.
    trace0 = hero["data"][0]
    assert trace0.get("x"), f"{tab}: hero trace 0 has no x"
    assert trace0.get("y"), f"{tab}: hero trace 0 has no y"
    assert len(trace0["x"]) > 100, f"{tab}: hero only has {len(trace0['x'])} points"


# ---------------------------------------------------------------------------
# 2) Each macro tab has Panel A/B/C + cond-dist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tab", ALL_TABS)
def test_panel_a_rendered(tab: str, payload: dict) -> None:
    charts = payload["macro_variant_charts"].get(tab)
    assert charts is not None, f"{tab}: no variant_charts entry"
    panel_a = charts.get("panel_a")
    assert panel_a is not None and panel_a.get("data"), f"{tab}: panel_a empty"


@pytest.mark.parametrize("tab", ALL_TABS)
def test_panel_b_rendered(tab: str, payload: dict) -> None:
    charts = payload["macro_variant_charts"].get(tab)
    panel_b = charts.get("panel_b") if charts else None
    assert panel_b is not None and panel_b.get("data"), f"{tab}: panel_b empty"
    # Scatter trace should have ≥ 60 points (matches min_periods).
    assert len(panel_b["data"][0].get("x", [])) >= 60


@pytest.mark.parametrize("tab", ALL_TABS)
def test_panel_c_is_shared_sentinel(tab: str, payload: dict) -> None:
    charts = payload["macro_variant_charts"].get(tab)
    assert charts.get("panel_c") == "__SHARED_PANEL_C__"


@pytest.mark.parametrize("tab", ALL_TABS)
def test_cond_dist_rendered(tab: str, payload: dict) -> None:
    charts = payload["macro_variant_charts"].get(tab)
    cond = charts.get("cond_dist") if charts else None
    assert cond is not None and cond.get("data"), f"{tab}: cond_dist empty"


# ---------------------------------------------------------------------------
# 3) MRC special elements (Stage B)
# ---------------------------------------------------------------------------


def test_mrc_constituent_contributions_bars(payload: dict) -> None:
    """MRC was 7 constituents in v11.0c; v11.0.1 still uses 7 in the
    ``mrc_extras.constituent_contributions`` chart because that chart
    surfaces the v11.0c MACRO_KEYS group. MRC v2 (13 inputs) lives in
    ``compute_mrc_v2()`` and is a separate composite."""
    extras = payload["mrc_extras"]
    chart = extras["constituent_contributions"]
    assert chart and chart.get("data"), "constituent contributions chart empty"
    bars = chart["data"][0]
    # Allow 7 (v11.0c) or 13 (v11.0.1 if extended) — guard the lower bound.
    n_bars = len(bars.get("x", []))
    assert n_bars >= 7, f"expected ≥ 7 constituent bars; got {n_bars}"
    assert n_bars == len(bars.get("y", []))


def test_mrc_correlation_heatmap_dimensions(payload: dict) -> None:
    """v11.0c heatmap was 7×7; v11.0.1 keeps the v11.0c constituent set in
    this chart. Accept ≥ 7 in each dimension."""
    chart = payload["mrc_extras"]["correlation_heatmap"]
    assert chart and chart.get("data"), "correlation heatmap empty"
    z = chart["data"][0].get("z")
    assert z, "heatmap z matrix missing"
    n_rows = len(z)
    assert n_rows >= 7
    assert all(len(row) == n_rows for row in z), "heatmap not square"


def test_mrc_pca_scree_has_bars_and_cumulative(payload: dict) -> None:
    chart = payload["mrc_extras"]["pca_scree"]
    assert chart and chart.get("data")
    # Bar trace + cumulative line trace.
    assert len(chart["data"]) >= 2
    bar = chart["data"][0]
    assert bar.get("type") == "bar"
    assert len(bar.get("x", [])) >= 3


def test_mrc_cross_composite_quadrant_real_data(payload: dict) -> None:
    chart = payload["mrc_extras"]["cross_composite_quadrant"]
    assert chart and chart.get("data"), "cross-composite chart empty"
    historical = chart["data"][0]
    assert len(historical.get("x", [])) >= 100, (
        f"only {len(historical.get('x', []))} historical points"
    )
    # Current observation marker = second trace.
    assert len(chart["data"]) >= 2


def test_mrc_cross_composite_has_four_quadrant_shapes(payload: dict) -> None:
    chart = payload["mrc_extras"]["cross_composite_quadrant"]
    shapes = chart["layout"].get("shapes", [])
    # 4 fill rectangles + 2 zero gridlines = 6 shapes minimum.
    rects = [s for s in shapes if s.get("type") == "rect"]
    assert len(rects) >= 4, f"only {len(rects)} quadrant rects"


# ---------------------------------------------------------------------------
# 4) Overview MVCI×MRC mini chart (Stage C)
# ---------------------------------------------------------------------------


def test_overview_mini_chart_has_two_lines(payload: dict) -> None:
    chart = payload["overview_mvci_mrc_mini"]
    assert chart and chart.get("data")
    assert len(chart["data"]) == 2
    for trace in chart["data"]:
        assert trace.get("x") and trace.get("y"), "mini chart trace empty"


def test_overview_mini_chart_data_lengths_reasonable(payload: dict) -> None:
    chart = payload["overview_mvci_mrc_mini"]
    for trace in chart["data"]:
        assert len(trace["x"]) > 100


# ---------------------------------------------------------------------------
# 5) Per-tab metrics populated (Stage D + E)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tab", ALL_TABS)
def test_macro_metrics_populated(tab: str, payload: dict) -> None:
    metrics = payload["macro_metrics"].get(tab)
    assert metrics is not None, f"{tab}: no metrics entry"
    for field in ("z_fmt", "p_neg_fmt", "regime", "regime_color"):
        assert metrics.get(field), f"{tab}: missing {field}"


@pytest.mark.parametrize("tab", ALL_TABS)
def test_macro_p_neg_is_real_number_or_nan(tab: str, payload: dict) -> None:
    """P(neg 10Y) must be a real number (not n/a) for every macro indicator.
    'n/a' would mean the dashboard renders the gap that v11.0b shipped."""
    metrics = payload["macro_metrics"][tab]
    p_neg = metrics.get("p_neg")
    # Accept any finite value in [0, 1]; reject None / NaN (latter shows as n/a).
    assert p_neg is not None
    import math
    assert 0.0 <= p_neg <= 1.0 and math.isfinite(p_neg), (
        f"{tab}: P(neg) = {p_neg} (would render as n/a)"
    )


def test_p_neg_fmt_not_na_for_majority(payload: dict) -> None:
    """At least 6 of 8 macro tabs should have a non-n/a P(neg) display."""
    metrics = payload["macro_metrics"]
    non_na = sum(
        1 for k in ALL_TABS if metrics.get(k, {}).get("p_neg_fmt") not in (None, "n/a")
    )
    assert non_na >= 6, f"only {non_na}/8 have a real P(neg) fmt"


def test_macro_metrics_include_bootstrap_ci(payload: dict) -> None:
    """At least one macro indicator has a non-empty CI95 string."""
    metrics = payload["macro_metrics"]
    has_ci = sum(
        1 for k in ALL_TABS if metrics.get(k, {}).get("p_neg_ci_fmt", "") != ""
    )
    assert has_ci >= 1, "no indicator surfaces a P(neg) CI95"


# ---------------------------------------------------------------------------
# 6) Variant label coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tab", MACRO_KEYS)
def test_variant_label_defined(tab: str) -> None:
    assert tab in VARIANT_LABEL
    assert len(VARIANT_LABEL[tab]) > 0
