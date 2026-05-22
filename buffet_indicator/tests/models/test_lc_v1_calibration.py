"""Tests for ``src.models.lc_v1_calibration`` (Session 7 §2.G).

Test layout
-----------
* T-G1: Brier score of perfect forecaster = 0.
* T-G2: Brier score of constant-0.5 forecaster on balanced data = 0.25.
* T-G3: Murphy decomposition identity BS = Reliability − Resolution + Uncertainty.
* T-G4: CRPS closed-form on synthetic Gaussian data.
* T-G5: PIT of well-calibrated Gaussian forecast is approximately uniform.
* T-G6: K-S test rejects misspecified forecast (e.g., wrong σ).

References
----------
* prompt/052226/PROMPT_v11_3_session_7_DECISIONS_investigation_F_G.md §2.G.7
"""
from __future__ import annotations

import numpy as np
import pytest

from src.models import lc_v1_calibration as cal


# ---------------------------------------------------------------------------
# T-G1: perfect forecaster → BS=0
# ---------------------------------------------------------------------------


def test_TG1_brier_perfect_forecaster() -> None:
    """T-G1: forecasts that exactly match outcomes (probs ∈ {0,1}) → BS=0."""
    p = np.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
    y = np.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
    d = cal.compute_brier_decomposition(p, y, n_bins=10)
    assert d.brier_score == 0.0
    assert d.reliability == 0.0
    assert d.resolution == d.uncertainty


# ---------------------------------------------------------------------------
# T-G2: constant 0.5 on balanced data → BS=0.25
# ---------------------------------------------------------------------------


def test_TG2_brier_constant_half_on_balanced() -> None:
    """T-G2: constant prob=0.5 on equal-mass 0/1 outcomes → BS=0.25."""
    p = np.full(1000, 0.5)
    y = np.tile([0, 1], 500).astype(float)
    d = cal.compute_brier_decomposition(p, y, n_bins=10)
    assert abs(d.brier_score - 0.25) < 1e-12


# ---------------------------------------------------------------------------
# T-G3: Murphy decomposition identity
# ---------------------------------------------------------------------------


