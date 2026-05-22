"""Tests for the locked LC v1.0 verdict JSON (Session 8 §2.J).

References
----------
* prompt/052226/PROMPT_v11_3_session_8_H_I_J_closeout.md §2.J.4
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

VERDICT_PATH = (
    Path(__file__).resolve().parents[2] / "outputs" / "lc_v1_verdict.json"
)


@pytest.fixture(scope="module")
def verdict() -> dict:
    if not VERDICT_PATH.exists():
        pytest.skip(f"verdict.json missing: {VERDICT_PATH}")
    return json.loads(VERDICT_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# T-J1..T-J6
# ---------------------------------------------------------------------------


def test_TJ1_verdict_parses_valid_json(verdict: dict) -> None:
    """T-J1: verdict.json parses as valid JSON dict."""
    assert isinstance(verdict, dict)


def test_TJ2_verdict_is_FAIL(verdict: dict) -> None:
    """T-J2: verdict == 'FAIL'."""
    assert verdict["verdict"] == "FAIL"


def test_TJ3_all_seven_criteria_present(verdict: dict) -> None:
    """T-J3: all 7 criteria have keys and pass values."""
    scorecard = verdict["scorecard"]
    expected = {
        "criterion_1_oos_r2_1y_tier2",
        "criterion_2_oos_r2_3y_tier2",
        "criterion_3_oos_r2_5y_tier2",
        "criterion_4_t_positive_lc_full_any_horizon",
        "criterion_5_adf_all_components",
        "criterion_6_max_vif_lt_5",
        "criterion_7_bonferroni_sig_any_cell",
    }
    assert set(scorecard.keys()) == expected
    for k, v in scorecard.items():
        assert "pass" in v, f"missing 'pass' key in {k}"
        assert isinstance(v["pass"], bool), f"{k}.pass is not bool"


def test_TJ4_display_framing_diagnostic_only(verdict: dict) -> None:
    """T-J4: display_framing == 'DIAGNOSTIC_ONLY'."""
    assert verdict["display_framing"] == "DIAGNOSTIC_ONLY"
    assert verdict["actionable_for_investment"] is False


def test_TJ5_three_publishable_findings(verdict: dict) -> None:
    """T-J5: 3 publishable findings present with required keys."""
    findings = verdict["research_findings_publishable"]
    assert len(findings) == 3
    expected_ids = {
        "lc_deep_negative_beta_3y",
        "five_of_five_components_negative",
        "universal_gaussian_calibration_failure",
    }
    actual_ids = {f["id"] for f in findings}
    assert actual_ids == expected_ids
    for f in findings:
        assert "summary" in f
        assert "interpretation" in f or "evidence_table_path" in f


def test_TJ6_npass_equals_zero(verdict: dict) -> None:
    """T-J6: n_pass_total == 0 of 7 (LC v1.0 FAIL)."""
    assert verdict["n_pass_total"] == 0
    assert verdict["n_total_criteria"] == 7


def test_TJ_v11_4_amendment_candidates_present(verdict: dict) -> None:
    """4 v11.4 amendment candidates documented for the next-version Strategist."""
    candidates = verdict["v11_4_amendment_candidates"]
    assert isinstance(candidates, list)
    assert len(candidates) >= 4


def test_TJ_bai_perron_breaks_recorded(verdict: dict) -> None:
    """Bai-Perron break dates recorded for all 3 composites."""
    breaks = verdict["bai_perron_structural_breaks"]
    for scope in ("LC_FULL", "LC_TIER2", "LC_DEEP"):
        assert scope in breaks
        assert isinstance(breaks[scope], list)
        assert len(breaks[scope]) >= 3


def test_TJ_sprint_provenance(verdict: dict) -> None:
    """Sprint provenance: 9 sessions enumerated; invariants intact."""
    prov = verdict["sprint_provenance"]
    assert len(prov["sessions"]) == 9  # 1, 2, 3, 4, 5, 6, 6.5, 7, 8
    invariants = prov["pre_reg_invariants_intact"]
    assert invariants["a90b02d_mv_conditional"] is True
    assert invariants["a8635ef_lc_v1"] is True
    assert invariants["v50_original_sha"] == (
        "6087918DB909D3BB3AE66F43305C3331E4171AEBC55DDC0366AAFF6128026F47"
    )
