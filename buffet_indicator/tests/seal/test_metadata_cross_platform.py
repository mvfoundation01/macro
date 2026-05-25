"""§11.2 T21 — seal helpers do not require Unix-only tools.
DRAFT_v4 §9 item 11 (seal 2a94417).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.seal.metadata import collect_seal_metadata_with_python_helpers  # noqa: E402


def test_seal_helpers_do_not_require_unix_only_tools() -> None:
    """No jq / sha256sum dependency; Python helpers work cross-platform.

    NEW per Codex round-2 New-9. Cross-platform seal invariant.
    References: DRAFT_v4 §9 item 11 + sealed pre-reg §11.2 T21.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
