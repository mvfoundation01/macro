"""Phase E.5 — verdict JSON writer tests.

References: PROMPT_CC_v11_4_v2_sprint_PHASE_E.md §6 + sealed §12.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.ingest._base import SourceMissingError  # noqa: E402
from src.models.v2_criteria import VERDICTS  # noqa: E402
from src.models.retest import VALID_RETEST_STATUSES  # noqa: E402


def _has_required_masters() -> bool:
    from src.ingest.master_archive import load_master
    for sid in (
        "walcl", "wdtgal", "rrpontsyd", "m2_sl", "busloans", "totll",
        "dtwexbgs", "tedrate", "sofr", "ioer", "iorb",
    ):
        try:
            load_master(sid)
        except SourceMissingError:
            return False
    return True


pytestmark = pytest.mark.skipif(
    not _has_required_masters(),
    reason="Requires Phase B master parquets in data/master/.",
)


def test_verdict_json_has_required_top_level_keys(tmp_path: Path) -> None:
    from src.models.v2_run_verdict import run_verdict

    out = tmp_path / "lc_v2_verdict.json"
    _, doc, _ = run_verdict(n_bootstrap=200, purpose="test", output_path=out)

    required = {
        "schema_version", "verdict", "evidence_status", "retest_status",
        "pre_reg_commit", "data_cutoff", "run_timestamp", "git_head",
        "n_pass_total", "n_pass_predictive", "component_id_map",
        "criteria", "decision_rule_check", "look_ahead_audit",
        "panel_meta", "_meta",
    }
    assert required.issubset(doc.keys()), (
        f"missing keys: {sorted(required - doc.keys())}"
    )


def test_verdict_enums_are_schema_valid(tmp_path: Path) -> None:
    from src.models.v2_run_verdict import run_verdict

    out = tmp_path / "lc_v2_verdict.json"
    _, doc, _ = run_verdict(n_bootstrap=200, purpose="test", output_path=out)
    assert doc["verdict"] in VERDICTS
    assert doc["evidence_status"] in {"NORMAL", "NO_EVALUABLE_CRITERIA", "MIXED"}
    assert doc["retest_status"] in VALID_RETEST_STATUSES


def test_verdict_has_7_criteria_with_expected_cell_counts(tmp_path: Path) -> None:
    from src.models.v2_run_verdict import run_verdict

    out = tmp_path / "lc_v2_verdict.json"
    _, doc, _ = run_verdict(n_bootstrap=200, purpose="test", output_path=out)
    crits = doc["criteria"]
    assert len(crits) == 7
    cell_counts = {c["criterion_id"]: len(c["cells"]) for c in crits}
    assert cell_counts == {
        "C1": 1, "C2": 1, "C3": 1,  # 1 LC_TIER2 cell each
        "C4": 4,                     # 4 LC_FULL horizons
        "C5": 5,                     # 5 ADF entries
        "C6": 5,                     # 5 VIF entries
        "C7": 20,                    # 5 components x 4 horizons
    }


def test_verdict_round_trip_json(tmp_path: Path) -> None:
    from src.models.v2_run_verdict import run_verdict

    out = tmp_path / "lc_v2_verdict.json"
    _, doc, sha = run_verdict(n_bootstrap=200, purpose="test", output_path=out)
    # File exists and parses back to a structurally equivalent dict.
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["schema_version"] == doc["schema_version"]
    assert parsed["verdict"] == doc["verdict"]
    assert parsed["n_pass_total"] == doc["n_pass_total"]
    # Sidecar SHA file exists.
    sidecar = out.with_suffix(out.suffix + ".sha256")
    assert sidecar.exists()
    assert sidecar.read_text(encoding="utf-8").strip() == sha


def test_verdict_component_id_map_matches_sealed(tmp_path: Path) -> None:
    from src.models.v2_run_verdict import run_verdict

    out = tmp_path / "lc_v2_verdict.json"
    _, doc, _ = run_verdict(n_bootstrap=200, purpose="test", output_path=out)
    assert doc["component_id_map"] == {
        "z1": "netfed_liquidity",
        "z2": "m2_growth_yoy",
        "z3": "banklend_growth_yoy",
        "z4": "dxy_inverse",
        "z5": "funding_stress",
    }


def test_verdict_pit_audit_passes(tmp_path: Path) -> None:
    from src.models.v2_run_verdict import run_verdict

    out = tmp_path / "lc_v2_verdict.json"
    _, doc, _ = run_verdict(n_bootstrap=200, purpose="test", output_path=out)
    audit = doc["look_ahead_audit"]
    assert audit["all_cells_pit_compliant"] is True
    assert audit["violations"] == []


def test_verdict_decision_rule_matches_n_pass(tmp_path: Path) -> None:
    from src.models.v2_run_verdict import run_verdict

    out = tmp_path / "lc_v2_verdict.json"
    _, doc, _ = run_verdict(n_bootstrap=200, purpose="test", output_path=out)
    rule = doc["decision_rule_check"]
    assert rule["rule"] == "n_pass >= 4 of 7"
    expected_pass = doc["n_pass_total"] >= 4
    assert rule["total_passed"] is expected_pass
    if expected_pass:
        assert doc["verdict"] == "PASS"
    else:
        assert doc["verdict"] == "FAIL"


def test_verdict_sealed_provenance_present(tmp_path: Path) -> None:
    from src.models.v2_run_verdict import run_verdict
    from src.models.v2_verdict_writer import SEALED_PREREG_COMMIT, SEALED_PREREG_SHA256

    out = tmp_path / "lc_v2_verdict.json"
    _, doc, _ = run_verdict(n_bootstrap=200, purpose="test", output_path=out)
    assert doc["pre_reg_commit"] == SEALED_PREREG_COMMIT
    assert doc["sealed_prereg_sha256"] == SEALED_PREREG_SHA256
