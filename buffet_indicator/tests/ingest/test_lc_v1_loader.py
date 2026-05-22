"""Tests for src.ingest.lc_v1_loader (LC v1.0 sub-stage A1).

Coverage targets: ≥90% of src/ingest/lc_v1_loader.py per spec §11.2 (the same
floor used for the LC modeling module; applied here so A1 ships with the same
quality bar).

Test layout:
- C* tests cover the catalog (frozen-spec invariants).
- F* tests cover the FRED builder via responses-mocked HTTP.
- S* tests cover the LEGACY Stooq path (``build_lc_icedxy_stooq_master_legacy``)
  — retained for audit replay per Session 6 §2.0 blocker resolution.
- O* tests cover the orchestrator.
- I* tests are integration tests gated by INTEGRATION_TESTS=1.

New ICE DXY priority-chain tests live in ``tests/ingest/test_lc_v1_loader_icedxy.py``.

References
----------
- spec_v11_3__liquidity_composite.md §1.1, §16 (sub-stage A1)
- specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md §1.1 (sealed catalog)
- specs/RECON_lc_v1_2026-05-22.md §12 (A1 plan)
- specs/BLOCKED_v11_3_A1_icedxy_stooq.md — Stooq deprecation context (Session 6 §2.0).
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest
import responses

from src.ingest import fred_loader as fl
from src.ingest import lc_v1_loader as lc
from src.ingest import master_archive as ma
from src.ingest._base import DataValidationError, NetworkError


VALID_KEY = "a" * 32


# ---------------------------------------------------------------------------
# Shared isolation fixture (mirror of test_master_archive._isolated_master_dir)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_master_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    master = tmp_path / "data" / "master"
    raw = tmp_path / "data" / "raw"
    master.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ma, "MASTER_DIR", master)
    monkeypatch.setattr(ma, "CATALOG", master / "_catalog.json")
    monkeypatch.setattr(ma, "SCALING_ANCHORS", master / "_scaling_anchors.json")
    return master


def _mk_obs_for_frequency(
    frequency: str,
    start: str = "2024-01-03",
    n: int = 15,
) -> list[tuple[str, float]]:
    """Generate ``n`` realistic observations whose dates do not collapse under
    FRED's month-end normalisation. Choose step by frequency.

    - D, W → ~1 day step (FRED leaves daily/weekly alone after normalize).
    - M, Q, A → spacing wide enough that each lands in a distinct period.
    """
    step_days = {"D": 1, "W": 7, "M": 32, "Q": 95, "A": 370}.get(frequency, 1)
    idx = pd.date_range(start, periods=n, freq=f"{step_days}D")
    return [(str(d.date()), 100.0 + i) for i, d in enumerate(idx)]


def _register_fred_pair(
    api_key: str,
    fred_id: str,
    frequency: str,
    obs_start: str,
    obs: list[tuple[str, float]],
) -> None:
    """Register meta + observations responses for one FRED series."""
    responses.add(
        responses.GET,
        fl.FRED_META_URL,
        match=[
            responses.matchers.query_param_matcher(
                {"series_id": fred_id, "api_key": api_key, "file_type": "json"}
            )
        ],
        json={
            "seriess": [
                {
                    "id": fred_id,
                    "frequency_short": frequency,
                    "units_short": "x",
                    "last_updated": "2026-05-01 08:00:00-05",
                }
            ]
        },
        status=200,
    )
    responses.add(
        responses.GET,
        fl.FRED_OBS_URL,
        match=[
            responses.matchers.query_param_matcher(
                {
                    "series_id": fred_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "observation_start": obs_start,
                }
            )
        ],
        json={"observations": [{"date": d, "value": str(v)} for d, v in obs]},
        status=200,
    )


# ---------------------------------------------------------------------------
# C1 — Catalog completeness (sealed per pre-reg a8635ef)
# ---------------------------------------------------------------------------


def test_C1_fred_catalog_has_exactly_11_series() -> None:
    """Pre-reg a8635ef §1.1 + spec §1.1 list 11 FRED series for LC v1.0."""
    assert len(lc.LC_V1_FRED_CATALOG) == 11


def test_C2_fred_catalog_contains_expected_lc_ids() -> None:
    """Spec §1.1: exact lc_id set is frozen."""
    expected = {
        "walcl", "wdtgal", "rrpontsyd",
        "m2_sl",
        "busloans", "totll",
        "dtwexbgs",
        "tedrate", "sofr", "ioer", "iorb",
    }
    assert set(lc.LC_V1_FRED_CATALOG.keys()) == expected


def test_C3_fred_catalog_fred_ids_match_spec() -> None:
    """Each lc_id maps to the FRED series id stated in spec §1.1."""
    expected_fred_ids = {
        "walcl": "WALCL",
        "wdtgal": "WDTGAL",
        "rrpontsyd": "RRPONTSYD",
        "m2_sl": "M2SL",
        "busloans": "BUSLOANS",
        "totll": "TOTLL",
        "dtwexbgs": "DTWEXBGS",
        "tedrate": "TEDRATE",
        "sofr": "SOFR",
        "ioer": "IOER",
        "iorb": "IORB",
    }
    for lc_id, fred_id in expected_fred_ids.items():
        assert lc.LC_V1_FRED_CATALOG[lc_id].fred_id == fred_id


def test_C4_discontinued_series_have_dates() -> None:
    """Spec §1.1: TEDRATE (2022-01-31) and IOER (2021-07-28) are discontinued."""
    assert lc.LC_V1_FRED_CATALOG["tedrate"].discontinued_at == "2022-01-31"
    assert lc.LC_V1_FRED_CATALOG["ioer"].discontinued_at == "2021-07-28"
    # Active series should not be marked discontinued
    for active in ("walcl", "wdtgal", "rrpontsyd", "m2_sl", "busloans",
                   "totll", "dtwexbgs", "sofr", "iorb"):
        assert lc.LC_V1_FRED_CATALOG[active].discontinued_at is None


def test_C5_icedxy_spec_pinned_to_stooq_dx_f() -> None:
    """Spec §1.1 row s4b: ICE DXY via Stooq symbol 'dx.f' from 1971-01-04."""
    assert lc.LC_V1_ICEDXY_SPEC.stooq_symbol == "dx.f"
    assert lc.LC_V1_ICEDXY_SPEC.earliest_expected == "1971-01-04"


# ---------------------------------------------------------------------------
# F1-Fn — FRED builder (mocked HTTP via `responses`)
# ---------------------------------------------------------------------------


@responses.activate
def test_F1_build_fred_master_happy_path(tmp_path: Path) -> None:
    """Happy path: build WALCL master from a synthetic FRED response."""
    obs = _mk_obs_for_frequency("W", start="2024-01-03", n=15)
    _register_fred_pair(VALID_KEY, "WALCL", "W", "2002-12-18", obs)

    result = lc.build_lc_fred_master(
        "walcl",
        VALID_KEY,
        cache_dir=tmp_path / "cache",
    )

    assert result.series_id == "walcl"
    assert result.n_observations == 15
    assert result.sources_used == ("fred:WALCL",)
    # Check the persisted parquet has the master schema
    df = pd.read_parquet(ma._master_path("walcl"))
    assert set(df.columns) == {"value", "source", "vintage", "transform"}
    assert df["source"].iloc[0] == "fred:WALCL"
    assert df["transform"].iloc[0] == "none"


def test_F2_unknown_lc_id_raises_keyerror() -> None:
    with pytest.raises(KeyError, match="Unknown LC v1 series id"):
        lc.build_lc_fred_master("not_a_real_id", VALID_KEY)


@responses.activate
def test_F3_empty_fred_response_raises(tmp_path: Path) -> None:
    """Spec §1.1: every series must return at least 1 observation; empty → reject."""
    _register_fred_pair(VALID_KEY, "SOFR", "D", "2018-04-03", [])
    # FRED's own validator rejects <10 obs first; we expect either error type.
    with pytest.raises((DataValidationError, Exception)):
        lc.build_lc_fred_master("sofr", VALID_KEY, cache_dir=tmp_path / "cache")


@responses.activate
def test_F4_first_obs_warning_outside_30d_window(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    """If FRED first obs is >30d from spec.earliest_expected, log a warning."""
    # Register obs starting 2 years AFTER expected (DTWEXBGS expected 2006-01-04)
    obs = _mk_obs_for_frequency("D", start="2008-01-02", n=15)
    _register_fred_pair(VALID_KEY, "DTWEXBGS", "D", "2006-01-04", obs)
    with caplog.at_level("WARNING"):
        lc.build_lc_fred_master("dtwexbgs", VALID_KEY, cache_dir=tmp_path / "cache")
    assert any("later than expected" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# S1-Sn — Stooq ICE DXY builder (offline parse + error paths)
# ---------------------------------------------------------------------------


def _mk_stooq_csv(start: str = "1971-01-04", n: int = 12) -> bytes:
    idx = pd.bdate_range(start, periods=n)
    rows = ["Date,Open,High,Low,Close,Volume"]
    for i, d in enumerate(idx):
        c = 100.0 + i * 0.1
        rows.append(f"{d.date()},{c},{c},{c},{c},0")
    return ("\n".join(rows) + "\n").encode("utf-8")


def test_S1_parse_stooq_csv_happy_path() -> None:
    body = _mk_stooq_csv(n=5)
    series = lc._parse_stooq_csv(body)
    assert len(series) == 5
    assert series.name == "ice_dxy"
    assert series.index[0] == pd.Timestamp("1971-01-04")


def test_S2_parse_stooq_csv_rejects_missing_columns() -> None:
    body = b"WrongCol,Foo\n2024-01-01,1.0\n"
    with pytest.raises(DataValidationError, match="missing required columns"):
        lc._parse_stooq_csv(body)


def test_S3_build_icedxy_with_injected_body() -> None:
    """Session 6 §2.0: build_lc_icedxy_master is now model-construction; the
    Stooq master-write path is retained under build_lc_icedxy_stooq_master_legacy."""
    body = _mk_stooq_csv(n=20)
    with pytest.warns(DeprecationWarning):
        result = lc.build_lc_icedxy_stooq_master_legacy(stooq_body=body)
    assert result.series_id == "ice_dxy"
    assert result.n_observations == 20
    assert result.sources_used == ("stooq:dx.f",)


def test_S4_build_icedxy_rejects_empty_parse() -> None:
    """Empty parse → DataValidationError (legacy Stooq path)."""
    body = b"Date,Open,High,Low,Close,Volume\n"
    with pytest.warns(DeprecationWarning):
        with pytest.raises(DataValidationError):
            lc.build_lc_icedxy_stooq_master_legacy(stooq_body=body)


def test_S5_fetch_stooq_csv_rejects_no_data_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If Stooq says 'No data' for a symbol, our fetcher raises."""
    class _FakeResp:
        status_code = 200
        content = b"No data found for the requested symbol"
    monkeypatch.setattr(
        "src.ingest.lc_v1_loader.requests.get",
        lambda *a, **kw: _FakeResp(),
    )
    with pytest.raises(DataValidationError, match="returned no data"):
        lc._fetch_stooq_csv("nonexistent")


