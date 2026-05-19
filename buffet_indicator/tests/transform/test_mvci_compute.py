"""Tests for src.transform.mvci_compute."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.transform.mvci_compute import (
    compute_mvci_schemes,
    equal_weight_mvci,
    inv_variance_mvci,
    pca_pc1_mvci,
)


def _panel(
    n: int = 240, n_cons: int = 6, seed: int = 0, sigmas: list[float] | None = None
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    if sigmas is None:
        sigmas = [1.0] * n_cons
    cols = {}
    for i in range(n_cons):
        cols[f"c{i}"] = rng.standard_normal(n) * sigmas[i]
    return pd.DataFrame(cols, index=idx)


# ---------------------------------------------------------------------------
# MV1 -- identical inputs -> output equals that series
# ---------------------------------------------------------------------------


def test_MV1_identical_constituents_returns_them() -> None:
    rng = np.random.default_rng(1)
    series = rng.standard_normal(120)
    panel = pd.DataFrame(
        {f"c{i}": series for i in range(6)},
        index=pd.date_range("2010-01-31", periods=120, freq="ME"),
    )
    out = equal_weight_mvci(panel)
    np.testing.assert_allclose(out["z_score_series"].values, series, atol=1e-12)


# ---------------------------------------------------------------------------
# MV2 -- inputs that sum to zero each row -> MVCI ~ 0
# ---------------------------------------------------------------------------


def test_MV2_zero_sum_inputs_mvci_zero() -> None:
    idx = pd.date_range("2010-01-31", periods=60, freq="ME")
    panel = pd.DataFrame(
        {"a": [1.0] * 60, "b": [-1.0] * 60},
        index=idx,
    )
    out = equal_weight_mvci(panel)
    assert (out["z_score_series"].abs() < 1e-12).all()


# ---------------------------------------------------------------------------
# MV3 -- inv-variance: high-variance constituent gets lower weight
# ---------------------------------------------------------------------------


def test_MV3_inv_variance_downweights_noisy() -> None:
    panel = _panel(n=240, n_cons=3, seed=2, sigmas=[1.0, 1.0, 5.0])
    out = inv_variance_mvci(panel, min_periods=60)
    w = out["weights_current"]
    assert w["c2"] < w["c0"]
    assert w["c2"] < w["c1"]


# ---------------------------------------------------------------------------
# MV4 -- PCA first PC loadings sum to ~1 (and after sign-fix, positive)
# ---------------------------------------------------------------------------


def test_MV4_pca_loadings_sum_to_one() -> None:
    # Positively-correlated constituents -> first PC has positive loadings.
    rng = np.random.default_rng(3)
    n = 240
    common = rng.standard_normal(n)
    panel = pd.DataFrame(
        {f"c{i}": common + 0.3 * rng.standard_normal(n) for i in range(6)},
        index=pd.date_range("2000-01-31", periods=n, freq="ME"),
    )
    out = pca_pc1_mvci(panel, min_periods=60)
    w = list(out["weights_current"].values())
    assert sum(w) == pytest.approx(1.0, abs=1e-9)
    assert all(x > 0 for x in w)


# ---------------------------------------------------------------------------
# MV5 -- PCA explained variance in [0, 1]
# ---------------------------------------------------------------------------


def test_MV5_pca_explained_variance_in_unit_interval() -> None:
    panel = _panel(n=240, n_cons=6, seed=4)
    out = pca_pc1_mvci(panel, min_periods=60)
    ev = out["explained_variance"]
    assert ev is not None
    assert 0.0 <= ev <= 1.0


# ---------------------------------------------------------------------------
# MV6 -- min_periods=60 respected
# ---------------------------------------------------------------------------


def test_MV6_min_periods_respected_for_inv_variance() -> None:
    panel = _panel(n=120, n_cons=3, seed=5)
    out = inv_variance_mvci(panel, min_periods=60)
    series = out["z_score_series"]
    assert series.iloc[:59].isna().all()
    assert series.iloc[60:].notna().any()


# ---------------------------------------------------------------------------
# MV7 -- index matches input panel
# ---------------------------------------------------------------------------


def test_MV7_index_matches_panel() -> None:
    panel = _panel(n=200, n_cons=4, seed=6)
    eq = equal_weight_mvci(panel)
    iv = inv_variance_mvci(panel)
    pc = pca_pc1_mvci(panel)
    for out in (eq, iv, pc):
        assert out["z_score_series"].index.equals(panel.index)


# ---------------------------------------------------------------------------
# MV8 -- single constituent edge case
# ---------------------------------------------------------------------------


def test_MV8_single_constituent_returns_that_series() -> None:
    idx = pd.date_range("2010-01-31", periods=80, freq="ME")
    rng = np.random.default_rng(7)
    only = pd.Series(rng.standard_normal(80), index=idx, name="c0")
    panel = pd.DataFrame({"c0": only})
    out = equal_weight_mvci(panel)
    np.testing.assert_allclose(out["z_score_series"].values, only.values, atol=1e-12)
    assert out["weights_current"] == {"c0": 1.0}


def test_compute_mvci_schemes_returns_all_three() -> None:
    panel = _panel(n=200, n_cons=4, seed=8)
    schemes = compute_mvci_schemes(panel)
    assert set(schemes.keys()) == {"equal_weight", "inv_variance", "pca_pc1"}
    for s in schemes.values():
        assert "z_score_series" in s
        assert "weights_current" in s
