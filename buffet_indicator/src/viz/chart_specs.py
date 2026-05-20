"""Plotly figure-spec builders for the dashboard charts (Spec v8b polish).

v8b changes (vs v8a):
  - Larger heights: hero 600px (was 400), panel 450px (was implicit ~350)
  - Larger typography: 14px ticks, 16px axis titles, 18px chart titles
  - Plotly modebar visible by default with drag-zoom, scroll-zoom, image export
  - Crosshair spike lines + ``hovermode = "x unified"``
  - Explicit dtick=1.0 on z-score y-axes, widened range to [-4, 4]
  - Historical-analog annotations (1929, 2000, 2021) on hero charts
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.viz.captions import REGIME_COLORS
from src.viz.chart_overlays import add_recession_bands


def _maybe_add_recessions(
    spec: dict[str, Any],
    dates: list[str] | None,
    show_recessions: bool,
) -> dict[str, Any]:
    """v11.0: add NBER recession bands to a time-series chart layout.

    No-op when ``show_recessions`` is False or ``dates`` is empty/None.
    Otherwise filters the band set to ``[min(dates), max(dates)]`` so we
    don't pollute the layout with rects outside the visible window.
    """
    if not show_recessions or not dates:
        return spec
    lo = pd.Timestamp(dates[0])
    hi = pd.Timestamp(dates[-1])
    if hi < lo:
        lo, hi = hi, lo
    add_recession_bands(spec["layout"], x_range=(lo, hi))
    return spec


# ---------------------------------------------------------------------------
# v8b typography + sizing constants
# ---------------------------------------------------------------------------

FONT_FAMILY = '"Inter", "Helvetica Neue", system-ui, sans-serif'
TICK_FONT_SIZE = 14
AXIS_TITLE_FONT_SIZE = 16
CHART_TITLE_FONT_SIZE = 18
LEGEND_FONT_SIZE = 13
ANNOTATION_FONT_SIZE = 13

HERO_HEIGHT = 600
PANEL_HEIGHT = 450
ZSCORE_Y_RANGE = [-4.0, 4.0]


def _z_axis_block(title: str = "Z-score (σ)") -> dict[str, Any]:
    """Common y-axis settings for z-score charts (v8b)."""
    return {
        "title": {
            "text": title,
            "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY},
        },
        "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
        "range": ZSCORE_Y_RANGE,
        "dtick": 1.0,
        "zeroline": True,
        "zerolinecolor": "#333",
        "zerolinewidth": 1.5,
        "gridcolor": "rgba(150, 150, 150, 0.2)",
        "showgrid": True,
        "showspikes": True,
        "spikecolor": "#666",
        "spikethickness": 1,
        "spikedash": "dot",
    }


def _x_axis_block(*, with_rangeslider: bool = True, with_rangeselector: bool = True,
                   default_button: int = 4) -> dict[str, Any]:
    """Common x-axis settings (v8b)."""
    block: dict[str, Any] = {
        "title": {
            "text": "",
            "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY},
        },
        "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
        "showspikes": True,
        "spikecolor": "#666",
        "spikethickness": 1,
        "spikedash": "dot",
        "spikemode": "across",
        "gridcolor": "rgba(150, 150, 150, 0.15)",
    }
    if with_rangeslider:
        block["rangeslider"] = {"visible": True, "thickness": 0.05}
    if with_rangeselector:
        block["rangeselector"] = {
            "buttons": [
                {"count": 1, "label": "1Y", "step": "year", "stepmode": "backward"},
                {"count": 5, "label": "5Y", "step": "year", "stepmode": "backward"},
                {"count": 10, "label": "10Y", "step": "year", "stepmode": "backward"},
                {"count": 30, "label": "30Y", "step": "year", "stepmode": "backward"},
                {"step": "all", "label": "All"},
            ],
            "active": default_button,
            "font": {"size": 13, "family": FONT_FAMILY, "color": "#333"},
            "bgcolor": "rgba(245, 245, 245, 0.9)",
            "activecolor": "#1F77B4",
            "borderwidth": 1,
            "bordercolor": "#ccc",
            "x": 0,
            "y": 1.10,
        }
    return block


def _interactive_config(chart_name: str = "chart") -> dict[str, Any]:
    """v8b interactive config: visible toolbar, drag-zoom, PNG export.

    v8b.1 fix B.2: scrollZoom defaults to False to avoid trapping page-scroll
    on touch devices. The dashboard JS runtime enables scrollZoom at runtime
    via feature detection (non-touch desktop only).
    """
    return {
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "scrollZoom": False,
        "doubleClick": "reset+autosize",
        "modeBarButtonsToRemove": [
            "lasso2d",
            "select2d",
            "autoScale2d",
            "hoverClosestCartesian",
            "hoverCompareCartesian",
        ],
        "toImageButtonOptions": {
            "format": "png",
            "filename": f"mv_valuation_{chart_name}",
            "height": 800,
            "width": 1400,
            "scale": 2,
        },
    }


# ---------------------------------------------------------------------------
# Historical analog annotations (1929, 2000, 2021 peaks)
# ---------------------------------------------------------------------------


def _add_historical_annotations(z_series: pd.Series, annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append labeled arrows at 1929, 2000, 2021 peak dates when in series range.

    v8b.1 fix C: each annotation has ``xanchor``/``ax``/``xshift`` configured so
    the label sits on the chart-interior side of the arrow (not overflowing
    past the right edge at 360px viewport).
    """
    if z_series is None or z_series.empty:
        return annotations
    idx_min, idx_max = z_series.index.min(), z_series.index.max()
    total_span = idx_max - idx_min
    # All annotations live in the (date, z) data space; anchor side is chosen
    # by relative position to keep labels inside the plotting area on narrow
    # viewports.
    peaks = [
        ("1929-09-30", "1929 peak<br>(crash followed)"),
        ("2000-03-31", "Dot-com peak<br>(-50% over 2y)"),
        ("2021-12-31", "Post-COVID peak<br>(-25% in 2022)"),
    ]
    for date_str, label in peaks:
        date = pd.Timestamp(date_str)
        if not (idx_min <= date <= idx_max):
            continue
        idx = z_series.index.get_indexer([date], method="nearest")[0]
        actual_date = z_series.index[idx]
        actual_z = float(z_series.iloc[idx])
        # Relative x-position in [0, 1]. Right-most annotation must anchor to
        # the right so the label extends leftward into the chart.
        rel = (
            (actual_date - idx_min).total_seconds()
            / total_span.total_seconds()
            if total_span.total_seconds() > 0
            else 0.5
        )
        if rel > 0.80:
            xanchor = "right"
            ax = -30
        elif rel < 0.20:
            xanchor = "left"
            ax = 30
        else:
            xanchor = "center"
            ax = 0
        annotations.append(
            {
                "x": actual_date.strftime("%Y-%m-%d"),
                "y": actual_z,
                "xref": "x",
                "yref": "y",
                "text": label,
                "showarrow": True,
                "arrowhead": 2,
                "arrowsize": 1,
                "arrowcolor": "#666",
                "ax": ax,
                "ay": -40,
                "xanchor": xanchor,
                "bgcolor": "rgba(255, 255, 255, 0.92)",
                "bordercolor": "#666",
                "borderwidth": 1,
                "font": {"size": 11, "family": FONT_FAMILY, "color": "#222"},
            }
        )
    return annotations


# ---------------------------------------------------------------------------
# Regime background bands
# ---------------------------------------------------------------------------