def test_S6_fetch_stooq_csv_propagates_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeResp:
        status_code = 503
        content = b"Service Unavailable"
    monkeypatch.setattr(
        "src.ingest.lc_v1_loader.requests.get",
        lambda *a, **kw: _FakeResp(),
    )
    with pytest.raises((NetworkError, Exception)):
        lc._fetch_stooq_csv("dx.f")


# ---------------------------------------------------------------------------
# O1-On — Orchestrator
# ---------------------------------------------------------------------------


@responses.activate
def test_O1_build_all_lc_v1_masters_fred_subset(tmp_path: Path) -> None:
    """Orchestrator builds all 11 FRED masters when skip_icedxy=True."""
    for lc_id, spec in lc.LC_V1_FRED_CATALOG.items():
        _register_fred_pair(
            VALID_KEY,
            spec.fred_id,
            spec.frequency,
            spec.earliest_expected,
            _mk_obs_for_frequency(spec.frequency, n=15),
        )
    out = lc.build_all_lc_v1_masters(
        VALID_KEY,
        cache_dir=tmp_path / "cache",
        skip_icedxy=True,
    )
    assert set(out.keys()) == set(lc.LC_V1_FRED_CATALOG.keys())
    for lc_id in lc.LC_V1_FRED_CATALOG:
        assert ma._master_path(lc_id).exists()


