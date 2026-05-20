"""v11.0 acceptance tests for margin debt 12M log growth."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.transform.margin_debt_compute import (
    REQUIRED_COLUMNS,
    compute_margin_debt_growth,
    latest_summary,
)


@pytest.fixture(scope="module")
def md() -> pd.DataFrame:
    return compute_margin_debt_growth()


def test_margin_debt_loads_from_xlsx(md: pd.DataFrame) -> None:
    assert isinstance(md, pd.DataFrame)
    for col in REQUIRED_COLUMNS:
        assert col in md.columns, f"missing column {col!r}"
    assert md.attrs.get("variant_key") == "margin_debt_growth"
    assert md.attrs.get("direction") == "standard"


def test_margin_debt_growth_first_12_rows_nan(md: pd.DataFrame) -> None:
    """The 12-month log-growth must be NaN for the first 12 observations."""
    head = md.head(12)
    assert head["growth_12m"].isna().all()
    # Row 13 onward must have at least some non-NaN.
    assert md.iloc[12:]["growth_12m"].notna().any()


def test_margin_debt_signal_equals_growth_12m(md: pd.DataFrame) -> None:
    """signal must equal growth_12m exactly (no negation, no scaling)."""
    err = (md["signal"] - md["growth_12m"]).abs().max(skipna=True)
    assert err < 1e-12 or np.isnan(err)


def test_margin_debt_2007_2009_growth_pattern(md: pd.DataFrame) -> None:
    """Peak positive growth in 2007, deeply negative in 2009 (classic cycle)."""
    peak_2007 = md.loc["2007-04-30":"2007-10-31", "growth_12m"].max()
    trough_2009 = md.loc["2008-12-31":"2009-12-31", "growth_12m"].min()
    assert peak_2007 > 0.30, (
        f"2007 12M growth peak = {peak_2007:.3f}; expected > 0.30 log (~35% YoY)."
    )
    assert trough_2009 < -0.30, (
        f"2009 12M growth trough = {trough_2009:.3f}; expected < -0.30 log."
    )


def test_margin_debt_log_level_matches_log_of_level(md: pd.DataFrame) -> None:
    err = (md["log_level"] - np.log(md["margin_debt_level"])).abs().max()
    assert err < 1e-12


def test_latest_summary_keys(md: pd.DataFrame) -> None:
    s = latest_summary(md)
    assert {"date", "level_usd", "growth_12m_log", "growth_12m_pct", "signal"} == set(
        s.keys()
    )
    assert s["level_usd"] > 0
