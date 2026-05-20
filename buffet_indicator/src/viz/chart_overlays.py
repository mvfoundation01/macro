"""Reusable Plotly chart-layout overlays (v11.0).

Currently provides :func:`add_recession_bands` which mutates a Plotly figure's
``layout`` dict to add NBER recession bands behind the trace. The intent is
to apply this on every time-series chart EXCEPT scatter plots (Panel B),
heatmaps, bar charts, ACF/PACF stems, and calibration plots.

The overlay reads from ``data/master/nber_recessions.parquet`` via
:func:`src.ingest.nber_recessions.load_nber_recessions`, which is itself
memoized -- so calling :func:`add_recession_bands` many times in a single
dashboard build does not re-read the parquet.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.ingest.nber_recessions import load_nber_recessions

# Tailwind gray-400 @ 25% opacity. Visible enough to read against white
# background, soft enough not to compete with the foreground trace.
RECESSION_BAND_COLOR = "rgba(156, 163, 175, 0.25)"


def _ensure_layout_dict(layout: Any) -> dict[str, Any]:
    if layout is None:
        return {}
    # Plotly Figure / go.Layout have .to_plotly_json() but inputs in this
    # codebase are plain dicts -- enforce.
    if not isinstance(layout, dict):
        raise TypeError(
            f"add_recession_bands expects a dict-typed layout, got {type(layout).__name__}"
        )
    return layout


def _filter_to_range(
    df: pd.DataFrame,
    x_range: tuple[pd.Timestamp, pd.Timestamp] | None,
) -> pd.DataFrame:
    if x_range is None:
        return df
    lo, hi = pd.Timestamp(x_range[0]), pd.Timestamp(x_range[1])
    if lo > hi:
        lo, hi = hi, lo
    mask = (df["end_date"] >= lo) & (df["start_date"] <= hi)
    return df.loc[mask].copy()


def add_recession_bands(
    layout: dict[str, Any],
    x_range: tuple[pd.Timestamp, pd.Timestamp] | None = None,
    *,
    color: str = RECESSION_BAND_COLOR,
    layer: str = "below",
) -> dict[str, Any]:
    """Add NBER recession bands to a Plotly layout.

    Parameters
    ----------
    layout : dict
        The Plotly layout dict (e.g., ``spec["layout"]``). Mutated in place
        AND returned for chained-style use.
    x_range : (pd.Timestamp, pd.Timestamp) | None
        If provided, only bands whose ``[start_date, end_date]`` intersects
        ``x_range`` are added. Useful for charts that show post-1945 data
        only (avoids cluttering the layout with 19th-century rects no one
        will see).
    color : str
        Plotly-style RGBA string. Default tailwind gray-400 @ 25%.
    layer : str
        ``"below"`` (default) so trace lines remain visible; ``"above"`` for
        emphasis is technically supported but rarely useful.

    Returns
    -------
    dict
        The mutated layout (same object as the ``layout`` argument).
    """
    layout = _ensure_layout_dict(layout)
    df = load_nber_recessions()
    df = _filter_to_range(df, x_range)

    shapes = list(layout.get("shapes") or [])
    for _, row in df.iterrows():
        shapes.append(
            {
                "type": "rect",
                "xref": "x",
                "yref": "paper",
                "x0": row["start_date"].strftime("%Y-%m-%d"),
                "x1": row["end_date"].strftime("%Y-%m-%d"),
                "y0": 0,
                "y1": 1,
                "fillcolor": color,
                "line": {"width": 0},
                "layer": layer,
                # Tag so downstream tests / chart code can find or remove only
                # the recession rects without disturbing regime bands etc.
                "name": "nber_recession",
            }
        )
    layout["shapes"] = shapes
    return layout


__all__ = ["add_recession_bands", "RECESSION_BAND_COLOR"]
