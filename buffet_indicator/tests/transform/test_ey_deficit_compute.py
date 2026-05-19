"""Tests for src.transform.ey_deficit_compute."""
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

from src.transform.ey_deficit_compute import (
    EYDeficitInputMissingError,
    compute_ey_deficit,
    compute_real_10y_yield,
)


@dataclass
class _FakeShiller:
    data: pd.DataFrame
    available_columns: tuple[str, ...] = field(default_factory=tuple)


def _shiller_fixture(n: int = 600, start: str = "1976-01-31") -> _FakeShiller:
    idx = pd.date_range(start, periods=n, freq="ME")
    rng = np.random.default_rng(0)
    cape = 15.0 + 5.0 * np.sin(np.arange(n) / 60.0) + 1.5 * rng.standard_normal(n)
    cape[cape < 5.0] = 5.0
    cape[cape > 50.0] = 50.0
    cpi = 30.0 * np.cumprod(1.0 + 0.0025 + 0.0005 * rng.standard_normal(n))
    gs10 = 0.04 + 0.02 * rng.standard_normal(n)  # decimal units like real Shiller
    gs10 = np.clip(gs10, 0.01, 0.15)
    df = pd.DataFrame({"cape": cape, "cpi": cpi, "long_rate_gs10": gs10}, index=idx)
    return _FakeShiller(data=df, available_columns=tuple(df.columns))


# ---------------------------------------------------------------------------
# ED1 -- real_10y in plausible range
# ---------------------------------------------------------------------------


def test_ED1_real_yield_in_plausible_range() -> None:
    fix = _shiller_fixture()
    real = compute_real_10y_yield(
        fix.data["long_rate_gs10"], fix.data["cpi"], tips_10y=None
    )
    assert real.between(-10.0, 15.0).all()


# ---------------------------------------------------------------------------
# ED2 -- splice continuity: synthetic TIPS that matches Shiller-derived real
# ---------------------------------------------------------------------------


def test_ED2_splice_no_large_jump() -> None:
    fix = _shiller_fixture()
    real_pre = compute_real_10y_yield(
        fix.data["long_rate_gs10"], fix.data["cpi"], tips_10y=None
    )
    # Build synthetic TIPS = real_pre + small noise post-2003.
    rng = np.random.default_rng(7)
    post_idx = pd.date_range("2003-01-31", "2024-12-31", freq="ME")
    common = real_pre.index.intersection(post_idx)
    tips = (
        real_pre.loc[common] + 0.1 * rng.standard_normal(len(common))
    ) if len(common) >= 12 else pd.Series(dtype="float64")
    if tips.empty:
        pytest.skip("synthetic fixture too short for splice")
    real_combined = compute_real_10y_yield(
        fix.data["long_rate_gs10"], fix.data["cpi"], tips_10y=tips
    )
    # Boundary jump should be modest.
    boundary = pd.Timestamp("2003-01-31")
    if boundary in real_combined.index:
        idx = list(real_combined.index).index(boundary)
        if idx > 0:
            jump = abs(real_combined.iloc[idx] - real_combined.iloc[idx - 1])
            assert jump < 2.0


# ---------------------------------------------------------------------------
# ED3 -- EY-Deficit positive when bonds exceed equity yield
# ---------------------------------------------------------------------------


def test_ED3_positive_when_real_yield_above_earnings_yield() -> None:
    # Construct fixture: CAPE 40 (ey=2.5%), real_yield strictly > 2.5% from 2003+.
    n = 360
    idx = pd.date_range("1996-01-31", periods=n, freq="ME")
    cape = pd.Series([40.0] * n, index=idx, name="cape")
    cpi = pd.Series(
        100.0 * np.cumprod(np.ones(n) * 1.002), index=idx, name="cpi"
    )
    gs10 = pd.Series([0.06] * n, index=idx, name="gs10")  # 6% nominal
    df = pd.DataFrame({"cape": cape, "cpi": cpi, "long_rate_gs10": gs10})
    fake = _FakeShiller(data=df, available_columns=tuple(df.columns))
    out = compute_ey_deficit(fake)
    # Real yield ~= 6% - 2.4% (CPI YoY) = 3.6%; CAPE EY = 2.5%; deficit > 0.
    assert (out["ey_deficit"].dropna() > 0).all()


# ---------------------------------------------------------------------------
# ED4 / ED5 -- explicit sign checks
# ---------------------------------------------------------------------------


def test_ED4_negative_when_equity_attractive() -> None:
    """cape_ey=4%, real_yield=2% -> deficit = -2% (equity attractive)."""
    n = 120
    idx = pd.date_range("2010-01-31", periods=n, freq="ME")
    # CAPE 25 -> EY 4%
    cape = pd.Series([25.0] * n, index=idx, name="cape")
    cpi = pd.Series(
        100.0 * np.cumprod(np.ones(n) * 1.001), index=idx, name="cpi"
    )
    # Nominal 10Y = 2% + 1.2% inflation = 3.2% (in decimal). Real yield ~ 2.0%.
    gs10 = pd.Series([0.032] * n, index=idx, name="gs10")
    df = pd.DataFrame({"cape": cape, "cpi": cpi, "long_rate_gs10": gs10})
    out = compute_ey_deficit(_FakeShiller(data=df, available_columns=tuple(df.columns)))
    eyd = out["ey_deficit"].dropna()
    # cape_ey = 4%, real_yield ~ 2%, deficit ~ -2%
    assert eyd.mean() < 0
    assert abs(eyd.mean() + 2.0) < 0.6


def test_ED5_positive_when_bonds_attractive() -> None:
    """cape_ey=2%, real_yield=3% -> deficit = +1% (bonds attractive, OV signal)."""
    n = 120
    idx = pd.date_range("2010-01-31", periods=n, freq="ME")
    cape = pd.Series([50.0] * n, index=idx, name="cape")  # EY 2%
    cpi = pd.Series(
        100.0 * np.cumprod(np.ones(n) * 1.001), index=idx, name="cpi"
    )
    # Nominal = 4.2%, real ~ 3% (after subtracting 1.2% inflation)
    gs10 = pd.Series([0.042] * n, index=idx, name="gs10")
    df = pd.DataFrame({"cape": cape, "cpi": cpi, "long_rate_gs10": gs10})
    out = compute_ey_deficit(_FakeShiller(data=df, available_columns=tuple(df.columns)))
    eyd = out["ey_deficit"].dropna()
    assert eyd.mean() > 0
    assert abs(eyd.mean() - 1.0) < 0.6


def test_missing_inputs_raise() -> None:
    df = pd.DataFrame(
        {"long_rate_gs10": [0.04] * 12, "cpi": [100.0] * 12},
        index=pd.date_range("2020-01-31", periods=12, freq="ME"),
    )
    fake = _FakeShiller(data=df, available_columns=tuple(df.columns))
    with pytest.raises(EYDeficitInputMissingError):
        compute_ey_deficit(fake)
