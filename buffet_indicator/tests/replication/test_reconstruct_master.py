"""Phase F-REPRO.B — reconstruction script tests.

All tests mock the FRED loader; no real network calls. Verifies:
- Missing manifest → exit code 3
- Malformed manifest JSON → exit code 3
- Missing FRED_API_KEY (and FRED series present) → exit code 2
- Successful retrieval + SHA match
- SHA mismatch recorded (NOT treated as failure)
- Per-series load_fred_series exception → recorded in failed list
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.replication.reconstruct_master import (  # noqa: E402
    FRED_SOURCE_KEYS,
    ReconstructionReport,
    reconstruct_master,
)


def _write_manifest(path: Path, series: dict) -> None:
    body = json.dumps({"_meta": {"manifest_version": "test"}, "series": series}, indent=2)
    path.write_text(body, encoding="utf-8")


def _write_sample_parquet(path: Path, content: bytes = b"sample_parquet_bytes") -> str:
    """Write arbitrary bytes (we don't need a real parquet here — only its SHA)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def test_reconstruct_missing_manifest_exits_3(tmp_path: Path) -> None:
    out = tmp_path / "out"
    report = reconstruct_master(
        manifest_path=tmp_path / "missing.json",
        output_dir=out,
        verify_sha=True,
        fred_api_key="x" * 32,
        fred_loader=MagicMock(),
    )
    assert report.exit_code == 3


def test_reconstruct_malformed_manifest_exits_3(tmp_path: Path) -> None:
    manifest = tmp_path / "bad.json"
    manifest.write_text("not json {{{", encoding="utf-8")
    report = reconstruct_master(
        manifest_path=manifest,
        output_dir=tmp_path / "out",
        verify_sha=True,
        fred_api_key="x" * 32,
        fred_loader=MagicMock(),
    )
    assert report.exit_code == 3


def test_reconstruct_missing_credentials_exits_2(tmp_path: Path) -> None:
    """If FRED_API_KEY absent and FRED series in manifest, mark missing_credentials."""
    series = {k: {"sha256": "x" * 64} for k in FRED_SOURCE_KEYS}
    manifest = tmp_path / "data_manifest.json"
    _write_manifest(manifest, series)
    report = reconstruct_master(
        manifest_path=manifest,
        output_dir=tmp_path / "out",
        verify_sha=True,
        fred_api_key="",
        fred_loader=MagicMock(),
    )
    assert report.exit_code == 2
    assert set(report.missing_credentials) == set(FRED_SOURCE_KEYS)
    assert report.succeeded == []


def test_reconstruct_successful_with_sha_match(tmp_path: Path) -> None:
    """When loader returns a parquet whose SHA matches the manifest, record sha_matches."""
    series = {}
    out_dir = tmp_path / "out"
    expected_shas: dict[str, str] = {}
    for key, meta in FRED_SOURCE_KEYS.items():
        cache_path = out_dir / f"{meta['fred_id']}.parquet"
        sha = _write_sample_parquet(cache_path, content=meta["fred_id"].encode())
        expected_shas[key] = sha
        series[key] = {"sha256": sha}
    manifest = tmp_path / "data_manifest.json"
    _write_manifest(manifest, series)

    def fake_load(*, series_id, frequency, api_key, cache_dir):
        return SimpleNamespace(parquet_path=str(out_dir / f"{series_id}.parquet"))

    loader = SimpleNamespace(load_fred_series=fake_load)
    report = reconstruct_master(
        manifest_path=manifest,
        output_dir=out_dir,
        verify_sha=True,
        fred_api_key="a" * 32,
        fred_loader=loader,
    )
    assert report.exit_code == 0
    assert set(report.succeeded) == set(FRED_SOURCE_KEYS)
    assert set(report.sha_matches) == set(FRED_SOURCE_KEYS)
    assert report.sha_mismatches == []


def test_reconstruct_sha_mismatch_recorded_not_failure(tmp_path: Path) -> None:
    """Post-FRED-revision SHA mismatch must be RECORDED in sha_mismatches but
    NOT counted as a failure (exit code 0)."""
    series = {}
    out_dir = tmp_path / "out"
    for key, meta in FRED_SOURCE_KEYS.items():
        cache_path = out_dir / f"{meta['fred_id']}.parquet"
        _write_sample_parquet(cache_path, content=b"reconstructed_post_revision")
        series[key] = {"sha256": "0" * 64}  # manifest expects different SHA
    manifest = tmp_path / "data_manifest.json"
    _write_manifest(manifest, series)

    def fake_load(*, series_id, frequency, api_key, cache_dir):
        return SimpleNamespace(parquet_path=str(out_dir / f"{series_id}.parquet"))

    loader = SimpleNamespace(load_fred_series=fake_load)
    report = reconstruct_master(
        manifest_path=manifest,
        output_dir=out_dir,
        verify_sha=True,
        fred_api_key="a" * 32,
        fred_loader=loader,
    )
    assert report.exit_code == 0
    assert set(report.succeeded) == set(FRED_SOURCE_KEYS)
    assert set(m["key"] for m in report.sha_mismatches) == set(FRED_SOURCE_KEYS)
    assert report.sha_matches == []
    for mismatch in report.sha_mismatches:
        assert "FRED may have revised" in mismatch["note"]


def test_reconstruct_loader_exception_recorded_in_failed(tmp_path: Path) -> None:
    series = {k: {"sha256": "x" * 64} for k in FRED_SOURCE_KEYS}
    manifest = tmp_path / "data_manifest.json"
    _write_manifest(manifest, series)

    def fake_load(**kwargs):
        raise RuntimeError("synthetic_fred_api_error")

    loader = SimpleNamespace(load_fred_series=fake_load)
    report = reconstruct_master(
        manifest_path=manifest,
        output_dir=tmp_path / "out",
        verify_sha=True,
        fred_api_key="a" * 32,
        fred_loader=loader,
    )
    assert report.exit_code == 1
    assert len(report.failed) == len(FRED_SOURCE_KEYS)
    for f in report.failed:
        assert "synthetic_fred_api_error" in f["reason"]


def test_reconstruct_skips_non_fred_series(tmp_path: Path) -> None:
    """Non-FRED entries (TradingView, Shiller, Yahoo) listed as skipped_non_fred."""
    series = {
        "master.walcl": {"sha256": "x" * 64},
        "forward_returns.spxtr_daily": {"sha256": "y" * 64},
        "shiller.ie_data": {"sha256": "z" * 64},
        "tradingview.spx": {"sha256": "w" * 64},
        "yahoo.wilshire": {"sha256": "v" * 64},
        "master.wilshire_5000": {"sha256": "u" * 64},
    }
    manifest = tmp_path / "data_manifest.json"
    _write_manifest(manifest, series)

    out_dir = tmp_path / "out"
    _write_sample_parquet(out_dir / "WALCL.parquet", content=b"walcl_data")

    def fake_load(*, series_id, frequency, api_key, cache_dir):
        return SimpleNamespace(parquet_path=str(out_dir / f"{series_id}.parquet"))

    loader = SimpleNamespace(load_fred_series=fake_load)
    report = reconstruct_master(
        manifest_path=manifest,
        output_dir=out_dir,
        verify_sha=False,
        fred_api_key="a" * 32,
        fred_loader=loader,
    )
    # WALCL succeeded; non-FRED entries skipped.
    assert "master.walcl" in report.succeeded
    assert "forward_returns.spxtr_daily" in report.skipped_non_fred
    assert "shiller.ie_data" in report.skipped_non_fred
    assert "tradingview.spx" in report.skipped_non_fred
    assert "yahoo.wilshire" in report.skipped_non_fred
    assert "master.wilshire_5000" in report.skipped_non_fred


def test_report_to_json_has_summary_fields(tmp_path: Path) -> None:
    report = ReconstructionReport(manifest_path="m", output_dir="o", verify_sha=True)
    report.succeeded = ["a", "b"]
    report.failed = [{"key": "c", "reason": "x"}]
    j = report.to_json()
    assert j["summary"]["n_succeeded"] == 2
    assert j["summary"]["n_failed"] == 1
    assert j["summary"]["exit_code"] == 0  # default; only set in reconstruct_master
