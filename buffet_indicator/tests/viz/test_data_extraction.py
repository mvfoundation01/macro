"""Unit tests for src.viz.data_extraction."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.viz.data_extraction import (
    assemble_dashboard_data,
    load_chart_parquets,
    load_headline,
    parquet_to_records,
)


def test_V8A5_parquet_to_records_roundtrip(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-31", periods=3, freq="ME"),
            "value": [1.0, 2.0, 3.0],
        }
    )
    records = parquet_to_records(df)
    assert len(records) == 3
    assert isinstance(records[0]["date"], str)
    assert records[0]["value"] == 1.0


def test_load_headline_reads_json(tmp_path: Path) -> None:
    payload = {"headline": {"asof": "2026-05-31", "variants": {}}}
    p = tmp_path / "headline.json"
    p.write_text(json.dumps(payload))
    h = load_headline(p)
    assert h["asof"] == "2026-05-31"


def test_assemble_dashboard_data_minimal() -> None:
    """Minimal headline + empty parquets should still produce a payload."""
    headline = {
        "asof": "2026-05-31",
        "view": "descriptive",
        "interpretation": {"narrative_code": "MIXED", "narrative": "x" * 200},
        "cross_variant_long_run": {"agreement": 0.7, "mean_z": 1.0},
        "cross_variant_current_regime": {"agreement": 0.2, "mean_z": 0.5},
        "variants": {
            "mvci": {
                "headline_value": 1.5,
                "headline_label": "MVCI",
                "headline_unit": "sigma",
                "long_run": {
                    "z_score": 1.5,
                    "empirical_percentile": 95.0,
                    "regime": "Overvalued",
                    "regime_color": "#E87722",
                    "confidence_pct": 60.0,
                    "schemes": {"pca_pc1": {"weights_current": {"a": 0.5, "b": 0.5}}},
                },
            }
        },
    }
    parquets: dict[str, pd.DataFrame] = {}
    out = assemble_dashboard_data(headline, parquets)
    assert out["asof"] == "2026-05-31"
    assert "variants" in out
    assert "mvci" in out["variants"]
    assert "regime_colors" in out
    assert "mvci_pca_loadings_chart" in out


def test_load_chart_parquets_missing_dir(tmp_path: Path) -> None:
    out = load_chart_parquets(tmp_path / "does_not_exist")
    assert out == {}
