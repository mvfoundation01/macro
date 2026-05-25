"""Phase F-DOC.D — display framing tests per sealed §7 + §10.1.

Verifies the DIAGNOSTIC ONLY view for the v2.0 FAIL verdict contains:
- Required structural elements (header, criteria, audit, provenance)
- Explicit "do not interpret as predictive signal" disclaimer
- Failure mode diagnosis (Mode A, Mode B)
- Negative: no forbidden signal-language patterns
- Mode routing (PASS/PASS_WITH_CAVEATS/FAIL) per n_pass_total
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.models.v2_display_framing import (  # noqa: E402
    compose_diagnostic_only_view,
    determine_framing_mode,
    write_display_framing,
)


CANONICAL_VERDICT_PATH = Path(__file__).resolve().parents[2] / "outputs" / "lc_v2_verdict.json"


def _canonical_verdict_available() -> bool:
    return CANONICAL_VERDICT_PATH.exists()


pytestmark = pytest.mark.skipif(
    not _canonical_verdict_available(),
    reason="Requires the canonical outputs/lc_v2_verdict.json (Phase F-BLK1.J promotes it).",
)


def test_determine_framing_mode_fail_for_n_pass_lt_4() -> None:
    assert determine_framing_mode({"n_pass_total": 0}) == "FAIL"
    assert determine_framing_mode({"n_pass_total": 1}) == "FAIL"
    assert determine_framing_mode({"n_pass_total": 3}) == "FAIL"


def test_determine_framing_mode_pass_with_caveats_for_4() -> None:
    assert determine_framing_mode({"n_pass_total": 4}) == "PASS_WITH_CAVEATS"


def test_determine_framing_mode_pass_for_5_or_more() -> None:
    assert determine_framing_mode({"n_pass_total": 5}) == "PASS"
    assert determine_framing_mode({"n_pass_total": 7}) == "PASS"


def test_fail_verdict_produces_diagnostic_only_view(tmp_path: Path) -> None:
    """v2.0 canonical FAIL verdict produces DIAGNOSTIC ONLY view with all sealed-required elements."""
    output = write_display_framing(CANONICAL_VERDICT_PATH, tmp_path)
    assert output.name == "lc_v2_display_fail.md"
    content = output.read_text(encoding="utf-8")

    # Required sealed §7 elements.
    assert "DIAGNOSTIC ONLY" in content
    assert "FAIL" in content
    assert "1 / 7" in content or "1/7" in content
    # All 7 criteria mentioned.
    for cid in ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]:
        assert cid in content, f"missing {cid} in display view"
    # Failure mode diagnosis (Mode A + Mode B) + C6 PASSED line.
    assert "Mode A" in content
    assert "Mode B" in content
    assert "C6" in content and "PASSED" in content
    # Audit + sealed sha + provenance.
    assert "PIT look-ahead audit" in content
    assert "c3c3ec1a" in content
    assert "lc_v2_verdict.json" in content
    # Disclaimers.
    assert "DO NOT INTERPRET AS PREDICTIVE SIGNAL" in content
    # The disclaimer block appears at least twice (initial + restating).
    assert content.count("DO NOT INTERPRET AS PREDICTIVE SIGNAL") >= 2


def test_diagnostic_only_view_does_not_contain_forbidden_signal_language(tmp_path: Path) -> None:
    """Negative test: view must NOT contain language suggesting predictive use."""
    output = write_display_framing(CANONICAL_VERDICT_PATH, tmp_path)
    content = output.read_text(encoding="utf-8").lower()
    forbidden = [
        "actionable signal",
        "buy when",
        "sell when",
        "predicts that the market",
        "indicates that the market will",
        "implies a forecast for",
        "use this as a signal",
        "this signal indicates",
    ]
    for f in forbidden:
        assert f not in content, f"forbidden signal-language pattern found: {f!r}"


def test_compose_diagnostic_only_view_returns_content_and_writes_file(tmp_path: Path) -> None:
    verdict = json.loads(CANONICAL_VERDICT_PATH.read_text(encoding="utf-8"))
    out = tmp_path / "test_view.md"
    content = compose_diagnostic_only_view(verdict, out)
    assert out.exists()
    assert content == out.read_text(encoding="utf-8")
    assert content.startswith("# DIAGNOSTIC ONLY VIEW")


def test_pass_modes_raise_not_implemented(tmp_path: Path) -> None:
    """PASS / PASS_WITH_CAVEATS branches deferred until a non-FAIL verdict exists."""
    stub_pass = {"n_pass_total": 5, "verdict": "PASS"}
    stub_pwc = {"n_pass_total": 4, "verdict": "PASS"}
    pass_path = tmp_path / "stub_pass.json"
    pwc_path = tmp_path / "stub_pwc.json"
    pass_path.write_text(json.dumps(stub_pass), encoding="utf-8")
    pwc_path.write_text(json.dumps(stub_pwc), encoding="utf-8")

    with pytest.raises(NotImplementedError, match="PASS"):
        write_display_framing(pass_path, tmp_path)
    with pytest.raises(NotImplementedError, match="PASS_WITH_CAVEATS"):
        write_display_framing(pwc_path, tmp_path)
