"""§11.2 T08+T09 — stationary bootstrap. DRAFT_v4 §3.8 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import arch.bootstrap  # noqa: E402
import numpy as np  # noqa: E402

from src.stats.bootstrap import (  # noqa: E402
    BootstrapResult,
    choose_stationary_block_length,
    stationary_bootstrap_ci,
)


def test_optimal_block_length_uses_arch_stationary_column() -> None:
    """arch.bootstrap.optimal_block_length(np.arange(100.0))['stationary'].iloc[0]
    matches; columns include both 'stationary' and 'circular'; CORRECT column
    selection is 'stationary' (NOT 'circular').

    CORRECTED per Codex round-3 New-1 against installed arch==7.0.0.
    References: DRAFT_v4 §3.8 + sealed pre-reg §11.2 T08.
    """
    x = np.arange(100.0)
    obl = arch.bootstrap.optimal_block_length(x)
    # Real library returns DataFrame with both columns.
    assert "stationary" in obl.columns
    assert "circular" in obl.columns
    expected = int(np.ceil(float(obl["stationary"].iloc[0])))
    # Clamp upper bound to n // 2 per §3.8 implementation.
    expected = min(max(1, expected), max(1, len(x) // 2))
    actual = choose_stationary_block_length(x)
    assert actual == expected
    # Sanity: 'stationary' and 'circular' columns differ in general -> we
    # must select 'stationary'.
    circ = int(np.ceil(float(obl["circular"].iloc[0])))
    circ_clamped = min(max(1, circ), max(1, len(x) // 2))
    if circ_clamped != expected:
        assert actual != circ_clamped


def test_stationary_bootstrap_is_byte_identical() -> None:
    """Two runs with same seed produce byte-identical bootstrap output.

    Uses np.random.SeedSequence determinism. Runs with a small n_bootstrap
    for speed; determinism property is independent of count.
    References: DRAFT_v4 §3.8 + sealed pre-reg §11.2 T09.
    """
    rng = np.random.default_rng(123)
    data = rng.standard_normal(200)

    a = stationary_bootstrap_ci(data, n_bootstrap=200, seed=42)
    b = stationary_bootstrap_ci(data, n_bootstrap=200, seed=42)
    assert isinstance(a, BootstrapResult)
    assert isinstance(b, BootstrapResult)
    # Byte-identical: equal dataclass instances + identical seed-derived hex.
    assert a == b
    assert a.seed_hex == b.seed_hex
    # CI structure is well-formed.
    assert np.isfinite(a.ci_lower)
    assert np.isfinite(a.ci_upper)
    assert a.ci_lower <= a.ci_upper
    assert a.n_bootstrap_used == 200
    assert a.block_length >= 1
    assert a.block_length_source == "stationary_optimal"
    assert a.confidence_level == 0.95
    assert a.not_evaluable_reason is None

    # Different seed -> different bootstrap samples (the CIs may differ).
    c = stationary_bootstrap_ci(data, n_bootstrap=200, seed=43)
    assert c.seed_hex != a.seed_hex


def test_stationary_bootstrap_n_lt_30_returns_not_evaluable() -> None:
    """n < 30 -> not_evaluable_reason='n_lt_30'; CI bounds NaN; point still computed."""
    rng = np.random.default_rng(1)
    data = rng.standard_normal(25)
    result = stationary_bootstrap_ci(data, n_bootstrap=200, seed=42)
    assert result.not_evaluable_reason == "n_lt_30"
    assert np.isnan(result.ci_lower)
    assert np.isnan(result.ci_upper)


def test_stationary_bootstrap_block_gt_n_over_2_returns_not_evaluable() -> None:
    """block_length > n // 2 -> not_evaluable_reason='block_gt_n_over_2'."""
    rng = np.random.default_rng(1)
    data = rng.standard_normal(40)
    result = stationary_bootstrap_ci(
        data,
        n_bootstrap=200,
        seed=42,
        block_length=25,  # > 40 // 2 = 20
    )
    assert result.not_evaluable_reason == "block_gt_n_over_2"
    assert np.isnan(result.ci_lower)
    assert np.isnan(result.ci_upper)
