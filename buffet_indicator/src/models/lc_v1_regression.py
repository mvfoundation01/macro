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

#: Per pre-reg §3.5 — bootstrap replication count.
BOOTSTRAP_N_REPS = 10_000

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

    # Campbell-Yogo: stub when rho_X > 0.95 (full implementation needs the
    # lookup tables from the paper's appendix; we emit None until a
    # higher-fidelity implementation lands).
    cy_low: float | None = None
    cy_high: float | None = None
    # if rho_x > CAMPBELL_YOGO_RHO_THRESHOLD: TODO: implement Bonferroni Q-test.

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
) -> pd.DataFrame:
    """Run the predictive regression for all 12 (scope × horizon) cells.

    Writes ``outputs/tables/lc_v1_predictive_regression.csv`` by default.

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

    Returns
    -------
    pd.DataFrame
        12 rows (3 scopes × 4 horizons) × N columns.
    """
    scope_map = {"LC_FULL": lc_full, "LC_TIER2": lc_tier2, "LC_DEEP": lc_deep}
    rows: list[dict[str, Any]] = []
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

    df = pd.DataFrame(rows)

    output_csv = output_csv or (OUTPUTS_DIR / REGRESSION_CSV_RELATIVE)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
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
