"""Acceptance tests for Spec v8a (dashboard MVP).

Run via:
    set ACCEPTANCE=1
    python -m pytest tests/test_v8a_acceptance.py -v --no-cov
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _acceptance_enabled() -> bool:
    return os.environ.get("ACCEPTANCE") == "1"


@pytest.mark.acceptance
def test_v8a_dashboard_html_exists_and_valid() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.viz.build_dashboard import build_dashboard

    build_dashboard()
    p = Path("outputs/dashboard.html")
    assert p.exists()
    size = p.stat().st_size
    # v8b widened the ceiling from 10 MB to 15 MB to accommodate the new tabs
    # (Q-Ratio, EY-Deficit, Diagnostics, Data, Methodology), per-chart
    # interpretation blocks (32 instances), and inline CSV exports for client-
    # side downloads on the Data tab (spec v8b §7).
    assert 100_000 < size < 15_000_000, (
        f"dashboard.html size {size} bytes outside expected [100KB, 15MB]"
    )
    html = p.read_text(encoding="utf-8")
    assert 'data-tab="mvci"' in html
    assert 'data-tab="overview"' in html
    assert "MV Composite Index" in html


@pytest.mark.acceptance
def test_v8a_dashboard_uses_correct_regime_colors() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    p = Path("outputs/dashboard.html")
    assert p.exists(), "Run build_dashboard first"
    html = p.read_text(encoding="utf-8")
    for hex_code in ("#C8102E", "#E87722", "#9AA0A6", "#5DBB63", "#1B7A3E"):
        assert hex_code in html, f"Required color {hex_code} missing"


@pytest.mark.acceptance
def test_v8a_dashboard_embeds_headline_values() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    p = Path("outputs/dashboard.html")
    assert p.exists()
    html = p.read_text(encoding="utf-8")
    m = re.search(
        r'<script id="dashboard-data" type="application/json">(.+?)</script>',
        html,
        re.DOTALL,
    )
    assert m is not None
    data = json.loads(m.group(1))
    assert "variants" in data
    assert "mvci" in data["variants"]
    mvci_z = data["variants"]["mvci"]["long_run"]["z_score"]
    assert isinstance(mvci_z, (int, float))
    assert -5 < mvci_z < 5


@pytest.mark.acceptance
def test_v8a_chart_data_files_exist() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    for fname in (
        "z_history.parquet",
        "value_history.parquet",
        "sp500_with_regime.parquet",
        "scatter_data.parquet",
    ):
        path = Path("outputs/charts") / fname
        assert path.exists(), f"Missing {path}"
