"""Generic loader for TradingView XLSX / XLS / CSV exports."""
from __future__ import annotations

import csv as _csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import chardet
import pandas as pd

from src.config import TV_GDP_BAK, TV_SPX, TV_SPXTR, TV_WILSHIRE
from src.ingest._base import (
    DataValidationError,
    FileFormatError,
    SourceMissingError,
    get_logger,
    sha256_file,
    utcnow,
)

logger = get_logger("buffett.ingest.csv")


REQUIRED_COLS = {"time", "close"}
OPTIONAL_COLS = {"open", "high", "low", "volume"}


@dataclass(frozen=True)
class TabularSeries:
    symbol: str
    data: pd.DataFrame
    frequency: Literal["D", "W", "M", "Q"]
    units: str
    file_format: Literal["csv", "xlsx", "xls"]
    retrieval_timestamp: datetime
    load_timestamp: datetime
    sha256: str
    source_file: Path


CsvKey = Literal["spx", "spxtr", "wilshire_tv", "gdp_backup"]


# ---------------------------------------------------------------------------
# Per-extension readers
# ---------------------------------------------------------------------------


def _detect_encoding(path: Path) -> str:
    with open(path, "rb") as fh:
        head = fh.read(65536)
    result = chardet.detect(head)
    return result.get("encoding") or "utf-8"


def _read_csv(path: Path) -> pd.DataFrame:
    encoding = _detect_encoding(path)
    # csv.Sniffer for delimiter
    with open(path, "r", encoding=encoding, errors="replace") as fh:
        sample = fh.read(4096)
    try:
        dialect = _csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delim = dialect.delimiter
    except _csv.Error:
        delim = ","
    return pd.read_csv(path, encoding=encoding, sep=delim)


def _read_excel(path: Path, sheet_name: str | int, engine: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name, engine=engine)


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------


def _try_parse_time(series: pd.Series, file_format: str) -> pd.DatetimeIndex | None:
    """Return a normalized UTC-naive DatetimeIndex, or None if parsing fails."""
    if series.empty:
        return None

    # If pandas already gave us datetime64, just normalize.
    if pd.api.types.is_datetime64_any_dtype(series):
        idx = pd.DatetimeIndex(series)
        if idx.tz is not None:
            idx = idx.tz_convert("UTC").tz_localize(None)
        return idx.normalize()

    s = series.copy()

    # Strategy 1 -- numeric: try unix epoch (large ints) or Excel serial (smaller floats).
    if pd.api.types.is_numeric_dtype(s):
        s_num = pd.to_numeric(s, errors="coerce")
        if s_num.notna().all():
            sample = float(s_num.iloc[0])
            # Heuristic: Excel serial dates are roughly 0..120000; unix epochs are 1e9+.
            if sample > 1_000_000_000:
                idx = pd.to_datetime(s_num, unit="s", errors="coerce")
            else:
                # Excel serial date, origin 1899-12-30
                idx = pd.to_datetime(s_num, unit="D", origin="1899-12-30", errors="coerce")
            if idx.notna().all():
                idx = pd.DatetimeIndex(idx)
                if idx.tz is not None:
                    idx = idx.tz_convert("UTC").tz_localize(None)
                return idx.normalize()

    # Strategy 2 -- strings: ISO 8601 (with Z, with offset), date-only, etc.
    s_str = s.astype("string").str.strip()

    def _coerce(values: pd.Series) -> pd.DatetimeIndex:
        idx = pd.DatetimeIndex(values)
        if idx.tz is not None:
            idx = idx.tz_convert("UTC").tz_localize(None)
        return idx.normalize()

    # Try strict ISO formats first.
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            parsed = pd.to_datetime(s_str, format=fmt, errors="raise", utc=True)
            return _coerce(parsed)
        except (ValueError, TypeError):
            continue
    # Fallback to permissive parsing.
    try:
        parsed = pd.to_datetime(s_str, errors="raise", utc=True)
        return _coerce(parsed)
    except (ValueError, TypeError):
        pass

    # Last-ditch: unix-epoch-as-string of digits.
    if s_str.str.match(r"^\d+$").all():
        nums = pd.to_numeric(s_str, errors="coerce")
        idx = pd.to_datetime(nums, unit="s", errors="coerce")
        if idx.notna().all():
            return pd.DatetimeIndex(idx).normalize()

    return None


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _infer_frequency(idx: pd.DatetimeIndex) -> Literal["D", "W", "M", "Q"]:
    if len(idx) < 2:
        return "D"
    median_gap = float(pd.Series(idx).diff().dt.days.dropna().median())
    if median_gap <= 4:
        return "D"
    if median_gap <= 10:
        return "W"
    if median_gap <= 45:
        return "M"
    return "Q"


