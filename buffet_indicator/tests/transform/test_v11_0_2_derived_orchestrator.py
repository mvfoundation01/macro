"""v11.0.2 — verify orchestrator output for the 6 derived spreads.

After Stage A, each derived spread has a dual_frame_summary.parquet with
β, t_HH, R², conviction, confidence populated at all 7 horizons.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


DERIVED_KEYS = (
    "spread_hy_ig",
    "spread_ccc_bb",
    "spread_hy_reach_for_yield",
    "spread_hy_treasury_traditional",
    "spread_equity_credit_rp",
    "spread_hy_oas_3m_delta",
)


# ---------------------------------------------------------------------------
# Stage A.6 — orchestrator parquets exist for all 6 derived spreads
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_dual_frame_summary_exists(key: str) -> None:
    p = Path(f"outputs/indicators/{key}/dual_frame_summary.parquet")
    assert p.exists(), f"missing {p}"


@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_dual_frame_long_run_horizons_present(key: str) -> None:
    df = pd.read_parquet(f"outputs/indicators/{key}/dual_frame_summary.parquet")
    lr = df[df["frame"] == "long_run"]
    horizons = set(lr["horizon_months"].dropna().astype(int).tolist())
    # 1Y, 3Y, 5Y, 10Y at minimum (v11.0b primary set).
    assert {12, 36, 60, 120}.issubset(horizons), f"{key}: horizons = {horizons}"


@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_dual_frame_beta_finite(key: str) -> None:
    df = pd.read_parquet(f"outputs/indicators/{key}/dual_frame_summary.parquet")
    lr = df[df["frame"] == "long_run"]
    # At least one horizon row has finite β.
    finite = lr["beta_hat"].dropna().apply(np.isfinite)
    assert finite.any(), f"{key}: all β NaN"


@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_dual_frame_conviction_in_range(key: str) -> None:
    df = pd.read_parquet(f"outputs/indicators/{key}/dual_frame_summary.parquet")
    lr = df[df["frame"] == "long_run"]
    h120 = lr[lr["horizon_months"] == 120]
    assert not h120.empty
    conv = float(h120.iloc[0]["conviction"])
    assert 0.0 <= conv <= 5.0, f"{key}: conviction={conv}"


@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_dual_frame_confidence_in_range(key: str) -> None:
    df = pd.read_parquet(f"outputs/indicators/{key}/dual_frame_summary.parquet")
    lr = df[df["frame"] == "long_run"]
    # confidence_pct is replicated across horizon rows (same value).
    conf = float(lr.iloc[0]["confidence_pct"])
    assert 0.0 <= conf <= 100.0, f"{key}: confidence={conf}"


@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_n_observations_at_least_300(key: str) -> None:
    df = pd.read_parquet(f"outputs/indicators/{key}/dual_frame_summary.parquet")
    lr = df[df["frame"] == "long_run"]
    n_obs = int(lr.iloc[0]["n_observations"])
    # Macro stub for derived spreads = ~340-354.
    assert n_obs >= 300, f"{key}: n_obs={n_obs}"


# ---------------------------------------------------------------------------
# Dashboard surfaces real numbers (not "n/a") on the 6 derived tabs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_dashboard_shows_numeric_conviction(key: str) -> None:
    """The derived tab's indicator tile must show Conviction X.X / 5 (not n/a)."""
    import re
    text = Path("outputs/dashboard.html").read_text(encoding="utf-8")
    section_start = text.find(f'<section data-tab="{key}"')
    section_end = text.find("</section>", section_start)
    section = text[section_start:section_end]
    # Strip non-ascii for safety; we only need the numeric pattern.
    safe = section.encode("ascii", "replace").decode("ascii")
    # Find "X.X / 5" pattern under v.conviction_fmt — should appear at least once.
    matches = re.findall(r"(\d+\.\d+)\s*/\s*5", safe)
    assert matches, f"{key}: no Conviction X.X / 5 in section"


@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_dashboard_shows_numeric_confidence(key: str) -> None:
    """The derived tab's indicator tile must show Confidence as XX% (not n/a)."""
    import re
    text = Path("outputs/dashboard.html").read_text(encoding="utf-8")
    section_start = text.find(f'<section data-tab="{key}"')
    section_end = text.find("</section>", section_start)
    section = text[section_start:section_end]
    # Look for a percent in [0, 100] (rough — any \d+% will do)
    safe = section.encode("ascii", "replace").decode("ascii")
    pct = re.findall(r">(\d+(?:\.\d+)?)%<", safe)
    assert len(pct) >= 2, f"{key}: only {len(pct)} %-formatted values in tile area"


