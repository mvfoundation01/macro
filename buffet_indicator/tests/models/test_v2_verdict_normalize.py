"""Phase F-DOC.C — verdict JSON normalization tests.

Verifies that dynamic-metadata stripping enables substantive-equivalence
comparison across runs (same data + sealed methodology + same code, different
env / timestamp / git_head).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.models.v2_verdict_normalize import (  # noqa: E402
    DYNAMIC_FIELD_PATHS,
    field_level_diff,
    normalize_verdict_for_comparison,
    normalized_sha256,
)


@pytest.fixture
def stub_verdict() -> dict:
    return {
        "schema_version": "v2.0",
        "verdict": "FAIL",
        "n_pass_total": 1,
        "run_timestamp": "2026-05-25T20:00:00Z",
        "git_head": "abc1234",
        "criteria": [
            {"criterion_id": "C6", "status": "PASS", "value": 1.695},
        ],
        "_meta": {
            "library_versions_installed": {"arch": "8.0.0"},
            "library_versions_sealed_pinned": {"arch": "7.0.0"},
            "library_version_delta_note": "note",
            "python_version": "3.14.3",
            "python_implementation": "CPython",
            "platform": "Windows-11",
            "seal_metadata": {
                "git_head": "abc1234",
                "timestamp_utc_iso8601": "2026-05-25T20:00:00Z",
                "python_version": "3.14.3",
                "python_implementation": "CPython",
                "platform": "Windows-11",
                "platform_system": "Windows",
                "platform_machine": "AMD64",
                "sealed_prereg_sha256": "c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05",
            },
        },
    }


def test_normalize_strips_documented_dynamic_fields(stub_verdict: dict) -> None:
    """All DYNAMIC_FIELD_PATHS removed; substantive content preserved."""
    out = normalize_verdict_for_comparison(stub_verdict)
    for dotted in DYNAMIC_FIELD_PATHS:
        cur = out
        parts = dotted.split(".")
        present = True
        for p in parts:
            if not isinstance(cur, dict) or p not in cur:
                present = False
                break
            cur = cur[p]
        assert not present, f"dynamic field {dotted!r} should have been stripped"
    # Substantive fields preserved.
    assert out["verdict"] == "FAIL"
    assert out["n_pass_total"] == 1
    assert out["criteria"][0]["value"] == 1.695
    assert out["_meta"]["library_versions_sealed_pinned"]["arch"] == "7.0.0"
    assert out["_meta"]["seal_metadata"]["sealed_prereg_sha256"].startswith("c3c3ec1a")


def test_normalize_is_deep_copy_safe(stub_verdict: dict) -> None:
    """Normalization must not mutate the input."""
    snapshot = json.dumps(stub_verdict, sort_keys=True)
    _ = normalize_verdict_for_comparison(stub_verdict)
    assert json.dumps(stub_verdict, sort_keys=True) == snapshot


def test_normalized_sha256_stable_across_runs(stub_verdict: dict, tmp_path: Path) -> None:
    """Two verdicts identical EXCEPT in dynamic fields have the same normalized SHA."""
    a = stub_verdict
    b = json.loads(json.dumps(a))
    # Mutate ONLY dynamic fields.
    b["run_timestamp"] = "2099-12-31T23:59:59Z"
    b["git_head"] = "deadbeef"
    b["_meta"]["library_versions_installed"] = {"arch": "9.0.0"}
    b["_meta"]["python_version"] = "3.99.99"
    b["_meta"]["seal_metadata"]["git_head"] = "f00dface"
    b["_meta"]["seal_metadata"]["timestamp_utc_iso8601"] = "2099-12-31T23:59:59Z"
    b["_meta"]["seal_metadata"]["python_version"] = "3.99.99"
    b["_meta"]["seal_metadata"]["platform"] = "Linux-99.99"

    a_path = tmp_path / "a.json"
    b_path = tmp_path / "b.json"
    a_path.write_text(json.dumps(a), encoding="utf-8")
    b_path.write_text(json.dumps(b), encoding="utf-8")

    sha_a = normalized_sha256(a_path)
    sha_b = normalized_sha256(b_path)
    assert sha_a == sha_b, (
        "normalized SHA must be identical when only dynamic fields differ"
    )


def test_normalized_sha256_detects_substantive_difference(
    stub_verdict: dict, tmp_path: Path,
) -> None:
    """A change to a substantive field MUST flip the normalized SHA."""
    a = stub_verdict
    b = json.loads(json.dumps(a))
    b["criteria"][0]["value"] = 99.9  # substantive change

    a_path = tmp_path / "a.json"
    b_path = tmp_path / "b.json"
    a_path.write_text(json.dumps(a), encoding="utf-8")
    b_path.write_text(json.dumps(b), encoding="utf-8")

    assert normalized_sha256(a_path) != normalized_sha256(b_path)


def test_field_level_diff_returns_substantive_changes_only(
    stub_verdict: dict, tmp_path: Path,
) -> None:
    a = stub_verdict
    b = json.loads(json.dumps(a))
    b["run_timestamp"] = "2099-12-31T23:59:59Z"  # dynamic — should not appear
    b["criteria"][0]["value"] = 99.9            # substantive — should appear

    a_path = tmp_path / "a.json"
    b_path = tmp_path / "b.json"
    a_path.write_text(json.dumps(a), encoding="utf-8")
    b_path.write_text(json.dumps(b), encoding="utf-8")

    diffs = field_level_diff(a_path, b_path)
    assert "run_timestamp" not in diffs
    assert "criteria[0].value" in diffs
    a_val, b_val = diffs["criteria[0].value"]
    assert a_val == 1.695
    assert b_val == 99.9


def test_field_level_diff_tolerates_float_drift_below_tolerance(
    stub_verdict: dict, tmp_path: Path,
) -> None:
    a = stub_verdict
    b = json.loads(json.dumps(a))
    b["criteria"][0]["value"] = 1.695 + 5e-13  # below default 1e-12 tol

    a_path = tmp_path / "a.json"
    b_path = tmp_path / "b.json"
    a_path.write_text(json.dumps(a), encoding="utf-8")
    b_path.write_text(json.dumps(b), encoding="utf-8")

    diffs = field_level_diff(a_path, b_path, float_tolerance=1e-12)
    assert "criteria[0].value" not in diffs


def test_field_level_diff_treats_two_nans_as_equal(tmp_path: Path) -> None:
    a = {"criteria": [{"oos_r2": float("nan")}]}
    b = {"criteria": [{"oos_r2": float("nan")}]}
    a_path = tmp_path / "a.json"
    b_path = tmp_path / "b.json"
    a_path.write_text(json.dumps(a, default=str), encoding="utf-8")
    b_path.write_text(json.dumps(b, default=str), encoding="utf-8")
    # Real verdict JSONs serialize NaN as the string "NaN" (via default=str).
    # This still produces matching strings → no diff. The NaN-aware branch in
    # field_level_diff guards against false positives when callers pass real
    # NaN floats directly.
    diffs = field_level_diff(a_path, b_path)
    assert diffs == {}
