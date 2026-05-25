"""Bootstrap policy (50K immutable) — DRAFT_v4 §3.8 + §11.3 (seal 2a94417).

References
----------
- Sealed pre-reg §3.8 + §11.3 invariant #10: ``n_bootstrap = 50_000`` is
  IMMUTABLE for all verdict-bearing quantities. No runtime-based downsample.
- Sealed pre-reg §11.1 line 742: function signature.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BootstrapPolicy:
    """Immutable bootstrap-count policy.

    Attributes
    ----------
    verdict_count : int
        Bootstrap reps for verdict-bearing CIs. MUST be 50_000.
    diagnostic_count : int
        Bootstrap reps for diagnostic-only outputs (allowed to be lower).
    runtime_downsample_permitted : bool
        MUST be False (§3.8 invariant). Maintained for explicit assertion
        in tests.
    """

    verdict_count: int
    diagnostic_count: int
    runtime_downsample_permitted: bool


def load_bootstrap_policy() -> BootstrapPolicy:
    """Return the canonical bootstrap policy per §3.8 + §11.3.

    Returns
    -------
    BootstrapPolicy
        With ``verdict_count == 50_000`` and
        ``runtime_downsample_permitted is False``.

    References
    ----------
    Sealed pre-reg §3.8 + §11.3 + §11.1 line 742. Test: ``T19``.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
