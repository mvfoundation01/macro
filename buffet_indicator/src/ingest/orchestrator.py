"""Top-level orchestrator: runs the full ingestion layer end-to-end."""
from __future__ import annotations

from pathlib import Path
from typing import Any


from src.config import MANIFEST, ensure_skeleton
from src.ingest._base import (
    IngestError,
    SourceMissingError,
    atomic_write_json,
    get_logger,
    utcnow,
)
from src.ingest.csv_loader import load_tradingview_inputs
from src.ingest.fred_loader import load_buffett_fred
from src.ingest.master_archive import build_all_masters
from src.ingest.shiller_loader import load_shiller
from src.ingest.yahoo_loader import load_wilshire_yahoo

logger = get_logger("buffett.ingest.orchestrator")


def _load_api_key(api_key_arg: str | None) -> str:
    if api_key_arg:
        return api_key_arg
    cfg_path = Path("config.yaml")
    if cfg_path.exists():
        import yaml

        cfg = yaml.safe_load(cfg_path.read_text()) or {}
        key = cfg.get("fred_api_key")
        if key and key != "PASTE_YOUR_32_CHAR_KEY_HERE":
            return key
    import os

    env_key = os.environ.get("FRED_API_KEY")
    if env_key:
        return env_key
    raise IngestError(
        "No FRED API key provided",
        user_message=(
            "FRED API key is required. Pass via api_key=..., put it in config.yaml "
            "(fred_api_key), or set FRED_API_KEY env var."
        ),
    )


def _write_manifest(result: dict[str, Any]) -> None:
    entries: list[dict[str, Any]] = []
    for key, fs in result.get("fred", {}).items():
        entries.append(
            {
                "key": f"fred.{key}",
                "series_id": fs.series_id,
                "source_tier": 2,
                "frequency": fs.frequency,
                "units": fs.units,
                "n_observations": int(len(fs.data)),
                "earliest": str(fs.data.index.min().date()),
                "latest": str(fs.data.index.max().date()),
                "sha256": fs.sha256,
                "cache_path": str(fs.cache_path),
                "retrieval_timestamp": fs.retrieval_timestamp.isoformat(),
            }
        )
    for key, ts in result.get("tradingview", {}).items():
        entries.append(
            {
                "key": f"tradingview.{key}",
                "symbol": ts.symbol,
                "source_tier": 5,
                "frequency": ts.frequency,
                "units": ts.units,
                "n_observations": int(len(ts.data)),
                "earliest": str(ts.data.index.min().date()),
                "latest": str(ts.data.index.max().date()),
                "sha256": ts.sha256,
                "source_file": str(ts.source_file),
                "file_format": ts.file_format,
                "retrieval_timestamp": ts.retrieval_timestamp.isoformat(),
            }
        )
    if (yh := result.get("yahoo_wilshire")) is not None:
        entries.append(
            {
                "key": "yahoo.wilshire",
                "symbol": yh.symbol,
                "source_tier": 4,
                "frequency": yh.frequency,
                "n_observations": int(len(yh.data)),
                "earliest": str(yh.data.index.min().date()),
                "latest": str(yh.data.index.max().date()),
                "sha256": yh.sha256,
                "cache_path": str(yh.cache_path),
                "retrieval_timestamp": yh.retrieval_timestamp.isoformat(),
            }
        )
    if (sh := result.get("shiller")) is not None:
        entries.append(
            {
                "key": "shiller.ie_data",
                "source_tier": 1,
                "frequency": "M",
                "file_format": sh.file_format,
                "n_observations": int(len(sh.data)),
                "earliest": str(sh.start_date.date()),
                "latest": str(sh.end_date.date()),
                "sha256": sh.sha256,
                "retrieval_timestamp": sh.retrieval_timestamp.isoformat(),
            }
        )
    for sid, ms in result.get("masters", {}).items():
        entries.append(
            {
                "key": f"master.{sid}",
                "series_id": sid,
                "source_tier": "spliced",
                "n_observations": ms.n_observations,
                "earliest": str(ms.earliest.date()),
                "latest": str(ms.latest.date()),
                "sources_used": list(ms.sources_used),
            }
        )
    atomic_write_json(
        MANIFEST,
        {
            "generated_at": utcnow().isoformat(),
            "entries": entries,
        },
    )


