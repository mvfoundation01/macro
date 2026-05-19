"""Tests for src.ingest.fred_loader."""
from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import pandas as pd
import pytest
import responses
from freezegun import freeze_time

from src.ingest import fred_loader as fl
from src.ingest._base import (
    APIKeyError,
    DataValidationError,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


VALID_KEY = "a" * 32  # matches ^[a-z0-9]{32}$


def _mk_obs(start: str = "1947-01-01", n: int = 20, freq: str = "Q") -> list[dict[str, str]]:
    idx = pd.date_range(start, periods=n, freq=freq + "S" if freq == "Q" else freq)
    return [{"date": str(d.date()), "value": str(100.0 + i)} for i, d in enumerate(idx)]


def _register_meta(api_key: str, series_id: str = "GDP", frequency: str = "Q") -> None:
    responses.add(
        responses.GET,
        fl.FRED_META_URL,
        match=[
            responses.matchers.query_param_matcher(
                {
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                }
            )
        ],
        json={
            "seriess": [
                {
                    "id": series_id,
                    "frequency_short": frequency,
                    "units_short": "Bil. of $",
                    "last_updated": "2026-05-01 08:00:00-05",
                }
            ]
        },
        status=200,
    )


def _register_obs(
    api_key: str,
    observations: list[dict[str, str]],
    series_id: str = "GDP",
    status: int = 200,
    observation_start: str = "1945-01-01",
) -> None:
    body: object = (
        {"observations": observations} if status == 200 else {"error": "bad"}
    )
    responses.add(
        responses.GET,
        fl.FRED_OBS_URL,
        match=[
            responses.matchers.query_param_matcher(
                {
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "observation_start": observation_start,
                }
            )
        ],
        json=body,
        status=status,
    )


# ---------------------------------------------------------------------------
# F1 -- happy path
# ---------------------------------------------------------------------------


@responses.activate
def test_F1_happy_path(tmp_cache_dir: Path) -> None:
    _register_meta(VALID_KEY)
    _register_obs(VALID_KEY, _mk_obs(n=20))

    s = fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)

    assert isinstance(s, fl.FredSeries)
    assert s.series_id == "GDP"
    assert s.frequency == "Q"
    assert len(s.data) == 20
    assert s.cache_path.exists()
    assert (tmp_cache_dir / "GDP.meta.json").exists()


# ---------------------------------------------------------------------------
# F2 -- end-of-period normalization (1947-01-01 -> 1947-03-31)
# ---------------------------------------------------------------------------


@responses.activate
def test_F2_end_of_period_normalization(tmp_cache_dir: Path) -> None:
    _register_meta(VALID_KEY)
    _register_obs(VALID_KEY, _mk_obs(start="1947-01-01", n=12, freq="Q"))

    s = fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)
    assert s.data.index[0] == pd.Timestamp("1947-03-31")
    assert s.data.index[1] == pd.Timestamp("1947-06-30")


# ---------------------------------------------------------------------------
# F3 -- "." -> NaN
# ---------------------------------------------------------------------------


@responses.activate
def test_F3_missing_value_dot(tmp_cache_dir: Path) -> None:
    obs = _mk_obs(n=30)
    obs[5]["value"] = "."
    _register_meta(VALID_KEY)
    _register_obs(VALID_KEY, obs)

    s = fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)
    assert pd.isna(s.data.iloc[5])
    assert s.data.isna().sum() == 1


# ---------------------------------------------------------------------------
# F4 -- cache hit within TTL (zero HTTP calls on second invocation)
# ---------------------------------------------------------------------------


@responses.activate
def test_F4_cache_hit_within_ttl(tmp_cache_dir: Path) -> None:
    _register_meta(VALID_KEY)
    _register_obs(VALID_KEY, _mk_obs(n=20))

    s1 = fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)
    n_before = len(responses.calls)
    s2 = fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)
    n_after = len(responses.calls)
    assert n_after == n_before  # cache hit, no extra HTTP
    pd.testing.assert_series_equal(s1.data, s2.data, check_names=False)


# ---------------------------------------------------------------------------
# F5 -- cache stale: freezegun + 25h -> HTTP called again
# ---------------------------------------------------------------------------


@responses.activate
def test_F5_cache_stale_after_ttl(tmp_cache_dir: Path) -> None:
    _register_meta(VALID_KEY)
    _register_obs(VALID_KEY, _mk_obs(n=20))
    # Allow a second meta+obs round (responses is permissive about same-URL reuse).
    _register_meta(VALID_KEY)
    _register_obs(VALID_KEY, _mk_obs(n=20))

    with freeze_time("2026-01-01 00:00:00") as frozen:
        fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)
        n_after_first = len(responses.calls)
        frozen.tick(timedelta(hours=25))
        fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)
        n_after_second = len(responses.calls)

    assert n_after_second > n_after_first


