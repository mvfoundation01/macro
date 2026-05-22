"""LC v1.0 end-to-end build driver — ROBUSTNESS variant (truncate mode).

Mirror of ``scripts/build_lc_v1_artifacts.py`` but passes
``rrpontsyd_pre2013_treatment="truncate"`` to ``compute_z1_netfed``, reproducing
the Session 6.5 behavior where RRPONTSYD's pre-2013-09-23 NaNs are NOT
zero-filled. Provides a robustness companion to the canonical zero-fill run.

Outputs:

* ``outputs/lc_v1_composites_truncate.parquet`` — same shape as canonical.
* ``outputs/tables/lc_v1_predictive_regression_truncate.csv`` — same shape.

Per Strategist DECISIONS.md (2026-05-24) §Q1: zero-fill is canonical. This
script exists for robustness reporting only.

Usage::

    python scripts/build_lc_v1_artifacts_robustness.py [--verbose]
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
)

logger = logging.getLogger(__name__)


def verify_prereg_ancestor() -> None:
    """Mirror of the canonical driver's pre-reg ancestor HARD GATE."""
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
        "--n-bootstrap-reps", type=int, default=10_000,
        help="Stationary bootstrap replication count (default 10_000 for robustness; "
             "50_000 used in canonical Session 7 §2.F run).",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    verify_prereg_ancestor()

    logger.info("Computing 5 component z-scores (TRUNCATE mode for z1)...")
    z1 = compute_z1_netfed(rrpontsyd_pre2013_treatment="truncate")
    z2 = compute_z2_m2_yoy()
    z3 = compute_z3_banklend_yoy()
    z4 = compute_z4_dxy_inv()
    z5 = compute_z5_funding_stress()
    for name, z in [("z1", z1), ("z2", z2), ("z3", z3), ("z4", z4), ("z5", z5)]:
        _log_series_stats(name, z)

    logger.info("Building 3 composite scopes + writing TRUNCATE parquet...")
    out_parquet = _PROJECT_ROOT / "outputs" / "lc_v1_composites_truncate.parquet"
    composites_df, composites_path = build_lc_v1_composites(
        z1=z1, z2=z2, z3=z3, z4=z4, z5=z5,
        output_path=out_parquet,
    )
    for col in ("LC_FULL", "LC_TIER2", "LC_DEEP"):
        _log_series_stats(col, composites_df[col])
    logger.info("Wrote %s", composites_path)

    logger.info("Loading SPX total-return monthly (Shiller pre-1988 + SPXTR 1988+)...")
    spx_tr = _load_spx_total_return()
    _log_series_stats("spx_tr", spx_tr)

    logger.info("Running 12-cell predictive regression (truncate mode)...")
    out_csv = _PROJECT_ROOT / "outputs" / "tables" / "lc_v1_predictive_regression_truncate.csv"
    df_reg = run_all_regressions(
        lc_full=composites_df["LC_FULL"],
        lc_tier2=composites_df["LC_TIER2"],
        lc_deep=composites_df["LC_DEEP"],
        spx_tr_monthly=spx_tr,
        output_csv=out_csv,
        n_bootstrap_reps=args.n_bootstrap_reps,
    )
    logger.info("Wrote %s", out_csv)

    print("\n" + "=" * 80)
    print("LC v1.0 REGRESSION RESULTS (TRUNCATE MODE - ROBUSTNESS COMPANION)")
    print("=" * 80)
    with pd.option_context("display.float_format", lambda x: f"{x:.4f}",
                           "display.max_columns", 30):
        print(df_reg.to_string(index=False))
    print("=" * 80)
    print("Artifacts (TRUNCATE mode robustness companion):")
    print(f"  - {composites_path}")
    print(f"  - {out_csv}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