def make_regime_band_shapes() -> list[dict[str, Any]]:
    """Horizontal background bands colored by regime (Master Spec section 7.0.E)."""
    return [
        {
            "type": "rect",
            "xref": "paper",
            "yref": "y",
            "x0": 0,
            "x1": 1,
            "y0": 2,
            "y1": 3.5,
            "fillcolor": REGIME_COLORS["Strongly Overvalued"],
            "opacity": 0.10,
            "layer": "below",
            "line": {"width": 0},
        },
        {
            "type": "rect",
            "xref": "paper",
            "yref": "y",
            "x0": 0,
            "x1": 1,
            "y0": 1,
            "y1": 2,
            "fillcolor": REGIME_COLORS["Overvalued"],
            "opacity": 0.08,
            "layer": "below",
            "line": {"width": 0},
        },
        {
            "type": "rect",
            "xref": "paper",
            "yref": "y",
            "x0": 0,
            "x1": 1,
            "y0": -1,
            "y1": 1,
            "fillcolor": REGIME_COLORS["Fair Value"],
            "opacity": 0.05,
            "layer": "below",
            "line": {"width": 0},
        },
        {
            "type": "rect",
            "xref": "paper",
            "yref": "y",
            "x0": 0,
            "x1": 1,
            "y0": -2,
            "y1": -1,
            "fillcolor": REGIME_COLORS["Undervalued"],
            "opacity": 0.08,
            "layer": "below",
            "line": {"width": 0},
        },
        {
            "type": "rect",
            "xref": "paper",
            "yref": "y",
            "x0": 0,
            "x1": 1,
            "y0": -3.5,
            "y1": -2,
            "fillcolor": REGIME_COLORS["Strongly Undervalued"],
            "opacity": 0.10,
            "layer": "below",
            "line": {"width": 0},
        },
    ]


def _classify_regime(z: float) -> str:
    if z >= 2.0:
        return "Strongly Overvalued"
    if z >= 1.0:
        return "Overvalued"
    if z >= -1.0:
        return "Fair Value"
    if z >= -2.0:
        return "Undervalued"
    return "Strongly Undervalued"


# ---------------------------------------------------------------------------
# Panel A: Z-score time series
# ---------------------------------------------------------------------------