def _validate_dataframe(
    df: pd.DataFrame,
    expected_frequency: str,
    max_gap_days: int,
    source_file: Path,
) -> Literal["D", "W", "M", "Q"]:
    if not df.index.is_monotonic_increasing:
        raise DataValidationError(
            f"{source_file.name}: index not monotonic after sort"
        )
    if len(df) < 100:
        raise DataValidationError(
            f"{source_file.name}: only {len(df)} rows (<100)",
        )
    close_nonan = float(df["close"].notna().mean())
    if close_nonan < 0.95:
        raise DataValidationError(
            f"{source_file.name}: close column {1 - close_nonan:.1%} NaN (>5%)"
        )
    if (df["close"].dropna() <= 0).any():
        raise DataValidationError(
            f"{source_file.name}: non-positive close values present"
        )
    # Extreme-outlier guard: any single-day return >10x?
    rets = df["close"].pct_change().abs().dropna()
    if (rets > 9).any():
        raise DataValidationError(
            f"{source_file.name}: extreme single-day return detected"
        )

    deltas = pd.Series(df.index).diff().dt.days.dropna()
    if not deltas.empty and float(deltas.max()) > max_gap_days:
        big = deltas[deltas > max_gap_days]
        raise DataValidationError(
            f"{source_file.name}: gap of {int(big.max())} days exceeds "
            f"max_gap_days={max_gap_days}"
        )

    inferred = _infer_frequency(df.index)
    if inferred != expected_frequency:
        raise DataValidationError(
            f"{source_file.name}: inferred freq={inferred} != expected={expected_frequency}"
        )
    return inferred


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_tradingview_file(
    path: Path,
    *,
    expected_symbol: str | None = None,
    expected_frequency: Literal["D", "W", "M", "Q"] = "D",
    sheet_name: str | int = 0,
    units: str = "",
    max_gap_days: int = 14,
) -> TabularSeries:
    """Load a single TradingView CSV/XLSX/XLS export into a TabularSeries."""
    path = Path(path)
    if not path.exists():
        raise SourceMissingError(
            f"Expected raw file not found: {path}",
            user_message=(
                f"The TradingView export {path.name} is missing from the raw-data folder."
            ),
        )

    ext = path.suffix.lower()
    if ext == ".csv":
        df = _read_csv(path)
        file_format: Literal["csv", "xlsx", "xls"] = "csv"
    elif ext == ".xlsx":
        df = _read_excel(path, sheet_name=sheet_name, engine="openpyxl")
        file_format = "xlsx"
    elif ext == ".xls":
        df = _read_excel(path, sheet_name=sheet_name, engine="xlrd")
        file_format = "xls"
    else:
        raise FileFormatError(f"Unsupported file extension: {ext}")

    if df.empty:
        raise FileFormatError(f"{path.name}: empty sheet")

    # Lowercase column names.
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing_required = REQUIRED_COLS - set(df.columns)
    if missing_required:
        raise FileFormatError(
            f"{path.name}: missing required columns {sorted(missing_required)}; "
            f"got {list(df.columns)}"
        )

    # Subset to known columns; ignore extras.
    keep = [c for c in df.columns if c in REQUIRED_COLS | OPTIONAL_COLS]
    df = df[keep].copy()

    parsed_idx = _try_parse_time(df["time"], file_format)
    if parsed_idx is None:
        raise FileFormatError(
            f"{path.name}: could not parse 'time' column with any known strategy"
        )
    df.index = parsed_idx
    df.index.name = "date"
    df = df.drop(columns=["time"])

    # Numeric coercion for value columns.
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort + dedupe
    df = df.sort_index()
    dup_mask = df.index.duplicated(keep="last")
    if dup_mask.any():
        logger.warning(
            "%s: dropping %d duplicate timestamps (keep last)",
            path.name,
            int(dup_mask.sum()),
        )
        df = df[~df.index.duplicated(keep="last")]

    frequency = _validate_dataframe(df, expected_frequency, max_gap_days, path)

    sha = sha256_file(path)
    file_mtime = datetime.fromtimestamp(path.stat().st_mtime)

    return TabularSeries(
        symbol=expected_symbol or path.stem,
        data=df,
        frequency=frequency,
        units=units,
        file_format=file_format,
        retrieval_timestamp=file_mtime,
        load_timestamp=utcnow(),
        sha256=sha,
        source_file=path,
    )


