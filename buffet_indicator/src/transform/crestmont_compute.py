"""Crestmont P/E indicator (Spec v9.1 — rolling-window per Easterling 2010).

References
----------
Easterling, E. (2010). *Probable Outcomes: Secular Stock Market Insights*.
    Crestmont Holdings, ch. 6: "Stock Market P/E Ratio", pp. 142-148.
Easterling, E. (2008). "Crestmont Research: P/E Ratios and Stock Market
    Returns" — trend-earnings normalization methodology.

Methodology (v9.1 — corrected)
-------------------------------
v9.0 used a single full-sample OLS fit on log(real_eps), producing a constant
trend. Strategist's arbitration of v9.0 traced corr(Crestmont, Mean Reversion)
≈ 1.00 to this choice: over the full 1871-present sample, real-price growth
≈ real-earnings growth (Gordon Growth equilibrium), so the two indicators
collapsed to nearly-identical series.

v9.1 restores Easterling's actual published methodology: a **rolling
~50-year window** is fit at each timestamp, producing time-varying
(α_t, β_t) coefficients:

    For each month t:
        window  = real_eps[max(0, t - W + 1) : t + 1]   (right-aligned, causal)
        if len(window) < W_min  → crestmont_pe_t = NaN
        positions = 0, 1, ..., n-1   (window-local index)
        OLS:  log(real_eps_τ) = α_t + β_t · position(τ) + ε_τ
        trend_eps_t = exp(α_t + β_t · (n - 1))
        crestmont_pe_t = real_price_t / trend_eps_t

The "window's last position" is the in-sample fitted value at t — no
look-ahead. Acceptance gate: corr(crestmont_z, mean_reversion_z) < 0.95.

Data-access note (carried from v9.0)
------------------------------------
The original spec called for ``load_master("shiller_sp500_real", ...)``. Only
``wilshire_5000`` is currently canonicalized as a master parquet; Shiller data
ships via the ``ShillerData`` dataclass returned by ``load_shiller``. We follow
the existing project pattern. When called with ``shiller_data=None`` (the v9.1
default), the function loads live Shiller data internally; tests can pass a
mock object positionally.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from src.ingest.shiller_loader import ShillerData

# Easterling 2010 / 2008 methodology constants. Documented per Part-6 rule #9.
_DEFAULT_WINDOW_YEARS = 50
"""Easterling (2010) p. 144: 'The trend uses approximately 50 years of
historical earnings data.'"""

_DEFAULT_MIN_WINDOW_YEARS = 30
"""Minimum sample for a stable rolling regression. Below this, Crestmont P/E
is NaN to avoid high-variance trend estimates."""

_MIN_OBS_FOR_TREND_FIT = 60
"""Module-level minimum observations needed to attempt any rolling computation
at all (≥ 5 years). Distinct from the rolling-window minimum: this is the
absolute lower bound below which the function raises ValueError."""


