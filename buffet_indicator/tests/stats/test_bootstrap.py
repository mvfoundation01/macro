"""§11.2 T08+T09 — stationary bootstrap. DRAFT_v4 §3.8 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.bootstrap import (  # noqa: E402
    choose_stationary_block_length,
    stationary_bootstrap_ci,
)


def test_optimal_block_length_uses_arch_stationary_column() -> None:
    """arch.bootstrap.optimal_block_length(np.arange(100.0))['stationary'].iloc[0]
    matches; columns include both 'stationary' and 'circular'; CORRECT column
    selection is 'stationary' (NOT 'circular').

    CORRECTED per Codex round-3 New-1 against installed arch==7.0.0.
    References: DRAFT_v4 §3.8 + sealed pre-reg §11.2 T08.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")


def test_stationary_bootstrap_is_byte_identical() -> None:
    """Two runs with same seed produce byte-identical bootstrap output.

    Uses np.random.SeedSequence determinism.
    References: DRAFT_v4 §3.8 + sealed pre-reg §11.2 T09.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
