"""Tests for src.ingest.csv_loader."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src.ingest import csv_loader as cl
from src.ingest._base import (
    DataValidationError,
    FileFormatError,
    SourceMissingError,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_synthetic_daily_df(n: int = 150, start: str = "2020-01-01") -> pd.DataFrame:
    idx = pd.bdate_range(start=start, periods=n)
    close = pd.Series(range(1, n + 1), dtype="float64") + 100.0
    return pd.DataFrame(
        {
            "time": idx.strftime("%Y-%m-%d"),
            "open": close - 0.5,
            "high": close + 0.5,
            "low": close - 1.0,
            "close": close.values,
            "volume": [1000 + i for i in range(n)],
        }
    )


@pytest.fixture()
def csv_daily(tmp_path: Path) -> Path:
    df = _make_synthetic_daily_df(150)
    p = tmp_path / "fake_spx.csv"
    df.to_csv(p, index=False)
    return p


@pytest.fixture()
def xlsx_daily(tmp_path: Path) -> Path:
    df = _make_synthetic_daily_df(150)
    p = tmp_path / "fake_spx.xlsx"
    df.to_excel(p, index=False)
    return p


@pytest.fixture()
def xls_legacy(tmp_path: Path) -> Path:
    """Build a tiny .xls via xlwt-equivalent path: pandas writes .xls only via xlwt
    (unavailable here), so we fall back to a CSV but name it .xls -- the loader
    should still work if read_excel can handle it. To avoid that brittle test,
    we generate a valid .xls using openpyxl-on-xlsx is wrong; use xlrd's tiny
    library via raw bytes: simpler -- skip this in unit tests and use a real
    fixture file from disk if available."""
    pytest.importorskip("xlwt")
    import xlwt  # type: ignore

    df = _make_synthetic_daily_df(150)
    p = tmp_path / "fake_spx.xls"
    wb = xlwt.Workbook()
    sh = wb.add_sheet("Sheet1")
    cols = list(df.columns)
    for j, c in enumerate(cols):
        sh.write(0, j, c)
    for i, row in df.reset_index(drop=True).iterrows():
        for j, c in enumerate(cols):
            sh.write(i + 1, j, row[c])
    wb.save(str(p))
    return p


# ---------------------------------------------------------------------------
# C1 -- XLSX OHLCV happy path
# ---------------------------------------------------------------------------


def test_C1_xlsx_happy_path(xlsx_daily: Path) -> None:
    ts = cl.load_tradingview_file(xlsx_daily, expected_frequency="D")
    assert ts.file_format == "xlsx"
    assert "close" in ts.data.columns
    assert "open" in ts.data.columns
    assert "volume" in ts.data.columns
    assert len(ts.data) == 150
    assert ts.frequency == "D"


# ---------------------------------------------------------------------------
# C2 -- XLS legacy happy path
# ---------------------------------------------------------------------------


def test_C2_xls_happy_path(xls_legacy: Path) -> None:
    ts = cl.load_tradingview_file(xls_legacy, expected_frequency="D")
    assert ts.file_format == "xls"
    assert len(ts.data) == 150


# ---------------------------------------------------------------------------
# C3 -- CSV happy path
# ---------------------------------------------------------------------------


def test_C3_csv_happy_path(csv_daily: Path) -> None:
    ts = cl.load_tradingview_file(csv_daily, expected_frequency="D")
    assert ts.file_format == "csv"
    assert ts.data.index[0] == pd.Timestamp("2020-01-01")
    assert ts.symbol  # default to file stem if no expected_symbol


# ---------------------------------------------------------------------------
# C4 -- ISO 8601 with Z normalized to midnight
# ---------------------------------------------------------------------------


def test_C4_iso_z_normalized(tmp_path: Path) -> None:
    n = 120
    idx = pd.bdate_range("2022-01-03", periods=n)
    df = pd.DataFrame(
        {
            "time": [d.strftime("%Y-%m-%dT09:30:00Z") for d in idx],
            "close": [100.0 + i for i in range(n)],
        }
    )
    p = tmp_path / "iso.csv"
    df.to_csv(p, index=False)

    ts = cl.load_tradingview_file(p, expected_frequency="D")
    # All timestamps must be midnight UTC-naive.
    assert (ts.data.index.hour == 0).all()
    assert (ts.data.index.minute == 0).all()
    assert ts.data.index.tz is None


# ---------------------------------------------------------------------------
# C5 -- Excel serial date (numeric)
# ---------------------------------------------------------------------------


def test_C5_excel_serial_date(tmp_path: Path) -> None:
    # 45306 -> 2024-01-15
    n = 120
    serial0 = 45306
    df = pd.DataFrame(
        {
            "time": [serial0 + i for i in range(n)],
            "close": [200.0 + i for i in range(n)],
        }
    )
    p = tmp_path / "serial.xlsx"
    df.to_excel(p, index=False)

    ts = cl.load_tradingview_file(p, expected_frequency="D")
    assert ts.data.index[0] == pd.Timestamp("2024-01-15")


# ---------------------------------------------------------------------------
# C6 -- filename with comma + space
# ---------------------------------------------------------------------------


def test_C6_filename_with_comma_space(tmp_path: Path) -> None:
    df = _make_synthetic_daily_df(150)
    p = tmp_path / "SP_SPX, 1D.csv"
    df.to_csv(p, index=False)
    ts = cl.load_tradingview_file(p, expected_frequency="D")
    assert len(ts.data) == 150


# ---------------------------------------------------------------------------
# C7 -- missing close column -> FileFormatError
# ---------------------------------------------------------------------------


def test_C7_missing_close(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "time": pd.bdate_range("2020-01-01", periods=150).strftime("%Y-%m-%d"),
            "open": list(range(150)),
        }
    )
    p = tmp_path / "no_close.csv"
    df.to_csv(p, index=False)
    with pytest.raises(FileFormatError):
        cl.load_tradingview_file(p, expected_frequency="D")


# ---------------------------------------------------------------------------
# C8 -- duplicates deduped with warning
# ---------------------------------------------------------------------------


def test_C8_duplicates_deduped(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    df = _make_synthetic_daily_df(150)
    df = pd.concat([df, df.iloc[[10, 20, 30]]], ignore_index=True)
    p = tmp_path / "dups.csv"
    df.to_csv(p, index=False)
    with caplog.at_level(logging.WARNING, logger="buffett.ingest.csv"):
        ts = cl.load_tradingview_file(p, expected_frequency="D")
    assert len(ts.data) == 150
    assert any("duplicate" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# C9 -- 30-day gap fails
# ---------------------------------------------------------------------------


def test_C9_gap_fails_validation(tmp_path: Path) -> None:
    df = _make_synthetic_daily_df(150)
    # Drop a 30-day chunk in the middle.
    df = pd.concat([df.iloc[:50], df.iloc[80:]], ignore_index=True)
    p = tmp_path / "gap.csv"
    df.to_csv(p, index=False)
    with pytest.raises(DataValidationError):
        cl.load_tradingview_file(p, expected_frequency="D", max_gap_days=14)


# ---------------------------------------------------------------------------
# C10 -- load_tradingview_inputs require_all=False handles missing files
# ---------------------------------------------------------------------------


def test_C10_inputs_missing_optional(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Point all spec paths at non-existent files; require_all=False should not raise.
    fake_dir = tmp_path / "no_files_here"
    fake_dir.mkdir()
    monkeypatch.setitem(cl._TV_SPEC["spx"], "path", fake_dir / "x.csv")
    monkeypatch.setitem(cl._TV_SPEC["spxtr"], "path", fake_dir / "y.csv")
    monkeypatch.setitem(cl._TV_SPEC["wilshire_tv"], "path", fake_dir / "z.csv")
    monkeypatch.setitem(cl._TV_SPEC["gdp_backup"], "path", fake_dir / "w.csv")
    out = cl.load_tradingview_inputs(require_all=False)
    assert out == {}

    with pytest.raises(SourceMissingError):
        cl.load_tradingview_inputs(require_all=True)
