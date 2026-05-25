"""Conditional skewed-t fit (Hansen 1994) — DRAFT_v4 §3.7 Amendment 3 (seal 2a94417).

References
----------
- Sealed pre-reg §3.7 Amendment 3: Hansen (1994) standardized skewed-t
  fit via ``arch.univariate.SkewStudent`` with L-BFGS-B optimization
  and Gaussian fallback on degenerate residuals.
- Bounds: ``eta_tail in [2.05, 200.0]``; ``lambda_skew in [-0.95, 0.95]``.
- Fallback gates: ``n_resid < 120`` OR ``sigma_hat <= 1e-12`` OR
  fewer than 20 unique rounded residuals OR any non-finite residual.
- Sealed pre-reg §11.1 line 731: function signature.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import math
import numpy as np
import scipy.optimize

from arch.univariate import SkewStudent


N_RESID_FLOOR: int = 120
"""Minimum residual count below which Gaussian fallback fires (§3.7.2)."""

SIGMA_FLOOR: float = 1e-12
"""Numerical lower bound on residual std-dev (§3.7.2)."""

UNIQUE_RESID_FLOOR: int = 20
"""Minimum unique rounded-residual count (§3.7.2)."""

ETA_TAIL_BOUNDS: tuple[float, float] = (2.05, 200.0)
"""L-BFGS-B bounds on eta_tail (§3.7.1)."""

LAMBDA_SKEW_BOUNDS: tuple[float, float] = (-0.95, 0.95)
"""L-BFGS-B bounds on lambda_skew (§3.7.1)."""

INITIAL_PARAMETERS: tuple[float, float] = (8.0, 0.0)
"""(eta_tail, lambda_skew) start point for L-BFGS-B (§3.7.2)."""


@dataclass(frozen=True)
class SkewTFitResult:
    """Result of a conditional skewed-t fit (§3.7 Amendment 3).

    Attributes
    ----------
    distribution_family : str
        Either ``"skewed_t"`` (Hansen 1994 fit succeeded) or
        ``"gaussian_fallback"`` (degenerate residuals; fallback used).
    eta_tail : float | None
        Tail-thickness parameter (Hansen 1994 nu / arch ``eta``);
        ``None`` if fallback.
    lambda_skew : float | None
        Skew parameter (Hansen 1994 lambda); ``None`` if fallback.
    loglikelihood_at_optimum : float
        Log-likelihood at the fitted parameters (finite). For Gaussian
        fallback this is the standard-normal log-likelihood of the input
        residuals (so verdict-JSON comparisons remain meaningful).
    fallback_reason : str | None
        Reason for fallback if applicable. One of
        ``"n_resid_lt_120"``, ``"sigma_le_1e-12"``,
        ``"unique_resid_lt_20"``, ``"non_finite_resid"``,
        ``"ml_convergence_failure"``, or ``None``.
    """

    distribution_family: str
    eta_tail: Optional[float]
    lambda_skew: Optional[float]
    loglikelihood_at_optimum: float
    fallback_reason: Optional[str]


def _gaussian_loglik(resid: np.ndarray) -> float:
    """Standard-normal log-likelihood of ``resid`` (for fallback reporting)."""
    n = resid.size
    if n == 0:
        return float("nan")
    return float(-0.5 * n * math.log(2.0 * math.pi) - 0.5 * float(np.sum(resid * resid)))


def _check_fallback(resid: np.ndarray) -> Optional[str]:
    """Apply §3.7.2 fallback gates; return the first triggered reason or None."""
    if not np.all(np.isfinite(resid)):
        return "non_finite_resid"
    if resid.size < N_RESID_FLOOR:
        return "n_resid_lt_120"
    sigma_hat = float(np.std(resid, ddof=1)) if resid.size > 1 else 0.0
    if not np.isfinite(sigma_hat) or sigma_hat <= SIGMA_FLOOR:
        return "sigma_le_1e-12"
    rounded = np.round(resid, decimals=6)
    if np.unique(rounded).size < UNIQUE_RESID_FLOOR:
        return "unique_resid_lt_20"
    return None


def fit_conditional_skew_t(residuals: np.ndarray, *, seed: int) -> SkewTFitResult:
    """Fit Hansen (1994) skewed-t to residuals with deterministic seeding.

    Uses ``arch.univariate.SkewStudent`` and L-BFGS-B ML optimization
    per §3.7.2. On any §3.7.2 fallback gate trigger, returns a
    ``gaussian_fallback`` result with parameters ``None``.

    Parameters
    ----------
    residuals : np.ndarray
        1-D array of standardized regression residuals.
    seed : int
        Seed for any stochastic initialization (used only for the
        underlying ``SkewStudent`` distribution state; deterministic).

    Returns
    -------
    SkewTFitResult

    References
    ----------
    Sealed pre-reg §3.7 Amendment 3 + §11.1 line 731. Tests: ``T06``, ``T07``.
    """
    resid = np.asarray(residuals, dtype="float64").ravel()

    fallback = _check_fallback(resid)
    if fallback is not None:
        return SkewTFitResult(
            distribution_family="gaussian_fallback",
            eta_tail=None,
            lambda_skew=None,
            loglikelihood_at_optimum=_gaussian_loglik(resid),
            fallback_reason=fallback,
        )

    # Standardize for ML so the unit-variance assumption used by the
    # arch `loglikelihood(parameters, resids, sigma2)` interface is
    # satisfied numerically. Mean-zero standardization preserves the
    # Hansen (1994) skewed-t shape parameters.
    mean_hat = float(np.mean(resid))
    sigma_hat = float(np.std(resid, ddof=1))
    std_resid = ((resid - mean_hat) / sigma_hat).astype("float64", copy=False)
    sigma2 = np.ones_like(std_resid)

    dist = SkewStudent(seed=int(seed))

    def _neg_loglik(params: np.ndarray) -> float:
        try:
            value = dist.loglikelihood(np.asarray(params, dtype="float64"), std_resid, sigma2, individual=False)
        except (ValueError, FloatingPointError):
            return float("inf")
        val = float(value)
        return -val if math.isfinite(val) else float("inf")

    start = np.asarray(INITIAL_PARAMETERS, dtype="float64")
    bounds = [ETA_TAIL_BOUNDS, LAMBDA_SKEW_BOUNDS]
    result = scipy.optimize.minimize(
        fun=_neg_loglik,
        x0=start,
        method="L-BFGS-B",
        bounds=bounds,
    )

    if not result.success or not math.isfinite(float(result.fun)):
        return SkewTFitResult(
            distribution_family="gaussian_fallback",
            eta_tail=None,
            lambda_skew=None,
            loglikelihood_at_optimum=_gaussian_loglik(std_resid),
            fallback_reason="ml_convergence_failure",
        )

    eta_tail_hat, lambda_skew_hat = (float(result.x[0]), float(result.x[1]))
    return SkewTFitResult(
        distribution_family="skewed_t",
        eta_tail=eta_tail_hat,
        lambda_skew=lambda_skew_hat,
        loglikelihood_at_optimum=-float(result.fun),
        fallback_reason=None,
    )
