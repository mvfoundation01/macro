"""End-to-end smoke test (Spec section 10).

Run via:
    python scripts/smoke_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `from src...` imports when invoked directly.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import yaml

from src.config import ensure_skeleton
from src.ingest.master_archive import load_master
from src.ingest.orchestrator import run_ingestion


def main() -> int:
    ensure_skeleton()
    api_key = None
    cfg_path = Path("config.yaml")
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
        api_key = cfg.get("fred_api_key")
        if api_key == "PASTE_YOUR_32_CHAR_KEY_HERE":
            api_key = None
    result = run_ingestion(api_key=api_key)

    print("\n=== MASTER LOOKUP via load_master ===")
    try:
        w = load_master("wilshire_5000")
        print(
            f"  wilshire_5000: {w.earliest.date()} -> {w.latest.date()} "
            f" n={w.n_observations}  sources={w.sources_used}"
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  load_master failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
