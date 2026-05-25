"""§11.2 T06+T07 — skewed-t fit + arch API. DRAFT_v4 §3.7 Am.3 (seal 2a94417)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
from arch.univariate import SkewStudent  # noqa: E402

from src.stats.skewt import (  # noqa: E402
    SkewTFitResult,
    fit_conditional_skew_t,
)


def test_skewstudent_loglikelihood_signature_is_used_correctly() -> None:
    """arch API: loglikelihood(parameters, resids, sigma2); finite likelihood.

    NEW per Codex round-2 New-1.
    References: DRAFT_v4 §3.7 Amendment 3 + sealed pre-reg §11.2 T06.
    """
    rng = np.random.default_rng(42)
    raw = rng.standard_t(df=5, size=500)
    # Standardize: standard_t(5) has variance 5/3 -> scale by sqrt(3/5).
    resids = raw * math.sqrt((5 - 2) / 5)

    dist = SkewStudent(seed=42)
    # Direct call to the arch API (NOT TypeError).
    sigma2 = np.ones_like(resids, dtype="float64")
    ll = dist.loglikelihood(
        np.array([8.0, 0.0], dtype="float64"),
        resids.astype("float64"),
        sigma2,
        individual=False,
    )
    assert math.isfinite(float(ll))

    # The fit function uses this same API and produces a skewed-t fit.
    result = fit_conditional_skew_t(resids, seed=42)
    assert isinstance(result, SkewTFitResult)
    assert result.distribution_family == "skewed_t"
    assert math.isfinite(result.loglikelihood_at_optimum)


def test_skewed_t_known_distribution_and_fallback() -> None:
    """seed=42 size=500 standard_t df=5 standardized -> 3.0<=eta_tail<=8.0,
    |lambda|<=0.15; degenerate residuals -> gaussian_fallback.

    Per Codex round-3 New-3 tolerance: interval calibrated to Codex's
    empirical run (eta_tail~4.2542, lambda~-0.0427).
    References: DRAFT_v4 §3.7 Amendment 3 + sealed pre-reg §11.2 T07.
    """
    rng = np.random.default_rng(42)
    raw = rng.standard_t(df=5, size=500)
    resids = raw * math.sqrt((5 - 2) / 5)  # standardize

    result = fit_conditional_skew_t(resids, seed=42)
    assert result.distribution_family == "skewed_t"
    assert result.eta_tail is not None
    assert result.lambda_skew is not None
    assert 3.0 <= result.eta_tail <= 8.0
    assert abs(result.lambda_skew) <= 0.15
    assert result.fallback_reason is None

    # Degenerate: constant residual array -> sigma_hat = 0 -> gaussian fallback.
    constant = np.full(200, 0.5, dtype="float64")
    fb = fit_conditional_skew_t(constant, seed=42)
    assert fb.distribution_family == "gaussian_fallback"
    assert fb.eta_tail is None
    assert fb.lambda_skew is None
    assert fb.fallback_reason in {"sigma_le_1e-12", "unique_resid_lt_20"}

    # Small sample (n < 120) -> gaussian fallback.
    small = rng.standard_normal(50)
    fb_small = fit_conditional_skew_t(small, seed=42)
    assert fb_small.distribution_family == "gaussian_fallback"
    assert fb_small.fallback_reason == "n_resid_lt_120"

    # Non-finite residual -> gaussian fallback.
    bad = np.concatenate([rng.standard_normal(150), [float("nan")]])
    fb_bad = fit_conditional_skew_t(bad, seed=42)
    assert fb_bad.distribution_family == "gaussian_fallback"
    assert fb_bad.fallback_reason == "non_finite_resid"
