"""Phase E.2 / E.3 / E.4 — verdict-run composition tests.

References: PROMPT_CC_v11_4_v2_sprint_PHASE_E.md §3-§5 + sealed §3-§5.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.ingest._base import SourceMissingError  # noqa: E402


def _has_required_masters() -> bool:
    from src.ingest.master_archive import load_master
    for sid in (
        "walcl", "wdtgal", "rrpontsyd", "m2_sl", "busloans", "totll",
        "dtwexbgs", "tedrate", "sofr", "ioer", "iorb",
    ):
        try:
            load_master(sid)
        except SourceMissingError:
            return False
    return True


pytestmark = pytest.mark.skipif(
    not _has_required_masters(),
    reason="Requires Phase B master parquets in data/master/.",
)


def test_run_regression_sweep_returns_12_cells() -> None:
    from src.models.v2_panel_builder import build_v2_panel
    from src.models.v2_verdict_run import SweepResult, run_regression_sweep

    panel = build_v2_panel()
    sweep = run_regression_sweep(panel, n_bootstrap=200, purpose="test", fit_skewt=True, bootstrap_beta=True)
    assert len(sweep) == 12
    for key, sr in sweep.items():
        assert isinstance(sr, SweepResult)
        assert sr.cell_key == key
        assert sr.regression is not None
        assert sr.regression.gate_status in {"evaluable", "not_evaluable"}


def test_run_adf_returns_5_components() -> None:
    from src.models.v2_panel_builder import build_v2_panel
    from src.models.v2_verdict_run import run_adf_per_component

    panel = build_v2_panel()
    adf = run_adf_per_component(panel)
    assert set(adf.keys()) == {"z1", "z2", "z3", "z4", "z5"}
    for cid, res in adf.items():
        assert res.component_id == cid
        # At least one of these should be computable for z2/z3 (longest history).
        if cid in {"z2", "z3"}:
            assert res.p_value is not None


def test_run_vif_returns_keys_and_max() -> None:
    from src.models.v2_panel_builder import build_v2_panel
    from src.models.v2_verdict_run import run_vif

    panel = build_v2_panel()
    vif = run_vif(panel)
    for cid in ("z1", "z2", "z3", "z4", "z5"):
        assert cid in vif
    assert "max_vif" in vif


def test_run_bonferroni_returns_20_cells() -> None:
    from src.models.v2_panel_builder import build_v2_panel
    from src.models.v2_verdict_run import run_bonferroni_sweep

    panel = build_v2_panel()
    cells = run_bonferroni_sweep(panel)
    assert len(cells) == 20  # 5 components x 4 horizons
    components = {c.component_id for c in cells}
    horizons = {c.horizon_months for c in cells}
    assert components == {"z1", "z2", "z3", "z4", "z5"}
    assert horizons == {12, 36, 60, 120}


def test_compose_criteria_panel_includes_all_sections() -> None:
    from src.models.v2_panel_builder import build_v2_panel
    from src.models.v2_verdict_run import (
        compose_criteria_panel,
        run_adf_per_component,
        run_bonferroni_sweep,
        run_regression_sweep,
        run_vif,
    )

    panel = build_v2_panel()
    sweep = run_regression_sweep(panel, n_bootstrap=100, purpose="test", fit_skewt=False, bootstrap_beta=False)
    adf = run_adf_per_component(panel)
    vif = run_vif(panel)
    bonferroni = run_bonferroni_sweep(panel)
    crit_panel = compose_criteria_panel(sweep, adf, vif, bonferroni)
    assert isinstance(crit_panel, pd.DataFrame)
    # 12 regression rows + 5 ADF rows + 1 VIF row + 20 Bonferroni rows = 38
    assert crit_panel.shape[0] == 38
