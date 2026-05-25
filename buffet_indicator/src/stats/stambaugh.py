"""Stambaugh-bias gating predicate — DRAFT_v4 §3.5 (seal 2a94417).

References
----------
- Sealed pre-reg §3.5: Stambaugh correction applied iff
  ``rho_hat > 0.85`` (STRICT ``>``; ``rho_hat == 0.85`` does NOT apply).
- Sealed pre-reg §11.1 line 740: function signature.
"""
from __future__ import annotations


def should_apply_stambaugh(rho: float) -> bool:
    """Return True iff Stambaugh bias-correction should be applied.

    Per §3.5 the threshold is STRICT: ``rho > 0.85`` triggers the
    correction; ``rho == 0.85`` does NOT (test ``T10`` pins this).

    Parameters
    ----------
    rho : float
        AR(1) coefficient of the predictor.

    Returns
    -------
    bool

    References
    ----------
    Sealed pre-reg §3.5 + §11.1 line 740. Test: ``T10``.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