# ---------------------------------------------------------------------------
# Bulk loader for the four TradingView inputs.
# ---------------------------------------------------------------------------


_TV_SPEC: dict[str, dict[str, object]] = {
    "spx": {
        "path": TV_SPX,
        "expected_frequency": "D",
        "expected_symbol": "SPX",
        "units": "index points (USD)",
        # SPX historical file blends Shiller monthly (1871-1928) with daily (1928+):
        # tolerate the large gap rather than failing validation.
        "max_gap_days": 100,
    },
    "spxtr": {
        "path": TV_SPXTR,
        "expected_frequency": "D",
        "expected_symbol": "SPXTR",
        "units": "index points (USD, total return)",
        "max_gap_days": 14,
    },
    "wilshire_tv": {
        "path": TV_WILSHIRE,
        "expected_frequency": "D",
        "expected_symbol": "FRED:WILL5000PRFC",
        "units": "USD (Wilshire 5000 Full-Cap Index, FRED mirror)",
        # The TV Wilshire mirror is monthly in 1970-1975, then daily through 2023-05-30.
        # Tolerate gaps up to ~33 days so the deep history survives validation.
        "max_gap_days": 35,
    },
    "gdp_backup": {
        "path": TV_GDP_BAK,
        "expected_frequency": "Q",
        "expected_symbol": "FRED:GDP",
        "units": "USD (FRED GDP backup)",
        "max_gap_days": 100,
    },
}


def load_tradingview_inputs(*, require_all: bool = False) -> dict[str, TabularSeries]:
    """Load all known TradingView inputs.

    If a file is missing and ``require_all`` is False, log a WARNING and skip it.
    """
    out: dict[str, TabularSeries] = {}
    for key, spec in _TV_SPEC.items():
        path = Path(spec["path"])  # type: ignore[arg-type]
        if not path.exists():
            if require_all:
                raise SourceMissingError(f"Required TradingView input missing: {path}")
            logger.warning("Optional TradingView input not found, skipping: %s", path)
            continue
        try:
            ts = load_tradingview_file(
                path,
                expected_symbol=spec.get("expected_symbol"),  # type: ignore[arg-type]
                expected_frequency=spec["expected_frequency"],  # type: ignore[arg-type]
                units=spec.get("units", ""),  # type: ignore[arg-type]
                max_gap_days=spec["max_gap_days"],  # type: ignore[arg-type]
            )
        except DataValidationError:
            if require_all:
                raise
            logger.warning("Validation failed for %s, skipping", path.name)
            continue

        if key == "wilshire_tv":
            end = ts.data.index.max().date()
            logger.info(
                "Wilshire TV history ends %s (TradingView mirror stopped publishing).",
                end,
            )
        out[key] = ts
    return out


__all__ = [
    "TabularSeries",
    "load_tradingview_file",
    "load_tradingview_inputs",
    "CsvKey",
]
