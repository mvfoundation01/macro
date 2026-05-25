"""§11.2 T10 — Stambaugh strict boundary. DRAFT_v4 §3.5 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.stambaugh import should_apply_stambaugh  # noqa: E402


def test_stambaugh_exact_boundary_not_applied() -> None:
    """Strict > at rho=0.85: should_apply_stambaugh(0.85) is False;
    should_apply_stambaugh(nextafter(0.85, 1.0)) is True.

    NEW per Codex round-2 New-5.
    References: DRAFT_v4 §3.5 + sealed pre-reg §11.2 T10.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
