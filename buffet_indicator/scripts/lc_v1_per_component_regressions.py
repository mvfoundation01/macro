"""LC v1.0 per-component univariate predictive regressions.

For each of z₁..z₅ (canonical zero-fill for z₁) and each horizon h ∈ {1,3,5,10}
years, run ``r_{t,t+h} = α + β · z_component_t + ε`` using the same
Newey-West / Stambaugh / stationary-bootstrap pipeline as the composite
regression in ``src/models/lc_v1_regression.run_predictive_regression``.

Purpose: verify that composite β signs are consistent with a weighted average
of per-component β signs. If LC_DEEP β at 5Y is negative but z₂/z₃/z₄
per-component β's are all positive, that is a composite-construction bug. If
per-component β's are also negative, the negative-sign finding is robust.

Output:
    outputs/tables/lc_v1_per_component_regressions.csv  (5 components × 4 horizons = 20 rows)

References
----------
* prompt/052226/PROMPT_v11_3_session_7_DECISIONS_investigation_F_G.md §2.1.6
* DECISIONS.md 2026-05-24 §Q2 (sign-anomaly investigation)
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

import pandas as pd

from src.models.lc_v1_components import (
    compute_z1_netfed,
    compute_z2_m2_yoy,
    compute_z3_banklend_yoy,
    compute_z4_dxy_inv,
    compute_z5_funding_stress,
)
from src.models.lc_v1_regression import (
    run_predictive_regression,
    _load_spx_total_return,
    HORIZONS_YEARS,
    _result_to_dict,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--n-bootstrap-reps", type=int, default=10_000,
        help="Stationary bootstrap reps (default 10_000).",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Computing 5 component z-scores (zero-fill for z1)...")
    components: dict[str, pd.Series] = {
        "z1_netfed": compute_z1_netfed(),
        "z2_m2_yoy": compute_z2_m2_yoy(),
        "z3_banklend_yoy": compute_z3_banklend_yoy(),
        "z4_dxy_inv": compute_z4_dxy_inv(),
        "z5_funding_stress": compute_z5_funding_stress(),
    }

    logger.info("Loading SPX total-return monthly...")
    spx_tr = _load_spx_total_return()

    from src.models.lc_v1_regression import _forward_log_return

    rows: list[dict] = []
    for comp_name, z_series in components.items():
        logger.info("Running per-component regressions for %s...", comp_name)
        for h in HORIZONS_YEARS:
            fwd = _forward_log_return(spx_tr, h)
            res = run_predictive_regression(
                lc=z_series.dropna(),
                forward_return=fwd,
                horizon_years=h,
                scope_name=comp_name,
                n_bootstrap_reps=args.n_bootstrap_reps,
            )
            d = _result_to_dict(res)
            # Rename `scope` → `component` for clarity in this output.
            d["component"] = d.pop("scope")
            rows.append(d)

    df = pd.DataFrame(rows)
    # Move the `component` column to first position.
    cols = ["component"] + [c for c in df.columns if c != "component"]
    df = df[cols]

    out_csv = _PROJECT_ROOT / "outputs" / "tables" / "lc_v1_per_component_regressions.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    logger.info("Wrote %s", out_csv)

    print("\n" + "=" * 80)
    print("LC v1.0 PER-COMPONENT UNIVARIATE REGRESSIONS  -  5 components x 4 horizons")
    print("=" * 80)
    with pd.option_context("display.float_format", lambda x: f"{x:.4f}",
                           "display.max_columns", 30):
        print(df.to_string(index=False))
    print("=" * 80)
    print(f"Artifact: {out_csv}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
