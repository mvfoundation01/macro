"""v11.1 Stage F — 4 layout-collision-fix acceptance tests."""
from __future__ import annotations

from pathlib import Path

import pytest


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"


def _read_dashboard() -> str:
    if not DASHBOARD_HTML.exists():
        pytest.skip(f"Dashboard not built: {DASHBOARD_HTML}")
    return DASHBOARD_HTML.read_text(encoding="utf-8")


def test_l1_post_covid_annotation_removed():
    """L1: 'Post-COVID peak' annotation is no longer baked into chart specs.

    Verified at the source level (chart_specs.py) because the rendered HTML
    only includes the annotation text inside Plotly JSON if the annotation
    is emitted by the spec builder.
    """
    src = (Path(__file__).resolve().parents[2] / "src" / "viz" / "chart_specs.py").read_text(
        encoding="utf-8"
    )
    # The "Post-COVID peak" string must NOT appear in the peaks list anymore.
    # It may still appear in the v11.1 fix-comment for documentation, but not
    # as an active annotation entry.
    lines_with_active_annotation = [
        ln for ln in src.split("\n")
        if "Post-COVID peak" in ln and not ln.strip().startswith("#")
    ]
    assert not lines_with_active_annotation, (
        f"Active 'Post-COVID peak' annotation still present: {lines_with_active_annotation}"
    )


def test_l1_2021_peak_date_removed_from_peaks_list():
    """L1 deeper: the 2021-12-31 entry is no longer in the peaks list."""
    src = (Path(__file__).resolve().parents[2] / "src" / "viz" / "chart_specs.py").read_text(
        encoding="utf-8"
    )
    # Find the peaks = [...] block in _add_historical_annotations and verify
    # only 1929 + 2000 remain.
    import re
    m = re.search(r'peaks\s*=\s*\[(.+?)\]', src, re.DOTALL)
    assert m is not None, "peaks = [...] list not found"
    peaks_block = m.group(1)
    assert "2021-12-31" not in peaks_block, "2021-12-31 peak should be removed (L1)"
    assert "1929-09-30" in peaks_block, "1929 peak should remain"
    assert "2000-03-31" in peaks_block, "2000 peak should remain"


def test_l2_bayesian_mean_uses_paper_xref():
    """L2: Bayesian-mean annotation no longer overlaps the chart title.

    Verified at the source level: the annotation now uses xref/yref='paper'
    so it sits in plot-area coordinates, not in title coordinates.
    """
    src = (Path(__file__).resolve().parents[2] / "src" / "viz" / "chart_specs.py").read_text(
        encoding="utf-8"
    )
    # The Bayesian-mean annotation block spans multiple lines including nested
    # braces (for "font": {...}), so we look for a region near the "Bayesian mean"
    # text and check that xref/yref are "paper" within a ±400-char window.
    idx = src.find('f"Bayesian mean = {bayesian_mean*100')
    assert idx >= 0, "Bayesian-mean f-string literal not found"
    # Take a window before and after to capture the whole annotation dict
    window = src[max(0, idx - 800):idx + 200]
    assert '"xref": "paper"' in window, (
        "Bayesian mean annotation should use xref='paper' near its block"
    )
    assert '"yref": "paper"' in window, (
        "Bayesian mean annotation should use yref='paper' near its block"
    )


def test_l3_panel_b_annotation_moved_to_bottom_left():
    """L3: Panel B regression-stats annotation is now in lower half (y < 0.5)."""
    src = (Path(__file__).resolve().parents[2] / "src" / "viz" / "chart_specs.py").read_text(
        encoding="utf-8"
    )
    # Find the annotation in make_panel_b that contains "R²"
    import re
    # Match the annotations block with R²/beta/t_NW text
    annotation_matches = re.findall(
        r'"y":\s*([\d.]+)[^}]*?"text":\s*\(\s*\n?\s*f"R²[^"]+\s*f"[^"]+t_NW[^"]+',
        src,
        re.DOTALL,
    )
    if not annotation_matches:
        # Try simpler match: y near the regression text block
        m2 = re.search(
            r'"x":\s*0\.02,\s*\n?\s*"y":\s*([\d.]+)[\s\S]*?R²',
            src,
        )
        assert m2 is not None, "Could not find Panel B regression annotation"
        y = float(m2.group(1))
    else:
        y = float(annotation_matches[0])
    assert y < 0.5, f"Panel B regression annotation y={y} should be < 0.5 (bottom half)"


def test_l4_nan_t_stat_renders_as_na_not_nan():
    """L4: NaN t-stat now renders as 'n/a' rather than '+nan'."""
    src = (Path(__file__).resolve().parents[2] / "src" / "viz" / "chart_specs.py").read_text(
        encoding="utf-8"
    )
    # The new code must contain conditional formatting that produces 't_NW = n/a'
    assert 't_NW = n/a' in src, "Conditional 't_NW = n/a' string missing — L4 fix not present"


def test_dashboard_html_no_plus_nan_in_rendered_panels():
    """L4 secondary: rendered dashboard HTML should not contain '+nan' (or 'nan')
    as a literal t-stat display."""
    html = _read_dashboard()
    # Anywhere "t_NW =" appears followed by literal nan would be a bug.
    import re
    bad = re.findall(r't_NW\s*=\s*\+?nan', html, re.IGNORECASE)
    assert not bad, f"Found rendered '+nan' t-stat in HTML: {bad[:3]}"
