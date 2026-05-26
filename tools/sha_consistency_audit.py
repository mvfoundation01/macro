"""
SHA-256 cross-document consistency audit.

Scans key v11.4 sprint documents for hex-encoded SHA-256 patterns and
groups by value. Verifies that each canonical SHA appears consistently
across the codebase, and flags any unknown SHA values for review.

Usage: python tools/sha_consistency_audit.py
Run from repo root.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path

CANONICAL: dict[str, str] = {
    "sealed_pre_reg": "c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05",  # pragma: allowlist secret
    "verdict_filebyte_blk1": "df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c",  # pragma: allowlist secret
    "verdict_normalized_substantive": "0fe5c5053af78bac061a7ca89568b484b6583a6d9da0d0ddbf5b0837d7344f02",  # pragma: allowlist secret
    "verdict_pre_blk1_filebyte": "6671cc9ff7b9e9f97a0c7447528bf0bcdc12b18a9406b29a8f0e632550200416",  # pragma: allowlist secret
    "verdict_closeout_filebyte": "1925e658ef9c88aabecae03c445396f4ed6ffe7a290f07cd0ecb5122a5c31899",  # pragma: allowlist secret
    "verdict_clonestate_filebyte": "33649ab75c5f521ad17d8198f85ec7f4d8d0d1230f4d17977369bdcbaf5c891a",  # pragma: allowlist secret
}

SHA256_PATTERN = re.compile(r"\b([0-9a-f]{64})\b", re.IGNORECASE)

DOCS_TO_SCAN: list[str] = [
    "README.md",
    "DECISIONS.md",
    "buffet_indicator/outputs/SPRINT_v11_4_INDEX.md",
    "buffet_indicator/outputs/lc_v2_verdict_summary.md",
    "buffet_indicator/outputs/lc_v2_verdict_blk1_delta.md",
    "buffet_indicator/outputs/lc_v2_verdict_closeout_delta.md",
    "buffet_indicator/outputs/v11_4_sprint_engineering_closeout.md",
    "buffet_indicator/outputs/replication/REPLICATION_INSTRUCTIONS.md",
    "buffet_indicator/outputs/replication/v11_4_clean_state_repro_report.md",
    "buffet_indicator/data_manifest.json",
    ".github/workflows/v11_4_verify.yml",
    "tools/sealed_pre_reg_guard.py",
]


def main() -> int:
    sha_to_docs: dict[str, list[str]] = defaultdict(list)
    unknown_shas: dict[str, list[str]] = defaultdict(list)

    canonical_values = {v.lower() for v in CANONICAL.values()}

    print("=== Scanning documents for SHA-256 patterns ===")
    for doc in DOCS_TO_SCAN:
        path = Path(doc)
        if not path.exists():
            print(f"  [skip] {doc} (not found)")
            continue
        content = path.read_text(encoding="utf-8")
        shas_in_doc = set(SHA256_PATTERN.findall(content.lower()))
        for sha in shas_in_doc:
            sha_to_docs[sha].append(doc)
            if sha not in canonical_values:
                unknown_shas[sha].append(doc)
        print(f"  [ok]   {doc} ({len(shas_in_doc)} SHA(s) found)")

    print("\n=== Canonical SHA presence audit ===")
    for name, sha in CANONICAL.items():
        docs = sha_to_docs.get(sha.lower(), [])
        print(f"  {name}")
        print(f"    sha={sha}")
        print(f"    appears in {len(docs)} document(s):")
        for d in docs:
            print(f"      - {d}")

    if unknown_shas:
        print("\n=== Unknown SHAs found (potential typos or new artifacts) ===")
        for sha, docs in unknown_shas.items():
            print(f"  {sha}")
            for d in docs:
                print(f"    in: {d}")
    else:
        print(
            "\n=== Unknown SHAs found: NONE (all SHAs in scanned docs are canonical) ==="
        )

    print("\n=== Live SHA verification ===")
    actual_sealed_path = Path(
        "buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md"
    )
    if actual_sealed_path.exists():
        actual = hashlib.sha256(actual_sealed_path.read_bytes()).hexdigest()
        match = "OK" if actual == CANONICAL["sealed_pre_reg"] else "MISMATCH"
        print(f"  [{match}] sealed pre-reg live SHA: {actual}")

    actual_verdict_path = Path("buffet_indicator/outputs/lc_v2_verdict.json")
    if actual_verdict_path.exists():
        actual = hashlib.sha256(actual_verdict_path.read_bytes()).hexdigest()
        match = "OK" if actual == CANONICAL["verdict_filebyte_blk1"] else "MISMATCH"
        print(f"  [{match}] canonical verdict live SHA: {actual}")

    actual_pre_blk1_path = Path(
        "buffet_indicator/outputs/historical/lc_v2_verdict_pre_blk1.json"
    )
    if actual_pre_blk1_path.exists():
        actual = hashlib.sha256(actual_pre_blk1_path.read_bytes()).hexdigest()
        match = "OK" if actual == CANONICAL["verdict_pre_blk1_filebyte"] else "MISMATCH"
        print(f"  [{match}] pre-BLK-1 historical verdict live SHA: {actual}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
