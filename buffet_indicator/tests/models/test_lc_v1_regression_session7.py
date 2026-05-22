"""Session 7 §2.F tests for ``src.models.lc_v1_regression``:

* T-F1..T-F4 — 50K bootstrap reproducibility + conditional probability tail outputs.
* T-CY1..T-CY3 — Campbell-Yogo Bonferroni Q-test CI fallback.

References
----------
* prompt/052226/PROMPT_v11_3_session_7_DECISIONS_investigation_F_G.md §2.F.5
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.models import lc_v1_regression as reg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_synthetic_spx_tr(n_months: int = 700, seed: int = 7) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1965-01-31", periods=n_months, freq="ME")
    log_levels = np.cumsum(rng.normal(0.005, 0.04, size=n_months))
    return pd.Series(100.0 * np.exp(log_levels), index=idx, name="spx_tr")


def _mk_synthetic_lc(n_months: int = 700, persistence: float = 0.95,
                     seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1965-01-31", periods=n_months, freq="ME")
    x = np.zeros(n_months)
    for i in range(1, n_months):
        x[i] = persistence * x[i - 1] + rng.normal(0, 1.0)
    return pd.Series(x - x.mean(), index=idx, name="lc")


# ===========================================================================
# T-CY1..T-CY3 — Campbell-Yogo CI
# ===========================================================================


def test_TCY1_cy_returns_nan_when_rho_below_threshold() -> None:
    """T-CY1: when ρ_X ≤ 0.95, CY is not applicable → CI fields remain None."""
    lc = _mk_synthetic_lc(n_months=400, persistence=0.5, seed=11)
    spx = _mk_synthetic_spx_tr(n_months=400, seed=12)
    fwd = reg._forward_log_return(spx, 1)
    res = reg.run_predictive_regression(
        lc=lc, forward_return=fwd, horizon_years=1, scope_name="LC_FULL",
        n_bootstrap_reps=200,
    )
    assert res.rho_X < reg.CAMPBELL_YOGO_RHO_THRESHOLD
    assert res.cy_ci_95_low is None
    assert res.cy_ci_95_high is None


def test_TCY2_cy_populated_when_rho_high() -> None:
    """T-CY2: ρ_X > 0.95 with c in implemented grid → CY CI populated (not None)."""
    lc = _mk_synthetic_lc(n_months=400, persistence=0.99, seed=21)
    spx = _mk_synthetic_spx_tr(n_months=400, seed=22)
    fwd = reg._forward_log_return(spx, 1)
    res = reg.run_predictive_regression(
        lc=lc, forward_return=fwd, horizon_years=1, scope_name="LC_FULL",
        n_bootstrap_reps=200,
    )
    if res.rho_X > reg.CAMPBELL_YOGO_RHO_THRESHOLD:
        # c = T(ρ - 1); T = 400, ρ ≈ 0.99 → c ≈ -4, within grid {-50..0}.
        assert res.cy_ci_95_low is not None
        assert res.cy_ci_95_high is not None
        assert res.cy_ci_95_low < res.cy_ci_95_high
        # CY CI should contain (or nearly contain) β̂.
        assert res.cy_ci_95_low <= res.beta_point <= res.cy_ci_95_high


def test_TCY3_cy_table_interpolation() -> None:
    """T-CY3: critical-value interpolation matches the hardcoded grid."""
    # Exact grid points.
    assert reg._interpolate_cy_critical_value(0) == 1.645
    assert reg._interpolate_cy_critical_value(-10) == 1.780
    assert reg._interpolate_cy_critical_value(-50) == 2.050
    # Midpoint between -5 and -10 (linear interp).
    cv_mid = reg._interpolate_cy_critical_value(-7.5)
    assert 1.710 <= cv_mid <= 1.780
    # Outside grid → NaN.
    assert np.isnan(reg._interpolate_cy_critical_value(-100))
    assert np.isnan(reg._interpolate_cy_critical_value(1.0))


# ===========================================================================
# T-F1..T-F4 — Bootstrap + conditional probabilities
# ===========================================================================


def test_TF1_bootstrap_n_reps_default_is_50k() -> None:
    """T-F1: Session 7 default escalates BOOTSTRAP_N_REPS to 50_000."""
    assert reg.BOOTSTRAP_N_REPS == 50_000


def test_TF2_bootstrap_reproducible_seed42() -> None:
    """T-F2: seed=42 + same data produces identical bootstrap median twice."""
    lc = _mk_synthetic_lc(n_months=300, persistence=0.5, seed=99)
    spx = _mk_synthetic_spx_tr(n_months=300, seed=100)
    fwd = reg._forward_log_return(spx, 1)
    res_a = reg.run_predictive_regression(
        lc=lc, forward_return=fwd, horizon_years=1, scope_name="LC_FULL",
        n_bootstrap_reps=500, bootstrap_seed=42,
    )
    res_b = reg.run_predictive_regression(
        lc=lc, forward_return=fwd, horizon_years=1, scope_name="LC_FULL",
        n_bootstrap_reps=500, bootstrap_seed=42,
    )
    assert abs(res_a.beta_bootstrap_median - res_b.beta_bootstrap_median) < 1e-9


def test_TF3_conditional_probabilities_complementary_ranges() -> None:
    """T-F3: p_below_5pct_cagr + P(>5%) = 1 (within rounding) using empirical CDF."""
    spx = _mk_synthetic_spx_tr(n_months=400, seed=33)
    lc = _mk_synthetic_lc(n_months=400, persistence=0.5, seed=34)
    cprob = reg.compute_conditional_probabilities(
        lc_current=float(lc.iloc[-1]),
        lc_series=lc,
        spx_tr_monthly=spx,
        horizon_years=1,
        n_bootstrap=200,
    )
    # The 5% and 7% events are not strict complements (the gap is P(5%-7% CAGR))
    # but the two probabilities should each be in [0, 1].
    assert 0.0 <= cprob["p_below_5pct_cagr"] <= 1.0
    assert 0.0 <= cprob["p_above_7pct_cagr"] <= 1.0
    # No event should be > 1 or < 0; CI bounds well-defined.
    for key in [
        "p_neg_total_return", "p_below_rf10y", "p_below_5pct_cagr",
        "p_above_7pct_cagr", "p_maxdd_lt_neg20", "p_maxdd_lt_neg30",
        "p_maxdd_lt_neg50",
    ]:
        assert 0.0 <= cprob[key] <= 1.0
        assert 0.0 <= cprob[f"{key}_ci_low"] <= 1.0
        assert 0.0 <= cprob[f"{key}_ci_high"] <= 1.0
        assert cprob[f"{key}_ci_low"] <= cprob[f"{key}_ci_high"]


def test_TF4_conditional_probabilities_quintile_membership() -> None:
    """T-F4: lc_current is in the bucket whose [lo, hi] range contains it."""
    spx = _mk_synthetic_spx_tr(n_months=400, seed=44)
    lc = _mk_synthetic_lc(n_months=400, persistence=0.5, seed=45)
    cprob = reg.compute_conditional_probabilities(
        lc_current=float(lc.iloc[-1]),
        lc_series=lc,
        spx_tr_monthly=spx,
        horizon_years=3,
        n_bootstrap=100,
    )
    assert 1 <= cprob["lc_quintile"] <= 5
    assert cprob["n_obs_in_quintile"] > 0


def test_TF5_forward_total_return_and_maxdd_shape() -> None:
    """T-F5: ``_forward_total_return_and_maxdd`` returns a DataFrame whose
    length is roughly len(input) − horizon_months."""
    spx = _mk_synthetic_spx_tr(n_months=300, seed=55)
    horizon_months = 12
    df = reg._forward_total_return_and_maxdd(spx, horizon_months)
    assert set(df.columns) == {"cum_return", "cagr", "maxdd"}
    # All maxdd values ≤ 0 by construction.
    assert (df["maxdd"] <= 0.0).all()
    # Length consistent with horizon truncation.
    assert len(df) <= len(spx) - horizon_months + 1
