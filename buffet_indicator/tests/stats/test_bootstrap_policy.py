"""§11.2 T19 — bootstrap count policy. DRAFT_v4 §3.8 + §11.3 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import dataclasses  # noqa: E402

from src.stats.bootstrap_policy import (  # noqa: E402
    BootstrapPolicy,
    load_bootstrap_policy,
)


def test_bootstrap_count_policy_is_not_runtime_dependent() -> None:
    """policy.verdict_count == 50_000; no 'runtime_exceeded' reason permitted;
    runtime_downsample_permitted is False.

    NEW per Codex round-2 New-4. 50K is IMMUTABLE for verdict-bearing CIs.
    References: DRAFT_v4 §3.8 + §11.3 + sealed pre-reg §11.2 T19.
    """
    policy = load_bootstrap_policy()
    assert isinstance(policy, BootstrapPolicy)
    assert policy.verdict_count == 50_000
    assert policy.diagnostic_count == 50_000
    assert policy.runtime_downsample_permitted is False

    # Immutability: the dataclass is frozen.
    assert getattr(BootstrapPolicy, "__dataclass_params__").frozen is True

    # Repeat call returns equal policy (deterministic).
    assert load_bootstrap_policy() == policy

    # No silent "runtime_exceeded" or downsample reason field present.
    fields = {f.name for f in dataclasses.fields(BootstrapPolicy)}
    assert "runtime_exceeded" not in fields
    assert "downsample_reason" not in fields