# ---------------------------------------------------------------------------
# F6 -- invalid api_key format -> APIKeyError
# ---------------------------------------------------------------------------


def test_F6_invalid_api_key_format(tmp_cache_dir: Path) -> None:
    with pytest.raises(APIKeyError):
        fl.load_fred_series("GDP", "not-a-real-key", cache_dir=tmp_cache_dir)


# ---------------------------------------------------------------------------
# F7 -- 403 response -> APIKeyError, no retry
# ---------------------------------------------------------------------------


@responses.activate
def test_F7_403_rejects_immediately(tmp_cache_dir: Path) -> None:
    responses.add(
        responses.GET,
        fl.FRED_META_URL,
        json={"error": "forbidden"},
        status=403,
    )
    with pytest.raises(APIKeyError):
        fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)
    # Only ONE call should have been made (no retry).
    assert len(responses.calls) == 1


# ---------------------------------------------------------------------------
# F8 -- 429 then 429 then 200 -> retry kicks in (>=3 calls)
# ---------------------------------------------------------------------------


@responses.activate
def test_F8_429_retries(tmp_cache_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Make tenacity sleep instant.
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda *_: None)

    # Two 429s, then meta 200, then obs 200.
    responses.add(responses.GET, fl.FRED_META_URL, json={"error": "rate"}, status=429)
    responses.add(responses.GET, fl.FRED_META_URL, json={"error": "rate"}, status=429)
    responses.add(
        responses.GET,
        fl.FRED_META_URL,
        json={
            "seriess": [
                {
                    "id": "GDP",
                    "frequency_short": "Q",
                    "units_short": "Bil. of $",
                    "last_updated": "2026-05-01 08:00:00-05",
                }
            ]
        },
        status=200,
    )
    responses.add(
        responses.GET,
        fl.FRED_OBS_URL,
        json={"observations": _mk_obs(n=20)},
        status=200,
    )

    fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)
    # 3 calls to meta (2x 429 + 1x 200) + 1 to obs
    assert len(responses.calls) >= 3


# ---------------------------------------------------------------------------
# F9 -- api_key never appears in log records
# ---------------------------------------------------------------------------


@responses.activate
def test_F9_api_key_redacted_in_logs(tmp_cache_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    _register_meta(VALID_KEY)
    _register_obs(VALID_KEY, _mk_obs(n=15))

    with caplog.at_level(logging.DEBUG, logger="buffett.ingest.fred"):
        fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)

    for rec in caplog.records:
        assert VALID_KEY not in rec.getMessage()


# ---------------------------------------------------------------------------
# F10 -- load_buffett_fred returns dict with all 4 expected keys
# ---------------------------------------------------------------------------


@responses.activate
def test_F10_load_buffett_fred_all_keys(tmp_cache_dir: Path) -> None:
    for key, info in fl.FRED_CATALOG.items():
        sid = info["series_id"]
        _register_meta(VALID_KEY, series_id=sid)
        # Make values small for equities so cross-series sanity passes.
        obs = _mk_obs(start="1947-01-01", n=20, freq="Q")
        if key.startswith("equities"):
            for i, o in enumerate(obs):
                o["value"] = str(1000.0 + i)
            if key == "equities_all":
                for i, o in enumerate(obs):
                    o["value"] = str(5000.0 + i)
        _register_obs(VALID_KEY, obs, series_id=sid)

    # Freeze "now" inside the freshness window so the optional warning is silent.
    with freeze_time("2026-05-18"):
        out = fl.load_buffett_fred(
            VALID_KEY,
            cache_dir=tmp_cache_dir,
            skip_freshness_check=True,
        )
    assert set(out.keys()) == {"gdp", "equities_all", "equities_public", "equities_nonfin"}
    for s in out.values():
        assert isinstance(s, fl.FredSeries)


# ---------------------------------------------------------------------------
# Additional sanity: too-short series fails validation
# ---------------------------------------------------------------------------


@responses.activate
def test_too_short_series_raises(tmp_cache_dir: Path) -> None:
    _register_meta(VALID_KEY)
    _register_obs(VALID_KEY, _mk_obs(n=5))  # below 10
    with pytest.raises(DataValidationError):
        fl.load_fred_series("GDP", VALID_KEY, cache_dir=tmp_cache_dir)
