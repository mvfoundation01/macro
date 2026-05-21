"""v11.2-stat — V2 DIAGNOSTIC banner tests (Part A §A.3).

Verifies that the V2 MV-Conditional diagnostic disclosure mandated by
pre-registration §3.3 appears prominently in the built dashboard.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_HTML = REPO_ROOT / "outputs" / "dashboard.html"


def _read_dashboard() -> str:
    if not DASHBOARD_HTML.exists():
        pytest.skip(f"{DASHBOARD_HTML} not built yet — run `python -m src.cli dashboard`")
    return DASHBOARD_HTML.read_text(encoding="utf-8")


def test_v2_diagnostic_banner_present_in_strategy_engine_tab():
    """Banner HTML element with id='v2-diagnostic-banner' exists in built dashboard."""
    html = _read_dashboard()
    assert 'id="v2-diagnostic-banner"' in html, (
        "V2 diagnostic banner missing from built dashboard.html — "
        "pre-reg §3.3 mandates this disclosure when rules are rejected."
    )


def test_v2_diagnostic_banner_cites_prereg_commit_sha():
    """Banner explicitly cites pre-reg commit a90b02d so auditors can trace it."""
    html = _read_dashboard()
    assert 'a90b02d' in html, (
        "Banner must reference pre-reg commit SHA a90b02d for audit traceability."
    )


def test_v2_diagnostic_banner_states_all_three_rules_rejected():
    """Banner names all 3 rules and explicitly states REJECTED outcome."""
    html = _read_dashboard()
    for rule in ("R-PRIMARY", "R-ALT1", "R-ALT2"):
        assert rule in html, f"banner missing rule name {rule}"
    assert "REJECTED" in html, "banner must explicitly state REJECTED outcome for the rules"
