"""Tests for src.transform.qratio_compute."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.transform.qratio_compute import (
    QRatioInputMissingError,
    compute_qratio,
    compute_qratio_variant,
)


@dataclass
class _FakeFred:
    series_id: str
    data: pd.Series
    frequency: str = "Q"
    units: str = ""
    last_updated_at_fred: datetime = datetime(2026, 5, 1)
    retrieval_timestamp: datetime = datetime(2026, 5, 18)
    sha256: str = ""
    cache_path: Path = Path(".")


def _mk_q_inputs(n: int = 80, start: str = "2006-03-31") -> tuple[_FakeFred, _FakeFred]:
    """Build synthetic NCBEILQ + TNWMVBSNNCB at quarterly month-end."""
    idx = pd.date_range(start, periods=n, freq="QE")
    rng = np.random.default_rng(0)
    # Both in MILLIONS per FRED API metadata.
    equities = pd.Series(
        20_000_000.0 + 200_000.0 * np.arange(n) + 500_000.0 * rng.standard_normal(n),
        index=idx,
        name="NCBEILQ027S",
    )
    net_worth = pd.Series(
        20_000_000.0 + 200_000.0 * np.arange(n) + 500_000.0 * rng.standard_normal(n)
        + 5_000_000.0,  # roughly 25% larger so Q ~ 0.8-0.9
        index=idx,
        name="TNWMVBSNNCB",
    )
    eq = _FakeFred("NCBEILQ027S", equities)
    nw = _FakeFred("TNWMVBSNNCB", net_worth)
    return eq, nw


def test_QR1_returns_monthly_series() -> None:
    eq, nw = _mk_q_inputs(n=40)
    q = compute_qratio(eq, nw)
    assert isinstance(q, pd.Series)
    assert q.name == "qratio"
    # Monthly index step should be 28-31 days.
    deltas = q.index.to_series().diff().dt.days.dropna()
    assert deltas.max() <= 35


def test_QR2_values_in_plausible_range() -> None:
    eq, nw = _mk_q_inputs(n=40)
    q = compute_qratio(eq, nw)
    assert (q > 0).all()
    # With our synthetic 1:1 ratio of millions/(billions*1000), values cluster near 1.0.
    assert q.between(0.2, 5.0).all()


def test_QR3_specific_ratio() -> None:
    """Constant equities=50M / net_worth=25M -> Q=2.0 (both in same units)."""
    idx = pd.date_range("2020-03-31", periods=8, freq="QE")
    eq = _FakeFred("E", pd.Series([50_000_000.0] * 8, index=idx))
    nw = _FakeFred("NW", pd.Series([25_000_000.0] * 8, index=idx))
    q = compute_qratio(eq, nw)
    assert (q.dropna().round(6) == 2.0).all()


def test_QR4_vti_extrapolation_monotone() -> None:
    eq, nw = _mk_q_inputs(n=20)
    # Build VTI daily rising 1% per day for 60 days after last quarter-end.
    last_qend = eq.data.index.max()
    daily_idx = pd.bdate_range(last_qend, periods=90)
    vti = pd.Series(
        100.0 * np.cumprod(np.ones(len(daily_idx)) * 1.001),
        index=daily_idx,
        name="VTI",
    )
    q_with = compute_qratio(eq, nw, vti_series=vti)
    q_without = compute_qratio(eq, nw)
    # With VTI, the series should extend past the last Z.1 quarter-end.
    assert q_with.index.max() > q_without.index.max()
    # Extrapolated tail should be monotonically increasing (VTI is).
    tail = q_with.loc[q_with.index > last_qend]
    assert (tail.diff().dropna() > 0).all()


def test_QR5_missing_net_worth_raises() -> None:
    eq, _ = _mk_q_inputs()
    with pytest.raises(QRatioInputMissingError):
        compute_qratio(eq, None)


def test_compute_qratio_variant_returns_dict() -> None:
    eq, nw = _mk_q_inputs()
    out = compute_qratio_variant(eq, nw)
    assert set(out.keys()) == {"qratio"}


def test_compute_qratio_variant_handles_missing_gracefully() -> None:
    eq, _ = _mk_q_inputs()
    out = compute_qratio_variant(eq, None)
    assert out == {}
