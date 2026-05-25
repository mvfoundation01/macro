"""§11.2 T01 — HAC lag uses v1 formula. DRAFT_v4 §3.5 (seal 2a94417)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.hac import compute_hac_lag  # noqa: E402


def test_compute_hac_lag_uses_v1_formula() -> None:
    """HAC lag = horizon_months - 1 (h=12 -> 11, h=120 -> 119).

    References: DRAFT_v4 §3.5 + sealed pre-reg §11.2 T01.
    """
    # Canonical four horizons per §3.5 table.
    assert compute_hac_lag(12) == 11   # 1Y
    assert compute_hac_lag(36) == 35   # 3Y
    assert compute_hac_lag(60) == 59   # 5Y
    assert compute_hac_lag(120) == 119  # 10Y

    # Boundary at h = 1 (minimum positive horizon) -> lag = 0.
    assert compute_hac_lag(1) == 0

    # Non-positive horizons rejected.
    with pytest.raises(ValueError):
        compute_hac_lag(0)
    with pytest.raises(ValueError):
        compute_hac_lag(-1)

    # Non-int types rejected.
    with pytest.raises(TypeError):
        compute_hac_lag(12.0)  # type: ignore[arg-type]