@responses.activate
def test_O2_orchestrator_includes_icedxy_when_body_injected(tmp_path: Path) -> None:
    """Session 6 §2.0: orchestrator only builds ICE DXY via the legacy Stooq
    path when ``use_stooq_legacy=True`` is explicitly opted in (audit replay)."""
    for lc_id, spec in lc.LC_V1_FRED_CATALOG.items():
        _register_fred_pair(
            VALID_KEY,
            spec.fred_id,
            spec.frequency,
            spec.earliest_expected,
            _mk_obs_for_frequency(spec.frequency, n=15),
        )
    with pytest.warns(DeprecationWarning):
        out = lc.build_all_lc_v1_masters(
            VALID_KEY,
            cache_dir=tmp_path / "cache",
            skip_icedxy=False,
            use_stooq_legacy=True,
            stooq_body=_mk_stooq_csv(n=15),
        )
    assert "ice_dxy" in out
    assert out["ice_dxy"].n_observations == 15
    assert ma._master_path("ice_dxy").exists()


@responses.activate
def test_O3_orchestrator_skips_icedxy_by_default(tmp_path: Path) -> None:
    """Session 6 §2.0: default ``skip_icedxy=True`` — ICE DXY is now sourced
    via scripts/bootstrap_icedxy_from_norgate.py, not the orchestrator."""
    for lc_id, spec in lc.LC_V1_FRED_CATALOG.items():
        _register_fred_pair(
            VALID_KEY,
            spec.fred_id,
            spec.frequency,
            spec.earliest_expected,
            _mk_obs_for_frequency(spec.frequency, n=15),
        )
    out = lc.build_all_lc_v1_masters(VALID_KEY, cache_dir=tmp_path / "cache")
    assert "ice_dxy" not in out
    assert set(out.keys()) == set(lc.LC_V1_FRED_CATALOG.keys())


