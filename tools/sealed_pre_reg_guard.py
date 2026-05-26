"""Sealed pre-reg SHA-256 immutability guard (Phase F-CI.B)."""

import hashlib
import sys
from pathlib import Path

SEALED_PATH = Path("buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md")
SEALED_SHA = "c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05"


def main() -> int:
    if not SEALED_PATH.exists():
        print(f"::error::Sealed pre-reg missing at {SEALED_PATH}", file=sys.stderr)
        return 1
    actual_sha = hashlib.sha256(SEALED_PATH.read_bytes()).hexdigest()
    if actual_sha != SEALED_SHA:
        print(
            f"::error::SEALED PRE-REG TAMPERING DETECTED\n"
            f"Expected SHA-256: {SEALED_SHA}\n"
            f"Actual SHA-256:   {actual_sha}\n"
            f"\n"
            f"The sealed pre-registration is IMMUTABLE per sealed §6.4 + master spec.\n"
            f"This commit is BLOCKED. Revert your changes to the sealed file.\n",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
