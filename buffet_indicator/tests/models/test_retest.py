"""§11.2 T16+T17 — annual re-test cadence. DRAFT_v4 §6.2 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.models.retest import annual_retest_status  # noqa: E402


def test_annual_retest_fires_once_per_year() -> None:
    """Idempotency: repeat calls within a year produce no new verdict;
    no-new-data and date-trigger paths handled.

    References: DRAFT_v4 §6.2 + sealed pre-reg §11.2 T16.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")


def test_retest_unstable_verdict_is_schema_valid() -> None:
    """Reversal fixture -> UNSTABLE verdict, schema validates per §12.

    NEW per Codex round-2 New-6.
    References: DRAFT_v4 §6.2 + §12 + sealed pre-reg §11.2 T17.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
