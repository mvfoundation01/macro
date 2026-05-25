"""HAC (Newey-West) lag helper — DRAFT_v4 §3.5 (seal 2a94417).

References
----------
- Sealed pre-reg §3.5: HAC lag = ``horizon_months - 1`` (v1.0-inherited
  formula). For h=12 → 11, h=120 → 119.
- Sealed pre-reg §11.1 line 729: function signature.
"""
from __future__ import annotations


def compute_hac_lag(horizon_months: int) -> int:
    """Return the Newey-West HAC lag for a forecast horizon.

    Per §3.5 the canonical formula is ``hac_lag = horizon_months - 1``
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

    Raises
    ------
    TypeError
        If ``horizon_months`` is not an ``int``.
    ValueError
        If ``horizon_months`` is not a positive integer.

    References
    ----------
    Sealed pre-reg §3.5 + §11.1 line 729.
    """
    if not isinstance(horizon_months, (int,)) or isinstance(horizon_months, bool):
        raise TypeError(
            f"horizon_months must be int, got {type(horizon_months).__name__}"
        )
    if horizon_months < 1:
        raise ValueError(
            f"horizon_months must be >= 1, got {horizon_months}"
        )
    return horizon_months - 1
