"""§11.2 T20 — sealed pre-reg contains no unresolved placeholders.
DRAFT_v4 §9 + seal-block invariant (seal 2a94417).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402


def test_sealed_prereg_contains_no_unresolved_placeholders() -> None:
    """No <VERIFIED_BY_CLAUDE_CODE>, <TRANSCRIBE_FROM_V1>, <TRANSCRIBE>,
    <COMPUTE>, <TO_BE_FILLED_BY_CLAUDE_CODE_AT_SEAL_TIME> remain in sealed
    text (using Q5 R1 line-skip for docs about the markers themselves).

    NEW per Codex round-2 New-7. Seal-blocking invariant.
    References: DRAFT_v4 §9 + sealed pre-reg §11.2 T20.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
