"""Smoke tests for the orchestrator (offline)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ingest import orchestrator as orch
from src.ingest import master_archive as ma
from src.ingest import csv_loader as cl
from src.ingest.yahoo_loader import YahooSeries


def test_run_ingestion_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run orchestrator without network: skip FRED, mock Yahoo, point TV at synthetic files."""
    # Synthetic TradingView files in a tmp dir.
    raw = tmp_path / "raw"
    raw.mkdir()
    n = 200
    idx = pd.bdate_range("2024-01-02", periods=n)
    close = 4000.0 + np.arange(n, dtype="float64")
    df = pd.DataFrame({"time": idx.strftime("%Y-%m-%d"), "close": close})

    spx = raw / "spx.csv"
    df.to_csv(spx, index=False)

    monkeypatch.setitem(cl._TV_SPEC["spx"], "path", spx)
    monkeypatch.setitem(cl._TV_SPEC["spxtr"], "path", raw / "missing.csv")
    monkeypatch.setitem(cl._TV_SPEC["wilshire_tv"], "path", raw / "missing.csv")
    monkeypatch.setitem(cl._TV_SPEC["gdp_backup"], "path", raw / "missing.csv")

    # Stub Yahoo (won't be reached because wilshire_tv is missing -> masters skipped).
    def _fake_wilshire(**kw):  # type: ignore[no-untyped-def]
        yh_idx = pd.bdate_range("2024-01-02", periods=500)
        return YahooSeries(
            symbol="^W5000",
            canonical_name="^W5000",
            data=pd.DataFrame({"Close": np.arange(500, dtype="float64") + 40000.0}, index=yh_idx),
            frequency="D",
            retrieval_timestamp=pd.Timestamp("2026-05-15"),
            sha256="x" * 64,
            cache_path=Path("/nonexistent"),
        )

    monkeypatch.setattr(orch, "load_wilshire_yahoo", _fake_wilshire)
    # Stub shiller so we don't depend on the real file in unit tests.
    monkeypatch.setattr(
        orch,
        "load_shiller",
        lambda: None,  # the orchestrator handles None gracefully via try/except
    )

    # Redirect MANIFEST to tmp so we don't pollute the project root.
    fake_manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(orch, "MANIFEST", fake_manifest)

    result = orch.run_ingestion(skip_fred=True)
    assert "tradingview" in result
    assert "spx" in result["tradingview"]
    assert "yahoo_wilshire" in result
    # Master should be empty because wilshire_tv input was missing.
    assert result["masters"] == {}
    assert fake_manifest.exists()
