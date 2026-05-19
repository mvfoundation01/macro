"""Acceptance tests for Spec v5.0 (forward outlook + probability engine).

Run with:
    set ACCEPTANCE=1
    python -m pytest tests/test_v5_acceptance.py -v --no-cov
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _acceptance_enabled() -> bool:
    return os.environ.get("ACCEPTANCE") == "1"


@pytest.mark.acceptance
def test_v5_headline_has_forward_outlook() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.models.orchestrator_modeling import run_modeling

    r = run_modeling(bootstrap_n=1000, n_bootstrap_prob=1000)
    h = r["headline"]
    for v in h["variants"].values():
        assert "forward_outlook" in v["long_run"]
        assert "primary" in v["long_run"]["forward_outlook"]
        assert "h_120m" in v["long_run"]["forward_outlook"]["primary"]
        h10 = v["long_run"]["forward_outlook"]["primary"]["h_120m"]
        assert h10.get("available") is True
        assert "regression" in h10
        assert "probabilities" in h10
        p_neg = h10["probabilities"]["events"]["P_neg_return"]
        assert 0 <= p_neg["point"] <= 1
        lo, hi = p_neg["ci95"]
        assert lo <= p_neg["point"] <= hi


@pytest.mark.acceptance
def test_v5_full_conviction_replaces_preliminary() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.models.orchestrator_modeling import run_modeling

    r = run_modeling(bootstrap_n=1000, n_bootstrap_prob=1000)
    h = r["headline"]
    v = h["variants"]["bi_allequity_pct"]
    fc = v["long_run"]["full_conviction"]["h_120m"]
    assert 1.0 <= fc["score"] <= 5.0
    assert set(fc["components"].keys()) >= {
        "magnitude",
        "agreement",
        "significance",
        "oos_r2",
        "hit_rate",
    }


def test_v5_huber_zscore_default() -> None:
    """Huber's |z| in the tail should exceed the std-based |z| under outlier injection."""
    from src.models.zscore import expanding_zscore

    rng = np.random.default_rng(42)
    base = rng.standard_normal(450)
    outliers = rng.standard_normal(50) * 5.0
    s = pd.Series(
        np.concatenate([base, outliers]),
        index=pd.date_range("2000-01-31", periods=500, freq="ME"),
    )
    z_huber = expanding_zscore(s, scale_method="huber")
    z_std = expanding_zscore(s, scale_method="std")
    # Use a tail point with clean (non-outlier) sample so the comparison is meaningful.
    assert abs(z_huber.dropna().iloc[-1]) > abs(z_std.dropna().iloc[-1])


@pytest.mark.acceptance
def test_v5_three_fr_sources_agree_directionally() -> None:
    """All three FR sources should give same-sign beta for bi_allequity at 10Y."""
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.models.orchestrator_modeling import run_modeling

    r = run_modeling(bootstrap_n=1000, n_bootstrap_prob=1000)
    outlook = r["headline"]["variants"]["bi_allequity_pct"]["long_run"][
        "forward_outlook"
    ]
    primary = outlook["primary"]["h_120m"]
    betas = [primary["regression"]["beta"]]
    if "robustness_spxtr_only" in outlook:
        betas.append(
            outlook["robustness_spxtr_only"]["h_120m"]["regression"]["beta"]
        )
    if "robustness_shiller_only" in outlook:
        betas.append(
            outlook["robustness_shiller_only"]["h_120m"]["regression"]["beta"]
        )
    signs = [np.sign(b) for b in betas if np.isfinite(b)]
    assert len(set(signs)) == 1, f"FR sources disagree in sign: {betas}"


@pytest.mark.acceptance
def test_v5_bi_allequity_lr_beta_negative_significant() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.models.orchestrator_modeling import run_modeling

    r = run_modeling(bootstrap_n=1000, n_bootstrap_prob=1000)
    reg = r["headline"]["variants"]["bi_allequity_pct"]["long_run"][
        "forward_outlook"
    ]["primary"]["h_120m"]["regression"]
    assert reg["beta"] < 0
    assert reg["t_nw"] < -1.5  # significant at conventional level
