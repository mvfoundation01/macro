"""Spec v9.0 §1.4 — Crestmont P/E unit tests."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.transform.crestmont_compute import (
    _MIN_OBS_FOR_TREND_FIT,
    compute_crestmont_pe,
)


def _synth_shiller(n_months: int = 200, seed: int = 0) -> SimpleNamespace:
    """Build a minimal ShillerData-like object for tests.

    Mimics the duck-typed ``shiller_data.data`` DataFrame interface.
    """
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1900-01-31", periods=n_months, freq="ME")
    # exponential trend in real_eps with noise
    t = np.arange(n_months)
    real_eps = 10.0 * np.exp(0.002 * t) * np.exp(rng.standard_normal(n_months) * 0.05)
    real_price = real_eps * (15.0 + rng.standard_normal(n_months) * 2.0)
    data = pd.DataFrame(
        {"real_price": real_price, "real_earnings": real_eps},
        index=idx,
    )
    return SimpleNamespace(data=data)


def _live_shiller():
    from src.ingest.shiller_loader import load_shiller
    return load_shiller()


def test_crestmont_module_returns_dataframe_with_expected_columns() -> None:
    """Live ShillerData → DataFrame with all 8 required columns."""
    sh = _live_shiller()
    df = compute_crestmont_pe(sh)
    required = {
        "real_price",
        "real_eps",
        "trend_eps",
        "crestmont_pe",
        "log_crestmont_pe",
        "alpha",
        "beta",
        "n_fit",
    }
    assert required.issubset(set(df.columns))


def test_crestmont_trend_eps_positive_everywhere() -> None:
    """exp(α + β·t) is always positive — guards against numerical underflow."""
    sh = _live_shiller()
    df = compute_crestmont_pe(sh)
    assert (df["trend_eps"] > 0).all()


def test_crestmont_pe_finite_and_positive() -> None:
    sh = _live_shiller()
    df = compute_crestmont_pe(sh)
    assert np.isfinite(df["crestmont_pe"]).all()
    assert (df["crestmont_pe"] > 0).all()


def test_crestmont_index_is_monthly_unique_sorted() -> None:
    sh = _live_shiller()
    df = compute_crestmont_pe(sh)
    assert df.index.is_unique
    assert df.index.is_monotonic_increasing


def test_crestmont_raises_on_too_short_history() -> None:
    """Synthetic 30-row input should raise ValueError."""
    sh = _synth_shiller(n_months=30)
    with pytest.raises(ValueError, match=r"≥ 60 monthly|≥ \d+ monthly"):
        compute_crestmont_pe(sh)


def test_crestmont_trend_alpha_beta_consistent_first_row() -> None:
    """Re-applying the trend formula at t=0 yields exp(α) within float precision."""
    sh = _live_shiller()
    df = compute_crestmont_pe(sh)
    alpha = float(df["alpha"].iloc[0])
    expected_first = float(np.exp(alpha))  # t=0 → exp(α + β·0) = exp(α)
    assert abs(df["trend_eps"].iloc[0] - expected_first) < 1e-6


def test_crestmont_synthetic_recovers_known_trend() -> None:
    """A synthetic series with known α, β should recover those parameters."""
    # Generate exp trend with α=2.0, β=0.002 plus tight noise
    rng = np.random.default_rng(123)
    n = 240
    idx = pd.date_range("1900-01-31", periods=n, freq="ME")
    t = np.arange(n)
    real_eps = np.exp(2.0 + 0.002 * t + rng.standard_normal(n) * 0.01)
    real_price = real_eps * 15.0
    sh = SimpleNamespace(
        data=pd.DataFrame({"real_price": real_price, "real_earnings": real_eps}, index=idx)
    )
    df = compute_crestmont_pe(sh)
    # Fit should be close to ground truth
    assert abs(float(df["alpha"].iloc[0]) - 2.0) < 0.02
    assert abs(float(df["beta"].iloc[0]) - 0.002) < 1e-4


def test_crestmont_constant_is_documented() -> None:
    """The trend-fit minimum is the documented Easterling threshold."""
    assert _MIN_OBS_FOR_TREND_FIT == 60
