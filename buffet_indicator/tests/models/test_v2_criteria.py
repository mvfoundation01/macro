"""§11.2 T12+T13+T14 — v2.0 verdict criteria evaluator.
DRAFT_v4 §5 + §12 (seal 2a94417).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.models.v2_criteria import evaluate_v2_criteria  # noqa: E402


def test_all_seven_criteria_known_pass_and_fail() -> None:
    """Synthetic all-pass / all-fail fixtures yield correct verdict logic.

    References: DRAFT_v4 §5 + sealed pre-reg §11.2 T12.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")


def test_criterion_4_strict_t_boundary() -> None:
    """t=1.65 -> FAIL; t=1.6501 -> PASS (STRICT > at C4 t threshold).

    References: DRAFT_v4 §5 (C4 strict t-boundary) + sealed pre-reg §11.2 T13.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")


def test_bonferroni_denominator_is_20() -> None:
    """Bonferroni alpha/20 = 0.0025 (5 components x 4 horizons).

    NEW per Codex round-2.
    References: DRAFT_v4 §5 + sealed pre-reg §11.2 T14.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
