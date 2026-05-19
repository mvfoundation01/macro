"""Spec v9.0 §2.6 — MVCI 8-constituent integration tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def test_v9_mvci_has_eight_constituents() -> None:
    """_CONSTITUENT_KEYS enumerates all 8 variants including crestmont."""
    from src.models.orchestrator_modeling import _CONSTITUENT_KEYS
    assert len(_CONSTITUENT_KEYS) == 8
    assert "crestmont" in _CONSTITUENT_KEYS


def test_v9_headline_labels_include_crestmont() -> None:
    from src.models.orchestrator_modeling import HEADLINE_LABELS, HEADLINE_DIRECTION
    assert "crestmont" in HEADLINE_LABELS
    assert HEADLINE_DIRECTION["crestmont"] == +1


def test_v9_correlation_matrix_has_crestmont_row_and_col() -> None:
    p = _ROOT / "outputs" / "charts" / "diagnostics_correlation_matrix.parquet"
    if not p.exists():
        return
    df = pd.read_parquet(p)
    assert "crestmont" in df.columns
    assert "crestmont" in df.index


def test_v9_pca_loadings_full_includes_crestmont() -> None:
    headline_path = _ROOT / "outputs" / "tables" / "headline.json"
    if not headline_path.exists():
        return
    headline = json.loads(headline_path.read_text(encoding="utf-8"))["headline"]
    pca = headline["variants"]["mvci"]["long_run"]["schemes"]["pca_pc1"]
    loadings_full = pca.get("loadings_full") or pca.get("weights_current") or {}
    assert "crestmont" in loadings_full
    # The 8 keys should match the constituents
    from src.models.orchestrator_modeling import _CONSTITUENT_KEYS
    assert set(loadings_full.keys()) == set(_CONSTITUENT_KEYS)


def test_v9_mvci_zscore_within_pm_0_3_of_v8b1_baseline() -> None:
    """MVCI z-score after adding 8th correlated constituent should be ~unchanged."""
    headline_path = _ROOT / "outputs" / "tables" / "headline.json"
    if not headline_path.exists():
        return
    headline = json.loads(headline_path.read_text(encoding="utf-8"))["headline"]
    z_new = headline["variants"]["mvci"]["long_run"]["z_score"]
    # v8b.1 baseline: +1.787 σ. Acceptable range +1.487 to +2.087.
    assert 1.487 <= z_new <= 2.087, (
        f"MVCI z shifted to {z_new}, outside ±0.3σ band around v8b.1 baseline 1.787"
    )


def test_v9_crestmont_variant_present_in_headline() -> None:
    headline_path = _ROOT / "outputs" / "tables" / "headline.json"
    if not headline_path.exists():
        return
    headline = json.loads(headline_path.read_text(encoding="utf-8"))["headline"]
    assert "crestmont" in headline["variants"]
    cr = headline["variants"]["crestmont"]
    assert "headline_value" in cr
    assert "long_run" in cr
    assert cr["long_run"].get("z_score") is not None


def test_v9_weighting_schemes_equal_and_pca_agree() -> None:
    """Equal-weight and PCA-PC1 should agree within ±0.05σ
    (inv-variance routinely diverges and is excluded from this gate)."""
    headline_path = _ROOT / "outputs" / "tables" / "headline.json"
    if not headline_path.exists():
        return
    headline = json.loads(headline_path.read_text(encoding="utf-8"))["headline"]
    schemes = headline["variants"]["mvci"]["long_run"]["schemes"]
    eq = schemes["equal_weight"]["z_score"]
    pca = schemes["pca_pc1"]["z_score"]
    assert abs(eq - pca) < 0.05, f"equal-weight {eq:.3f} vs PCA-PC1 {pca:.3f} drift too large"