def compute_crestmont_pe(
    shiller_data: "ShillerData | None" = None,
    *,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    window_years: int = _DEFAULT_WINDOW_YEARS,
    min_window_years: int = _DEFAULT_MIN_WINDOW_YEARS,
) -> pd.DataFrame:
    """Compute Crestmont P/E using rolling-window earnings-trend normalization.

    Parameters
    ----------
    shiller_data : ShillerData or None
        Output of :func:`src.ingest.shiller_loader.load_shiller`. If ``None``
        (the default), live Shiller data is loaded internally. Tests can pass
        a mock object exposing ``.data`` with ``real_price`` + ``real_earnings``
        columns.
    start, end :
        Optional date filter (inclusive).
    window_years : int, default 50
        Rolling window length in years for the OLS fit. Default matches
        Easterling (2010) p. 144.
    min_window_years : int, default 30
        Minimum years of data required before a Crestmont P/E is produced.
        Earlier rows emit NaN. (Spec test: ``first_360`` rows all NaN with
        defaults.)

    Returns
    -------
    pd.DataFrame
        Indexed by month-end date. Columns:

        ============ ===================================================
        real_price   Shiller real S&P 500 price (inflation-adjusted)
        real_eps     Shiller real earnings (inflation-adjusted, monthly)
        trend_eps    exp(α_t + β_t · (n - 1)); NaN before min window
        crestmont_pe real_price / trend_eps; NaN before min window
        log_crestmont_pe natural log; NaN before min window
        alpha_t      Rolling intercept at time t (NaN before min window)
        beta_t       Rolling slope at time t (NaN before min window)
        n_in_window  Observations actually used in fit at time t
        window_years Constant; documentation column
        ============ ===================================================

    Raises
    ------
    ValueError
        If fewer than ``_MIN_OBS_FOR_TREND_FIT`` (60) observations survive
        after dropna.

    References
    ----------
    Easterling, E. (2010). *Probable Outcomes: Secular Stock Market Insights*.
        Crestmont Holdings. Chapter 6: "Stock Market P/E Ratio", pp. 142-148.

    Notes
    -----
    The rolling window is **right-aligned, inclusive of t**, with strictly
    causal information set — verified by ``test_crestmont_v91_no_lookahead``.
    """
    if shiller_data is None:
        from src.ingest.shiller_loader import load_shiller
        shiller_data = load_shiller()

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

    n_total = len(panel)
    if n_total < _MIN_OBS_FOR_TREND_FIT:
        raise ValueError(
            f"Crestmont requires ≥ {_MIN_OBS_FOR_TREND_FIT} monthly observations "
            f"for any rolling fit; got {n_total}."
        )

    window_months = int(window_years * 12)
    min_window_months = int(min_window_years * 12)

    real_price_arr = panel["real_price"].to_numpy(dtype="float64")
    real_eps_arr = panel["real_eps"].to_numpy(dtype="float64")

    trend_eps = np.full(n_total, np.nan)
    crestmont_pe = np.full(n_total, np.nan)
    log_crestmont_pe = np.full(n_total, np.nan)
    alpha_t = np.full(n_total, np.nan)
    beta_t = np.full(n_total, np.nan)
    n_in_window = np.zeros(n_total, dtype="int64")

    n_nonpos = 0
    for t in range(n_total):
        # "Data exist BEFORE t" is t (count of indices 0..t-1).
        if t < min_window_months:
            n_in_window[t] = t + 1  # documentary; trend NaN
            continue

        window_start = max(0, t - window_months + 1)
        eps_window = real_eps_arr[window_start : t + 1]
        n = eps_window.size
        n_in_window[t] = n

        if (eps_window <= 0).any():
            n_nonpos += 1
            continue

        log_eps = np.log(eps_window)
        positions = np.arange(n, dtype="float64")
        # Vectorized OLS via lstsq.
        X = np.column_stack([np.ones(n), positions])
        coef, _, _, _ = np.linalg.lstsq(X, log_eps, rcond=None)
        a, b = float(coef[0]), float(coef[1])
        alpha_t[t] = a
        beta_t[t] = b
        te = float(np.exp(a + b * (n - 1)))
        trend_eps[t] = te
        if te > 0:
            crestmont_pe[t] = real_price_arr[t] / te
            log_crestmont_pe[t] = np.log(crestmont_pe[t])

    if n_nonpos > 0 and n_nonpos / max(n_total - min_window_months, 1) > 0.05:
        logging.warning(
            "Crestmont: %d rolling windows skipped due to non-positive earnings "
            "(>5%% of post-min-window rows); inspect Shiller data integrity.",
            n_nonpos,
        )

    out = panel.assign(
        trend_eps=trend_eps,
        crestmont_pe=crestmont_pe,
        log_crestmont_pe=log_crestmont_pe,
        alpha_t=alpha_t,
        beta_t=beta_t,
        n_in_window=n_in_window,
        window_years=int(window_years),
    )
    return out[
        [
            "real_price",
            "real_eps",
            "trend_eps",
            "crestmont_pe",
            "log_crestmont_pe",
            "alpha_t",
            "beta_t",
            "n_in_window",
            "window_years",
        ]
    ]


def compute_crestmont_variant(
    shiller_data: "ShillerData | None" = None,
) -> dict[str, pd.Series]:
    """Project-pattern wrapper returning ``{"crestmont": pd.Series}``.

    Drops NaN early-history rows (pre-min-window) before returning, so
    downstream z-score machinery sees only valid Crestmont P/E values.
    """
    try:
        df = compute_crestmont_pe(shiller_data)
    except ValueError:
        return {}
    series = df["crestmont_pe"].astype("float64").dropna()
    if series.empty:
        return {}
    series.name = "crestmont"
    series.index = (
        pd.DatetimeIndex(series.index)
        .to_period("M")
        .to_timestamp(how="end")
        .normalize()
    )
    return {"crestmont": series}


__all__ = ["compute_crestmont_pe", "compute_crestmont_variant"]
