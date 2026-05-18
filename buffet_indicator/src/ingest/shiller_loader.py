"""Loader for Robert Shiller's ``ie_data.xls`` (Yale).

The legacy ``.xls`` format requires ``xlrd``; the modern ``.xlsx`` mirror uses
``openpyxl``. Both are supported.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from src.config import SHILLER_XLS
from src.ingest._base import (
    FileFormatError,
    SourceMissingError,
    DataValidationError,
    get_logger,
    sha256_file,
    utcnow,
)

logger = get_logger("buffett.ingest.shiller")


# ---------------------------------------------------------------------------
# Column header regex map (Appendix A.1)
# ---------------------------------------------------------------------------


SHILLER_COLUMN_PATTERNS: dict[str, str] = {
    # Date column = primary YYYY.MM column. NOT "Date Fraction" (decimal-year alt).
    "date_fraction": r"^Date$|^Date\s+Fraction$",
    # Real Shiller composite header: "Comp. P" -- nominal S&P composite.
    "price_nominal": r"^S&?P\s*Comp\.?\s*P$|^Comp\.?\s*P$|^S&?P\s*Comp.*\(P\)$|^Price$|^P$",
    # Real header: "Dividend D"
    "dividend_nominal": r"^Dividend\s*D$|^Dividend(\s*\(D\))?$|^D$",
    # Real header: "Earnings E"
    "earnings_nominal": r"^Earnings\s*E$|^Earnings(\s*\(E\))?$|^E$",
    # Real header: "Index CPI" (Consumer Price Index)
    "cpi": r"^CPI$|^Consumer\s*Price\s*Index\s*CPI$|^Index\s*CPI$",
    # Real header: "Interest Rate GS10" (preceded by "Long")
    "long_rate_gs10": (
        r"Long.*Interest.*Rate.*GS10|"
        r"^Rate\s*GS10$|^GS10$|^Long Interest Rate$|"
        r"^Interest\s*Rate\s*GS10$|"
        r"Long\s*Interest\s*Rate\s*GS10"
    ),
    "real_price": r"^Real\s*Price$",
    "real_dividend": r"^Real\s*Dividend$",
    # Real header: "Return Price" (with "Real Total" above)
    "real_total_return": (
        r"^Real\s*Total\s*Return\s*Price$|"
        r"^Real\s*Total\s*Return Price$|"
        r"^Return\s*Price$"
    ),
    "real_earnings": r"^Real\s*Earnings$",
    # Real header for CAPE column: "Earnings Ratio P/E10 or CAPE" (density filter
    # strips off the "Cyclically Adjusted Price" banner prefix that comes 3 rows up).
    "cape": (
        r"^CAPE$|^P/?E10$|"
        r"^P/?E10\s*or\s*CAPE$|"
        r"^Earnings\s*Ratio\s*P/?E10\s*or\s*CAPE$|"
        r"^Cyclically\s*Adjusted.*P/?E10\s*or\s*CAPE$"
    ),
    # Real header: "Earnings Ratio TR P/E10 or TR CAPE"
    "tr_cape": (
        r"^TR\s*CAPE$|"
        r"^TR\s*P/?E10\s*or\s*TR\s*CAPE$|"
        r"^Earnings\s*Ratio\s*TR\s*P/?E10\s*or\s*TR\s*CAPE$"
    ),
    # Real header: "Excess CAPE Yield" (composite)
    "excess_cape_yield": r"^Excess\s*CAPE\s*Yield$|^CAPE\s*Yield$",
}

REQUIRED = {
    "date_fraction",
    "price_nominal",
    "dividend_nominal",
    "earnings_nominal",
    "cpi",
    "long_rate_gs10",
    "real_price",
    "real_dividend",
    "real_total_return",
    "real_earnings",
    "cape",
}


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShillerData:
    data: pd.DataFrame
    available_columns: tuple[str, ...]
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    file_format: Literal["xls", "xlsx"]
    retrieval_timestamp: datetime
    load_timestamp: datetime
    sha256: str


# ---------------------------------------------------------------------------
# Date parsing (the October trap)
# ---------------------------------------------------------------------------


def _parse_date(raw: object, prev_month: int | None) -> pd.Timestamp:
    """Decode Shiller's ``YYYY.MM`` encoding, disambiguating the .1 vs .10 trap."""
    s = str(raw).strip()
    if "." not in s:
        year = int(float(s))
        month = 1 if prev_month is None else min(12, prev_month + 1)
        return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

    year_str, frac_str = s.split(".", 1)
    year = int(year_str)
    if len(frac_str) == 1:
        digit = int(frac_str)
        if prev_month == 9 and digit == 1:
            month = 10
        elif prev_month is None:
            month = digit
        elif prev_month == 12 and digit == 1:
            month = 1
        else:
            month = digit
    elif len(frac_str) == 2:
        month = int(frac_str)
    else:
        # Partial-month fraction (e.g. 2026.04167 ~ mid-May)
        frac = float("0." + frac_str)
        month = max(1, min(12, int(round(frac * 12)) + 1))

    month = max(1, min(12, month))
    return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)


