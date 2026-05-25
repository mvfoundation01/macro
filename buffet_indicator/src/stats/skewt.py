"""Conditional skewed-t fit (Hansen 1994) — DRAFT_v4 §3.7 Amendment 3 (seal 2a94417).

References
----------
- Sealed pre-reg §3.7 Amendment 3: Hansen (1994) skewed-t fit with gaussian fallback.
- Sealed pre-reg §11.1 line 731: function signature.
- ``arch`` package API: ``loglikelihood(parameters, resids, sigma2)``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class SkewTFitResult:
    """Result of a conditional skewed-t fit (§3.7 Amendment 3).

    Attributes
    ----------
    distribution_family : str
        Either ``"skewed_t"`` (Hansen 1994 fit succeeded) or
        ``"gaussian_fallback"`` (degenerate residuals; fallback used).
    eta_tail : float | None
        Tail-thickness parameter (Hansen 1994 nu); None if fallback.
    lambda_skew : float | None
        Skew parameter (Hansen 1994 lambda); None if fallback.
    loglikelihood_at_optimum : float
        Log-likelihood at the fitted parameters (finite).
    fallback_reason : str | None
        Reason for fallback if applicable.
    """

    distribution_family: str
    eta_tail: Optional[float]
    lambda_skew: Optional[float]
    loglikelihood_at_optimum: float
    fallback_reason: Optional[str]


def fit_conditional_skew_t(residuals: np.ndarray, *, seed: int) -> SkewTFitResult:
    """Fit Hansen (1994) skewed-t to residuals with deterministic seeding.

    Uses the ``arch`` package's skewed-t implementation. On degenerate
    residuals (e.g., near-zero variance), falls back to a gaussian fit and
    returns ``distribution_family="gaussian_fallback"``.

    Parameters
    ----------
    residuals : np.ndarray
        1-D array of regression residuals (standardized, finite).
    seed : int
        Seed for any stochastic initialization (keyword-only).

    Returns
    -------
    SkewTFitResult

    References
    ----------
    Sealed pre-reg §3.7 Amendment 3 + §11.1 line 731. Tests: ``T06``, ``T07``.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
