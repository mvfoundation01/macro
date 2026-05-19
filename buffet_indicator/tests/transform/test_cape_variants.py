"""Tests for src.transform.cape_variants."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.transform.cape_variants import compute_cape_variants


@dataclass
class _FakeShiller:
    data: pd.DataFrame
    available_columns: tuple[str, ...] = field(default_factory=tuple)


def _mk_shiller_with_cape(start: str = "1871-01-31", n: int = 1864) -> _FakeShiller:
    """Synthetic Shiller fixture with CAPE NaN for the first 120 months (~10y)."""
    idx = pd.date_range(start, periods=n, freq="ME")
    rng = np.random.default_rng(0)
    cape_vals = 15.0 + 5.0 * np.sin(np.arange(n) / 60.0) + rng.standard_normal(n) * 0.5
    cape_vals[:120] = np.nan  # CAPE undefined until 1881
    df = pd.DataFrame({"cape": cape_vals}, index=idx)
    return _FakeShiller(data=df, available_columns=("cape",))


def test_CV1_returns_dict_with_cape_key() -> None:
    fake = _mk_shiller_with_cape()
    out = compute_cape_variants(fake)
    assert "cape" in out
    assert isinstance(out["cape"], pd.Series)


def test_CV2_no_nans_in_output() -> None:
    fake = _mk_shiller_with_cape()
    out = compute_cape_variants(fake)
    assert out["cape"].isna().sum() == 0


def test_CV3_monthly_datetimeindex() -> None:
    fake = _mk_shiller_with_cape()
    out = compute_cape_variants(fake)
    idx = out["cape"].index
    assert isinstance(idx, pd.DatetimeIndex)
    # All entries are month-end.
    assert idx.is_month_end.all()


def test_CV4_start_date_at_or_after_1881() -> None:
    fake = _mk_shiller_with_cape()
    out = compute_cape_variants(fake)
    assert out["cape"].index.min() >= pd.Timestamp("1881-01-01")


def test_missing_cape_column_returns_empty_dict() -> None:
    df = pd.DataFrame(
        {"price_nominal": [1.0, 2.0]},
        index=pd.date_range("1871-01-31", periods=2, freq="ME"),
    )
    fake = _FakeShiller(data=df, available_columns=("price_nominal",))
    out = compute_cape_variants(fake)
    assert out == {}
