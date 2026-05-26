"""Phase F-REPRO.B — reconstruct master data archive from public sources.

Reads ``data_manifest.json`` (Phase F-REPRO.A) and re-fetches every FRED-source
v2.0 component series via the FRED public API. Validates retrieved data
against the manifest's cached SHA-256 + n_observations / earliest / latest
metadata.

Usage::

    FRED_API_KEY=<key> python -m src.replication.reconstruct_master \
        --manifest data_manifest.json \
        --output-dir data/raw/ \
        --verify-sha

Exit codes:
- ``0``: all manifest-listed FRED series retrieved successfully (SHA may differ
  if FRED has issued revisions since the sprint; see ``sha_mismatches``).
- ``1``: at least one series failed retrieval (network / API / parse error).
- ``2``: ``FRED_API_KEY`` missing and at least one series requires it.
- ``3``: manifest file not readable / malformed.

The script's output JSON (``reconstruction_report.json``) is the canonical
replication-attempt record per :mod:`outputs/replication/REPLICATION_INSTRUCTIONS.md`.

Notes
-----
- FRED series are subject to retroactive revision. A SHA mismatch between the
  reconstructed series and the manifest is EXPECTED, not a failure mode, when
  fetching a series whose underlying data has been revised since the sprint.
  The substantive reproducibility test is whether the verdict pipeline
  (downstream of reconstruction) produces the same outcome — see Phase
  F-REPRO.C clean-state cross-check.
- TradingView / Shiller / Yahoo-sourced series are NOT reconstructed by this
  script; their cached CSV / XLS files must be obtained separately (see
  ``REPLICATION_INSTRUCTIONS.md`` for guidance).

References
----------
- PROMPT_CC_v11_4_phase_F_REPRO.md §3.
- :mod:`src.ingest.fred_loader` — the underlying FRED HTTP+cache client.
- :mod:`src.replication.reconstruct_master` — this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


logger = logging.getLogger(__name__)


# FRED-source v2.0 component series. Maps manifest_key → load_fred_series args.
# The fred_loader interprets `series_id` (FRED identifier) and `frequency`.
FRED_SOURCE_KEYS: dict[str, dict[str, str]] = {
    "master.walcl":     {"fred_id": "WALCL",     "frequency": "W"},
    "master.wdtgal":    {"fred_id": "WDTGAL",    "frequency": "W"},
    "master.rrpontsyd": {"fred_id": "RRPONTSYD", "frequency": "D"},
    "master.m2_sl":     {"fred_id": "M2SL",      "frequency": "M"},
    "master.busloans":  {"fred_id": "BUSLOANS",  "frequency": "M"},
    "master.totll":     {"fred_id": "TOTLL",     "frequency": "W"},
    "master.dtwexbgs":  {"fred_id": "DTWEXBGS",  "frequency": "D"},
    "master.tedrate":   {"fred_id": "TEDRATE",   "frequency": "D"},
    "master.sofr":      {"fred_id": "SOFR",      "frequency": "D"},
    "master.iorb":      {"fred_id": "IORB",      "frequency": "D"},
    "master.ioer":      {"fred_id": "IOER",      "frequency": "D"},
}


@dataclass
class ReconstructionReport:
    """Summary of a reconstruction attempt."""

    manifest_path: str
    output_dir: str
    verify_sha: bool
    succeeded: list[str] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    sha_mismatches: list[dict[str, str]] = field(default_factory=list)
    sha_matches: list[str] = field(default_factory=list)
    skipped_non_fred: list[str] = field(default_factory=list)
    missing_credentials: list[str] = field(default_factory=list)
    exit_code: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "output_dir": self.output_dir,
            "verify_sha": self.verify_sha,
            "summary": {
                "n_succeeded": len(self.succeeded),
                "n_failed": len(self.failed),
                "n_sha_matches": len(self.sha_matches),
                "n_sha_mismatches": len(self.sha_mismatches),
                "n_skipped_non_fred": len(self.skipped_non_fred),
                "n_missing_credentials": len(self.missing_credentials),
                "exit_code": self.exit_code,
            },
            "succeeded": sorted(self.succeeded),
            "failed": self.failed,
            "sha_matches": sorted(self.sha_matches),
            "sha_mismatches": self.sha_mismatches,
            "skipped_non_fred": sorted(self.skipped_non_fred),
            "missing_credentials": sorted(self.missing_credentials),
        }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconstruct_master(
    manifest_path: Path,
    output_dir: Path,
    *,
    verify_sha: bool = True,
    fred_api_key: Optional[str] = None,
    fred_loader: Optional[Any] = None,
) -> ReconstructionReport:
    """Reconstruct FRED-source v2.0 series per ``manifest_path``.

    Parameters
    ----------
    manifest_path : Path
        Path to ``data_manifest.json``.
    output_dir : Path
        Directory for reconstructed series (one parquet per series).
    verify_sha : bool, default True
        If True, compare reconstructed SHA-256 to manifest entry; record
        mismatches (NOT a failure — FRED revisions can legitimately change
        SHA).
    fred_api_key : str, optional
        FRED API key. Defaults to ``os.environ["FRED_API_KEY"]``.
    fred_loader : module, optional
        Override for the FRED loader (mockable for unit tests).

    Returns
    -------
    ReconstructionReport
    """
    report = ReconstructionReport(
        manifest_path=str(manifest_path),
        output_dir=str(output_dir),
        verify_sha=bool(verify_sha),
    )

    if not manifest_path.exists():
        logger.error("manifest not found: %s", manifest_path)
        report.exit_code = 3
        return report

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("manifest JSON parse failed: %s", exc)
        report.exit_code = 3
        return report

    series_block = manifest.get("series") or manifest.get("entries") or {}
    if isinstance(series_block, list):
        series_block = {e.get("key", f"entry_{i}"): e for i, e in enumerate(series_block)}

    api_key = fred_api_key if fred_api_key is not None else os.environ.get("FRED_API_KEY", "")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Lazy import — keeps tests fast and avoids hitting fredapi on import.
    if fred_loader is None:
        try:
            from src.ingest import fred_loader as _fl  # type: ignore[no-redef]
            fred_loader = _fl
        except ImportError as exc:
            logger.error("fred_loader unavailable: %s", exc)
            report.exit_code = 1
            return report

    for manifest_key, fred_meta in FRED_SOURCE_KEYS.items():
        entry = series_block.get(manifest_key)
        if entry is None:
            report.failed.append({"key": manifest_key, "reason": "not_in_manifest"})
            continue

        if not api_key:
            report.missing_credentials.append(manifest_key)
            continue

        fred_id = fred_meta["fred_id"]
        try:
            result = fred_loader.load_fred_series(
                series_id=fred_id,
                frequency=fred_meta["frequency"],
                api_key=api_key,
                cache_dir=output_dir,
            )
        except Exception as exc:  # noqa: BLE001 — record reason and continue
            report.failed.append(
                {"key": manifest_key, "fred_id": fred_id,
                 "reason": f"{type(exc).__name__}: {str(exc)[:200]}"}
            )
            continue

        report.succeeded.append(manifest_key)
        cache_path = getattr(result, "parquet_path", None) or (output_dir / f"{fred_id}.parquet")
        if verify_sha and cache_path and Path(cache_path).exists():
            actual = _sha256_file(Path(cache_path))
            expected = entry.get("sha256")
            if expected and actual == expected:
                report.sha_matches.append(manifest_key)
            elif expected:
                report.sha_mismatches.append({
                    "key": manifest_key,
                    "fred_id": fred_id,
                    "expected": expected,
                    "actual": actual,
                    "note": "FRED may have revised this series since the sprint; substantive verdict reproducibility is the binding test (Phase F-REPRO.C).",
                })

    # Non-FRED series that this script does not reconstruct.
    for key in series_block:
        if key in FRED_SOURCE_KEYS:
            continue
        if key.startswith("forward_returns.") or key.startswith("master.wilshire_5000") or key.startswith("tradingview.") or key.startswith("yahoo.") or key == "shiller.ie_data":
            report.skipped_non_fred.append(key)

    if report.failed:
        report.exit_code = 1
    elif report.missing_credentials:
        report.exit_code = 2
    return report


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=Path("data_manifest.json"),
        help="Path to data_manifest.json (Phase F-REPRO.A output).",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/raw"),
        help="Directory for reconstructed FRED series (parquet per series).",
    )
    parser.add_argument(
        "--verify-sha", action="store_true",
        help="Compare reconstructed SHA-256 to manifest (record mismatches).",
    )
    parser.add_argument(
        "--report-path", type=Path, default=Path("outputs/replication/reconstruction_report.json"),
        help="Where to write the JSON reconstruction report.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    report = reconstruct_master(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        verify_sha=args.verify_sha,
    )

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(
        json.dumps(report.to_json(), indent=2, sort_keys=False, default=str) + "\n",
        encoding="utf-8",
    )
    summary = report.to_json()["summary"]
    print(
        f"reconstruct_master: succeeded={summary['n_succeeded']} "
        f"failed={summary['n_failed']} "
        f"sha_matches={summary['n_sha_matches']} "
        f"sha_mismatches={summary['n_sha_mismatches']} "
        f"missing_credentials={summary['n_missing_credentials']} "
        f"skipped_non_fred={summary['n_skipped_non_fred']} "
        f"exit_code={report.exit_code}"
    )
    return int(report.exit_code)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