# ---------------------------------------------------------------------------
# Header detection + column mapping
# ---------------------------------------------------------------------------


def _is_blankish(v: object) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and pd.isna(v):
        return True
    s = str(v).strip()
    return s == "" or s.lower() == "nan" or s.lower().startswith("unnamed")


def _find_header_row(raw: pd.DataFrame, *, max_rows: int = 20) -> int:
    """Locate the *last* row of the header block.

    Strategy: scan rows 0..max_rows for the LAST row containing a cell whose
    stripped value equals exactly ``Date`` (case-insensitive). In the real
    Shiller XLS this is row 7 -- the row above also contains a "Date  " token
    (column label for the decimal-year alternate), so we must keep walking
    down until we find the canonical terminal header row.
    """
    rows = min(max_rows, len(raw))
    last_match: int | None = None
    for i in range(rows):
        for cell in raw.iloc[i].tolist():
            if _is_blankish(cell):
                continue
            cell_str = str(cell).strip()
            if cell_str.lower() in ("date", "date fraction"):
                last_match = i
                break
    if last_match is None:
        raise FileFormatError(
            "Could not locate Shiller header row (no cell equals 'Date' or 'Date Fraction')"
        )
    return last_match


def _row_density(raw: pd.DataFrame, row: int) -> float:
    n_cols = raw.shape[1]
    if n_cols == 0:
        return 0.0
    non_blank = sum(1 for v in raw.iloc[row].tolist() if not _is_blankish(v))
    return non_blank / n_cols


def _header_block_rows(raw: pd.DataFrame, header_row: int) -> list[int]:
    """Return the contiguous block of header rows ending at ``header_row``.

    A "header row" is one whose non-blank density exceeds a threshold. We walk
    upward from ``header_row`` and stop at the first row that looks bannerish
    (very sparse) or that is fully blank.
    """
    threshold = 0.15  # 15% non-blank cells = part of header block
    rows: list[int] = [header_row]
    r = header_row - 1
    while r >= 0:
        d = _row_density(raw, r)
        if d >= threshold:
            rows.append(r)
            r -= 1
        else:
            break
    rows.sort()
    return rows


def _build_composite_headers(raw: pd.DataFrame, header_row: int) -> list[str]:
    """Build per-column composite header strings by joining non-blank cells
    across the contiguous block of header rows ending at ``header_row``."""
    n_cols = raw.shape[1]
    header_rows = _header_block_rows(raw, header_row)
    out: list[str] = []
    for col_idx in range(n_cols):
        parts: list[str] = []
        for r in header_rows:
            cell = raw.iat[r, col_idx]
            if _is_blankish(cell):
                continue
            parts.append(str(cell).strip())
        out.append(" ".join(parts).strip())
    return out


