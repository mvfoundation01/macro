"""§11.2 T10 — Stambaugh strict boundary. DRAFT_v4 §3.6 + §3.9 (seal 2a94417)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.stats.stambaugh import should_apply_stambaugh  # noqa: E402


def test_stambaugh_exact_boundary_not_applied() -> None:
    """Strict > at rho=0.85: should_apply_stambaugh(0.85) is False;
    should_apply_stambaugh(nextafter(0.85, 1.0)) is True.

    NEW per Codex round-2 New-5.
    References: DRAFT_v4 §3.6 + §3.9 + sealed pre-reg §11.2 T10.
    """
    # Strict boundary: equality at 0.85 is NOT applied.
    assert should_apply_stambaugh(0.85) is False
    # Smallest representable float above 0.85 IS applied.
    assert should_apply_stambaugh(math.nextafter(0.85, 1.0)) is True
    # Below threshold: NOT applied.
    assert should_apply_stambaugh(0.84) is False
    assert should_apply_stambaugh(math.nextafter(0.85, 0.0)) is False
    # Well above threshold: applied.
    assert should_apply_stambaugh(0.90) is True
    assert should_apply_stambaugh(0.99) is True
    # Non-finite values: NOT applied (defensive).
    assert should_apply_stambaugh(float("nan")) is False
    assert should_apply_stambaugh(float("inf")) is False
    assert should_apply_stambaugh(float("-inf")) is False
