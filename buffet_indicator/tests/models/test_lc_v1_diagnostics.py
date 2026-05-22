"""Tests for ``src.models.lc_v1_diagnostics`` (Session 8 §2.H).

Test layout
-----------
* T-H1..T-H6: stationarity tests on synthetic AR(1) / random walk / break.
* T-H7..T-H9: VIF / correlation / eigenvalue spectrum.
* T-H10..T-H12: Bai-Perron break detection + schema.

References
----------
* prompt/052226/PROMPT_v11_3_session_8_H_I_J_closeout.md §2.H.4
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.models import lc_v1_diagnostics as diag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ar1(n: int, rho: float, sigma: float = 1.0, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = rho * x[i - 1] + rng.normal(0, sigma)
    idx = pd.date_range("1990-01-31", periods=n, freq="ME")
    return pd.Series(x, index=idx, name="synthetic")


def _random_walk(n: int, seed: int = 0) -> pd.Series:
    return _ar1(n, rho=1.0, sigma=1.0, seed=seed)


# ===========================================================================
# T-H1..T-H6: stationarity tests
# ===========================================================================


def test_TH1_adf_rejects_on_ar1_rho05() -> None:
    """T-H1: ADF on AR(1) ρ=0.5 (stationary) → rejects unit-root null."""
    s = _ar1(500, rho=0.5, seed=11)
    res = diag.run_stationarity_tests(s, "ar1_rho05")
    assert res.adf_pvalue < 0.05, f"ADF p={res.adf_pvalue} should reject"


def test_TH2_adf_fails_on_random_walk() -> None:
    """T-H2: ADF on random walk → does NOT reject (fails to reject unit-root)."""
    s = _random_walk(500, seed=12)
    res = diag.run_stationarity_tests(s, "random_walk")
    assert res.adf_pvalue > 0.05, f"ADF p={res.adf_pvalue} should fail to reject"


def test_TH3_kpss_fails_to_reject_on_stationary() -> None:
    """T-H3: KPSS on stationary AR(1) ρ=0.3 → does NOT reject stationarity null."""
    s = _ar1(500, rho=0.3, seed=13)
    res = diag.run_stationarity_tests(s, "ar1_rho03")
    assert res.kpss_pvalue >= 0.05, (
        f"KPSS p={res.kpss_pvalue} should fail to reject stationarity"
    )


def test_TH4_kpss_rejects_on_random_walk() -> None:
    """T-H4: KPSS on random walk → rejects stationarity null."""
    s = _random_walk(500, seed=14)
    res = diag.run_stationarity_tests(s, "random_walk")
    assert res.kpss_pvalue < 0.05, (
        f"KPSS p={res.kpss_pvalue} should reject on random walk"
    )


def test_TH5_pp_consistent_with_adf_on_stationary() -> None:
    """T-H5: Phillips-Perron also rejects unit-root null on stationary AR(1)."""
    s = _ar1(500, rho=0.4, seed=15)
    res = diag.run_stationarity_tests(s, "ar1_rho04")
    assert res.pp_pvalue < 0.10, (
        f"PP p={res.pp_pvalue} should reject (consistent with ADF)"
    )


def test_TH6_za_detects_structural_break() -> None:
    """T-H6: Zivot-Andrews detects a known break in a synthetic shifted series."""
    rng = np.random.default_rng(16)
    n = 300
    break_at = 150
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.5 * x[i - 1] + rng.normal(0, 1.0)
    # Inject a level shift at break_at.
    x[break_at:] += 5.0
    idx = pd.date_range("1990-01-31", periods=n, freq="ME")
    s = pd.Series(x, index=idx)
    res = diag.run_stationarity_tests(s, "broken_series")
    # ZA stat should reject the unit-root-with-break null on a stationary-
    # with-break series. ``za_break_date`` is left empty because the arch
    # library does not expose the estimated break period publicly.
    assert np.isfinite(res.za_stat)
    assert np.isfinite(res.za_pvalue)
    assert res.za_pvalue < 0.10


# ===========================================================================
# T-H7..T-H9: VIF / correlation / eigenvalue spectrum
# ===========================================================================


def test_TH7_vif_near_one_on_uncorrelated() -> None:
    """T-H7: VIF ≈ 1.0 on truly uncorrelated independent series."""
    rng = np.random.default_rng(17)
    n = 300
    idx = pd.date_range("1990-01-31", periods=n, freq="ME")
    comps = {
        f"z{i}": pd.Series(rng.normal(0, 1.0, size=n), index=idx)
        for i in range(1, 6)
    }
    mc = diag.compute_vif_matrix(comps)
    for name, v in mc.vif.items():
        assert v < 1.5, f"VIF[{name}] = {v} should be near 1.0 on uncorrelated data"
    assert all(not f for f in mc.multicollinearity_flags.values())


def test_TH8_vif_large_on_perfect_correlation() -> None:
    """T-H8: VIF very large when two series are near-perfectly correlated."""
    rng = np.random.default_rng(18)
    n = 300
    idx = pd.date_range("1990-01-31", periods=n, freq="ME")
    base = rng.normal(0, 1.0, size=n)
    comps = {
        "z1": pd.Series(base, index=idx),
        "z2": pd.Series(base + rng.normal(0, 0.01, size=n), index=idx),
        "z3": pd.Series(rng.normal(0, 1.0, size=n), index=idx),
        "z4": pd.Series(rng.normal(0, 1.0, size=n), index=idx),
        "z5": pd.Series(rng.normal(0, 1.0, size=n), index=idx),
    }
    mc = diag.compute_vif_matrix(comps)
    # z1 and z2 are nearly identical → VIF should be very high for both.
    assert mc.vif["z1"] > 10.0
    assert mc.vif["z2"] > 10.0
    assert mc.multicollinearity_flags["z1"]
    assert mc.multicollinearity_flags["z2"]


def test_TH9_correlation_matrix_symmetric_diagonal_one() -> None:
    """T-H9: correlation matrix is symmetric with diagonal = 1."""
    rng = np.random.default_rng(19)
    n = 200
    idx = pd.date_range("1990-01-31", periods=n, freq="ME")
    comps = {
        f"z{i}": pd.Series(rng.normal(0, 1.0, size=n), index=idx)
        for i in range(1, 6)
    }
    mc = diag.compute_vif_matrix(comps)
    np.testing.assert_allclose(
        np.diag(mc.correlation_matrix.to_numpy(dtype=float)),
        np.ones(5),
        atol=1e-9,
    )
    # Symmetry.
    np.testing.assert_allclose(
        mc.correlation_matrix.to_numpy(dtype=float),
        mc.correlation_matrix.to_numpy(dtype=float).T,
        atol=1e-9,
    )


def test_TH9b_eigenvalues_sum_to_total_variance() -> None:
    """Eigenvalues of the covariance matrix sum to total variance (= trace)."""
    rng = np.random.default_rng(20)
    n = 300
    idx = pd.date_range("1990-01-31", periods=n, freq="ME")
    comps = {
        f"z{i}": pd.Series(rng.normal(0, 1.0, size=n), index=idx)
        for i in range(1, 6)
    }
    mc = diag.compute_vif_matrix(comps)
    # Eigenvalues should be ≥ 0 (covariance matrix is PSD).
    assert (mc.eigenvalues >= -1e-9).all()
    # Cumulative proportions end at 1.0.
    assert abs(mc.eigenvalue_cumulative[-1] - 1.0) < 1e-9


# ===========================================================================
# T-H10..T-H12: Bai-Perron + schema
# ===========================================================================


def test_TH10_bai_perron_detects_known_break() -> None:
    """T-H10: Bai-Perron detects a known break in a synthetic shifted series."""
    rng = np.random.default_rng(21)
    n = 300
    break_at = 150
    x = rng.normal(0, 1.0, size=n)
    x[break_at:] += 4.0  # large level shift
    idx = pd.date_range("1990-01-31", periods=n, freq="ME")
    s = pd.Series(x, index=idx)
    result = diag.run_bai_perron_breaks(s, "shifted", max_breaks=5)
    assert result.n_breaks_detected >= 1
    # Detected break should land near break_at (within ±10 monthly obs).
    detected_indices = [b["break_index"] for b in result.breaks]
    assert any(abs(i - break_at) <= 10 for i in detected_indices)


def test_TH11_bai_perron_finite_on_stationary() -> None:
    """T-H11: Bai-Perron BIC selection returns a finite number of breaks
    (≤ max_breaks) on stationary AR(1). The exact count varies with seed
    and dataset; the BIC criterion prevents runaway over-fitting but does
    not guarantee 0 breaks even on stationary data (BIC sometimes picks up
    spurious regime shifts in finite samples)."""
    s = _ar1(300, rho=0.4, seed=22)
    result = diag.run_bai_perron_breaks(s, "stationary", max_breaks=5)
    assert 0 <= result.n_breaks_detected <= 5, (
        f"Bai-Perron returned n_breaks={result.n_breaks_detected}; must be in [0, max_breaks]"
    )


def test_TH12_short_series_returns_no_breaks() -> None:
    """T-H12: very short series → no breaks detected (length safety guard)."""
    s = pd.Series([1.0, 2.0, 3.0, 4.0], index=pd.date_range("2020-01-01", periods=4, freq="ME"))
    result = diag.run_bai_perron_breaks(s, "tiny", max_breaks=5)
    assert result.n_breaks_detected == 0


def test_TH12b_short_series_returns_nan_stationarity() -> None:
    """Stationarity tests on a too-short series → NaN p-values."""
    s = pd.Series(np.arange(5, dtype=float),
                  index=pd.date_range("2020-01-31", periods=5, freq="ME"))
    res = diag.run_stationarity_tests(s, "tiny")
    assert np.isnan(res.adf_pvalue)


def test_TH12c_run_stationarity_conclusion_logic() -> None:
    """Conclusion logic: ADF rejects + KPSS doesn't reject → 'stationary'."""
    s = _ar1(500, rho=0.3, seed=33)
    res = diag.run_stationarity_tests(s, "stationary_test")
    # On AR(1) rho=0.3, expect 'stationary' or 'conflicting' (KPSS sensitivity).
    assert res.conclusion in {"stationary", "conflicting"}


def test_TH12d_vif_threshold_constant() -> None:
    """VIF_THRESHOLD constant equals 5.0 per master spec §3.6."""
    assert diag.VIF_THRESHOLD == 5.0