def _map_headers(headers: list[str]) -> dict[str, int]:
    """Return a mapping from logical name to column index using the pattern map.

    Headers must be the *composite* per-column strings (see _build_composite_headers).
    Banner-text columns (which often contain author names, etc.) are skipped:
    we require an exact regex match.
    """
    out: dict[str, int] = {}
    compiled = {k: re.compile(v, re.IGNORECASE) for k, v in SHILLER_COLUMN_PATTERNS.items()}
    for col_idx, h in enumerate(headers):
        if not h:
            continue
        for logical, pat in compiled.items():
            if logical in out:
                continue
            if pat.match(h):
                out[logical] = col_idx
                break
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_shiller(
    file_path: Path = SHILLER_XLS,
    *,
    sheet_name: str | int = "Data",
) -> ShillerData:
    """Load Shiller's monthly dataset into a ShillerData."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise SourceMissingError(
            f"Shiller file not found: {file_path}",
            user_message=(
                "ie_data.xls is missing from the raw-data folder. "
                "Download from http://www.econ.yale.edu/~shiller/data.htm"
            ),
        )

    ext = file_path.suffix.lower()
    if ext == ".xls":
        engine = "xlrd"
        file_format: Literal["xls", "xlsx"] = "xls"
    elif ext == ".xlsx":
        engine = "openpyxl"
        file_format = "xlsx"
    else:
        raise FileFormatError(f"Unsupported Shiller extension: {ext}")

    try:
        raw = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine, header=None, dtype=object)
    except Exception as exc:
        raise FileFormatError(f"Could not read {file_path.name}: {exc}") from exc

    header_row = _find_header_row(raw)
    headers = _build_composite_headers(raw, header_row)
    col_map = _map_headers(headers)

    missing = sorted(REQUIRED - set(col_map.keys()))
    if missing:
        # Provide a diagnostic preview of the detected headers.
        preview = [str(h) for h in headers if h is not None][:20]
        raise FileFormatError(
            f"{file_path.name}: missing required columns {missing}. "
            f"Detected headers (first 20): {preview}"
        )

    body = raw.iloc[header_row + 1 :].reset_index(drop=True)

    # Parse dates with prev_month context for the October trap.
    parsed_dates: list[pd.Timestamp | None] = []
    prev_month: int | None = None
    for raw_date in body.iloc[:, col_map["date_fraction"]].tolist():
        if raw_date is None or (isinstance(raw_date, float) and pd.isna(raw_date)) or str(raw_date).strip() == "":
            parsed_dates.append(None)
            continue
        try:
            d = _parse_date(raw_date, prev_month)
        except Exception:  # noqa: BLE001
            parsed_dates.append(None)
            continue
        prev_month = d.month
        parsed_dates.append(d)

    # Build the output dataframe with logical column names.
    data: dict[str, list[float]] = {}
    for logical, col_idx in col_map.items():
        if logical == "date_fraction":
            continue
        col = body.iloc[:, col_idx]
        data[logical] = pd.to_numeric(col, errors="coerce").tolist()

    df = pd.DataFrame(data)
    df.index = pd.DatetimeIndex(parsed_dates)
    df.index.name = "date"

    # Drop rows with NaT index (trailing empty rows or unparseable dates).
    valid = df.index.notna()
    df = df.loc[valid]
    df = df.sort_index()

    # Truncate trailing all-NaN rows (Shiller sometimes leaves blank trailing rows).
    while not df.empty and df.iloc[-1].isna().all():
        df = df.iloc[:-1]

    if len(df) < 1500:
        raise DataValidationError(
            f"Shiller too few observations: {len(df)} (<1500)"
        )

    earliest = df.index.min()
    if not (
        pd.Timestamp("1870-12-01") <= earliest <= pd.Timestamp("1871-03-31")
    ):
        raise DataValidationError(
            f"Shiller start date {earliest.date()} not within 1871-01-31 +/- 1 month"
        )

    # Long-rate units normalization: percentage -> decimal.
    if "long_rate_gs10" in df.columns:
        gs10 = df["long_rate_gs10"].dropna()
        if not gs10.empty:
            first_val = float(gs10.iloc[0])
            if first_val > 1.0:
                logger.info("Shiller long_rate_gs10 detected as percentage; converting to decimal.")
                df["long_rate_gs10"] = df["long_rate_gs10"] / 100.0
            else:
                logger.info("Shiller long_rate_gs10 detected as decimal; passthrough.")

    available = tuple(c for c in df.columns)
    sha = sha256_file(file_path)
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

    return ShillerData(
        data=df,
        available_columns=available,
        start_date=earliest,
        end_date=df.index.max(),
        file_format=file_format,
        retrieval_timestamp=mtime,
        load_timestamp=utcnow(),
        sha256=sha,
    )


__all__ = [
    "ShillerData",
    "load_shiller",
    "SHILLER_COLUMN_PATTERNS",
    "REQUIRED",
    "_parse_date",
]