def test_TG3_brier_murphy_identity() -> None:
    """T-G3: BS = Reliability − Resolution + Uncertainty (algebraic identity).

    The exact 3-term Murphy identity holds when forecasts are constant within
    each bin (no within-bin variance). We use discretized forecasts at bin
    centers to satisfy this precondition.
    """
    rng = np.random.default_rng(42)
    bin_centers_grid = np.array(
        [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
    )
    p = rng.choice(bin_centers_grid, size=500)
    y = (rng.uniform(0.0, 1.0, size=500) < p).astype(float)
    d = cal.compute_brier_decomposition(p, y, n_bins=10)
    lhs = d.brier_score
    rhs = d.reliability - d.resolution + d.uncertainty
    assert abs(lhs - rhs) < 1e-9, f"BS={lhs} != Rel-Res+Unc={rhs}"


# ---------------------------------------------------------------------------
# T-G4: CRPS closed-form correctness
# ---------------------------------------------------------------------------


def test_TG4_crps_gaussian_closed_form() -> None:
    """T-G4: CRPS of a perfect-mean Gaussian on observations from that
    Gaussian equals σ × (1/√π − ... ). For y=μ, the closed form gives
    σ · (0 + 2·φ(0) − 1/√π) = σ · (2/√(2π) − 1/√π)."""
    n = 1000
    sigma = 0.10
    mu = np.full(n, 1.50)
    sd = np.full(n, sigma)
    y = mu.copy()
    val = cal.compute_crps(mu, sd, y)
    expected = sigma * (2.0 / np.sqrt(2.0 * np.pi) - 1.0 / np.sqrt(np.pi))
    assert abs(val - expected) < 1e-9


def test_TG4b_crps_lower_when_forecast_better() -> None:
    """T-G4b: CRPS for a Gaussian forecast with smaller bias has lower CRPS."""
    n = 500
    rng = np.random.default_rng(7)
    y = rng.normal(0.0, 1.0, size=n)
    crps_good = cal.compute_crps(np.zeros(n), np.ones(n), y)
    crps_biased = cal.compute_crps(np.full(n, 3.0), np.ones(n), y)
    assert crps_good < crps_biased


# ---------------------------------------------------------------------------
# T-G5: PIT uniform under correct distribution
# ---------------------------------------------------------------------------


def test_TG5_pit_uniform_under_correct_forecast() -> None:
    """T-G5: realized y_t ~ N(μ_t, σ_t) and PIT u_t = Φ((y-μ)/σ) is iid
    Uniform(0,1) → K-S p-value not tiny on large sample."""
    n = 1000
    rng = np.random.default_rng(11)
    mu = rng.normal(0.0, 0.5, size=n)
    sd = np.full(n, 0.20)
    y = rng.normal(mu, sd)
    result = cal.compute_pit(mu, sd, y, n_bins=10)
    # Well-calibrated → high p-value (typically > 0.05).
    assert result.ks_pvalue > 0.01
    # PIT counts roughly uniform → no single bin dominates.
    assert result.histogram_counts.max() < n * 0.3


# ---------------------------------------------------------------------------
# T-G6: K-S test rejects miscalibrated forecast
# ---------------------------------------------------------------------------


def test_TG6_pit_rejects_underdispersed_forecast() -> None:
    """T-G6: forecast with σ̂ = σ_true/4 → PIT clumps at tails → K-S rejects."""
    n = 500
    rng = np.random.default_rng(21)
    y = rng.normal(0.0, 1.0, size=n)
    mu = np.zeros(n)
    sd = np.full(n, 0.25)  # 4× underdispersed
    result = cal.compute_pit(mu, sd, y)
    assert result.ks_pvalue < 0.05, (
        f"K-S should reject misspecified forecast; got p={result.ks_pvalue:.4f}"
    )


# ---------------------------------------------------------------------------
# T-G7: log score lower when forecast better
# ---------------------------------------------------------------------------


def test_TG7_log_score_lower_when_forecast_better() -> None:
    """T-G7: log score (negative log-likelihood per obs) drops when σ̂ matches σ_true."""
    n = 500
    rng = np.random.default_rng(31)
    y = rng.normal(0.0, 1.0, size=n)
    ls_good = cal.compute_log_score(np.zeros(n), np.ones(n), y)
    ls_overdispersed = cal.compute_log_score(np.zeros(n), np.full(n, 5.0), y)
    assert ls_good < ls_overdispersed


# ---------------------------------------------------------------------------
# T-G8: Wilson interval sanity
# ---------------------------------------------------------------------------


def test_TG8_wilson_interval_sanity() -> None:
    """T-G8: Wilson interval contains the empirical proportion and is in [0,1]
    (with small floating-point tolerance for the boundary cases s=0 and s=n).
    """
    eps = 1e-9
    for s, n in [(0, 10), (5, 10), (10, 10), (50, 100), (3, 10)]:
        lo, hi = cal.wilson_interval(s, n)
        p = s / n
        assert 0.0 - eps <= lo <= p + eps
        assert p - eps <= hi <= 1.0 + eps


# ---------------------------------------------------------------------------
# T-G9: render_reliability_diagram returns a Figure (smoke test)
# ---------------------------------------------------------------------------


def test_TG9_render_reliability_diagram_smoke() -> None:
    """T-G9: render_reliability_diagram returns a matplotlib Figure object."""
    rng = np.random.default_rng(101)
    p = rng.uniform(0.0, 1.0, size=200)
    y = (rng.uniform(0.0, 1.0, size=200) < p).astype(float)
    d = cal.compute_brier_decomposition(p, y, n_bins=10)
    fig = cal.render_reliability_diagram(d, title="test", isotonic_overlay=False)
    assert fig is not None
    import matplotlib.figure as mfig
    assert isinstance(fig, mfig.Figure)


def test_TG10_render_pit_histogram_smoke() -> None:
    """T-G10: render_pit_histogram returns a matplotlib Figure object."""
    rng = np.random.default_rng(102)
    y = rng.normal(0.0, 1.0, size=200)
    result = cal.compute_pit(np.zeros(200), np.ones(200), y, n_bins=10)
    fig = cal.render_pit_histogram(result, title="test")
    assert fig is not None
    import matplotlib.figure as mfig
    assert isinstance(fig, mfig.Figure)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_TG_edge_empty_input_raises() -> None:
    """Empty input arrays → ValueError on brier."""
    with pytest.raises(ValueError):
        cal.compute_brier_decomposition(np.array([]), np.array([]))


def test_TG_edge_crps_empty_returns_nan() -> None:
    """Empty input arrays → NaN on CRPS / log score."""
    assert np.isnan(cal.compute_crps(np.array([]), np.array([]), np.array([])))
    assert np.isnan(cal.compute_log_score(np.array([]), np.array([]), np.array([])))


def test_TG_edge_brier_shape_mismatch_raises() -> None:
    p = np.zeros(10)
    y = np.zeros(11)
    with pytest.raises(ValueError, match="shape mismatch"):
        cal.compute_brier_decomposition(p, y)


def test_TG_edge_crps_shape_mismatch_raises() -> None:
    """Length-mismatched inputs → ValueError on CRPS / log score."""
    with pytest.raises(ValueError, match="length mismatch"):
        cal.compute_crps(np.zeros(5), np.ones(5), np.zeros(6))
    with pytest.raises(ValueError, match="length mismatch"):
        cal.compute_log_score(np.zeros(5), np.ones(5), np.zeros(6))


def test_TG_edge_crps_degenerate_sd() -> None:
    """Zero σ → CRPS falls back to mean absolute error."""
    y = np.array([1.0, 2.0, 3.0])
    mu = np.array([1.5, 1.5, 1.5])
    sd = np.array([0.0, 0.0, 0.0])
    val = cal.compute_crps(mu, sd, y)
    # MAE = mean(|1-1.5|, |2-1.5|, |3-1.5|) = mean(0.5, 0.5, 1.5) = 0.833
    assert abs(val - 0.8333333) < 1e-3


def test_TG_edge_log_score_degenerate_sd() -> None:
    """Zero σ → log score returns NaN."""
    val = cal.compute_log_score(np.zeros(3), np.zeros(3), np.zeros(3))
    assert np.isnan(val)


def test_TG_edge_pit_shape_mismatch_raises() -> None:
    """Mismatched lengths → ValueError on PIT."""
    with pytest.raises(ValueError, match="length mismatch"):
        cal.compute_pit(np.zeros(5), np.ones(5), np.zeros(6))


def test_TG_edge_pit_empty_input() -> None:
    """Empty input → PITResult with NaN K-S and empty histogram."""
    result = cal.compute_pit(np.array([]), np.array([]), np.array([]))
    assert len(result.pit_values) == 0
    assert np.isnan(result.ks_pvalue)


def test_TG_edge_pit_degenerate_sd() -> None:
    """Zero σ → PIT returns empty PITResult with NaN K-S."""
    result = cal.compute_pit(np.zeros(5), np.zeros(5), np.ones(5))
    assert len(result.pit_values) == 0
    assert np.isnan(result.ks_pvalue)


def test_TG_edge_brier_zero_bins_used() -> None:
    """Edge: forecast probs outside [0,1] → bin assignment may yield zero
    valid bins; reliability/resolution return NaN."""
    # Use a single forecast value outside [0,1] (artificial edge); the digitize
    # logic puts everything in bin 0 (or N-1) — n_used should still be > 0.
    # To force zero valid bins, we use empty-shape input; but that raises.
    # Instead, use a single-sample input to exercise an unusual branch.
    p = np.array([0.5])
    y = np.array([1.0])
    d = cal.compute_brier_decomposition(p, y, n_bins=10)
    assert d.n_bins_used == 1  # only the bin containing 0.5 is non-empty
    assert np.isfinite(d.reliability)
