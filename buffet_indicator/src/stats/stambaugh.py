"""Stambaugh-bias gating predicate — DRAFT_v4 §3.6 + §3.9 (seal 2a94417).

References
----------
- Sealed pre-reg §3.6: Stambaugh (1999) correction applied iff
  ``rho_hat > 0.85`` (STRICT ``>``).
- Sealed pre-reg §3.9 comparator table: ``rho_hat == 0.85`` -> NOT applied
  (FIX per Codex round-2 New-5).
- Sealed pre-reg §11.1 line 740: function signature.
"""
from __future__ import annotations

import math


STAMBAUGH_THRESHOLD: float = 0.85
"""Strict-greater-than threshold for Stambaugh correction (§3.6 + §3.9)."""


def should_apply_stambaugh(rho: float) -> bool:
    """Return True iff Stambaugh bias-correction should be applied.

    Per §3.6 + §3.9 the threshold is STRICT: ``rho > 0.85`` triggers the
    correction; ``rho == 0.85`` does NOT. Non-finite ``rho`` returns False
    (degenerate AR(1) estimate; do not apply correction silently).

    Parameters
    ----------
    rho : float
        AR(1) coefficient of the predictor.

    Returns
    -------
    bool

    References
    ----------
    Sealed pre-reg §3.6 + §3.9 + §11.1 line 740. Test: ``T10``.
    """
    if not math.isfinite(rho):
        return False
    return rho > STAMBAUGH_THRESHOLD
