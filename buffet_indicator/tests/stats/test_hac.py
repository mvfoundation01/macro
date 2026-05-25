"""§11.2 T01 — HAC lag uses v1 formula. DRAFT_v4 §3.2 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.hac import compute_hac_lag  # noqa: E402


def test_compute_hac_lag_uses_v1_formula() -> None:
    """HAC lag = horizon_months - 1 (h=12 -> 11, h=120 -> 119).

    References: DRAFT_v4 §3.2 + sealed pre-reg §11.2 T01.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
