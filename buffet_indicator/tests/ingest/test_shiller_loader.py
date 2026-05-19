"""Tests for src.ingest.shiller_loader."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from src.config import SHILLER_XLS
from src.ingest import shiller_loader as sl
from src.ingest._base import FileFormatError


# ---------------------------------------------------------------------------
# Helpers -- hand-crafted minimal fixture.
# ---------------------------------------------------------------------------


REQUIRED_HEADERS = [
    "Date",            # date_fraction
    "S&P Comp. (P)",   # price_nominal
    "Dividend",        # dividend_nominal
    "Earnings",        # earnings_nominal
    "CPI",             # cpi
    "Long Interest Rate GS10",  # long_rate_gs10
    "Real Price",      # real_price
    "Real Dividend",   # real_dividend
    "Real Total Return Price",  # real_total_return
    "Real Earnings",   # real_earnings
    "CAPE",            # cape
]


def _build_fixture_dataframe(n_months: int = 1900, *, percent_rates: bool = True) -> pd.DataFrame:
    """Build a synthetic Shiller-shaped sheet with header row at row 8."""
    # Junk rows above the header (7 of them, header at index 7 -> row 8 in 1-indexed).
    rows: list[list[object]] = []
    for _ in range(7):
        rows.append(["" for _ in REQUIRED_HEADERS])
    rows.append(list(REQUIRED_HEADERS))

    # Generate monthly data starting Jan 1871.
    year = 1871
    month = 1
    for i in range(n_months):
        date_token = f"{year}.{month:02d}"
        price = 100.0 + 0.05 * i
        div = 2.0 + 0.01 * i
        earn = 5.0 + 0.02 * i
        cpi = 10.0 + 0.01 * i
        rate = (4.5 if percent_rates else 0.045) + 0.001 * (i % 5)
        rp = 200.0 + 0.1 * i
        rd = 4.0 + 0.02 * i
        rtr = 300.0 + 0.2 * i
        re_v = 10.0 + 0.05 * i
        cape = 15.0 + 0.02 * i if i >= 120 else float("nan")  # CAPE NaN before 1881
        rows.append([date_token, price, div, earn, cpi, rate, rp, rd, rtr, re_v, cape])
        month += 1
        if month == 13:
            month = 1
            year += 1
    return pd.DataFrame(rows)


def _write_xlsx(df: pd.DataFrame, p: Path) -> Path:
    df.to_excel(p, index=False, header=False)
    return p


# ---------------------------------------------------------------------------
# S1 -- XLS happy path (real file; opt-in)
# ---------------------------------------------------------------------------


def test_S1_real_xls_if_present() -> None:
    if not SHILLER_XLS.exists():
        pytest.skip(f"Shiller file not present at {SHILLER_XLS}")
    d = sl.load_shiller(SHILLER_XLS)
    assert d.file_format in ("xls", "xlsx")
    assert len(d.data) > 1500
    assert d.start_date <= pd.Timestamp("1871-03-31")


# ---------------------------------------------------------------------------
# S2 -- XLSX happy path
# ---------------------------------------------------------------------------


def test_S2_xlsx_happy_path(tmp_path: Path) -> None:
    df = _build_fixture_dataframe(1900)
    p = _write_xlsx(df, tmp_path / "synthetic_shiller.xlsx")
    d = sl.load_shiller(p, sheet_name=0)
    assert d.file_format == "xlsx"
    assert len(d.data) == 1900
    assert d.start_date == pd.Timestamp("1871-01-31")


# ---------------------------------------------------------------------------
# Direct _parse_date tests S3-S6.
# ---------------------------------------------------------------------------


def test_S3_parse_jan_first_row() -> None:
    assert sl._parse_date("1871.01", None) == pd.Timestamp("1871-01-31")


def test_S4_parse_october_two_digit() -> None:
    assert sl._parse_date("1871.10", 9) == pd.Timestamp("1871-10-31")


def test_S5_parse_october_ambiguous_with_context() -> None:
    # Excel sometimes displays 1871.10 as 1871.1 (numeric).
    assert sl._parse_date(1871.1, 9) == pd.Timestamp("1871-10-31")


def test_S6_parse_first_row_jan_default() -> None:
    assert sl._parse_date(1871.1, None) == pd.Timestamp("1871-01-31")


# ---------------------------------------------------------------------------
# S7 -- header at row 8 found
# ---------------------------------------------------------------------------


def test_S7_header_row_8_found(tmp_path: Path) -> None:
    df = _build_fixture_dataframe(1900)
    p = _write_xlsx(df, tmp_path / "header_row_test.xlsx")
    d = sl.load_shiller(p, sheet_name=0)
    # If the wrong header row had been picked, the loader would have raised
    # FileFormatError, so reaching here is the check.
    assert len(d.data) == 1900


# ---------------------------------------------------------------------------
# S8 -- required column missing -> FileFormatError
# ---------------------------------------------------------------------------


def test_S8_missing_required_column(tmp_path: Path) -> None:
    df = _build_fixture_dataframe(1900)
    # Remove CAPE column entirely.
    df = df.drop(columns=[df.columns[-1]])
    p = _write_xlsx(df, tmp_path / "missing_col.xlsx")
    with pytest.raises(FileFormatError):
        sl.load_shiller(p, sheet_name=0)


# ---------------------------------------------------------------------------
# S9 -- long rate detected as percentage and converted
# ---------------------------------------------------------------------------


def test_S9_long_rate_percent_to_decimal(tmp_path: Path) -> None:
    df = _build_fixture_dataframe(1900, percent_rates=True)
    p = _write_xlsx(df, tmp_path / "percent_rate.xlsx")
    d = sl.load_shiller(p, sheet_name=0)
    first = float(d.data["long_rate_gs10"].dropna().iloc[0])
    assert first < 1.0  # was ~4.5, now ~0.045


# ---------------------------------------------------------------------------
# S10 -- @integration: real ie_data.xls present
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_S10_real_ie_data() -> None:
    if os.environ.get("INTEGRATION_TESTS") != "1":
        pytest.skip("INTEGRATION_TESTS!=1")
    if not SHILLER_XLS.exists():
        pytest.skip(f"Shiller file not present at {SHILLER_XLS}")
    d = sl.load_shiller(SHILLER_XLS)
    assert len(d.data) >= 1850
    # CAPE NaN before 1881 (10-year window starts then).
    pre_1881 = d.data.loc[d.data.index < pd.Timestamp("1881-01-01")]
    assert pre_1881["cape"].isna().all()
