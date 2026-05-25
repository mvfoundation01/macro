"""§11.2 T04+T05+T11 — predictive regression v2.0.
DRAFT_v4 §3.3 + §3.5 (seal 2a94417).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.models.predictive_regression_v2 import (  # noqa: E402
    run_predictive_regression_v2,
)


def test_predictive_regression_uses_statsmodels_hac() -> None:
    """statsmodels NW with use_correction=True; HAC_kwds set correctly.

    References: DRAFT_v4 §3.5 + sealed pre-reg §11.2 T04.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")


def test_oos_rows_counted_after_realization() -> None:
    """OOS rows counted by the s + h <= t rule on a synthetic panel.

    References: DRAFT_v4 §3.4 (gate definition) + sealed pre-reg §11.2 T05.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")


def test_campbell_yogo_status_never_silent_nan() -> None:
    """rho=0.99 -> status enum always set ('computed_v1_grid' or
    'not_evaluable_outside_grid'); never silent NaN.

    References: DRAFT_v4 §3.5 + sealed pre-reg §11.2 T11.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
