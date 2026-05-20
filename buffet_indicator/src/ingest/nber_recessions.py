"""NBER US recession-period loader (v11.0 Macro Risk Module).

NBER publishes the canonical US business-cycle reference dates as monthly peak
and trough months. The FRED ``USREC`` series is the same information presented
as a monthly 0/1 indicator. We persist the peak/trough table to MoDH as
``nber_recessions.parquet`` so downstream chart overlays can render bands
without re-fetching.

The 1854-2020 dates are public-domain reference; we hardcode them so the
pipeline does not depend on FRED network access at chart-render time. If FRED
later updates the table (e.g., dates a 2026 recession), refresh by editing
``_NBER_PEAKS_TROUGHS`` below — the manifest cycles through ``vintage`` so a
re-run records the new ``today`` for provenance.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from src.config import MASTER_DIR
from src.ingest._base import (
    atomic_write_json,
    atomic_write_parquet,
    get_logger,
    utcnow,
)

logger = get_logger("buffett.ingest.nber")

# NBER US business-cycle reference dates (monthly peak, trough).
# Source: https://www.nber.org/research/business-cycle-dating
# A recession is defined as the period from the peak month to the trough month
# (inclusive of peak month, inclusive of trough month). NBER uses month-level
# precision; we anchor start = first day of peak month, end = last day of
# trough month so day-level shading covers the full recession on charts.
_NBER_PEAKS_TROUGHS: tuple[tuple[str, str], ...] = (
    ("1857-06", "1858-12"),
    ("1860-10", "1861-06"),
    ("1865-04", "1867-12"),
    ("1869-06", "1870-12"),
    ("1873-10", "1879-03"),
    ("1882-03", "1885-05"),
    ("1887-03", "1888-04"),
    ("1890-07", "1891-05"),
    ("1893-01", "1894-06"),
    ("1895-12", "1897-06"),
    ("1899-06", "1900-12"),
    ("1902-09", "1904-08"),
    ("1907-05", "1908-06"),
    ("1910-01", "1912-01"),
    ("1913-01", "1914-12"),
    ("1918-08", "1919-03"),
    ("1920-01", "1921-07"),
    ("1923-05", "1924-07"),
    ("1926-10", "1927-11"),
    ("1929-08", "1933-03"),
    ("1937-05", "1938-06"),
    ("1945-02", "1945-10"),
    ("1948-11", "1949-10"),
    ("1953-07", "1954-05"),
    ("1957-08", "1958-04"),
    ("1960-04", "1961-02"),
    ("1969-12", "1970-11"),
    ("1973-11", "1975-03"),
    ("1980-01", "1980-07"),
    ("1981-07", "1982-11"),
    ("1990-07", "1991-03"),
    ("2001-03", "2001-11"),
    ("2007-12", "2009-06"),
    ("2020-02", "2020-04"),
)

NBER_RECESSIONS_PARQUET = MASTER_DIR / "nber_recessions.parquet"
NBER_RECESSIONS_META = MASTER_DIR / "nber_recessions.meta.json"


def _build_dataframe() -> pd.DataFrame:
    """Materialize the hardcoded peak/trough table into a DataFrame."""
    rows = []
    for peak_str, trough_str in _NBER_PEAKS_TROUGHS:
        # Peak month -- shade starts at the first day of the peak month.
        start = pd.Timestamp(peak_str + "-01")
        # Trough month -- shade ends at the last day of the trough month.
        end = (pd.Timestamp(trough_str + "-01") + pd.offsets.MonthEnd(0)).normalize()
        rows.append({"start_date": start, "end_date": end})
    df = pd.DataFrame(rows)
    df = df.sort_values("start_date").reset_index(drop=True)
    return df


def _persist(df: pd.DataFrame) -> None:
    """Write the recession table + manifest to MASTER_DIR."""
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_parquet(NBER_RECESSIONS_PARQUET, df)
    atomic_write_json(
        NBER_RECESSIONS_META,
        {
            "source": "nber_business_cycle_reference_dates",
            "equivalent_fred_series": "USREC",
            "vintage": utcnow().isoformat(),
            "n_recessions": int(len(df)),
            "earliest_peak": df["start_date"].min().date().isoformat(),
            "latest_trough": df["end_date"].max().date().isoformat(),
            "url": "https://www.nber.org/research/business-cycle-dating",
            "note": "Hardcoded 1857-2020 reference dates; refresh module when NBER posts new cycles.",
        },
    )


@lru_cache(maxsize=1)
def load_nber_recessions() -> pd.DataFrame:
    """Return NBER-dated US recession periods.

    Each row has two columns:

    - ``start_date`` : ``pd.Timestamp`` -- first day of NBER peak month
    - ``end_date``   : ``pd.Timestamp`` -- last day of NBER trough month

    The table is materialized once into ``data/master/nber_recessions.parquet``
    on first call; subsequent calls read the parquet via :func:`functools.lru_cache`.

    Returns
    -------
    pd.DataFrame
        Sorted ascending by ``start_date``. ``end_date >= start_date`` everywhere.
    """
    if NBER_RECESSIONS_PARQUET.exists():
        try:
            df = pd.read_parquet(NBER_RECESSIONS_PARQUET)
            if {"start_date", "end_date"}.issubset(df.columns) and len(df) >= 30:
                df["start_date"] = pd.to_datetime(df["start_date"])
                df["end_date"] = pd.to_datetime(df["end_date"])
                return df.sort_values("start_date").reset_index(drop=True)
            logger.warning(
                "nber_recessions parquet exists but is malformed; rebuilding."
            )
        except Exception as exc:  # pragma: no cover - robustness path
            logger.warning("Failed to read nber_recessions parquet (%s); rebuilding.", exc)

    df = _build_dataframe()
    _persist(df)
    return df


def refresh() -> pd.DataFrame:
    """Force rebuild of the parquet from the embedded table."""
    load_nber_recessions.cache_clear()
    df = _build_dataframe()
    _persist(df)
    return df


__all__ = [
    "load_nber_recessions",
    "refresh",
    "NBER_RECESSIONS_PARQUET",
    "NBER_RECESSIONS_META",
]
