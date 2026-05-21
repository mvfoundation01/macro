"""Subprocess invocation of v50 + Norgate detection + output sync.

This module is the bridge between the MV dashboard and the v50 engine that
lives outside the repo. ``run_v50_pipeline()`` invokes v50 in a subprocess
with ``V11_1_DROP_STRATEGIES=1`` set, logs to ``logs/v11_1_v50_run_*.log``,
and on success copies CSV / XLSX / 4 governance txt files into the repo's
``outputs/quant_engine/latest/`` directory.

Norgate detection is best-effort: if the package isn't installed or the
data service isn't reachable, the refresh button on the dashboard is
disabled and the user falls back to the last successful run.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .strategy_engine_config import (
    QUANT_PIPELINE_ROOT,
    V50_SCRIPT,
    QE_LATEST_DIR,
    QE_GOVERNANCE_DIR,
)

log = logging.getLogger(__name__)


def check_norgate_available() -> bool:
    """Return True iff Norgate Data Service is reachable.

    Returns False (without raising) on any error — caller decides whether
    a missing Norgate is fatal or just disables the refresh button.
    """
    try:
        import norgatedata  # type: ignore
    except ImportError:
        log.info("Norgate package not installed")
        return False
    try:
        wls = norgatedata.watchlists()
    except Exception as e:  # noqa: BLE001
        log.warning(f"Norgate unavailable: {type(e).__name__}: {e}")
        return False
    return wls is not None and len(wls) > 0


def run_v50_pipeline(
    force_rebuild_features: bool = False,
    timeout_sec: int = 3600,
) -> dict:
    """Run v50 in a subprocess with V11_1_DROP_STRATEGIES=1.

    Args:
        force_rebuild_features: If True, deletes ``features_*.pkl`` and
            ``wf_pred_*.pkl`` from the cache so v50 rebuilds them. This
            adds ~10 minutes to runtime; default False reuses cached
            features for ~10-15 minute warm runs.
        timeout_sec: subprocess timeout (default 1 hour).

    Returns:
        ``{'success': bool, 'timestamp': str|None, 'stdout_log_path': str|None,
           'elapsed_sec': float, 'error': str|None}``
    """
    if not V50_SCRIPT.exists():
        return {
            "success": False,
            "error": f"v50 script not found at {V50_SCRIPT}",
            "timestamp": None,
            "stdout_log_path": None,
            "elapsed_sec": 0,
        }

    env = os.environ.copy()
    env["V11_1_DROP_STRATEGIES"] = "1"

    if force_rebuild_features:
        cache_dir = QUANT_PIPELINE_ROOT / "data_cache"
        for pattern in ("features_*.pkl", "wf_pred_*.pkl"):
            for f in cache_dir.glob(pattern):
                f.unlink(missing_ok=True)
                log.info(f"Removed cached feature file: {f.name}")

    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = (
        log_dir / f'v11_1_v50_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )

    t0 = datetime.now()
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            result = subprocess.run(
                [sys.executable, str(V50_SCRIPT)],
                cwd=str(QUANT_PIPELINE_ROOT),
                env=env,
                stdout=f,
                stderr=subprocess.STDOUT,
                timeout=timeout_sec,
                check=False,
            )
        elapsed = (datetime.now() - t0).total_seconds()
        if result.returncode == 0:
            ts = sync_latest_outputs()
            return {
                "success": True,
                "timestamp": ts,
                "stdout_log_path": str(log_path),
                "elapsed_sec": elapsed,
                "error": None,
            }
        return {
            "success": False,
            "error": f"v50 exited code {result.returncode}",
            "timestamp": None,
            "stdout_log_path": str(log_path),
            "elapsed_sec": elapsed,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"v50 timeout after {timeout_sec}s",
            "timestamp": None,
            "stdout_log_path": str(log_path),
            "elapsed_sec": (datetime.now() - t0).total_seconds(),
        }


def sync_latest_outputs() -> Optional[str]:
    """Copy latest v50 outputs to ``outputs/quant_engine/latest/``.

    Picks the latest ``v50_*.csv`` from the v50 results directory (by
    sorted filename — timestamps embed the date so lex order = chrono
    order). Copies that CSV, the matching XLSX, and the 4 governance
    txt files, then writes ``last_refresh.txt`` with the timestamp.

    Returns the timestamp string ``YYYYMMDD_HHMM`` or None if no v50 output
    was found in the source directory.
    """
    src_dir = QUANT_PIPELINE_ROOT / "results"
    if not src_dir.exists():
        return None
    csvs = sorted(src_dir.glob("v50_*.csv"))
    csvs = [
        p for p in csvs
        if "model_card" not in p.name
        and "config_snapshot" not in p.name
        and "environment_lock" not in p.name
        and "change_log" not in p.name
    ]
    if not csvs:
        return None
    latest_csv = csvs[-1]
    ts = latest_csv.stem.split("_", 1)[1]

    QE_LATEST_DIR.mkdir(parents=True, exist_ok=True)
    QE_GOVERNANCE_DIR.mkdir(exist_ok=True)

    shutil.copy(latest_csv, QE_LATEST_DIR / "latest.csv")
    xlsx = src_dir / f"v50_{ts}.xlsx"
    if xlsx.exists():
        shutil.copy(xlsx, QE_LATEST_DIR / "latest.xlsx")
    for kind in ("model_card", "config_snapshot", "environment_lock", "change_log"):
        gov = src_dir / f"v50_{kind}_{ts}.txt"
        if gov.exists():
            shutil.copy(gov, QE_GOVERNANCE_DIR / f"{kind}.txt")
    (QE_LATEST_DIR / "last_refresh.txt").write_text(ts, encoding="utf-8")
    return ts