def _print_summary(result: dict[str, Any]) -> None:
    print("\n=== FRED ===")
    for k, s in result.get("fred", {}).items():
        print(
            f"  {k:18s} {s.data.index[0].date()} -> {s.data.index[-1].date()} "
            f" n={len(s.data):>5d}"
        )
    print("\n=== TradingView ===")
    for k, s in result.get("tradingview", {}).items():
        print(
            f"  {k:18s} {s.data.index[0].date()} -> {s.data.index[-1].date()} "
            f" n={len(s.data):>5d}"
        )
    if (yh := result.get("yahoo_wilshire")) is not None:
        print("\n=== Yahoo Wilshire ===")
        print(
            f"  selected: {yh.symbol}  range: {yh.data.index[0].date()} -> "
            f"{yh.data.index[-1].date()}  n={len(yh.data)}"
        )
    if (sh := result.get("shiller")) is not None:
        print("\n=== Shiller ===")
        print(
            f"  {sh.data.index[0].date()} -> {sh.data.index[-1].date()} "
            f" n={len(sh.data)}"
        )
        if "cape" in sh.data.columns:
            cape_last = sh.data["cape"].dropna().iloc[-1] if not sh.data["cape"].dropna().empty else float("nan")
            print(f"  Latest CAPE: {cape_last:.2f}")
    print("\n=== MASTERS (the persistent spliced archive) ===")
    for sid, ms in result.get("masters", {}).items():
        print(
            f"  {sid}: {ms.earliest.date()} -> {ms.latest.date()} "
            f" n={ms.n_observations}  sources={ms.sources_used}"
        )


def run_ingestion(
    *,
    api_key: str | None = None,
    force_refresh: bool = False,
    skip_fred: bool = False,
    skip_yahoo: bool = False,
    skip_masters: bool = False,
) -> dict[str, Any]:
    """Build the complete ingestion layer.

    Returns a dict with keys: ``fred``, ``tradingview``, ``yahoo_wilshire``,
    ``shiller``, ``masters``.
    """
    ensure_skeleton()
    result: dict[str, Any] = {}

    # 1. FRED -- optional skip allows the orchestrator to run without a key (testing/dry-run).
    if not skip_fred:
        try:
            key = _load_api_key(api_key)
            result["fred"] = load_buffett_fred(key, force_refresh=force_refresh)
        except IngestError as exc:
            logger.warning("FRED loaders skipped: %s", exc)
            result["fred"] = {}
    else:
        result["fred"] = {}

    # 2. TradingView inputs.
    try:
        result["tradingview"] = load_tradingview_inputs(require_all=False)
    except SourceMissingError as exc:
        logger.warning("TradingView inputs not fully available: %s", exc)
        result["tradingview"] = {}

    # 3. Yahoo Wilshire.
    if not skip_yahoo:
        try:
            result["yahoo_wilshire"] = load_wilshire_yahoo()
        except IngestError as exc:
            logger.warning("Yahoo Wilshire skipped: %s", exc)
            result["yahoo_wilshire"] = None
    else:
        result["yahoo_wilshire"] = None

    # 4. Shiller.
    try:
        result["shiller"] = load_shiller()
    except IngestError as exc:
        logger.warning("Shiller skipped: %s", exc)
        result["shiller"] = None

    # 5. Masters.
    if not skip_masters and result.get("tradingview", {}).get("wilshire_tv") and result.get("yahoo_wilshire"):
        try:
            result["masters"] = build_all_masters()
        except IngestError as exc:
            logger.warning("Master archive build skipped: %s", exc)
            result["masters"] = {}
    else:
        result["masters"] = {}

    _write_manifest(result)
    _print_summary(result)
    return result


__all__ = ["run_ingestion"]
