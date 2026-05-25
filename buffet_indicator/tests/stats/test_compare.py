"""compare_threshold unit tests. DRAFT_v4 §3.9 + §5 (seal 2a94417).

(No §11.2 test_id; ancillary correctness coverage for the helper used
throughout the v2.0 criterion evaluator.)
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.compare import SUPPORTED_OPERATORS, compare_threshold  # noqa: E402


def test_compare_threshold_strict_gt_boundary() -> None:
    """Strict > matches §5 / §3.9 boundary semantics."""
    # C4 t > 1.65: t == 1.65 -> FAIL.
    assert compare_threshold(1.65, ">", 1.65) is False
    assert compare_threshold(1.6501, ">", 1.65) is True
    # C1 OOS R^2 > 0.005 boundary.
    assert compare_threshold(0.005, ">", 0.005) is False
    assert compare_threshold(0.00500001, ">", 0.005) is True


def test_compare_threshold_strict_lt_boundary() -> None:
    """Strict < matches §3.4 sample-gate semantics."""
    assert compare_threshold(60.0, "<", 60.0) is False  # at boundary -> evaluable
    assert compare_threshold(59.999, "<", 60.0) is True
    assert compare_threshold(60.001, "<", 60.0) is False


def test_compare_threshold_other_operators() -> None:
    assert compare_threshold(5.0, ">=", 5.0) is True
    assert compare_threshold(4.9, ">=", 5.0) is False
    assert compare_threshold(5.0, "<=", 5.0) is True
    assert compare_threshold(5.1, "<=", 5.0) is False
    assert compare_threshold(5.0, "==", 5.0) is True
    assert compare_threshold(5.0, "!=", 5.0) is False
    assert compare_threshold(5.0, "!=", 5.1) is True


def test_compare_threshold_nan_default_fail() -> None:
    assert compare_threshold(float("nan"), ">", 1.65) is False
    assert compare_threshold(float("nan"), "<", 0.05) is False


def test_compare_threshold_nan_modes() -> None:
    assert compare_threshold(float("nan"), ">", 1.65, on_nan="fail") is False
    assert compare_threshold(float("nan"), ">", 1.65, on_nan="pass") is True
    with pytest.raises(ValueError):
        compare_threshold(float("nan"), ">", 1.65, on_nan="raise")


def test_compare_threshold_rejects_unknown_op() -> None:
    with pytest.raises(ValueError):
        compare_threshold(1.0, "approx", 1.0)
    with pytest.raises(ValueError):
        compare_threshold(1.0, ">", 1.0, on_nan="other")


def test_compare_threshold_supported_operators_constant() -> None:
    assert ">" in SUPPORTED_OPERATORS
    assert "<" in SUPPORTED_OPERATORS
    assert ">=" in SUPPORTED_OPERATORS
    assert "<=" in SUPPORTED_OPERATORS
