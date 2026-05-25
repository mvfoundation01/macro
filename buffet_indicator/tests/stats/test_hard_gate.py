"""§11.2 T15 — HARD GATE ancestor + detached + preseal + shallow.
DRAFT_v4 §0.3 + §8.2 (seal 2a94417). PRIORITY-FIRST.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.hard_gate import (  # noqa: E402
    HardGateIndeterminate,
    HardGateViolation,
    assert_prereg_ancestor,
)


def test_hard_gate_handles_ancestor_detached_preseal_and_shallow() -> None:
    """HardGateViolation and HardGateIndeterminate raised on synthetic git
    fixtures (preseal, shallow, detached). Real seal commit + descendant HEAD
    must pass.

    This is the PRIORITY-FIRST acceptance test for v2.0 sprint Phase A.4;
    its PASS lifts seal report §16 success criterion #6 from DEFERRED to PASS.
    References: DRAFT_v4 §0.3 + §8.2 + sealed pre-reg §11.2 T15.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
