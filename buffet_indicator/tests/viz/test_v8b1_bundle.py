"""Spec v8b.1 §5 — Bundle-size optimization tests (D.1 - D.4)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _dashboard_html() -> str | None:
    p = _ROOT / "outputs" / "dashboard.html"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


def test_v8b1_dashboard_html_size_below_target() -> None:
    """Bundle ceiling.

    v8b.1 set this at 8 MB; v11.0 master spec relaxed it to 10 MB after
    adding the macro module (7 indicators + MRC composite + all dual-frame
    chart specs). The current bundle should remain under that ceiling.
    """
    p = _ROOT / "outputs" / "dashboard.html"
    if not p.exists():
        return
    size_mb = p.stat().st_size / 1e6
    assert size_mb < 10.0, (
        f"dashboard.html size {size_mb:.2f} MB exceeds 10 MB ceiling"
    )


def test_v8b1_shared_panel_c_sentinel_present() -> None:
    """Per-variant panel_c is sentinel-replaced to share one inline spec."""
    html = _dashboard_html()
    if html is None:
        return
    assert "__SHARED_PANEL_C__" in html


def test_v8b1_shared_panel_c_real_spec_present() -> None:
    """The shared_panel_c key carries the actual chart spec."""
    html = _dashboard_html()
    if html is None:
        return
    m = re.search(r'<script id="dashboard-data" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert m is not None
    payload = json.loads(m.group(1))
    pc = payload.get("shared_panel_c")
    assert pc is not None
    assert "data" in pc


def test_v8b1_hero_overview_sentinel() -> None:
    """Overview hero is sentinel-referenced to the mvci hero."""
    html = _dashboard_html()
    if html is None:
        return
    m = re.search(r'<script id="dashboard-data" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert m is not None
    payload = json.loads(m.group(1))
    heros = payload.get("hero_specs", {})
    assert heros.get("overview") == "__HERO_MVCI__"
    assert isinstance(heros.get("mvci"), dict)


def test_v8b1_scatter_csv_removed_from_inline_exports() -> None:
    """scatter_data CSV should be rebuilt on-demand; not in inline csv_exports."""
    html = _dashboard_html()
    if html is None:
        return
    m = re.search(r'<script id="dashboard-data" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert m is not None
    payload = json.loads(m.group(1))
    csv_exports = payload.get("csv_exports", {})
    assert "scatter_data" not in csv_exports


def test_v8b1_rebuild_scatter_csv_present_in_js() -> None:
    """dashboard.js has the on-demand scatter CSV rebuilder."""
    js = (_ROOT / "src" / "viz" / "static" / "dashboard.js").read_text(encoding="utf-8")
    assert "rebuildScatterCSV" in js
    assert "panel_b" in js


def test_v8b1_headline_json_slimmed() -> None:
    """The Data tab JSON viewer payload has series fields stripped."""
    html = _dashboard_html()
    if html is None:
        return
    m = re.search(r'<script id="dashboard-data" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert m is not None
    payload = json.loads(m.group(1))
    jstr = payload.get("headline_json_str", "")
    # The strip-placeholder should appear at least once if series fields existed
    if jstr:
        assert "series omitted" in jstr or len(jstr) < 1_500_000
