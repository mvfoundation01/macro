"""Predictive regression v2.0 with NW HAC + Stambaugh + Campbell-Yogo
— DRAFT_v4 §3.3 + §3.5 + §3.6 + §3.9 (seal 2a94417).

References
----------
- Sealed pre-reg §3.3: training set ``{(x_s, r_{s, s+h}) : s + h <= t}``
  (the realized-return cutoff rule).
- Sealed pre-reg §3.4 (Amendment 4): insufficient-sample gate.
- Sealed pre-reg §3.5: HAC standard errors (NW, ``use_correction=True``,
  ``maxlags = horizon_months - 1``).
- Sealed pre-reg §3.6: Stambaugh (1999) bias when ``rho_hat > 0.85``
  strict; Campbell-Yogo (2006) CIs when ``rho_hat > 0.95``.
- Sealed pre-reg §3.9: comparator semantics (strict ``>`` at 0.85 boundary).
- Sealed pre-reg §11.1 line 732: function signature.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.stats.hac import compute_hac_lag
from src.stats.sample_gate import sample_gate_status
from src.stats.stambaugh import should_apply_stambaugh


# Sealed §3.6 boundaries.
STAMBAUGH_LOWER_THRESHOLD: float = 0.85       # strict >; see §3.9
STAMBAUGH_UPPER_THRESHOLD: float = 0.995      # >= -> not_evaluable_rho_boundary
CAMPBELL_YOGO_THRESHOLD: float = 0.95         # > -> CY regime (§3.6)
STAMBAUGH_MIN_N_BASE: int = 120
"""Minimum AR(1)-estimation sample size for Stambaugh: ``max(120, 3 * HAC_lag)``."""


@dataclass(frozen=True)
class RegressionResult:
    """Result of a v2.0 predictive regression cell (§3.3 + §3.5 + §3.6).

    Required attributes (per scaffold + §11.1 line 732)
    --------------------------------------------------
    beta : float
        OLS slope coefficient of the predictor (in-sample fit).
    t_nw : float
        Newey-West HAC t-statistic on ``beta``.
    p_nw : float
        Two-sided NW HAC p-value (Amendment 2 convention: ``|t| > 1.65``).
    stambaugh_status : str
        Enum: ``"computed"`` | ``"not_evaluable_rho_boundary"`` | ``"not_applied"``.
    campbell_yogo_status : str
        Enum: ``"computed_v1_grid"`` | ``"not_evaluable_outside_grid"``.
    rho_ar1 : float
        AR(1) coefficient of the predictor (in-sample).
    n_obs_oos : int
        Out-of-sample observation count (post-realization, per §3.3 / §3.4
        ``s + h <= t`` rule).
    n_eff : float
        HAC-adjusted effective sample size (§3.4 / Amendment 4).
    residuals : object | None
        In-sample residuals (np.ndarray) for downstream skewed-t fit.

    Extended attributes (for verdict JSON in Phase E; backward-compatible
    optional defaults — do NOT remove)
    ------------------------------------
    alpha : float | None
    se_nw_beta : float | None
    n_obs_insample : int | None
    hac_lag : int | None
    gate_status : str | None ("evaluable" / "not_evaluable")
    beta_stambaugh : float | None
    stambaugh_bias : float | None
    campbell_yogo_ci_lower : float | None
    campbell_yogo_ci_upper : float | None
    oos_r2 : float | None        (Goyal-Welch 2008)
    clark_west_stat : float | None
    sigma_hat : float | None
    oos_residuals : object | None  (np.ndarray; None if oos empty)
    """

    beta: float
    t_nw: float
    p_nw: float
    stambaugh_status: str
    campbell_yogo_status: str
    rho_ar1: float
    n_obs_oos: int
    n_eff: float
    residuals: Optional[object] = None
    # Extended optional fields (Phase D additions for verdict JSON / Phase E).
    alpha: Optional[float] = None
    se_nw_beta: Optional[float] = None
    n_obs_insample: Optional[int] = None
    hac_lag: Optional[int] = None
    gate_status: Optional[str] = None
    beta_stambaugh: Optional[float] = None
    stambaugh_bias: Optional[float] = None
    campbell_yogo_ci_lower: Optional[float] = None
    campbell_yogo_ci_upper: Optional[float] = None
    oos_r2: Optional[float] = None
    clark_west_stat: Optional[float] = None
    sigma_hat: Optional[float] = None
    oos_residuals: Optional[object] = None


def _ar1_coefficient(series: np.ndarray) -> float:
    """OLS AR(1) coefficient of a 1-D series; 0.0 if degenerate or too short."""
    n = series.size
    if n < 3:
        return 0.0
    z_t = series[1:]
    z_tm1 = series[:-1]
    z_mean = float(series.mean())
    num = float(np.dot(z_tm1 - z_mean, z_t - z_mean))
    den = float(np.dot(z_tm1 - z_mean, z_tm1 - z_mean))
    if den <= 0.0 or not math.isfinite(den):
        return 0.0
    return float(num / den)


def _stambaugh_bias(
    x: np.ndarray, residuals: np.ndarray, rho_ar1: float
) -> Optional[float]:
    """Stambaugh (1999) analytical bias estimate for the predictive slope.

    Per §3.6 (inherited from v1.0). Returns ``None`` if numerically degenerate.
    """
    n = x.size
    if n < 3 or residuals.size < 2:
        return None
    x_t = x[1:]
    x_tm1 = x[:-1]
    x_mean = float(x.mean())
    u = x_t - x_mean - rho_ar1 * (x_tm1 - x_mean)
    eps_aligned = residuals[1:] if residuals.size == n else residuals[: u.size]
    if eps_aligned.size != u.size:
        eps_aligned = eps_aligned[: u.size]
    if u.size < 2:
        return None
    gamma_eu = float(np.cov(eps_aligned, u, ddof=0)[0, 1])
    gamma_uu = float(np.var(u, ddof=0))
    if gamma_uu <= 0.0 or not math.isfinite(gamma_uu):
        return None
    return float(-(gamma_eu / gamma_uu) * (1.0 + 3.0 * rho_ar1) / n)


def _hac_adjusted_n_eff(residuals: np.ndarray, hac_lag: int, n_count: int) -> float:
    """Effective sample size n_eff per §3.4 / Amendment 4.

    ``n_eff = n_count / (1 + 2 * sum_k max(0, rho_k))`` where ``rho_k`` is
    the lag-k autocorrelation of the residual series. Negative ``rho_k`` are
    truncated at zero for conservatism.
    """
    if n_count <= 0:
        return 0.0
    if hac_lag <= 0 or residuals.size < hac_lag + 2:
        return float(n_count)
    e = residuals - residuals.mean()
    denom = float(np.dot(e, e))
    if denom <= 0.0 or not math.isfinite(denom):
        return float(n_count)
    s = 0.0
    for k in range(1, int(hac_lag) + 1):
        if k >= e.size:
            break
        rho_k = float(np.dot(e[k:], e[:-k]) / denom)
        if math.isfinite(rho_k) and rho_k > 0.0:
            s += rho_k
    denom_eff = 1.0 + 2.0 * s
    if denom_eff <= 0.0:
        return float(n_count)
    return float(n_count) / denom_eff


def _oos_r2_goyal_welch(y_oos: np.ndarray, y_pred: np.ndarray, y_bar_train: float) -> float:
    """OOS R^2 vs prevailing-mean benchmark (Goyal-Welch 2008).

    ``OOS_R2 = 1 - SSE_model / SSE_benchmark`` where benchmark predicts
    ``y_bar_train`` constantly. Returns NaN if benchmark SSE is zero.
    """
    if y_oos.size == 0:
        return float("nan")
    sse_model = float(np.sum((y_oos - y_pred) ** 2))
    sse_bench = float(np.sum((y_oos - y_bar_train) ** 2))
    if sse_bench <= 0.0 or not math.isfinite(sse_bench):
        return float("nan")
    return float(1.0 - sse_model / sse_bench)


def _clark_west_stat(y_oos: np.ndarray, y_pred: np.ndarray, y_bar_train: float) -> float:
    """Clark-West (2007) MSPE-adjusted statistic, mean of f_t / SE(f_t).

    f_t = (y - ybar)^2 - [(y - yhat)^2 - (yhat - ybar)^2]
    Returns NaN if degenerate.
    """
    if y_oos.size < 2:
        return float("nan")
    f = (y_oos - y_bar_train) ** 2 - (
        (y_oos - y_pred) ** 2 - (y_pred - y_bar_train) ** 2
    )
    mean_f = float(np.mean(f))
    se_f = float(np.std(f, ddof=1) / math.sqrt(f.size))
    if se_f <= 0.0 or not math.isfinite(se_f):
        return float("nan")
    return float(mean_f / se_f)


def _classify_stambaugh(rho_ar1: float, n_train: int, hac_lag: int) -> str:
    """Stambaugh status per §3.6 + §3.9."""
    n_min = max(STAMBAUGH_MIN_N_BASE, 3 * int(hac_lag))
    if not math.isfinite(rho_ar1):
        return "not_evaluable_rho_boundary"
    if rho_ar1 >= STAMBAUGH_UPPER_THRESHOLD:
        return "not_evaluable_rho_boundary"
    if n_train < n_min:
        return "not_evaluable_rho_boundary"
    if should_apply_stambaugh(rho_ar1):
        return "computed"
    return "not_applied"


def _classify_campbell_yogo(rho_ar1: float) -> str:
    """Campbell-Yogo status per §3.6.

    Sealed §3.6 + §10.1 endorse Campbell-Yogo (2006) Table 5 critical
    values when ``rho_hat > 0.95``, but the actual grid is not transcribed
    in the sealed pre-reg (Strategist Q3 arbitration: cite-by-reference).
    Pending grid transcription, status reports ``"not_evaluable_outside_grid"``
    for all ``rho`` values; the enum is still always set per T11 invariant.
    """
    if not math.isfinite(rho_ar1):
        return "not_evaluable_outside_grid"
    # Faithful to v1.0 (which did not transcribe the grid): status is
    # always "not_evaluable_outside_grid" until the grid is sealed.
    return "not_evaluable_outside_grid"


def run_predictive_regression_v2(
    x,
    y,
    *,
    horizon_months: int,
    forecast_origin: pd.Timestamp,
) -> RegressionResult:
    """Run a v2.0 predictive regression with NW HAC + bias-correction.

    Per §3.3 + §3.5 + §3.6: aligns ``x`` and ``y``, splits at the
    ``s + h <= forecast_origin`` realization rule, fits OLS-NW HAC
    on the in-sample subset, predicts OOS, and reports Stambaugh /
    Campbell-Yogo / OOS R^2 / Clark-West diagnostics.

    Parameters
    ----------
    x : pd.Series | array-like
        Predictor series with DatetimeIndex (e.g., PIT z-score).
    y : pd.Series | array-like
        Forward-return series aligned to ``x``'s index. ``y[s]`` is
        ``r_{s, s+h}``; the realization date is ``s + h_months``.
    horizon_months : int, keyword-only
        Forecast horizon in months (positive).
    forecast_origin : pd.Timestamp, keyword-only
        OOS split date. Training rows have ``s + h <= forecast_origin``.

    Returns
    -------
    RegressionResult

    References
    ----------
    Sealed pre-reg §3.3 + §3.5 + §3.6 + §3.9 + §11.1 line 732.
    Tests: ``T04`` (HAC config), ``T05`` (s+h<=t row counting),
    ``T11`` (CY status enum always set).
    """
    hac_lag = compute_hac_lag(horizon_months)

    # Coerce to aligned pd.Series; drop NaN pairs.
    xs = pd.Series(x).copy()
    ys = pd.Series(y).copy()
    aligned = (
        pd.concat([xs.rename("x"), ys.rename("y")], axis=1, join="inner")
        .dropna()
        .sort_index()
    )

    # Training cutoff per §3.3: s + h <= forecast_origin  <=>  s <= forecast_origin - h.
    fo = pd.Timestamp(forecast_origin)
    horizon_offset = pd.DateOffset(months=int(horizon_months))
    training_cutoff = fo - horizon_offset

    in_sample = aligned[aligned.index <= training_cutoff]
    oos = aligned[aligned.index > training_cutoff]
    n_obs_insample = int(in_sample.shape[0])
    n_obs_oos = int(oos.shape[0])

    # If insufficient training rows for a 2-parameter OLS fit, return a
    # not-evaluable RegressionResult.
    if n_obs_insample < 3:
        return RegressionResult(
            beta=float("nan"),
            t_nw=float("nan"),
            p_nw=float("nan"),
            stambaugh_status="not_evaluable_rho_boundary",
            campbell_yogo_status="not_evaluable_outside_grid",
            rho_ar1=float("nan"),
            n_obs_oos=n_obs_oos,
            n_eff=0.0,
            residuals=None,
            alpha=None,
            se_nw_beta=None,
            n_obs_insample=n_obs_insample,
            hac_lag=hac_lag,
            gate_status="not_evaluable",
            beta_stambaugh=None,
            stambaugh_bias=None,
            campbell_yogo_ci_lower=None,
            campbell_yogo_ci_upper=None,
            oos_r2=None,
            clark_west_stat=None,
            sigma_hat=None,
            oos_residuals=None,
        )

    x_train = in_sample["x"].to_numpy(dtype="float64")
    y_train = in_sample["y"].to_numpy(dtype="float64")
    X_design = sm.add_constant(x_train, has_constant="add")

    fit = sm.OLS(y_train, X_design).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": max(0, int(hac_lag)), "use_correction": True},
    )
    alpha_hat = float(fit.params[0])
    beta_hat = float(fit.params[1])
    se_nw_beta = float(fit.bse[1])
    t_nw = float(fit.tvalues[1])
    p_nw = float(fit.pvalues[1])  # statsmodels default two-sided per §5.1 Amendment 2

    residuals_train = y_train - (alpha_hat + beta_hat * x_train)
    sigma_hat = float(np.std(residuals_train, ddof=1)) if n_obs_insample > 1 else float("nan")

    # AR(1) of predictor for Stambaugh / Campbell-Yogo triggers.
    rho_ar1 = _ar1_coefficient(x_train)

    # Stambaugh classification + correction.
    stambaugh_status = _classify_stambaugh(rho_ar1, n_obs_insample, hac_lag)
    beta_stambaugh: Optional[float] = None
    stambaugh_bias: Optional[float] = None
    if stambaugh_status == "computed":
        bias = _stambaugh_bias(x_train, residuals_train, rho_ar1)
        if bias is not None and math.isfinite(bias):
            stambaugh_bias = float(bias)
            beta_stambaugh = float(beta_hat - bias)

    # Campbell-Yogo classification.
    campbell_yogo_status = _classify_campbell_yogo(rho_ar1)

    # n_eff via HAC autocorrelation of training residuals (§3.4 / §3.6).
    n_eff = _hac_adjusted_n_eff(residuals_train, hac_lag, n_obs_oos)

    gate_status = sample_gate_status(n_obs_oos, hac_lag, n_eff)

    # OOS evaluation.
    oos_r2: Optional[float] = None
    clark_west_stat: Optional[float] = None
    oos_residuals: Optional[np.ndarray] = None
    if n_obs_oos > 0:
        x_oos = oos["x"].to_numpy(dtype="float64")
        y_oos = oos["y"].to_numpy(dtype="float64")
        y_pred = alpha_hat + beta_hat * x_oos
        y_bar_train = float(np.mean(y_train))
        oos_r2 = _oos_r2_goyal_welch(y_oos, y_pred, y_bar_train)
        clark_west_stat = _clark_west_stat(y_oos, y_pred, y_bar_train)
        oos_residuals = y_oos - y_pred

    return RegressionResult(
        beta=beta_hat,
        t_nw=t_nw,
        p_nw=p_nw,
        stambaugh_status=stambaugh_status,
        campbell_yogo_status=campbell_yogo_status,
        rho_ar1=float(rho_ar1),
        n_obs_oos=n_obs_oos,
        n_eff=float(n_eff),
        residuals=residuals_train,
        alpha=alpha_hat,
        se_nw_beta=se_nw_beta,
        n_obs_insample=n_obs_insample,
        hac_lag=int(hac_lag),
        gate_status=gate_status,
        beta_stambaugh=beta_stambaugh,
        stambaugh_bias=stambaugh_bias,
        campbell_yogo_ci_lower=None,
        campbell_yogo_ci_upper=None,
        oos_r2=oos_r2,
        clark_west_stat=clark_west_stat,
        sigma_hat=sigma_hat,
        oos_residuals=oos_residuals,
    )
