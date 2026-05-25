"""HAC (Newey-West) lag helper — DRAFT_v4 §3.2 (seal 2a94417).

References
----------
- Sealed pre-reg §3.2: HAC lag = ``horizon_months - 1`` (v1.0-inherited formula).
- Sealed pre-reg §11.1 line 729: function signature.
"""
from __future__ import annotations


def compute_hac_lag(horizon_months: int) -> int:
    """Return the Newey-West HAC lag for a forecast horizon.

    Per §3.2 the canonical formula is ``hac_lag = horizon_months - 1``
    (inherited from v1.0). For ``horizon_months = 12`` this yields 11;
    for ``120`` it yields 119.

    Parameters
    ----------
    horizon_months : int
        Forecast horizon in months (positive integer).

    Returns
    -------
    int
        Newey-West HAC lag in months.

    References
    ----------
    Sealed pre-reg §3.2 + §11.1 line 729.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
