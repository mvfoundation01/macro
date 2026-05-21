"""Spec v8b §2.5, §3.4, §4.5 — unit tests for chart_specs + captions.

These tests cover the P0 deliverables:
  A — bigger, more interactive charts (5 tests)
  B — larger Y-axis typography (3 tests)
  C — per-chart interpretation system (5 tests)

Plus content checks that the rendered dashboard.html contains expected v8b
strings (interpretation blocks, why-it-matters expandables, historical
annotations).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.viz.captions import (  # noqa: E402
    WHY_IT_MATTERS,
    all_interpretations_for,
    buffett_hero_interpretation,
    cape_hero_interpretation,
    ey_deficit_hero_interpretation,
    mean_reversion_hero_interpretation,
    mvci_hero_interpretation,
    qratio_hero_interpretation,
    why_it_matters,
)
from src.viz.chart_specs import (  # noqa: E402
    AXIS_TITLE_FONT_SIZE,
    CHART_TITLE_FONT_SIZE,
    FONT_FAMILY,
    TICK_FONT_SIZE,
    ZSCORE_Y_RANGE,
    make_correlation_heatmap,
    make_hero_chart,
    make_oos_r2_chart,
    make_panel_a,
)


def _z_series_long(n: int = 1800, seed: int = 0) -> pd.Series:
    """Synthetic z series spanning 1881-present so historical annotations land in range."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1881-01-31", periods=n, freq="ME")
    return pd.Series(rng.standard_normal(n) * 1.5, index=idx, name="z")


def _z_series_short(n: int = 240, seed: int = 1) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    return pd.Series(rng.standard_normal(n), index=idx, name="z")


# ===========================================================================
# Deliverable A — bigger, more interactive charts (5 tests)
# ===========================================================================


def test_V8B_A1_hero_chart_height_is_600() -> None:
    spec = make_hero_chart(_z_series_short(), "Test")
    assert spec["layout"]["height"] == 600


def test_V8B_A2_panel_chart_height_is_450() -> None:
    spec = make_panel_a(_z_series_short())
    assert spec["layout"]["height"] == 450


def test_V8B_A3_modebar_visible_with_export_button() -> None:
    """v8b.1 B.2 changed scrollZoom default from True to False (mobile-safe).

    The JS layer feature-detects touch devices and only enables scrollZoom
    on non-touch desktops at render time. The base spec must default False.
    """
    spec = make_hero_chart(_z_series_short(), "Test")
    cfg = spec["config"]
    assert cfg["displayModeBar"] is True
    assert cfg["displaylogo"] is False
    assert cfg["scrollZoom"] is False  # v8b.1 default; JS opts in on desktop
    assert cfg["doubleClick"] == "reset+autosize"
    assert "toImageButtonOptions" in cfg
    assert cfg["toImageButtonOptions"]["scale"] == 2


def test_V8B_A4_crosshair_enabled_on_both_axes() -> None:
    spec = make_hero_chart(_z_series_short(), "Test")
    layout = spec["layout"]
    assert layout["xaxis"]["showspikes"] is True
    assert layout["yaxis"]["showspikes"] is True
    assert layout["hovermode"] == "x unified"
    assert layout["spikedistance"] == -1


def test_V8B_A5_hover_template_includes_regime_and_percentile() -> None:
    spec = make_hero_chart(_z_series_short(), "Test")
    trace = spec["data"][0]
    template = trace.get("hovertemplate", "")
    assert "Regime" in template
    assert "Percentile" in template
    # customdata must carry the labels we reference
    assert "customdata" in trace
    assert len(trace["customdata"]) == len(trace["x"])


# ===========================================================================
# Deliverable B — larger Y-axis typography (3 tests + extras)
# ===========================================================================


def test_V8B_B1_y_axis_tick_font_is_14() -> None:
    spec = make_hero_chart(_z_series_short(), "Test")
    yaxis = spec["layout"]["yaxis"]
    assert yaxis["tickfont"]["size"] == TICK_FONT_SIZE == 14
    assert yaxis["tickfont"]["family"] == FONT_FAMILY


def test_V8B_B2_y_axis_dtick_is_one_sigma_range_minus4_to_4() -> None:
    spec = make_hero_chart(_z_series_short(), "Test")
    yaxis = spec["layout"]["yaxis"]
    assert yaxis["dtick"] == 1.0
    assert yaxis["range"] == ZSCORE_Y_RANGE == [-4.0, 4.0]
    assert yaxis["zeroline"] is True


