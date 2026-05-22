"""LC v1.0 end-to-end build driver.

Reads the 12 source series from the Master of Data History (MoDH), computes
the 5 component z-scores, builds the 3 composite scopes (LC_FULL/TIER2/DEEP),
constructs the SPX total-return monthly returns series, and runs the
predictive regression across all 12 (scope × horizon) cells.

Outputs:

* ``outputs/lc_v1_composites.parquet`` — 3 composite scopes, monthly EOM.
  (Written internally by ``build_lc_v1_composites`` with the pre-reg
  ancestor HARD GATE enforced per spec §0.1.)
* ``outputs/tables/lc_v1_predictive_regression.csv`` — 12 regression cells
  (3 scopes × {1Y, 3Y, 5Y, 10Y}).

Pre-condition:
    ``data/master/icedxy_close.parquet`` exists (produced once by
    ``scripts/bootstrap_icedxy_from_norgate.py`` while a Norgate Diamond
    subscription is active).

Hard gate:
    pre-registration commit ``a8635ef`` MUST be an ancestor of HEAD before
    any output is written. Per spec §0.1, violation = pipeline rejection.
    The gate is enforced inside ``write_composites_parquet`` (called by
    ``build_lc_v1_composites``); we also call ``verify_prereg_ancestor``
    at driver start for an early, explicit fail-fast.

Usage::

    python scripts/build_lc_v1_artifacts.py [--verbose]

References
----------
* prompt/052226/PROMPT_v11_3_session_6_5_oneshot_bootstrap_and_regression.md §2.2
* specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.1-§3.5
* SESSION_6_FINAL_REPORT.md (per-module signatures referenced here)
"""
from __future__ import annotations

# --- sys.path bootstrap (must precede any src.* imports) ---
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# -----------------------------------------------------------

import argparse
import logging
import subprocess  # nosec B404 - used only for the git ancestor probe

import pandas as pd

from src.models.lc_v1_components import (
    compute_z1_netfed,
    compute_z2_m2_yoy,
    compute_z3_banklend_yoy,
    compute_z4_dxy_inv,
    compute_z5_funding_stress,
)
from src.models.lc_v1_composite import build_lc_v1_composites
from src.models.lc_v1_regression import (
    run_all_regressions,
    _load_spx_total_return,
    REGRESSION_CSV_RELATIVE,
)

logger = logging.getLogger(__name__)


def verify_prereg_ancestor() -> None:
    """HARD GATE: a8635ef must be an ancestor of HEAD before any artifact write.

    Mirrors ``src.models.lc_v1_composite._verify_pre_reg_ancestor`` so this
    driver fails fast at startup rather than mid-write.
    """
    result = subprocess.run(  # nosec B603 B607
        ["git", "merge-base", "--is-ancestor", "a8635ef", "HEAD"],
        cwd=str(_PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "HARD GATE FAILED: pre-reg commit a8635ef is NOT an ancestor of HEAD. "
            "Per spec §0.1, no LC artifact may be written. Aborting."
        )
    logger.info("HARD GATE PASS: a8635ef is ancestor of HEAD.")


def _log_series_stats(name: str, s: pd.Series) -> None:
    valid = s.dropna()
    if valid.empty:
        logger.info("%s: n=0, range=<empty>", name)
    else:
        logger.info(
            "%s: n=%d, range=%s -> %s",
            name, len(valid),
            valid.index.min().date(), valid.index.max().date(),
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--no-enforce-pre-reg", action="store_true",
        help="Skip the a8635ef ancestor HARD GATE (testing only).",
    )
    parser.add_argument(
        "--n-bootstrap-reps", type=int, default=10_000,
        help="Stationary bootstrap replication count (default 10_000 per pre-reg §3.5).",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not args.no_enforce_pre_reg:
        verify_prereg_ancestor()

    logger.info("Computing 5 component z-scores...")
    z1 = compute_z1_netfed()
    z2 = compute_z2_m2_yoy()
    z3 = compute_z3_banklend_yoy()
    z4 = compute_z4_dxy_inv()
    z5 = compute_z5_funding_stress()
    for name, z in [("z1", z1), ("z2", z2), ("z3", z3), ("z4", z4), ("z5", z5)]:
        _log_series_stats(name, z)

    logger.info("Building 3 composite scopes + writing parquet (with HARD GATE)...")
    composites_df, composites_path = build_lc_v1_composites(
        z1=z1, z2=z2, z3=z3, z4=z4, z5=z5,
        enforce_pre_reg=not args.no_enforce_pre_reg,
    )
    for col in ("LC_FULL", "LC_TIER2", "LC_DEEP"):
        _log_series_stats(col, composites_df[col])
    logger.info("Wrote %s", composites_path)

    logger.info("Loading SPX total-return monthly (Shiller pre-1988 + SPXTR 1988+)...")
    spx_tr = _load_spx_total_return()
    _log_series_stats("spx_tr", spx_tr)

    logger.info("Running 12-cell predictive regression...")
    df_reg = run_all_regressions(
        lc_full=composites_df["LC_FULL"],
        lc_tier2=composites_df["LC_TIER2"],
        lc_deep=composites_df["LC_DEEP"],
        spx_tr_monthly=spx_tr,
        n_bootstrap_reps=args.n_bootstrap_reps,
    )
    out_csv = _PROJECT_ROOT / "outputs" / REGRESSION_CSV_RELATIVE
    logger.info("Wrote %s", out_csv)

    print("\n" + "=" * 80)
    print("LC v1.0 REGRESSION RESULTS  -  12 CELLS")
    print("=" * 80)
    # Format with sensible precision for terminal display.
    with pd.option_context("display.float_format", lambda x: f"{x:.4f}", "display.max_columns", 30):
        print(df_reg.to_string(index=False))
    print("=" * 80)
    print("Artifacts:")
    print(f"  - {composites_path}")
    print(f"  - {out_csv}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
