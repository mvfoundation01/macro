"""§11.2 T20 — sealed pre-reg contains no unresolved placeholders.
DRAFT_v4 §9 + seal-block invariant (seal 2a94417).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


FORBIDDEN_MARKERS: tuple[str, ...] = (
    "<VERIFIED_BY_CLAUDE_CODE>",
    "<TRANSCRIBE_FROM_V1>",
    "<TRANSCRIBE>",
    "<COMPUTE>",
    "<TO_BE_FILLED_BY_CLAUDE_CODE_AT_SEAL_TIME>",
)
"""Tokens that must never appear in the sealed pre-reg outside of self-documenting lines."""

SEALED_PREREG = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md"
)


def _line_is_documenting_marker(line: str) -> bool:
    """Q5 R1 line-skip: a line is allowed to mention a marker if it is
    *documenting* the marker (i.e., describing the forbidden tokens) rather
    than actually leaving an unresolved placeholder.

    We use a conservative heuristic: a line that contains EITHER the word
    "forbidden", "placeholder", "marker", "shall not appear", or
    "must not appear" is documenting the marker; or the line is fenced
    inside the §11.2 acceptance test description (referencing the test itself)
    or the §9 verification-items list.
    """
    low = line.lower()
    documentation_phrases = (
        "forbidden",
        "placeholder",
        "marker",
        "shall not appear",
        "must not appear",
        "shall not remain",
        "must not remain",
        "unresolved placeholder",
        "no `<verified_by_claude_code>`",
        "no <verified_by_claude_code>",
        "no `<transcribe",
        "no <transcribe",
        "no `<compute",
        "no <compute",
        "no `<to_be_filled",
        "no <to_be_filled",
    )
    return any(phrase in low for phrase in documentation_phrases)


def test_sealed_prereg_contains_no_unresolved_placeholders() -> None:
    """No <VERIFIED_BY_CLAUDE_CODE>, <TRANSCRIBE_FROM_V1>, <TRANSCRIBE>,
    <COMPUTE>, <TO_BE_FILLED_BY_CLAUDE_CODE_AT_SEAL_TIME> remain in sealed
    text (using Q5 R1 line-skip for docs about the markers themselves).

    NEW per Codex round-2 New-7. Seal-blocking invariant.
    References: DRAFT_v4 §9 + sealed pre-reg §11.2 T20.
    """
    assert SEALED_PREREG.exists(), f"sealed pre-reg missing at {SEALED_PREREG}"
    text = SEALED_PREREG.read_text(encoding="utf-8")
    offending: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _line_is_documenting_marker(line):
            continue
        for marker in FORBIDDEN_MARKERS:
            if marker in line:
                offending.append((lineno, marker, line.strip()))
    assert not offending, (
        "Unresolved placeholders found in sealed pre-reg:\n"
        + "\n".join(f"  line {ln}: {mk!r} -> {body}" for ln, mk, body in offending)
    )
