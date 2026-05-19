"""Tests for src.models.regime."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.models.regime import classify, classify_series


def test_R1_strongly_overvalued() -> None:
    label, color = classify(2.5)
    assert label == "Strongly Overvalued"
    assert color == "#C8102E"


def test_R2_fair_value() -> None:
    label, color = classify(0.0)
    assert label == "Fair Value"
    assert color == "#9AA0A6"


def test_R3_strongly_undervalued() -> None:
    label, color = classify(-2.5)
    assert label == "Strongly Undervalued"
    assert color == "#1B7A3E"


def test_R4_nan_insufficient_data() -> None:
    label, color = classify(float("nan"))
    assert label == "Insufficient Data"
    assert color == "#000000"


def test_R5_boundaries() -> None:
    # z == 2.0 is NOT strongly (uses strict >), so Overvalued
    assert classify(2.0)[0] == "Overvalued"
    # z just above 2.0 IS strongly
    assert classify(2.0001)[0] == "Strongly Overvalued"
    # z == 1.0 is NOT overvalued (uses strict >), so Fair Value
    assert classify(1.0)[0] == "Fair Value"
    # z == -1.0 is still Fair Value (uses >= -1)
    assert classify(-1.0)[0] == "Fair Value"
    # z just below -1.0 is Undervalued
    assert classify(-1.0001)[0] == "Undervalued"
    # z == -2.0 is still Undervalued (uses >= -2)
    assert classify(-2.0)[0] == "Undervalued"
    assert classify(-2.0001)[0] == "Strongly Undervalued"


def test_classify_series_returns_dataframe() -> None:
    z = pd.Series(
        [2.5, 0.5, -1.5],
        index=pd.date_range("2024-01-31", periods=3, freq="ME"),
    )
    df = classify_series(z)
    assert list(df.columns) == ["z", "regime", "color"]
    assert df["regime"].tolist() == ["Strongly Overvalued", "Fair Value", "Undervalued"]
