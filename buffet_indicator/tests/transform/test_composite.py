"""v2.0 sprint Phase C.2 — composite construction tests.

Per sealed pre-reg §1.1 + §1.2 + §10.1 + arbitration §5.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.transform.composite import (  # noqa: E402
    SCOPE_EFFECTIVE_START,
    SCOPE_WEIGHTS,
    build_composite,
)


def _monthly(start: str, n: int) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="ME")


def test_weights_abs_sum_close_to_one() -> None:
    """Each scope's weights satisfy Σ|w| ≈ 1.0 (sealed §10.1 invariant)."""
    for scope, w in SCOPE_WEIGHTS.items():
        abs_sum = sum(abs(v) for v in w.values())
        assert 0.99 <= abs_sum <= 1.01, f"{scope}: Σ|w|={abs_sum:.4f}"


def test_lc_full_weights_match_sealed() -> None:
    """LC_FULL weights match sealed §10.1 verbatim."""
    w = SCOPE_WEIGHTS["LC_FULL"]
    assert w == {"z1": 0.25, "z2": 0.20, "z3": 0.20, "z4": 0.20, "z5": -0.15}


def test_lc_tier2_drops_z1_and_keeps_z5_negative() -> None:
    """LC_TIER2 drops z1, keeps z5 with negative weight."""
    w = SCOPE_WEIGHTS["LC_TIER2"]
    assert "z1" not in w
    assert set(w) == {"z2", "z3", "z4", "z5"}
    assert w["z5"] < 0


def test_lc_deep_drops_z1_and_z5() -> None:
    """LC_DEEP drops both z1 and z5."""
    w = SCOPE_WEIGHTS["LC_DEEP"]
    assert "z1" not in w
    assert "z5" not in w
    assert set(w) == {"z2", "z3", "z4"}


def test_effective_start_dates() -> None:
    """Effective start dates match sealed §10.1."""
    assert SCOPE_EFFECTIVE_START["LC_FULL"] == pd.Timestamp("2003-01-31")
    assert SCOPE_EFFECTIVE_START["LC_TIER2"] == pd.Timestamp("1987-01-31")
    assert SCOPE_EFFECTIVE_START["LC_DEEP"] == pd.Timestamp("1973-01-31")


def test_lc_full_synthetic_hand_computed() -> None:
    """Hand-compute LC_FULL on a single date with known z-scores."""
    idx = _monthly("2010-01-31", 12)
    z1 = pd.Series(1.0, index=idx)
    z2 = pd.Series(2.0, index=idx)
    z3 = pd.Series(-1.0, index=idx)
    z4 = pd.Series(0.5, index=idx)
    z5 = pd.Series(3.0, index=idx)  # negative weight => -0.15 * 3.0
    out = build_composite(z1, z2, z3, z4, z5, scope="LC_FULL")
    # Per cell: 0.25*1 + 0.20*2 + 0.20*(-1) + 0.20*0.5 + (-0.15)*3
    # = 0.25 + 0.40 - 0.20 + 0.10 - 0.45 = 0.10
    assert out.iloc[0] == pytest.approx(0.10, rel=1e-9)
    assert out.name == "LC_FULL_composite"


def test_lc_tier2_synthetic_hand_computed() -> None:
    """Hand-compute LC_TIER2 on a single date."""
    idx = _monthly("2000-01-31", 5)
    z2 = pd.Series(1.0, index=idx)
    z3 = pd.Series(1.0, index=idx)
    z4 = pd.Series(1.0, index=idx)
    z5 = pd.Series(-1.0, index=idx)
    out = build_composite(None, z2, z3, z4, z5, scope="LC_TIER2")
    # 0.267 + 0.267 + 0.267 + (-0.200)*(-1) = 0.801 + 0.200 = 1.001
    expected = 0.267 + 0.267 + 0.267 + (-0.200) * (-1.0)
    assert out.iloc[0] == pytest.approx(expected, rel=1e-9)
    assert out.name == "LC_TIER2_composite"


def test_lc_deep_synthetic_hand_computed() -> None:
    """Hand-compute LC_DEEP (3 components)."""
    idx = _monthly("1980-01-31", 5)
    z2 = pd.Series(0.6, index=idx)
    z3 = pd.Series(-0.3, index=idx)
    z4 = pd.Series(1.2, index=idx)
    out = build_composite(None, z2, z3, z4, None, scope="LC_DEEP")
    expected = 0.333 * 0.6 + 0.333 * (-0.3) + 0.333 * 1.2
    assert out.iloc[0] == pytest.approx(expected, rel=1e-9)
    assert out.name == "LC_DEEP_composite"


def test_nan_propagation_required_component_missing() -> None:
    """If any required component is NaN at t -> composite NaN at t."""
    idx = _monthly("2010-01-31", 12)
    z1 = pd.Series(1.0, index=idx)
    z2 = pd.Series(1.0, index=idx)
    z2.iloc[5] = np.nan  # missing z2 at idx[5]
    z3 = pd.Series(1.0, index=idx)
    z4 = pd.Series(1.0, index=idx)
    z5 = pd.Series(1.0, index=idx)
    out = build_composite(z1, z2, z3, z4, z5, scope="LC_FULL")
    assert pd.isna(out.iloc[5])
    # Other dates non-NaN.
    assert not pd.isna(out.iloc[4])
    assert not pd.isna(out.iloc[6])


def test_effective_start_masks_pre_scope_dates() -> None:
    """LC_FULL composite is NaN before 2003-01-31 even if components non-NaN."""
    idx = _monthly("2000-01-31", 60)  # Jan 2000 -> Dec 2004
    z1 = pd.Series(1.0, index=idx)
    z2 = pd.Series(1.0, index=idx)
    z3 = pd.Series(1.0, index=idx)
    z4 = pd.Series(1.0, index=idx)
    z5 = pd.Series(1.0, index=idx)
    out = build_composite(z1, z2, z3, z4, z5, scope="LC_FULL")
    pre = out.loc[out.index < pd.Timestamp("2003-01-31")]
    post = out.loc[out.index >= pd.Timestamp("2003-01-31")]
    assert pre.isna().all()
    assert not post.isna().any()


def test_lc_tier2_missing_z5_raises() -> None:
    """LC_TIER2 requires z5 -> passing None for z5 raises ValueError."""
    idx = _monthly("1990-01-31", 5)
    z = pd.Series(1.0, index=idx)
    with pytest.raises(ValueError, match="z5"):
        build_composite(None, z, z, z, None, scope="LC_TIER2")


def test_lc_deep_does_not_require_z1_z5() -> None:
    """LC_DEEP only needs z2/z3/z4; passing None for z1/z5 is fine."""
    idx = _monthly("1975-01-31", 5)
    z = pd.Series(1.0, index=idx)
    out = build_composite(None, z, z, z, None, scope="LC_DEEP")
    assert not out.isna().any()


def test_unknown_scope_raises() -> None:
    idx = _monthly("2010-01-31", 5)
    z = pd.Series(1.0, index=idx)
    with pytest.raises(ValueError, match="unknown scope"):
        build_composite(z, z, z, z, z, scope="LC_BOGUS")  # type: ignore[arg-type]


def test_composite_index_aligns_with_inputs() -> None:
    """Output index matches the union of input indices (here equal indices)."""
    idx = _monthly("2010-01-31", 24)
    z = pd.Series(np.arange(24.0), index=idx)
    out = build_composite(z, z, z, z, z, scope="LC_FULL")
    pd.testing.assert_index_equal(out.index, idx)
