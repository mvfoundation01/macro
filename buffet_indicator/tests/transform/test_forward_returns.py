"""Tests for src.transform.forward_returns."""
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

from src.transform.forward_returns import (
    DEFAULT_HORIZONS,
    ForwardReturnSpliceError,
    build_forward_returns,
    forward_returns,
    shiller_nominal_total_return,
    splice_shiller_spxtr,
)


@dataclass
class _FakeShiller:
    """Minimal Shiller-shaped wrapper for tests (matches ShillerData attrs)."""

    data: pd.DataFrame
    available_columns: tuple[str, ...] = field(default_factory=tuple)


def _mk_fake_shiller(n: int = 240, start: str = "2000-01-31") -> _FakeShiller:
    idx = pd.date_range(start, periods=n, freq="ME")
    real_tr = np.cumprod(1.0 + 0.005 * np.ones(n)) * 100.0
    cpi = np.linspace(170.0, 250.0, n)
    df = pd.DataFrame({"real_total_return": real_tr, "cpi": cpi}, index=idx)
    return _FakeShiller(data=df, available_columns=tuple(df.columns))


def _mk_long_shiller() -> _FakeShiller:
    """Long enough Shiller fixture spanning the splice boundary."""
    idx = pd.date_range("1980-01-31", "2026-04-30", freq="ME")
    # Real total return: deterministic 0.5%/month real growth.
    real_tr = np.cumprod(np.ones(len(idx)) * 1.005) * 100.0
    cpi = np.linspace(80.0, 320.0, len(idx))
    df = pd.DataFrame({"real_total_return": real_tr, "cpi": cpi}, index=idx)
    return _FakeShiller(data=df, available_columns=tuple(df.columns))


# ---------------------------------------------------------------------------
# FR1 -- single-horizon CAGR: monthly TR doubles in 12 months -> ~100% CAGR
# ---------------------------------------------------------------------------


def test_FR1_single_horizon_doubling() -> None:
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    tr = pd.Series(np.power(2.0, np.arange(24) / 12.0), index=idx, name="tr")
    out = forward_returns(tr, horizons_months=(12,))
    # Doubled over 12 months -> annualized CAGR ~ 100%.
    valid = out["r_12m"].dropna()
    assert (valid - 1.0).abs().max() < 1e-9


# ---------------------------------------------------------------------------
# FR2 -- last h rows are NaN per column
# ---------------------------------------------------------------------------


def test_FR2_tail_nan_per_horizon() -> None:
    idx = pd.date_range("2020-01-31", periods=60, freq="ME")
    tr = pd.Series(np.cumprod(np.ones(60) * 1.005), index=idx, name="tr")
    out = forward_returns(tr, horizons_months=(1, 12, 36))
    for h, col in [(1, "r_1m"), (12, "r_12m"), (36, "r_36m")]:
        last_h = out[col].iloc[-h:]
        assert last_h.isna().all()


# ---------------------------------------------------------------------------
# FR3 -- splice continuity fail
# ---------------------------------------------------------------------------


def test_FR3_splice_continuity_fail() -> None:
    idx_shiller = pd.date_range("1980-01-31", "1990-01-31", freq="ME")
    idx_spxtr = pd.date_range("1988-01-31", "1995-01-31", freq="ME")
    # Shiller-derived monthly returns: ~0.5%/month
    shiller = pd.Series(
        np.cumprod(1.0 + np.full(len(idx_shiller), 0.005)) * 100, index=idx_shiller
    )
    # SPXTR series with returns ~5%/month (huge divergence in overlap)
    spxtr = pd.Series(
        np.cumprod(1.0 + np.full(len(idx_spxtr), 0.05)) * 100, index=idx_spxtr
    )
    with pytest.raises(ForwardReturnSpliceError):
        splice_shiller_spxtr(shiller, spxtr, boundary=pd.Timestamp("1988-01-31"))


# ---------------------------------------------------------------------------
# FR4 -- splice continuity passes when series are identical
# ---------------------------------------------------------------------------


