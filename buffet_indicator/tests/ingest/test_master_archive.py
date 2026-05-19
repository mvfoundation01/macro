"""Tests for src.ingest.master_archive."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ingest import master_archive as ma
from src.ingest._base import DataValidationError, IntegrityError, SourceMissingError
from src.ingest.yahoo_loader import YahooSeries


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_master_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect MASTER_DIR / CATALOG / SCALING_ANCHORS to a tmp_path per test."""
    master = tmp_path / "data" / "master"
    raw = tmp_path / "data" / "raw"
    master.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(ma, "MASTER_DIR", master)
    monkeypatch.setattr(ma, "CATALOG", master / "_catalog.json")
    monkeypatch.setattr(ma, "SCALING_ANCHORS", master / "_scaling_anchors.json")
    return master


def _mk_tv_csv(tmp_path: Path, *, start: str = "1970-12-31", end: str = "2023-05-30") -> Path:
    idx = pd.bdate_range(start=start, end=end)
    close = 830.0 + np.linspace(0, 41000.0, len(idx))
    df = pd.DataFrame({"time": idx.strftime("%Y-%m-%d"), "close": close})
    p = tmp_path / "wilshire.csv"
    df.to_csv(p, index=False)
    return p


def _mk_yh_df(start: str = "2022-01-03", end: str = "2026-05-15", scale: float = 1.5) -> pd.DataFrame:
    """Date-deterministic synthetic Yahoo data: value depends only on the date
    (not on the start/end window), so two runs over overlapping ranges produce
    identical closes for the same date."""
    idx = pd.bdate_range(start=start, end=end)
    # Linear ramp anchored to absolute ordinal days so the value at 2023-06-01
    # is identical regardless of `end`.
    ordinals = (idx - pd.Timestamp("2022-01-03")).days.astype("float64")
    base_close = 38000.0 + 12.0 * ordinals
    return pd.DataFrame(
        {
            "Open": base_close,
            "High": base_close,
            "Low": base_close,
            "Close": base_close * scale,
            "Volume": [0] * len(idx),
        },
        index=idx,
    )


def _mk_yh_series(start: str = "2022-01-03", end: str = "2026-05-15", scale: float = 1.5) -> YahooSeries:
    df = _mk_yh_df(start=start, end=end, scale=scale)
    return YahooSeries(
        symbol="^W5000",
        canonical_name="^W5000",
        data=df,
        frequency="D",
        retrieval_timestamp=pd.Timestamp("2026-05-15"),
        sha256="x" * 64,
        cache_path=Path("/nonexistent"),
    )


# ---------------------------------------------------------------------------
# M1 -- splice happy path
# ---------------------------------------------------------------------------


def test_M1_splice_happy_path() -> None:
    idx = pd.bdate_range("2022-01-01", periods=200)
    base = pd.Series(100.0 + np.arange(200, dtype="float64"), index=idx, name="base")
    ext = pd.Series(
        (100.0 + np.arange(200, dtype="float64")) * 1.5,
        index=idx,
        name="ext",
    )
    # Extend ext beyond base by 50 rows.
    ext_extra_idx = pd.bdate_range(idx[-1] + pd.Timedelta(days=1), periods=50)
    ext_extra = pd.Series(
        (300.0 + np.arange(50, dtype="float64")) * 1.5,
        index=ext_extra_idx,
    )
    ext_full = pd.concat([ext, ext_extra])
    spliced, meta = ma._splice_two_series(base, ext_full, "base", "ext")
    assert abs(meta["scale_factor_k"] - 1.5) < 1e-6
    assert len(spliced) == len(base) + len(ext_extra)
    # Scaled values match base at overlap endpoint.
    assert abs(spliced.loc[idx[-1]] - base.iloc[-1]) < 1e-6


# ---------------------------------------------------------------------------
# M2 -- insufficient overlap
# ---------------------------------------------------------------------------


def test_M2_insufficient_overlap() -> None:
    base_idx = pd.bdate_range("2022-01-01", periods=200)
    base = pd.Series(np.arange(200, dtype="float64") + 100.0, index=base_idx)
    # Only 30 overlapping days.
    ext_idx = base_idx[-30:].append(pd.bdate_range(base_idx[-1] + pd.Timedelta(days=1), periods=50))
    ext = pd.Series(np.arange(80, dtype="float64") + 200.0, index=ext_idx)
    with pytest.raises(DataValidationError):
        ma._splice_two_series(base, ext, "b", "e", overlap_min_days=60)


# ---------------------------------------------------------------------------
# M3 -- unstable ratio (regime break)
# ---------------------------------------------------------------------------


def test_M3_unstable_ratio() -> None:
    idx = pd.bdate_range("2022-01-01", periods=200)
    base = pd.Series(np.arange(200, dtype="float64") + 100.0, index=idx)
    # Half the overlap is scaled by 1.5, the other half by 3.0 -> unstable.
    ratios = np.array([1.5] * 100 + [3.0] * 100)
    ext = pd.Series((np.arange(200, dtype="float64") + 100.0) * ratios, index=idx)
    with pytest.raises(DataValidationError):
        ma._splice_two_series(base, ext, "b", "e")


