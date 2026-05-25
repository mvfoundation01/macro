"""§11.2 T19 — bootstrap count policy. DRAFT_v4 §3.8 + §11.3 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.bootstrap_policy import load_bootstrap_policy  # noqa: E402


def test_bootstrap_count_policy_is_not_runtime_dependent() -> None:
    """policy.verdict_count == 50_000; no 'runtime_exceeded' reason permitted;
    runtime_downsample_permitted is False.

    NEW per Codex round-2 New-4. 50K is IMMUTABLE for verdict-bearing CIs.
    References: DRAFT_v4 §3.8 + §11.3 + sealed pre-reg §11.2 T19.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
