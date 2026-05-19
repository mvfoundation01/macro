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
    """v8b interactive config: visible toolbar, drag-zoom, scroll-zoom, PNG export."""
    return {
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "scrollZoom": True,
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
    """Append labeled arrows at 1929, 2000, 2021 peak dates when in series range."""
    if z_series is None or z_series.empty:
        return annotations
    peaks = [
        ("1929-09-30", "1929 peak<br>(crash followed)"),
        ("2000-03-31", "Dot-com peak<br>(-50% over 2y)"),
        ("2021-12-31", "Post-COVID peak<br>(-25% in 2022)"),
    ]
    idx_min, idx_max = z_series.index.min(), z_series.index.max()
    for date_str, label in peaks:
        date = pd.Timestamp(date_str)
        if idx_min <= date <= idx_max:
            idx = z_series.index.get_indexer([date], method="nearest")[0]
            actual_date = z_series.index[idx]
            actual_z = float(z_series.iloc[idx])
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
                    "ax": 0,
                    "ay": -40,
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
) -> dict[str, Any]:
    """Build a Plotly figure dict for Panel A (z-score time series)."""
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

    return {
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
                    "text": "Subsequent 10Y CAGR (%)",
                    "font": {"size": AXIS_TITLE_FONT_SIZE, "family": FONT_FAMILY},
                },
                "tickfont": {"size": TICK_FONT_SIZE, "family": FONT_FAMILY, "color": "#333"},
                "ticksuffix": "%",
                "showspikes": True,
                "spikecolor": "#666",
                "spikethickness": 1,
                "spikedash": "dot",
                "zeroline": True,
                "zerolinecolor": "#999",
                "gridcolor": "rgba(150, 150, 150, 0.2)",
                "nticks": 8,
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


def make_panel_c(sp500_df: pd.DataFrame, *, chart_name: str = "panel_c") -> dict[str, Any]:
    """S&P 500 (log scale) colored by MVCI regime."""
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

    return {
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

    return {
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

    return {
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


def make_oos_r2_chart(dates: list[str], r2_values: list[float], *, chart_name: str = "oos_r2") -> dict[str, Any]:
    """OOS R² (Goyal-Welch) evolution line chart."""
    return {
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
]
