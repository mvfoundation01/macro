"""Tests for src.transform.align_monthly."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.transform.align_monthly import (
    align_to_monthly_grid,
    resample_daily_to_monthly,
    resample_quarterly_backtest,
    resample_quarterly_descriptive,
)


def test_A1_daily_to_monthly_uses_last_value() -> None:
    idx = pd.bdate_range("2024-01-01", "2024-03-31")
    values = [float(i) for i in range(len(idx))]
    s = pd.Series(values, index=idx, name="x")
    out = resample_daily_to_monthly(s, agg="last")
    # January's month-end value should be the value at the last business day of Jan.
    jan_end = out.index[0]
    assert jan_end.month == 1
    expected_last_jan_bday = s.loc[s.index <= jan_end].iloc[-1]
    assert out.iloc[0] == pytest.approx(expected_last_jan_bday)


def test_A2_quarterly_descriptive_within_quarter() -> None:
    # Quarterly series spanning multiple quarters: Q1, Q2, Q3 2025.
    s = pd.Series(
        [100.0, 110.0, 120.0],
        index=pd.DatetimeIndex(
            [
                pd.Timestamp("2025-01-01"),
                pd.Timestamp("2025-04-01"),
                pd.Timestamp("2025-07-01"),
            ]
        ),
        name="gdp",
    )
    out = resample_quarterly_descriptive(s)
    # May 2025 (inside Q2 2025) should have Q2's value once Q2's quarter-end has occurred.
    may_end = pd.Timestamp("2025-05-31")
    assert may_end in out.index
    assert out.loc[may_end] == pytest.approx(110.0)
    # August 2025 (inside Q3 2025) should have Q3's value.
    aug_end = pd.Timestamp("2025-08-31")
    assert out.loc[aug_end] == pytest.approx(120.0)


def test_A3_quarterly_backtest_30d_lag() -> None:
    # Q4 2024 = 2024-10-01; Q1 2025 = 2025-01-01.
    s = pd.Series(
        [80.0, 100.0],
        index=pd.DatetimeIndex([pd.Timestamp("2024-10-01"), pd.Timestamp("2025-01-01")]),
        name="gdp",
    )
    out = resample_quarterly_backtest(s, pd.Timedelta(days=30))
    # 2025-03-31: Q1 2025 ends 2025-03-31; released 2025-04-30 -> NOT yet available.
    # So 2025-03-31 should use Q4 2024 (released 2025-01-30, available since then).
    if pd.Timestamp("2025-03-31") in out.index:
        assert out.loc[pd.Timestamp("2025-03-31")] == pytest.approx(80.0)
    # 2025-04-30: Q1 2025 (released 2025-04-30) IS available.
    if pd.Timestamp("2025-04-30") in out.index:
        assert out.loc[pd.Timestamp("2025-04-30")] == pytest.approx(100.0)


def test_A4_quarterly_backtest_75d_lag() -> None:
    # Q1 2025 ends 2025-03-31; available 2025-06-14 (+ 75d).
    s = pd.Series(
        [100.0],
        index=pd.DatetimeIndex([pd.Timestamp("2025-01-01")]),
        name="z1",
    )
    out = resample_quarterly_backtest(s, pd.Timedelta(days=75))
    # 2025-06-30 should have Q1 2025's value (06-14 <= 06-30).
    if pd.Timestamp("2025-06-30") in out.index:
        assert out.loc[pd.Timestamp("2025-06-30")] == pytest.approx(100.0)


def test_A5_descriptive_vs_backtest_diverge_in_tail() -> None:
    s = pd.Series(
        [80.0, 90.0, 100.0],
        index=pd.DatetimeIndex(
            [
                pd.Timestamp("2024-10-01"),
                pd.Timestamp("2025-01-01"),
                pd.Timestamp("2025-04-01"),
            ]
        ),
        name="gdp",
    )
    desc = resample_quarterly_descriptive(s)
    bt = resample_quarterly_backtest(s, pd.Timedelta(days=30))
    common = desc.index.intersection(bt.index)
    # Within shared dates, the backtest version is a 1-quarter-lagged subset of desc.
    diff = (desc.loc[common] != bt.loc[common]).sum()
    assert diff >= 1  # at least one month differs


def test_A6_align_returns_monthly_indexed_dataframe() -> None:
    daily = pd.Series(
        [100.0 + i for i in range(252)],
        index=pd.bdate_range("2024-01-01", periods=252),
        name="wilshire_usd_t",
    )
    qly = pd.Series(
        [80.0, 81.0, 82.0, 83.0],
        index=pd.DatetimeIndex(
            [
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-04-01"),
                pd.Timestamp("2024-07-01"),
                pd.Timestamp("2024-10-01"),
            ]
        ),
        name="gdp_t",
    )
    df = align_to_monthly_grid(
        {"wilshire_usd_t": daily, "gdp_t": qly}, view="descriptive"
    )
    assert isinstance(df, pd.DataFrame)
    assert df.index.is_monotonic_increasing
    # All index values should be month-ends.
    assert (df.index.is_month_end).all()


def test_A7_empty_input_returns_empty_dataframe() -> None:
    df = align_to_monthly_grid({}, view="descriptive")
    assert df.empty


def test_A8_pre1947_nan_in_gdp_not_dropped() -> None:
    # Shiller monthly going back to 1900 + GDP starting 1947.
    monthly_idx = pd.date_range("1900-01-31", "1950-12-31", freq="ME")
    shiller = pd.Series([10.0 + i for i in range(len(monthly_idx))], index=monthly_idx, name="cape")
    qly = pd.Series(
        [80.0, 81.0],
        index=pd.DatetimeIndex([pd.Timestamp("1947-01-01"), pd.Timestamp("1947-04-01")]),
        name="gdp_t",
    )
    df = align_to_monthly_grid(
        {"cape": shiller, "gdp_t": qly}, view="descriptive"
    )
    # Rows before 1947 should still be present (only gdp_t is NaN there).
    pre_1947 = df.loc[df.index < pd.Timestamp("1947-01-31")]
    assert not pre_1947.empty
    assert pre_1947["gdp_t"].isna().all()
    assert pre_1947["cape"].notna().all()
