"""Tests for src.transform.unit_harmonization."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.transform.unit_harmonization import (
    rate_to_decimal,
    to_trillions_from_billions,
    to_trillions_from_millions,
)


def test_U1_millions_to_trillions() -> None:
    out = to_trillions_from_millions(pd.Series([1_000_000.0]))
    assert out.iloc[0] == pytest.approx(1.0)


def test_U2_billions_to_trillions() -> None:
    out = to_trillions_from_billions(pd.Series([1_000.0]))
    assert out.iloc[0] == pytest.approx(1.0)


def test_U3_rate_percent_to_decimal() -> None:
    out = rate_to_decimal(pd.Series([4.30, 4.31]))
    assert out.iloc[0] == pytest.approx(0.0430)
    assert out.iloc[1] == pytest.approx(0.0431)


def test_U4_rate_already_decimal_unchanged() -> None:
    s = pd.Series([0.043, 0.044])
    out = rate_to_decimal(s)
    assert out.iloc[0] == pytest.approx(0.043)
    assert out.iloc[1] == pytest.approx(0.044)


def test_U5_rate_idempotent() -> None:
    s = pd.Series([4.30, 4.31])
    once = rate_to_decimal(s)
    twice = rate_to_decimal(once)
    pd.testing.assert_series_equal(once, twice)


def test_rate_to_decimal_all_nan() -> None:
    s = pd.Series([float("nan"), float("nan")])
    out = rate_to_decimal(s)
    assert out.isna().all()
