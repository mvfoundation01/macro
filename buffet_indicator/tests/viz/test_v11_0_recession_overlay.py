"""v11.0 acceptance tests for the NBER recession overlay infrastructure."""
from __future__ import annotations

import pandas as pd
import pytest

from src.ingest.nber_recessions import (
    NBER_RECESSIONS_PARQUET,
    load_nber_recessions,
    refresh,
)
from src.viz.chart_overlays import RECESSION_BAND_COLOR, add_recession_bands
from src.viz.chart_specs import (
    make_allocation_chart,
    make_correlation_heatmap,
    make_drawdown_chart,
    make_equity_curve_chart,
    make_hero_chart,
    make_mean_reversion_hero,
    make_oos_r2_chart,
    make_panel_a,
    make_panel_b,
    make_panel_c,
    make_pca_loadings_bar,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def long_z_series() -> pd.Series:
    """A monthly z-series covering 1900-2025 so every NBER band intersects."""
    idx = pd.date_range("1900-01-31", "2025-04-30", freq="ME")
    return pd.Series([0.5] * len(idx), index=idx, name="z")


@pytest.fixture(scope="module")
def long_dates(long_z_series: pd.Series) -> list[str]:
    return [pd.Timestamp(d).strftime("%Y-%m-%d") for d in long_z_series.index]


@pytest.fixture(scope="module")
def sp_df(long_z_series: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": long_z_series.index,
            "sp500_close": [100.0] * len(long_z_series),
            "regime_mvci": ["Fair Value"] * len(long_z_series),
        }
    )


# ---------------------------------------------------------------------------
# 1. Loader / dataframe contract
# ---------------------------------------------------------------------------


def test_nber_recessions_load_returns_dataframe_with_start_end() -> None:
    df = load_nber_recessions()
    assert {"start_date", "end_date"}.issubset(df.columns)
    assert (df["end_date"] >= df["start_date"]).all()
    # NBER lists ~34 US recessions since 1854.
    assert len(df) >= 30


def test_nber_recessions_is_sorted_ascending() -> None:
    df = load_nber_recessions()
    diffs = df["start_date"].diff().dropna()
    assert (diffs > pd.Timedelta(0)).all(), "start_date should be strictly increasing"


def test_nber_recessions_well_known_dates_present() -> None:
    """Sanity: Great Depression, 1973-75, 2008, COVID should all be present."""
    df = load_nber_recessions()
    starts = set(df["start_date"].dt.strftime("%Y-%m").tolist())
    for canonical in ("1929-08", "1973-11", "2007-12", "2020-02"):
        assert canonical in starts, f"Missing canonical recession start {canonical}"


def test_nber_recessions_parquet_materialized() -> None:
    """First load (or refresh) writes the parquet to MoDH."""
    refresh()  # force rebuild and persist
    assert NBER_RECESSIONS_PARQUET.exists()


# ---------------------------------------------------------------------------
# 2. add_recession_bands utility
# ---------------------------------------------------------------------------


def test_add_recession_bands_preserves_existing_shapes() -> None:
    layout = {"shapes": [{"type": "rect", "name": "pre_existing"}]}
    add_recession_bands(layout)
    assert any(s.get("name") == "pre_existing" for s in layout["shapes"])


def test_add_recession_bands_respects_x_range() -> None:
    layout: dict = {}
    add_recession_bands(
        layout,
        x_range=(pd.Timestamp("1990-01-01"), pd.Timestamp("2026-01-01")),
    )
    n_rect = sum(
        1 for s in layout["shapes"] if s.get("name") == "nber_recession"
    )
    # Recessions intersecting 1990-2026: 1990-91, 2001, 2007-09, 2020 = 4.
    assert n_rect == 4


def test_add_recession_bands_default_color_and_layer() -> None:
    layout: dict = {}
    add_recession_bands(layout)
    rects = [s for s in layout["shapes"] if s.get("name") == "nber_recession"]
    assert all(r["fillcolor"] == RECESSION_BAND_COLOR for r in rects)
    assert all(r["layer"] == "below" for r in rects)


# ---------------------------------------------------------------------------
# 3. Wired into all 8 time-series chart factories
# ---------------------------------------------------------------------------


def _count_recession_rects(spec: dict) -> int:
    return sum(
        1
        for s in spec["layout"].get("shapes", [])
        if s.get("name") == "nber_recession"
    )


def test_recession_bands_added_to_hero_chart(long_z_series: pd.Series) -> None:
    spec = make_hero_chart(long_z_series, title="test")
    assert _count_recession_rects(spec) >= 24


def test_recession_bands_added_to_panel_a(long_z_series: pd.Series) -> None:
    spec = make_panel_a(long_z_series)
    assert _count_recession_rects(spec) >= 24


def test_recession_bands_added_to_panel_c(sp_df: pd.DataFrame) -> None:
    spec = make_panel_c(sp_df)
    assert _count_recession_rects(spec) >= 24


