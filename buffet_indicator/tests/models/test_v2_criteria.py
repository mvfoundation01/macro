"""§11.2 T12+T13+T14 — v2.0 verdict criteria evaluator.
DRAFT_v4 §5 + §12 (seal 2a94417).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402

from src.models.v2_criteria import (  # noqa: E402
    C7_ADJUSTED_ALPHA,
    C7_BONFERRONI_DENOMINATOR,
    CRITERION_STATUSES,
    EVIDENCE_STATUSES,
    VERDICTS,
    VerdictResult,
    evaluate_v2_criteria,
)


def _row(**kwargs) -> dict:
    """Helper to build a panel row with sensible defaults."""
    base = {
        "composite": "",
        "horizon_months": 12,
        "component_id": "",
        "gate_status": "evaluable",
        "n_obs_oos": 200,
        "oos_r2": None,
        "t_nw": None,
        "p_value": None,
        "adf_pvalue": None,
        "max_vif": None,
    }
    base.update(kwargs)
    return base


def _all_pass_panel() -> pd.DataFrame:
    """Synthetic panel where all 7 criteria PASS."""
    rows = [
        # C1: LC_TIER2 @ 1Y OOS R^2 > 0.005
        _row(composite="LC_TIER2", horizon_months=12, oos_r2=0.02),
        # C2: LC_TIER2 @ 3Y OOS R^2 > 0.020
        _row(composite="LC_TIER2", horizon_months=36, oos_r2=0.05),
        # C3: LC_TIER2 @ 5Y OOS R^2 > 0.040
        _row(composite="LC_TIER2", horizon_months=60, oos_r2=0.08),
        # C4: LC_FULL at any horizon |t_NW| > 1.65
        _row(composite="LC_FULL", horizon_months=12, t_nw=2.5),
        _row(composite="LC_FULL", horizon_months=36, t_nw=1.0),
        _row(composite="LC_FULL", horizon_months=60, t_nw=0.5),
        _row(composite="LC_FULL", horizon_months=120, gate_status="not_evaluable"),
    ]
    # C5: 5 components with ADF p-values that pass Holm-Šidák at α=0.05.
    adf_p = [0.0001, 0.0005, 0.001, 0.002, 0.005]
    for cid, p in zip(("z1", "z2", "z3", "z4", "z5"), adf_p):
        rows.append(_row(component_id=cid, adf_pvalue=p, horizon_months=0))
    # C6: max VIF < 5
    rows.append(_row(max_vif=2.5))
    # C7: 20 cells (5 components x 4 horizons), at least one passes.
    for cid in ("z1", "z2", "z3", "z4", "z5"):
        for h in (12, 36, 60, 120):
            p_val = 0.0001 if (cid == "z1" and h == 12) else 0.5
            rows.append(
                _row(
                    component_id=cid,
                    horizon_months=h,
                    p_value=p_val,
                    gate_status="evaluable",
                )
            )
    return pd.DataFrame(rows)


def _all_fail_panel() -> pd.DataFrame:
    """Synthetic panel where all 7 criteria FAIL."""
    rows = [
        _row(composite="LC_TIER2", horizon_months=12, oos_r2=-0.01),
        _row(composite="LC_TIER2", horizon_months=36, oos_r2=-0.01),
        _row(composite="LC_TIER2", horizon_months=60, oos_r2=-0.01),
        _row(composite="LC_FULL", horizon_months=12, t_nw=0.5),
        _row(composite="LC_FULL", horizon_months=36, t_nw=-1.0),
        _row(composite="LC_FULL", horizon_months=60, t_nw=0.0),
        _row(composite="LC_FULL", horizon_months=120, gate_status="not_evaluable"),
    ]
    # C5: ADF doesn't reject for all.
    for cid in ("z1", "z2", "z3", "z4", "z5"):
        rows.append(_row(component_id=cid, adf_pvalue=0.5, horizon_months=0))
    # C6: max VIF >= 5
    rows.append(_row(max_vif=8.0))
    # C7: no cells pass Bonferroni 0.0025
    for cid in ("z1", "z2", "z3", "z4", "z5"):
        for h in (12, 36, 60, 120):
            rows.append(
                _row(component_id=cid, horizon_months=h, p_value=0.5)
            )
    return pd.DataFrame(rows)


def test_all_seven_criteria_known_pass_and_fail() -> None:
    """Synthetic all-pass / all-fail fixtures yield correct verdict logic.

    References: DRAFT_v4 §5 + sealed pre-reg §11.2 T12.
    """
    panel_pass = _all_pass_panel()
    result_pass = evaluate_v2_criteria(panel_pass)
    assert isinstance(result_pass, VerdictResult)
    assert result_pass.verdict == "PASS"
    assert result_pass.verdict in VERDICTS
    assert result_pass.evidence_status in EVIDENCE_STATUSES
    assert result_pass.n_pass_total == 7
    # Predictive subset: C1, C2, C3, C4, C7 (5 predictive criteria) all pass.
    assert result_pass.n_pass_predictive == 5
    for c in result_pass.criteria:
        assert c["status"] in CRITERION_STATUSES

    panel_fail = _all_fail_panel()
    result_fail = evaluate_v2_criteria(panel_fail)
    assert result_fail.verdict == "FAIL"
    assert result_fail.n_pass_total == 0
    assert result_fail.n_pass_predictive == 0


def test_criterion_4_strict_t_boundary() -> None:
    """t=1.65 -> FAIL; t=1.6501 -> PASS (STRICT > at C4 t threshold).

    References: DRAFT_v4 §5.1 (C4 strict t-boundary) + sealed pre-reg §11.2 T13.
    """
    # Build a panel with LC_FULL t exactly at 1.65 at one horizon; others not evaluable.
    rows_boundary = [
        _row(composite="LC_FULL", horizon_months=12, t_nw=1.65),
        _row(composite="LC_FULL", horizon_months=36, gate_status="not_evaluable"),
        _row(composite="LC_FULL", horizon_months=60, gate_status="not_evaluable"),
        _row(composite="LC_FULL", horizon_months=120, gate_status="not_evaluable"),
        # Fill C1/C2/C3 / C5 / C6 / C7 with fail panels so we focus on C4.
        _row(composite="LC_TIER2", horizon_months=12, oos_r2=-1.0),
        _row(composite="LC_TIER2", horizon_months=36, oos_r2=-1.0),
        _row(composite="LC_TIER2", horizon_months=60, oos_r2=-1.0),
        _row(max_vif=8.0),
    ]
    for cid in ("z1", "z2", "z3", "z4", "z5"):
        rows_boundary.append(_row(component_id=cid, adf_pvalue=0.99))
        for h in (12, 36, 60, 120):
            rows_boundary.append(
                _row(component_id=cid, horizon_months=h, p_value=0.99)
            )
    panel_at_boundary = pd.DataFrame(rows_boundary)
    result_at = evaluate_v2_criteria(panel_at_boundary)
    c4 = next(c for c in result_at.criteria if c["criterion_id"] == "C4")
    assert c4["counted_as"] == "FAIL"

    # Same panel but t = 1.6501 -> PASS.
    panel_above = panel_at_boundary.copy()
    panel_above.loc[
        (panel_above["composite"] == "LC_FULL") & (panel_above["horizon_months"] == 12),
        "t_nw",
    ] = 1.6501
    result_above = evaluate_v2_criteria(panel_above)
    c4_above = next(c for c in result_above.criteria if c["criterion_id"] == "C4")
    assert c4_above["counted_as"] == "PASS"

    # Negative t: |t| boundary still strict.
    panel_neg = panel_at_boundary.copy()
    panel_neg.loc[
        (panel_neg["composite"] == "LC_FULL") & (panel_neg["horizon_months"] == 12),
        "t_nw",
    ] = -1.65
    result_neg = evaluate_v2_criteria(panel_neg)
    c4_neg = next(c for c in result_neg.criteria if c["criterion_id"] == "C4")
    assert c4_neg["counted_as"] == "FAIL"

    panel_neg_above = panel_at_boundary.copy()
    panel_neg_above.loc[
        (panel_neg_above["composite"] == "LC_FULL")
        & (panel_neg_above["horizon_months"] == 12),
        "t_nw",
    ] = -1.6501
    result_neg_above = evaluate_v2_criteria(panel_neg_above)
    c4_neg_above = next(
        c for c in result_neg_above.criteria if c["criterion_id"] == "C4"
    )
    assert c4_neg_above["counted_as"] == "PASS"


def test_bonferroni_denominator_is_20() -> None:
    """Bonferroni alpha/20 = 0.0025 (5 components x 4 horizons).

    NEW per Codex round-2.
    References: DRAFT_v4 §5.3 + sealed pre-reg §11.2 T14.
    """
    assert C7_BONFERRONI_DENOMINATOR == 20
    assert C7_ADJUSTED_ALPHA == 0.0025

    # Build a panel with a single cell at p = 0.0025 boundary (FAIL — strict <).
    rows = [
        _row(composite="LC_TIER2", horizon_months=12, oos_r2=-1.0),
        _row(composite="LC_TIER2", horizon_months=36, oos_r2=-1.0),
        _row(composite="LC_TIER2", horizon_months=60, oos_r2=-1.0),
        _row(composite="LC_FULL", horizon_months=12, gate_status="not_evaluable"),
        _row(composite="LC_FULL", horizon_months=36, gate_status="not_evaluable"),
        _row(composite="LC_FULL", horizon_months=60, gate_status="not_evaluable"),
        _row(composite="LC_FULL", horizon_months=120, gate_status="not_evaluable"),
        _row(max_vif=8.0),
    ]
    for cid in ("z1", "z2", "z3", "z4", "z5"):
        rows.append(_row(component_id=cid, adf_pvalue=0.99))
        for h in (12, 36, 60, 120):
            rows.append(
                _row(component_id=cid, horizon_months=h, p_value=0.5)
            )
    panel = pd.DataFrame(rows)
    # Inject one cell exactly at the Bonferroni-adjusted threshold.
    panel.loc[
        (panel["component_id"] == "z1") & (panel["horizon_months"] == 12),
        "p_value",
    ] = C7_ADJUSTED_ALPHA  # 0.0025
    result_at = evaluate_v2_criteria(panel)
    c7_at = next(c for c in result_at.criteria if c["criterion_id"] == "C7")
    assert c7_at["counted_as"] == "FAIL"  # strict <

    # One nudge below 0.0025 -> PASS.
    panel2 = panel.copy()
    panel2.loc[
        (panel2["component_id"] == "z1") & (panel2["horizon_months"] == 12),
        "p_value",
    ] = 0.0024
    result_below = evaluate_v2_criteria(panel2)
    c7_below = next(c for c in result_below.criteria if c["criterion_id"] == "C7")
    assert c7_below["counted_as"] == "PASS"
