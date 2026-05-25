"""Phase F-BLK1.C — synthetic look-ahead detection test (non-tautological proof).

Per Strategist mistake #10 forward policy: any PIT audit must include a
synthetic test where a known violation is planted and the audit MUST catch it.
If the audit cannot detect a clear violation it is tautological and the
audit design is wrong (BLOCKER).

References
----------
- PROMPT_CC_v11_4_phase_F_BLK1_fix.md §4 (BLK1.C).
- Sealed pre-reg §3.2.2 (vintage policy).
- Phase F-BLK1.A: ``feature_vintage_max_at_origin`` per cell.
- Phase F-BLK1.B: ``run_pit_audit_non_tautological``.
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
from src.models.v2_panel_builder import build_v2_panel  # noqa: E402
from src.models.v2_verdict_writer import run_pit_audit_non_tautological  # noqa: E402


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


def test_pit_audit_catches_synthetic_look_ahead() -> None:
    """Non-tautological audit must detect a planted future-dated violation.

    Strategy:
    1. Build the panel normally (PIT-compliant).
    2. Pick a real (scope, horizon) cell and a real origin in its index.
    3. Inject a feature_vintage_max well into the future (e.g., 2099-12-31).
    4. Run the audit.
    5. Assert FAIL + the planted violation is recorded.

    If the audit cannot catch this, it is tautological by Strategist mistake
    #10 definition and the audit design is wrong.
    """
    panel = build_v2_panel()

    # Find first non-empty cell.
    target_key = None
    target_origin = None
    for key, cell in panel.cells.items():
        if cell.n_obs_total > 0 and len(cell.feature_vintage_max_at_origin) > 0:
            target_key = key
            target_origin = next(iter(cell.feature_vintage_max_at_origin.keys()))
            break
    assert target_key is not None, "no non-empty cells in panel — cannot run synthetic test"

    # Confirm the clean audit passes BEFORE injection.
    clean = run_pit_audit_non_tautological(panel)
    assert clean["audit_status"] == "PASS", f"clean panel should PASS; got {clean}"

    # Inject violation.
    synthetic_violation = pd.Timestamp("2099-12-31")
    panel.cells[target_key].feature_vintage_max_at_origin[target_origin] = synthetic_violation

    # Re-run audit — MUST catch.
    dirty = run_pit_audit_non_tautological(panel)
    assert dirty["audit_status"] == "FAIL", (
        f"audit failed to catch planted look-ahead violation: {dirty}"
    )
    assert dirty["n_violations"] >= 1
    scope, h_y = target_key
    cell_label = f"{scope}_{h_y}Y"
    matching = [
        v for v in dirty["violations"]
        if v["cell"] == cell_label
        and v["origin"] == pd.Timestamp(target_origin).isoformat()
    ]
    assert len(matching) == 1, (
        f"expected 1 matching violation for {cell_label} at {target_origin}; got {matching}"
    )
    assert matching[0]["feature_vintage_max"] == synthetic_violation.isoformat()


def test_pit_audit_passes_clean_panel() -> None:
    """On a properly-constructed panel the audit must pass cleanly."""
    panel = build_v2_panel()
    audit = run_pit_audit_non_tautological(panel)
    assert audit["audit_status"] == "PASS"
    assert audit["n_violations"] == 0
    assert audit["n_origins_audited"] > 0, (
        "audit should iterate at least one (origin, cell) pair"
    )
    assert audit["n_cells_audited"] == 12  # 3 scopes × 4 horizons


def test_pit_audit_origin_count_matches_panel_sum() -> None:
    """Audit n_origins_audited == sum of per-cell origin map lengths.

    Confirms the audit walks every (origin, cell) pair rather than collapsing
    to a single aggregate (which is what the BLK1 fix targets).
    """
    panel = build_v2_panel()
    expected_n = sum(
        len(cell.feature_vintage_max_at_origin) for cell in panel.cells.values()
    )
    audit = run_pit_audit_non_tautological(panel)
    assert audit["n_origins_audited"] == expected_n, (
        f"audit n_origins_audited={audit['n_origins_audited']} "
        f"!= sum of per-cell origin counts={expected_n}"
    )
    assert expected_n > 50, (
        f"expected >50 (origin, cell) pairs across 12 cells; got {expected_n}"
    )


def test_pit_audit_records_construction_marker() -> None:
    """Audit output records pit_audit_construction marker from panel.meta
    so downstream consumers can distinguish post-BLK1 audits from pre-BLK1."""
    panel = build_v2_panel()
    audit = run_pit_audit_non_tautological(panel)
    assert audit.get("pit_audit_construction") == "per_origin_non_tautological_F_BLK1_A"
    assert audit.get("feature_vintage_basis") == "observation_date_approximation"
