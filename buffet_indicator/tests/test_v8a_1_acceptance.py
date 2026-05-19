"""Acceptance tests for Spec v8a.1 (critical visual patch).

Run via:
    set ACCEPTANCE=1
    python -m pytest tests/test_v8a_1_acceptance.py -v --no-cov
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
def test_v8a1_mean_reversion_in_headline() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.models.orchestrator_modeling import run_modeling

    r = run_modeling(bootstrap_n=500, n_bootstrap_prob=500)
    h = r["headline"]
    assert "mean_reversion" in h["variants"]
    mr = h["variants"]["mean_reversion"]
    assert mr["headline_label"].startswith("Mean Reversion")
    assert mr["headline_value"] > 0
    # MR should be Overvalued or Strongly Overvalued in May 2026.
    assert mr["long_run"]["z_score"] > 1.0


@pytest.mark.acceptance
def test_v8a1_mvci_uses_seven_constituents() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.models.orchestrator_modeling import run_modeling

    r = run_modeling(bootstrap_n=500, n_bootstrap_prob=500)
    cv = r["headline"]["cross_variant_long_run"]
    assert cv["n_variants"] == 7


@pytest.mark.acceptance
def test_v8a1_dashboard_has_hero_charts_and_sparklines() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    p = Path("outputs/dashboard.html")
    assert p.exists()
    html = p.read_text(encoding="utf-8")

    # 5 tabs each have a hero chart container.
    for hero_id in (
        "hero-chart-overview",
        "hero-chart-mvci",
        "hero-chart-buffett",
        "hero-chart-cape",
        "hero-chart-mean-reversion",
    ):
        assert f'id="{hero_id}"' in html, f"Missing hero container: {hero_id}"

    # Mean Reversion tab partial is mounted.
    assert 'data-tab="mean_reversion"' in html

    # Sparkline divs render for the non-coming-soon Overview cards
    # (6 cards: 3 BI + CAPE + MR + MVCI). Q-Ratio and EY-Deficit deferred to v8b.
    sparkline_ids = set(re.findall(r'id="sparkline-([a-z_]+)"', html))
    assert sparkline_ids >= {
        "mvci",
        "bi_allequity_pct",
        "bi_wilshire_pct",
        "bi_spx_proxy",
        "cape",
        "mean_reversion",
    }

    # CSS rule for sparkline height present (not Jinja-escaped).
    assert '[id^="sparkline-"]' in html
    assert ".hero-chart-container" in html

    # Embedded JSON payload has hero_specs for all 5 tabs.
    m = re.search(
        r'<script id="dashboard-data" type="application/json">(.+?)</script>',
        html,
        re.DOTALL,
    )
    data = json.loads(m.group(1))
    hero_specs = data.get("hero_specs", {})
    assert set(hero_specs.keys()) >= {
        "overview",
        "mvci",
        "buffett",
        "cape",
        "mean_reversion",
    }
    # MR hero has the deviation annotation.
    mr_hero = hero_specs["mean_reversion"]
    assert mr_hero is not None
    annot_text = mr_hero["layout"]["annotations"][0]["text"]
    assert "long-run trend" in annot_text
