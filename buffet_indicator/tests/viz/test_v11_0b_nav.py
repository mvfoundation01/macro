"""v11.0b nav-restructure tests."""
from __future__ import annotations

from pathlib import Path


HEADER_PATH = Path("src/viz/templates/_header.html")
EXPECTED_TABS = (
    # overview
    "overview",
    # valuation (7)
    "mvci", "buffett", "cape", "crestmont", "qratio", "ey_deficit", "mean_reversion",
    # macro_risk (8)
    "mrc", "yc_10y3m", "yc_10y2y", "cs_hy_master", "cs_ig_master",
    "cs_hy_bb", "cs_hy_ccc", "margin_debt_growth",
    # analysis (2)
    "diagnostics", "backtest",
    # reference (2)
    "data", "methodology",
)


def test_nav_contains_all_expected_tabs() -> None:
    text = HEADER_PATH.read_text(encoding="utf-8")
    for tab_key in EXPECTED_TABS:
        assert f'data-tab="{tab_key}"' in text, f"nav missing tab {tab_key}"


def test_nav_has_four_collapsible_groups() -> None:
    text = HEADER_PATH.read_text(encoding="utf-8")
    for group in ("valuation", "macro_risk", "analysis", "reference"):
        assert f'data-group="{group}"' in text, f"nav missing group {group}"
        assert f'data-group-toggle="{group}"' in text


def test_nav_url_hash_router_present() -> None:
    text = HEADER_PATH.read_text(encoding="utf-8")
    assert "parseHash" in text
    assert "writeHash" in text
    # v11.0b: the activator function was renamed to activateFromHash when the
    # routing was refactored to dispatch into the existing showTab() handler.
    assert "activateFromHash" in text or "activateTabFromHash" in text
    assert 'hashchange' in text


def test_nav_macro_risk_group_has_eight_children() -> None:
    text = HEADER_PATH.read_text(encoding="utf-8")
    # Count occurrences of data-tab-group="macro_risk" in tab-button context.
    needles = [
        'data-tab="mrc" data-tab-group="macro_risk"',
        'data-tab="yc_10y3m" data-tab-group="macro_risk"',
        'data-tab="yc_10y2y" data-tab-group="macro_risk"',
        'data-tab="cs_hy_master" data-tab-group="macro_risk"',
        'data-tab="cs_ig_master" data-tab-group="macro_risk"',
        'data-tab="cs_hy_bb" data-tab-group="macro_risk"',
        'data-tab="cs_hy_ccc" data-tab-group="macro_risk"',
        'data-tab="margin_debt_growth" data-tab-group="macro_risk"',
    ]
    for needle in needles:
        assert needle in text, f"missing nav entry: {needle}"


def test_nav_total_tab_count_matches_expected() -> None:
    text = HEADER_PATH.read_text(encoding="utf-8")
    # Each "data-tab=" occurrence corresponds to a navigable tab. The header
    # is allowed to add additional buttons (dark-toggle has its own id) so we
    # accept >= len(EXPECTED_TABS).
    count = text.count('data-tab="')
    assert count >= len(EXPECTED_TABS)