def make_panel_a(
    z_series: pd.Series,
    *,
    title: str = "Z-Score Time Series",
    chart_name: str = "panel_a",
    show_recessions: bool = True,
) -> dict[str, Any]:
    """Build a Plotly figure dict for Panel A (z-score time series).

    v11.0: NBER recession bands rendered behind the trace when
    ``show_recessions`` is True (default).
    """
    z_clean = z_series.dropna()
    dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in z_clean.index]
    values = [float(v) for v in z_clean.values]
    latest_date = dates[-1] if dates else None
    latest_val = values[-1] if values else None

    # Build custom data: regime label + percentile per point.
    regime_labels = [_classify_regime(v) for v in values]
    pcts: list[float] = []
    if values:
        arr = np.asarray(values, dtype="float64")
        ranks = arr.argsort().argsort()
        denom = max(len(arr) - 1, 1)
        pcts = (ranks / denom * 100.0).tolist()
    customdata = list(zip(regime_labels, pcts))

    spec = {
        "data": [
            {
                "x": dates,
                "y": values,
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#1F77B4", "width": 2},
                "name": "Z-score",
                "customdata": customdata,
                "hovertemplate": (
                    "<b>%{x|%B %Y}</b><br>"
                    "Z-score: %{y:+.2f} σ<br>"
                    "Regime: %{customdata[0]}<br>"
                    "Percentile: %{customdata[1]:.0f}th<extra></extra>"
                ),
            },
            {
                "x": [latest_date] if latest_date else [],
                "y": [latest_val] if latest_val is not None else [],
                "type": "scatter",
                "mode": "markers+text",
                "marker": {"size": 12, "color": "#000"},
                "text": [
                    f"Current: {latest_val:+.2f}σ" if latest_val is not None else ""
                ],
                "textposition": "top right",
                "textfont": {"size": 13, "family": FONT_FAMILY},
                "showlegend": False,
                "hoverinfo": "skip",
            },
        ],
        "layout": {
            "title": {
                "text": title,
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                "x": 0.5,
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": _x_axis_block(),
            "yaxis": _z_axis_block(),
            "shapes": make_regime_band_shapes(),
            "hovermode": "x unified",
            "hoverdistance": 50,
            "spikedistance": -1,
            "height": PANEL_HEIGHT,
            "margin": {"t": 70, "b": 80, "l": 70, "r": 30},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "legend": {"font": {"size": LEGEND_FONT_SIZE, "family": FONT_FAMILY}},
        },
        "config": _interactive_config(chart_name),
    }
    return _maybe_add_recessions(spec, dates, show_recessions)


# ---------------------------------------------------------------------------
# Panel B: Z vs forward 10Y CAGR
# ---------------------------------------------------------------------------


def make_panel_b(
    scatter_df: pd.DataFrame,
    *,
    current_z: float,
    regression: dict[str, float],
    title: str = "Z-Score vs 10-Year Forward CAGR",
    horizon_col: str = "forward_120m_cagr",
    chart_name: str = "panel_b",
) -> dict[str, Any]:
    """Scatter plot of z (x) vs forward h-month CAGR (y), with OLS line."""
    df = scatter_df.dropna(subset=["z_score_long_run", horizon_col]).copy()
    df = df.sort_values("date")
    dates = pd.to_datetime(df["date"])
    x = df["z_score_long_run"].astype("float64").tolist()
    y = (df[horizon_col].astype("float64") * 100.0).tolist()
    year_ints = dates.dt.year.astype("int64").tolist()
    custom = dates.dt.strftime("%Y-%m").tolist()

    alpha = float(regression.get("alpha", 0.0))
    beta = float(regression.get("beta", 0.0))
    r_squared = float(regression.get("r_squared", 0.0))
    t_nw = float(regression.get("t_nw", 0.0))

    x_min, x_max = -3.0, 3.0
    if x:
        x_min = min(x_min, min(x))
        x_max = max(x_max, max(x))
    line_x = [x_min, x_max]
    line_y = [(alpha + beta * v) * 100.0 for v in line_x]

    return {
        "data": [
            {
                "x": x,
                "y": y,
                "type": "scatter",
                "mode": "markers",
                "marker": {
                    "size": 7,
                    "opacity": 0.55,
                    "color": year_ints,
                    "colorscale": "Turbo",
                    "showscale": True,
                    "colorbar": {
                        "title": {
                            "text": "Year",
                            "font": {"size": 13, "family": FONT_FAMILY},
                        },
                        "tickfont": {"size": 12, "family": FONT_FAMILY},
                    },
                },
                "customdata": custom,
                "hovertemplate": (
                    "<b>%{customdata}</b><br>"
                    "z = %{x:+.2f} σ<br>"
                    "10Y CAGR = %{y:.1f}%<extra></extra>"
                ),
                "name": "Historical",
            },
            {
                "x": line_x,
                "y": line_y,
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "red", "width": 2, "dash": "dash"},
                "name": "OLS fit",
                "hoverinfo": "skip",
            },
            {
                "x": [current_z, current_z],
                "y": [min(y) if y else -10.0, max(y) if y else 20.0],
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#000", "width": 1, "dash": "dot"},
                "name": "Current z",
                "hoverinfo": "skip",
            },
        ],
        "layout": {
            "title": {
                "text": title,
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                "x": 0.5,
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": {
                "title": {
                    "text": "Z-score at observation date",
                    "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                },
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                "showspikes": True,
                "spikecolor": "#666",
                "spikethickness": 1,
                "spikedash": "dot",
                "zeroline": True,
                "zerolinecolor": "#999",
                "gridcolor": "rgba(150, 150, 150, 0.2)",
            },
            "yaxis": {
                "title": {
                    "text": "Subsequent 10Y CAGR",
                    "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                },
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                # v8b.1 fix B.1: y-values are absolute percent (we multiply by
                # 100 upstream), so dtick=5 means a 5pp gridline. With
                # ticksuffix="%" the labels read 5%, 10%, 15%...
                "ticksuffix": "%",
                "dtick": 5,
                "nticks": 10,
                "showspikes": True,
                "spikecolor": "#666",
                "spikethickness": 1,
                "spikedash": "dot",
                "zeroline": True,
                "zerolinecolor": "#333",
                "zerolinewidth": 1.5,
                "gridcolor": "rgba(150, 150, 150, 0.2)",
            },
            "annotations": [
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.02,
                    "y": 0.98,
                    "showarrow": False,
                    "text": (
                        f"R² = {r_squared:.2f}<br>β = {beta:+.3f}<br>"
                        f"t_NW = {t_nw:+.2f}"
                    ),
                    "align": "left",
                    "bgcolor": "rgba(255,255,255,0.9)",
                    "bordercolor": "#cccccc",
                    "borderwidth": 1,
                    "font": {"size": ANNOTATION_FONT_SIZE, "family": FONT_FAMILY},
                },
            ],
            "height": PANEL_HEIGHT,
            "margin": {"t": 60, "b": 70, "l": 70, "r": 30},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "hovermode": "closest",
            "legend": {"font": {"size": LEGEND_FONT_SIZE, "family": FONT_FAMILY}},
        },
        "config": _interactive_config(chart_name),
    }


# ---------------------------------------------------------------------------
# Panel C: S&P 500 colored by regime
# ---------------------------------------------------------------------------


def make_panel_c(
    sp500_df: pd.DataFrame,
    *,
    chart_name: str = "panel_c",
    show_recessions: bool = True,
) -> dict[str, Any]:
    """S&P 500 (log scale) colored by MVCI regime.

    v11.0: NBER recession bands rendered behind the regime-colored trace when
    ``show_recessions`` is True (default).
    """
    df = sp500_df.dropna(subset=["sp500_close"]).copy()
    df = df.sort_values("date").reset_index(drop=True)
    if df.empty:
        return _empty_panel_c(chart_name)

    df["regime_mvci"] = df["regime_mvci"].fillna("Insufficient Data")
    runs: list[tuple[str, int, int]] = []
    current_regime = df["regime_mvci"].iloc[0]
    run_start = 0
    for i in range(1, len(df)):
        if df["regime_mvci"].iloc[i] != current_regime:
            runs.append((current_regime, run_start, i))
            current_regime = df["regime_mvci"].iloc[i]
            run_start = i - 1
    runs.append((current_regime, run_start, len(df)))

    traces: list[dict[str, Any]] = []
    seen: set[str] = set()
    for regime, lo, hi in runs:
        segment = df.iloc[lo:hi]
        color = REGIME_COLORS.get(regime, "#666666")
        showlegend = regime not in seen
        seen.add(regime)
        traces.append(
            {
                "x": segment["date"].astype(str).tolist(),
                "y": segment["sp500_close"].astype("float64").tolist(),
                "type": "scatter",
                "mode": "lines",
                "line": {"color": color, "width": 2},
                "name": regime,
                "legendgroup": regime,
                "showlegend": showlegend,
                "hovertemplate": (
                    "<b>%{x}</b><br>"
                    "S&P 500 = %{y:.0f}<br>"
                    f"Regime: {regime}<extra></extra>"
                ),
            }
        )

    # v11.0: extract date range from df for recession overlay.
    dates_for_overlay = df["date"].astype(str).tolist()

    spec = {
        "data": traces,
        "layout": {
            "title": {
                "text": "S&P 500 (log scale) — Colored by MVCI Regime",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                "x": 0.5,
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": {
                "title": {"text": "Date", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                "showspikes": True,
                "spikecolor": "#666",
                "spikethickness": 1,
                "spikedash": "dot",
                "spikemode": "across",
                "gridcolor": "rgba(150, 150, 150, 0.15)",
            },
            "yaxis": {
                "title": {"text": "S&P 500", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                "type": "log",
                "showspikes": True,
                "spikecolor": "#666",
                "spikethickness": 1,
                "spikedash": "dot",
                "gridcolor": "rgba(150, 150, 150, 0.2)",
                "nticks": 8,
            },
            "hovermode": "x unified",
            "hoverdistance": 50,
            "spikedistance": -1,
            "height": PANEL_HEIGHT,
            "margin": {"t": 60, "b": 70, "l": 70, "r": 30},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "legend": {"font": {"size": LEGEND_FONT_SIZE, "family": FONT_FAMILY}},
        },
        "config": _interactive_config(chart_name),
    }
    return _maybe_add_recessions(spec, dates_for_overlay, show_recessions)


def _empty_panel_c(chart_name: str = "panel_c") -> dict[str, Any]:
    return {
        "data": [],
        "layout": {
            "title": {"text": "S&P 500 — data unavailable", "x": 0.5},
            "yaxis": {"type": "log"},
            "height": PANEL_HEIGHT,
            "margin": {"t": 50, "b": 60, "l": 60, "r": 30},
            "annotations": [
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "text": "S&P 500 monthly series not available",
                }
            ],
        },
        "config": _interactive_config(chart_name),
    }


# ---------------------------------------------------------------------------
# Sparkline (Overview cards)
# ---------------------------------------------------------------------------


def make_sparkline(z_series: pd.Series, *, color: str = "#1F77B4") -> dict[str, Any]:
    """Minimalist line chart for the Overview card sparklines (no axes/legend)."""
    z_clean = z_series.dropna()
    tail = z_clean.tail(360)
    return {
        "data": [
            {
                "x": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in tail.index],
                "y": [float(v) for v in tail.values],
                "type": "scatter",
                "mode": "lines",
                "line": {"color": color, "width": 1.5},
                "hovertemplate": "%{x}: %{y:+.2f}σ<extra></extra>",
                "showlegend": False,
            }
        ],
        "layout": {
            "xaxis": {"visible": False, "fixedrange": True},
            "yaxis": {"visible": False, "fixedrange": True},
            "margin": {"t": 4, "b": 4, "l": 4, "r": 4},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "showlegend": False,
        },
        "config": {"displayModeBar": False, "responsive": True, "staticPlot": True},
    }


# ---------------------------------------------------------------------------
# PCA loadings bar chart
# ---------------------------------------------------------------------------


def make_pca_loadings_bar(loadings: dict[str, float]) -> dict[str, Any]:
    """Horizontal bar chart of MVCI PCA first-PC loadings."""
    if not loadings:
        return {"data": [], "layout": {"title": {"text": "PCA loadings — n/a"}}}
    ordered = sorted(loadings.items(), key=lambda x: x[1], reverse=True)
    names = [k for k, _ in ordered]
    vals = [float(v) for _, v in ordered]
    return {
        "data": [
            {
                "x": vals,
                "y": names,
                "type": "bar",
                "orientation": "h",
                "marker": {"color": "#1F77B4"},
                "hovertemplate": "%{y}: %{x:.3f}<extra></extra>",
            }
        ],
        "layout": {
            "title": {
                "text": "PCA First PC Loadings",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                "x": 0.5,
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": {
                "title": {"text": "Loading", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "yaxis": {
                "autorange": "reversed",
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "height": 360,
            "margin": {"t": 50, "b": 40, "l": 150, "r": 20},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
        },
        "config": _interactive_config("pca_loadings"),
    }


# ---------------------------------------------------------------------------
# Hero chart (Spec v8a.1, scaled for v8b)
# ---------------------------------------------------------------------------


def make_hero_chart(
    z_series: pd.Series,
    title: str,
    subtitle: str = "Z-score deviations from the long-run trend, color-coded by regime",
    *,
    height: int = HERO_HEIGHT,
    current_label_format: str = "Current: {value:+.2f} σ",
    chart_name: str = "hero",
    add_historical_annotations: bool = True,
    show_recessions: bool = True,
) -> dict[str, Any]:
    """Hero chart at the top of each tab. Scaled-up Panel A with more
    prominent annotations and regime bands.

    v8b updates:
      - height default 600
      - Plotly toolbar visible
      - 14px tick fonts, 16px axis title
      - Crosshair on x and y
      - Historical analog annotations (1929/2000/2021)
      - Wide y-range [-4, 4] with dtick=1.0
    """
    z_clean = z_series.dropna()
    dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in z_clean.index]
    values = [float(v) for v in z_clean.values]
    latest_date = dates[-1] if dates else None
    latest_val = values[-1] if values else None

    regime_labels = [_classify_regime(v) for v in values]
    pcts: list[float] = []
    if values:
        arr = np.asarray(values, dtype="float64")
        ranks = arr.argsort().argsort()
        denom = max(len(arr) - 1, 1)
        pcts = (ranks / denom * 100.0).tolist()
    customdata = list(zip(regime_labels, pcts))

    shapes = make_regime_band_shapes()
    for s in shapes:
        s["opacity"] = 0.15

    annotations: list[dict[str, Any]] = []
    if add_historical_annotations:
        annotations = _add_historical_annotations(z_clean, annotations)

    spec = {
        "data": [
            {
                "x": dates,
                "y": values,
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#1F77B4", "width": 2.5},
                "name": "Z-score",
                "customdata": customdata,
                "hovertemplate": (
                    "<b>%{x|%B %Y}</b><br>"
                    "Z-score: %{y:+.2f} σ<br>"
                    "Regime: %{customdata[0]}<br>"
                    "Percentile: %{customdata[1]:.0f}th<extra></extra>"
                ),
            },
            {
                "x": [latest_date] if latest_date else [],
                "y": [latest_val] if latest_val is not None else [],
                "type": "scatter",
                "mode": "markers+text",
                "marker": {
                    "size": 16,
                    "color": "#000",
                    "line": {"color": "#fff", "width": 2},
                },
                "text": [
                    current_label_format.format(value=latest_val)
                    if latest_val is not None
                    else ""
                ],
                "textposition": "top right",
                "textfont": {"size": 14, "color": "#000", "family": FONT_FAMILY},
                "showlegend": False,
                "hoverinfo": "skip",
            },
        ],
        "layout": {
            "title": {
                "text": (
                    f"<b>{title}</b><br>"
                    f"<span style='font-size:13px;color:#666'>{subtitle}</span>"
                ),
                "x": 0.5,
                "xanchor": "center",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": _x_axis_block(),
            "yaxis": _z_axis_block(),
            "shapes": shapes,
            "annotations": annotations,
            "hovermode": "x unified",
            "hoverdistance": 50,
            "spikedistance": -1,
            "height": height,
            "margin": {"t": 100, "b": 90, "l": 75, "r": 35},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "legend": {"font": {"size": LEGEND_FONT_SIZE, "family": FONT_FAMILY}},
        },
        "config": _interactive_config(chart_name),
    }
    return _maybe_add_recessions(spec, dates, show_recessions)


# ---------------------------------------------------------------------------
# Mean Reversion hero chart -- real S&P + exponential trend line
# ---------------------------------------------------------------------------


def make_mean_reversion_hero(
    real_sp_series: pd.Series,
    trend_series: pd.Series,
    current_deviation_pct: float,
    *,
    height: int = HERO_HEIGHT,
    chart_name: str = "mean_reversion_hero",
    show_recessions: bool = True,
) -> dict[str, Any]:
    """Hero chart for the Mean Reversion tab.

    Two lines on a log y-axis: the real S&P 500 and its log-linear trend.
    Annotation reports current % deviation from trend (red if above, green
    if below).
    """
    sp_clean = real_sp_series.dropna()
    tr_clean = trend_series.dropna()
    common = sp_clean.index.intersection(tr_clean.index)
    if len(common) > 0:
        sp_clean = sp_clean.loc[common]
        tr_clean = tr_clean.loc[common]

    annot_color = "#C8102E" if current_deviation_pct > 0 else "#1B7A3E"
    annot_text = f"Currently {current_deviation_pct:+.1f}% from long-run trend"
    dates_for_overlay = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in sp_clean.index]

    spec = {
        "data": [
            {
                "x": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in sp_clean.index],
                "y": [float(v) for v in sp_clean.values],
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#1F77B4", "width": 2.5},
                "name": "Real S&P 500",
                "hovertemplate": (
                    "<b>%{x|%B %Y}</b><br>"
                    "Real S&P = %{y:,.1f}<extra></extra>"
                ),
            },
            {
                "x": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in tr_clean.index],
                "y": [float(v) for v in tr_clean.values],
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#666666", "width": 2, "dash": "dash"},
                "name": "Exponential trend",
                "hovertemplate": (
                    "<b>%{x|%B %Y}</b><br>"
                    "Trend = %{y:,.1f}<extra></extra>"
                ),
            },
        ],
        "layout": {
            "title": {
                "text": (
                    "<b>Real S&P 500 vs Exponential Trend</b><br>"
                    "<span style='font-size:13px;color:#666'>"
                    "Inflation-adjusted price on a log scale; trend fit over full history"
                    "</span>"
                ),
                "x": 0.5,
                "xanchor": "center",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": _x_axis_block(),
            "yaxis": {
                "title": {
                    "text": "Real S&P 500 (log scale)",
                    "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                },
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                "type": "log",
                "nticks": 8,
                "showspikes": True,
                "spikecolor": "#666",
                "spikethickness": 1,
                "spikedash": "dot",
                "gridcolor": "rgba(150, 150, 150, 0.2)",
            },
            "annotations": [
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 1.10,
                    "showarrow": False,
                    "text": annot_text,
                    "font": {"size": 15, "color": annot_color, "family": FONT_FAMILY},
                    "align": "center",
                }
            ],
            "hovermode": "x unified",
            "hoverdistance": 50,
            "spikedistance": -1,
            "height": height,
            "margin": {"t": 110, "b": 90, "l": 75, "r": 35},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "legend": {"font": {"size": LEGEND_FONT_SIZE, "family": FONT_FAMILY}},
        },
        "config": _interactive_config(chart_name),
    }
    return _maybe_add_recessions(spec, dates_for_overlay, show_recessions)


# ---------------------------------------------------------------------------
# v8b — Diagnostics helpers (correlation heatmap, OOS R² evolution)
# ---------------------------------------------------------------------------


def make_correlation_heatmap(corr_matrix: pd.DataFrame, *, chart_name: str = "correlation") -> dict[str, Any]:
    """Symmetric correlation heatmap with annotations."""
    if corr_matrix is None or corr_matrix.empty:
        return {"data": [], "layout": {"title": {"text": "Correlation matrix unavailable"}}}
    labels = list(corr_matrix.columns)
    z_vals = corr_matrix.values.tolist()
    text_vals = [[f"{v:+.2f}" for v in row] for row in corr_matrix.values]
    return {
        "data": [
            {
                "type": "heatmap",
                "x": labels,
                "y": labels,
                "z": z_vals,
                "text": text_vals,
                "texttemplate": "%{text}",
                "textfont": {"size": 12, "family": FONT_FAMILY},
                "colorscale": "RdBu",
                "reversescale": True,
                "zmin": -1,
                "zmax": 1,
                "hovertemplate": "%{x} ↔ %{y}<br>ρ = %{z:+.3f}<extra></extra>",
                "colorbar": {
                    "title": {"text": "ρ", "font": {"size": 13, "family": FONT_FAMILY}},
                    "tickfont": {"size": 12, "family": FONT_FAMILY},
                },
            }
        ],
        "layout": {
            "title": {
                "text": "Cross-variant z-score correlation matrix",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                "x": 0.5,
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": {
                "tickfont": {"size": 12, "family": FONT_FAMILY},
                "side": "bottom",
            },
            "yaxis": {
                "tickfont": {"size": 12, "family": FONT_FAMILY},
                "autorange": "reversed",
            },
            "height": 480,
            "margin": {"t": 50, "b": 100, "l": 130, "r": 60},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
        },
        "config": _interactive_config(chart_name),
    }


def make_oos_r2_chart(
    dates: list[str],
    r2_values: list[float],
    *,
    chart_name: str = "oos_r2",
    show_recessions: bool = True,
) -> dict[str, Any]:
    """OOS R² (Goyal-Welch) evolution line chart."""
    spec = {
        "data": [
            {
                "x": dates,
                "y": r2_values,
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#1F77B4", "width": 2},
                "name": "OOS R² (10Y)",
                "hovertemplate": "%{x}<br>R²_OOS = %{y:.3f}<extra></extra>",
            },
            {
                "x": [dates[0] if dates else None, dates[-1] if dates else None],
                "y": [0.0, 0.0],
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#999", "width": 1, "dash": "dash"},
                "name": "Zero",
                "hoverinfo": "skip",
                "showlegend": False,
            },
        ],
        "layout": {
            "title": {
                "text": "Out-of-sample R² (Goyal-Welch, expanding window, 10Y horizon)",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                "x": 0.5,
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": {
                "title": {"text": "End of training window", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                "gridcolor": "rgba(150, 150, 150, 0.15)",
            },
            "yaxis": {
                "title": {"text": "R²_OOS", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                "gridcolor": "rgba(150, 150, 150, 0.2)",
                "zeroline": True,
                "zerolinecolor": "#666",
            },
            "height": PANEL_HEIGHT,
            "margin": {"t": 60, "b": 70, "l": 75, "r": 35},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "hovermode": "x unified",
        },
        "config": _interactive_config(chart_name),
    }
    return _maybe_add_recessions(spec, list(dates) if dates else None, show_recessions)


def make_acf_pacf_charts(
    residuals: pd.Series,
    *,
    n_lags: int = 20,
    chart_name: str = "acf_pacf",
) -> dict[str, Any]:
    """Two-panel Plotly spec for residual ACF (left) and PACF (right).

    Stem plot per lag with 95% confidence bands at ±1.96/√N (Bartlett's
    approximation under the null of white noise).
    """
    if residuals is None or residuals.empty or len(residuals.dropna()) < n_lags + 5:
        return {"data": [], "layout": {"title": {"text": "ACF/PACF — insufficient residuals"}}}

    series = residuals.dropna().astype("float64").to_numpy()
    n = len(series)
    ci_band = 1.96 / np.sqrt(n)

    try:
        from statsmodels.tsa.stattools import acf, pacf
    except ImportError:
        return {"data": [], "layout": {"title": {"text": "ACF/PACF unavailable — statsmodels missing"}}}

    acf_vals = acf(series, nlags=n_lags, fft=True)
    pacf_vals = pacf(series, nlags=n_lags, method="ywm")
    lags = list(range(len(acf_vals)))

    def _stems(values: list[float], xaxis: str, yaxis: str, color: str, name: str) -> list[dict[str, Any]]:
        traces: list[dict[str, Any]] = []
        # Stem lines (vertical from 0 to value) — one trace per lag for clarity.
        for lag, v in zip(lags, values, strict=False):
            traces.append(
                {
                    "x": [lag, lag],
                    "y": [0.0, float(v)],
                    "type": "scatter",
                    "mode": "lines",
                    "line": {"color": color, "width": 1.5},
                    "xaxis": xaxis,
                    "yaxis": yaxis,
                    "showlegend": False,
                    "hoverinfo": "skip",
                }
            )
        # Markers on top
        traces.append(
            {
                "x": lags,
                "y": [float(v) for v in values],
                "type": "scatter",
                "mode": "markers",
                "marker": {"size": 7, "color": color},
                "xaxis": xaxis,
                "yaxis": yaxis,
                "name": name,
                "hovertemplate": "Lag %{x}<br>" + name + " = %{y:+.3f}<extra></extra>",
                "showlegend": False,
            }
        )
        return traces

    traces = _stems(list(acf_vals), "x", "y", "#1F77B4", "ACF") + _stems(
        list(pacf_vals), "x2", "y2", "#C8102E", "PACF"
    )

    # Confidence bands (horizontal lines at ±ci_band)
    for sign in (1, -1):
        for xaxis, yaxis in (("x", "y"), ("x2", "y2")):
            traces.append(
                {
                    "x": [0, n_lags],
                    "y": [sign * ci_band, sign * ci_band],
                    "type": "scatter",
                    "mode": "lines",
                    "line": {"color": "rgba(200, 16, 46, 0.5)", "width": 1, "dash": "dash"},
                    "xaxis": xaxis,
                    "yaxis": yaxis,
                    "hoverinfo": "skip",
                    "showlegend": False,
                }
            )

    return {
        "data": traces,
        "layout": {
            "title": {
                "text": "Residual ACF & PACF — MVCI 10Y predictive regression",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                "x": 0.5,
            },
            "font": {"family": FONT_FAMILY},
            "grid": {"rows": 1, "columns": 2, "pattern": "independent"},
            "xaxis": {
                "title": {"text": "Lag (months)", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY},
                "dtick": 2,
                "anchor": "y",
                "domain": [0.0, 0.46],
            },
            "yaxis": {
                "title": {"text": "ACF", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY},
                "zeroline": True,
                "zerolinecolor": "#333",
                "range": [-1.05, 1.05],
            },
            "xaxis2": {
                "title": {"text": "Lag (months)", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY},
                "dtick": 2,
                "anchor": "y2",
                "domain": [0.54, 1.0],
            },
            "yaxis2": {
                "title": {"text": "PACF", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY},
                "zeroline": True,
                "zerolinecolor": "#333",
                "range": [-1.05, 1.05],
                "anchor": "x2",
            },
            "height": 420,
            "margin": {"t": 60, "b": 70, "l": 70, "r": 30},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
        },
        "config": _interactive_config(chart_name),
    }


def make_calibration_plot(
    buckets: list[dict[str, float]],
    *,
    brier_score: float,
    reliability: float,
    resolution: float,
    uncertainty: float,
    chart_name: str = "calibration",
) -> dict[str, Any]:
    """Reliability diagram + Brier decomposition (v8b.1 A.4)."""
    if not buckets:
        return {"data": [], "layout": {"title": {"text": "Calibration — insufficient data"}}}

    x = [b["predicted_mean"] for b in buckets]
    y = [b["realized_freq"] for b in buckets]
    n = [b["n"] for b in buckets]
    sizes = [max(8.0, float(np.sqrt(c)) * 2.0) for c in n]

    return {
        "data": [
            {
                "x": [0, 1],
                "y": [0, 1],
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#999", "width": 1.5, "dash": "dash"},
                "name": "Perfect calibration",
                "hoverinfo": "skip",
            },
            {
                "x": x,
                "y": y,
                "type": "scatter",
                "mode": "markers+lines",
                "marker": {"size": sizes, "color": "#1F77B4"},
                "line": {"color": "#1F77B4", "width": 2},
                "name": "Observed",
                "customdata": n,
                "hovertemplate": (
                    "Predicted: %{x:.2f}<br>"
                    "Realized: %{y:.2f}<br>"
                    "n = %{customdata}<extra></extra>"
                ),
            },
        ],
        "layout": {
            "title": {
                "text": "Calibration / reliability diagram (P(10Y CAGR < 5%))",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                "x": 0.5,
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": {
                "title": {"text": "Predicted probability", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY},
                "dtick": 0.1,
                "range": [0.0, 1.0],
                "gridcolor": "rgba(150, 150, 150, 0.2)",
            },
            "yaxis": {
                "title": {"text": "Realized frequency", "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY},
                "dtick": 0.1,
                "range": [0.0, 1.0],
                "gridcolor": "rgba(150, 150, 150, 0.2)",
            },
            "annotations": [
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.02,
                    "y": 0.98,
                    "showarrow": False,
                    "align": "left",
                    "text": (
                        f"Brier score: {brier_score:.3f}<br>"
                        f"Reliability: {reliability:.3f}<br>"
                        f"Resolution: {resolution:.3f}<br>"
                        f"Uncertainty: {uncertainty:.3f}"
                    ),
                    "bgcolor": "rgba(255, 255, 255, 0.92)",
                    "bordercolor": "#cccccc",
                    "borderwidth": 1,
                    "font": {"size": ANNOTATION_FONT_SIZE, "family": FONT_FAMILY},
                }
            ],
            "height": PANEL_HEIGHT,
            "margin": {"t": 60, "b": 70, "l": 75, "r": 35},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "hovermode": "closest",
            "legend": {"font": {"size": LEGEND_FONT_SIZE, "family": FONT_FAMILY}},
        },
        "config": _interactive_config(chart_name),
    }


def make_equity_curve_chart(
    dates: list[str],
    strategy_nav: list[float],
    benchmark_nav: list[float],
    *,
    chart_name: str = "equity_curve",
    show_recessions: bool = True,
) -> dict[str, Any]:
    """v10.0: log-scale strategy vs benchmark NAV chart."""
    spec = {
        "data": [
            {
                "x": dates,
                "y": strategy_nav,
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#1F77B4", "width": 2.5},
                "name": "Tactical strategy",
                "hovertemplate": "<b>%{x|%Y-%m}</b><br>NAV = %{y:.2f}x<extra></extra>",
            },
            {
                "x": dates,
                "y": benchmark_nav,
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#999999", "width": 2.5, "dash": "dash"},
                "name": "Benchmark (100% S&P 500 TR)",
                "hovertemplate": "<b>%{x|%Y-%m}</b><br>NAV = %{y:.2f}x<extra></extra>",
            },
        ],
        "layout": {
            "title": {
                "text": "<b>Tactical strategy vs buy-and-hold (100% S&P 500 TR)</b><br>"
                "<span style='font-size:13px;color:#666'>"
                "Cumulative NAV, log scale, 1875-present"
                "</span>",
                "x": 0.5,
                "xanchor": "center",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": _x_axis_block(),
            "yaxis": {
                "title": {
                    "text": "Cumulative NAV (log scale)",
                    "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                },
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                "type": "log",
                "nticks": 8,
                "gridcolor": "rgba(150, 150, 150, 0.2)",
            },
            "hovermode": "x unified",
            "hoverdistance": 50,
            "height": HERO_HEIGHT,
            "margin": {"t": 100, "b": 90, "l": 75, "r": 35},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "legend": {"font": {"size": LEGEND_FONT_SIZE, "family": FONT_FAMILY}},
        },
        "config": _interactive_config(chart_name),
    }
    return _maybe_add_recessions(spec, list(dates) if dates else None, show_recessions)


def make_drawdown_chart(
    dates: list[str],
    dd_strategy: list[float],
    dd_benchmark: list[float],
    *,
    chart_name: str = "drawdown",
    show_recessions: bool = True,
) -> dict[str, Any]:
    """v10.0: dual drawdown lines (strategy + benchmark)."""
    spec = {
        "data": [
            {
                "x": dates,
                "y": [v * 100 for v in dd_strategy],
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#1F77B4", "width": 2},
                "fill": "tozeroy",
                "fillcolor": "rgba(31, 119, 180, 0.15)",
                "name": "Strategy drawdown",
                "hovertemplate": "<b>%{x|%Y-%m}</b><br>%{y:.1f}%<extra></extra>",
            },
            {
                "x": dates,
                "y": [v * 100 for v in dd_benchmark],
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#C8102E", "width": 2, "dash": "dash"},
                "name": "Benchmark drawdown",
                "hovertemplate": "<b>%{x|%Y-%m}</b><br>%{y:.1f}%<extra></extra>",
            },
        ],
        "layout": {
            "title": {
                "text": "Drawdowns over time (strategy vs benchmark)",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                "x": 0.5,
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": _x_axis_block(),
            "yaxis": {
                "title": {
                    "text": "Drawdown (%)",
                    "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                },
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                "ticksuffix": "%",
                "gridcolor": "rgba(150, 150, 150, 0.2)",
                "zeroline": True,
                "zerolinecolor": "#333",
                "zerolinewidth": 1.5,
            },
            "hovermode": "x unified",
            "height": PANEL_HEIGHT,
            "margin": {"t": 60, "b": 80, "l": 75, "r": 35},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "legend": {"font": {"size": LEGEND_FONT_SIZE, "family": FONT_FAMILY}},
        },
        "config": _interactive_config(chart_name),
    }
    return _maybe_add_recessions(spec, list(dates) if dates else None, show_recessions)


def make_allocation_chart(
    dates: list[str],
    weights: list[float],
    *,
    chart_name: str = "allocation",
    show_recessions: bool = True,
) -> dict[str, Any]:
    """v10.0: stacked-area showing equity weight over time."""
    eq_pct = [(w * 100) if w is not None and w == w else None for w in weights]
    cash_pct = [
        (100 - (w * 100)) if w is not None and w == w else None for w in weights
    ]
    spec = {
        "data": [
            {
                "x": dates,
                "y": eq_pct,
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#5DBB63", "width": 0},
                "stackgroup": "one",
                "fillcolor": "rgba(93, 187, 99, 0.65)",
                "name": "Equity %",
                "hovertemplate": "<b>%{x|%Y-%m}</b><br>Equity: %{y:.0f}%<extra></extra>",
            },
            {
                "x": dates,
                "y": cash_pct,
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "#9AA0A6", "width": 0},
                "stackgroup": "one",
                "fillcolor": "rgba(154, 160, 166, 0.65)",
                "name": "T-bills %",
                "hovertemplate": "<b>%{x|%Y-%m}</b><br>T-bills: %{y:.0f}%<extra></extra>",
            },
        ],
        "layout": {
            "title": {
                "text": "Equity allocation history (0% = full T-bills, 100% = full equity)",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                "x": 0.5,
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": _x_axis_block(),
            "yaxis": {
                "title": {
                    "text": "Allocation (%)",
                    "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                },
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                "ticksuffix": "%",
                "range": [0, 100],
                "dtick": 25,
                "gridcolor": "rgba(150, 150, 150, 0.2)",
            },
            "hovermode": "x unified",
            "height": PANEL_HEIGHT,
            "margin": {"t": 60, "b": 80, "l": 75, "r": 35},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "legend": {"font": {"size": LEGEND_FONT_SIZE, "family": FONT_FAMILY}},
        },
        "config": _interactive_config(chart_name),
    }
    return _maybe_add_recessions(spec, list(dates) if dates else None, show_recessions)


# ---------------------------------------------------------------------------
# v11.0c — macro-risk-specific chart factories
# ---------------------------------------------------------------------------


def make_cross_composite_quadrant(
    mvci_z: pd.Series,
    mrc_z: pd.Series,
    quadrant_means: dict[str, float] | None = None,
    *,
    chart_name: str = "cross_composite_quadrant",
) -> dict[str, Any]:
    """2D scatter of (MVCI z, MRC z) with quadrant shading + current marker.

    The four quadrants are shaded with colours encoding historical
    forward-10Y mean returns (greener = higher returns historically), so
    the reader sees at a glance which quadrant they're currently in.

    Parameters
    ----------
    mvci_z, mrc_z : pd.Series
        Time-aligned z-score series (will be inner-joined on index).
    quadrant_means : dict | None
        Optional ``{quadrant_label: mean_forward_return}`` for hover text.
    """
    common = mvci_z.dropna().index.intersection(mrc_z.dropna().index)
    if len(common) < 24:
        return {"data": [], "layout": {"title": {"text": "Cross-composite — n/a"}}}
    df = pd.DataFrame(
        {"mvci": mvci_z.loc[common], "mrc": mrc_z.loc[common]}
    ).sort_index()
    quad_labels: list[str] = []
    for a, b in zip(df["mvci"], df["mrc"]):
        if a >= 0 and b >= 0:
            quad_labels.append("high_val_high_stress")
        elif a >= 0 and b < 0:
            quad_labels.append("high_val_low_stress")
        elif a < 0 and b >= 0:
            quad_labels.append("low_val_high_stress")
        else:
            quad_labels.append("low_val_low_stress")
    years = [pd.Timestamp(d).year for d in df.index]
    dates_str = [pd.Timestamp(d).strftime("%Y-%m") for d in df.index]
    means = quadrant_means or {}
    hover = [
        f"{ds}<br>MVCI = {a:+.2f}σ<br>MRC = {b:+.2f}σ<br>quadrant = {q}<br>"
        f"hist mean fwd-10Y = {means.get(q, float('nan'))*100:.1f}%"
        if not np.isnan(means.get(q, float("nan")))
        else f"{ds}<br>MVCI = {a:+.2f}σ<br>MRC = {b:+.2f}σ<br>quadrant = {q}"
        for ds, a, b, q in zip(dates_str, df["mvci"], df["mrc"], quad_labels)
    ]
    current = df.iloc[-1]
    current_quad = quad_labels[-1]

    # Quadrant fill colours (translucent) — light green/green/yellow/red.
    quad_shapes = [
        # low_val_low_stress (x < 0, y < 0) — light green
        {
            "type": "rect", "xref": "x", "yref": "y",
            "x0": -6, "x1": 0, "y0": -6, "y1": 0,
            "fillcolor": "rgba(93, 187, 99, 0.10)",
            "line": {"width": 0}, "layer": "below",
        },
        # low_val_high_stress (x < 0, y > 0) — green
        {
            "type": "rect", "xref": "x", "yref": "y",
            "x0": -6, "x1": 0, "y0": 0, "y1": 6,
            "fillcolor": "rgba(27, 122, 62, 0.15)",
            "line": {"width": 0}, "layer": "below",
        },
        # high_val_low_stress (x > 0, y < 0) — yellow
        {
            "type": "rect", "xref": "x", "yref": "y",
            "x0": 0, "x1": 6, "y0": -6, "y1": 0,
            "fillcolor": "rgba(232, 119, 34, 0.12)",
            "line": {"width": 0}, "layer": "below",
        },
        # high_val_high_stress (x > 0, y > 0) — red
        {
            "type": "rect", "xref": "x", "yref": "y",
            "x0": 0, "x1": 6, "y0": 0, "y1": 6,
            "fillcolor": "rgba(200, 16, 46, 0.15)",
            "line": {"width": 0}, "layer": "below",
        },
        # Zero gridlines
        {
            "type": "line", "xref": "x", "yref": "y",
            "x0": -6, "x1": 6, "y0": 0, "y1": 0,
            "line": {"color": "#333", "width": 1, "dash": "dot"},
        },
        {
            "type": "line", "xref": "x", "yref": "y",
            "x0": 0, "x1": 0, "y0": -6, "y1": 6,
            "line": {"color": "#333", "width": 1, "dash": "dot"},
        },
    ]

    return {
        "data": [
            {
                "x": [float(v) for v in df["mvci"]],
                "y": [float(v) for v in df["mrc"]],
                "type": "scatter",
                "mode": "markers",
                "marker": {
                    "size": 6,
                    "color": years,
                    "colorscale": "Turbo",
                    "showscale": True,
                    "colorbar": {
                        "title": {"text": "Year", "font": {"size": 12, "family": FONT_FAMILY}},
                        "tickfont": {"size": 11, "family": FONT_FAMILY},
                    },
                    "opacity": 0.7,
                },
                "text": hover,
                "hovertemplate": "%{text}<extra></extra>",
                "name": "Historical months",
            },
            {
                "x": [float(current["mvci"])],
                "y": [float(current["mrc"])],
                "type": "scatter",
                "mode": "markers+text",
                "marker": {
                    "size": 18,
                    "color": "#000",
                    "line": {"color": "#fff", "width": 2},
                    "symbol": "star",
                },
                "text": [f"Now: {current_quad}"],
                "textposition": "top center",
                "textfont": {"size": 13, "family": FONT_FAMILY},
                "hoverinfo": "skip",
                "showlegend": False,
            },
        ],
        "layout": {
            "title": {
                "text": (
                    "<b>Cross-composite quadrants: MVCI &times; MRC</b><br>"
                    "<span style='font-size:13px;color:#666'>"
                    "Greener quadrants = higher historical forward-10Y returns</span>"
                ),
                "x": 0.5, "xanchor": "center",
                "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": {
                "title": {"text": "MVCI z-score (valuation)",
                          "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "range": [-4, 4],
                "zeroline": False,
                "gridcolor": "rgba(150,150,150,0.15)",
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "yaxis": {
                "title": {"text": "MRC z-score (macro stress)",
                          "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "range": [-4, 4],
                "zeroline": False,
                "gridcolor": "rgba(150,150,150,0.15)",
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "shapes": quad_shapes,
            "height": HERO_HEIGHT,
            "margin": {"t": 90, "b": 70, "l": 75, "r": 90},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "hovermode": "closest",
            "showlegend": False,
        },
        "config": _interactive_config(chart_name),
    }


def make_pca_scree(
    explained_variance: list[float] | None,
    *,
    chart_name: str = "pca_scree",
) -> dict[str, Any]:
    """PCA variance-explained scree plot with cumulative line overlay."""
    if not explained_variance:
        return {"data": [], "layout": {"title": {"text": "PCA scree — n/a"}}}
    ev = [float(v) for v in explained_variance if v is not None and np.isfinite(v)]
    if not ev:
        return {"data": [], "layout": {"title": {"text": "PCA scree — n/a"}}}
    pc_labels = [f"PC{i+1}" for i in range(len(ev))]
    cumulative = np.cumsum(ev).tolist()
    return {
        "data": [
            {
                "x": pc_labels, "y": ev, "type": "bar",
                "marker": {"color": "#1F77B4"},
                "name": "Variance explained",
                "hovertemplate": "%{x}: %{y:.1%}<extra></extra>",
            },
            {
                "x": pc_labels, "y": cumulative, "type": "scatter", "mode": "lines+markers",
                "line": {"color": "#C8102E", "width": 2},
                "marker": {"size": 8, "color": "#C8102E"},
                "name": "Cumulative",
                "yaxis": "y2",
                "hovertemplate": "%{x} cumulative: %{y:.1%}<extra></extra>",
            },
        ],
        "layout": {
            "title": {
                "text": "PCA variance explained (MRC constituents)",
                "x": 0.5, "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": {
                "title": {"text": "Principal component",
                          "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "yaxis": {
                "title": {"text": "Variance explained",
                          "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickformat": ".0%",
                "range": [0, 1],
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "yaxis2": {
                "title": {"text": "Cumulative",
                          "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "overlaying": "y", "side": "right",
                "tickformat": ".0%",
                "range": [0, 1.05],
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "height": PANEL_HEIGHT,
            "margin": {"t": 50, "b": 70, "l": 70, "r": 70},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "legend": {"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
        },
        "config": _interactive_config(chart_name),
    }


def make_constituent_contributions(
    z_by_variant: dict[str, float],
    labels: dict[str, str] | None = None,
    *,
    chart_name: str = "constituent_contributions",
) -> dict[str, Any]:
    """Horizontal bar chart of each constituent's current z-score.

    Bars are sorted by |z| (descending) and coloured red if z > 0 (pushing
    composite higher = more bearish for equities) or green if z < 0.
    """
    if not z_by_variant:
        return {"data": [], "layout": {"title": {"text": "Constituents — n/a"}}}
    items = [(k, float(v)) for k, v in z_by_variant.items() if v is not None and np.isfinite(v)]
    items.sort(key=lambda kv: abs(kv[1]), reverse=True)
    keys = [k for k, _ in items]
    vals = [v for _, v in items]
    display_labels = [labels.get(k, k) if labels else k for k in keys]
    colors = ["#C8102E" if v > 0 else "#1B7A3E" for v in vals]
    return {
        "data": [
            {
                "x": vals, "y": display_labels, "type": "bar", "orientation": "h",
                "marker": {"color": colors},
                "hovertemplate": "%{y}: %{x:+.2f}σ<extra></extra>",
            }
        ],
        "layout": {
            "title": {
                "text": "Constituent z-scores (current month)",
                "x": 0.5, "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY},
            },
            "font": {"family": FONT_FAMILY},
            "xaxis": {
                "title": {"text": "Z-score (σ)",
                          "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "zeroline": True, "zerolinecolor": "#333", "zerolinewidth": 1.5,
                "range": [-4, 4],
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "yaxis": {
                "autorange": "reversed",
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "height": PANEL_HEIGHT,
            "margin": {"t": 50, "b": 60, "l": 170, "r": 30},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
        },
        "config": _interactive_config(chart_name),
    }


def make_conditional_distribution(
    bucket_returns: list[float],
    *,
    bayesian_mean: float | None = None,
    var_5: float | None = None,
    title: str = "Conditional return distribution",
    chart_name: str = "cond_dist",
) -> dict[str, Any]:
    """Histogram of forward returns observed in the current z-bucket, with
    optional Bayesian posterior mean + VaR(5%) annotations."""
    if not bucket_returns:
        return {"data": [], "layout": {"title": {"text": f"{title} — n/a"}}}
    arr = np.array(bucket_returns, dtype="float64")
    arr = arr[~np.isnan(arr)]
    if len(arr) < 5:
        return {"data": [], "layout": {"title": {"text": f"{title} — n<5"}}}
    annotations: list[dict[str, Any]] = []
    shapes: list[dict[str, Any]] = []
    if bayesian_mean is not None and np.isfinite(bayesian_mean):
        shapes.append({
            "type": "line", "xref": "x", "yref": "paper",
            "x0": bayesian_mean * 100, "x1": bayesian_mean * 100, "y0": 0, "y1": 1,
            "line": {"color": "#1F77B4", "width": 2, "dash": "dash"},
        })
        annotations.append({
            "x": bayesian_mean * 100, "y": 0.95, "xref": "x", "yref": "paper",
            "showarrow": True, "arrowhead": 2,
            "text": f"Bayesian mean = {bayesian_mean*100:+.1f}%",
            "font": {"size": 12, "color": "#1F77B4", "family": FONT_FAMILY},
        })
    if var_5 is not None and np.isfinite(var_5):
        shapes.append({
            "type": "line", "xref": "x", "yref": "paper",
            "x0": var_5 * 100, "x1": var_5 * 100, "y0": 0, "y1": 1,
            "line": {"color": "#C8102E", "width": 2, "dash": "dot"},
        })
        annotations.append({
            "x": var_5 * 100, "y": 0.85, "xref": "x", "yref": "paper",
            "showarrow": True, "arrowhead": 2,
            "text": f"VaR(5%) = {var_5*100:+.1f}%",
            "font": {"size": 12, "color": "#C8102E", "family": FONT_FAMILY},
        })
    return {
        "data": [
            {
                "x": (arr * 100).tolist(),
                "type": "histogram",
                "marker": {"color": "#1F77B4", "opacity": 0.7},
                "nbinsx": 25,
                "name": "Empirical",
                "hovertemplate": "%{x:.1f}%: n=%{y}<extra></extra>",
            }
        ],
        "layout": {
            "title": {"text": title, "x": 0.5,
                      "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
            "font": {"family": FONT_FAMILY},
            "xaxis": {
                "title": {"text": "Forward annualised return (%)",
                          "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickformat": ".0f", "ticksuffix": "%",
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "yaxis": {
                "title": {"text": "Observations",
                          "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
            },
            "shapes": shapes,
            "annotations": annotations,
            "height": PANEL_HEIGHT,
            "margin": {"t": 60, "b": 70, "l": 70, "r": 30},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
        },
        "config": _interactive_config(chart_name),
    }


def make_dual_z_overlay(
    z1: pd.Series,
    z2: pd.Series,
    *,
    name1: str = "MVCI",
    name2: str = "MRC",
    title: str = "MVCI and MRC over time",
    chart_name: str = "dual_z_overlay",
    show_recessions: bool = True,
) -> dict[str, Any]:
    """Compact two-line time-series chart (used for Overview Macro Risk Snapshot)."""
    z1c = z1.dropna()
    z2c = z2.dropna()
    common = z1c.index.union(z2c.index).sort_values()
    if len(common) < 24:
        return {"data": [], "layout": {"title": {"text": f"{title} — n/a"}}}
    dates_str = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in common]
    spec = {
        "data": [
            {
                "x": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in z1c.index],
                "y": [float(v) for v in z1c.values],
                "type": "scatter", "mode": "lines",
                "line": {"color": "#1F77B4", "width": 2},
                "name": name1,
                "hovertemplate": f"{name1}: %{{y:+.2f}}σ<extra></extra>",
            },
            {
                "x": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in z2c.index],
                "y": [float(v) for v in z2c.values],
                "type": "scatter", "mode": "lines",
                "line": {"color": "#7E57C2", "width": 2},
                "name": name2,
                "hovertemplate": f"{name2}: %{{y:+.2f}}σ<extra></extra>",
            },
        ],
        "layout": {
            "title": {"text": title, "x": 0.5,
                      "font": {"size": CHART_TITLE_FONT_SIZE, "family": FONT_FAMILY}},
            "font": {"family": FONT_FAMILY},
            "xaxis": _x_axis_block(with_rangeslider=False),
            "yaxis": _z_axis_block(),
            "height": PANEL_HEIGHT,
            "margin": {"t": 50, "b": 60, "l": 70, "r": 30},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "legend": {"orientation": "h", "y": -0.18, "x": 0.5, "xanchor": "center"},
            "hovermode": "x unified",
        },
        "config": _interactive_config(chart_name),
    }
    return _maybe_add_recessions(spec, dates_str, show_recessions)


__all__ = [
    "FONT_FAMILY",
    "TICK_FONT_SIZE",
    "AXIS_TITLE_FONT_SIZE",
    "CHART_TITLE_FONT_SIZE",
    "LEGEND_FONT_SIZE",
    "HERO_HEIGHT",
    "PANEL_HEIGHT",
    "ZSCORE_Y_RANGE",
    "make_regime_band_shapes",
    "make_panel_a",
    "make_panel_b",
    "make_panel_c",
    "make_sparkline",
    "make_pca_loadings_bar",
    "make_hero_chart",
    "make_mean_reversion_hero",
    "make_correlation_heatmap",
    "make_oos_r2_chart",
    "make_acf_pacf_charts",
    "make_calibration_plot",
    "make_equity_curve_chart",
    "make_drawdown_chart",
    "make_allocation_chart",
]
