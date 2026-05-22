"""One-time Norgate Diamond → MoDH bootstrap for ICE DXY (US Dollar Index).

Owner runs this ONCE while Norgate Diamond subscription is active. After
successful execution, the deep history (1971+) is cached in
``data/master/icedxy_close.parquet`` and committed via Git LFS. The
subscription can later be canceled without losing the data.

Usage (from ``D:\\macro\\buffet_indicator``):

    python scripts/bootstrap_icedxy_from_norgate.py [--symbol DXY] [--dry-run]

Owner action checklist (do once)
--------------------------------
1. Confirm Norgate Diamond subscription is active.
2. Confirm the ``norgatedata`` Python package is installed:

       pip install norgatedata

3. Confirm the ICE DXY symbol used by your Norgate installation. Common
   choices: ``'DXY'``, ``'$DXY'``, ``'NYBOT-DX'``. Pass ``--symbol <X>`` if
   the default does not match your watchlist.
4. Run this script. It will:

   a. Fetch 1971-01-01 → today daily close prices via the
      ``norgatedata.price_timeseries`` API.
   b. Write ``data/master/icedxy_close.parquet`` with the MoDH schema
      (``value``, ``source``, ``vintage``, ``transform``).
   c. Print earliest date, latest date, n_obs, head/tail rows, and the
      SHA-256 of the resulting parquet.
   d. Stage + commit via Git LFS (skipped when ``--dry-run``).
   e. Push to ``origin/spec/liquidity-composite-v1.0`` (skipped on ``--dry-run``).

5. Verify::

       git log --oneline -1 data/master/icedxy_close.parquet

6. Done. Subscription can be canceled at any future date — subsequent
   pipeline executions read the cached parquet.

References
----------
- specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.1 row z4 + §1.3.
- specs/BLOCKED_v11_3_A1_icedxy_stooq.md (Session 6 resolution section).
- prompt/052226/PROMPT_v11_3_stage_3_LC_v1_session_6.md §2.0.2.
- master spec §2.4.8 — one-time deep-history builder.
"""
from __future__ import annotations

# --- sys.path bootstrap (must precede any src.* imports) ---
# Standard pattern for scripts under scripts/ invoked as `python scripts/foo.py`
# rather than `python -m scripts.foo`. See tests/scripts/test_sys_path_bootstrap.py
# for the rule that locks this in for all scripts that import from src.*.
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# -----------------------------------------------------------

import argparse
import hashlib
import subprocess  # nosec B404 - used for trusted git commands only, no shell=True

import pandas as pd

# NOTE: this script REQUIRES the norgatedata package (no gated import). Running
# the bootstrap without the Norgate subscription is not a supported workflow.
import norgatedata  # type: ignore  # noqa: F401  (imported for side-effect/side check)

from src.config import MASTER_DIR
from src.ingest._base import get_logger, utcnow
from src.ingest.lc_v1_loader import (
    ICEDXY_CACHE_FILENAME,
    NORGATE_DEFAULT_SYMBOL,
    _fetch_norgate_dxy_live,
    write_icedxy_cache_parquet,
)

logger = get_logger("buffett.bootstrap.icedxy")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _summarize(daily: pd.Series) -> str:
    earliest = daily.index.min()
    latest = daily.index.max()
    return (
        f"earliest={earliest.date()} latest={latest.date()} "
        f"n_obs={len(daily)}\n"
        f"head:\n{daily.head(3)}\n"
        f"tail:\n{daily.tail(3)}"
    )


def _run_git(args: list[str], *, cwd: Path) -> None:
    """Invoke ``git`` with hard-coded args list (no shell). Trusted input only."""
    cmd = ["git", *args]
    logger.info("Running: %s (cwd=%s)", " ".join(cmd), cwd)
    subprocess.run(cmd, cwd=str(cwd), check=True)  # nosec B603 - trusted args list


def bootstrap_icedxy(symbol: str, *, dry_run: bool) -> int:
    """Run the bootstrap. Returns process exit code."""
    logger.info("Bootstrap start: symbol=%s dry_run=%s", symbol, dry_run)

    daily = _fetch_norgate_dxy_live(symbol)
    print(_summarize(daily))

    cache_path = MASTER_DIR / ICEDXY_CACHE_FILENAME

    if dry_run:
        print(f"[DRY-RUN] Would write {cache_path}; would commit + push.")
        return 0

    written = write_icedxy_cache_parquet(
        daily, cache_path=cache_path, source_label="norgate_diamond",
    )
    sha = _sha256_file(written)
    print(f"Wrote {written} (SHA-256={sha})")

    # Stage + commit + push.
    repo_root = MASTER_DIR.parents[1]  # buffet_indicator/
    rel_path = written.relative_to(repo_root)
    _run_git(["add", str(rel_path)], cwd=repo_root)

    msg = (
        f"lc_v1: bootstrap ICE DXY deep history from Norgate Diamond "
        f"(1971+, n={len(daily)}, SHA={sha[:12]})\n\n"
        f"One-shot cache write per Session 6 §2.0. After this commit the\n"
        f"Norgate Diamond subscription can be canceled — pipeline calls read\n"
        f"data/master/{ICEDXY_CACHE_FILENAME} from the cached parquet.\n\n"
        f"Vintage: {pd.Timestamp(utcnow()).isoformat()}\n"
        f"Symbol: {symbol}\n"
    )
    _run_git(["commit", "-m", msg], cwd=repo_root)
    _run_git(["push", "origin", "spec/liquidity-composite-v1.0"], cwd=repo_root)

    print("Bootstrap complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--symbol", default=NORGATE_DEFAULT_SYMBOL,
        help=f"Norgate DXY symbol (default: {NORGATE_DEFAULT_SYMBOL!r}). "
             f"Common alternatives: '$DXY', 'NYBOT-DX'.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print fetch summary but do not write parquet or git-commit.",
    )
    args = parser.parse_args(argv)
    return bootstrap_icedxy(args.symbol, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
