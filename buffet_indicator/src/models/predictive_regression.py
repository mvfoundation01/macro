"""Predictive regression of forward returns on a z-score.

Implements:
    r_{t,t+h} = alpha + beta * z_t + eps_{t,t+h}

with Newey-West HAC SE (PSD, default reporting), Hansen-Hodrick SE
(no Bartlett weights), and Stambaugh (1999) bias-corrected beta.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.ingest._base import IngestError


class InsufficientSampleError(IngestError):
    """Predictive regression requires n_obs >= 30."""


# ---------------------------------------------------------------------------
# Hansen-Hodrick SE
# ---------------------------------------------------------------------------


def _hansen_hodrick_se(
    x: np.ndarray, eps: np.ndarray, max_lag: int
) -> float:
    """Hansen-Hodrick (1980) SE for OLS beta with overlapping returns.

    Computes ``Sigma = Gamma_0 + 2 * sum_{j=1..max_lag} Gamma_j`` (no Bartlett
    weights). Returns ``SE(beta_hat) = sqrt(Sigma) / (sqrt(n) * Var(x))``.
    """
    n = len(x)
    if n == 0:
        return float("nan")
    x_c = x - x.mean()
    u = x_c * eps  # score contributions
    gamma_0 = float(np.dot(u, u) / n)
    s = gamma_0
    for j in range(1, max_lag + 1):
        if j >= n:
            break
        gamma_j = float(np.dot(u[j:], u[:-j]) / n)
        s += 2.0 * gamma_j
    var_x = float(np.var(x_c, ddof=0))
    if var_x <= 0 or not np.isfinite(s) or s <= 0:
        return float("nan")
    return float(np.sqrt(s) / (np.sqrt(n) * var_x))


# ---------------------------------------------------------------------------
# Stambaugh (1999) bias correction
# ---------------------------------------------------------------------------


def _stambaugh_correction(
    z: np.ndarray, eps: np.ndarray, beta_ols: float
) -> dict[str, Any]:
    """Stambaugh (1999) finite-sample bias correction for predictive beta."""
    if z.size < 3:
        return {
            "beta_corrected": float(beta_ols),
            "bias_estimate": 0.0,
            "rho_ar1": 0.0,
            "se_corrected": None,
        }

    z_t = z[1:]
    z_tm1 = z[:-1]
    z_mean = float(z.mean())
    num = float(np.dot(z_tm1 - z_mean, z_t - z_mean))
    den = float(np.dot(z_tm1 - z_mean, z_tm1 - z_mean))
    rho = num / den if den > 0 else 0.0
    u = z_t - z_mean - rho * (z_tm1 - z_mean)

    eps_aligned = eps[1:] if eps.size == z.size else eps[: z_t.size]
    if eps_aligned.size != u.size:
        eps_aligned = eps_aligned[: u.size]
    gamma_eu = float(np.cov(eps_aligned, u, ddof=0)[0, 1])
    gamma_uu = float(np.var(u, ddof=0))

    T = len(z)
    bias = (
        -(gamma_eu / gamma_uu) * (1.0 + 3.0 * rho) / T if gamma_uu > 0 else 0.0
    )
    beta_corrected = beta_ols - bias
    return {
        "beta_corrected": float(beta_corrected),
        "bias_estimate": float(bias),
        "rho_ar1": float(rho),
        "se_corrected": None,  # punt to v5.1
        "gamma_eu": float(gamma_eu),
        "gamma_uu": float(gamma_uu),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def predictive_regression(
    z: pd.Series,
    r_fwd: pd.Series,
    horizon_months: int,
) -> dict[str, Any]:
    """OLS r = alpha + beta * z + eps with HAC SE + Stambaugh correction."""
    import statsmodels.api as sm

    aligned = pd.concat([z, r_fwd], axis=1).dropna()
    aligned.columns = ["z", "r"]
    if len(aligned) < 30:
        raise InsufficientSampleError(
            f"predictive_regression: n={len(aligned)} < 30"
        )

    y = aligned["r"].to_numpy(dtype="float64")
    z_arr = aligned["z"].to_numpy(dtype="float64")
    X = sm.add_constant(z_arr)

    model = sm.OLS(y, X).fit()
    alpha = float(model.params[0])
    beta = float(model.params[1])

    lag_nw = max(1, horizon_months - 1)
    nw = model.get_robustcov_results(
        cov_type="HAC", maxlags=lag_nw, use_correction=True
    )
    beta_se_nw = float(nw.bse[1])
    t_nw = float(nw.tvalues[1])
    pvalue_nw = float(nw.pvalues[1])

    beta_se_hh = _hansen_hodrick_se(z_arr, np.asarray(model.resid), lag_nw)
    t_hh = beta / beta_se_hh if beta_se_hh and beta_se_hh > 0 else float("nan")

    bs = _stambaugh_correction(z_arr, np.asarray(model.resid), beta)

    return {
        "n_obs": int(len(aligned)),
        "alpha": alpha,
        "beta": beta,
        "beta_se_hh": beta_se_hh,
        "beta_se_nw": beta_se_nw,
        "t_hh": t_hh,
        "t_nw": t_nw,
        "pvalue_nw": pvalue_nw,
        "r_squared": float(model.rsquared),
        "beta_stambaugh": bs["beta_corrected"],
        "beta_stambaugh_bias": bs["bias_estimate"],
        "beta_stambaugh_se": bs["se_corrected"],
        "rho_ar1": bs["rho_ar1"],
        "horizon_months": int(horizon_months),
    }


__all__ = [
    "InsufficientSampleError",
    "predictive_regression",
    "_hansen_hodrick_se",
    "_stambaugh_correction",
]
