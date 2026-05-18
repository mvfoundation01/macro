"""CLI entry point: ``python -m src.cli`` runs the full ingestion."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from src.config import ensure_skeleton
from src.ingest.orchestrator import run_ingestion


def main() -> int:
    parser = argparse.ArgumentParser(description="Buffett Indicator ingestion CLI")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: ./config.yaml).",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Bypass caches and re-fetch from all online sources.",
    )
    parser.add_argument(
        "--skip-fred",
        action="store_true",
        help="Skip FRED loader (useful if api key is missing).",
    )
    parser.add_argument(
        "--skip-yahoo",
        action="store_true",
        help="Skip Yahoo loader (offline runs).",
    )
    parser.add_argument(
        "--skip-masters",
        action="store_true",
        help="Skip master archive build.",
    )
    args = parser.parse_args()

    ensure_skeleton()

    api_key: str | None = None
    cfg_path = Path(args.config)
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
        if cfg.get("fred_api_key") and cfg["fred_api_key"] != "PASTE_YOUR_32_CHAR_KEY_HERE":
            api_key = cfg["fred_api_key"]

    run_ingestion(
        api_key=api_key,
        force_refresh=args.force_refresh,
        skip_fred=args.skip_fred,
        skip_yahoo=args.skip_yahoo,
        skip_masters=args.skip_masters,
    )
    print("\nIngestion complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
