"""Phase F-DOC.C — verdict JSON normalized comparison.

Strips dynamic-metadata fields so two verdict JSONs (e.g., pre-pin vs pinned
re-run) can be compared for substantive equivalence. Returns a canonical
SHA-256 of the normalized substantive content, plus a per-field diff helper.

Dynamic fields that legitimately vary across runs:
- ``run_timestamp`` — when the run executed
- ``git_head`` — code commit at run time
- ``_meta.library_versions_installed`` — installed env
- ``_meta.python_version`` / ``_meta.platform`` — host OS
- ``_meta.library_version_delta_note`` — narrative note that references env
- ``_meta.seal_metadata.recorded_at`` — when seal metadata was captured

References
----------
- PROMPT_CC_v11_4_phase_F_DOC.md §4.2
- Phase F-BLK1.F byte-exact write (file-byte SHA changes per dynamic fields;
  normalized SHA must NOT change under sealed methodology + same data cutoff)
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any


DYNAMIC_FIELD_PATHS: tuple[str, ...] = (
    # Top-level dynamic
    "run_timestamp",
    "git_head",
    # _meta dynamic (env + narrative)
    "_meta.library_versions_installed",
    "_meta.library_version_delta_note",
    "_meta.python_version",
    "_meta.python_implementation",
    "_meta.platform",
    # _meta.seal_metadata dynamic (actual field names per
    # src.seal.metadata.collect_seal_metadata_with_python_helpers)
    "_meta.seal_metadata.git_head",
    "_meta.seal_metadata.timestamp_utc_iso8601",
    "_meta.seal_metadata.python_version",
    "_meta.seal_metadata.python_implementation",
    "_meta.seal_metadata.platform",
    "_meta.seal_metadata.platform_system",
    "_meta.seal_metadata.platform_machine",
)


def _del_dotted(obj: Any, dotted: str) -> None:
    """Delete a dotted-path key from a nested dict (in-place). No-op if absent."""
    parts = dotted.split(".")
    cur = obj
    for p in parts[:-1]:
        if not isinstance(cur, dict) or p not in cur:
            return
        cur = cur[p]
    if isinstance(cur, dict) and parts[-1] in cur:
        del cur[parts[-1]]


def normalize_verdict_for_comparison(verdict: dict) -> dict:
    """Return a deep copy of ``verdict`` with dynamic-metadata fields removed.

    The remaining content is the substantive verdict: decision rule, per-criterion
    statuses + values, per-cell regression / bootstrap / skewt fits, audit
    results, panel meta (data cutoff, scopes, OOS splits, vintage construction).
    Under sealed methodology + same data + same code, this normalized content
    must be byte-identical across runs (subject to tolerated float drift per
    library version).
    """
    normalized = copy.deepcopy(verdict)
    for dotted in DYNAMIC_FIELD_PATHS:
        _del_dotted(normalized, dotted)
    return normalized


def normalized_sha256(verdict_json_path: Path) -> str:
    """Compute SHA-256 of the normalized verdict (substantive content only)."""
    verdict = json.loads(Path(verdict_json_path).read_text(encoding="utf-8"))
    normalized = normalize_verdict_for_comparison(verdict)
    canonical = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def field_level_diff(
    a_path: Path,
    b_path: Path,
    *,
    float_tolerance: float = 1e-12,
) -> dict[str, tuple[Any, Any]]:
    """Per-field substantive diff between two verdict JSONs.

    Returns mapping ``{dotted_path: (a_value, b_value)}`` for fields that differ
    after normalization. Float values are compared with absolute tolerance
    ``float_tolerance``; NaN equals NaN. Lists are walked element-wise; missing
    elements are ``None``.
    """
    a = normalize_verdict_for_comparison(
        json.loads(Path(a_path).read_text(encoding="utf-8"))
    )
    b = normalize_verdict_for_comparison(
        json.loads(Path(b_path).read_text(encoding="utf-8"))
    )

    diffs: dict[str, tuple[Any, Any]] = {}

    def _both_nan(x: Any, y: Any) -> bool:
        try:
            return (
                isinstance(x, float)
                and isinstance(y, float)
                and math.isnan(x)
                and math.isnan(y)
            )
        except (TypeError, ValueError):
            return False

    def walk(av: Any, bv: Any, path: str = "") -> None:
        if av is None and bv is None:
            return
        if type(av) is not type(bv):
            diffs[path] = (av, bv)
            return
        if isinstance(av, dict):
            keys = set(av.keys()) | set(bv.keys())
            for k in keys:
                walk(av.get(k), bv.get(k), f"{path}.{k}" if path else k)
        elif isinstance(av, list):
            for i in range(max(len(av), len(bv))):
                aa = av[i] if i < len(av) else None
                bb = bv[i] if i < len(bv) else None
                walk(aa, bb, f"{path}[{i}]")
        elif isinstance(av, float) and isinstance(bv, float):
            if _both_nan(av, bv):
                return
            if not math.isfinite(av) or not math.isfinite(bv):
                if av != bv:
                    diffs[path] = (av, bv)
                return
            if abs(av - bv) > float_tolerance:
                diffs[path] = (av, bv)
        else:
            if av != bv:
                diffs[path] = (av, bv)

    walk(a, b)
    return diffs
