"""§11.2 T16+T17 — annual re-test cadence. DRAFT_v4 §6.2 (seal 2a94417)."""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402

from src.models.retest import (  # noqa: E402
    VALID_RETEST_STATUSES,
    VALID_VERDICTS,
    RetestResult,
    RetestState,
    annual_retest_status,
)


def _panel_with(
    verdict: str | None,
    cutoff: datetime.date | None,
    *,
    rows: int = 12,
) -> pd.DataFrame:
    """Construct a tiny panel with attrs['verdict']/attrs['data_cutoff']."""
    idx = pd.date_range("2025-01-31", periods=rows, freq="ME")
    df = pd.DataFrame({"x": range(rows)}, index=idx)
    if verdict is not None:
        df.attrs["verdict"] = verdict
    if cutoff is not None:
        df.attrs["data_cutoff"] = pd.Timestamp(cutoff)
    return df


def test_annual_retest_fires_once_per_year() -> None:
    """Idempotency: repeat calls within a year produce no new verdict;
    no-new-data and date-trigger paths handled.

    References: DRAFT_v4 §6.2 + sealed pre-reg §11.2 T16.
    """
    state = RetestState(
        last_retest_date=None,
        last_verdict="PASS",
        anchor_month=6,
        anchor_day=1,
        last_data_cutoff=datetime.date(2026, 5, 31),
    )

    # Before anchor in current year -> NOT_APPLICABLE.
    pre_anchor = datetime.date(2027, 5, 31)
    r1 = annual_retest_status(
        pre_anchor, state, _panel_with("PASS", datetime.date(2027, 5, 31))
    )
    assert r1.retest_status == "NOT_APPLICABLE"
    assert r1.new_verdict is None
    assert r1.next_state == state  # state unchanged

    # On or after anchor -> fires (first run of the year).
    on_anchor = datetime.date(2027, 6, 1)
    r2 = annual_retest_status(
        on_anchor, state, _panel_with("PASS", datetime.date(2027, 6, 1))
    )
    assert r2.retest_status == "STABLE"  # verdict matches last_verdict
    assert r2.new_verdict == "PASS"
    assert r2.next_state.last_retest_date == on_anchor

    # Re-call same year (idempotency) -> NOT_APPLICABLE.
    r3 = annual_retest_status(
        datetime.date(2027, 7, 1),
        r2.next_state,
        _panel_with("FAIL", datetime.date(2027, 7, 1)),  # would have reversed
    )
    assert r3.retest_status == "NOT_APPLICABLE"
    assert r3.new_verdict is None
    # State preserved across idempotent calls.
    assert r3.next_state == r2.next_state

    # No new data path (data cutoff <= last cutoff) -> RETEST_SKIPPED_NO_NEW_DATA.
    state_with_cut = RetestState(
        last_retest_date=datetime.date(2026, 6, 1),
        last_verdict="PASS",
        anchor_month=6,
        anchor_day=1,
        last_data_cutoff=datetime.date(2027, 5, 31),
    )
    r4 = annual_retest_status(
        datetime.date(2027, 6, 15),
        state_with_cut,
        _panel_with("PASS", datetime.date(2027, 5, 31)),  # stale cutoff
    )
    assert r4.retest_status == "RETEST_SKIPPED_NO_NEW_DATA"
    assert r4.new_verdict is None

    # Empty data -> RETEST_BLOCKED_DATA_UNAVAILABLE.
    empty = pd.DataFrame()
    r5 = annual_retest_status(
        datetime.date(2027, 6, 15), state_with_cut, empty
    )
    assert r5.retest_status == "RETEST_BLOCKED_DATA_UNAVAILABLE"
    assert r5.new_verdict is None


def test_retest_unstable_verdict_is_schema_valid() -> None:
    """Reversal fixture -> UNSTABLE verdict, schema validates per §12.

    NEW per Codex round-2 New-6.
    References: DRAFT_v4 §6.2 + §12 + sealed pre-reg §11.2 T17.
    """
    # Prior verdict PASS at 2026-06-01; new fixture says FAIL -> UNSTABLE.
    state = RetestState(
        last_retest_date=datetime.date(2026, 6, 1),
        last_verdict="PASS",
        anchor_month=6,
        anchor_day=1,
        last_data_cutoff=datetime.date(2026, 5, 31),
    )
    today = datetime.date(2027, 6, 1)
    result = annual_retest_status(
        today,
        state,
        _panel_with("FAIL", datetime.date(2027, 5, 31)),
    )
    assert isinstance(result, RetestResult)
    assert result.retest_status == "UNSTABLE"
    assert result.new_verdict == "FAIL"
    # Schema validity: enums per §12.
    assert result.retest_status in VALID_RETEST_STATUSES
    assert result.new_verdict in VALID_VERDICTS
    assert result.next_state.last_retest_date == today
    assert result.next_state.last_verdict == "FAIL"
    # Reverse-back fixture (FAIL -> PASS) should also yield UNSTABLE.
    state_post = result.next_state
    reverse_back = annual_retest_status(
        datetime.date(2028, 6, 1),
        state_post,
        _panel_with("PASS", datetime.date(2028, 5, 31)),
    )
    assert reverse_back.retest_status == "UNSTABLE"
    assert reverse_back.new_verdict == "PASS"
