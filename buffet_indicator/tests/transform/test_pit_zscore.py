"""v2.0 sprint Phase C.1 — PIT z-score tests.

Per sealed pre-reg §10.1 + PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md §4.
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

from src.transform.pit_zscore import pit_zscore  # noqa: E402


def _monthly(n: int, start: str = "2000-01-31") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="ME")


def test_pit_zscore_nan_before_min_window() -> None:
    """First ``min_window`` outputs must be NaN (insufficient prior history)."""
    idx = _monthly(200)
    s = pd.Series(np.arange(200, dtype="float64"), index=idx)
    z = pit_zscore(s, min_window=120)
    # With strict_shift=True, position k uses observations [0..k-1].
    # Bessel SD requires >=2 observations; expanding(min_periods=120) needs
    # 120 prior obs => z is NaN for positions where shifted has <120 valid obs.
    # Position 120: shifted[120] = s[119]; valid prior obs in shifted[:121] = 120.
    assert z.iloc[:120].isna().all(), "first 120 z-values must be NaN"
    assert not z.iloc[120:].isna().any(), "z must be non-NaN at and after 120"


def test_pit_zscore_strict_shift_excludes_current_observation() -> None:
    """At date t, z must not depend on observation t (strict PIT)."""
    idx = _monthly(150)
    rng = np.random.default_rng(seed=42)
    s = pd.Series(rng.normal(size=150), index=idx)
    z = pit_zscore(s, min_window=120)

    # Manually verify z at position 130: uses observations s[0..129] (shifted),
    # so z[130] = (s[129] - mean(s[0..129])) / std(s[0..129], ddof=1).
    prior = s.iloc[:130]
    mu = prior.mean()
    sd = prior.std(ddof=1)
    expected = (s.iloc[129] - mu) / sd
    assert pytest.approx(z.iloc[130], rel=1e-9) == expected


def test_pit_zscore_no_future_leakage_via_truncation_invariance() -> None:
    """pit_zscore(series.iloc[:k])[k-1] == pit_zscore(series)[k-1] for k > min_window."""
    idx = _monthly(200)
    rng = np.random.default_rng(seed=7)
    s = pd.Series(rng.normal(size=200), index=idx)
    full = pit_zscore(s, min_window=120)

    k = 150
    truncated_input = s.iloc[:k]
    truncated_out = pit_zscore(truncated_input, min_window=120)
    # Position k-1 in truncated must match position k-1 in full.
    assert pytest.approx(truncated_out.iloc[k - 1], rel=1e-9) == full.iloc[k - 1]


def test_pit_zscore_bessel_ddof_1() -> None:
    """SD uses Bessel correction (ddof=1), not population SD."""
    idx = _monthly(150)
    s = pd.Series(np.arange(150, dtype="float64"), index=idx)
    z = pit_zscore(s, min_window=120)
    # Manually replicate at position 125 with ddof=1.
    prior = s.iloc[:125]
    expected = (s.iloc[124] - prior.mean()) / prior.std(ddof=1)
    assert pytest.approx(z.iloc[125], rel=1e-9) == expected


def test_pit_zscore_index_preserved() -> None:
    """Output index matches input index exactly."""
    idx = _monthly(150)
    s = pd.Series(np.arange(150, dtype="float64"), index=idx)
    z = pit_zscore(s, min_window=120)
    pd.testing.assert_index_equal(z.index, s.index)


def test_pit_zscore_default_min_window_is_120() -> None:
    """Default min_window is the sealed §10.1 canonical 120."""
    idx = _monthly(200)
    s = pd.Series(np.arange(200, dtype="float64"), index=idx)
    z_default = pit_zscore(s)
    z_explicit = pit_zscore(s, min_window=120)
    pd.testing.assert_series_equal(z_default, z_explicit)


def test_pit_zscore_rejects_too_small_min_window() -> None:
    with pytest.raises(ValueError, match="min_window"):
        pit_zscore(pd.Series([1.0, 2.0]), min_window=1)


def test_pit_zscore_rejects_non_series_input() -> None:
    with pytest.raises(TypeError, match="series"):
        pit_zscore([1.0, 2.0, 3.0], min_window=2)


def test_pit_zscore_strict_shift_false_includes_current_observation() -> None:
    """strict_shift=False (diagnostic mode) uses series directly without shift."""
    idx = _monthly(150)
    s = pd.Series(np.arange(150, dtype="float64"), index=idx)
    z_strict = pit_zscore(s, min_window=120, strict_shift=True)
    z_loose = pit_zscore(s, min_window=120, strict_shift=False)
    # The loose mode includes current observation -> different values.
    assert not z_strict.equals(z_loose)
    # Loose-mode value at 125 uses observations s[0..125] inclusive.
    prior_incl = s.iloc[:126]
    expected = (s.iloc[125] - prior_incl.mean()) / prior_incl.std(ddof=1)
    assert pytest.approx(z_loose.iloc[125], rel=1e-9) == expected
