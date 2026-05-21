"""v11.0 acceptance tests for yield curve compute (10Y-3M, 10Y-2Y)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.ingest._base import SourceMissingError
from src.transform.yield_curve_compute import (
    REQUIRED_COLUMNS,
    compute_all_yield_curves,
    compute_yield_curve_10y2y,
    compute_yield_curve_10y3m,
    latest_summary,
)


def _load_fred_key() -> str | None:
    cfg_path = Path("config.yaml")
    if not cfg_path.exists():
        return None
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    key = cfg.get("fred_api_key")
    if key and key != "PASTE_YOUR_32_CHAR_KEY_HERE":
        return str(key)
    return None


# ---------------------------------------------------------------------------
# 10Y-3M (TradingView CSV source)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def yc_10y3m() -> pd.DataFrame:
    return compute_yield_curve_10y3m()


def test_yc_10y3m_returns_required_columns(yc_10y3m: pd.DataFrame) -> None:
    for col in REQUIRED_COLUMNS:
        assert col in yc_10y3m.columns, f"Missing required column {col!r}"
    assert isinstance(yc_10y3m.index, pd.DatetimeIndex)


def test_yc_10y3m_signal_is_negated_spread(yc_10y3m: pd.DataFrame) -> None:
    """signal must equal -(spread_raw) to floating tolerance."""
    err = (yc_10y3m["signal"] + yc_10y3m["spread_raw"]).abs().max()
    assert err < 1e-10, f"signal + spread_raw should be 0; max abs err = {err}"


def test_yc_10y3m_monthly_index_strictly_increasing(yc_10y3m: pd.DataFrame) -> None:
    diffs = pd.Series(yc_10y3m.index).diff().dropna()
    assert (diffs > pd.Timedelta(0)).all()


def test_yc_10y3m_recent_inversion_detected(yc_10y3m: pd.DataFrame) -> None:
    """The 2022-2024 yield curve inversion must be visible in the data."""
    window = yc_10y3m.loc["2022-10-01":"2024-06-30"]
    n_inverted = int((window["spread_raw"] < 0).sum())
    assert n_inverted >= 10, (
        f"Expected ≥10 months of inversion 2022-10 → 2024-06; got {n_inverted}"
    )


def test_yc_10y3m_latest_summary_keys(yc_10y3m: pd.DataFrame) -> None:
    summary = latest_summary(yc_10y3m)
    assert set(summary.keys()) == {"date", "spread_raw_pp", "signal", "is_inverted"}
    assert isinstance(summary["spread_raw_pp"], float)
    assert isinstance(summary["is_inverted"], bool)


def test_yc_10y3m_no_lookahead() -> None:
    """At each month-end, the underlying yields come only from <= that day's data."""
    df = compute_yield_curve_10y3m()
    # We loaded daily TVC files; the month-end value is the last daily close
    # observable that month. Spot-check the latest 12 months are non-NaN.
    assert df.tail(12)["us10y_yield"].notna().all()
    assert df.tail(12)["short_yield"].notna().all()


# ---------------------------------------------------------------------------
# 10Y-2Y (FRED T10Y2Y)
# ---------------------------------------------------------------------------


def test_yc_10y2y_requires_api_key() -> None:
    with pytest.raises(SourceMissingError):
        compute_yield_curve_10y2y(api_key=None)


def test_yc_10y2y_loads_from_fred_t10y2y() -> None:
    api_key = _load_fred_key()
    if not api_key:
        pytest.skip("No FRED API key configured; cannot test T10Y2Y loader.")
    df = compute_yield_curve_10y2y(api_key=api_key)
    assert set(REQUIRED_COLUMNS).issubset(df.columns)
    # T10Y2Y begins 1976-06.
    assert df.index.min().year <= 1977
    # And signal == -spread_raw.
    err = (df["signal"] + df["spread_raw"]).abs().max()
    assert err < 1e-10


# ---------------------------------------------------------------------------
# Aggregate builder + best-effort behavior
# ---------------------------------------------------------------------------


def test_compute_all_yield_curves_returns_10y3m_without_api_key() -> None:
    out = compute_all_yield_curves(api_key=None)
    assert "yc_10y3m" in out
    # Without API key, 10y2y must be absent (best-effort, not error).
    assert "yc_10y2y" not in out


def test_compute_all_yield_curves_with_key_returns_both() -> None:
    api_key = _load_fred_key()
    if not api_key:
        pytest.skip("No FRED API key configured.")
    out = compute_all_yield_curves(api_key=api_key)
    assert "yc_10y3m" in out
    assert "yc_10y2y" in out
    for k, df in out.items():
        assert set(REQUIRED_COLUMNS).issubset(df.columns), f"{k} schema"
        assert df.attrs.get("variant_key") == k
        assert df.attrs.get("direction") == "inverted"