def test_V8B_B3_y_axis_range_accommodates_extreme_readings() -> None:
    spec = make_hero_chart(_z_series_short(), "Test")
    yrange = spec["layout"]["yaxis"]["range"]
    assert yrange[0] <= -3.5
    assert yrange[1] >= 3.5


def test_V8B_B4_axis_title_uses_16px() -> None:
    spec = make_hero_chart(_z_series_short(), "Test")
    assert spec["layout"]["yaxis"]["title"]["font"]["size"] == AXIS_TITLE_FONT_SIZE == 16


def test_V8B_B5_chart_title_uses_18px() -> None:
    spec = make_hero_chart(_z_series_short(), "Test")
    assert spec["layout"]["title"]["font"]["size"] == CHART_TITLE_FONT_SIZE == 18


# ===========================================================================
# Deliverable C — interpretation system (5 tests)
# ===========================================================================


def test_V8B_C1_mvci_hero_interpretation_has_three_blocks() -> None:
    intr = mvci_hero_interpretation(1.79, "Overvalued", 97)
    assert set(intr.keys()) == {"what_this_shows", "how_to_read", "current_reading"}


def test_V8B_C2_each_interpretation_block_is_substantial() -> None:
    intr = mvci_hero_interpretation(1.79, "Overvalued", 97)
    for key, text in intr.items():
        assert len(text) >= 100, f"{key} too short: {len(text)} chars"


def test_V8B_C3_per_indicator_interpretations_exist_and_render() -> None:
    """Spec v8b §4.2: hero interpretation per variant."""
    cape = cape_hero_interpretation(36.5, 1.22, 93.4, "Overvalued")
    assert "CAPE" in cape["current_reading"]
    buf = buffett_hero_interpretation("Buffett (Wilshire)", 215.0, 1.5, 95.0, "Overvalued")
    assert "Buffett" in buf["what_this_shows"]
    q = qratio_hero_interpretation(1.98, 1.03, 87, "Overvalued")
    assert "Q" in q["what_this_shows"]
    ey = ey_deficit_hero_interpretation(-0.80, 0.39, 65, "Fair Value")
    assert "Equity Yield" in ey["what_this_shows"] or "EY" in ey["current_reading"]
    mr = mean_reversion_hero_interpretation(181.0, 2.11, 99, "Strongly Overvalued")
    assert "trend" in mr["how_to_read"].lower()


def test_V8B_C4_why_it_matters_present_for_every_indicator() -> None:
    """Every indicator key in WHY_IT_MATTERS has a non-trivial paragraph.

    v9.0 added crestmont as a 7th key.
    """
    required = {"mvci", "cape", "buffett", "qratio", "ey_deficit", "mean_reversion"}
    assert required.issubset(set(WHY_IT_MATTERS.keys()))
    for key in WHY_IT_MATTERS.keys():
        body = why_it_matters(key)
        assert len(body) >= 200, f"{key} body too short: {len(body)} chars"


def test_V8B_C5_historical_annotations_added_when_in_range() -> None:
    """Hero charts spanning 1881+ annotate the historical valuation peaks.

    v11.1 L1 fix: the "Post-COVID peak (-25% in 2022)" annotation was removed
    because the "-25% in 2022" referred to the S&P 500 drawdown, not the
    indicator's own behavior — and so was contextually wrong on z-score
    history charts. Only the 1929 + 2000 valuation peaks remain.
    """
    spec = make_hero_chart(_z_series_long(), "Test", add_historical_annotations=True)
    annotations = spec["layout"].get("annotations") or []
    texts = " ".join(str(a.get("text", "")) for a in annotations)
    assert "1929" in texts
    assert "Dot-com" in texts or "2000" in texts
    # v11.1 L1: Post-COVID / 2021 peak intentionally removed; no assertion.


