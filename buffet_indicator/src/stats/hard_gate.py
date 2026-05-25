"""HARD GATE — pre-registration ancestor assertion (DRAFT_v4 §0.3 + §8.2).

This module is the PRIORITY-FIRST deliverable of the v2.0 sprint
(Phase A.4): its presence + passing tests lifts seal report §16 success
criterion #6 from DEFERRED to PASS.

The HARD GATE invariant from §0.3 + §8.2: every verdict-bearing run MUST
execute against a git ``HEAD`` that is a strict descendant of the sealed
pre-registration commit ``2a94417524e67c7b88cb05ad1ac61fafd6b5711a``.
Violation modes are distinguished:

* :class:`HardGateViolation` — the policy is definitively violated
  (e.g., ``HEAD`` is on a sibling branch, or is a preseal ancestor and
  ``allow_preseal=False``).
* :class:`HardGateIndeterminate` — the policy cannot be evaluated
  conclusively (e.g., shallow clone, missing commit object, unresolvable
  ``HEAD``); refuse to certify rather than guess.

References
----------
- Sealed pre-reg §0.3 + §8.2: HARD GATE invariant statement.
- Sealed pre-reg §11.1 line 735: function signature.
- Seal report ``outputs/seal_report_v11_4.md`` §16 #6: criterion-lift target.
"""
from __future__ import annotations

import subprocess


class HardGateViolation(Exception):
    """Raised when HEAD is not a strict descendant of the sealed pre-reg commit."""


class HardGateIndeterminate(Exception):
    """Raised when ancestry cannot be determined (e.g., shallow clone)."""


def _run_git(*args: str) -> tuple[int, str, str]:
    """Run ``git`` with capture; return ``(returncode, stdout, stderr)``."""
    proc = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


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
        Full SHA (or any valid revspec) of the sealed pre-registration commit.
    sealed : bool, keyword-only
        If True, enforce the gate (raise on violation / indeterminacy).
        If False, this call is a no-op (development mode).
    allow_preseal : bool, default False
        If True and ``head`` is an ancestor of ``pre_reg_commit`` (i.e., the
        run is preseal), permit it. Used by the seal sequence itself, not
        by verdict-bearing runs.
    head : str, default ``"HEAD"``
        Git revspec to check (default current ``HEAD``).

    Raises
    ------
    HardGateViolation
        ``sealed=True`` and ``head`` is not a descendant of
        ``pre_reg_commit`` (and ``allow_preseal=False`` or HEAD is not an
        ancestor either).
    HardGateIndeterminate
        ``sealed=True`` and ancestry cannot be conclusively determined
        (shallow clone, missing commit, unresolvable HEAD).

    Returns
    -------
    None
        Returned silently when the gate passes.

    References
    ----------
    Sealed pre-reg §0.3 + §8.2 + §11.1 line 735.
    Test: ``T15`` (``test_hard_gate_handles_ancestor_detached_preseal_and_shallow``).
    """
    if not sealed:
        # Development mode: gate is informational, do not raise.
        return

    # Shallow-clone defence: a shallow history may omit ancestors and
    # produce a misleading "not an ancestor" verdict. Per §8.2, refuse
    # to certify in that case.
    code, out, _ = _run_git("rev-parse", "--is-shallow-repository")
    if code == 0 and out.strip() == "true":
        raise HardGateIndeterminate(
            f"Repository is a shallow clone; ancestry of "
            f"pre_reg_commit={pre_reg_commit[:12]!s} cannot be verified. "
            "Refusing to certify this run as verdict-bearing."
        )

    # Resolve head to a SHA (catches missing refs and detached states cleanly).
    code, head_sha, err = _run_git("rev-parse", "--verify", head)
    if code != 0:
        raise HardGateIndeterminate(
            f"Could not resolve head={head!r}: git rev-parse exit={code}; "
            f"{err.strip()}"
        )
    head_sha = head_sha.strip()

    # Verify the pre_reg_commit object exists locally.
    code, _, err = _run_git("cat-file", "-e", pre_reg_commit)
    if code != 0:
        raise HardGateIndeterminate(
            f"pre_reg_commit={pre_reg_commit[:12]!s} is not present in this "
            f"repository (git cat-file exit={code}). "
            f"{err.strip()}"
        )

    # Primary check: is pre_reg_commit an ancestor of head?
    # Exit codes: 0 = is ancestor; 1 = not ancestor; other = error.
    code, _, _ = _run_git("merge-base", "--is-ancestor", pre_reg_commit, head_sha)
    if code == 0:
        return  # head descends from (or equals) pre_reg_commit -> PASS

    if code == 1:
        # Not an ancestor. Two distinguishable failure modes:
        #   (a) head is itself an ancestor of pre_reg_commit (preseal) -- if
        #       allow_preseal=True, this is acceptable; otherwise violation.
        #   (b) histories are unrelated / sibling branches -- always violation.
        if allow_preseal:
            inv_code, _, _ = _run_git(
                "merge-base", "--is-ancestor", head_sha, pre_reg_commit
            )
            if inv_code == 0:
                return  # head is preseal of pre_reg_commit, explicitly allowed
        raise HardGateViolation(
            f"HEAD ({head_sha[:12]!s}) is not a descendant of "
            f"pre_reg_commit ({pre_reg_commit[:12]!s}). "
            f"allow_preseal={allow_preseal!r}."
        )

    # Any other exit code: indeterminate.
    raise HardGateIndeterminate(
        f"git merge-base returned unexpected exit code={code} when checking "
        f"ancestry of pre_reg_commit={pre_reg_commit[:12]!s} against HEAD."
    )
