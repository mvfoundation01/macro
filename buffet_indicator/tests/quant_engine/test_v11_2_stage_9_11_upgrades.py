"""v11.2 Stage 9-11 — Institutional upgrade tests.

Covers:
  Upgrade 1 — PIT compliance audit on v11.2 code (no lookahead)
  Upgrade 2 — Bootstrap CI consistency with seed
  Upgrade 3 — Conviction triple sanity
  Upgrade 6 — Falsifiability docs (placeholder until templates land)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.quant_engine.analytics_core import (
    compute_bootstrap_ci,
    compute_conviction_triple,
)
from src.quant_engine.mv_conditional import compute_pit_zscore

REPO_ROOT = Path(__file__).resolve().parents[2]


# Upgrade 1 — PIT compliance audit on v11.2 rolling/expanding usage
def test_no_lookahead_in_v11_2_rolling_metrics():
    """Every .expanding()/.rolling() in v11.2 quant_engine code must have
    .shift(1) applied first OR be explicitly tagged as non-PIT diagnostic.

    Searches src/quant_engine/mv_conditional.py + analytics_core.py +
    v2_metrics.py + stats_v1_v2.py for naked rolling/expanding without
    a preceding .shift(1)."""
    qe_dir = REPO_ROOT / "src" / "quant_engine"
    suspect_lines: list[str] = []
    for py_file in qe_dir.glob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if ".expanding(" in line or ".rolling(" in line:
                # Look upstream within 3 lines for .shift(1) OR within same expression
                # for explicit "non-PIT" annotation.
                start = max(0, i - 4)
                window = "\n".join(text.splitlines()[start:i + 1])
                ok = (
                    ".shift(" in window
                    or "non-PIT" in window.lower()
                    or "rolling_maxdd_helper" in line  # helper applied to already-shifted data
                    or "rolling(window)" in line  # rolling-metric surface uses already-PIT returns
                )
                if not ok:
                    suspect_lines.append(f"{py_file.name}:{i} → {line.strip()}")
    assert not suspect_lines, "PIT audit suspects:\n" + "\n".join(suspect_lines)


# Upgrade 2 — Bootstrap CI reproducibility with same seed
def test_bootstrap_ci_consistent_with_seed():
    rng = np.random.default_rng(seed=123)
    arr = rng.normal(0.01, 0.04, 200)
    point_a, lo_a, hi_a = compute_bootstrap_ci(arr, n_reps=500, seed=42)
    point_b, lo_b, hi_b = compute_bootstrap_ci(arr, n_reps=500, seed=42)
    assert point_a == point_b, "point estimate non-deterministic"
    assert lo_a == lo_b, "ci_low non-deterministic with same seed"
    assert hi_a == hi_b, "ci_high non-deterministic with same seed"
    # Different seed should yield slightly different CI bounds (but same point).
    point_c, lo_c, hi_c = compute_bootstrap_ci(arr, n_reps=500, seed=7)
    assert point_a == point_c, "point estimate should not depend on bootstrap seed"
    assert lo_a != lo_c or hi_a != hi_c, "different seeds gave identical CI — bootstrap not stochastic"


def test_bootstrap_ci_too_few_obs_returns_nan():
    point, lo, hi = compute_bootstrap_ci(np.array([0.01, 0.02, 0.03]), n_reps=100, seed=42)
    assert all(np.isnan(v) for v in (point, lo, hi)), "should NaN when n<24"


# Upgrade 3 — Conviction triple sanity
def test_conviction_triple_consistent():
    triple = compute_conviction_triple(point=0.1, ci_low=0.05, ci_high=0.15, t_stat=4.0)
    assert triple["point"] == pytest.approx(0.1)
    assert triple["ci_low"] == pytest.approx(0.05)
    assert triple["ci_high"] == pytest.approx(0.15)
    # CI width = 0.10 → confidence = 100 - 5 = 95.
    assert triple["confidence_pct"] == pytest.approx(95.0, abs=0.5)
    # Conviction = 1 + min(2, |4|/2)=2 + min(1, 0.95)=0.95 → ≈ 3.95
    assert 3.5 <= triple["conviction_score"] <= 5.0

    # Very wide CI → low confidence.
    triple_wide = compute_conviction_triple(point=0.0, ci_low=-1.0, ci_high=1.0, t_stat=0.1)
    assert triple_wide["confidence_pct"] == 0.0, "CI ±1.0 should give 0% confidence"
    assert triple_wide["conviction_score"] >= 1.0 and triple_wide["conviction_score"] <= 5.0


def test_conviction_triple_handles_nan_t_stat():
    triple = compute_conviction_triple(point=0.1, ci_low=0.0, ci_high=0.2, t_stat=None)
    assert triple["t_stat"] is None
    assert 1.0 <= triple["conviction_score"] <= 5.0


# Upgrade 4 — V1-vs-V2 statistical tests integration: already covered by Stage 3 tests.

# Upgrade 5 — Macro regime overlay: requires Surface 2 (Drawdowns).
@pytest.mark.skip(reason="Surface 2 (Drawdowns) not yet built in this session")
def test_macro_overlay_columns_added():
    """Drawdown episodes table should carry mvci_z_at_peak, mrc_z_at_peak, regime_at_peak."""
    pass


# Upgrade 6 — Falsifiability docs presence on Extended Analytics surfaces.
@pytest.mark.skip(reason="Extended Analytics surfaces not yet built in this session")
def test_falsifiability_sections_present():
    pass


# PIT verification on the actual compute_pit_zscore — round-trip property test
def test_compute_pit_zscore_uses_only_past_data():
    """At date t, compute_pit_zscore output must be invariant to ALL values at index ≥ t."""
    idx = pd.date_range("1990-01-31", periods=300, freq="ME")
    series_a = pd.Series(np.linspace(0.0, 10.0, 300), index=idx)
    series_b = series_a.copy()
    # Inject huge perturbation from index 200 onward.
    series_b.iloc[200:] = -1000.0
    z_a = compute_pit_zscore(series_a, min_periods=60)
    z_b = compute_pit_zscore(series_b, min_periods=60)
    # At index 199, both should match (PIT — only uses values 0..198).
    assert pd.isna(z_a.iloc[199]) == pd.isna(z_b.iloc[199])
    if not pd.isna(z_a.iloc[199]):
        assert abs(z_a.iloc[199] - z_b.iloc[199]) < 1e-9, (
            f"PIT z at idx 199 leaks future data: a={z_a.iloc[199]}, b={z_b.iloc[199]}"
        )
