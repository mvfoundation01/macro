# Buffett Indicator — Ingestion Layer

Build a multi-variant Buffett Indicator pipeline from FRED + TradingView + Yahoo + Shiller. This package owns the ingestion + spliced-master-archive layer. Downstream models read series via the single `load_master(series_id, ...)` API.

## Setup

```powershell
# 1. Install deps (use the pinned versions where possible)
python -m pip install -r requirements.lock

# 2. Copy the template and paste your FRED API key
copy config.yaml.template config.yaml
# edit config.yaml: fred_api_key: "<your 32-char hex>"

# 3. Run the full ingestion + master build
python -m src.cli
```

The CLI accepts `--skip-fred`, `--skip-yahoo`, `--skip-masters`, and `--force-refresh` for incremental / offline runs.

## What it builds

- `data/raw/` — per-source caches (FRED parquet + meta JSON, Yahoo parquet). Not git-tracked.
- `data/master/<series_id>.parquet` — the spliced, append-only master archive. **Tracked via Git LFS** (see `.gitattributes`).
- `data/master/_catalog.json` — index of every master series with current range + sources.
- `data/master/_scaling_anchors.json` — splice scale factors persisted across runs (so the same `k` is reused on the daily tail refresh).
- `data_manifest.json` — manifest of every input loaded in the last run (provenance, SHAs, row counts).

## The single read API

All downstream code MUST consume series through `load_master`:

```python
from src.ingest.master_archive import load_master
w = load_master("wilshire_5000", start="1990-01-01")
print(w.earliest, w.latest, w.n_observations, w.sources_used)
```

Reading the parquet directly bypasses the splice + drift correction baked into the master and is a spec violation.

## Daily refresh

Re-running `python -m src.cli` after the first build:

1. Reads existing master parquet.
2. Fetches only the tail (~30 days) from Yahoo.
3. Re-applies the saved scale factor (no re-compute, no drift).
4. Appends only NEW dates (existing dates untouched).
5. Atomic write.

Deep history is captured in git LFS and survives even if both TradingView and Yahoo go offline.

## Tests

```powershell
python -m pytest -q
```

Integration tests (real network / real Shiller XLS) are opt-in:

```powershell
$env:INTEGRATION_TESTS = "1"
python -m pytest -m integration -q
```

## Layout

```
src/
├── config.py                 path resolution (Windows + POSIX)
├── cli.py                    CLI entry point (python -m src.cli)
└── ingest/
    ├── _base.py              exceptions, retry, atomic IO, logging
    ├── fred_loader.py        FRED JSON API + cache
    ├── csv_loader.py         TradingView CSV/XLS/XLSX (extension dispatch)
    ├── yahoo_loader.py       yfinance + fallback chain
    ├── shiller_loader.py     ie_data.xls multi-row header detection
    ├── master_archive.py     splice + append-only persistence (THE master)
    └── orchestrator.py       top-level run_ingestion()
tests/ingest/                 50+ unit tests + 2 opt-in integration tests
scripts/smoke_test.py         end-to-end verification
```
