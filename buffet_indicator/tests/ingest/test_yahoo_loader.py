"""Tests for src.ingest.yahoo_loader."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from src.ingest import yahoo_loader as yl
from src.ingest._base import DataValidationError, NetworkError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_df(n: int = 600, start: str = "2020-01-01") -> pd.DataFrame:
    idx = pd.bdate_range(start=start, periods=n)
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(n)],
            "High": [101.0 + i for i in range(n)],
            "Low": [99.0 + i for i in range(n)],
            "Close": [100.5 + i for i in range(n)],
            "Volume": [1000 + i for i in range(n)],
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# Y1 -- happy path
# ---------------------------------------------------------------------------


def test_Y1_happy_path(monkeypatch: pytest.MonkeyPatch, tmp_cache_dir: Path) -> None:
    monkeypatch.setattr(yl, "_fetch_yf", lambda symbol, **kw: _mk_df(500))
    s = yl.load_yahoo_series("^W5000", cache_dir=tmp_cache_dir)
    assert isinstance(s, yl.YahooSeries)
    assert len(s.data) == 500
    assert s.cache_path.exists()


# ---------------------------------------------------------------------------
# Y2 -- caret escaping in cache filename
# ---------------------------------------------------------------------------


def test_Y2_caret_in_symbol_escaped(monkeypatch: pytest.MonkeyPatch, tmp_cache_dir: Path) -> None:
    monkeypatch.setattr(yl, "_fetch_yf", lambda symbol, **kw: _mk_df(500))
    s = yl.load_yahoo_series("^W5000", cache_dir=tmp_cache_dir)
    assert "CARET_W5000" in s.cache_path.name
    assert not s.cache_path.name.startswith("^")


# ---------------------------------------------------------------------------
# Y3 -- cache hit: zero yfinance calls
# ---------------------------------------------------------------------------


def test_Y3_cache_hit(monkeypatch: pytest.MonkeyPatch, tmp_cache_dir: Path) -> None:
    calls = {"n": 0}

    def _fake(symbol, **kw):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return _mk_df(500)

    monkeypatch.setattr(yl, "_fetch_yf", _fake)
    yl.load_yahoo_series("^W5000", cache_dir=tmp_cache_dir)
    assert calls["n"] == 1
    yl.load_yahoo_series("^W5000", cache_dir=tmp_cache_dir)
    assert calls["n"] == 1  # served from cache


# ---------------------------------------------------------------------------
# Y4 -- empty DataFrame -> DataValidationError
# ---------------------------------------------------------------------------


def test_Y4_empty_df_raises(monkeypatch: pytest.MonkeyPatch, tmp_cache_dir: Path) -> None:
    monkeypatch.setattr(yl, "_fetch_yf", lambda symbol, **kw: pd.DataFrame())
    with pytest.raises(DataValidationError):
        yl.load_yahoo_series("^W5000", cache_dir=tmp_cache_dir)


# ---------------------------------------------------------------------------
# Y5 -- rate-limit message triggers NetworkError
# ---------------------------------------------------------------------------


def test_Y5_rate_limit_wraps_to_network_error(
    monkeypatch: pytest.MonkeyPatch, tmp_cache_dir: Path
) -> None:
    def _boom(symbol, **kw):  # type: ignore[no-untyped-def]
        raise yl.NetworkError("yfinance rate-limited: try later")

    monkeypatch.setattr(yl, "_fetch_yf", _boom)
    with pytest.raises(NetworkError):
        yl.load_yahoo_series("^W5000", cache_dir=tmp_cache_dir)


# ---------------------------------------------------------------------------
# Y6 -- load_wilshire_yahoo selects longest history
# ---------------------------------------------------------------------------


def test_Y6_longest_history_wins(monkeypatch: pytest.MonkeyPatch, tmp_cache_dir: Path) -> None:
    lengths = {"^W5000": 300, "^FTW5000": 1500, "^W5000FLT": 800}

    def _fake(symbol, **kw):  # type: ignore[no-untyped-def]
        return _mk_df(lengths[symbol])

    monkeypatch.setattr(yl, "_fetch_yf", _fake)
    best = yl.load_wilshire_yahoo(cache_dir=tmp_cache_dir)
    assert best.symbol == "^FTW5000"
    assert len(best.data) == 1500


# ---------------------------------------------------------------------------
# Y7 -- all chain symbols fail
# ---------------------------------------------------------------------------


def test_Y7_all_fail(monkeypatch: pytest.MonkeyPatch, tmp_cache_dir: Path) -> None:
    def _fake(symbol, **kw):  # type: ignore[no-untyped-def]
        raise yl.NetworkError(f"no data for {symbol}")

    monkeypatch.setattr(yl, "_fetch_yf", _fake)
    with pytest.raises(NetworkError) as exc:
        yl.load_wilshire_yahoo(cache_dir=tmp_cache_dir)
    msg = exc.value.user_message
    assert "Wilshire" in msg


# ---------------------------------------------------------------------------
# Y8 -- integration (real network, opt-in)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_Y8_real_w5000(tmp_cache_dir: Path) -> None:
    if os.environ.get("INTEGRATION_TESTS") != "1":
        pytest.skip("INTEGRATION_TESTS!=1")
    s = yl.load_wilshire_yahoo(cache_dir=tmp_cache_dir, force_refresh=True)
    age = (pd.Timestamp.utcnow().tz_localize(None) - s.data.index.max()).days
    assert age <= 7
