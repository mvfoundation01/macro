"""Acceptance tests for Spec v4.2 (Dual-frame z-scores).

These tests hit the REAL ingestion outputs and FRED API. They're tagged
@pytest.mark.acceptance so the regular ``pytest -q`` run skips them unless
ACCEPTANCE=1 is set.

Run via:
    set ACCEPTANCE=1
    python -m pytest tests/test_v4_acceptance.py -v --no-cov
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


_NARRATIVE_CODES = {
    "AGREE_EXTREME_HIGH",
    "AGREE_EXTREME_LOW",
    "AGREE_FAIR",
    "BUBBLE_OR_SHIFT",
    "CRASH_OR_SHIFT",
    "MIXED",
}


def _acceptance_enabled() -> bool:
    return os.environ.get("ACCEPTANCE") == "1"


@pytest.mark.acceptance
def test_v42_dual_frame_structure() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.models.orchestrator_modeling import run_modeling

    r = run_modeling(bootstrap_n=2000)
    h = r["headline"]

    # v4.2 required these three BI variants; v6 added 'cape' as a 4th.
    required = {"bi_allequity_pct", "bi_wilshire_pct", "bi_spx_proxy"}
    assert required <= set(h["variants"].keys())

    # Each variant has both frames + frame_interpretation.
    for v in h["variants"].values():
        assert "long_run" in v
        assert "current_regime" in v
        assert "frame_interpretation" in v
        for frame in (v["long_run"], v["current_regime"]):
            assert set(frame.keys()) >= {
                "z_score",
                "z_score_ci95",
                "empirical_percentile",
                "regime",
                "confidence_pct",
                "trend_method",
            }
            assert 0 < frame["confidence_pct"] <= 100
        assert v["frame_interpretation"]["narrative_code"] in _NARRATIVE_CODES

    # Per-frame cross-variant blocks present.
    assert "cross_variant_long_run" in h
    assert "cross_variant_current_regime" in h

    # Interpretation block populated with prose.
    assert h["interpretation"]["primary_frame"] == "long_run"
    assert len(h["interpretation"]["narrative"]) > 100


@pytest.mark.acceptance
def test_v42_long_run_overvalued_may2026() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.models.orchestrator_modeling import run_modeling

    r = run_modeling(bootstrap_n=2000)
    # v4.2's "all variants overvalued" check applies to the original BI variants
    # only; v6 added 'cape' and v7 added 'qratio', 'ey_deficit', 'mvci' which
    # have different distributions and need their own thresholds (see v6/v7).
    v4_2_keys = {"bi_allequity_pct", "bi_wilshire_pct", "bi_spx_proxy"}
    for name, v in r["headline"]["variants"].items():
        if name not in v4_2_keys:
            continue
        assert v["long_run"]["z_score"] > 1.0
        assert v["long_run"]["empirical_percentile"] > 85


@pytest.mark.acceptance
def test_v42_bi_spx_scaled() -> None:
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.models.orchestrator_modeling import run_modeling

    r = run_modeling(bootstrap_n=2000)
    assert 150 <= r["headline"]["variants"]["bi_spx_proxy"]["bi_value"] <= 350


@pytest.mark.acceptance
def test_v42_backtest_view_present() -> None:
    """Backtest view should have the same dual-frame structure."""
    if not _acceptance_enabled():
        pytest.skip("ACCEPTANCE!=1")
    from src.models.orchestrator_modeling import run_modeling

    r = run_modeling(bootstrap_n=2000)
    bt = r["backtest_view"]
    assert "variants" in bt
    for v in bt["variants"].values():
        assert "long_run" in v and "current_regime" in v
