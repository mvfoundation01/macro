"""Bayesian posterior for forward returns: Normal-Normal conjugate update.

If PyMC is available we could swap in a full MCMC version, but the closed-form
Normal-Normal update is sufficient (and much faster) for the v5 headline. PyMC
is intentionally NOT a hard requirement -- the spec explicitly lists it as
optional.
"""
from __future__ import annotations

from typing import Any

import numpy as np


# Master Spec section 5.1c: Gordon Growth Model prior for long-run nominal CAGR.
DEFAULT_GORDON_PRIOR: dict[str, float] = {"mean": 0.07, "sd": 0.015}


def bayesian_forward_return(
    z_current: float,
    regression_result: dict[str, Any],
    *,
    gordon_growth_prior: dict[str, float] | None = None,
    use_pymc: bool = False,
    residual_sd_override: float | None = None,
) -> dict[str, Any]:
    """Normal-Normal posterior on the next h-period CAGR given current z.

    Prior:        Gordon Growth (default mean 7% nominal, SD 1.5%).
    Likelihood:   point prediction from the predictive regression
                  ``mu_lik = alpha + beta * z_current``, with SD equal to the
                  in-sample residual SD (or ``residual_sd_override``).
    Posterior:    closed-form Normal-Normal conjugate update.

    Returns dict with ``posterior_mean``, ``posterior_sd``, credible
    intervals at 50/80/95, ``prior``, ``likelihood``, ``method``.
    """
    prior = dict(gordon_growth_prior or DEFAULT_GORDON_PRIOR)
    if "mean" not in prior or "sd" not in prior:
        raise ValueError("gordon_growth_prior must contain 'mean' and 'sd'")
    prior_mean = float(prior["mean"])
    prior_sd = float(prior["sd"])
    if prior_sd <= 0:
        raise ValueError("prior SD must be positive")

    alpha = float(regression_result["alpha"])
    beta = float(regression_result["beta"])
    mu_lik = alpha + beta * float(z_current)

    if residual_sd_override is not None:
        sd_lik = float(residual_sd_override)
    else:
        # Residual SD from R^2 + the variance of r is not stored in the result
        # dict; approximate via Newey-West beta SE scaled by sqrt(n_obs) -> a
        # rough but stable proxy for the conditional SD.
        n_obs = max(2, int(regression_result.get("n_obs", 100)))
        se_nw = float(regression_result.get("beta_se_nw", 0.02))
        sd_lik = max(1e-6, se_nw * np.sqrt(max(1, n_obs - 2)))

    if sd_lik <= 0:
        sd_lik = max(1e-6, prior_sd)

    # Closed-form Normal-Normal update.
    prior_prec = 1.0 / (prior_sd ** 2)
    lik_prec = 1.0 / (sd_lik ** 2)
    post_prec = prior_prec + lik_prec
    post_mean = (prior_prec * prior_mean + lik_prec * mu_lik) / post_prec
    post_sd = float(np.sqrt(1.0 / post_prec))

    # Credible intervals.
    z_table = {0.50: 0.6745, 0.80: 1.2816, 0.95: 1.9600}
    intervals: dict[str, tuple[float, float]] = {}
    for level, crit in z_table.items():
        intervals[f"ci{int(level * 100)}"] = (
            float(post_mean - crit * post_sd),
            float(post_mean + crit * post_sd),
        )

    return {
        "method": "closed_form_normal_normal" if not use_pymc else "pymc_requested_fallback",
        "posterior_mean": float(post_mean),
        "posterior_sd": post_sd,
        **intervals,
        "prior": {"mean": prior_mean, "sd": prior_sd},
        "likelihood": {"mean": float(mu_lik), "sd": float(sd_lik)},
        "z_current": float(z_current),
    }


__all__ = ["bayesian_forward_return", "DEFAULT_GORDON_PRIOR"]
