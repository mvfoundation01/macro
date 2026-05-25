"""§11.2 T21 — seal helpers do not require Unix-only tools.
DRAFT_v4 §9 item 11 (seal 2a94417).
"""
from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.seal import metadata as metadata_module  # noqa: E402
from src.seal.metadata import collect_seal_metadata_with_python_helpers  # noqa: E402


SEALED_PREREG_SHA256 = "c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05"


def test_seal_helpers_do_not_require_unix_only_tools() -> None:
    """No jq / sha256sum dependency; Python helpers work cross-platform.

    NEW per Codex round-2 New-9. Cross-platform seal invariant.
    References: DRAFT_v4 §9 item 11 + sealed pre-reg §11.2 T21.
    """
    meta = collect_seal_metadata_with_python_helpers()
    # Result is a JSON-serializable dict.
    assert isinstance(meta, dict)
    json.dumps(meta)
    # Required keys are present.
    required_keys = {
        "git_head",
        "timestamp_utc_iso8601",
        "sealed_prereg_path",
        "sealed_prereg_sha256",
        "python_version",
        "python_implementation",
        "platform",
        "platform_system",
        "platform_machine",
    }
    assert required_keys.issubset(meta.keys())
    # sealed_prereg_sha256 matches the canonical sealed hash.
    assert meta["sealed_prereg_sha256"] == SEALED_PREREG_SHA256
    # git_head is a 40-char hex SHA when we are in a git repo.
    if meta["git_head"] is not None:
        assert re.match(r"^[0-9a-f]{40}$", meta["git_head"])
    # No subprocess invocation of Unix-only tools (jq, sha256sum) in source.
    source = inspect.getsource(metadata_module)
    for tool in ('"jq"', "'jq'", '"sha256sum"', "'sha256sum'"):
        assert tool not in source, f"forbidden Unix tool {tool} appears in source"
    # No import of jq/sha256sum modules.
    assert "\nimport jq" not in source
    assert "\nfrom jq" not in source
