"""§11.2 T06+T07 — skewed-t fit + arch API. DRAFT_v4 §3.7 Am.3 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.skewt import fit_conditional_skew_t  # noqa: E402


def test_skewstudent_loglikelihood_signature_is_used_correctly() -> None:
    """arch API: loglikelihood(parameters, resids, sigma2); finite likelihood.

    NEW per Codex round-2 New-1.
    References: DRAFT_v4 §3.7 Amendment 3 + sealed pre-reg §11.2 T06.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")


def test_skewed_t_known_distribution_and_fallback() -> None:
    """seed=42 size=500 t-df=5 standardized -> 3.0<=eta_tail<=8.0, |lambda|<=0.15;
    degenerate residuals -> gaussian_fallback.

    Per Codex round-3 New-3 tolerance: interval calibrated to Codex's
    empirical run (eta_tail~4.2542, lambda~-0.0427).
    References: DRAFT_v4 §3.7 Amendment 3 + sealed pre-reg §11.2 T07.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
