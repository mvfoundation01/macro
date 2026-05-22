"""Tests for ``src.models.lc_v1_composite`` (LC v1.0 sub-stage D).

Coverage target: ≥90% per Session 6 prompt §2.D.

References
----------
* specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.1 + §1.2 — sealed.
* prompt/052226/PROMPT_v11_3_stage_3_LC_v1_session_6.md §2.D.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.models import lc_v1_composite as composite


# ---------------------------------------------------------------------------
# Helpers — synthetic z-component series
# ---------------------------------------------------------------------------


def _mk_z_series(
    name: str, start: str = "1970-01-31", n: int = 800, fill: float = 1.0,
) -> pd.Series:
    """Build a monthly EOM z-series with constant fill (good for weight tests)."""
    idx = pd.date_range(start, periods=n, freq="ME")
    return pd.Series(np.full(n, fill, dtype="float64"), index=idx, name=name)


# ===========================================================================
# T-D1.* — LC_FULL
# ===========================================================================


def test_TD1_1_lc_full_formula_unit_components() -> None:
    """T-D1.1: with all z's = 1.0, LC_FULL = 0.25 + 0.20 + 0.20 + 0.20 - 0.15 = 0.70."""
    z1 = _mk_z_series("z1", start="2003-01-31", n=300, fill=1.0)
    z2 = _mk_z_series("z2", start="2003-01-31", n=300, fill=1.0)
    z3 = _mk_z_series("z3", start="2003-01-31", n=300, fill=1.0)
    z4 = _mk_z_series("z4", start="2003-01-31", n=300, fill=1.0)
    z5 = _mk_z_series("z5", start="2003-01-31", n=300, fill=1.0)
    lc = composite.compute_lc_full(z1, z2, z3, z4, z5)
    # Expected = 0.25 + 0.20 + 0.20 + 0.20 - 0.15 = 0.70.
    expected = 0.25 + 0.20 + 0.20 + 0.20 - 0.15
    np.testing.assert_allclose(np.asarray(lc.dropna().values, dtype=float), expected, atol=1e-9)


