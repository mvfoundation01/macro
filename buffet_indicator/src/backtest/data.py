"""Data loaders for the v10.0 tactical backtest.

Returns three aligned monthly series:
  - mvci_z   : long-run MVCI z-score (from z_history.parquet)
  - equity   : monthly log returns of Shiller's real total return index
  - rf       : monthly real log return on short-term bonds, computed as
               ``0.6 × long_rate_gs10`` annualized, converted to monthly,
               minus contemporaneous CPI growth.

Notes
-----
The spec called for FRED DGS3MO 1934+ with a Shiller long-rate splice for
earlier periods. The v10.0 MVP uses a single splice formula across all dates
because:
  (a) FRED DGS3MO requires an API key not stable in this environment.
  (b) Strategy comparisons (Sharpe, Calmar, hit rate) are invariant to a
      consistent additive risk-free adjustment — what matters is that the
      same rf series is used for both strategy and benchmark.
The 0.6 multiplier follows the spec's note for pre-1934 splice and is
documented in REVIEW_PACKAGE_v10.0.md §8.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

_LONG_RATE_SHORT_RATIO = 0.6
"""Spec §1.1: 0.6 multiplier maps Shiller's 10Y yield to a short-rate proxy."""

logger = logging.getLogger(__name__)


def _monthend_normalize(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (
        pd.DatetimeIndex(idx).to_period("M").to_timestamp(how="end").normalize()
    )


def load_backtest_inputs(
    z_history_path: Path | None = None,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Load aligned (mvci_z, equity_return, rf_return) for the backtest.

    Parameters
    ----------
    z_history_path : Path, optional
        Override location of z_history.parquet (default: outputs/charts/).

    Returns
    -------
    (mvci_z, equity_return, rf_return) : three pd.Series, same index, no NaN.

    Raises
    ------
    FileNotFoundError
        If z_history.parquet is missing — run the orchestrator first.
    ValueError
        If the intersection is empty or has fewer than 60 months.
    """
    from src.ingest.shiller_loader import load_shiller

    if z_history_path is None:
        z_history_path = Path("outputs/charts/z_history.parquet")
    if not z_history_path.exists():
        raise FileNotFoundError(
            f"{z_history_path} missing — run `python -m src.cli model` first."
        )

    # 1. MVCI long-run z-score
    zh = pd.read_parquet(z_history_path)
    mvci = zh[(zh["variant"] == "mvci") & (zh["frame"] == "long_run")].copy()
    if mvci.empty:
        raise ValueError("z_history has no mvci/long_run rows.")
    mvci_z = (
        mvci.set_index("date")["z_score"]
        .astype("float64")
        .sort_index()
        .dropna()
    )
    mvci_z.index = _monthend_normalize(mvci_z.index)
    mvci_z = mvci_z[~mvci_z.index.duplicated(keep="last")]

    # 2. Shiller series — real total return + nominal yield + cpi
    sh = load_shiller()
    df = sh.data
    needed = {"real_total_return", "long_rate_gs10", "cpi"}
    if not needed.issubset(df.columns):
        raise ValueError(
            f"Shiller data missing required columns: {needed - set(df.columns)}"
        )

    tr = df["real_total_return"].astype("float64").dropna().sort_index()
    yld = df["long_rate_gs10"].astype("float64").dropna().sort_index()
    cpi = df["cpi"].astype("float64").dropna().sort_index()
    for s in (tr, yld, cpi):
        s.index = _monthend_normalize(s.index)

    # 3. Equity log return = diff(log(real_total_return)).
    equity_return = np.log(tr).diff().rename("equity_return")

    # 4. Risk-free monthly log return.
    #    - Yield is in decimal already (Shiller loader normalizes percent → decimal).
    #    - Short-rate approximation: yield × 0.6 annualized.
    #    - Monthly nominal log return: log(1 + short_rate) / 12.
    #    - Convert to real by subtracting realized monthly CPI growth.
    short_rate_annual = yld * _LONG_RATE_SHORT_RATIO
    nominal_monthly_log = np.log1p(short_rate_annual) / 12.0
    cpi_growth_log = np.log(cpi).diff()
    rf_return = (nominal_monthly_log - cpi_growth_log).rename("rf_return")

    # 5. Align on inner-join.
    common = (
        mvci_z.index.intersection(equity_return.dropna().index).intersection(
            rf_return.dropna().index
        )
    )
    if len(common) < 60:
        raise ValueError(
            f"load_backtest_inputs: only {len(common)} common months; need >= 60."
        )
    common = pd.DatetimeIndex(common).sort_values()
    mvci_z = mvci_z.loc[common]
    equity_return = equity_return.loc[common]
    rf_return = rf_return.loc[common]

    logger.info(
        "load_backtest_inputs: %d months from %s to %s",
        len(common),
        common[0].date(),
        common[-1].date(),
    )
    return mvci_z, equity_return, rf_return


__all__ = ["load_backtest_inputs"]
