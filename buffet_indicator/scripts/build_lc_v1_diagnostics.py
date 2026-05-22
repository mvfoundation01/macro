"""LC v1.0 diagnostics driver (Session 8 §2.H).

Runs stationarity tests (ADF/KPSS/PP/ZA), VIF + correlation + eigenvalue
spectrum, and Bai-Perron breaks. Writes 5 CSV files under ``outputs/tables/``:

* ``lc_v1_stationarity.csv``
* ``lc_v1_diagnostics.csv`` (VIF + multicollinearity flag)
* ``lc_v1_component_correlation_matrix.csv``
* ``lc_v1_component_eigenvalues.csv``
* ``lc_v1_bai_perron_breaks.csv``

References
----------
* prompt/052226/PROMPT_v11_3_session_8_H_I_J_closeout.md §2.H
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
from src.models.lc_v1_diagnostics import (
    compute_vif_matrix,
    run_bai_perron_breaks,
    run_stationarity_tests,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 5 components (zero-fill canonical for z1).
    logger.info("Computing 5 component z-scores (zero-fill canonical)...")
    components: dict[str, pd.Series] = {
        "z1_netfed": compute_z1_netfed(),
        "z2_m2_yoy": compute_z2_m2_yoy(),
        "z3_banklend_yoy": compute_z3_banklend_yoy(),
        "z4_dxy_inv": compute_z4_dxy_inv(),
        "z5_funding_stress": compute_z5_funding_stress(),
    }

    # 3 composites from the canonical parquet.
    composites_path = _PROJECT_ROOT / "outputs" / "lc_v1_composites.parquet"
    composites = pd.read_parquet(composites_path)

    # ------------------------------------------------------------------
    # 1. Stationarity tests (4 each) on 5 components + 3 composites
    # ------------------------------------------------------------------
    logger.info("Running stationarity tests on 5 components + 3 composites...")
    series_to_test: list[tuple[str, pd.Series]] = []
    for name, s in components.items():
        series_to_test.append((name, s))
    for col in ("LC_FULL", "LC_TIER2", "LC_DEEP"):
        series_to_test.append((col, composites[col].dropna()))

    stationarity_rows: list[dict[str, object]] = []
    for name, s in series_to_test:
        res = run_stationarity_tests(s, name)
        stationarity_rows.append({
            "series_name": res.series_name,
            "n_obs": res.n_obs,
            "adf_stat": res.adf_stat,
            "adf_pvalue": res.adf_pvalue,
            "adf_lags": res.adf_lags,
            "kpss_stat": res.kpss_stat,
            "kpss_pvalue": res.kpss_pvalue,
            "kpss_lags": res.kpss_lags,
            "pp_stat": res.pp_stat,
            "pp_pvalue": res.pp_pvalue,
            "za_stat": res.za_stat,
            "za_pvalue": res.za_pvalue,
            "za_break_date": res.za_break_date,
            "conclusion": res.conclusion,
        })
    stationarity_df = pd.DataFrame(stationarity_rows)
    out_dir = _PROJECT_ROOT / "outputs" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    stationarity_df.to_csv(out_dir / "lc_v1_stationarity.csv", index=False)
    logger.info("Wrote %s", out_dir / "lc_v1_stationarity.csv")

    # ------------------------------------------------------------------
    # 2. VIF + correlation + eigenvalues on 5-component panel
    # ------------------------------------------------------------------
    logger.info("Computing VIF / correlation / eigenvalues on 5-component panel...")
    mc = compute_vif_matrix(components)
    vif_rows: list[dict[str, object]] = []
    for name in mc.component_names:
        # max_corr_with_others = max |corr| excluding self
        row_corr = mc.correlation_matrix.loc[name].copy()
        row_corr[name] = 0.0
        max_corr = float(row_corr.abs().max())
        vif_rows.append({
            "component": name,
            "vif": mc.vif[name],
            "max_corr_with_others": max_corr,
            "multicollinearity_flag": mc.multicollinearity_flags[name],
        })
    pd.DataFrame(vif_rows).to_csv(
        out_dir / "lc_v1_diagnostics.csv", index=False,
    )
    logger.info("Wrote %s", out_dir / "lc_v1_diagnostics.csv")

    mc.correlation_matrix.to_csv(out_dir / "lc_v1_component_correlation_matrix.csv")
    logger.info("Wrote %s", out_dir / "lc_v1_component_correlation_matrix.csv")

    eig_df = pd.DataFrame({
        "eigenvalue": mc.eigenvalues,
        "proportion": mc.eigenvalue_proportions,
        "cumulative": mc.eigenvalue_cumulative,
    })
    eig_df.to_csv(out_dir / "lc_v1_component_eigenvalues.csv", index=False)
    logger.info("Wrote %s", out_dir / "lc_v1_component_eigenvalues.csv")

    # ------------------------------------------------------------------
    # 3. Bai-Perron breaks on 3 composites
    # ------------------------------------------------------------------
    logger.info("Running Bai-Perron multiple-break tests on 3 composites...")
    bp_rows: list[dict[str, object]] = []
    for col in ("LC_FULL", "LC_TIER2", "LC_DEEP"):
        s = composites[col].dropna()
        result = run_bai_perron_breaks(s, col, max_breaks=5, min_segment_size=30)
        if result.n_breaks_detected == 0:
            bp_rows.append({
                "series_name": col,
                "n_breaks_detected": 0,
                "break_index": "",
                "break_date": "",
                "break_ci_low": "",
                "break_ci_high": "",
                "regime_pre_mean": "",
                "regime_post_mean": "",
            })
        else:
            for b in result.breaks:
                bp_rows.append({
                    "series_name": col,
                    "n_breaks_detected": result.n_breaks_detected,
                    "break_index": b["break_index"],
                    "break_date": b["break_date"],
                    "break_ci_low": "",  # Bai-Perron CI not implemented in Session 5 module
                    "break_ci_high": "",
                    "regime_pre_mean": b["regime_pre_mean"],
                    "regime_post_mean": b["regime_post_mean"],
                })
    pd.DataFrame(bp_rows).to_csv(
        out_dir / "lc_v1_bai_perron_breaks.csv", index=False,
    )
    logger.info("Wrote %s", out_dir / "lc_v1_bai_perron_breaks.csv")

    # Console summary.
    print("\n" + "=" * 80)
    print("LC v1.0 DIAGNOSTICS  -  STATIONARITY")
    print("=" * 80)
    with pd.option_context("display.float_format", lambda x: f"{x:.4f}",
                           "display.max_columns", 30):
        print(
            stationarity_df[
                ["series_name", "n_obs", "adf_pvalue", "kpss_pvalue",
                 "pp_pvalue", "za_pvalue", "conclusion"]
            ].to_string(index=False)
        )
    print()
    print("=" * 80)
    print("LC v1.0 DIAGNOSTICS  -  VIF / MULTICOLLINEARITY")
    print("=" * 80)
    with pd.option_context("display.float_format", lambda x: f"{x:.4f}"):
        print(pd.DataFrame(vif_rows).to_string(index=False))
    print()
    print("=" * 80)
    print("LC v1.0 DIAGNOSTICS  -  BAI-PERRON BREAKS")
    print("=" * 80)
    print(pd.DataFrame(bp_rows).to_string(index=False))
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
