"""Cross-platform seal-metadata helpers — DRAFT_v4 §9 item 11 (seal 2a94417).

References
----------
- Sealed pre-reg §9 item 11: seal-time helpers must NOT depend on
  Unix-only tools (no ``jq``, no ``sha256sum``); use Python equivalents
  so the helpers work identically on Windows and POSIX.
- Sealed pre-reg §11.1 line 743: function signature.
"""
from __future__ import annotations

import datetime
import hashlib
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional


SEALED_PREREG_RELPATH: str = "buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md"
"""Sealed pre-reg path relative to the repo root."""


def _git_head_sha(repo_root: Path) -> Optional[str]:
    """Return the current git HEAD SHA, or None on any error.

    Uses ``subprocess`` (the one Unix-not-required helper) per §9 item 11.
    No ``shell=True`` and no string-concatenated commands (§13.3).
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out or None


def _sha256_of_file(path: Path) -> Optional[str]:
    """Return lowercased hex SHA-256 of ``path``, or None if absent."""
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, FileNotFoundError):
        return None


def _repo_root() -> Path:
    """Locate the repo root by walking up until we see a ``.git`` directory."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".git").exists():
            return parent
    # Fallback: 3 levels up from this file (buffet_indicator/src/seal/metadata.py).
    return here.parents[3]


def collect_seal_metadata_with_python_helpers() -> dict:
    """Collect seal-time metadata using cross-platform Python only.

    Returns a JSON-serializable ``dict`` containing:

    - ``git_head`` — current ``HEAD`` SHA (from ``subprocess git``; the
      only external invocation; no ``jq``/``sha256sum``).
    - ``timestamp_utc_iso8601`` — current UTC time in ISO-8601 form.
    - ``sealed_prereg_path`` — repo-relative path to the sealed pre-reg.
    - ``sealed_prereg_sha256`` — lowercased hex digest, or ``None`` if
      the file is absent.
    - ``python_version`` — full ``sys.version`` interpreter string.
    - ``python_implementation`` — CPython / PyPy / etc.
    - ``platform`` — ``platform.platform()`` cross-platform identifier.
    - ``platform_system`` — ``platform.system()`` (Windows / Linux / Darwin).
    - ``platform_machine`` — CPU architecture.

    Returns
    -------
    dict

    References
    ----------
    Sealed pre-reg §9 item 11 + §11.1 line 743. Test: ``T21``.
    """
    root = _repo_root()
    sealed_path = root / SEALED_PREREG_RELPATH

    return {
        "git_head": _git_head_sha(root),
        "timestamp_utc_iso8601": (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "sealed_prereg_path": SEALED_PREREG_RELPATH,
        "sealed_prereg_sha256": _sha256_of_file(sealed_path),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
    }