def test_FR4_splice_continuity_pass() -> None:
    idx_pre = pd.date_range("1980-01-31", "1990-12-31", freq="ME")
    idx_post = pd.date_range("1988-01-31", "1995-01-31", freq="ME")
    rng = np.random.default_rng(0)
    monthly_rets = 0.008 + 0.02 * rng.standard_normal(len(idx_pre))
    shiller = pd.Series(np.cumprod(1.0 + monthly_rets) * 100, index=idx_pre)
    # SPXTR exactly mirrors Shiller's returns in the overlap window.
    overlap_returns = shiller.pct_change().dropna().loc[idx_post[0] : idx_post[-1]]
    cum = np.cumprod(1.0 + overlap_returns.reindex(idx_post[1:]).fillna(0.0)) * 100.0
    spxtr = pd.concat([pd.Series([100.0], index=[idx_post[0]]), cum]).sort_index()
    spliced = splice_shiller_spxtr(shiller, spxtr, boundary=pd.Timestamp("1988-01-31"))
    # Spliced series should be continuous across boundary.
    pre = spliced.loc[spliced.index < "1988-01-31"]
    post = spliced.loc[spliced.index >= "1988-01-31"]
    assert not pre.empty
    assert not post.empty
    assert post.iloc[0] == pytest.approx(pre.iloc[-1], rel=1e-4)


# ---------------------------------------------------------------------------
# FR5 -- nominal_TR_t = real_TR_t * CPI_t / CPI_0
# ---------------------------------------------------------------------------


def test_FR5_real_to_nominal_formula() -> None:
    fake = _mk_fake_shiller(n=120)
    nom = shiller_nominal_total_return(fake)
    df = fake.data
    cpi_base = float(df["cpi"].iloc[0])
    expected = df["real_total_return"] * df["cpi"] / cpi_base
    pd.testing.assert_series_equal(
        nom.astype("float64"), expected.astype("float64"), check_names=False
    )


# ---------------------------------------------------------------------------
# FR6 -- build_forward_returns returns all three keys
# ---------------------------------------------------------------------------


def test_FR6_build_returns_all_keys() -> None:
    fake = _mk_long_shiller()
    # Construct SPXTR daily that's consistent with Shiller nominal in overlap.
    nominal = shiller_nominal_total_return(fake)
    # Daily SPXTR mirror: forward-fill nominal to daily.
    daily_idx = pd.date_range("1988-01-04", "2026-04-30", freq="B")
    nominal.index = pd.DatetimeIndex(nominal.index).normalize()
    daily_vals = nominal.reindex(daily_idx, method="ffill").ffill().bfill()
    out = build_forward_returns(
        fake, daily_vals, horizons_months=(12, 60, 120), check_continuity=False
    )
    assert set(out.keys()) == {"fr_spliced", "fr_spxtr_only", "fr_shiller_only"}


# ---------------------------------------------------------------------------
# FR7 -- approximate start dates
# ---------------------------------------------------------------------------


def test_FR7_start_dates_approximate() -> None:
    fake = _mk_long_shiller()
    nominal = shiller_nominal_total_return(fake)
    nominal.index = pd.DatetimeIndex(nominal.index).normalize()
    daily_idx = pd.date_range("1988-01-04", "2026-04-30", freq="B")
    daily_vals = nominal.reindex(daily_idx, method="ffill").ffill().bfill()
    out = build_forward_returns(
        fake, daily_vals, horizons_months=(12,), check_continuity=False
    )
    sh_only = out["fr_shiller_only"].dropna(subset=["r_12m"])
    sp_only = out["fr_spxtr_only"].dropna(subset=["r_12m"])
    assert sh_only.index.min() <= pd.Timestamp("1981-02-28")
    assert sp_only.index.min() >= pd.Timestamp("1988-01-01")


# ---------------------------------------------------------------------------
# FR8 -- shiller_only is REAL (different from nominal in inflationary fixture)
# ---------------------------------------------------------------------------


def test_FR8_shiller_only_returns_real() -> None:
    fake = _mk_long_shiller()
    out = build_forward_returns(
        fake,
        spxtr_daily=None,
        horizons_months=(120,),
        check_continuity=False,
    )
    # Without SPXTR the spliced series is just Shiller-nominal -> different
    # behavior than fr_shiller_only (which is REAL).
    real_mean = float(out["fr_shiller_only"]["r_120m"].dropna().mean())
    nominal_mean = float(out["fr_spliced"]["r_120m"].dropna().mean())
    assert nominal_mean > real_mean  # nominal includes inflation tailwind


def test_default_horizons_unchanged() -> None:
    assert DEFAULT_HORIZONS == (1, 3, 12, 36, 60, 84, 120)
