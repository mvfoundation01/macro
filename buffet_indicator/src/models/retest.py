"""Annual re-test cadence — DRAFT_v4 §6.2 (seal 2a94417).

References
----------
- Sealed pre-reg §6.2: annual re-test fires once per calendar year on a
  pre-declared anchor date, producing PASS/FAIL/UNSTABLE per §12.
- Sealed pre-reg §11.1 line 736: function signature.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class RetestState:
    """Persisted state across annual re-tests.

    Attributes
    ----------
    last_retest_date : date | None
        Most recent re-test date; None if never run.
    last_verdict : str | None
        Most recent verdict (``"PASS"``/``"FAIL"``/``"UNSTABLE"``).
    anchor_month : int
        Calendar month (1..12) of the pre-declared anchor.
    anchor_day : int
        Calendar day of the pre-declared anchor.
    """

    last_retest_date: Optional[date]
    last_verdict: Optional[str]
    anchor_month: int
    anchor_day: int


@dataclass(frozen=True)
class RetestResult:
    """Result of an annual re-test step.

    Attributes
    ----------
    retest_status : str
        Per §12: ``"NOT_APPLICABLE"`` | ``"STABLE"`` | ``"UNSTABLE"``
        | ``"RETEST_SKIPPED_NO_NEW_DATA"`` | ``"RETEST_BLOCKED_DATA_UNAVAILABLE"``.
    new_verdict : str | None
        Verdict produced if re-test fired; None otherwise.
    next_state : RetestState
        Updated state for next call.
    """

    retest_status: str
    new_verdict: Optional[str]
    next_state: RetestState


def annual_retest_status(
    today: date,
    state: RetestState,
    data: pd.DataFrame,
) -> RetestResult:
    """Decide and (if applicable) run the annual re-test for ``today``.

    Per §6.2: re-test fires at most once per calendar year on/after the
    pre-declared anchor date. Idempotent on repeat calls within a year.
    Handles ``no-new-data`` and ``data-unavailable`` paths per §12 schema.

    Parameters
    ----------
    today : datetime.date
        Calendar date of the call.
    state : RetestState
        Persisted state from prior call.
    data : pd.DataFrame
        Latest panel; may be empty if data unavailable.

    Returns
    -------
    RetestResult

    References
    ----------
    Sealed pre-reg §6.2 + §11.1 line 736 + §12 schema.
    Tests: ``T16``, ``T17``.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
