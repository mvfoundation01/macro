"""Crestmont P/E indicator (Spec v9.0).

References
----------
Easterling, E. (2010). *Probable Outcomes: Secular Stock Market Insights*.
    Crestmont Holdings, ch. 6 (Crestmont P/E definition).
Easterling, E. (2008). "Crestmont Research: P/E Ratios and Stock Market
    Returns" — trend-earnings normalization methodology.

Methodology
-----------
The Crestmont P/E is a cyclically-adjusted P/E that normalizes price by a
**trend line of real earnings** rather than a trailing average (Shiller CAPE).

    log(real_eps_t) = α + β · t + ε_t      (full-sample OLS fit)
    trend_eps_t     = exp(α̂ + β̂ · t)      (smooth exponential trend)
    crestmont_pe_t  = real_price_t / trend_eps_t

Data-access note
----------------
The v9.0 spec calls for ``load_master("shiller_sp500_real", ...)``. The current
project ships Shiller data via the ``ShillerData`` dataclass returned by
``src.ingest.shiller_loader.load_shiller``; only ``wilshire_5000`` is currently
canonicalized as a master parquet. We follow the existing project pattern
(used by ``cape_variants`` and ``mean_reversion_compute``) until the master
series for Shiller real_price/real_earnings is built. This deviation is
recorded in REVIEW_PACKAGE_v9.0.md §9.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import statsmodels.api as sm

if TYPE_CHECKING:
    from src.ingest.shiller_loader import ShillerData

# Easterling 2010 / 2008 methodology constants. Documented for §PART-6 rule #9.
_MIN_OBS_FOR_TREND_FIT = 60
"""Minimum monthly observations required to fit a stable exponential trend
on real earnings. 5 years is the practical lower bound recommended by
Easterling (2008) trend-fitting notes; below this the trend slope is
high-variance."""


def compute_crestmont_pe(
    shiller_data: "ShillerData",
    *,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Compute the Crestmont P/E series with trend-earnings normalization.

    Parameters
    ----------
    shiller_data : ShillerData
        Output of ``src.ingest.shiller_loader.load_shiller``. Must expose
        ``data`` DataFrame with ``real_price`` and ``real_earnings`` columns.
    start, end :
        Optional date filter (inclusive). ``None`` = full available history.

    Returns
    -------
    pd.DataFrame
        Indexed by month-end date. Columns:

        ============ ===================================================
        real_price   Shiller real S&P 500 price (inflation-adjusted)
        real_eps     Shiller real earnings (inflation-adjusted, monthly)
        trend_eps    Fitted exp(α̂ + β̂·t) exponential trend
        crestmont_pe real_price / trend_eps (the headline indicator)
        log_crestmont_pe natural log; used for z-score standardization
        alpha        OLS log-linear intercept (constant across rows)
        beta         OLS log-linear monthly slope (constant across rows)
        n_fit        Observations used in the trend fit
        ============ ===================================================

    Raises
    ------
    ValueError
        If fewer than ``_MIN_OBS_FOR_TREND_FIT`` (60) observations
        survive after dropping NaN rows.

    Algorithm
    ---------
    1. Extract ``real_price`` and ``real_earnings`` from ``shiller_data.data``
       and align on a common DatetimeIndex.
    2. Drop rows with non-positive ``real_eps`` from the trend fit (``log`` is
       undefined there). Such rows are extremely rare and absent in the
       Shiller 1871-present panel, but we guard anyway.
    3. Fit ``log(real_eps_t) = α + β·t + ε`` via OLS where ``t`` is the
       month-index (0, 1, 2, ...) over the cleaned fit sample.
    4. Project ``trend_eps_t = exp(α̂ + β̂·t)`` for every row in the aligned
       dataframe (including any rows excluded from the fit).
    5. Compute ``crestmont_pe_t = real_price_t / trend_eps_t``.
    """
    df = shiller_data.data
    cols = {"real_price", "real_earnings"}
    if not cols.issubset(df.columns):
        raise ValueError(
            f"compute_crestmont_pe: shiller_data missing columns {cols - set(df.columns)}. "
            "Available columns: " + ", ".join(df.columns)
        )

    panel = (
        df[["real_price", "real_earnings"]]
        .rename(columns={"real_earnings": "real_eps"})
        .copy()
    )
    panel = panel.dropna(subset=["real_price", "real_eps"])
    panel.index = pd.DatetimeIndex(panel.index)
    panel = panel.sort_index()

    if start is not None:
        panel = panel.loc[panel.index >= pd.Timestamp(start)]
    if end is not None:
        panel = panel.loc[panel.index <= pd.Timestamp(end)]

    if len(panel) < _MIN_OBS_FOR_TREND_FIT:
        raise ValueError(
            f"Crestmont requires ≥ {_MIN_OBS_FOR_TREND_FIT} monthly observations "
            f"for stable trend fit; got {len(panel)}."
        )

    positive = panel["real_eps"] > 0
    n_dropped = int((~positive).sum())
    if n_dropped > 0:
        logging.warning(
            "Crestmont: dropping %d rows with non-positive real earnings from "
            "trend fit; trend will still be applied to all rows.",
            n_dropped,
        )

    fit = panel.loc[positive].copy()
    fit_t = np.arange(len(fit), dtype="float64")
    fit_y = np.log(fit["real_eps"].to_numpy(dtype="float64"))
    model = sm.OLS(fit_y, sm.add_constant(fit_t)).fit()
    alpha = float(model.params[0])
    beta = float(model.params[1])

    panel_t = np.arange(len(panel), dtype="float64")
    panel = panel.assign(
        trend_eps=np.exp(alpha + beta * panel_t),
        alpha=alpha,
        beta=beta,
        n_fit=int(positive.sum()),
    )
    panel["crestmont_pe"] = panel["real_price"] / panel["trend_eps"]
    panel["log_crestmont_pe"] = np.log(panel["crestmont_pe"])

    return panel[
        [
            "real_price",
            "real_eps",
            "trend_eps",
            "crestmont_pe",
            "log_crestmont_pe",
            "alpha",
            "beta",
            "n_fit",
        ]
    ]


def compute_crestmont_variant(
    shiller_data: "ShillerData",
) -> dict[str, pd.Series]:
    """Project-pattern wrapper around :func:`compute_crestmont_pe`.

    Returns ``{"crestmont": pd.Series}`` of the Crestmont P/E level series,
    matching the dict-of-series interface used by :func:`compute_cape_variants`,
    :func:`compute_mean_reversion_variant`, etc. The orchestrator's z-score
    machinery applies its own log-trend fit on the level series.
    """
    try:
        df = compute_crestmont_pe(shiller_data)
    except ValueError:
        return {}
    if df.empty:
        return {}
    series = df["crestmont_pe"].astype("float64").copy()
    series.name = "crestmont"
    # Month-end normalization for downstream alignment.
    series.index = (
        pd.DatetimeIndex(series.index)
        .to_period("M")
        .to_timestamp(how="end")
        .normalize()
    )
    return {"crestmont": series}


__all__ = ["compute_crestmont_pe", "compute_crestmont_variant"]
