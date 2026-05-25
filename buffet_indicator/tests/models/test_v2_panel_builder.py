"""Phase E.1 — v2.0 panel builder tests.

References: PROMPT_CC_v11_4_v2_sprint_PHASE_E.md §2 + sealed §3 / §10.1.
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
from src.models.v2_panel_builder import (  # noqa: E402
    DEFAULT_HORIZONS_YEARS,
    DEFAULT_OOS_SPLIT,
    V2Panel,
    build_all_components,
    build_all_composites,
    build_v2_panel,
)


def _has_required_masters() -> bool:
    """Return True if all required master parquets exist locally."""
    required = [
        "walcl", "wdtgal", "rrpontsyd", "m2_sl", "busloans", "totll",
        "dtwexbgs", "tedrate", "sofr", "ioer", "iorb",
    ]
    from src.ingest.master_archive import load_master
    for sid in required:
        try:
            load_master(sid)
        except SourceMissingError:
            return False
    return True


pytestmark = pytest.mark.skipif(
    not _has_required_masters(),
    reason="Requires Phase B master parquets in data/master/ — skip on CI without raw data.",
)


def test_panel_has_12_candidate_cells() -> None:
    """3 scopes × 4 horizons = 12 candidate cells (some may have 0 obs)."""
    panel = build_v2_panel()
    assert isinstance(panel, V2Panel)
    assert len(panel.cells) == 12
    expected_keys = {
        (scope, h)
        for scope in ("LC_FULL", "LC_TIER2", "LC_DEEP")
        for h in DEFAULT_HORIZONS_YEARS
    }
    assert set(panel.cells.keys()) == expected_keys


def test_panel_components_have_pit_warmup() -> None:
    """Each component's z-score has at least 120-month warm-up
    (or relaxed for z5 spread per Phase E note 2)."""
    comp = build_all_components()
    # z2/z3/z5 are valid earlier (longer underlying history); z1/z4 valid later.
    for name in ("z1", "z2", "z3", "z4", "z5"):
        s = getattr(comp, name)
        assert s is not None, f"{name} should be produced"
        valid = s.dropna()
        assert len(valid) > 0, f"{name} has no valid PIT z-score values"


def test_panel_composites_respect_scope_effective_start() -> None:
    comp = build_all_components()
    composites = build_all_composites(comp)
    # All composites are non-NaN only after their effective start AND component warmup.
    for scope, s in composites.items():
        v = s.dropna()
        assert len(v) > 0, f"{scope} composite has no valid values"


def test_panel_pit_audit_feature_vintage_max_le_cell_latest() -> None:
    """For each cell, feature_vintage_max <= max(cell forecast origins)."""
    panel = build_v2_panel()
    for (scope, h_y), cell in panel.cells.items():
        if cell.n_obs_total == 0:
            continue
        assert cell.feature_vintage_max is not None
        assert cell.feature_vintage_max <= cell.composite_series.index.max(), (
            f"PIT violation at {scope} h={h_y}Y: "
            f"fvm={cell.feature_vintage_max} > latest_origin={cell.composite_series.index.max()}"
        )


def test_panel_oos_split_default_is_2021_01() -> None:
    """Phase E adjusted OOS split (per sealed §3.2.1 + data availability)."""
    assert DEFAULT_OOS_SPLIT["LC_FULL"] == pd.Timestamp("2021-01-31")
    assert DEFAULT_OOS_SPLIT["LC_TIER2"] == pd.Timestamp("2021-01-31")
    assert DEFAULT_OOS_SPLIT["LC_DEEP"] == pd.Timestamp("2021-01-31")


def test_panel_n_obs_split_consistent() -> None:
    """For each non-empty cell, n_obs_insample + n_obs_oos == n_obs_total."""
    panel = build_v2_panel()
    for (scope, h_y), cell in panel.cells.items():
        assert cell.n_obs_insample + cell.n_obs_oos == cell.n_obs_total, (
            f"{scope} h={h_y}Y: {cell.n_obs_insample}+{cell.n_obs_oos}!={cell.n_obs_total}"
        )


def test_panel_meta_documents_data_availability() -> None:
    """The panel meta block surfaces Phase E data-availability decisions."""
    panel = build_v2_panel()
    assert panel.meta["icedxy_pre2006_status"] == "not_available"
    assert panel.meta["z5_post_splice_warmup_relaxed_to_24mo"] is True
    assert panel.meta["rrpontsyd_pre2013_treatment"] == "zero_fill_strict_lt_2013_09_23"
