"""Tests for src.ingest.fred_alfred_loader (LC v1.0 sub-stage A2).

Coverage targets: ≥90% of src/ingest/fred_alfred_loader.py per spec §11.2.

Key invariants under test:

1. **Look-ahead safety**: a vintage snapshot dated T must not contain any
   ``realtime_start > T``. Sub-stage A2's whole purpose is to make
   `load_master(vintage=T)` return values as they were known on T.
2. **Vintage snapshot resolution**: `load_master(vintage=T)` selects the
   largest stored vintage ≤ T (not exact match, not future vintage).
3. **Spec-mandated targets**: the 5 series listed in spec §1.2 are present
   in LC_V1_ALFRED_TARGETS exactly.

References
----------
- spec_v11_3__liquidity_composite.md §1.2 (ALFRED requirements)
- master spec §2.4.7 (vintage storage convention)
- specs/RECON_lc_v1_2026-05-22.md §9 open questions 1 & 2
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from src.ingest import fred_alfred_loader as fal
from src.ingest import master_archive as ma
from src.ingest._base import DataValidationError


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_master_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    master = tmp_path / "data" / "master"
    master.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ma, "MASTER_DIR", master)
    monkeypatch.setattr(ma, "CATALOG", master / "_catalog.json")
    monkeypatch.setattr(fal, "MASTER_DIR", master)
    return master


class _FakeFredClient:
    """Stand-in for fredapi.Fred — just returns whatever long_frame was injected."""
    def __init__(self, long_frame: pd.DataFrame) -> None:
        self._lf = long_frame

    def get_series_all_releases(self, series_id: str) -> pd.DataFrame:
        return self._lf.copy()


def _mk_alfred_long(
    series_id: str = "M2SL",
    obs_dates: list[str] | None = None,
    revisions: list[tuple[str, dict[str, float]]] | None = None,
) -> pd.DataFrame:
    """Build a synthetic ALFRED long-format DataFrame.

    Each (vintage, {obs_date: value}) pair adds rows. Later vintages override
    earlier ones for the same obs_date — mimics real revisions.
    """
    obs_dates = obs_dates or ["2024-01-31", "2024-02-29", "2024-03-31"]
    revisions = revisions or [
        ("2024-02-15", {"2024-01-31": 100.0}),
        ("2024-03-15", {"2024-01-31": 101.0, "2024-02-29": 110.0}),
        ("2024-04-15", {"2024-01-31": 102.0, "2024-02-29": 111.0, "2024-03-31": 120.0}),
    ]
    rows = []
    for vintage, vals in revisions:
        for d, v in vals.items():
            rows.append({"date": d, "realtime_start": vintage, "value": v})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# C1-Cn — Catalog of spec-mandated targets
# ---------------------------------------------------------------------------


def test_C1_alfred_targets_has_exactly_5_series() -> None:
    """Spec §1.2 mandates ALFRED for 5 revisable series."""
    assert len(fal.LC_V1_ALFRED_TARGETS) == 5


def test_C2_alfred_targets_match_spec() -> None:
    """LC_V1_ALFRED_TARGETS lc_ids must match spec §1.2 exactly."""
    expected = {"m2_sl", "busloans", "totll", "walcl", "wdtgal"}
    assert {t.lc_id for t in fal.LC_V1_ALFRED_TARGETS} == expected


def test_C3_alfred_targets_vintage_starts_match_spec() -> None:
    """Spec §1.2: M2/BUSLOANS/TOTLL backfill from 1980-01-01; WALCL/WDTGAL from 2002-12-18."""
    by_id = {t.lc_id: t for t in fal.LC_V1_ALFRED_TARGETS}
    assert by_id["m2_sl"].vintage_start == "1980-01-01"
    assert by_id["busloans"].vintage_start == "1980-01-01"
    assert by_id["totll"].vintage_start == "1980-01-01"
    assert by_id["walcl"].vintage_start == "2002-12-18"
    assert by_id["wdtgal"].vintage_start == "2002-12-18"


# ---------------------------------------------------------------------------
# F1-Fn — fetch_alfred_all_releases (via fake client)
# ---------------------------------------------------------------------------


def test_F1_fetch_alfred_happy_path() -> None:
    lf = _mk_alfred_long()
    result = fal.fetch_alfred_all_releases(
        "M2SL", "a" * 32, fred_client_factory=lambda: _FakeFredClient(lf),
    )
    assert len(result) == len(lf)
    assert set(result.columns) >= {"date", "realtime_start", "value"}
    # Sorted by (realtime_start, date)
    assert (
        result.sort_values(["realtime_start", "date"]).reset_index(drop=True)
        .equals(result)
    )


def test_F2_fetch_alfred_rejects_empty_response() -> None:
    empty = pd.DataFrame(columns=["date", "realtime_start", "value"])
    with pytest.raises(DataValidationError, match="no observations"):
        fal.fetch_alfred_all_releases(
            "BADID", "a" * 32, fred_client_factory=lambda: _FakeFredClient(empty),
        )


def test_F3_fetch_alfred_rejects_missing_columns() -> None:
    bad = pd.DataFrame({"date": ["2024-01-01"], "value": [100.0]})  # missing realtime_start
    with pytest.raises(DataValidationError, match="missing required columns"):
        fal.fetch_alfred_all_releases(
            "M2SL", "a" * 32, fred_client_factory=lambda: _FakeFredClient(bad),
        )


# ---------------------------------------------------------------------------
# S1-Sn — store_vintage_snapshots
# ---------------------------------------------------------------------------


def test_S1_store_vintage_snapshots_creates_per_vintage_files(tmp_path: Path) -> None:
    lf = _mk_alfred_long()
    vdir = tmp_path / "v"
    written = fal.store_vintage_snapshots(
        "m2_sl", "M2SL", lf, vintage_dir=vdir,
    )
    assert len(written) == 3  # one per unique vintage
    for v, p in written.items():
        assert p.exists()
        assert p.parent == vdir
        # Filename pattern: m2_sl__YYYYMMDD.parquet
        expected_stem = f"m2_sl__{v.strftime('%Y%m%d')}"
        assert p.stem == expected_stem


def test_S2_vintage_snapshot_excludes_future_realtimes(tmp_path: Path) -> None:
    """LOOK-AHEAD AUDIT: snapshot for vintage T must contain only
    realtime_start <= T data. This is the central look-ahead-safety invariant."""
    lf = _mk_alfred_long()
    vdir = tmp_path / "v"
    written = fal.store_vintage_snapshots(
        "m2_sl", "M2SL", lf, vintage_dir=vdir,
    )
    # Check the earliest vintage: 2024-02-15.
    v0 = pd.Timestamp("2024-02-15")
    snap = pd.read_parquet(written[v0])
    # On 2024-02-15, only the (2024-02-15, {2024-01-31: 100}) row existed.
    assert len(snap) == 1
    assert snap.index[0] == pd.Timestamp("2024-01-31")
    assert float(snap["value"].iloc[0]) == 100.0
    # Check 2024-03-15: 2 obs known.
    v1 = pd.Timestamp("2024-03-15")
    snap1 = pd.read_parquet(written[v1])
    assert len(snap1) == 2
    # 2024-01-31 should now be REVISED from 100.0 to 101.0 (latest revision per
    # store_vintage_snapshots: keep="last").
    assert float(snap1.loc[pd.Timestamp("2024-01-31"), "value"]) == 101.0


def test_S3_store_rejects_empty_long_frame(tmp_path: Path) -> None:
    empty = pd.DataFrame(columns=["date", "realtime_start", "value"])
    with pytest.raises(DataValidationError, match="empty"):
        fal.store_vintage_snapshots("m2_sl", "M2SL", empty, vintage_dir=tmp_path / "v")


def test_S4_store_respects_vintage_start(tmp_path: Path) -> None:
    """Vintages earlier than vintage_start are skipped (caller controls scope)."""
    lf = _mk_alfred_long()
    vdir = tmp_path / "v"
    written = fal.store_vintage_snapshots(
        "m2_sl", "M2SL", lf,
        vintage_start=pd.Timestamp("2024-03-15"),
        vintage_dir=vdir,
    )
    # 2 vintages remain (2024-03-15, 2024-04-15)
    assert len(written) == 2
    assert pd.Timestamp("2024-02-15") not in written


# ---------------------------------------------------------------------------
# L1-Ln — load_master_at_vintage
# ---------------------------------------------------------------------------


def test_L1_load_master_at_vintage_picks_largest_le(tmp_path: Path) -> None:
    lf = _mk_alfred_long()
    vdir = tmp_path / "v"
    fal.store_vintage_snapshots("m2_sl", "M2SL", lf, vintage_dir=vdir)
    # Ask for 2024-03-20: should resolve to 2024-03-15 snapshot.
    series = fal.load_master_at_vintage(
        "m2_sl", pd.Timestamp("2024-03-20"), vintage_dir=vdir,
    )
    # 2024-03-15 snapshot has 2 obs (2024-01-31 revised to 101, 2024-02-29 to 110)
    assert len(series) == 2
    assert float(series.loc[pd.Timestamp("2024-01-31")]) == 101.0


def test_L2_load_master_at_vintage_raises_when_too_early(tmp_path: Path) -> None:
    lf = _mk_alfred_long()
    vdir = tmp_path / "v"
    fal.store_vintage_snapshots("m2_sl", "M2SL", lf, vintage_dir=vdir)
    with pytest.raises(FileNotFoundError, match="No vintage snapshot"):
        fal.load_master_at_vintage(
            "m2_sl", pd.Timestamp("2023-01-01"), vintage_dir=vdir,
        )


def test_L3_load_master_at_vintage_raises_when_dir_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No vintage directory"):
        fal.load_master_at_vintage(
            "m2_sl", pd.Timestamp("2024-04-01"),
            vintage_dir=tmp_path / "nonexistent",
        )


# ---------------------------------------------------------------------------
# M1-Mn — load_master(vintage=) extension on master_archive
# ---------------------------------------------------------------------------


def test_M1_load_master_with_vintage_kwarg_routes_to_vintage(
    tmp_path: Path,
) -> None:
    """When ``vintage`` is passed, load_master should return data from the
    vintage snapshot, not the main parquet (which doesn't exist in this test)."""
    vdir = tmp_path / "data" / "master" / "_vintages"
    vdir.mkdir(parents=True, exist_ok=True)
    lf = _mk_alfred_long()
    fal.store_vintage_snapshots("m2_sl", "M2SL", lf, vintage_dir=vdir)

    result = ma.load_master(
        "m2_sl", vintage=pd.Timestamp("2024-04-30"),
    )
    # 2024-04-15 snapshot has 3 obs (all revised to 102/111/120)
    assert result.n_observations == 3
    assert result.sources_used[0].startswith("alfred_vintage:")


def test_M2_load_master_vintage_latest_uses_main_parquet(tmp_path: Path) -> None:
    """vintage='latest' (or None) should use the main parquet — existing behavior."""
    # Build a main parquet manually
    series_id = "wilshire_5000"  # existing series_id known to master_archive
    df = pd.DataFrame(
        {
            "value": [100.0, 101.0],
            "source": pd.array(["test"] * 2, dtype="string"),
            "vintage": pd.to_datetime(["2024-01-01"] * 2),
            "transform": pd.array(["none"] * 2, dtype="string"),
        },
        index=pd.DatetimeIndex(["2024-01-01", "2024-01-02"], name="date"),
    )
    path = ma._master_path(series_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    result = ma.load_master(series_id, vintage="latest")
    assert result.n_observations == 2
    assert result.sources_used == ("test",)


def test_M3_load_master_vintage_respects_start_end_filters(tmp_path: Path) -> None:
    vdir = tmp_path / "data" / "master" / "_vintages"
    vdir.mkdir(parents=True, exist_ok=True)
    lf = _mk_alfred_long()
    fal.store_vintage_snapshots("m2_sl", "M2SL", lf, vintage_dir=vdir)
    result = ma.load_master(
        "m2_sl",
        vintage=pd.Timestamp("2024-04-30"),
        start="2024-02-01",
        end="2024-02-29",
    )
    assert result.n_observations == 1
    assert result.earliest == pd.Timestamp("2024-02-29")


# ---------------------------------------------------------------------------
# O1 — Orchestrator
# ---------------------------------------------------------------------------


def test_O1_build_lc_alfred_vintages_processes_all_targets(tmp_path: Path) -> None:
    """Orchestrator iterates over the 5 targets and writes vintage parquets."""
    # Build a fake long-frame that works for ANY series_id
    def factory() -> _FakeFredClient:
        return _FakeFredClient(_mk_alfred_long())
    out = fal.build_lc_alfred_vintages(
        "a" * 32,
        fred_client_factory=factory,
        vintage_dir=tmp_path / "v",
    )
    assert set(out.keys()) == {"m2_sl", "busloans", "totll", "walcl", "wdtgal"}
    # Each target should have written 3 vintage snapshots (the fake has 3 vintages)
    for lc_id in out:
        # The first vintage in mock is 2024-02-15, but WALCL/WDTGAL vintage_start=2002-12-18
        # → all 3 vintages should be kept since they're all > 2002-12-18.
        # m2_sl/busloans/totll vintage_start=1980-01-01 → same outcome.
        assert len(out[lc_id]) == 3, f"{lc_id} wrote {len(out[lc_id])} snapshots"


# ---------------------------------------------------------------------------
# I1 — Integration (gated)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_I1_real_alfred_m2_one_recent_vintage() -> None:
    """Smoke test against real FRED ALFRED. Requires INTEGRATION_TESTS=1 + FRED_API_KEY.

    Slow: pulls full M2SL vintage history (~40 years × monthly revisions)."""
    if os.environ.get("INTEGRATION_TESTS") != "1":
        pytest.skip("set INTEGRATION_TESTS=1 to run")
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        pytest.skip("FRED_API_KEY not set")
    long_frame = fal.fetch_alfred_all_releases("M2SL", api_key)
    assert len(long_frame) > 1000
    # At least one revision after the 2020 redefinition.
    assert (long_frame["realtime_start"] > pd.Timestamp("2020-05-01")).any()
