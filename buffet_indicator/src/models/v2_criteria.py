"""LC v2.0 verdict criteria evaluator — DRAFT_v4 §5 + §12 (seal 2a94417).

References
----------
- Sealed pre-reg §5: seven criteria C1..C7, with strict ``>`` / ``<``
  at thresholds (e.g., C4 strict ``>`` at ``t=1.65``).
- Sealed pre-reg §5.1: C4 Amendment 2 — ``|t_NW| > 1.65`` two-sided.
- Sealed pre-reg §5.2: C5 Holm-Šidák multiplicity on ADF (5 components).
- Sealed pre-reg §5.3: C7 Bonferroni denominator = 20 (5 components × 4 horizons).
- Sealed pre-reg §2.1: binary decision rule ``n_pass >= 4 of 7``.
- Sealed pre-reg §12: verdict JSON schema.
- Sealed pre-reg §11.1 line 734: function signature.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd

from src.stats.compare import compare_threshold


# Sealed §5 thresholds.
C1_THRESHOLD: float = 0.005    # OOS R^2 @ 1Y on LC_TIER2
C2_THRESHOLD: float = 0.020    # OOS R^2 @ 3Y on LC_TIER2
C3_THRESHOLD: float = 0.040    # OOS R^2 @ 5Y on LC_TIER2
C4_T_THRESHOLD: float = 1.65   # |t_NW| > 1.65 (Amendment 2)
C5_ALPHA: float = 0.05         # ADF Holm-Šidák alpha
C6_VIF_THRESHOLD: float = 5.0  # max VIF < 5
C7_BONFERRONI_DENOMINATOR: int = 20  # 5 components × 4 horizons (§5.3)
C7_ALPHA: float = 0.05         # uncorrected familywise alpha
C7_ADJUSTED_ALPHA: float = C7_ALPHA / C7_BONFERRONI_DENOMINATOR  # 0.0025

DECISION_RULE_MIN_PASS: int = 4  # n_pass >= 4 -> PASS (§2.1)
"""Binary verdict floor per §2.1: ``n_pass >= 4 of 7``."""

PREDICTIVE_CRITERION_IDS: tuple[str, ...] = ("C1", "C2", "C3", "C4", "C7")
"""§2.1: criteria counted in ``n_pass_predictive`` transparency field."""

CRITERION_STATUSES: frozenset[str] = frozenset(
    {
        "PASS",
        "FAIL_STATISTICAL",
        "NOT_EVALUABLE_COUNTED_FAIL",
        "UNDEFINED_ALL_NOT_EVALUABLE",
    }
)
"""§12 per-criterion status enum."""

EVIDENCE_STATUSES: frozenset[str] = frozenset(
    {"NORMAL", "NO_EVALUABLE_CRITERIA", "MIXED"}
)
"""§12 evidence_status enum."""

VERDICTS: frozenset[str] = frozenset({"PASS", "FAIL", "UNSTABLE"})
"""§12 verdict enum (UNSTABLE only from annual re-test, §6.2)."""


@dataclass(frozen=True)
class VerdictResult:
    """LC v2.0 verdict over the 12 (composite x horizon) panel (§5 + §12).

    Required attributes (scaffold)
    ------------------------------
    verdict : str
        ``"PASS"`` | ``"FAIL"`` | ``"UNSTABLE"`` (§12). Initial sprint
        produces only ``"PASS"``/``"FAIL"``; ``"UNSTABLE"`` is set by the
        annual re-test reversal logic in :mod:`src.models.retest`.
    evidence_status : str
        ``"NORMAL"`` | ``"NO_EVALUABLE_CRITERIA"`` | ``"MIXED"`` (§12).
    n_pass_total : int
        Total criteria with ``counted_as == "PASS"`` (0..7).
    n_pass_predictive : int
        Pass count restricted to predictive criteria
        ({C1, C2, C3, C4, C7}, 0..5).
    criteria : list[dict]
        Per-criterion records per §12 schema.
    """

    verdict: str
    evidence_status: str
    n_pass_total: int
    n_pass_predictive: int
    criteria: list[dict[str, Any]]


def _row_for(
    panel: pd.DataFrame, composite: str, horizon_months: int
) -> Optional[pd.Series]:
    """Locate a single panel row by (composite, horizon_months)."""
    mask = (panel["composite"] == composite) & (
        panel["horizon_months"] == horizon_months
    )
    if not mask.any():
        return None
    return panel.loc[mask].iloc[0]


def _evaluable(row: Optional[pd.Series]) -> bool:
    """A row counts as evaluable iff it exists and is gate_status='evaluable'."""
    if row is None:
        return False
    gate = row.get("gate_status")
    return bool(gate == "evaluable")


def _safe_float(value: Any) -> float:
    """Coerce to float, propagating NaN on None/None-like inputs."""
    if value is None:
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _criterion_status(
    *,
    evaluable: bool,
    threshold_pass: Optional[bool],
) -> tuple[str, str]:
    """Translate (evaluable, threshold_pass) into (§12 status, counted_as).

    Per §3.4 + §12: ``not_evaluable`` cells count as FAIL.
    """
    if not evaluable:
        return "NOT_EVALUABLE_COUNTED_FAIL", "FAIL"
    if threshold_pass is None:
        # Evaluable but undefined (e.g., NaN value) -> counted as FAIL.
        return "FAIL_STATISTICAL", "FAIL"
    if threshold_pass:
        return "PASS", "PASS"
    return "FAIL_STATISTICAL", "FAIL"


def _eval_c1_c2_c3(
    panel: pd.DataFrame,
    criterion_id: str,
    horizon_months: int,
    threshold: float,
) -> dict[str, Any]:
    """C1/C2/C3: OOS R^2 @ {1Y, 3Y, 5Y} on LC_TIER2 > threshold."""
    row = _row_for(panel, "LC_TIER2", horizon_months)
    evaluable = _evaluable(row)
    value: Optional[float] = _safe_float(row["oos_r2"]) if (row is not None and "oos_r2" in row) else float("nan")
    if not math.isfinite(value):
        threshold_pass: Optional[bool] = None
        value = None
    else:
        threshold_pass = compare_threshold(value, ">", threshold)
    status, counted_as = _criterion_status(
        evaluable=evaluable, threshold_pass=threshold_pass
    )
    return {
        "criterion_id": criterion_id,
        "label": f"OOS R² @ {horizon_months // 12}Y on LC_TIER2 > {threshold}",
        "predictive": True,
        "status": status,
        "counted_as": counted_as,
        "value": value,
        "threshold": threshold,
        "operator": ">",
        "cells": [
            {
                "composite": "LC_TIER2",
                "horizon_months": horizon_months,
                "evaluable": evaluable,
                "n_obs_oos": int(row["n_obs_oos"])
                if (row is not None and "n_obs_oos" in row and math.isfinite(_safe_float(row["n_obs_oos"])))
                else None,
            }
        ],
    }


def _eval_c4(panel: pd.DataFrame) -> dict[str, Any]:
    """C4 (Amendment 2): LC_FULL ``|t_NW| > 1.65`` at any evaluable horizon."""
    cells: list[dict[str, Any]] = []
    any_evaluable = False
    passing = False
    realized_max_abs_t: float = float("-inf")
    for h in (12, 36, 60, 120):
        row = _row_for(panel, "LC_FULL", h)
        evaluable = _evaluable(row)
        t_value = _safe_float(row["t_nw"]) if (row is not None and "t_nw" in row) else float("nan")
        cells.append(
            {
                "composite": "LC_FULL",
                "horizon_months": h,
                "evaluable": evaluable,
                "t_nw": float(t_value) if math.isfinite(t_value) else None,
            }
        )
        if not evaluable:
            continue
        any_evaluable = True
        if math.isfinite(t_value):
            abs_t = abs(t_value)
            if abs_t > realized_max_abs_t:
                realized_max_abs_t = abs_t
            if compare_threshold(abs_t, ">", C4_T_THRESHOLD):
                passing = True
    # Decide status.
    if not any_evaluable:
        status = "NOT_EVALUABLE_COUNTED_FAIL"
        counted_as = "FAIL"
        value: Optional[float] = None
    else:
        threshold_pass = passing
        if not math.isfinite(realized_max_abs_t):
            realized_max_abs_t = float("nan")
            threshold_pass = False
        status, counted_as = _criterion_status(
            evaluable=True, threshold_pass=threshold_pass
        )
        value = float(realized_max_abs_t) if math.isfinite(realized_max_abs_t) else None
    return {
        "criterion_id": "C4",
        "label": "LC_FULL |t_NW| > 1.65 at any evaluable horizon (Amendment 2)",
        "predictive": True,
        "status": status,
        "counted_as": counted_as,
        "value": value,
        "threshold": C4_T_THRESHOLD,
        "operator": ">",
        "cells": cells,
    }


def _holm_sidak_step_down(p_values: list[float], alpha: float) -> bool:
    """Holm-Šidák step-down: pass iff ALL ordered p_(k) < 1 - (1 - alpha)^(1/(n-k+1))."""
    finite = [(i, p) for i, p in enumerate(p_values) if math.isfinite(p)]
    if len(finite) != len(p_values):
        return False
    n = len(p_values)
    sorted_p = sorted(p_values)
    for k in range(1, n + 1):
        threshold = 1.0 - (1.0 - alpha) ** (1.0 / (n - k + 1))
        if not (sorted_p[k - 1] < threshold):
            return False
    return True


def _eval_c5(panel: pd.DataFrame) -> dict[str, Any]:
    """C5: ADF rejects null for all 5 components at Holm-Šidák alpha=0.05."""
    p_values: list[float] = []
    cells: list[dict[str, Any]] = []
    for cid in ("z1", "z2", "z3", "z4", "z5"):
        row = panel.loc[panel.get("component_id", pd.Series(dtype=str)) == cid]
        if row.empty:
            p = float("nan")
        else:
            p = _safe_float(row.iloc[0].get("adf_pvalue"))
        cells.append({"component_id": cid, "adf_pvalue": float(p) if math.isfinite(p) else None})
        p_values.append(p)
    finite = all(math.isfinite(p) for p in p_values)
    if not finite or len(p_values) != 5:
        status, counted_as = "NOT_EVALUABLE_COUNTED_FAIL", "FAIL"
        value: Optional[float] = None
    else:
        if _holm_sidak_step_down(p_values, C5_ALPHA):
            status, counted_as = "PASS", "PASS"
        else:
            status, counted_as = "FAIL_STATISTICAL", "FAIL"
        value = max(p_values)
    return {
        "criterion_id": "C5",
        "label": "ADF rejects null for all 5 components, Holm-Šidák α=0.05",
        "predictive": False,
        "status": status,
        "counted_as": counted_as,
        "value": value,
        "threshold": C5_ALPHA,
        "operator": "<",
        "cells": cells,
    }


def _eval_c6(panel: pd.DataFrame) -> dict[str, Any]:
    """C6: max VIF across 5 components < 5."""
    vif_value: Optional[float] = None
    if "max_vif" in panel.columns:
        finite_vif = panel["max_vif"].dropna()
        if not finite_vif.empty:
            vif_value = float(finite_vif.max())
    if vif_value is None or not math.isfinite(vif_value):
        status, counted_as = "NOT_EVALUABLE_COUNTED_FAIL", "FAIL"
        value: Optional[float] = None
    else:
        threshold_pass = compare_threshold(vif_value, "<", C6_VIF_THRESHOLD)
        status = "PASS" if threshold_pass else "FAIL_STATISTICAL"
        counted_as = "PASS" if threshold_pass else "FAIL"
        value = vif_value
    return {
        "criterion_id": "C6",
        "label": "max VIF across 5 components < 5",
        "predictive": False,
        "status": status,
        "counted_as": counted_as,
        "value": value,
        "threshold": C6_VIF_THRESHOLD,
        "operator": "<",
        "cells": [],
    }


def _eval_c7(panel: pd.DataFrame) -> dict[str, Any]:
    """C7: any (component × horizon) cell has Bonferroni p < α/20 = 0.0025.

    Cells failing the §3.4 sample gate count as FAIL (do NOT reduce the
    denominator, per §5.3).
    """
    cells: list[dict[str, Any]] = []
    any_evaluable = False
    passing = False
    min_p_observed: float = float("inf")
    for cid in ("z1", "z2", "z3", "z4", "z5"):
        for h in (12, 36, 60, 120):
            mask = (
                (panel.get("component_id", pd.Series(dtype=str)) == cid)
                & (panel.get("horizon_months", pd.Series(dtype=int)) == h)
            )
            if not mask.any():
                cells.append(
                    {
                        "component_id": cid,
                        "horizon_months": h,
                        "evaluable": False,
                        "p_value": None,
                    }
                )
                continue
            row = panel.loc[mask].iloc[0]
            evaluable = bool(row.get("gate_status") == "evaluable")
            p_raw = _safe_float(row.get("p_value"))
            cells.append(
                {
                    "component_id": cid,
                    "horizon_months": h,
                    "evaluable": evaluable,
                    "p_value": float(p_raw) if math.isfinite(p_raw) else None,
                }
            )
            if not evaluable:
                continue
            any_evaluable = True
            if math.isfinite(p_raw):
                if p_raw < min_p_observed:
                    min_p_observed = p_raw
                if compare_threshold(p_raw, "<", C7_ADJUSTED_ALPHA):
                    passing = True
    if not any_evaluable:
        status, counted_as = "NOT_EVALUABLE_COUNTED_FAIL", "FAIL"
        value: Optional[float] = None
    elif passing:
        status, counted_as = "PASS", "PASS"
        value = float(min_p_observed) if math.isfinite(min_p_observed) else None
    else:
        status, counted_as = "FAIL_STATISTICAL", "FAIL"
        value = float(min_p_observed) if math.isfinite(min_p_observed) else None
    return {
        "criterion_id": "C7",
        "label": f"any (component × horizon) cell has p < α/20 = {C7_ADJUSTED_ALPHA}",
        "predictive": True,
        "status": status,
        "counted_as": counted_as,
        "value": value,
        "threshold": C7_ADJUSTED_ALPHA,
        "operator": "<",
        "cells": cells,
    }


def _evidence_status(criteria: list[dict[str, Any]]) -> str:
    """Per §12: evidence_status from per-criterion §12 statuses."""
    statuses = [c["status"] for c in criteria]
    if all(s == "NOT_EVALUABLE_COUNTED_FAIL" for s in statuses):
        return "NO_EVALUABLE_CRITERIA"
    if any(s == "NOT_EVALUABLE_COUNTED_FAIL" for s in statuses):
        return "MIXED"
    return "NORMAL"


def evaluate_v2_criteria(panel: pd.DataFrame) -> VerdictResult:
    """Evaluate the seven v2.0 criteria over the panel.

    Per §5 + §2.1 + §12. ``n_pass >= 4 of 7 -> PASS``.

    Panel shape (caller-prepared)
    -----------------------------
    A long-form DataFrame containing rows for each (composite × horizon)
    regression cell and each (component × horizon) C7 cell. Required
    columns (best-effort accessed; missing columns degrade to FAIL):

    - ``composite`` : str in {LC_FULL, LC_TIER2, LC_DEEP}
    - ``horizon_months`` : int in {12, 36, 60, 120}
    - ``component_id`` : str in {z1..z5} (C5 + C7)
    - ``gate_status`` : str in {evaluable, not_evaluable} (§3.4)
    - ``n_obs_oos`` : int
    - ``oos_r2`` : float (C1/C2/C3)
    - ``t_nw`` : float (C4)
    - ``p_value`` : float (C7 component cells)
    - ``adf_pvalue`` : float (C5 per-component rows)
    - ``max_vif`` : float (C6; can be a single-value column)

    Parameters
    ----------
    panel : pd.DataFrame
        12-cell + 5-component long-form panel.

    Returns
    -------
    VerdictResult

    References
    ----------
    Sealed pre-reg §2.1 + §3.4 + §5 + §12 + §11.1 line 734.
    Tests: ``T12``, ``T13``, ``T14``.
    """
    if "composite" not in panel.columns:
        panel = panel.assign(composite=pd.Series(dtype=str))
    if "horizon_months" not in panel.columns:
        panel = panel.assign(horizon_months=pd.Series(dtype=int))

    criteria = [
        _eval_c1_c2_c3(panel, "C1", 12, C1_THRESHOLD),
        _eval_c1_c2_c3(panel, "C2", 36, C2_THRESHOLD),
        _eval_c1_c2_c3(panel, "C3", 60, C3_THRESHOLD),
        _eval_c4(panel),
        _eval_c5(panel),
        _eval_c6(panel),
        _eval_c7(panel),
    ]
    n_pass_total = sum(1 for c in criteria if c["counted_as"] == "PASS")
    n_pass_predictive = sum(
        1
        for c in criteria
        if c["counted_as"] == "PASS" and c["criterion_id"] in PREDICTIVE_CRITERION_IDS
    )
    verdict = "PASS" if n_pass_total >= DECISION_RULE_MIN_PASS else "FAIL"
    evidence_status = _evidence_status(criteria)
    return VerdictResult(
        verdict=verdict,
        evidence_status=evidence_status,
        n_pass_total=int(n_pass_total),
        n_pass_predictive=int(n_pass_predictive),
        criteria=criteria,
    )
