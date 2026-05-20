"""v11.0 Margin Debt indicator -- FINRA Customer Margin Balances → 12M log growth.

Why 12-month growth rate rather than the raw level
--------------------------------------------------
Margin debt is a secular-trend series: it grows roughly with equity market cap,
so a level-based z-score would systematically classify the most-recent decade
as the most extreme observation. The canonical sentiment signal (Schwab,
Yardeni, FINRA presentations) is the **12-month rate of change**, which is
stationary around zero and turns sharply positive in late-cycle leveraged-
buying frenzies and sharply negative in deleveraging episodes (2008-09, 2020,
2022).

Direction convention (per spec PART 10 §10):
    signal = log(level_t / level_{t-12})   # high signal = bearish (no flip)

High 12M growth means investors are levering up rapidly -- historically a
precursor of mediocre forward returns.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import MARGIN_DEBT_XLSX
from src.ingest._base import SourceMissingError, get_logger

logger = get_logger("buffett.transform.margin_debt")


REQUIRED_COLUMNS = ("margin_debt_level", "log_level", "growth_12m", "signal")

# Column header variants we look for in the FINRA workbook. FINRA has tweaked
# capitalization across releases; we match case-insensitively on a substring
# that should be stable.
_DEBIT_BALANCE_SUBSTRING = "debit balance"


def _select_debit_column(df: pd.DataFrame) -> str:
    """Pick the column whose header looks like 'Debit Balances ...'."""
    candidates = [
        c for c in df.columns if _DEBIT_BALANCE_SUBSTRING in str(c).lower()
    ]
    if not candidates:
        raise SourceMissingError(
            f"Could not find a debit-balance column in the margin XLSX; "
            f"got {list(df.columns)}"
        )
    if len(candidates) > 1:
        # Prefer the one that mentions 'margin accounts' (the FINRA canonical).
        margin_cands = [c for c in candidates if "margin" in str(c).lower()]
        if margin_cands:
            return margin_cands[0]
    return candidates[0]


def _parse_year_month(series: pd.Series) -> pd.DatetimeIndex:
    """Convert FINRA's 'YYYY-MM' strings to month-end timestamps."""
    parsed = pd.to_datetime(series.astype(str), format="%Y-%m", errors="coerce")
    if parsed.isna().any():
        # Fallback to permissive parse.
        parsed = pd.to_datetime(series.astype(str), errors="coerce")
    # Snap to month-end so the series aligns with all other monthly indicators.
    return pd.DatetimeIndex(parsed) + pd.offsets.MonthEnd(0)


def _load_finra_workbook(path: Path) -> pd.DataFrame:
    """Read every sheet, concatenate, and return a deduplicated frame."""
    if not path.exists():
        raise SourceMissingError(
            f"Margin debt workbook not found at {path}",
            user_message=f"Expected file {path.name} in the raw-data folder.",
        )
    book = pd.read_excel(path, sheet_name=None)
    pieces: list[pd.DataFrame] = []
    for sheet_name, df in book.items():
        if df is None or df.empty:
            continue
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]
        if "Year-Month" not in df.columns and "Date" not in df.columns:
            logger.warning(
                "Sheet %r in %s lacks 'Year-Month'/'Date'; skipping.",
                sheet_name,
                path.name,
            )
            continue
        df["_sheet"] = sheet_name
        pieces.append(df)
    if not pieces:
        raise SourceMissingError(
            f"{path.name}: no usable sheet found with a 'Year-Month' column."
        )
    combined = pd.concat(pieces, ignore_index=True)
    return combined


def compute_margin_debt_growth(
    *,
    path: Path = MARGIN_DEBT_XLSX,
    log_schema_path: Path | None = None,
) -> pd.DataFrame:
    """Compute the 12-month margin-debt log-growth signal.

    Returns
    -------
    pd.DataFrame
        Indexed by month-end ``date`` with columns:

        - ``margin_debt_level`` : Debit balances in USD (FINRA original units)
        - ``log_level``         : ``log(margin_debt_level)``
        - ``growth_12m``        : ``log_level_t - log_level_{t-12}``; first 12
                                  rows are NaN by construction.
        - ``signal``            : == ``growth_12m`` (no negation)
    """
    combined = _load_finra_workbook(path)
    debit_col = _select_debit_column(combined)
    if log_schema_path is not None:
        log_schema_path.parent.mkdir(parents=True, exist_ok=True)
        log_schema_path.write_text(
            f"sheet={combined['_sheet'].unique().tolist()}\n"
            f"debit_column={debit_col!r}\n"
            f"n_rows={len(combined)}\n"
        )
    # Build the canonical series.
    levels = pd.to_numeric(combined[debit_col], errors="coerce")
    dates = _parse_year_month(combined["Year-Month"])
    s = (
        pd.Series(levels.to_numpy(), index=dates, name="margin_debt_level")
        .dropna()
        .sort_index()
    )
    s = s[~s.index.duplicated(keep="last")]
    if (s <= 0).any():
        bad = int((s <= 0).sum())
        logger.warning(
            "Margin debt: %d non-positive observations dropped before log.", bad
        )
        s = s[s > 0]
    df = pd.DataFrame({"margin_debt_level": s.astype("float64")})
    df["log_level"] = np.log(df["margin_debt_level"])
    df["growth_12m"] = df["log_level"].diff(12)
    df["signal"] = df["growth_12m"]
    df.index.name = "date"
    df.attrs["source"] = "finra:customer_margin_balances"
    df.attrs["variant_key"] = "margin_debt_growth"
    df.attrs["direction"] = "standard"
    df.attrs["debit_column"] = debit_col
    return df


def latest_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Last-observation summary for headline rows."""
    last_signal = df.dropna(subset=["signal"]).iloc[-1]
    last_level = df["margin_debt_level"].dropna().iloc[-1]
    return {
        "date": last_signal.name.date().isoformat()
        if hasattr(last_signal.name, "date")
        else str(last_signal.name),
        "level_usd": float(last_level),
        "growth_12m_log": float(last_signal["growth_12m"]),
        "growth_12m_pct": float(np.expm1(last_signal["growth_12m"]) * 100),
        "signal": float(last_signal["signal"]),
    }


__all__ = [
    "compute_margin_debt_growth",
    "latest_summary",
    "REQUIRED_COLUMNS",
]