# ---------------------------------------------------------------------------
# M4 -- scale factor on known fixture
# ---------------------------------------------------------------------------


def test_M4_scale_factor_known_value() -> None:
    idx = pd.bdate_range("2022-01-01", periods=150)
    base = pd.Series(np.linspace(100.0, 200.0, 150), index=idx)
    ext = base * 1.342500
    spliced, meta = ma._splice_two_series(base, ext, "b", "e")
    assert abs(meta["scale_factor_k"] - 1.3425) < 1e-6


# ---------------------------------------------------------------------------
# M5 -- build_wilshire_master first run
# ---------------------------------------------------------------------------


def test_M5_build_first_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tv_path = _mk_tv_csv(tmp_path)
    yh = _mk_yh_series()
    ms = ma.build_wilshire_master(tv_path=tv_path, yahoo_loader=lambda: yh)
    assert ms.series_id == "wilshire_5000"
    assert ms.earliest <= pd.Timestamp("1971-01-04")
    assert ms.latest >= pd.Timestamp("2026-05-01")
    assert (ma.MASTER_DIR / "wilshire_5000.parquet").exists()
    assert ma.CATALOG.exists()
    assert ma.SCALING_ANCHORS.exists()
    catalog = json.loads(ma.CATALOG.read_text())
    assert "wilshire_5000" in catalog


# ---------------------------------------------------------------------------
# M6 -- second build is idempotent (length non-decreasing)
# ---------------------------------------------------------------------------


def test_M6_second_run_idempotent(tmp_path: Path) -> None:
    tv_path = _mk_tv_csv(tmp_path)
    yh = _mk_yh_series()
    ms1 = ma.build_wilshire_master(tv_path=tv_path, yahoo_loader=lambda: yh)
    ms2 = ma.build_wilshire_master(tv_path=tv_path, yahoo_loader=lambda: yh)
    assert ms2.n_observations == ms1.n_observations
    assert ms2.earliest == ms1.earliest


# ---------------------------------------------------------------------------
# M7 -- tail-only update appends new dates
# ---------------------------------------------------------------------------


def test_M7_tail_only_update(tmp_path: Path) -> None:
    tv_path = _mk_tv_csv(tmp_path)
    yh1 = _mk_yh_series(end="2026-05-10")
    yh2 = _mk_yh_series(end="2026-05-20")
    ms1 = ma.build_wilshire_master(tv_path=tv_path, yahoo_loader=lambda: yh1)
    n1 = ms1.n_observations
    ms2 = ma.build_wilshire_master(tv_path=tv_path, yahoo_loader=lambda: yh2)
    assert ms2.n_observations > n1
    assert ms2.latest > ms1.latest


# ---------------------------------------------------------------------------
# M8 -- _update_master_atomically refuses to shrink
# ---------------------------------------------------------------------------


def test_M8_refuses_shrink_overwrite(tmp_path: Path) -> None:
    # Seed an existing master via _update_master_atomically.
    idx = pd.bdate_range("2024-01-01", periods=10)
    base_df = pd.DataFrame(
        {
            "value": np.arange(10, dtype="float64") + 100.0,
            "source": pd.Series(["x"] * 10, dtype="string"),
            "vintage": pd.to_datetime([pd.Timestamp("2024-01-01")] * 10),
            "transform": pd.Series(["none"] * 10, dtype="string"),
        },
        index=idx,
    )
    base_df.index.name = "date"
    ma._update_master_atomically("test_series", base_df)

    # Try to "shrink" by submitting a candidate that conflicts with same vintage.
    conflict = base_df.copy()
    conflict["value"] = conflict["value"] + 50.0  # different values, same vintages
    with pytest.raises(IntegrityError):
        ma._update_master_atomically("test_series", conflict)


# ---------------------------------------------------------------------------
# M9 -- load_master returns MasterSeries with expected metadata
# ---------------------------------------------------------------------------


def test_M9_load_master_basic(tmp_path: Path) -> None:
    tv_path = _mk_tv_csv(tmp_path)
    yh = _mk_yh_series()
    ma.build_wilshire_master(tv_path=tv_path, yahoo_loader=lambda: yh)
    out = ma.load_master("wilshire_5000")
    assert isinstance(out, ma.MasterSeries)
    assert out.earliest <= pd.Timestamp("1971-01-04")
    assert out.n_observations > 1000


# ---------------------------------------------------------------------------
# M10 -- load_master start/end window clipping
# ---------------------------------------------------------------------------


def test_M10_load_master_window(tmp_path: Path) -> None:
    tv_path = _mk_tv_csv(tmp_path)
    yh = _mk_yh_series()
    ma.build_wilshire_master(tv_path=tv_path, yahoo_loader=lambda: yh)
    clipped = ma.load_master("wilshire_5000", start="2020-01-01", end="2024-12-31")
    assert clipped.earliest >= pd.Timestamp("2020-01-01")
    assert clipped.latest <= pd.Timestamp("2024-12-31")
    assert clipped.n_observations > 0


# ---------------------------------------------------------------------------
# Edge: missing series file -> SourceMissingError
# ---------------------------------------------------------------------------


def test_load_master_missing_raises() -> None:
    with pytest.raises(SourceMissingError):
        ma.load_master("does_not_exist")
