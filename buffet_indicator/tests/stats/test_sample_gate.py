"""§11.2 T02+T03 — sample gate boundaries. DRAFT_v4 §3.4 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.sample_gate import sample_gate_status  # noqa: E402


def test_sample_gate_boundary_basic() -> None:
    """n_obs_oos=60 hac_lag=11 -> evaluable; 59 -> not_evaluable (strict <).

    References: DRAFT_v4 §3.4 + sealed pre-reg §11.2 T02.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")


def test_sample_gate_boundaries_include_hac_and_neff() -> None:
    """n_obs_oos=105 hac=35 neff=30.0 -> evaluable; 104 -> not; neff=29.999 -> not.

    NEW per Codex round-2 New-8.
    References: DRAFT_v4 §3.4 + sealed pre-reg §11.2 T03.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
