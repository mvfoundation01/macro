"""§11.2 T18 — component id map matches v1.0 catalog.
DRAFT_v4 §1 + §12 (seal 2a94417).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.ingest.component_map import parse_component_id_map  # noqa: E402


def test_prereg_component_id_map_matches_v1_sealed_catalog() -> None:
    """Parse sealed pre-reg and assert mapping equals
    {z1: netfed_liquidity, z2: m2_growth_yoy, z3: banklend_growth_yoy,
     z4: dxy_inverse, z5: funding_stress}.

    NEW per Codex round-2 New-2.
    References: DRAFT_v4 §1 + §12 + sealed pre-reg §11.2 T18.
    """
    pytest.fail("Test scaffolded per kickoff §4 - implementation pending")
