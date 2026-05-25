"""LC v2.0 verdict criteria evaluator — DRAFT_v4 §5 + §12 (seal 2a94417).

References
----------
- Sealed pre-reg §5: seven criteria (C1..C7), with strict ``>`` at criterion
  thresholds (e.g., C4 t > 1.65; Bonferroni denominator = 20).
- Sealed pre-reg §12: verdict JSON schema (PASS / FAIL / UNSTABLE).
- Sealed pre-reg §11.1 line 734: function signature.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class VerdictResult:
    """LC v2.0 verdict over the 12 (composite x horizon) panel.

    Attributes
    ----------
    verdict : str
        ``"PASS"`` | ``"FAIL"`` | ``"UNSTABLE"`` (§12).
    evidence_status : str
        ``"NORMAL"`` | ``"NO_EVALUABLE_CRITERIA"`` | ``"MIXED"`` (§12).
    n_pass_total : int
        Total criteria with ``counted_as == "PASS"`` (0..7).
    n_pass_predictive : int
        Predictive-criterion pass count (0..5).
    criteria : list
        Per-criterion records per §12 schema.
    """

    verdict: str
    evidence_status: str
    n_pass_total: int
    n_pass_predictive: int
    criteria: list[dict[str, Any]]


def evaluate_v2_criteria(panel: pd.DataFrame) -> VerdictResult:
    """Evaluate the seven v2.0 criteria over the panel.

    Per §5: C1..C7 with strict ``>``; C4 strict t-boundary at 1.65;
    Bonferroni denominator = 20 (5 components × 4 horizons).
    Per §12: produce verdict JSON-schema-valid result.

    Parameters
    ----------
    panel : pd.DataFrame
        12-row (composite x horizon) frame with per-cell regression,
        bootstrap, and gate columns.

    Returns
    -------
    VerdictResult

    References
    ----------
    Sealed pre-reg §5 + §12 + §11.1 line 734.
    Tests: ``T12``, ``T13``, ``T14``.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
