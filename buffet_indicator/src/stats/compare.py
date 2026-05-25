"""Threshold comparison helper — DRAFT_v4 §5 (seal 2a94417).

References
----------
- Sealed pre-reg §5: criterion comparison helper (strict ``>``/``<``).
- Sealed pre-reg §11.1 line 737: function signature.
"""
from __future__ import annotations


def compare_threshold(
    value: float,
    op: str,
    threshold: float,
    *,
    on_nan: str = "fail",
) -> bool:
    """Compare ``value`` to ``threshold`` under operator ``op``.

    Supported operators (canonical): ``">"``, ``">="``, ``"<"``, ``"<="``.
    Per §5 the canonical operators are STRICT for criterion thresholds
    (e.g., C4 uses strict ``>`` at ``t=1.65``).

    Parameters
    ----------
    value : float
        Left-hand value (the realized statistic).
    op : str
        Comparison operator: one of ``{">", ">=", "<", "<="}``.
    threshold : float
        Right-hand value (the spec threshold).
    on_nan : str, default "fail"
        Behaviour when ``value`` is NaN. ``"fail"`` returns False;
        other modes per implementation phase.

    Returns
    -------
    bool

    References
    ----------
    Sealed pre-reg §5 + §11.1 line 737.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
