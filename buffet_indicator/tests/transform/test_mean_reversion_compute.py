"""Tests for src.transform.mean_reversion_compute."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.transform.mean_reversion_compute import compute_mean_reversion_variant


@dataclass
class _FakeShiller:
    data: pd.DataFrame
    available_columns: tuple[str, ...] = field(default_factory=tuple)


def _mk_fixture_with_real_price(n: int = 1860) -> _FakeShiller:
    idx = pd.date_range("1871-01-31", periods=n, freq="ME")
    rng = np.random.default_rng(0)
    real_price = 100.0 * np.cumprod(1.0 + 0.005 + 0.04 * rng.standard_normal(n) / 12)
    df = pd.DataFrame({"real_price": real_price}, index=idx)
    return _FakeShiller(data=df, available_columns=tuple(df.columns))


def _mk_fixture_without_real_price(n: int = 1860) -> _FakeShiller:
    """Fixture with only price_nominal + cpi (forces fallback path)."""
    idx = pd.date_range("1871-01-31", periods=n, freq="ME")
    rng = np.random.default_rng(1)
    price_nominal = 5.0 * np.cumprod(
        1.0 + 0.006 + 0.03 * rng.standard_normal(n) / 12
    )
    cpi = 10.0 * np.cumprod(1.0 + 0.002 + 0.003 * rng.standard_normal(n) / 12)
    df = pd.DataFrame(
        {"price_nominal": price_nominal, "cpi": cpi}, index=idx
    )
    return _FakeShiller(data=df, available_columns=tuple(df.columns))


# ---------------------------------------------------------------------------
# MR1 -- returns dict with key 'mean_reversion'
# ---------------------------------------------------------------------------


def test_MR1_returns_dict_with_mean_reversion_key() -> None:
    fake = _mk_fixture_with_real_price()
    out = compute_mean_reversion_variant(fake)
    assert set(out.keys()) == {"mean_reversion"}


# ---------------------------------------------------------------------------
# MR2 -- monthly DatetimeIndex starting ~1871-01
# ---------------------------------------------------------------------------


def test_MR2_monthly_index_starting_1871() -> None:
    fake = _mk_fixture_with_real_price()
    s = compute_mean_reversion_variant(fake)["mean_reversion"]
    assert isinstance(s.index, pd.DatetimeIndex)
    assert s.index.is_month_end.all()
    assert s.index.min() <= pd.Timestamp("1871-03-31")


# ---------------------------------------------------------------------------
# MR3 -- fallback (no real_price column) reconstructs from price + CPI
# ---------------------------------------------------------------------------


def test_MR3_fallback_uses_price_and_cpi() -> None:
    fake = _mk_fixture_without_real_price()
    s = compute_mean_reversion_variant(fake)["mean_reversion"]
    # Reconstruction: rebased so the latest value equals the latest nominal price.
    expected_last = float(fake.data["price_nominal"].iloc[-1])
    assert s.iloc[-1] == pytest.approx(expected_last, rel=1e-9)
    # Earlier values should be HIGHER than nominal price (because CPI was lower).
    nominal_first = float(fake.data["price_nominal"].iloc[0])
    assert s.iloc[0] > nominal_first


# ---------------------------------------------------------------------------
# MR4 -- latest value positive
# ---------------------------------------------------------------------------


def test_MR4_latest_value_positive() -> None:
    fake = _mk_fixture_with_real_price()
    s = compute_mean_reversion_variant(fake)["mean_reversion"]
    assert float(s.iloc[-1]) > 0


def test_empty_when_neither_real_price_nor_price_cpi() -> None:
    df = pd.DataFrame(
        {"cape": [10.0] * 12},
        index=pd.date_range("2020-01-31", periods=12, freq="ME"),
    )
    fake = _FakeShiller(data=df, available_columns=tuple(df.columns))
    assert compute_mean_reversion_variant(fake) == {}
