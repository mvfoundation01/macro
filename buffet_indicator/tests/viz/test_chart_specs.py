"""Unit tests for src.viz.chart_specs and src.viz.captions."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.viz.captions import REGIME_COLORS, all_captions_for, regime_color
from src.viz.chart_specs import (
    make_panel_a,
    make_panel_b,
    make_panel_c,
    make_pca_loadings_bar,
    make_regime_band_shapes,
    make_sparkline,
)


def _z_series(n: int = 200, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    return pd.Series(rng.standard_normal(n), index=idx, name="z")


# ---------------------------------------------------------------------------
# V8A1 -- Panel A returns dict with required keys
# ---------------------------------------------------------------------------


def test_V8A1_make_panel_a_returns_required_keys() -> None:
    spec = make_panel_a(_z_series())
    assert "data" in spec
    assert "layout" in spec
    assert "config" in spec


# ---------------------------------------------------------------------------
# V8A2 -- Regime band shapes have correct colors + y-ranges
# ---------------------------------------------------------------------------


def test_V8A2_regime_band_shapes_correct() -> None:
    shapes = make_regime_band_shapes()
    by_color = {s["fillcolor"]: (s["y0"], s["y1"]) for s in shapes}
    assert by_color[REGIME_COLORS["Strongly Overvalued"]] == (2, 3.5)
    assert by_color[REGIME_COLORS["Overvalued"]] == (1, 2)
    assert by_color[REGIME_COLORS["Fair Value"]] == (-1, 1)
    assert by_color[REGIME_COLORS["Undervalued"]] == (-2, -1)
    assert by_color[REGIME_COLORS["Strongly Undervalued"]] == (-3.5, -2)


# ---------------------------------------------------------------------------
# V8A3 -- Panel B has a current-z marker
# ---------------------------------------------------------------------------


def test_V8A3_panel_b_includes_current_z() -> None:
    idx = pd.date_range("2000-01-31", periods=300, freq="ME")
    df = pd.DataFrame(
        {
            "date": idx,
            "z_score_long_run": np.random.default_rng(0).standard_normal(len(idx)),
            "forward_120m_cagr": np.random.default_rng(1).standard_normal(len(idx)) * 0.1
            + 0.07,
        }
    )
    spec = make_panel_b(
        df,
        current_z=2.0,
        regression={"alpha": 0.07, "beta": -0.02, "r_squared": 0.3, "t_nw": -3.0},
        horizon_col="forward_120m_cagr",
    )
    # Look for the "Current z" trace.
    names = [t.get("name") for t in spec["data"]]
    assert "Current z" in names


# ---------------------------------------------------------------------------
# V8A4 -- Panel C uses log y-axis
# ---------------------------------------------------------------------------


def test_V8A4_panel_c_log_yaxis() -> None:
    idx = pd.date_range("1990-01-31", periods=240, freq="ME")
    df = pd.DataFrame(
        {
            "date": idx,
            "sp500_close": np.linspace(300, 5000, len(idx)),
            "regime_mvci": ["Fair Value"] * 100
            + ["Overvalued"] * 80
            + ["Strongly Overvalued"] * 60,
            "regime_color_mvci": ["#9AA0A6"] * 100 + ["#E87722"] * 80 + ["#C8102E"] * 60,
        }
    )
    spec = make_panel_c(df)
    assert spec["layout"]["yaxis"]["type"] == "log"


# ---------------------------------------------------------------------------
# V8A9 -- Captions module returns a string per chart
# ---------------------------------------------------------------------------


def test_V8A9_captions_per_chart() -> None:
    for vkey in ("mvci", "bi_allequity_pct", "cape", "qratio", "ey_deficit"):
        c = all_captions_for(vkey)
        assert isinstance(c, dict)
        for k in ("panel_a", "panel_b", "panel_c"):
            assert isinstance(c[k], str)
            assert len(c[k]) > 10


# ---------------------------------------------------------------------------
# V8A12 -- Regime color lookup returns correct hex
# ---------------------------------------------------------------------------


def test_V8A12_regime_color_lookup() -> None:
    assert regime_color("Strongly Overvalued") == "#C8102E"
    assert regime_color("Overvalued") == "#E87722"
    assert regime_color("Fair Value") == "#9AA0A6"
    assert regime_color("Undervalued") == "#5DBB63"
    assert regime_color("Strongly Undervalued") == "#1B7A3E"


def test_sparkline_minimalist_layout() -> None:
    spec = make_sparkline(_z_series())
    assert spec["layout"]["xaxis"]["visible"] is False
    assert spec["layout"]["yaxis"]["visible"] is False
    assert spec["config"]["displayModeBar"] is False


def test_pca_loadings_bar_sorted_descending() -> None:
    spec = make_pca_loadings_bar({"a": 0.2, "b": 0.4, "c": 0.1})
    xs = spec["data"][0]["x"]
    assert xs == sorted(xs, reverse=True)
