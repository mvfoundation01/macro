"""Phase E orchestration entry-point — produces ``outputs/lc_v2_verdict.json``.

Usage::

    python -m src.models.v2_run_verdict \
        [--n-bootstrap 50000] \
        [--output outputs/lc_v2_verdict.json]

Composes Phase E.1 panel + E.2 sweep + E.3 diagnostics + E.4 evaluation
+ E.5 JSON writer + E.6 PIT audit per sealed pre-reg §3-§12.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from src.stats.bootstrap_policy import VERDICT_N_BOOTSTRAP
from src.models.v2_panel_builder import build_v2_panel
from src.models.v2_verdict_run import (
    compose_criteria_panel,
    run_adf_per_component,
    run_bonferroni_sweep,
    run_regression_sweep,
    run_vif,
)
from src.models.v2_verdict_writer import (
    SEALED_PREREG_PATH,
    compose_verdict_json,
    write_verdict_json,
)


def run_verdict(
    *,
    n_bootstrap: int = VERDICT_N_BOOTSTRAP,
    output_path: Path = Path("outputs/lc_v2_verdict.json"),
    sealed_prereg_path: Optional[Path] = None,
    master_seed: int = 42,
) -> tuple[Path, dict, str]:
    """Run the full verdict-bearing pipeline and write the JSON output.

    Returns
    -------
    (output_path, verdict_doc, sha256_hex)
    """
    if sealed_prereg_path is None:
        sealed_prereg_path = Path(SEALED_PREREG_PATH)
        if not sealed_prereg_path.exists():
            sealed_prereg_path = (
                Path(__file__).resolve().parents[2]
                / "specs"
                / "MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md"
            )

    print("[E.1] building panel ...", flush=True)
    panel = build_v2_panel()

    print(f"[E.2] regression sweep + skewed-t + bootstrap (n={n_bootstrap}) ...", flush=True)
    sweep = run_regression_sweep(
        panel,
        n_bootstrap=int(n_bootstrap),
        fit_skewt=True,
        bootstrap_beta=True,
        master_seed=int(master_seed),
    )

    print("[E.3] diagnostics (ADF + VIF + Bonferroni) ...", flush=True)
    adf = run_adf_per_component(panel)
    vif = run_vif(panel)
    bonferroni = run_bonferroni_sweep(panel, oos_split=panel.cells[("LC_FULL", 1)].oos_split_date)

    print("[E.5] composing verdict JSON ...", flush=True)
    verdict_doc = compose_verdict_json(
        panel, sweep, adf, vif, bonferroni,
        sealed_prereg_path=sealed_prereg_path,
    )

    json_path, sha = write_verdict_json(verdict_doc, output_path)
    print(f"[E.5] wrote verdict JSON: {json_path}")
    print(f"[E.5] sha256: {sha}")
    print(f"[verdict] outcome={verdict_doc['verdict']} "
          f"n_pass={verdict_doc['n_pass_total']}/7 "
          f"evidence_status={verdict_doc['evidence_status']}")
    return json_path, verdict_doc, sha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the v2.0 verdict-bearing pipeline.",
    )
    parser.add_argument(
        "--n-bootstrap", type=int, default=VERDICT_N_BOOTSTRAP,
        help="Bootstrap reps (sealed default 50000).",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/lc_v2_verdict.json"),
    )
    parser.add_argument("--master-seed", type=int, default=42)
    args = parser.parse_args(argv)
    run_verdict(
        n_bootstrap=args.n_bootstrap,
        output_path=args.output,
        master_seed=args.master_seed,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
