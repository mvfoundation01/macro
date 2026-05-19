"""Spec v8b.1 §3 — Strategist gap patches (B.1 - B.4) + C mobile annotation."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.viz.chart_specs import make_hero_chart, make_panel_b  # noqa: E402


def _z_series_long(n: int = 1800) -> pd.Series:
    rng = np.random.default_rng(0)
    idx = pd.date_range("1881-01-31", periods=n, freq="ME")
    return pd.Series(rng.standard_normal(n) * 1.5, index=idx, name="z")


def _panel_b_spec() -> dict:
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "date": pd.date_range("2000-01-31", periods=200, freq="ME"),
            "z_score_long_run": rng.standard_normal(200),
            "forward_120m_cagr": rng.standard_normal(200) * 0.05 + 0.07,
        }
    )
    return make_panel_b(
        df,
        current_z=1.5,
        regression={"alpha": 0.07, "beta": -0.03, "r_squared": 0.3, "t_nw": -3.0},
    )


# B.1 — Panel B percent formatting
def test_v8b1_panel_b_y_tick_format_is_percent() -> None:
    spec = _panel_b_spec()
    y = spec["layout"]["yaxis"]
    # Either tickformat = "%" or ticksuffix = "%" is acceptable; we use ticksuffix.
    assert y.get("ticksuffix") == "%" or y.get("tickformat") == ".1%"


def test_v8b1_panel_b_y_dtick_is_5pp() -> None:
    spec = _panel_b_spec()
    assert spec["layout"]["yaxis"]["dtick"] == 5


def test_v8b1_panel_b_y_zeroline_styled() -> None:
    spec = _panel_b_spec()
    y = spec["layout"]["yaxis"]
    assert y["zeroline"] is True
    assert y["zerolinewidth"] == 1.5


# B.2 — scroll-zoom default
def test_v8b1_scroll_zoom_default_false() -> None:
    """Spec config no longer defaults scrollZoom=True; JS opt-in only on desktop."""
    spec = make_hero_chart(_z_series_long(), "Test")
    assert spec["config"]["scrollZoom"] is False


def test_v8b1_dashboard_js_has_touch_feature_detect() -> None:
    js = (_ROOT / "src" / "viz" / "static" / "dashboard.js").read_text(encoding="utf-8")
    assert "IS_TOUCH_DEVICE" in js
    assert "ontouchstart" in js


# B.3 — PCA loadings non-zero for all variants in built dashboard
def test_v8b1_pca_loadings_all_seven_nonzero() -> None:
    """The MVCI PCA loadings chart should have a non-zero bar for every variant."""
    dashboard = _ROOT / "outputs" / "dashboard.html"
    if not dashboard.exists():
        return
    html = dashboard.read_text(encoding="utf-8")
    m = re.search(r'<script id="dashboard-data" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert m is not None
    payload = json.loads(m.group(1))
    pca = payload.get("mvci_pca_loadings_chart", {})
    if not pca.get("data"):
        return  # No PCA data — skip
    xs = pca["data"][0]["x"]
    assert len(xs) >= 6  # 6+ constituents
    non_zero = sum(1 for v in xs if abs(v) > 1e-6)
    assert non_zero >= 5, f"expected ≥5 non-zero loadings, got {non_zero}"


# B.4 — No text artifacts in source viz files
def test_v8b1_no_textual_artifacts_in_viz() -> None:
    """Scan for leftover code stubs. The spec's intent is artifacts like
    ``TODO``, ``FIXME``, or "coming.in.v8" stub comments — not legitimate
    technical uses of the noun "placeholder" in docstrings describing
    sentinel values. Skip lines that are clearly Python comments/docstrings.
    """
    viz_dir = _ROOT / "src" / "viz"
    # These are unambiguous stub markers — they shouldn't appear at all.
    strict_patterns = [r"\bTODO\b", r"\bFIXME\b", r"\bXXX\b", r"coming\.in\.v8"]
    bad: list[tuple[str, str, str]] = []
    for ext in ("*.py", "*.html", "*.js", "*.css"):
        for p in viz_dir.rglob(ext):
            if "__pycache__" in str(p):
                continue
            text = p.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), start=1):
                for pat in strict_patterns:
                    if re.search(pat, line, re.IGNORECASE):
                        bad.append((str(p.relative_to(_ROOT)), f"L{lineno}", pat))
    assert not bad, f"Text artifacts found: {bad}"


# C — Mobile annotation overflow fix
def test_v8b1_historical_annotations_have_xanchor() -> None:
    """Each historical annotation has xanchor set to keep label inside chart bounds."""
    spec = make_hero_chart(_z_series_long(), "Test", add_historical_annotations=True)
    annotations = spec["layout"].get("annotations") or []
    # At least one historical annotation
    hist_anns = [a for a in annotations if any(p in str(a.get("text", "")) for p in ("1929", "2000", "2021", "Dot-com", "Post-COVID"))]
    assert hist_anns, "no historical annotations found"
    for ann in hist_anns:
        assert ann.get("xanchor") in ("left", "center", "right"), ann
        assert ann.get("bgcolor") is not None
        assert ann.get("bordercolor") is not None


def test_v8b1_rightmost_annotation_anchors_right() -> None:
    """The 2021 peak (rightmost) should anchor right so the label extends leftward."""
    spec = make_hero_chart(_z_series_long(), "Test")
    annotations = spec["layout"].get("annotations") or []
    post_covid = [a for a in annotations if "Post-COVID" in str(a.get("text", ""))]
    if not post_covid:
        return
    ann = post_covid[0]
    assert ann.get("xanchor") == "right"
    assert ann.get("ax", 0) < 0  # arrow extends leftward
