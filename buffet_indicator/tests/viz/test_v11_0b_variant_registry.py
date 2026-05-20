"""v11.0b variant-registry tests."""
from __future__ import annotations

from src.viz.data_extraction import (
    VARIANT_REGISTRY,
    list_indicators,
    variant_meta,
    _MACRO_VARIANTS,
    _MRC_WEIGHTING_VARIANTS,
)


REQUIRED_FIELDS = ("group", "label", "unit", "sample_start", "sample_end", "ref_paper", "direction")


def test_variant_registry_has_eight_valuation_constituents_and_eight_macro() -> None:
    """8 valuation constituents (excluding MVCI composite) + ≥ 7 macro
    constituents (v11.0c had 7; v11.0.1 added 6 derived → 13)
    + 1 MRC composite alias + 3 MRC weighting variants."""
    val = list_indicators(group="valuation")
    mac = list_indicators(group="macro_risk")
    val_constituents = tuple(k for k in val if k != "mvci")
    mac_constituents = tuple(
        k for k in mac if not k.startswith("mrc")
    )
    assert len(val_constituents) == 8, f"got {val_constituents}"
    # v11.0c = 7 macro constituents; v11.0.1 added 6 derived spreads → 13.
    assert len(mac_constituents) >= 7, f"got {mac_constituents}"
    # Composites
    assert "mvci" in val
    assert "mrc" in mac
    assert {"mrc_equal_weight", "mrc_inv_variance", "mrc_pca_pc1"}.issubset(mac)


def test_each_variant_has_required_fields() -> None:
    for key, meta in VARIANT_REGISTRY.items():
        missing = [f for f in REQUIRED_FIELDS if f not in meta]
        assert not missing, f"{key} missing fields: {missing}"


def test_mrc_weighting_variants_registered() -> None:
    for variant in _MRC_WEIGHTING_VARIANTS:
        assert variant in VARIANT_REGISTRY
        meta = variant_meta(variant)
        assert meta["group"] == "macro_risk"
        assert meta["unit"] == "sigma"


def test_macro_constituents_registered() -> None:
    for variant in _MACRO_VARIANTS:
        assert variant in VARIANT_REGISTRY
        meta = variant_meta(variant)
        assert meta["group"] == "macro_risk"


def test_yield_curve_direction_is_inverted() -> None:
    for variant in ("yc_10y3m", "yc_10y2y"):
        meta = variant_meta(variant)
        assert meta["direction"] == "high_bearish_inverted"


def test_credit_spread_direction_is_log() -> None:
    for variant in ("cs_hy_master", "cs_ig_master", "cs_hy_bb", "cs_hy_ccc"):
        meta = variant_meta(variant)
        assert meta["direction"] == "high_bearish_log"


def test_margin_debt_direction_is_log_growth() -> None:
    assert variant_meta("margin_debt_growth")["direction"] == "high_bearish_log_growth"


def test_unknown_variant_raises_keyerror() -> None:
    import pytest
    with pytest.raises(KeyError):
        variant_meta("does_not_exist")


def test_total_variant_count() -> None:
    """8 valuation + 8 macro-risk + 3 MRC weighting variants = 19."""
    assert len(VARIANT_REGISTRY) >= 19
