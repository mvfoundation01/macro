"""§11.1 line 738 — v1.0 sample-count recomputation helper.
(No §11.2 test_id assigned; ancillary smoke-test for the §10.3-footnote helper.)
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.ingest.v1_sample_counts import (  # noqa: E402
    V1SampleCountsLoadError,
    collect_v1_realized_sample_counts,
)


def test_collect_v1_realized_sample_counts_loads_v1_branch() -> None:
    """Reads the sealed v1.0 regression CSV and returns the 12 expected cells."""
    try:
        df = collect_v1_realized_sample_counts(ref="spec/liquidity-composite-v1.0")
    except V1SampleCountsLoadError as exc:
        pytest.skip(f"v1.0 branch unavailable: {exc}")

    # 3 composites x 4 horizons = 12 cells.
    assert len(df) == 12
    expected_columns = {
        "composite",
        "horizon_months",
        "n_obs_insample",
        "n_obs_oos",
        "oos_split_date",
        "recomputation_status",
        "evaluable_v2",
    }
    assert expected_columns.issubset(df.columns)
    composites = set(df["composite"].tolist())
    assert composites == {"LC_FULL", "LC_TIER2", "LC_DEEP"}
    horizons = sorted(df["horizon_months"].unique().tolist())
    assert horizons == [12, 36, 60, 120]
    # All rows are 'deferred' per §10.3 footnote (n_obs_oos NaN).
    assert (df["recomputation_status"] == "deferred").all()
    assert df["n_obs_oos"].isna().all()
    assert (df["evaluable_v2"] == False).all()  # noqa: E712


def test_collect_v1_realized_sample_counts_raises_on_bad_ref() -> None:
    with pytest.raises(V1SampleCountsLoadError):
        collect_v1_realized_sample_counts(ref="not-a-real-ref-deadbeef")