def test_TD1_2_lc_full_weights_sum_to_one() -> None:
    """T-D1.2: |+0.25|+|+0.20|+|+0.20|+|+0.20|+|-0.15| = 1.00 exactly."""
    total = sum(abs(w) for w in composite.LC_FULL_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-12


def test_TD1_3_lc_full_nan_before_active_from() -> None:
    """T-D1.3: LC_FULL is NaN before 2003-01."""
    z1 = _mk_z_series("z1", start="1995-01-31", n=300, fill=1.0)
    z2 = _mk_z_series("z2", start="1995-01-31", n=300, fill=1.0)
    z3 = _mk_z_series("z3", start="1995-01-31", n=300, fill=1.0)
    z4 = _mk_z_series("z4", start="1995-01-31", n=300, fill=1.0)
    z5 = _mk_z_series("z5", start="1995-01-31", n=300, fill=1.0)
    lc = composite.compute_lc_full(z1, z2, z3, z4, z5)
    assert lc.loc[lc.index < composite.LC_FULL_ACTIVE_FROM].isna().all()


def test_TD1_4_lc_full_nan_where_any_component_nan() -> None:
    """T-D1.4: LC_FULL is NaN when any input component is NaN."""
    idx = pd.date_range("2003-01-31", periods=200, freq="ME")
    z1 = pd.Series(np.full(200, 1.0), index=idx)
    z2 = pd.Series(np.full(200, 1.0), index=idx)
    z3 = pd.Series(np.full(200, 1.0), index=idx)
    z4 = pd.Series(np.full(200, 1.0), index=idx)
    z5 = pd.Series(np.full(200, 1.0), index=idx)
    z3.iloc[50] = np.nan  # Inject NaN in z3 at row 50.
    lc = composite.compute_lc_full(z1, z2, z3, z4, z5)
    assert pd.isna(lc.iloc[50])
    assert pd.notna(lc.iloc[49])  # neighbors are fine
    assert pd.notna(lc.iloc[51])


# ===========================================================================
# T-D2.* — LC_TIER2
# ===========================================================================


def test_TD2_1_lc_tier2_renormalized_weights() -> None:
    """T-D2.1: |+0.267|·3 + |-0.200| = 1.001 (≈ 1.000 within rounding)."""
    total = sum(abs(w) for w in composite.LC_TIER2_WEIGHTS.values())
    assert abs(total - 1.001) < 1e-9
    # All z's = 1.0 → LC_TIER2 = 0.267·3 - 0.200 = 0.601.
    z2 = _mk_z_series("z2", start="1987-01-31", n=300, fill=1.0)
    z3 = _mk_z_series("z3", start="1987-01-31", n=300, fill=1.0)
    z4 = _mk_z_series("z4", start="1987-01-31", n=300, fill=1.0)
    z5 = _mk_z_series("z5", start="1987-01-31", n=300, fill=1.0)
    lc = composite.compute_lc_tier2(z2, z3, z4, z5)
    expected = 0.267 * 3.0 - 0.200
    np.testing.assert_allclose(np.asarray(lc.dropna().values, dtype=float), expected, atol=1e-9)


def test_TD2_2_lc_tier2_nan_before_active_from() -> None:
    """T-D2.2: LC_TIER2 is NaN before 1987-01."""
    z2 = _mk_z_series("z2", start="1980-01-31", n=300, fill=1.0)
    z3 = _mk_z_series("z3", start="1980-01-31", n=300, fill=1.0)
    z4 = _mk_z_series("z4", start="1980-01-31", n=300, fill=1.0)
    z5 = _mk_z_series("z5", start="1980-01-31", n=300, fill=1.0)
    lc = composite.compute_lc_tier2(z2, z3, z4, z5)
    assert lc.loc[lc.index < composite.LC_TIER2_ACTIVE_FROM].isna().all()


# ===========================================================================
# T-D3.* — LC_DEEP
# ===========================================================================


def test_TD3_1_lc_deep_renormalized_weights() -> None:
    """T-D3.1: |+0.333|·3 = 0.999 (≈ 1.000 within rounding)."""
    total = sum(abs(w) for w in composite.LC_DEEP_WEIGHTS.values())
    assert abs(total - 0.999) < 1e-9
    z2 = _mk_z_series("z2", start="1973-01-31", n=600, fill=1.0)
    z3 = _mk_z_series("z3", start="1973-01-31", n=600, fill=1.0)
    z4 = _mk_z_series("z4", start="1973-01-31", n=600, fill=1.0)
    lc = composite.compute_lc_deep(z2, z3, z4)
    expected = 0.333 * 3.0
    np.testing.assert_allclose(np.asarray(lc.dropna().values, dtype=float), expected, atol=1e-9)


def test_TD3_2_lc_deep_nan_before_active_from() -> None:
    """T-D3.2: LC_DEEP is NaN before 1973-01."""
    z2 = _mk_z_series("z2", start="1965-01-31", n=300, fill=1.0)
    z3 = _mk_z_series("z3", start="1965-01-31", n=300, fill=1.0)
    z4 = _mk_z_series("z4", start="1965-01-31", n=300, fill=1.0)
    lc = composite.compute_lc_deep(z2, z3, z4)
    assert lc.loc[lc.index < composite.LC_DEEP_ACTIVE_FROM].isna().all()


# ===========================================================================
# T-D4.* — Parquet output
# ===========================================================================


def _mk_full_z_set(start: str = "1970-01-31", n: int = 800, fill: float = 0.5) -> dict[str, pd.Series]:
    """Build a full set of 5 z-series at the same monthly index."""
    return {
        "z1": _mk_z_series("z1", start=start, n=n, fill=fill),
        "z2": _mk_z_series("z2", start=start, n=n, fill=fill),
        "z3": _mk_z_series("z3", start=start, n=n, fill=fill),
        "z4": _mk_z_series("z4", start=start, n=n, fill=fill),
        "z5": _mk_z_series("z5", start=start, n=n, fill=fill),
    }


def test_TD4_1_parquet_schema(tmp_path: Path) -> None:
    """T-D4.1: written parquet has columns LC_FULL, LC_TIER2, LC_DEEP + date index."""
    zs = _mk_full_z_set()
    df = composite.assemble_composites_frame(**zs)
    out = composite.write_composites_parquet(
        df, output_path=tmp_path / "lc_v1_composites.parquet",
        enforce_pre_reg=False,
    )
    read = pd.read_parquet(out)
    assert list(read.columns) == ["LC_FULL", "LC_TIER2", "LC_DEEP"]
    assert read.index.name == "date"
    assert pd.api.types.is_datetime64_any_dtype(read.index)


def test_TD4_2_parquet_metadata_records_pre_reg(tmp_path: Path) -> None:
    """T-D4.2: parquet file-level metadata records pre_reg_commit=a8635ef."""
    zs = _mk_full_z_set()
    df = composite.assemble_composites_frame(**zs)
    out = composite.write_composites_parquet(
        df, output_path=tmp_path / "lc_v1_composites.parquet",
        enforce_pre_reg=False,
    )
    meta = composite.read_composites_metadata(out)
    assert meta["pre_reg_commit"] == composite.PRE_REG_COMMIT
    assert meta["composite_version"] == "v1.0"
    assert "weights_full" in meta
    assert "weights_tier2" in meta
    assert "weights_deep" in meta
    assert "build_timestamp_utc" in meta


# ===========================================================================
# T-D5 — Pre-reg ancestor check
# ===========================================================================


def test_TD5_pre_reg_ancestor_passes_on_real_repo() -> None:
    """T-D5: pre-reg ancestor check passes on the current spec branch."""
    sha = composite._verify_pre_reg_ancestor()
    assert len(sha) == 40  # full SHA-1 hex


def test_TD5b_pre_reg_ancestor_fails_when_pre_reg_unknown(tmp_path: Path) -> None:
    """T-D5b: ancestor check raises when pre_reg_commit cannot be resolved."""
    with pytest.raises(RuntimeError, match=r"Pre-reg invariant VIOLATED"):
        composite._verify_pre_reg_ancestor(
            pre_reg_commit="deadbeef0000000000000000000000000000dead",
        )


def test_TD5c_write_composites_parquet_enforces_pre_reg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-D5c: when ``_verify_pre_reg_ancestor`` raises, the write aborts."""
    zs = _mk_full_z_set()
    df = composite.assemble_composites_frame(**zs)

    def _fail(*args: object, **kwargs: object) -> str:
        raise RuntimeError(
            "Pre-reg invariant VIOLATED: <test-injected failure>"
        )

    monkeypatch.setattr(composite, "_verify_pre_reg_ancestor", _fail)
    output_path = tmp_path / "should_not_be_written.parquet"
    with pytest.raises(RuntimeError, match=r"Pre-reg invariant VIOLATED"):
        composite.write_composites_parquet(
            df, output_path=output_path, enforce_pre_reg=True,
        )
    # The pre-reg check fires BEFORE the parquet write, so no file is created.
    assert not output_path.exists()


def test_TD5d_enforce_false_bypasses_ancestor_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-D5d: ``enforce_pre_reg=False`` skips the ancestor check entirely."""
    zs = _mk_full_z_set()
    df = composite.assemble_composites_frame(**zs)
    called: list[bool] = []

    def _spy(*args: object, **kwargs: object) -> str:
        called.append(True)
        return "fake-sha"

    monkeypatch.setattr(composite, "_verify_pre_reg_ancestor", _spy)
    output_path = tmp_path / "lc_v1_composites.parquet"
    composite.write_composites_parquet(
        df, output_path=output_path, enforce_pre_reg=False,
    )
    assert called == []  # _verify was NOT invoked
    assert output_path.exists()


# ===========================================================================
# T-D6 — Orchestrator end-to-end
# ===========================================================================


def test_TD6_build_lc_v1_composites_returns_df_and_path(tmp_path: Path) -> None:
    """T-D6: ``build_lc_v1_composites`` returns (df, path) and writes parquet."""
    zs = _mk_full_z_set()
    out_path = tmp_path / "lc_v1_composites.parquet"
    df, path = composite.build_lc_v1_composites(
        z1=zs["z1"], z2=zs["z2"], z3=zs["z3"], z4=zs["z4"], z5=zs["z5"],
        output_path=out_path,
        enforce_pre_reg=False,
    )
    assert isinstance(df, pd.DataFrame)
    assert path == out_path
    assert out_path.exists()
    assert set(df.columns) == {"LC_FULL", "LC_TIER2", "LC_DEEP"}