def test_V8B_C6_no_historical_annotations_for_short_series() -> None:
    """Short series that doesn't cover the peaks should have zero historical annotations."""
    short = pd.Series(
        np.random.randn(60), index=pd.date_range("2022-01-31", periods=60, freq="ME")
    )
    spec = make_hero_chart(short, "Test", add_historical_annotations=True)
    annotations = spec["layout"].get("annotations") or []
    texts = " ".join(str(a.get("text", "")) for a in annotations)
    # 2022-2027 range — only 2021 might land, but the date is 2021-12-31 which is just before the start
    # So we expect no annotations from the three peaks
    assert "1929" not in texts
    assert "2000" not in texts


def test_V8B_C7_all_interpretations_aggregate_includes_all_keys() -> None:
    bundle = all_interpretations_for(
        "mvci", z=1.79, percentile=97.0, regime="Overvalued",
        beta=-0.05, r_squared=0.30, t_nw=-3.5,
    )
    assert "hero" in bundle
    assert "panel_a" in bundle
    assert "panel_b" in bundle
    assert "panel_c" in bundle
    assert "why_it_matters" in bundle
    assert len(bundle["why_it_matters"]) > 100


# ===========================================================================
# Deliverable D/E — Q-Ratio + EY-Deficit dedicated tabs
# ===========================================================================


def test_V8B_D1_qratio_hero_interpretation_includes_value() -> None:
    intr = qratio_hero_interpretation(1.98, 1.03, 87, "Overvalued")
    assert "1.98" in intr["current_reading"]
    assert "Overvalued" in intr["current_reading"]


def test_V8B_E1_ey_deficit_hero_interpretation_uses_pct_unit() -> None:
    intr = ey_deficit_hero_interpretation(-0.80, 0.39, 65, "Fair Value")
    # Value is in % already; current_reading should include the unit
    assert "%" in intr["current_reading"]


# ===========================================================================
# Diagnostics charts (correlation heatmap + OOS R²)
# ===========================================================================


def test_V8B_F1_correlation_heatmap_spec_has_z_values() -> None:
    df = pd.DataFrame(
        {"a": [1.0, 0.8, 0.6], "b": [0.8, 1.0, 0.7], "c": [0.6, 0.7, 1.0]},
        index=["a", "b", "c"],
    )
    spec = make_correlation_heatmap(df)
    assert spec["data"][0]["type"] == "heatmap"
    assert len(spec["data"][0]["z"]) == 3
    assert spec["data"][0]["zmin"] == -1
    assert spec["data"][0]["zmax"] == 1


def test_V8B_F2_oos_r2_chart_spec_includes_zero_line() -> None:
    spec = make_oos_r2_chart(
        dates=["2000-01-01", "2010-01-01", "2020-01-01"],
        r2_values=[0.1, 0.2, 0.15],
    )
    names = [t.get("name", "") for t in spec["data"]]
    assert "OOS R² (10Y)" in names


# ===========================================================================
# Built-dashboard content checks (Spec v8b §4.5 tests 1-2)
# ===========================================================================


@pytest.fixture(scope="module")
def dashboard_html() -> str:
    path = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"
    if not path.exists():
        pytest.skip("dashboard.html not built — run `python -m src.cli dashboard` first.")
    return path.read_text(encoding="utf-8")


def test_V8B_content_interpretation_blocks_present(dashboard_html: str) -> None:
    """Built dashboard should have the 3-block interpretation grid on multiple charts."""
    assert dashboard_html.count("What this shows") >= 5
    assert dashboard_html.count("How to read it") >= 5
    assert dashboard_html.count("Current reading") >= 5


def test_V8B_content_why_it_matters_present(dashboard_html: str) -> None:
    assert "Why does CAPE matter?" in dashboard_html or "Why does CAPE" in dashboard_html
    assert "Why does the Buffett Indicator matter?" in dashboard_html or "Why does" in dashboard_html
    assert "Why does Mean Reversion matter?" in dashboard_html or "Why does Mean Reversion" in dashboard_html


def test_V8B_content_new_tabs_present(dashboard_html: str) -> None:
    for tab_key in ("qratio", "ey_deficit", "diagnostics", "data", "methodology"):
        assert f'data-tab="{tab_key}"' in dashboard_html, f"{tab_key} tab nav button missing"


def test_V8B_content_historical_annotations_in_payload(dashboard_html: str) -> None:
    """The embedded JSON should contain at least one annotation referencing 1929."""
    assert "1929" in dashboard_html
    assert "Dot-com" in dashboard_html or "2000 peak" in dashboard_html
