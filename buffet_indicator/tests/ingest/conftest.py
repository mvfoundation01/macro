"""Shared pytest fixtures for the ingest tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make ``src`` importable when pytest is run from the project root.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture()
def tmp_cache_dir(tmp_path: Path) -> Path:
    d = tmp_path / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture()
def integration_enabled() -> bool:
    return os.environ.get("INTEGRATION_TESTS") == "1"
