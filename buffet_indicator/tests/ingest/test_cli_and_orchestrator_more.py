"""Additional coverage for CLI and orchestrator helpers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


def test_cli_main_minimal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure src.cli.main can be invoked with --skip-* flags to exercise argparse."""
    from src import cli as cli_mod
    from src.ingest import orchestrator as orch

    # Stub run_ingestion to a no-op so the test is hermetic.
    calls: list[dict] = []

    def _fake_run(**kw):  # type: ignore[no-untyped-def]
        calls.append(kw)
        return {}

    monkeypatch.setattr(orch, "run_ingestion", _fake_run)
    # Also patch the import the CLI made.
    monkeypatch.setattr(cli_mod, "run_ingestion", _fake_run)

    argv_backup = sys.argv
    try:
        sys.argv = [
            "cli",
            "--skip-fred",
            "--skip-yahoo",
            "--skip-masters",
            "--config",
            str(tmp_path / "missing_config.yaml"),
        ]
        rc = cli_mod.main()
    finally:
        sys.argv = argv_backup
    assert rc == 0
    assert calls and calls[0]["skip_fred"] is True
    assert calls[0]["skip_yahoo"] is True
    assert calls[0]["skip_masters"] is True


def test_orchestrator_load_api_key_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Env var fallback path when no config.yaml is present in cwd."""
    from src.ingest import orchestrator as orch
    import os

    fake_key = "abcdef0123456789" * 2  # 32 chars
    monkeypatch.setenv("FRED_API_KEY", fake_key)
    cwd_backup = os.getcwd()
    try:
        os.chdir(tmp_path)  # tmp_path has no config.yaml
        key = orch._load_api_key(None)
        assert key == fake_key
    finally:
        os.chdir(cwd_backup)


def test_orchestrator_load_api_key_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from src.ingest import orchestrator as orch
    import os
    from src.ingest._base import IngestError

    monkeypatch.delenv("FRED_API_KEY", raising=False)
    cwd_backup = os.getcwd()
    try:
        os.chdir(tmp_path)  # no config.yaml here
        with pytest.raises(IngestError):
            orch._load_api_key(None)
    finally:
        os.chdir(cwd_backup)
