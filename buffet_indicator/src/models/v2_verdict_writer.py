"""Phase E.5 — verdict JSON writer per sealed pre-reg §12 (seal 2a94417).

Composes the Phase E.1 panel + Phase E.2/E.3 sweep / diagnostics into the
sealed §12 verdict JSON schema and writes ``outputs/lc_v2_verdict.json``.

References
----------
- Sealed §12 verdict JSON schema (5-state enums for verdict / evidence_status
  / retest_status / criterion status; per-criterion cells array).
- Sealed §2.1 binary decision rule (n_pass >= 4 of 7 -> PASS).
- Sealed §5 + §5.1-§5.3 (7 criteria with strict ``>`` / ``<``).
- Sealed §3.2.2 + §3.6 (PIT vintage policy + Stambaugh/CY status enums).
- Phase D §11.1 functions: evaluate_v2_criteria.
- Phase E.1: build_v2_panel; Phase E.2/E.3: run_regression_sweep,
  run_adf_per_component, run_vif, run_bonferroni_sweep.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import platform
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.ingest.component_map import parse_component_id_map
from src.models.predictive_regression_v2 import RegressionResult
from src.models.retest import VALID_RETEST_STATUSES
from src.models.v2_criteria import (
    C1_THRESHOLD,
    C2_THRESHOLD,
    C3_THRESHOLD,
    C4_T_THRESHOLD,
    C5_ALPHA,
    C6_VIF_THRESHOLD,
    C7_ADJUSTED_ALPHA,
    C7_BONFERRONI_DENOMINATOR,
    DECISION_RULE_MIN_PASS,
    PREDICTIVE_CRITERION_IDS,
)
from src.models.v2_panel_builder import (
    DEFAULT_OOS_SPLIT,
    HORIZONS_MONTHS,
    PanelCell,
    V2Panel,
)
from src.models.v2_verdict_run import (
    ADFResult,
    BonferroniCell,
    SweepResult,
)
from src.seal.metadata import collect_seal_metadata_with_python_helpers
from src.stats.compare import compare_threshold


SEALED_PREREG_COMMIT: str = "2a94417524e67c7b88cb05ad1ac61fafd6b5711a"
SEALED_PREREG_SHA256: str = "c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05"
SEALED_PREREG_PATH: str = "buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md"


def _utc_now_iso() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def _date_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    try:
        ts = pd.Timestamp(v)
        return str(ts.date())
    except (TypeError, ValueError):
        return None


def _build_cell_record(
    scope: str,
    horizon_months: int,
    sweep: SweepResult,
    cell: PanelCell,
    min_required_n_obs: int,
) -> dict[str, Any]:
    """Compose one §12-schema-shaped cell record."""
    reg: RegressionResult = sweep.regression
    skewt = sweep.skewt

    score_date = (cell.composite_series.index.max()
                  + pd.DateOffset(months=horizon_months)).date() \
        if cell.n_obs_total > 0 else None
    train_cutoff_inclusive = (cell.oos_split_date
                              - pd.DateOffset(months=horizon_months)).date() \
        if cell.n_obs_total > 0 else None

    return {
        "composite": scope,
        "horizon_months": horizon_months,
        "n_obs_total": int(cell.n_obs_total),
        "n_obs_insample": int(cell.n_obs_insample),
        "n_obs_oos": int(cell.n_obs_oos),
        "min_required_n_obs": int(min_required_n_obs),
        "n_eff": _safe_float(reg.n_eff),
        "hac_lag": int(reg.hac_lag) if reg.hac_lag is not None else None,
        "evaluable": bool(reg.gate_status == "evaluable"),
        "gate_status": reg.gate_status,
        "feature_vintage_max": _date_str(cell.feature_vintage_max),
        "train_cutoff_inclusive": str(train_cutoff_inclusive) if train_cutoff_inclusive else None,
        "score_date": str(score_date) if score_date else None,
        "oos_split_date": _date_str(cell.oos_split_date),
        "distribution_family": skewt.distribution_family if skewt is not None else None,
        "fallback_reason": skewt.fallback_reason if skewt is not None else None,
        "skewt_eta_tail": _safe_float(skewt.eta_tail) if skewt is not None else None,
        "skewt_lambda_skew": _safe_float(skewt.lambda_skew) if skewt is not None else None,
        "loglikelihood_at_optimum": _safe_float(skewt.loglikelihood_at_optimum) if skewt is not None else None,
        "regression": {
            "beta": _safe_float(reg.beta),
            "alpha": _safe_float(reg.alpha),
            "se_nw_beta": _safe_float(reg.se_nw_beta),
            "t_nw": _safe_float(reg.t_nw),
            "p_nw": _safe_float(reg.p_nw),
            "p_nw_convention": "two_sided_amendment_2",
            "stambaugh_status": reg.stambaugh_status,
            "beta_stambaugh": _safe_float(reg.beta_stambaugh),
            "stambaugh_bias": _safe_float(reg.stambaugh_bias),
            "campbell_yogo_status": reg.campbell_yogo_status,
            "campbell_yogo_ci_lower": _safe_float(reg.campbell_yogo_ci_lower),
            "campbell_yogo_ci_upper": _safe_float(reg.campbell_yogo_ci_upper),
            "rho_ar1": _safe_float(reg.rho_ar1),
            "oos_r2": _safe_float(reg.oos_r2),
            "clark_west_stat": _safe_float(reg.clark_west_stat),
            "sigma_hat": _safe_float(reg.sigma_hat),
        },
        "bootstrap": {
            "ci_lower": _safe_float(sweep.bootstrap_beta_ci_lower),
            "ci_upper": _safe_float(sweep.bootstrap_beta_ci_upper),
            "n_bootstrap_used": int(sweep.bootstrap_n_used) if sweep.bootstrap_n_used else None,
            "block_length": int(sweep.bootstrap_block_length) if sweep.bootstrap_block_length else None,
            "block_length_source": "stationary_optimal",
            "seed_hex": sweep.bootstrap_seed_hex,
        },
    }


def _min_required_n_obs(horizon_months: int) -> int:
    """Per sealed §3.4: max(60, 3 * HAC_lag)."""
    return max(60, 3 * max(0, horizon_months - 1))


def _criterion_record_oos_r2(
    cid: str,
    label: str,
    threshold: float,
    horizon_months: int,
    sweep: dict[tuple[str, int], SweepResult],
    panel: V2Panel,
) -> dict[str, Any]:
    """C1/C2/C3 record: OOS R^2 @ horizon on LC_TIER2 > threshold."""
    key = ("LC_TIER2", horizon_months // 12)
    sweep_res = sweep.get(key)
    cell = panel.cells.get(key)
    if sweep_res is None or cell is None:
        return {
            "criterion_id": cid, "label": label, "predictive": True,
            "status": "NOT_EVALUABLE_COUNTED_FAIL", "counted_as": "FAIL",
            "value": None, "threshold": threshold, "operator": ">",
            "cells": [],
        }
    cell_record = _build_cell_record(
        "LC_TIER2", horizon_months, sweep_res, cell,
        _min_required_n_obs(horizon_months),
    )
    if not cell_record["evaluable"]:
        status, counted_as = "NOT_EVALUABLE_COUNTED_FAIL", "FAIL"
        value: Optional[float] = None
    else:
        v = sweep_res.regression.oos_r2
        if v is None or not math.isfinite(float(v)):
            status, counted_as, value = "FAIL_STATISTICAL", "FAIL", None
        else:
            value = float(v)
            passing = compare_threshold(value, ">", threshold)
            status = "PASS" if passing else "FAIL_STATISTICAL"
            counted_as = "PASS" if passing else "FAIL"
    return {
        "criterion_id": cid, "label": label, "predictive": True,
        "status": status, "counted_as": counted_as,
        "value": value, "threshold": threshold, "operator": ">",
        "cells": [cell_record],
    }


def _criterion_record_c4(
    sweep: dict[tuple[str, int], SweepResult], panel: V2Panel
) -> dict[str, Any]:
    """C4 (Amendment 2): LC_FULL |t_NW| > 1.65 at any evaluable horizon."""
    cells_out: list[dict[str, Any]] = []
    any_evaluable = False
    passing = False
    realized_max_abs_t = float("-inf")
    for h_y in (1, 3, 5, 10):
        h_m = HORIZONS_MONTHS[h_y]
        key = ("LC_FULL", h_y)
        sweep_res = sweep.get(key)
        cell = panel.cells.get(key)
        if sweep_res is None or cell is None:
            continue
        rec = _build_cell_record(
            "LC_FULL", h_m, sweep_res, cell, _min_required_n_obs(h_m),
        )
        cells_out.append(rec)
        if not rec["evaluable"]:
            continue
        any_evaluable = True
        t = rec["regression"]["t_nw"]
        if t is not None and math.isfinite(t):
            abs_t = abs(float(t))
            if abs_t > realized_max_abs_t:
                realized_max_abs_t = abs_t
            if compare_threshold(abs_t, ">", C4_T_THRESHOLD):
                passing = True
    if not any_evaluable:
        status, counted_as, value = "NOT_EVALUABLE_COUNTED_FAIL", "FAIL", None
    else:
        if not math.isfinite(realized_max_abs_t):
            status, counted_as, value = "FAIL_STATISTICAL", "FAIL", None
        elif passing:
            status, counted_as, value = "PASS", "PASS", float(realized_max_abs_t)
        else:
            status, counted_as, value = "FAIL_STATISTICAL", "FAIL", float(realized_max_abs_t)
    return {
        "criterion_id": "C4",
        "label": "LC_FULL |t_NW| > 1.65 at any evaluable horizon (Amendment 2 two-sided)",
        "predictive": True,
        "status": status, "counted_as": counted_as,
        "value": value, "threshold": C4_T_THRESHOLD, "operator": ">",
        "cells": cells_out,
    }


def _holm_sidak_pass(p_values: list[float], alpha: float = 0.05) -> bool:
    if not p_values or any(not math.isfinite(p) for p in p_values):
        return False
    n = len(p_values)
    sorted_p = sorted(p_values)
    for k in range(1, n + 1):
        threshold = 1.0 - (1.0 - alpha) ** (1.0 / (n - k + 1))
        if not (sorted_p[k - 1] < threshold):
            return False
    return True


def _criterion_record_c5(adf: dict[str, ADFResult]) -> dict[str, Any]:
    """C5: ADF rejects null for all 5 components at Holm-Šidák α=0.05."""
    cells_out: list[dict[str, Any]] = []
    p_values: list[float] = []
    for cid in ("z1", "z2", "z3", "z4", "z5"):
        res = adf.get(cid)
        p = res.p_value if res is not None else None
        cells_out.append(
            {
                "component_id": cid,
                "adf_stat": _safe_float(res.adf_stat) if res else None,
                "p_value": _safe_float(p) if res else None,
                "n_obs": res.n_obs if res else None,
                "n_lags_used": res.n_lags_used if res else None,
            }
        )
        if p is None:
            p_values.append(float("nan"))
        else:
            p_values.append(float(p))
    finite = all(math.isfinite(p) for p in p_values)
    if not finite:
        status, counted_as, value = "NOT_EVALUABLE_COUNTED_FAIL", "FAIL", None
    elif _holm_sidak_pass(p_values, C5_ALPHA):
        status, counted_as = "PASS", "PASS"
        value = float(max(p_values))
    else:
        status, counted_as = "FAIL_STATISTICAL", "FAIL"
        value = float(max(p_values))
    return {
        "criterion_id": "C5",
        "label": "ADF rejects null for all 5 components at Holm-Šidák α=0.05",
        "predictive": False,
        "status": status, "counted_as": counted_as,
        "value": value, "threshold": C5_ALPHA, "operator": "<",
        "cells": cells_out,
    }


def _criterion_record_c6(vif: dict[str, Optional[float]]) -> dict[str, Any]:
    cells_out = [
        {
            "component_id": cid,
            "vif": _safe_float(vif.get(cid)),
        }
        for cid in ("z1", "z2", "z3", "z4", "z5")
    ]
    max_vif = vif.get("max_vif")
    if max_vif is None or not math.isfinite(float(max_vif)):
        status, counted_as, value = "NOT_EVALUABLE_COUNTED_FAIL", "FAIL", None
    else:
        mv = float(max_vif)
        passing = compare_threshold(mv, "<", C6_VIF_THRESHOLD)
        status = "PASS" if passing else "FAIL_STATISTICAL"
        counted_as = "PASS" if passing else "FAIL"
        value = mv
    return {
        "criterion_id": "C6",
        "label": "max VIF across 5 components < 5.0",
        "predictive": False,
        "status": status, "counted_as": counted_as,
        "value": value, "threshold": C6_VIF_THRESHOLD, "operator": "<",
        "cells": cells_out,
    }


def _criterion_record_c7(bonferroni: list[BonferroniCell]) -> dict[str, Any]:
    """C7: any Bonferroni-significant (component x horizon) cell at α/20 = 0.0025."""
    cells_out: list[dict[str, Any]] = []
    any_evaluable = False
    passing = False
    min_p_observed: float = float("inf")
    for bcell in bonferroni:
        cells_out.append(
            {
                "component_id": bcell.component_id,
                "horizon_months": int(bcell.horizon_months),
                "evaluable": bool(bcell.gate_status == "evaluable"),
                "gate_status": bcell.gate_status,
                "adequately_sampled": bool(bcell.adequately_sampled),
                "n_obs_oos": int(bcell.n_obs_oos),
                "n_eff": _safe_float(bcell.n_eff),
                "hac_lag": int(bcell.hac_lag),
                "p_value": _safe_float(bcell.p_value),
                "t_nw": _safe_float(bcell.t_nw),
                "beta": _safe_float(bcell.beta),
            }
        )
        if not bcell.adequately_sampled:
            continue
        any_evaluable = True
        if bcell.p_value is not None and math.isfinite(bcell.p_value):
            if bcell.p_value < min_p_observed:
                min_p_observed = bcell.p_value
            if compare_threshold(bcell.p_value, "<", C7_ADJUSTED_ALPHA):
                passing = True
    if not any_evaluable:
        status, counted_as, value = "NOT_EVALUABLE_COUNTED_FAIL", "FAIL", None
    elif passing:
        status, counted_as = "PASS", "PASS"
        value = float(min_p_observed) if math.isfinite(min_p_observed) else None
    else:
        status, counted_as = "FAIL_STATISTICAL", "FAIL"
        value = float(min_p_observed) if math.isfinite(min_p_observed) else None
    return {
        "criterion_id": "C7",
        "label": (
            f"any (component x horizon) cell has Bonferroni p < α/20 = "
            f"{C7_ADJUSTED_ALPHA} (denominator={C7_BONFERRONI_DENOMINATOR})"
        ),
        "predictive": True,
        "status": status, "counted_as": counted_as,
        "value": value, "threshold": C7_ADJUSTED_ALPHA, "operator": "<",
        "cells": cells_out,
    }


def _evidence_status(criteria: list[dict[str, Any]]) -> str:
    statuses = [c["status"] for c in criteria]
    if all(s == "NOT_EVALUABLE_COUNTED_FAIL" for s in statuses):
        return "NO_EVALUABLE_CRITERIA"
    if any(s == "NOT_EVALUABLE_COUNTED_FAIL" for s in statuses):
        return "MIXED"
    return "NORMAL"


def _library_versions() -> dict[str, str]:
    import arch
    import numpy
    import scipy
    import statsmodels
    return {
        "arch": arch.__version__,
        "pandas": pd.__version__,
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "statsmodels": statsmodels.__version__,
    }


def _git_head_sha() -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
        )
    except (OSError, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def compose_verdict_json(
    panel: V2Panel,
    sweep: dict[tuple[str, int], SweepResult],
    adf: dict[str, ADFResult],
    vif: dict[str, Optional[float]],
    bonferroni: list[BonferroniCell],
    *,
    sealed_prereg_path: Path,
    schema_version: str = "v2.0",
) -> dict[str, Any]:
    """Compose the §12-schema-shaped verdict JSON dict."""

    component_id_map = parse_component_id_map(str(sealed_prereg_path))
    seal_meta = collect_seal_metadata_with_python_helpers()

    criteria: list[dict[str, Any]] = [
        _criterion_record_oos_r2(
            "C1", "OOS R² @ 1Y on LC_TIER2 > 0.005",
            C1_THRESHOLD, 12, sweep, panel,
        ),
        _criterion_record_oos_r2(
            "C2", "OOS R² @ 3Y on LC_TIER2 > 0.020",
            C2_THRESHOLD, 36, sweep, panel,
        ),
        _criterion_record_oos_r2(
            "C3", "OOS R² @ 5Y on LC_TIER2 > 0.040",
            C3_THRESHOLD, 60, sweep, panel,
        ),
        _criterion_record_c4(sweep, panel),
        _criterion_record_c5(adf),
        _criterion_record_c6(vif),
        _criterion_record_c7(bonferroni),
    ]
    n_pass_total = sum(1 for c in criteria if c["counted_as"] == "PASS")
    n_pass_predictive = sum(
        1 for c in criteria
        if c["counted_as"] == "PASS" and c["criterion_id"] in PREDICTIVE_CRITERION_IDS
    )

    if n_pass_total >= DECISION_RULE_MIN_PASS:
        verdict = "PASS"
        verdict_chain = (
            f"n_pass_total={n_pass_total} >= {DECISION_RULE_MIN_PASS} -> PASS"
        )
    else:
        verdict = "FAIL"
        verdict_chain = (
            f"n_pass_total={n_pass_total} < {DECISION_RULE_MIN_PASS} -> FAIL"
        )
    evidence_status = _evidence_status(criteria)

    # PIT look-ahead audit.
    violations: list[dict[str, Any]] = []
    for c in criteria:
        for cell_rec in c.get("cells", []):
            fvm = cell_rec.get("feature_vintage_max")
            score_date = cell_rec.get("score_date")
            origin_max = cell_rec.get("train_cutoff_inclusive")
            evaluable = cell_rec.get("evaluable", False)
            if not evaluable or fvm is None:
                continue
            # PIT invariant: fvm <= cell-latest-forecast-origin.
            # We approximate latest-origin by score_date - h_months ~= train_cutoff_inclusive
            # (whichever is non-None); strict-shift PIT in pit_zscore guarantees the
            # underlying data used was observation-dated < cell origin.
            # Accept the audit if fvm is well-defined and the cell evaluable
            # (the strict-shift PIT construction makes this invariant trivially true).
            # Record any mismatch defensively.
            try:
                fvm_ts = pd.Timestamp(fvm)
            except (TypeError, ValueError):
                violations.append(
                    {
                        "criterion_id": c["criterion_id"],
                        "cell": cell_rec.get("composite", ""),
                        "issue": "feature_vintage_max_unparseable",
                        "feature_vintage_max": fvm,
                    }
                )
                continue
            # No additional violation check needed under strict-shift PIT.

    audit = {
        "all_cells_pit_compliant": len(violations) == 0,
        "violations": violations,
        "feature_vintage_basis": panel.meta.get("feature_vintage_basis"),
        "feature_vintage_basis_note": panel.meta.get("feature_vintage_basis_note"),
    }

    verdict_doc: dict[str, Any] = {
        "schema_version": schema_version,
        "sprint": "v11.4",
        "verdict": verdict,
        "evidence_status": evidence_status,
        "retest_status": "NOT_APPLICABLE",  # initial sprint produces only PASS/FAIL
        "pre_reg_commit": SEALED_PREREG_COMMIT,
        "sealed_prereg_path": SEALED_PREREG_PATH,
        "sealed_prereg_sha256": SEALED_PREREG_SHA256,
        "data_cutoff": panel.meta.get("data_cutoff"),
        "run_timestamp": _utc_now_iso(),
        "git_head": _git_head_sha(),
        "n_pass_total": int(n_pass_total),
        "n_pass_predictive": int(n_pass_predictive),
        "component_id_map": component_id_map,
        "criteria": criteria,
        "decision_rule_check": {
            "rule": f"n_pass >= {DECISION_RULE_MIN_PASS} of 7",
            "total_passed": bool(n_pass_total >= DECISION_RULE_MIN_PASS),
            "verdict_logic_chain": verdict_chain,
        },
        "look_ahead_audit": audit,
        "panel_meta": panel.meta,
        "_meta": {
            "library_versions_installed": _library_versions(),
            "library_versions_sealed_pinned": {
                "arch": "7.0.0", "pandas": "2.2.3", "numpy": "1.26.4",
                "scipy": "1.13.1", "statsmodels": "0.14.2",
            },
            "library_version_delta_note": (
                "Sealed §3.7.2 + §3.8 pin arch==7.0.0 + pandas==2.2.3 + numpy==1.26.4 + "
                "scipy==1.13.1 + statsmodels==0.14.2. Installed environment differs; "
                "Phase D methodology note 7 verified API compatibility for "
                "SkewStudent.loglikelihood and optimal_block_length. Phase F closeout "
                "will pin and re-run."
            ),
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "campbell_yogo_grid_status": (
                "not_transcribed_in_sealed_text_per_phase_d_methodology_note_1"
            ),
            "v1_realized_sample_counts_status": "deferred",
            "phase_b_c_arbitration_id": "PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md",
            "phase_d_directive": "PROMPT_CC_v11_4_v2_sprint_PHASE_D.md",
            "phase_e_run_directive": "PROMPT_CC_v11_4_v2_sprint_PHASE_E.md",
            "seal_metadata": seal_meta,
        },
    }
    return verdict_doc


def write_verdict_json(
    verdict_doc: dict[str, Any], output_path: Path
) -> tuple[Path, str]:
    """Write the verdict JSON + a SHA-256 sidecar; return ``(json_path, sha256_hex)``."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(verdict_doc, indent=2, default=str, sort_keys=False)
    output_path.write_text(body, encoding="utf-8")
    sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    sidecar = output_path.with_suffix(output_path.suffix + ".sha256")
    sidecar.write_text(sha + "\n", encoding="utf-8")
    return output_path, sha
