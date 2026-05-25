"""HARD GATE — pre-registration ancestor assertion (DRAFT_v4 §0.3 + §8.2).

This module is the PRIORITY-FIRST deliverable of the v2.0 sprint
(Phase A.4): its presence + tests lifts seal report §16 success
criterion #6 from DEFERRED to PASS.

References
----------
- Sealed pre-reg §0.3 + §8.2: HARD GATE invariant — every verdict run
  MUST be a strict git descendant of the seal commit
  ``2a94417524e67c7b88cb05ad1ac61fafd6b5711a``.
- Sealed pre-reg §11.1 line 735: function signature.
- Seal report ``outputs/seal_report_v11_4.md`` §16 #6: criterion-lift target.
"""
from __future__ import annotations


class HardGateViolation(Exception):
    """Raised when HEAD is not a strict descendant of the sealed pre-reg commit."""


class HardGateIndeterminate(Exception):
    """Raised when ancestry cannot be determined (e.g., shallow clone)."""


def assert_prereg_ancestor(
    pre_reg_commit: str,
    *,
    sealed: bool,
    allow_preseal: bool = False,
    head: str = "HEAD",
) -> None:
    """Assert that ``head`` is a strict descendant of ``pre_reg_commit``.

    Used to prevent any verdict-bearing run from being executed on a branch
    that does not include the sealed pre-registration in its history.

    Parameters
    ----------
    pre_reg_commit : str
        Full SHA of the sealed pre-registration commit.
    sealed : bool, keyword-only
        If True, enforce strict ancestry; if False (development mode),
        downgrade violations to warnings (still implemented but non-blocking).
    allow_preseal : bool, default False
        If True, permit ``head`` to be an ANCESTOR of ``pre_reg_commit``
        (used by the seal sequence itself; not for verdict runs).
    head : str, default "HEAD"
        Git revspec to check (default current HEAD).

    Raises
    ------
    HardGateViolation
        If ``sealed=True`` and ``head`` is not a descendant of
        ``pre_reg_commit``.
    HardGateIndeterminate
        If ``sealed=True`` and the repository is a shallow clone such that
        ancestry cannot be conclusively determined.

    Returns
    -------
    None
        Returns successfully (None) when the gate passes.

    References
    ----------
    Sealed pre-reg §0.3 + §8.2 + §11.1 line 735.
    Test: ``T15`` (``test_hard_gate_handles_ancestor_detached_preseal_and_shallow``).
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
