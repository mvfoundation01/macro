"""Threshold comparison helper — DRAFT_v4 §3.9 + §5 (seal 2a94417).

References
----------
- Sealed pre-reg §3.9: canonical comparator table for criterion / gate
  thresholds. All comparators routed through a single helper
  ``compare_threshold(value, op, threshold, *, on_nan="fail")``.
- Sealed pre-reg §11.1 line 737: function signature.
"""
from __future__ import annotations

import math


SUPPORTED_OPERATORS: frozenset[str] = frozenset({">", ">=", "<", "<=", "==", "!="})


def compare_threshold(
    value: float,
    op: str,
    threshold: float,
    *,
    on_nan: str = "fail",
) -> bool:
    """Compare ``value`` to ``threshold`` under operator ``op``.

    Supported operators per §3.9 comparator table:
    ``{">", ">=", "<", "<=", "==", "!="}``. Per §5, criterion thresholds
    use STRICT ``>``/``<`` (e.g., C4 strict ``>`` at ``t=1.65``).

    Parameters
    ----------
    value : float
        Left-hand value (the realized statistic).
    op : str
        Comparison operator.
    threshold : float
        Right-hand value (the spec threshold).
    on_nan : str, default ``"fail"``
        Behaviour when ``value`` is NaN. ``"fail"`` returns False;
        ``"pass"`` returns True; ``"raise"`` raises ``ValueError``.

    Returns
    -------
    bool

    Raises
    ------
    ValueError
        If ``op`` is not in :data:`SUPPORTED_OPERATORS`, if ``on_nan`` is
        not one of ``{"fail", "pass", "raise"}``, or if ``on_nan="raise"``
        and ``value`` is NaN.

    References
    ----------
    Sealed pre-reg §3.9 + §5 + §11.1 line 737.
    """
    if op not in SUPPORTED_OPERATORS:
        raise ValueError(
            f"unsupported operator {op!r}; expected one of "
            f"{sorted(SUPPORTED_OPERATORS)!r}"
        )
    if on_nan not in {"fail", "pass", "raise"}:
        raise ValueError(
            f"on_nan must be one of {{'fail', 'pass', 'raise'}}, got {on_nan!r}"
        )

    val = float(value)
    thr = float(threshold)
    if math.isnan(val):
        if on_nan == "raise":
            raise ValueError(f"value is NaN; op={op!r} threshold={thr!r}")
        return on_nan == "pass"

    if op == ">":
        return val > thr
    if op == ">=":
        return val >= thr
    if op == "<":
        return val < thr
    if op == "<=":
        return val <= thr
    if op == "==":
        return val == thr
    # op == "!="
    return val != thr
