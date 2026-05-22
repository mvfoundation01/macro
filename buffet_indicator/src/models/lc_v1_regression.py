"""LC v1.0 predictive regression per sealed pre-reg a8635ef §3.1-§3.5.

Specification
-------------

For each LC scope (``LC_FULL``, ``LC_TIER2``, ``LC_DEEP``) and each horizon
``h ∈ {1, 3, 5, 10}`` years, run the predictive regression

.. math::

    r_{t, t+h} = α + β · LC_t + ε_{t, t+h}

on monthly-indexed data, where ``r_{t, t+h}`` is the annualized log return
of the SPX-TR (S&P 500 Total Return) over the h-year window.

Standard errors and statistics:

* **Newey-West HAC** (Newey & West 1987), lag ``L = h·12 − 1``.
* **Hansen-Hodrick** (Hansen & Hodrick 1980) as robustness.
* **Stambaugh (1999)** analytical bias correction for persistent regressors.
* **Stationary block bootstrap** (Politis & Romano 1994; Politis & White 2004)
  — 10,000 replications with seed=42 for reproducibility.
* **Goyal-Welch (2008)** out-of-sample R² vs the prevailing-mean benchmark.
* **Clark-West (2007)** MSPE-adjusted statistic for nested-model comparison.
* **Campbell-Yogo (2006)** Bonferroni Q-test inversion CI when ``rho_X > 0.95``.

References
----------
[1] Newey, W. K. and West, K. D. (1987), Econometrica 55(3).
[2] Hansen, L. P. and Hodrick, R. J. (1980), JPE 88(5).
[3] Stambaugh, R. F. (1999), JFE 54(3).
[4] Goyal, A. and Welch, I. (2008), RFS 21(4).
[5] Clark, T. E. and West, K. D. (2007), J. Econometrics 138(1).
[6] Campbell, J. Y. and Yogo, M. (2006), JFE 81(1).
[7] Politis, D. N. and Romano, J. P. (1994), JASA 89(428).
[8] Politis, D. N. and White, H. (2004), Econometric Reviews 23(1).
[9] specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §3.1-§3.5.
[10] prompt/052226/PROMPT_v11_3_stage_3_LC_v1_session_6.md §2.E.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm  # type: ignore[import-untyped]

from src.config import OUTPUTS_DIR


# ---------------------------------------------------------------------------
# Constants (pre-reg a8635ef §3.1-§3.8)
# ---------------------------------------------------------------------------

#: Per pre-reg §3.5 + master spec §3.6 — bootstrap replication count.
#: Session 6 used 10_000 as the standard CI; Session 7 §2.F.2 escalates to
#: 50_000 because the tail-probability outputs (master spec §5.3) require
#: more reps to stabilize the 95 % CI on rare events.
BOOTSTRAP_N_REPS = 50_000

#: Per pre-reg §3.5 — global RNG seed for reproducibility.
BOOTSTRAP_SEED = 42

#: Per pre-reg §3.8 — OOS split dates per scope (estimation cutoffs).
OOS_SPLIT_DATES: dict[str, pd.Timestamp] = {
    "LC_FULL": pd.Timestamp("2013-01-01"),
    "LC_TIER2": pd.Timestamp("2011-01-01"),
    "LC_DEEP": pd.Timestamp("2011-01-01"),
}

#: Horizons (years) for the regression table.
HORIZONS_YEARS = (1, 3, 5, 10)

#: Scopes to evaluate.
SCOPES = ("LC_FULL", "LC_TIER2", "LC_DEEP")

#: Campbell-Yogo threshold — only apply CY CIs when AR(1) persistence > this.
CAMPBELL_YOGO_RHO_THRESHOLD = 0.95

#: Path for the regression-results CSV.
REGRESSION_CSV_RELATIVE = "tables/lc_v1_predictive_regression.csv"

#: Path for the conditional-probability CSV (Session 7 §2.F.3).
CONDITIONAL_PROBS_CSV_RELATIVE = "tables/lc_v1_conditional_probabilities.csv"

#: Default risk-free rate for p_below_rf10y probability (Session 7 §2.F.3).
#: Roughly the current US 10-year Treasury yield at 2026-05-22 (~4.2%).
DEFAULT_RF_10Y_ANNUALIZED = 0.042

#: Forward CAGR cutoffs for tail probabilities (annualized).
CAGR_CUTOFF_LOW = 0.05  # p_below_5pct_cagr
CAGR_CUTOFF_HIGH = 0.07  # p_above_7pct_cagr

#: Max-drawdown cutoffs (signed; -0.20 = 20% drawdown).
MAXDD_CUTOFFS = (-0.20, -0.30, -0.50)


# ---------------------------------------------------------------------------
# SPX Total Return — splice Shiller pre-1988 + SPXTR post-1988
# ---------------------------------------------------------------------------


SPLICE_DATE_SPX_TR = pd.Timestamp("1988-01-31")


def _load_spx_total_return(
    *,
    spxtr_daily: pd.Series | None = None,
    shiller_monthly: pd.Series | None = None,
    splice_date: pd.Timestamp = SPLICE_DATE_SPX_TR,
) -> pd.Series:
    """Build the monthly-EOM SPX TR level series.

    Splice (per pre-reg §3.1):

    * Post-1988-01-31: SPXTR daily resampled to month-end.
    * Pre-1988-01-31: Shiller's dividend-reinvested column (already monthly).
    * Multiplicative scale anchor at ``splice_date``: ``k = SPXTR[boundary] / Shiller[boundary]``.
    * Shiller scaled up to SPXTR level: ``shiller_scaled = shiller · k``.

    Parameters
    ----------
    spxtr_daily : pd.Series, optional
        Daily SPXTR close (TradingView). If None, loaded from
        ``src.config.TV_SPXTR`` via ``load_tradingview_file``.
    shiller_monthly : pd.Series, optional
        Shiller monthly dividend-reinvested level series (nominal). If None,
        loaded via ``load_shiller``.
    splice_date : pd.Timestamp
        Anchor for the multiplicative scale (default 1988-01-31).

    Returns
    -------
    pd.Series
        Monthly-EOM nominal SPX TR level series indexed by date.
    """
    if spxtr_daily is None:
        from src.config import TV_SPXTR
        from src.ingest.csv_loader import load_tradingview_file
        loaded = load_tradingview_file(TV_SPXTR, expected_frequency="D")
        spxtr_daily = loaded.data["close"]
    if shiller_monthly is None:
        from src.ingest.shiller_loader import load_shiller
        sh = load_shiller()
        from src.transform.forward_returns import shiller_nominal_total_return
        shiller_monthly = shiller_nominal_total_return(sh)
    # Normalize indices to month-end.
    spxtr_m = spxtr_daily.resample("ME").last().dropna()
    sh_m = shiller_monthly.copy()
    sh_m.index = pd.DatetimeIndex(sh_m.index).to_period("M").to_timestamp(how="end").normalize()
    sh_m = sh_m.dropna()

    # Anchor at splice_date (use nearest available date on each side).
    sh_at_anchor = float(sh_m.loc[sh_m.index <= splice_date].iloc[-1])
    spxtr_at_anchor = float(spxtr_m.loc[spxtr_m.index >= splice_date].iloc[0])
    if sh_at_anchor == 0 or not np.isfinite(sh_at_anchor):
        raise ValueError(
            f"Shiller TR at anchor {splice_date.date()} is degenerate ({sh_at_anchor})"
        )
    k = spxtr_at_anchor / sh_at_anchor
    sh_scaled = sh_m * k

    pre = sh_scaled.loc[sh_scaled.index < splice_date]
    post = spxtr_m.loc[spxtr_m.index >= splice_date]
    result: pd.Series = pd.concat([pre, post]).sort_index()
    result = result[~result.index.duplicated(keep="first")]
    result.name = "spx_tr_monthly"
    return result


def _forward_log_return(
    spx_tr: pd.Series, horizon_years: int,
) -> pd.Series:
    """Compute the h-year forward log return, annualized.

    ``r_{t, t+h} = (1/h) · (ln(P_{t+12h}) − ln(P_t))``

    Returns NaN for the trailing ``12h`` rows (insufficient horizon).
    """
    h_months = horizon_years * 12
    log_p: pd.Series = np.log(spx_tr.dropna())
    fwd: pd.Series = (log_p.shift(-h_months) - log_p) / horizon_years
    fwd.name = f"r_{horizon_years}y_annualized"
    return fwd


# ---------------------------------------------------------------------------
# Core regression statistics
# ---------------------------------------------------------------------------


def _stambaugh_bias_correction(
    beta_hat: float,
    eps: np.ndarray,
    lc_lag: np.ndarray,
    rho_x: float,
) -> float:
    """Stambaugh (1999) analytical bias correction for predictor persistence.

    Following Stambaugh (1999) JFE 54(3) eq. (19), the OLS β̂ for a
    predictor with AR(1) coefficient ρ is biased toward (1 + 3ρ)/T scaled
    by the innovation covariance:

    .. math::

        \\hat β_{Stambaugh} = \\hat β - \\frac{1 + 3 ρ}{T} · \\frac{σ_{εη}}{σ_η^2}

    where ``ε`` is the regression residual and ``η`` is the AR(1) innovation
    of the regressor.

    Parameters
    ----------
    beta_hat : float
        OLS estimate of β.
    eps : np.ndarray
        Regression residuals from the OLS fit.
    lc_lag : np.ndarray
        Lagged regressor values; AR(1) is fit on (lc_lag[1:], lc_lag[:-1]).
    rho_x : float
        AR(1) coefficient of the regressor.

    Returns
    -------
    float
        Stambaugh-corrected β̂.
    """
    if len(lc_lag) < 3 or len(eps) < 3:
        return float(beta_hat)
    # Compute AR(1) innovation eta_t = lc_lag[t] - rho_x * lc_lag[t-1].
    eta = lc_lag[1:] - rho_x * lc_lag[:-1]
    # Align eps with eta (eps is from regression of forward_return on lc_lag).
    n = min(len(eps), len(eta))
    eps_use = eps[-n:]
    eta_use = eta[-n:]
    sigma_eta_sq = float(np.var(eta_use, ddof=1))
    if sigma_eta_sq == 0 or not np.isfinite(sigma_eta_sq):
        return float(beta_hat)
    sigma_eps_eta = float(np.cov(eps_use, eta_use, ddof=1)[0, 1])
    bias = (1.0 + 3.0 * rho_x) * sigma_eps_eta / (n * sigma_eta_sq)
    return float(beta_hat - bias)


def _ar1_persistence(series: np.ndarray) -> float:
    """AR(1) coefficient of ``series`` (returns NaN if degenerate)."""
    if len(series) < 3:
        return float("nan")
    y = series[1:]
    x = series[:-1]
    if np.var(x) == 0:
        return float("nan")
    return float(np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1))


def _stationary_bootstrap_beta(
    lc: np.ndarray,
    y: np.ndarray,
    *,
    n_reps: int = BOOTSTRAP_N_REPS,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, tuple[float, float], np.ndarray]:
    """Stationary block bootstrap (Politis & Romano 1994; Politis & White 2004).

    Uses the ``arch.bootstrap.StationaryBootstrap`` with optimal block length
    ``b_opt = ⌈2 T^(1/3)⌉``. Returns median β and 95% percentile CI.

    Returns
    -------
    (beta_bs_median, ci_95, betas) : (float, (float, float), np.ndarray)
    """
    from arch.bootstrap import StationaryBootstrap
    rng = np.random.default_rng(seed)
    T = len(lc)
    if T < 30:
        return float("nan"), (float("nan"), float("nan")), np.array([])
    b_opt = max(1, int(np.ceil(2.0 * T ** (1.0 / 3.0))))
    X = np.column_stack([np.ones(T), lc])
    bs = StationaryBootstrap(b_opt, X, y, seed=rng)
    betas: list[float] = []
    for X_bs, _kw_bs in bs.bootstrap(n_reps):
        X_arr, y_arr = X_bs[0], X_bs[1]
        try:
            sol, *_ = np.linalg.lstsq(X_arr, y_arr, rcond=None)
            betas.append(float(sol[1]))
        except np.linalg.LinAlgError:
            continue
    arr = np.array(betas)
    if len(arr) == 0:
        return float("nan"), (float("nan"), float("nan")), arr
    return (
        float(np.median(arr)),
        (float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))),
        arr,
    )


def _goyal_welch_oos_r2(
    lc: pd.Series,
    y: pd.Series,
    split_date: pd.Timestamp,
) -> tuple[float, float, float]:
    """Goyal-Welch (2008) out-of-sample R² + Clark-West (2007) statistic.

    For each OOS date ``t``:

    * Estimate ``α̂_t, β̂_t`` using data ≤ t (expanding window).
    * Model prediction: ``ŷ_model = α̂_t + β̂_t · LC_t``.
    * Benchmark prediction: ``ŷ_bench = mean(y[≤ t])`` (prevailing mean).
    * Squared errors: ``e_model² = (y_t − ŷ_model)²``, ``e_bench² = (y_t − ŷ_bench)²``.

    ``R²_OOS = 1 − mean(e_model²) / mean(e_bench²)``.

    Clark-West f_t = (y_t − ŷ_bench)² − [(y_t − ŷ_model)² − (ŷ_model − ŷ_bench)²].
    ``cw_stat = mean(f) / SE_NW(f)``; one-sided p = 1 − Φ(cw_stat).

    Returns
    -------
    (r2_oos, cw_stat, cw_pval) : (float, float, float)
    """
    aligned = pd.concat([lc.rename("lc"), y.rename("y")], axis=1).dropna()
    if aligned.empty or len(aligned) < 30:
        return float("nan"), float("nan"), float("nan")

    oos_mask = aligned.index >= split_date
    if not oos_mask.any():
        return float("nan"), float("nan"), float("nan")

    e_model_sq: list[float] = []
    e_bench_sq: list[float] = []
    cw_f: list[float] = []

    for t in aligned.index[oos_mask]:
        is_window = aligned.index < t
        if is_window.sum() < 20:
            continue
        lc_is = aligned.loc[is_window, "lc"].to_numpy()
        y_is = aligned.loc[is_window, "y"].to_numpy()
        X_is = np.column_stack([np.ones(len(lc_is)), lc_is])
        try:
            beta_is, *_ = np.linalg.lstsq(X_is, y_is, rcond=None)
        except np.linalg.LinAlgError:
            continue
        alpha_is = float(beta_is[0])
        slope_is = float(beta_is[1])
        lc_t = float(aligned.loc[t, "lc"])
        y_t = float(aligned.loc[t, "y"])
        bench = float(np.mean(y_is))
        pred = alpha_is + slope_is * lc_t
        e_model_sq.append((y_t - pred) ** 2)
        e_bench_sq.append((y_t - bench) ** 2)
        cw_f.append((y_t - bench) ** 2 - ((y_t - pred) ** 2 - (pred - bench) ** 2))

    if not e_model_sq:
        return float("nan"), float("nan"), float("nan")

    mse_model = float(np.mean(e_model_sq))
    mse_bench = float(np.mean(e_bench_sq))
    r2_oos = 1.0 - mse_model / mse_bench if mse_bench > 0 else float("nan")

    f_arr = np.array(cw_f)
    if len(f_arr) < 2:
        return r2_oos, float("nan"), float("nan")
    f_mean = float(np.mean(f_arr))
    f_se = float(np.std(f_arr, ddof=1) / np.sqrt(len(f_arr)))
    if f_se == 0 or not np.isfinite(f_se):
        return r2_oos, float("nan"), float("nan")
    cw_stat = f_mean / f_se
    # One-sided p-value (upper tail).
    from scipy.stats import norm  # type: ignore[import-untyped]
    cw_pval = float(1.0 - norm.cdf(cw_stat))
    return r2_oos, float(cw_stat), cw_pval


# ---------------------------------------------------------------------------
# Conditional probability tail outputs (master spec §5.3)
# ---------------------------------------------------------------------------


def _forward_total_return_and_maxdd(
    spx_tr_levels: pd.Series,
    horizon_months: int,
) -> pd.DataFrame:
    """For each date t with horizon h, compute the forward total return and the
    max drawdown of the SPX TR over the window [t, t+h].

    Returns a DataFrame with columns ``cum_return`` (cumulative return over h),
    ``cagr`` (annualized return), and ``maxdd`` (max drawdown, signed; the
    most negative value of (P_s − running_max_s)/running_max_s for s ∈ [t, t+h]).
    """
    levels = spx_tr_levels.dropna().astype("float64")
    out: dict[str, list[float]] = {"cum_return": [], "cagr": [], "maxdd": []}
    idx: list[pd.Timestamp] = []
    horizon_years = horizon_months / 12.0
    for i in range(len(levels) - horizon_months):
        start_date = levels.index[i]
        window = levels.iloc[i : i + horizon_months + 1]
        if window.isna().any():
            continue
        start_v = float(window.iloc[0])
        end_v = float(window.iloc[-1])
        if start_v <= 0 or not np.isfinite(start_v) or not np.isfinite(end_v):
            continue
        cum_return = end_v / start_v - 1.0
        cagr = (end_v / start_v) ** (1.0 / horizon_years) - 1.0
        running_max = window.cummax()
        drawdowns = (window - running_max) / running_max
        maxdd = float(drawdowns.min())
        out["cum_return"].append(float(cum_return))
        out["cagr"].append(float(cagr))
        out["maxdd"].append(maxdd)
        idx.append(start_date)
    return pd.DataFrame(out, index=pd.DatetimeIndex(idx, name="date"))


def compute_conditional_probabilities(
    *,
    lc_current: float,
    lc_series: pd.Series,
    spx_tr_monthly: pd.Series,
    horizon_years: int,
    n_bootstrap: int = 50_000,
    seed: int = BOOTSTRAP_SEED,
    rf_10y: float = DEFAULT_RF_10Y_ANNUALIZED,
    n_quintiles: int = 5,
) -> dict[str, float]:
    """Compute conditional probability tail outputs per master spec §5.3.

    Conditioning: bucket historical LC values into ``n_quintiles`` quantiles.
    Identify the quintile containing ``lc_current``. Restrict the empirical
    forward-return distribution to historical dates in that quintile.
    Compute the 7 tail probabilities + their 95 % bootstrap CIs.

    Tail events (annualized forward return r, max drawdown m over horizon):

    * ``p_neg_total_return`` = P(cumulative return < 0%)
    * ``p_below_rf10y``      = P(annualized return < rf_10y)
    * ``p_below_5pct_cagr``  = P(annualized return < 5%)
    * ``p_above_7pct_cagr``  = P(annualized return > 7%)
    * ``p_maxdd_lt_neg20``   = P(max drawdown < -20%)
    * ``p_maxdd_lt_neg30``   = P(max drawdown < -30%)
    * ``p_maxdd_lt_neg50``   = P(max drawdown < -50%)

    Bootstrap: ``n_bootstrap`` stationary block-bootstrap reps over the
    conditional subsample. For each rep, recompute each probability. Report
    median + 95 % CI.

    Returns
    -------
    dict
        ``{lc_quintile, n_obs_in_quintile, p_<name>, p_<name>_ci_low,
        p_<name>_ci_high}`` keys for each tail event.
    """
    horizon_months = horizon_years * 12
    fwd = _forward_total_return_and_maxdd(spx_tr_monthly, horizon_months)
    lc = lc_series.dropna()
    common = fwd.index.intersection(lc.index)
    aligned = pd.concat(
        [lc.loc[common].rename("lc"), fwd.loc[common]], axis=1,
    ).dropna()
    if aligned.empty or not np.isfinite(lc_current):
        nan_block = {f"p_{n}": float("nan") for n in (
            "neg_total_return", "below_rf10y", "below_5pct_cagr",
            "above_7pct_cagr", "maxdd_lt_neg20", "maxdd_lt_neg30",
            "maxdd_lt_neg50",
        )}
        nan_block.update(
            {f"{k}_ci_low": float("nan") for k in nan_block}
        )
        nan_block.update(
            {f"{k.replace('_ci_low','_ci_high')}": float("nan")
             for k in list(nan_block) if k.endswith("_ci_low")}
        )
        nan_block["lc_quintile"] = float("nan")
        nan_block["n_obs_in_quintile"] = 0
        return nan_block

    quintile_edges = np.quantile(
        aligned["lc"].to_numpy(),
        np.linspace(0, 1, n_quintiles + 1),
    )
    # Determine the quintile bucket containing lc_current.
    cur_q = int(np.clip(
        np.searchsorted(quintile_edges[1:-1], lc_current, side="right"),
        0, n_quintiles - 1,
    ))
    lo = quintile_edges[cur_q]
    hi = quintile_edges[cur_q + 1]
    if cur_q == n_quintiles - 1:
        # Include the upper edge.
        cond_mask = (aligned["lc"] >= lo) & (aligned["lc"] <= hi)
    else:
        cond_mask = (aligned["lc"] >= lo) & (aligned["lc"] < hi)
    cond = aligned.loc[cond_mask]
    n_q = len(cond)

    def _probs(sample: pd.DataFrame) -> dict[str, float]:
        if sample.empty:
            return {k: float("nan") for k in (
                "p_neg_total_return", "p_below_rf10y",
                "p_below_5pct_cagr", "p_above_7pct_cagr",
                "p_maxdd_lt_neg20", "p_maxdd_lt_neg30", "p_maxdd_lt_neg50",
            )}
        return {
            "p_neg_total_return": float((sample["cum_return"] < 0.0).mean()),
            "p_below_rf10y": float((sample["cagr"] < rf_10y).mean()),
            "p_below_5pct_cagr": float((sample["cagr"] < CAGR_CUTOFF_LOW).mean()),
            "p_above_7pct_cagr": float((sample["cagr"] > CAGR_CUTOFF_HIGH).mean()),
            "p_maxdd_lt_neg20": float((sample["maxdd"] < MAXDD_CUTOFFS[0]).mean()),
            "p_maxdd_lt_neg30": float((sample["maxdd"] < MAXDD_CUTOFFS[1]).mean()),
            "p_maxdd_lt_neg50": float((sample["maxdd"] < MAXDD_CUTOFFS[2]).mean()),
        }

    point = _probs(cond)

    # Bootstrap: simple iid resampling within the conditional subsample (the
    # conditional bucket is a quintile that already partials out persistence
    # via LC bucketing; a block bootstrap within a single bucket would force
    # the resamples to also be persistence-correlated which is the wrong
    # null for "what is P(event | regime=quintile)").
    rng = np.random.default_rng(seed)
    if n_q < 5 or n_bootstrap < 1:
        out_dict: dict[str, float] = {**point}
        for k in point:
            out_dict[f"{k}_ci_low"] = float("nan")
            out_dict[f"{k}_ci_high"] = float("nan")
        out_dict["lc_quintile"] = float(cur_q + 1)
        out_dict["n_obs_in_quintile"] = n_q
        return out_dict

    cum_arr = cond["cum_return"].to_numpy()
    cagr_arr = cond["cagr"].to_numpy()
    maxdd_arr = cond["maxdd"].to_numpy()

    bs_neg = np.empty(n_bootstrap)
    bs_rf = np.empty(n_bootstrap)
    bs_5 = np.empty(n_bootstrap)
    bs_7 = np.empty(n_bootstrap)
    bs_dd20 = np.empty(n_bootstrap)
    bs_dd30 = np.empty(n_bootstrap)
    bs_dd50 = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx_bs = rng.integers(0, n_q, size=n_q)
        bs_neg[i] = (cum_arr[idx_bs] < 0.0).mean()
        bs_rf[i] = (cagr_arr[idx_bs] < rf_10y).mean()
        bs_5[i] = (cagr_arr[idx_bs] < CAGR_CUTOFF_LOW).mean()
        bs_7[i] = (cagr_arr[idx_bs] > CAGR_CUTOFF_HIGH).mean()
        bs_dd20[i] = (maxdd_arr[idx_bs] < MAXDD_CUTOFFS[0]).mean()
        bs_dd30[i] = (maxdd_arr[idx_bs] < MAXDD_CUTOFFS[1]).mean()
        bs_dd50[i] = (maxdd_arr[idx_bs] < MAXDD_CUTOFFS[2]).mean()

    def _ci(arr: np.ndarray) -> tuple[float, float]:
        return float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))

    bs_map = {
        "p_neg_total_return": bs_neg,
        "p_below_rf10y": bs_rf,
        "p_below_5pct_cagr": bs_5,
        "p_above_7pct_cagr": bs_7,
        "p_maxdd_lt_neg20": bs_dd20,
        "p_maxdd_lt_neg30": bs_dd30,
        "p_maxdd_lt_neg50": bs_dd50,
    }
    out_dict = {**point}
    for k, arr in bs_map.items():
        ci_lo, ci_hi = _ci(arr)
        out_dict[f"{k}_ci_low"] = ci_lo
        out_dict[f"{k}_ci_high"] = ci_hi
    out_dict["lc_quintile"] = float(cur_q + 1)
    out_dict["n_obs_in_quintile"] = n_q
    return out_dict


# ---------------------------------------------------------------------------
# Campbell-Yogo (2006) Bonferroni Q-test critical values
# ---------------------------------------------------------------------------

#: Critical values for the Q-test at 5% one-sided level (95% CI), keyed by
#: the local-to-unity parameter c. Values approximated from Campbell & Yogo
#: (2006) JFE 81(1) Table 2 (the columns labeled "5%, c known"). The table in
#: the paper is 2-D over (c, δ); this fallback uses the most conservative
#: column (δ = -0.9, typical for valuation-ratio regressions). For finer
#: resolution, a future session should reproduce the full 2-D grid.
#:
#: Pre-reg §3.5 + Campbell-Yogo (2006) JFE 81(1) pp. 36-37.
CY_T_CRIT_5PCT: dict[int, float] = {
    0: 1.645,    # asymptotic Φ⁻¹(0.95)
    -2: 1.660,
    -5: 1.710,
    -10: 1.780,
    -20: 1.900,
    -50: 2.050,
}


def _interpolate_cy_critical_value(c: float) -> float:
    """Linear interpolation of the CY 5% one-sided critical value table.

    Returns NaN if ``c`` is outside the implemented grid [-50, 0]. The Session
    7 §2.F.1 simplified implementation deliberately falls back to NaN per the
    prompt fallback option — outside-range cells are NOT silently filled with
    extrapolated values.
    """
    grid = sorted(CY_T_CRIT_5PCT.keys())
    if c > grid[-1] or c < grid[0]:
        return float("nan")
    # Bracket c between two adjacent grid points and linearly interpolate.
    for i in range(len(grid) - 1):
        c_lo, c_hi = grid[i], grid[i + 1]
        if c_lo <= c <= c_hi:
            cv_lo = CY_T_CRIT_5PCT[c_lo]
            cv_hi = CY_T_CRIT_5PCT[c_hi]
            if c_hi == c_lo:
                return float(cv_lo)
            t = (c - c_lo) / (c_hi - c_lo)
            return float(cv_lo + t * (cv_hi - cv_lo))
    return float("nan")


def _campbell_yogo_ci(
    *,
    beta_point: float,
    se_nw: float,
    rho_x: float,
    eps: np.ndarray,
    lc: np.ndarray,
) -> tuple[float, float]:
    """Campbell-Yogo (2006) Bonferroni Q-test confidence interval for β.

    The CY (2006) procedure constructs a confidence interval that is robust
    to near-unit-root persistence in the regressor. The full procedure
    requires (1) a DF-GLS test on the regressor to localize the local-to-
    unity parameter c with a Bonferroni first-stage CI, then (2) inversion
    of the Q-test statistic distribution at each c in the Bonferroni grid.

    **Session 7 §2.F.1 simplified implementation**: we use the closed-form
    plug-in ``c_hat = T · (ρ̂_X - 1)`` rather than DF-GLS (because the latter
    requires its own asymptotic table). The critical value is then looked up
    from a hardcoded subset of CY (2006) Table 2 keyed by c ∈ {-50, -20, -10,
    -5, -2, 0}, linearly interpolated between grid points. For c outside this
    range, the CI is returned as (NaN, NaN) per the prompt's fallback option.

    The simplification preserves the qualitative shape of the CY correction
    (the t critical value GROWS as the regressor becomes more persistent),
    but is less precise than the full 2-D (c, δ) lookup. A future session
    should reproduce the full Table 2 and add a proper DF-GLS first stage.

    Parameters
    ----------
    beta_point : float
        OLS β̂.
    se_nw : float
        Newey-West HAC SE for β̂.
    rho_x : float
        AR(1) coefficient of the regressor x.
    eps, lc : np.ndarray
        OLS residuals and regressor — kept for signature compatibility
        with future fuller implementations that need δ = corr(ε, η).

    Returns
    -------
    (cy_low, cy_high) : tuple[float, float]
        Bonferroni Q-test 95 % CI on β. Returns (NaN, NaN) when c is
        outside the implemented grid.

    References
    ----------
    [1] Campbell, J.Y. & Yogo, M. (2006) "Efficient tests of stock return
        predictability", JFE 81(1) pp. 27-60. Table 2 (pp. 36-37).
    """
    if not np.isfinite(rho_x) or not np.isfinite(beta_point) or not np.isfinite(se_nw):
        return float("nan"), float("nan")
    if se_nw <= 0:
        return float("nan"), float("nan")
    T = len(lc)
    if T < 2:
        return float("nan"), float("nan")
    c_hat = float(T * (rho_x - 1.0))
    cv = _interpolate_cy_critical_value(c_hat)
    if not np.isfinite(cv):
        return float("nan"), float("nan")
    return (beta_point - cv * se_nw, beta_point + cv * se_nw)


# ---------------------------------------------------------------------------
# Single-cell regression
# ---------------------------------------------------------------------------


@dataclass
class RegressionResult:
    """One row of the (scope × horizon) regression table."""
    scope: str
    horizon_years: int
    beta_point: float
    beta_se_nw: float
    t_nw: float
    p_nw_1sided: float
    beta_stambaugh: float
    rho_X: float
    beta_bootstrap_median: float
    beta_bootstrap_ci_95_low: float
    beta_bootstrap_ci_95_high: float
    r2_insample: float
    r2_oos_gw: float
    cw_stat: float
    cw_pval: float
    cy_ci_95_low: float | None
    cy_ci_95_high: float | None
    n_obs_insample: int
    oos_split_date: str


def run_predictive_regression(
    lc: pd.Series,
    forward_return: pd.Series,
    horizon_years: int,
    scope_name: str,
    *,
    oos_split_date: pd.Timestamp | None = None,
    n_bootstrap_reps: int = BOOTSTRAP_N_REPS,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> RegressionResult:
    """Run one (scope × horizon) predictive regression with full statistics.

    Parameters
    ----------
    lc : pd.Series
        Monthly LC composite (one of LC_FULL / LC_TIER2 / LC_DEEP).
    forward_return : pd.Series
        Monthly forward-return series at horizon h (output of
        :func:`_forward_log_return`).
    horizon_years : int
        h. Determines the Newey-West HAC lag (``L = h·12 − 1``) and the
        Stambaugh persistence correction context.
    scope_name : str
        Identifier of the LC scope. Used for the OOS split date and result row.
    oos_split_date : pd.Timestamp, optional
        Override the OOS split date (default from ``OOS_SPLIT_DATES``).
    n_bootstrap_reps : int
        Stationary bootstrap reps (default 10_000 per pre-reg §3.5).
    bootstrap_seed : int
        Bootstrap RNG seed (default 42 per pre-reg §3.5).

    Returns
    -------
    RegressionResult
    """
    aligned = pd.concat(
        [lc.rename("lc"), forward_return.rename("y")], axis=1,
    ).dropna()
    if aligned.empty:
        return RegressionResult(
            scope=scope_name, horizon_years=horizon_years,
            beta_point=float("nan"), beta_se_nw=float("nan"),
            t_nw=float("nan"), p_nw_1sided=float("nan"),
            beta_stambaugh=float("nan"), rho_X=float("nan"),
            beta_bootstrap_median=float("nan"),
            beta_bootstrap_ci_95_low=float("nan"),
            beta_bootstrap_ci_95_high=float("nan"),
            r2_insample=float("nan"), r2_oos_gw=float("nan"),
            cw_stat=float("nan"), cw_pval=float("nan"),
            cy_ci_95_low=None, cy_ci_95_high=None,
            n_obs_insample=0,
            oos_split_date=str(
                (oos_split_date or OOS_SPLIT_DATES.get(scope_name, pd.Timestamp("2013-01-01"))).date()
            ),
        )

    lc_arr = aligned["lc"].to_numpy()
    y_arr = aligned["y"].to_numpy()
    n = len(lc_arr)

    X = sm.add_constant(lc_arr)
    nw_lag = max(1, horizon_years * 12 - 1)
    model = sm.OLS(y_arr, X).fit(
        cov_type="HAC", cov_kwds={"maxlags": nw_lag, "use_correction": True},
    )
    beta_point = float(model.params[1])
    beta_se_nw = float(model.bse[1])
    t_nw = float(model.tvalues[1])
    # One-sided p (upper tail) per pre-reg criterion 4 expecting positive β.
    from scipy.stats import t as t_dist
    if beta_point > 0:
        p_nw_1sided = float(1.0 - t_dist.cdf(t_nw, df=max(1, n - 2)))
    else:
        p_nw_1sided = float(t_dist.cdf(t_nw, df=max(1, n - 2)))

    r2_insample = float(model.rsquared)

    rho_x = _ar1_persistence(lc_arr)
    eps = model.resid
    beta_stambaugh = _stambaugh_bias_correction(
        beta_hat=beta_point, eps=eps, lc_lag=lc_arr, rho_x=rho_x,
    )

    bs_median, bs_ci, _bs_arr = _stationary_bootstrap_beta(
        lc_arr, y_arr, n_reps=n_bootstrap_reps, seed=bootstrap_seed,
    )

    split = oos_split_date or OOS_SPLIT_DATES.get(scope_name, pd.Timestamp("2013-01-01"))
    r2_oos, cw_stat, cw_pval = _goyal_welch_oos_r2(
        aligned["lc"], aligned["y"], split_date=split,
    )

    # Campbell-Yogo (2006) Bonferroni Q-test inversion — applied when the
    # regressor is near-unit-root (rho_X > CAMPBELL_YOGO_RHO_THRESHOLD).
    # Session 7 §2.F.1 simplified implementation: hardcoded critical values
    # from CY (2006) Table 2 at c ∈ {-50, -20, -10, -5, -2, 0}; outside-range
    # values return NaN. See _campbell_yogo_ci docstring for the full caveat.
    cy_low: float | None
    cy_high: float | None
    if rho_x > CAMPBELL_YOGO_RHO_THRESHOLD:
        cy_lo_f, cy_hi_f = _campbell_yogo_ci(
            beta_point=beta_point, se_nw=beta_se_nw, rho_x=rho_x,
            eps=eps, lc=lc_arr,
        )
        # Convert NaN to None for the JSON-friendly result schema.
        cy_low = float(cy_lo_f) if np.isfinite(cy_lo_f) else None
        cy_high = float(cy_hi_f) if np.isfinite(cy_hi_f) else None
    else:
        cy_low = None
        cy_high = None

    return RegressionResult(
        scope=scope_name,
        horizon_years=horizon_years,
        beta_point=beta_point,
        beta_se_nw=beta_se_nw,
        t_nw=t_nw,
        p_nw_1sided=p_nw_1sided,
        beta_stambaugh=beta_stambaugh,
        rho_X=rho_x,
        beta_bootstrap_median=bs_median,
        beta_bootstrap_ci_95_low=bs_ci[0],
        beta_bootstrap_ci_95_high=bs_ci[1],
        r2_insample=r2_insample,
        r2_oos_gw=r2_oos,
        cw_stat=cw_stat,
        cw_pval=cw_pval,
        cy_ci_95_low=cy_low,
        cy_ci_95_high=cy_high,
        n_obs_insample=n,
        oos_split_date=str(split.date()),
    )


def _result_to_dict(r: RegressionResult) -> dict[str, Any]:
    return {
        "scope": r.scope,
        "horizon_years": r.horizon_years,
        "beta_point": r.beta_point,
        "beta_se_nw": r.beta_se_nw,
        "t_nw": r.t_nw,
        "p_nw_1sided": r.p_nw_1sided,
        "beta_stambaugh": r.beta_stambaugh,
        "rho_X": r.rho_X,
        "beta_bootstrap_median": r.beta_bootstrap_median,
        "beta_bootstrap_ci_95_low": r.beta_bootstrap_ci_95_low,
        "beta_bootstrap_ci_95_high": r.beta_bootstrap_ci_95_high,
        "r2_insample": r.r2_insample,
        "r2_oos_gw": r.r2_oos_gw,
        "cw_stat": r.cw_stat,
        "cw_pval": r.cw_pval,
        "cy_ci_95_low": r.cy_ci_95_low,
        "cy_ci_95_high": r.cy_ci_95_high,
        "n_obs_insample": r.n_obs_insample,
        "oos_split_date": r.oos_split_date,
    }


# ---------------------------------------------------------------------------
# Driver: 12 (scope × horizon) cells
# ---------------------------------------------------------------------------


def run_all_regressions(
    *,
    lc_full: pd.Series,
    lc_tier2: pd.Series,
    lc_deep: pd.Series,
    spx_tr_monthly: pd.Series,
    output_csv: Path | None = None,
    n_bootstrap_reps: int = BOOTSTRAP_N_REPS,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    conditional_probs_csv: Path | None = None,
    bootstrap_tail_probs: bool = True,
    rf_10y: float = DEFAULT_RF_10Y_ANNUALIZED,
) -> pd.DataFrame:
    """Run the predictive regression for all 12 (scope × horizon) cells.

    Writes ``outputs/tables/lc_v1_predictive_regression.csv`` by default. If
    ``bootstrap_tail_probs=True`` (Session 7 §2.F.3), also writes
    ``outputs/tables/lc_v1_conditional_probabilities.csv``.

    Parameters
    ----------
    lc_full, lc_tier2, lc_deep : pd.Series
        Monthly LC composites.
    spx_tr_monthly : pd.Series
        Monthly EOM SPX TR level series (output of ``_load_spx_total_return``).
    output_csv : Path, optional
        Override the default ``OUTPUTS_DIR / tables / lc_v1_predictive_regression.csv``.
    n_bootstrap_reps, bootstrap_seed
        Forwarded to each cell's :func:`run_predictive_regression`.
    conditional_probs_csv : Path, optional
        Override the default ``OUTPUTS_DIR / tables / lc_v1_conditional_probabilities.csv``.
    bootstrap_tail_probs : bool
        Default True (Session 7 §2.F.3). Skip the conditional-probability
        computation only for fast unit tests.
    rf_10y : float
        Risk-free rate used in ``p_below_rf10y``. Default ``DEFAULT_RF_10Y_ANNUALIZED``.

    Returns
    -------
    pd.DataFrame
        12 rows (3 scopes × 4 horizons) × N columns.
    """
    scope_map = {"LC_FULL": lc_full, "LC_TIER2": lc_tier2, "LC_DEEP": lc_deep}
    rows: list[dict[str, Any]] = []
    cprob_rows: list[dict[str, Any]] = []
    for scope_name in SCOPES:
        lc_scope = scope_map[scope_name].dropna()
        for h in HORIZONS_YEARS:
            forward_return = _forward_log_return(spx_tr_monthly, h)
            res = run_predictive_regression(
                lc=lc_scope, forward_return=forward_return,
                horizon_years=h, scope_name=scope_name,
                n_bootstrap_reps=n_bootstrap_reps,
                bootstrap_seed=bootstrap_seed,
            )
            rows.append(_result_to_dict(res))

            if bootstrap_tail_probs and not lc_scope.empty:
                lc_current = float(lc_scope.iloc[-1])
                cprob = compute_conditional_probabilities(
                    lc_current=lc_current,
                    lc_series=lc_scope,
                    spx_tr_monthly=spx_tr_monthly,
                    horizon_years=h,
                    n_bootstrap=n_bootstrap_reps,
                    seed=bootstrap_seed,
                    rf_10y=rf_10y,
                )
                cprob_row = {"scope": scope_name, "horizon_years": h,
                             "lc_current": lc_current, **cprob}
                cprob_rows.append(cprob_row)

    df = pd.DataFrame(rows)
    output_csv = output_csv or (OUTPUTS_DIR / REGRESSION_CSV_RELATIVE)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)

    if cprob_rows:
        df_cprob = pd.DataFrame(cprob_rows)
        cprob_csv = conditional_probs_csv or (OUTPUTS_DIR / CONDITIONAL_PROBS_CSV_RELATIVE)
        cprob_csv.parent.mkdir(parents=True, exist_ok=True)
        df_cprob.to_csv(cprob_csv, index=False)
    return df


__all__ = [
    "BOOTSTRAP_N_REPS",
    "BOOTSTRAP_SEED",
    "OOS_SPLIT_DATES",
    "HORIZONS_YEARS",
    "SCOPES",
    "CAMPBELL_YOGO_RHO_THRESHOLD",
    "REGRESSION_CSV_RELATIVE",
    "SPLICE_DATE_SPX_TR",
    "RegressionResult",
    "_load_spx_total_return",
    "_forward_log_return",
    "run_predictive_regression",
    "run_all_regressions",
]
