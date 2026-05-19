"""Tests for src.transform.wilshire_scaling."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.transform.wilshire_scaling import points_to_trillions, wilshire_multiplier


def test_W1_anchor_1985() -> None:
    assert wilshire_multiplier(pd.Timestamp("1985-01-01")) == pytest.approx(1.00, abs=1e-9)


def test_W2_anchor_2020() -> None:
    assert wilshire_multiplier(pd.Timestamp("2020-01-01")) == pytest.approx(1.05, abs=1e-9)


def test_W3_midpoint_2002() -> None:
    # 2002-07-01 is approximately the midpoint of 1985-01-01 .. 2020-01-01
    m = wilshire_multiplier(pd.Timestamp("2002-07-01"))
    assert m == pytest.approx(1.025, abs=0.001)


def test_W4_extrapolation_2026() -> None:
    m = wilshire_multiplier(pd.Timestamp("2026-05-15"))
    assert m == pytest.approx(1.0586, abs=0.0005)


def test_W5_extrapolation_pre1985() -> None:
    m = wilshire_multiplier(pd.Timestamp("1970-12-31"))
    # ~14.1 years before 1985 at 0.05/35 per year = -0.0202 -> 0.9798
    assert m == pytest.approx(0.9796, abs=0.005)


def test_W6_points_to_trillions_70k_pts() -> None:
    idx = pd.DatetimeIndex([pd.Timestamp("2026-05-15")])
    s = pd.Series([70_000.0], index=idx)
    out = points_to_trillions(s)
    # 70_000 pts * 1.0586 B/pt = 74_102 B = 74.1 T
    assert out.iloc[0] == pytest.approx(74.1, abs=0.2)


def test_points_to_trillions_empty() -> None:
    s = pd.Series([], dtype="float64")
    out = points_to_trillions(s)
    assert out.empty
