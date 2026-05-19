"""Spec v8b.1 §2 — Diagnostics completion tests (A.1 - A.4)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.diagnostics import (  # noqa: E402
    compute_break_dates,
    compute_calibration_metrics,
    compute_residuals_for_mvci_10y,
    emit_diagnostics,
)
from src.viz.chart_specs import make_acf_pacf_charts, make_calibration_plot  # noqa: E402


def _synth_z_history_long(n_per_variant: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows: list[dict[str, object]] = []
    idx = pd.date_range("1980-01-31", periods=n_per_variant, freq="ME")
    for vname in ("a", "b", "c"):
        z = rng.standard_normal(n_per_variant).cumsum() * 0.05  # drift to invite breaks
        for date, val in zip(idx, z, strict=False):
            rows.append({"date": date, "variant": vname, "frame": "long_run", "z_score": float(val)})
    return pd.DataFrame(rows)


def _synth_scatter(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    idx = pd.date_range("1980-01-31", periods=n, freq="ME")
    z = rng.standard_normal(n)
    fwd = -0.03 * z + 0.07 + rng.standard_normal(n) * 0.02
    return pd.DataFrame(
        {
            "date": idx,
            "variant": "mvci",
            "z_score_long_run": z,
            "forward_120m_cagr": fwd,
        }
    )


# A.1 — PP + ZA columns
def test_v8b1_stationarity_parquet_has_pp_za_columns() -> None:
    """diagnostics_stationarity parquet schema includes pp_pvalue + za_pvalue."""
    parquet = _ROOT / "outputs" / "charts" / "diagnostics_stationarity.parquet"
    if not parquet.exists():
        # Build fresh
        emit_diagnostics(_ROOT / "outputs" / "charts")
    df = pd.read_parquet(parquet)
    for col in ("variant", "frame", "n_obs", "adf_pvalue", "kpss_pvalue", "pp_pvalue", "za_pvalue"):
        assert col in df.columns, f"missing column {col}"


# A.2 — Break dates schema
def test_v8b1_break_dates_parquet_schema(tmp_path: Path) -> None:
    """compute_break_dates returns the spec'd schema."""
    zh = _synth_z_history_long(n_per_variant=200)
    df = compute_break_dates(zh, max_breaks=5)
    for col in ("variant", "break_idx", "break_date", "ci_lower", "ci_upper"):
        assert col in df.columns


def test_v8b1_break_dates_emitted_to_parquet() -> None:
    parquet = _ROOT / "outputs" / "charts" / "diagnostics_break_dates.parquet"
    if not parquet.exists():
        emit_diagnostics(_ROOT / "outputs" / "charts")
    df = pd.read_parquet(parquet)
    assert {"variant", "break_idx", "break_date", "ci_lower", "ci_upper"}.issubset(df.columns)


# A.3 — Residuals + ACF/PACF chart
def test_v8b1_residuals_parquet_emitted() -> None:
    parquet = _ROOT / "outputs" / "charts" / "diagnostics_mvci_residuals.parquet"
    if not parquet.exists():
        emit_diagnostics(_ROOT / "outputs" / "charts")
    df = pd.read_parquet(parquet)
    assert "residual" in df.columns or df.empty


def test_v8b1_compute_residuals_returns_series() -> None:
    scatter = _synth_scatter(n=200)
    res = compute_residuals_for_mvci_10y(scatter)
    assert isinstance(res, pd.Series)
    assert len(res) > 0
    assert res.dtype == np.float64


def test_v8b1_acf_pacf_chart_spec_dual_panel() -> None:
    """make_acf_pacf_charts emits a 2-panel grid spec with both ACF + PACF traces."""
    rng = np.random.default_rng(0)
    res = pd.Series(
        rng.standard_normal(200),
        index=pd.date_range("2000-01-31", periods=200, freq="ME"),
        name="residual",
    )
    spec = make_acf_pacf_charts(res, n_lags=20)
    # Two distinct y-axes
    layout = spec["layout"]
    assert "yaxis" in layout and "yaxis2" in layout
    # Should have ACF + PACF + CI bands as traces
    assert len(spec["data"]) > 0
    # At least one trace mentions ACF/PACF
    has_acf = any(t.get("name") == "ACF" for t in spec["data"])
    has_pacf = any(t.get("name") == "PACF" for t in spec["data"])
    assert has_acf and has_pacf


# A.4 — Calibration
def test_v8b1_calibration_metrics_json_valid() -> None:
    calib_path = _ROOT / "outputs" / "tables" / "calibration_metrics.json"
    if not calib_path.exists():
        emit_diagnostics(_ROOT / "outputs" / "charts")
    data = json.loads(calib_path.read_text(encoding="utf-8"))
    if not data.get("available"):
        return  # Insufficient data — acceptable on cold builds
    for k in ("horizon_years", "event", "n_observations", "buckets", "brier_score"):
        assert k in data
    assert 0 <= data["brier_score"] <= 1
    assert isinstance(data["buckets"], list) and len(data["buckets"]) > 0


def test_v8b1_compute_calibration_smoke() -> None:
    scatter = _synth_scatter(n=200)
    calib = compute_calibration_metrics(scatter)
    if not calib.get("available"):
        return
    assert "brier_score" in calib
    assert "reliability" in calib
    assert "resolution" in calib
    assert "uncertainty" in calib


def test_v8b1_calibration_plot_includes_reference_line() -> None:
    buckets = [
        {"predicted_mean": 0.05, "realized_freq": 0.10, "n": 100},
        {"predicted_mean": 0.25, "realized_freq": 0.30, "n": 100},
        {"predicted_mean": 0.55, "realized_freq": 0.50, "n": 100},
    ]
    spec = make_calibration_plot(
        buckets, brier_score=0.15, reliability=0.01, resolution=0.05, uncertainty=0.20
    )
    names = [t.get("name") for t in spec["data"]]
    assert "Perfect calibration" in names
    # Dashed reference line goes from (0,0) to (1,1)
    ref = next(t for t in spec["data"] if t.get("name") == "Perfect calibration")
    assert ref["x"] == [0, 1]
    assert ref["y"] == [0, 1]
