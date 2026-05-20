"""v11.0 acceptance tests for the Macro Risk Composite (MRC)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from src.transform.mrc_compute import (
    MRC_CONSTITUENTS,
    compute_mrc,
    correlation_with,
    latest_mrc_z,
)


def _load_fred_key() -> str | None:
    cfg = yaml.safe_load(Path("config.yaml").read_text()) or {}
    key = cfg.get("fred_api_key")
    return str(key) if key and key != "PASTE_YOUR_32_CHAR_KEY_HERE" else None


@pytest.fixture(scope="module")
def mrc_result() -> dict:
    api_key = _load_fred_key()
    return compute_mrc(api_key=api_key)


def test_mrc_has_seven_constituents(mrc_result: dict) -> None:
    """All 7 macro indicators must be present (assuming FRED key available)."""
    assert len(MRC_CONSTITUENTS) == 7
    if _load_fred_key():
        assert set(mrc_result["constituents"]) == set(MRC_CONSTITUENTS)
    else:
        # No FRED key → yc_10y2y is absent; 6 constituents.
        assert len(mrc_result["constituents"]) == 6


def test_mrc_value_history_emits_three_weighting_schemes(mrc_result: dict) -> None:
    assert set(mrc_result["schemes"].keys()) == {
        "equal_weight",
        "inv_variance",
        "pca_pc1",
    }
    for scheme_name, sch in mrc_result["schemes"].items():
        assert "z_score_series" in sch
        assert "z_score" in sch
        assert isinstance(sch["z_score_series"], pd.Series)


def test_mrc_pca_loadings_all_constituents_present(mrc_result: dict) -> None:
    """PCA loadings_full dict should have one entry per constituent."""
    pca = mrc_result["schemes"]["pca_pc1"]
    loadings = pca.get("loadings_full", {})
    assert set(loadings.keys()) == set(mrc_result["constituents"])
    # No zero loading (PC1 should weight every variant non-trivially).
    nonzero = sum(1 for v in loadings.values() if abs(v) > 1e-6)
    assert nonzero >= 6


def test_corr_mvci_mrc_below_threshold(mrc_result: dict) -> None:
    """Acceptance gate §5.3: corr(MVCI, MRC) must be < 0.8."""
    z_history_path = Path("outputs/charts/z_history.parquet")
    if not z_history_path.exists():
        pytest.skip(
            "z_history.parquet absent; cannot evaluate MVCI×MRC correlation."
        )
    df = pd.read_parquet(z_history_path)
    mvci_lr = (
        df[(df["variant"] == "mvci") & (df["frame"] == "long_run")][["date", "z_score"]]
        .set_index("date")["z_score"]
    )
    corr = correlation_with(mvci_lr, mrc_result, scheme="equal_weight")
    assert not np.isnan(corr), "Insufficient overlap between MVCI and MRC series."
    assert abs(corr) < 0.8, f"corr(MVCI, MRC) = {corr:.3f} exceeds 0.8 gate."


def test_mrc_2008_crisis_positive_signal(mrc_result: dict) -> None:
    """MRC equal-weight z-score must turn positive (bearish) in 2008 H2."""
    series = mrc_result["schemes"]["equal_weight"]["z_score_series"]
    crisis = series.loc["2008-09-01":"2009-03-31"]
    assert not crisis.empty
    peak = float(crisis.max())
    assert peak > 0.5, (
        f"MRC peak during 2008 crisis = {peak:+.3f}σ; expected > +0.5σ "
        "(stress regime should show clear positive deflection)."
    )


def test_mrc_z_panel_aligned_monthly(mrc_result: dict) -> None:
    """z_panel index should be monotonic monthly DatetimeIndex."""
    panel = mrc_result["z_panel"]
    assert isinstance(panel.index, pd.DatetimeIndex)
    assert panel.index.is_monotonic_increasing


def test_latest_mrc_z_returns_float(mrc_result: dict) -> None:
    z = latest_mrc_z(mrc_result, scheme="equal_weight")
    assert isinstance(z, float)
    assert not np.isnan(z)
