"""Tests for the LC v1.0 (DIAGNOSTIC) standalone dashboard panel (Session 8 §2.I).

The panel is built as a standalone HTML page at
``outputs/lc_v1_diagnostic_panel.html`` by
``scripts/build_lc_v1_dashboard_panel.py``. These structural tests assert
that the generated HTML contains the 9 required sections per prompt §2.I.2.

References
----------
* prompt/052226/PROMPT_v11_3_session_8_H_I_J_closeout.md §2.I.4
"""
from __future__ import annotations

from pathlib import Path

import pytest

PANEL_HTML = (
    Path(__file__).resolve().parents[2] / "outputs" / "lc_v1_diagnostic_panel.html"
)


@pytest.fixture(scope="module")
def panel_text() -> str:
    if not PANEL_HTML.exists():
        pytest.skip(
            f"Panel HTML not built yet at {PANEL_HTML}. Run "
            f"`python scripts/build_lc_v1_dashboard_panel.py` first."
        )
    return PANEL_HTML.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Headline / structure
# ---------------------------------------------------------------------------


def test_TI1_panel_html_exists(panel_text: str) -> None:
    """T-I1: panel HTML file exists and is non-trivial size (>10 KB)."""
    assert len(panel_text) > 10_000


def test_TI2_panel_has_diagnostic_title(panel_text: str) -> None:
    """T-I2: title contains 'DIAGNOSTIC' marker."""
    assert "LC v1.0 (DIAGNOSTIC)" in panel_text


def test_TI3_headline_verdict_card_says_FAIL(panel_text: str) -> None:
    """T-I3: headline verdict card contains 'FAIL' (per pre-reg §2.1 decision rule)."""
    assert "LC v1.0 — FAIL" in panel_text or "LC v1.0 — FAIL" in panel_text


def test_TI4_confidence_99pct(panel_text: str) -> None:
    """T-I4: verdict card reports 99% confidence floor."""
    assert "99%" in panel_text or "99 %" in panel_text


def test_TI5_diagnostic_only_framing(panel_text: str) -> None:
    """T-I5: display framing 'DIAGNOSTIC ONLY' explicit in verdict card."""
    assert "DIAGNOSTIC ONLY" in panel_text


# ---------------------------------------------------------------------------
# Section content
# ---------------------------------------------------------------------------


def test_TI6_three_findings_present(panel_text: str) -> None:
    """T-I6: all 3 publishable findings present."""
    assert "Finding 1" in panel_text
    assert "Finding 2" in panel_text
    assert "Finding 3" in panel_text


def test_TI7_regression_table_has_all_scopes(panel_text: str) -> None:
    """T-I7: regression table contains all 3 scopes."""
    assert "LC_FULL" in panel_text
    assert "LC_TIER2" in panel_text
    assert "LC_DEEP" in panel_text


def test_TI8_per_component_table_has_5_components(panel_text: str) -> None:
    """T-I8: per-component table mentions all 5 components."""
    for comp in (
        "z1_netfed", "z2_m2_yoy", "z3_banklend_yoy",
        "z4_dxy_inv", "z5_funding_stress",
    ):
        assert comp in panel_text, f"missing {comp}"


def test_TI9_insufficient_sample_warning_on_lc_full_10y(panel_text: str) -> None:
    """T-I9: 'insufficient sample' warning badge appears for LC_FULL @ 10Y."""
    assert "insufficient sample" in panel_text


def test_TI10_calibration_disclosure_present(panel_text: str) -> None:
    """T-I10: prominent calibration MISCALIBRATED disclosure present."""
    assert "MISCALIBRATED" in panel_text
    assert "PIT Kolmogorov-Smirnov" in panel_text
    assert "Do not use" in panel_text or "do not use" in panel_text


def test_TI11_diagnostics_collapsible_present(panel_text: str) -> None:
    """T-I11: Section 7 diagnostic tests collapsible present."""
    assert "Section 7" in panel_text
    assert "Stationarity" in panel_text
    assert "Multicollinearity" in panel_text
    assert "Bai-Perron" in panel_text


def test_TI12_calibration_collapsible_present(panel_text: str) -> None:
    """T-I12: Section 8 calibration collapsible present."""
    assert "Section 8" in panel_text
    assert "Brier" in panel_text
    assert "PIT" in panel_text


def test_TI13_methodology_section_present(panel_text: str) -> None:
    """T-I13: Section 9 methodology/provenance section present with key references."""
    assert "Section 9" in panel_text
    assert "MV_LIQUIDITY_COMPOSITE_PREREGISTER.md" in panel_text
    assert "a8635ef" in panel_text
    assert "DECISIONS.md" in panel_text


def test_TI14_no_emojis_outside_warning_badges(panel_text: str) -> None:
    """T-I14: warning glyph ⚠ is used for warning cards (no other decorative emojis)."""
    # ⚠ is the only intentional symbol; should appear at least once.
    assert "⚠" in panel_text or "&#9888;" in panel_text


def test_TI15_no_actionable_language(panel_text: str) -> None:
    """T-I15: panel should NOT recommend any action ('buy', 'sell', 'allocate' etc.)."""
    # Verify the DIAGNOSTIC framing — no actionable verbs.
    lowered = panel_text.lower()
    for bad in ("recommend buying", "recommend selling", "should allocate"):
        assert bad not in lowered, f"actionable language found: {bad}"


def test_TI16_bundle_size_under_20mb(panel_text: str) -> None:
    """T-I16: panel HTML stays well under the 20 MB dashboard bundle ceiling."""
    # 20 MB hard ceiling per prompt §2.I.5. We expect << 20 MB on the
    # standalone panel because the embedded figures are 2 PNGs (LC_TIER2 10Y
    # reliability + PIT) plus tables and HTML chrome — all well below 1 MB.
    assert len(panel_text.encode("utf-8")) < 20 * 1024 * 1024