def test_recession_bands_added_to_mean_reversion_hero(
    long_z_series: pd.Series,
) -> None:
    spec = make_mean_reversion_hero(long_z_series, long_z_series, 5.0)
    assert _count_recession_rects(spec) >= 24


def test_recession_bands_added_to_oos_r2(long_dates: list[str]) -> None:
    spec = make_oos_r2_chart(long_dates, [0.01] * len(long_dates))
    assert _count_recession_rects(spec) >= 24


def test_recession_bands_added_to_equity_curve(long_dates: list[str]) -> None:
    spec = make_equity_curve_chart(
        long_dates, [1.0] * len(long_dates), [1.0] * len(long_dates)
    )
    assert _count_recession_rects(spec) >= 24


def test_recession_bands_added_to_drawdown(long_dates: list[str]) -> None:
    spec = make_drawdown_chart(
        long_dates, [-0.05] * len(long_dates), [-0.05] * len(long_dates)
    )
    assert _count_recession_rects(spec) >= 24


def test_recession_bands_added_to_allocation(long_dates: list[str]) -> None:
    spec = make_allocation_chart(long_dates, [0.6] * len(long_dates))
    assert _count_recession_rects(spec) >= 24


# ---------------------------------------------------------------------------
# 4. Show-recessions toggle works
# ---------------------------------------------------------------------------


def test_show_recessions_false_emits_zero_bands(
    long_z_series: pd.Series, long_dates: list[str]
) -> None:
    """Every wired factory must respect show_recessions=False."""
    cases: list[dict] = [
        make_panel_a(long_z_series, show_recessions=False),
        make_hero_chart(long_z_series, title="t", show_recessions=False),
        make_panel_c(
            pd.DataFrame(
                {
                    "date": long_z_series.index,
                    "sp500_close": [100.0] * len(long_z_series),
                    "regime_mvci": ["Fair Value"] * len(long_z_series),
                }
            ),
            show_recessions=False,
        ),
        make_mean_reversion_hero(
            long_z_series, long_z_series, 5.0, show_recessions=False
        ),
        make_oos_r2_chart(
            long_dates, [0.01] * len(long_dates), show_recessions=False
        ),
        make_equity_curve_chart(
            long_dates,
            [1.0] * len(long_dates),
            [1.0] * len(long_dates),
            show_recessions=False,
        ),
        make_drawdown_chart(
            long_dates,
            [-0.05] * len(long_dates),
            [-0.05] * len(long_dates),
            show_recessions=False,
        ),
        make_allocation_chart(
            long_dates, [0.6] * len(long_dates), show_recessions=False
        ),
    ]
    for spec in cases:
        assert _count_recession_rects(spec) == 0


# ---------------------------------------------------------------------------
# 5. Excluded chart types do NOT receive bands
# ---------------------------------------------------------------------------


def test_recession_bands_excluded_from_scatter(long_z_series: pd.Series) -> None:
    """Panel B (z vs forward CAGR scatter) must NOT have recession bands."""
    scatter_df = pd.DataFrame(
        {
            "date": long_z_series.index[:60],
            "z_score_long_run": [0.5] * 60,
            "forward_120m_cagr": [0.05] * 60,
        }
    )
    spec = make_panel_b(
        scatter_df,
        current_z=0.5,
        regression={"beta": 0.1, "alpha": 0.05, "r2": 0.1},
    )
    assert _count_recession_rects(spec) == 0


def test_recession_bands_excluded_from_correlation_heatmap() -> None:
    """The diagnostics correlation heatmap is not a time series → no bands."""
    corr = pd.DataFrame(
        [[1.0, 0.5], [0.5, 1.0]], columns=["a", "b"], index=["a", "b"]
    )
    spec = make_correlation_heatmap(corr)
    assert _count_recession_rects(spec) == 0


def test_recession_bands_excluded_from_pca_loadings_bar() -> None:
    """PCA loadings is a horizontal bar chart → no bands."""
    spec = make_pca_loadings_bar({"a": 0.5, "b": 0.3, "c": 0.2})
    assert _count_recession_rects(spec) == 0


# ---------------------------------------------------------------------------
# 6. Consistent color across charts
# ---------------------------------------------------------------------------


def test_recession_bands_color_consistent_across_charts(
    long_z_series: pd.Series, long_dates: list[str]
) -> None:
    spec_a = make_panel_a(long_z_series)
    spec_h = make_hero_chart(long_z_series, title="t")
    spec_eq = make_equity_curve_chart(
        long_dates, [1.0] * len(long_dates), [1.0] * len(long_dates)
    )

    def _band_colors(spec: dict) -> set[str]:
        return {
            s["fillcolor"]
            for s in spec["layout"]["shapes"]
            if s.get("name") == "nber_recession"
        }

    colors = _band_colors(spec_a) | _band_colors(spec_h) | _band_colors(spec_eq)
    assert colors == {RECESSION_BAND_COLOR}
