"""§11.2 T02+T03 — sample gate boundaries. DRAFT_v4 §3.4 + §3.9 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.stats.sample_gate import sample_gate_status  # noqa: E402


def test_sample_gate_boundary_basic() -> None:
    """n_obs_oos=60 hac_lag=11 -> evaluable; 59 -> not_evaluable (strict <).

    References: DRAFT_v4 §3.4 + sealed pre-reg §11.2 T02.
    """
    # 1Y boundary: hac_lag=11 -> required n_obs_oos = max(60, 33) = 60.
    assert sample_gate_status(60, 11, n_eff=50.0) == "evaluable"
    assert sample_gate_status(59, 11, n_eff=50.0) == "not_evaluable"
    # Generous n_eff but n_obs_oos one short -> not evaluable.
    assert sample_gate_status(59, 11, n_eff=1000.0) == "not_evaluable"


def test_sample_gate_boundaries_include_hac_and_neff() -> None:
    """n_obs_oos=105 hac=35 neff=30.0 -> evaluable; 104 -> not; neff=29.999 -> not.

    NEW per Codex round-2 New-8.
    References: DRAFT_v4 §3.4 + sealed pre-reg §11.2 T03.
    """
    # 3Y horizon: hac_lag=35 -> required n_obs_oos = max(60, 105) = 105.
    assert sample_gate_status(105, 35, n_eff=30.0) == "evaluable"
    assert sample_gate_status(104, 35, n_eff=30.0) == "not_evaluable"
    # n_eff strict < 30 -> not evaluable.
    assert sample_gate_status(105, 35, n_eff=29.999) == "not_evaluable"
    # 30.0 exactly -> evaluable (§3.9 comparator table).
    assert sample_gate_status(105, 35, n_eff=30.0) == "evaluable"


def test_sample_gate_handles_long_horizon_min_obs() -> None:
    """5Y horizon (hac_lag=59) requires n_obs_oos >= 177; 10Y requires 357."""
    # 5Y: hac=59 -> 3 * 59 = 177.
    assert sample_gate_status(177, 59, n_eff=100.0) == "evaluable"
    assert sample_gate_status(176, 59, n_eff=100.0) == "not_evaluable"
    # 10Y: hac=119 -> 3 * 119 = 357.
    assert sample_gate_status(357, 119, n_eff=100.0) == "evaluable"
    assert sample_gate_status(356, 119, n_eff=100.0) == "not_evaluable"


def test_sample_gate_non_finite_n_eff_is_not_evaluable() -> None:
    """Non-finite n_eff returns not_evaluable (defensive)."""
    assert sample_gate_status(200, 11, n_eff=float("nan")) == "not_evaluable"
    assert sample_gate_status(200, 11, n_eff=float("inf")) == "not_evaluable"
    assert sample_gate_status(200, 11, n_eff=float("-inf")) == "not_evaluable"
