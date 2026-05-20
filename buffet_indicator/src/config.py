"""Project-wide path and constant configuration. Import paths from here only."""
from __future__ import annotations

import os
import platform
from pathlib import Path


def _resolve(env_var: str, win_default: str, posix_default: str) -> Path:
    if (v := os.environ.get(env_var)):
        return Path(v).expanduser().resolve()
    if platform.system() == "Windows":
        return Path(win_default)
    return Path.home() / posix_default


PROJECT_ROOT: Path = _resolve(
    "BUFFETT_PROJECT_ROOT", r"D:\macro\buffet_indicator", "macro/buffet_indicator"
)
SHARED_RAW_DATA: Path = _resolve(
    "BUFFETT_SHARED_RAW", r"D:\macro\raw data", "macro/raw data"
)

# Project-local
DATA_DIR = PROJECT_ROOT / "data"
RAW_CACHE = DATA_DIR / "raw"           # API caches (FRED, Yahoo) -- NOT git-tracked
MASTER_DIR = DATA_DIR / "master"       # MoDH parquets -- Git LFS
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
LOGS_DIR = PROJECT_ROOT / "logs"
MANIFEST = PROJECT_ROOT / "data_manifest.json"
CATALOG = MASTER_DIR / "_catalog.json"
SCALING_ANCHORS = MASTER_DIR / "_scaling_anchors.json"

# Shared raw (TradingView, Shiller files).
# NB: actual files on disk are .csv exports (not .xlsx as in the spec text).
# The csv_loader.py dispatches by extension, so this works transparently;
# we resolve to whichever real file exists.
def _pick_extension(stem: str, exts: tuple[str, ...]) -> Path:
    for ext in exts:
        p = SHARED_RAW_DATA / f"{stem}{ext}"
        if p.exists():
            return p
    # Fall back to the first variant so error messages stay informative.
    return SHARED_RAW_DATA / f"{stem}{exts[0]}"


TV_SPX = _pick_extension("SP_SPX, 1D", (".csv", ".xlsx", ".xls"))
TV_SPXTR = _pick_extension("SP_SPXTR, 1D", (".csv", ".xlsx", ".xls"))
TV_WILSHIRE = _pick_extension("FRED_WILL5000PRFC, 1D", (".csv", ".xlsx", ".xls"))
TV_GDP_BAK = _pick_extension("FRED_GDP, 3M", (".csv", ".xlsx", ".xls"))
SHILLER_XLS = _pick_extension("ie_data", (".xls", ".xlsx"))

# v11.0 macro risk inputs ----------------------------------------------------
TV_US10Y = _pick_extension("TVC_US10Y, 1D", (".csv", ".xlsx", ".xls"))
TV_US03M = _pick_extension("TVC_US03MY, 1D", (".csv", ".xlsx", ".xls"))
BAML_HY_MASTER = _pick_extension("FRED_BAMLH0A0HYM2, 1D", (".csv",))
BAML_IG_MASTER = _pick_extension("FRED_BAMLC0A0CM, 1D", (".csv",))
BAML_HY_BB = _pick_extension("FRED_BAMLH0A1HYBB, 1D", (".csv",))
BAML_HY_CCC = _pick_extension("FRED_BAMLH0A3HYC, 1D", (".csv",))
MARGIN_DEBT_XLSX = SHARED_RAW_DATA / "margin-statistics.xlsx"

GLOBAL_SEED = 42


def ensure_skeleton() -> None:
    """Create all project-local dirs. Idempotent."""
    for d in (DATA_DIR, RAW_CACHE, MASTER_DIR, OUTPUTS_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    # Provide .gitkeep so the empty dirs survive git.
    for d in (RAW_CACHE, LOGS_DIR):
        gk = d / ".gitkeep"
        if not gk.exists():
            gk.write_text("")
