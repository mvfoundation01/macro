"""v11.2 — Orchestrate V2 metrics + statistical tests CSVs.

Usage:
    python scripts/v11_2_build_v2_outputs.py

Reads V1 Combination monthly returns (emitted by v50 with V11_2_EXPORT_RETURNS=1),
applies the 3 pre-registered MV-Conditional rules, and writes:
  - outputs/quant_engine/latest/v2_latest.csv (3 rules × 8 periods × 5 costs)
  - outputs/quant_engine/latest/v2_statistical_tests.csv (3 rules, JK+RC+Holm)

If the v50 export CSVs are missing, exits with a clear error message.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.quant_engine.mv_conditional import (  # noqa: E402
    QE_LATEST_DIR,
    QUANT_PIPELINE_RESULTS,
    RULE_REGISTRY,
    apply_mv_conditional,
    load_combo_monthly_returns,
    load_mvci_mrc_zscores_monthly,
    load_tbill_monthly_return,
)
from src.quant_engine.stats_v1_v2 import build_v2_statistical_tests_table  # noqa: E402
from src.quant_engine.v2_metrics import build_v2_metrics_table  # noqa: E402


def main() -> int:
    print(f"[v11.2] results dir: {QUANT_PIPELINE_RESULTS}")
    print(f"[v11.2] output dir: {QE_LATEST_DIR}")

    # Build the 120-row metrics CSV.
    print("[v11.2] building v2_latest.csv (3 rules x 8 periods x 5 costs)...")
    metrics_df = build_v2_metrics_table()
    n_valid = metrics_df["cagr"].notna().sum()
    print(f"  -> {len(metrics_df)} rows ({n_valid} non-NaN) "
          f"written to {QE_LATEST_DIR / 'v2_latest.csv'}")

    # Build statistical tests CSV (uses FULL period, 15bps).
    print("[v11.2] building v2_statistical_tests.csv (FULL @ 15bps)...")
    try:
        z = load_mvci_mrc_zscores_monthly()
        combo = None
        for plabel in ("FULL", "FULL_2000"):
            try:
                combo = load_combo_monthly_returns(period_label=plabel, costbps=15)
                break
            except FileNotFoundError:
                continue
        if combo is None:
            print("  WARN no FULL combo monthly returns CSV - skipping stats table",
                  file=sys.stderr)
            return 1
        tbill = load_tbill_monthly_return()

        v2_by_rule: dict[str, pd.Series] = {}
        for rule_name, rule_fn in RULE_REGISTRY.items():
            weights = rule_fn(z["z_mvci"], z["z_mrc"])
            v2_by_rule[rule_name] = apply_mv_conditional(combo, weights, tbill)

        stats_df = build_v2_statistical_tests_table(
            combo_monthly_returns=combo,
            v2_returns_by_rule=v2_by_rule,
            out_path=QE_LATEST_DIR / "v2_statistical_tests.csv",
            n_bootstrap=10_000,
            block_length=6,
        )
        print(f"  -> {len(stats_df)} rows written to {QE_LATEST_DIR / 'v2_statistical_tests.csv'}")
        print()
        print("[v11.2] statistical tests summary:")
        print(stats_df[
            ["rule", "sharpe_v1", "sharpe_v2", "jk_sharpe_diff", "jk_p_value",
             "reality_check_p", "holm_sidak_reject", "passes_falsifiability_sharpe"]
        ].to_string(index=False))
    except Exception as e:
        print(f"  WARN statistical tests failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