# ---------------------------------------------------------------------------
# Stage B — tile label
# ---------------------------------------------------------------------------


def test_no_template_uses_old_label() -> None:
    """No tab template should still contain 'P(neg 10Y real return)' after Stage B."""
    template_dir = Path("src/viz/templates")
    for p in template_dir.glob("tab_*.html"):
        text = p.read_text(encoding="utf-8")
        assert "P(neg 10Y real return)" not in text, (
            f"{p.name} still contains old label"
        )


def test_dashboard_uses_new_label() -> None:
    text = Path("outputs/dashboard.html").read_text(encoding="utf-8")
    assert "P(neg 10Y real return)" not in text
    assert text.count("P(&lt; 5% 10Y CAGR)") >= 10


# ---------------------------------------------------------------------------
# Stage C — Reach-for-Yield contrarian
# ---------------------------------------------------------------------------


def test_reach_for_yield_contrarian_in_registry() -> None:
    from src.viz.data_extraction import VARIANT_REGISTRY
    meta = VARIANT_REGISTRY["spread_hy_reach_for_yield"]
    assert meta["direction_convention"] == "contrarian"


def test_reach_for_yield_callout_not_green_at_low_z() -> None:
    """At current low z, Reach-for-Yield should NOT be green (contrarian = orange)."""
    text = Path("outputs/dashboard.html").read_text(encoding="utf-8")
    ry_start = text.find('<section data-tab="spread_hy_reach_for_yield"')
    ry_end = text.find("</section>", ry_start)
    section = text[ry_start:ry_end]
    safe = section.encode("ascii", "replace").decode("ascii")
    # Find the header border-left color in the first card.
    import re
    m = re.search(r'border-left: 4px solid (#[0-9a-fA-F]+);', safe)
    assert m, "no border-left color found in Reach-for-Yield section"
    color = m.group(1).upper()
    # Green palette: #5DBB63, #1B7A3E. Reach-for-Yield at low z should be NOT green.
    assert color.upper() not in ("#5DBB63", "#1B7A3E"), (
        f"Reach-for-Yield callout color {color} is green; expected orange/red (contrarian)"
    )


# ---------------------------------------------------------------------------
# Stage D — Panel C subtitle + interpretation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_panel_c_subtitle_uses_indicator_label(key: str) -> None:
    """Panel C heading must not say 'by regime' generic — should use indicator label."""
    template_path = Path(f"src/viz/templates/tab_{key}.html")
    text = template_path.read_text(encoding="utf-8")
    # Panel C heading regex
    import re
    m = re.search(r"Panel C &mdash; S&amp;P 500 by ([^<]+?)\s*regime", text)
    assert m, f"{key}: Panel C subtitle pattern not found"
    # The captured indicator label must NOT be empty or just "regime".
    label = m.group(1).strip()
    assert label and label.lower() != "regime", f"{key}: empty Panel C label"


@pytest.mark.parametrize("key", DERIVED_KEYS)
def test_interpretation_text_not_placeholder(key: str) -> None:
    """Each derived tab must have non-placeholder Interpretation text."""
    template_path = Path(f"src/viz/templates/tab_{key}.html")
    text = template_path.read_text(encoding="utf-8")
    placeholders = (
        "Standardised signal of the derived spread.",
        "Standardised signal.",
    )
    for placeholder in placeholders:
        assert placeholder not in text, (
            f"{key}: still has placeholder interpretation text"
        )


# ---------------------------------------------------------------------------
# Stage E — bootstrap text
# ---------------------------------------------------------------------------


def test_no_template_says_500_replications() -> None:
    template_dir = Path("src/viz/templates")
    for p in template_dir.glob("tab_*.html"):
        text = p.read_text(encoding="utf-8")
        assert "500 replications" not in text, (
            f"{p.name} still says '500 replications'"
        )


def test_templates_say_10000_replications() -> None:
    template_dir = Path("src/viz/templates")
    found = 0
    for p in template_dir.glob("tab_*.html"):
        text = p.read_text(encoding="utf-8")
        if "10,000 replications" in text:
            found += 1
    # At least 13 macro indicator tabs should mention 10,000.
    assert found >= 13, f"only {found} templates mention 10,000 replications"


# ---------------------------------------------------------------------------
# Stage F — MRC v2 disclosure
# ---------------------------------------------------------------------------


def test_mrc_tab_has_correlation_disclosure() -> None:
    text = Path("src/viz/templates/tab_mrc.html").read_text(encoding="utf-8")
    assert "v11.0.2 composition disclosure" in text
    assert "correlates ~0.99" in text
    assert "diagnostic" in text.lower()
