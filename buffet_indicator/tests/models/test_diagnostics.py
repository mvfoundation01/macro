"""Unit tests for src.models.diagnostics (Spec v8b §6.2)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.diagnostics import (  # noqa: E402
    compute_correlation_matrix,
    compute_oos_r2_evolution,
    compute_stationarity,
    emit_diagnostics,
)


def _synth_z_history(n_per_variant: int = 200, seed: int = 0) -> pd.DataFrame:
    """Build a synthetic z_history with 3 variants, 2 frames each."""
    rng = np.random.default_rng(seed)
    rows = []
    base_idx = pd.date_range("2000-01-31", periods=n_per_variant, freq="ME")
    for v_seed, vname in enumerate(("a", "b", "c")):
        # Slight cross-variant correlation: shared common factor
        common = rng.standard_normal(n_per_variant)
        idiosync = rng.standard_normal(n_per_variant)
        z = 0.7 * common + 0.3 * idiosync
        for frame in ("long_run", "current_regime"):
            offset = 0.1 if frame == "current_regime" else 0.0
            for i, date in enumerate(base_idx):
                rows.append(
                    {
                        "date": date,
                        "variant": vname,
                        "frame": frame,
                        "z_score": float(z[i] + offset),
                    }
                )
    return pd.DataFrame(rows)


def _synth_scatter(n: int = 200, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    z = rng.standard_normal(n)
    # forward return is correlated with z (negative slope mimics overvaluation -> lower future return)
    fwd = -0.03 * z + 0.07 + rng.standard_normal(n) * 0.02
    return pd.DataFrame(
        {
            "date": idx,
            "variant": "mvci",
            "z_score_long_run": z,
            "forward_120m_cagr": fwd,
        }
    )


def test_compute_stationarity_returns_one_row_per_variant_frame() -> None:
    zh = _synth_z_history()
    df = compute_stationarity(zh)
    # 3 variants × 2 frames = 6 rows
    assert len(df) == 6
    for col in ("variant", "frame", "n_obs", "adf_pvalue", "kpss_pvalue", "pp_pvalue", "za_pvalue"):
        assert col in df.columns


def test_compute_stationarity_handles_empty_input() -> None:
    df = compute_stationarity(pd.DataFrame())
    assert df.empty
    assert "variant" in df.columns


def test_compute_stationarity_handles_too_few_obs() -> None:
    """Variants with < 30 observations should still emit a row, with NaN pvalues."""
    rows = []
    for i in range(10):
        rows.append({"date": pd.Timestamp(f"2020-{(i%12)+1:02d}-28"), "variant": "x", "frame": "long_run", "z_score": float(i)})
    df = compute_stationarity(pd.DataFrame(rows))
    assert len(df) == 1
    assert df.iloc[0]["n_obs"] == 10
    assert pd.isna(df.iloc[0]["adf_pvalue"])


def test_compute_correlation_matrix_returns_square_symmetric() -> None:
    zh = _synth_z_history()
    corr = compute_correlation_matrix(zh)
    assert corr.shape == (3, 3)
    assert (corr.index == corr.columns).all()
    # diagonal == 1
    for v in corr.index:
        assert corr.loc[v, v] == pytest.approx(1.0, abs=1e-9)


def test_compute_correlation_matrix_returns_empty_on_empty() -> None:
    corr = compute_correlation_matrix(pd.DataFrame())
    assert corr.empty


def test_compute_oos_r2_evolution_returns_one_row_per_test_period() -> None:
    scatter = _synth_scatter(n=200)
    df = compute_oos_r2_evolution(scatter, min_window=60)
    assert len(df) == 200 - 60
    assert "date" in df.columns
    assert "r2_oos" in df.columns
    assert "n_obs_in_window" in df.columns


def test_compute_oos_r2_evolution_empty_on_too_few_obs() -> None:
    scatter = _synth_scatter(n=30)
    df = compute_oos_r2_evolution(scatter, min_window=60)
    assert df.empty


def test_emit_diagnostics_writes_three_files(tmp_path: Path) -> None:
    charts_dir = tmp_path / "charts"
    # Write input parquets first
    zh = _synth_z_history()
    sc = _synth_scatter(n=200)
    charts_dir.mkdir()
    zh.to_parquet(charts_dir / "z_history.parquet")
    sc.to_parquet(charts_dir / "scatter_data.parquet")

    paths = emit_diagnostics(charts_dir)
    assert set(paths.keys()) == {"stationarity", "correlation", "oos_r2_evolution"}
    for path in paths.values():
        assert path.exists()
        assert path.stat().st_size > 0


def test_emit_diagnostics_works_without_input_parquets(tmp_path: Path) -> None:
    charts_dir = tmp_path / "empty"
    paths = emit_diagnostics(charts_dir)
    # All paths should still be written (some may be empty placeholders)
    for path in paths.values():
        assert path.exists()


def test_emit_diagnostics_accepts_in_memory_dataframes(tmp_path: Path) -> None:
    zh = _synth_z_history()
    sc = _synth_scatter(n=200)
    paths = emit_diagnostics(tmp_path, z_history=zh, scatter_df=sc)
    stat_df = pd.read_parquet(paths["stationarity"])
    assert not stat_df.empty
    corr_df = pd.read_parquet(paths["correlation"])
    assert corr_df.shape == (3, 3)
    oos_df = pd.read_parquet(paths["oos_r2_evolution"])
    assert not oos_df.empty
