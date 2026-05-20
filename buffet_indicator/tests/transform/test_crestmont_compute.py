"""Spec v9.0 §1.4 + v9.1 §1.4 — Crestmont P/E unit tests."""
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

from src.transform.crestmont_compute import (  # noqa: E402
    _DEFAULT_MIN_WINDOW_YEARS,
    _DEFAULT_WINDOW_YEARS,
    _MIN_OBS_FOR_TREND_FIT,
    compute_crestmont_pe,
)


def _synth_shiller(n_months: int = 200, seed: int = 0) -> SimpleNamespace:
    """Build a minimal ShillerData-like object for tests."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1900-01-31", periods=n_months, freq="ME")
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


# ===========================================================================
# v9.0 tests — column shape, positivity, monotonicity, error handling
# (Updated for v9.1: NaN early rows must be filtered before positivity asserts)
# ===========================================================================


def test_crestmont_module_returns_dataframe_with_expected_columns() -> None:
    """v9.1: column set updated to include alpha_t, beta_t, n_in_window."""
    sh = _live_shiller()
    df = compute_crestmont_pe(sh)
    required = {
        "real_price",
        "real_eps",
        "trend_eps",
        "crestmont_pe",
        "log_crestmont_pe",
        "alpha_t",
        "beta_t",
        "n_in_window",
        "window_years",
    }
    assert required.issubset(set(df.columns))


def test_crestmont_trend_eps_positive_where_defined() -> None:
    """exp(α_t + β_t·n) > 0 always (where computed)."""
    sh = _live_shiller()
    df = compute_crestmont_pe(sh)
    valid = df["trend_eps"].dropna()
    assert len(valid) > 0
    assert (valid > 0).all()


def test_crestmont_pe_finite_and_positive_where_defined() -> None:
    sh = _live_shiller()
    df = compute_crestmont_pe(sh)
    valid = df["crestmont_pe"].dropna()
    assert np.isfinite(valid).all()
    assert (valid > 0).all()


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


def test_crestmont_alpha_beta_columns_present_and_varying() -> None:
    """v9.1: rolling fit produces time-varying coefficients."""
    sh = _live_shiller()
    df = compute_crestmont_pe(sh)
    valid = df.dropna(subset=["alpha_t", "beta_t"])
    assert len(valid) > 100
    # Both must vary across time — the whole point of v9.1.
    assert valid["alpha_t"].std() > 0.01
    assert valid["beta_t"].std() > 1e-5


def test_crestmont_synthetic_uses_local_window() -> None:
    """A synthetic series with a regime-change in trend should produce a
    crestmont_pe that responds to the change, not a constant-trend fit."""
    rng = np.random.default_rng(123)
    n = 1200  # 100 years
    idx = pd.date_range("1900-01-31", periods=n, freq="ME")
    # Two regimes: first half slope 0.003/mo, second half slope 0.001/mo.
    t = np.arange(n, dtype="float64")
    half = n // 2
    log_eps = np.empty(n)
    log_eps[:half] = 2.0 + 0.003 * t[:half] + rng.standard_normal(half) * 0.02
    # Continue from where first regime ended, with new slope
    end_first = log_eps[half - 1]
    log_eps[half:] = end_first + 0.001 * (t[half:] - t[half - 1]) + rng.standard_normal(n - half) * 0.02
    real_eps = np.exp(log_eps)
    real_price = real_eps * 15.0
    sh = SimpleNamespace(
        data=pd.DataFrame({"real_price": real_price, "real_earnings": real_eps}, index=idx)
    )
    df = compute_crestmont_pe(sh, window_years=50, min_window_years=30)
    # Late in the series (after enough second-regime obs), beta_t should be
    # closer to 0.001 than to 0.003.
    late_beta = df["beta_t"].iloc[-12:].mean()
    assert 0.0001 < late_beta < 0.0025, (
        f"Late beta_t = {late_beta:.4f}; should be closer to 0.001 (second regime)"
    )


def test_crestmont_constants_documented() -> None:
    """Easterling 2010 reference constants exposed at module level."""
    assert _DEFAULT_WINDOW_YEARS == 50
    assert _DEFAULT_MIN_WINDOW_YEARS == 30
    assert _MIN_OBS_FOR_TREND_FIT == 60


# ===========================================================================
# v9.1 new tests — rolling window + acceptance gate
# ===========================================================================


def test_crestmont_v91_uses_rolling_window() -> None:
    """alpha_t and beta_t should NOT be constant — they vary with t."""
    df = compute_crestmont_pe()
    df_valid = df.dropna(subset=["alpha_t"])
    assert df_valid["alpha_t"].std() > 0.01, (
        f"alpha_t std is {df_valid['alpha_t'].std():.6f}; should vary across time"
    )
    assert df_valid["beta_t"].std() > 1e-5, (
        f"beta_t std is {df_valid['beta_t'].std():.6e}; should vary across time"
    )


def test_crestmont_v91_nan_before_min_window() -> None:
    """First 30 years should be NaN under v9.1 rolling-window defaults."""
    df = compute_crestmont_pe()
    first_360 = df.iloc[:360]
    assert first_360["crestmont_pe"].isna().all(), (
        "First 30 years should be NaN under v9.1 rolling-window"
    )
    assert df["crestmont_pe"].iloc[360:].notna().all(), (
        "From month 360 onwards crestmont_pe should be populated"
    )


def test_crestmont_v91_no_lookahead() -> None:
    """Re-running with end-truncated data should match the corresponding
    rows of full-sample computation, exactly (causal estimator)."""
    df_full = compute_crestmont_pe()
    cutoff = df_full.index[1500]
    df_truncated = compute_crestmont_pe(end=cutoff)
    common = df_full.index.intersection(df_truncated.index)
    # Compare only where both are non-NaN
    pd.testing.assert_series_equal(
        df_full.loc[common, "crestmont_pe"],
        df_truncated.loc[common, "crestmont_pe"],
        check_names=False,
        atol=1e-9,
    )


def test_crestmont_v91_decorrelated_from_mean_reversion() -> None:
    """v9.1 ACCEPTANCE GATE: corr(log_crestmont_pe, mean_reversion_z) < 0.95.

    Reads ``outputs/charts/z_history.parquet`` for the latest mean-reversion
    long-run z-score series. The Crestmont series here is the rolling-window
    log-PE; we compare its standardized profile against MR's z-score profile.
    """
    crestmont = compute_crestmont_pe()["log_crestmont_pe"].dropna()
    z_path = Path("outputs/charts/z_history.parquet")
    if not z_path.exists():
        pytest.skip("z_history.parquet missing — run orchestrator first.")
    z_history = pd.read_parquet(z_path)
    # Project's actual schema uses columns {variant, frame, z_score}.
    mr_rows = z_history[
        (z_history["variant"] == "mean_reversion")
        & (z_history["frame"] == "long_run")
    ]
    if mr_rows.empty:
        pytest.skip("mean_reversion long_run z-score series not in z_history.")
    mr_series = mr_rows.set_index("date")["z_score"].astype("float64")
    # Align on common dates
    crestmont.index = pd.DatetimeIndex(crestmont.index).normalize()
    mr_series.index = pd.DatetimeIndex(mr_series.index).normalize()
    common = crestmont.index.intersection(mr_series.index)
    assert len(common) > 100, f"Only {len(common)} common dates"
    corr = crestmont.loc[common].corr(mr_series.loc[common])
    assert abs(corr) < 0.95, (
        f"v9.1 ACCEPTANCE GATE FAILED: corr(crestmont, mean_reversion) = "
        f"{corr:.4f}. Rolling-window Crestmont is still too redundant with MR. "
        f"Strategist arbitration required — do NOT ship v9.1 silently."
    )