# ---------------------------------------------------------------------------
# Look-ahead audit (sub-stage A1 cannot leak future data — fetches are
# latest-vintage descriptive; the audit lives at the modeling layer in
# sub-stage B. Here we assert the obvious: catalogs do not silently mutate.)
# ---------------------------------------------------------------------------


def test_A1_audit_catalog_is_frozen_dataclass() -> None:
    """Catalog entries are frozen dataclasses → mutation raises FrozenInstanceError.
    Guards against accidental in-process drift of the sealed pre-reg."""
    from dataclasses import FrozenInstanceError
    spec = lc.LC_V1_FRED_CATALOG["walcl"]
    with pytest.raises(FrozenInstanceError):
        spec.fred_id = "TAMPERED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# I1-In — Integration tests (gated by INTEGRATION_TESTS=1)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_I1_real_fred_walcl_happy_path(tmp_path: Path) -> None:
    """Hit real FRED for WALCL. Requires INTEGRATION_TESTS=1 + FRED_API_KEY."""
    if os.environ.get("INTEGRATION_TESTS") != "1":
        pytest.skip("set INTEGRATION_TESTS=1 to run")
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        pytest.skip("FRED_API_KEY not set")
    result = lc.build_lc_fred_master(
        "walcl", api_key, cache_dir=tmp_path / "cache",
    )
    assert result.n_observations > 100
    assert result.earliest <= pd.Timestamp("2003-02-01")


@pytest.mark.integration
@pytest.mark.skip(
    reason="Session 6 §2.0: Stooq dx.f / ^dxy free endpoints empty since 2026-05-22; "
           "ICE DXY is now sourced via Norgate (bootstrap script) + yfinance fallback. "
           "Integration coverage of the new path lives in test_lc_v1_loader_icedxy.py::test_I3."
)
def test_I2_real_stooq_icedxy_happy_path() -> None:
    """DEPRECATED: Stooq integration test retained for audit only."""
    if os.environ.get("INTEGRATION_TESTS") != "1":
        pytest.skip("set INTEGRATION_TESTS=1 to run")
    with pytest.warns(DeprecationWarning):
        result = lc.build_lc_icedxy_stooq_master_legacy()
    assert result.n_observations > 1000
    assert result.earliest <= pd.Timestamp("1985-01-01")
