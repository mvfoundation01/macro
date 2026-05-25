"""Annual re-test cadence — DRAFT_v4 §6.2 (seal 2a94417).

References
----------
- Sealed pre-reg §6.2: annual re-test fires once per calendar year on a
  pre-declared anchor date, producing PASS / FAIL / UNSTABLE per §12.
- Sealed pre-reg §6.2.1: idempotency + no-new-data handling.
- Sealed pre-reg §11.1 line 736: function signature.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Optional

import pandas as pd


VALID_RETEST_STATUSES: frozenset[str] = frozenset(
    {
        "NOT_APPLICABLE",
        "STABLE",
        "UNSTABLE",
        "RETEST_SKIPPED_NO_NEW_DATA",
        "RETEST_BLOCKED_DATA_UNAVAILABLE",
    }
)
"""§12 retest_status enum (used by verdict JSON writer in Phase E)."""

VALID_VERDICTS: frozenset[str] = frozenset({"PASS", "FAIL", "UNSTABLE"})
"""§12 verdict enum."""


@dataclass(frozen=True)
class RetestState:
    """Persisted state across annual re-tests (§6.2.1).

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
    last_data_cutoff : date | None
        Most recent re-test's input data cutoff; None if never run.
    """

    last_retest_date: Optional[date]
    last_verdict: Optional[str]
    anchor_month: int
    anchor_day: int
    last_data_cutoff: Optional[date] = None


@dataclass(frozen=True)
class RetestResult:
    """Result of an annual re-test step (§6.2 / §12).

    Attributes
    ----------
    retest_status : str
        Per §12: one of :data:`VALID_RETEST_STATUSES`.
    new_verdict : str | None
        Verdict produced if re-test fired (one of :data:`VALID_VERDICTS`);
        None otherwise.
    next_state : RetestState
        Updated state for next call (idempotent if no-op).
    """

    retest_status: str
    new_verdict: Optional[str]
    next_state: RetestState


def _last_valid_day_of_month(year: int, month: int) -> int:
    """Return the last valid day-of-month for ``(year, month)``."""
    if month == 12:
        return 31
    next_first = datetime.date(year, month + 1, 1)
    last_of_month = next_first - datetime.timedelta(days=1)
    return last_of_month.day


def _scheduled_anchor(year: int, anchor_month: int, anchor_day: int) -> date:
    """Return ``date(year, anchor_month, anchor_day)`` snapped to a valid date.

    Handles Feb-29 anchors on non-leap years by snapping to Feb-28.
    """
    max_day = _last_valid_day_of_month(year, anchor_month)
    day = min(anchor_day, max_day)
    return datetime.date(year, anchor_month, day)


def _data_cutoff(data: pd.DataFrame) -> Optional[date]:
    """Extract a data_cutoff date from the panel.

    Convention (panel-builder responsibility):
    - ``data.attrs["data_cutoff"]`` (str/date/Timestamp) if present;
    - else the maximum DatetimeIndex value of ``data`` if monotonic;
    - else ``None``.
    """
    if data is None:
        return None
    attr_value: Any = getattr(data, "attrs", {}).get("data_cutoff")
    if attr_value is not None:
        ts = pd.Timestamp(attr_value)
        return ts.date()
    if hasattr(data, "index") and len(data.index) > 0:
        try:
            ts = pd.Timestamp(data.index.max())
            return ts.date()
        except (TypeError, ValueError):
            return None
    return None


def _verdict_from_data(data: pd.DataFrame) -> Optional[str]:
    """Extract a verdict string from ``data.attrs["verdict"]`` (test hook)."""
    attr_value: Any = getattr(data, "attrs", {}).get("verdict")
    if attr_value is None:
        return None
    s = str(attr_value)
    if s not in VALID_VERDICTS:
        raise ValueError(
            f"data.attrs['verdict']={s!r} not in {sorted(VALID_VERDICTS)!r}"
        )
    return s


def annual_retest_status(
    today: date,
    state: RetestState,
    data: pd.DataFrame,
) -> RetestResult:
    """Decide and (if applicable) run the annual re-test for ``today``.

    Per §6.2 / §6.2.1:
    - Fires at most once per calendar year on/after the pre-declared
      anchor date (``state.anchor_month``, ``state.anchor_day``).
    - Idempotent: a second call within the same year returns
      ``NOT_APPLICABLE`` with state unchanged.
    - If data is missing / empty: ``RETEST_BLOCKED_DATA_UNAVAILABLE``.
    - If data has no new realized returns since ``state.last_data_cutoff``:
      ``RETEST_SKIPPED_NO_NEW_DATA``.
    - Otherwise: extract verdict from ``data.attrs["verdict"]`` and
      compare to ``state.last_verdict``. Equal -> ``STABLE``; different
      -> ``UNSTABLE`` (reversal).

    Parameters
    ----------
    today : datetime.date
        Calendar date of the call.
    state : RetestState
        Persisted state from prior call.
    data : pd.DataFrame
        Latest panel; may be empty if data unavailable. Convention:
        ``data.attrs["verdict"]`` carries the freshly-computed verdict
        (writer-side, post evaluate_v2_criteria), and
        ``data.attrs["data_cutoff"]`` carries the cutoff date.

    Returns
    -------
    RetestResult

    References
    ----------
    Sealed pre-reg §6.2 + §6.2.1 + §11.1 line 736 + §12 schema.
    Tests: ``T16`` (idempotency / no-new-data), ``T17`` (reversal -> UNSTABLE).
    """
    if not isinstance(today, date):
        raise TypeError(f"today must be datetime.date, got {type(today).__name__}")

    scheduled = _scheduled_anchor(today.year, state.anchor_month, state.anchor_day)

    if today < scheduled:
        return RetestResult(
            retest_status="NOT_APPLICABLE",
            new_verdict=None,
            next_state=state,
        )

    # Idempotency: already ran for this year.
    if state.last_retest_date is not None and state.last_retest_date.year == today.year:
        return RetestResult(
            retest_status="NOT_APPLICABLE",
            new_verdict=None,
            next_state=state,
        )

    # Data availability check.
    if data is None or len(data) == 0:
        return RetestResult(
            retest_status="RETEST_BLOCKED_DATA_UNAVAILABLE",
            new_verdict=None,
            next_state=state,
        )

    cutoff = _data_cutoff(data)
    if cutoff is None:
        # Couldn't determine cutoff: treat as blocked (data shape unexpected).
        return RetestResult(
            retest_status="RETEST_BLOCKED_DATA_UNAVAILABLE",
            new_verdict=None,
            next_state=state,
        )

    if (
        state.last_data_cutoff is not None
        and cutoff <= state.last_data_cutoff
    ):
        return RetestResult(
            retest_status="RETEST_SKIPPED_NO_NEW_DATA",
            new_verdict=None,
            next_state=state,
        )

    # Compute / extract new verdict.
    new_verdict = _verdict_from_data(data)
    if new_verdict is None:
        # Verdict not provided in fixture / by caller; cannot resolve.
        return RetestResult(
            retest_status="RETEST_BLOCKED_DATA_UNAVAILABLE",
            new_verdict=None,
            next_state=state,
        )

    next_state = RetestState(
        last_retest_date=today,
        last_verdict=new_verdict,
        anchor_month=state.anchor_month,
        anchor_day=state.anchor_day,
        last_data_cutoff=cutoff,
    )

    if state.last_verdict is None:
        # First re-test: no prior verdict to compare; classify as STABLE.
        retest_status = "STABLE"
    elif state.last_verdict == new_verdict:
        retest_status = "STABLE"
    else:
        # Reversal across years -> UNSTABLE (§6.2).
        retest_status = "UNSTABLE"

    return RetestResult(
        retest_status=retest_status,
        new_verdict=new_verdict,
        next_state=next_state,
    )
