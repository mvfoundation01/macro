"""Tests for the new ICE DXY priority-chain + DTWEXBGS splice path in
``src.ingest.lc_v1_loader`` — added in Session 6 §2.0 to resolve the Stooq
blocker (``specs/BLOCKED_v11_3_A1_icedxy_stooq.md``).

Test layout
-----------
- T-N* — source priority chain (Norgate, yfinance, local cache, errors).
- T-S* — DTWEXBGS splice algorithm + gates (corr, z-divergence).
- T-A* — look-ahead audit (the splice algorithm uses no future data).
- T-I* — integration tests (gated by INTEGRATION_TESTS=1).

References
----------
- specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.3 — sealed splice spec.
- prompt/052226/PROMPT_v11_3_stage_3_LC_v1_session_6.md §2.0 — Session 6 instructions.
- data/master/_source_policy.json — formal priority record.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ingest import lc_v1_loader as lc


# ---------------------------------------------------------------------------
# Helpers — synthetic daily price series.
# ---------------------------------------------------------------------------


def _mk_daily_series(
    *,
    start: str,
    end: str,
    initial: float,
    annual_drift: float = 0.0,
    annual_vol: float = 0.05,
    seed: int = 0,
) -> pd.Series:
    """Generate a synthetic daily price series with mild log-Brownian drift."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(seed)
    n = len(idx)
    daily_mu = annual_drift / 252.0
    daily_sigma = annual_vol / np.sqrt(252.0)
    log_returns = rng.normal(daily_mu, daily_sigma, size=n)
    log_returns[0] = 0.0
    log_levels = np.cumsum(log_returns) + np.log(initial)
    return pd.Series(np.exp(log_levels), index=idx, name="icedxy_close")


def _mk_dtwexbgs_anchored_to_dxy(
    dxy_daily: pd.Series,
    *,
    anchor_date: str = "2006-01-04",
    scale: float = 1.40,
    extra_noise_sigma: float = 0.0,
    seed: int = 1,
) -> pd.Series:
    """Build a synthetic DTWEXBGS daily series that closely tracks ``dxy_daily``
    in the splice overlap, then drifts away. Used to construct PASS-gate cases.
    """
    dtw = dxy_daily.copy() * scale
    if extra_noise_sigma > 0:
        rng = np.random.default_rng(seed)
        noise = rng.normal(0.0, extra_noise_sigma, size=len(dtw))
        dtw = dtw * np.exp(noise)
    dtw = dtw.loc[dtw.index >= pd.Timestamp(anchor_date) - pd.Timedelta(days=400)]
    dtw.name = "dtwexbgs"
    return dtw


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_dxy_daily() -> pd.Series:
    """Daily ICE DXY series covering 2003-01 .. 2010-12 for splice tests."""
    return _mk_daily_series(
        start="2003-01-01", end="2010-12-31",
        initial=85.0, annual_drift=0.0, annual_vol=0.06, seed=7,
    )


@pytest.fixture
def synthetic_dtwexbgs_daily(synthetic_dxy_daily: pd.Series) -> pd.Series:
    """Daily DTWEXBGS series that tracks the ICE DXY closely (PASS-gate setup)."""
    return _mk_dtwexbgs_anchored_to_dxy(
        synthetic_dxy_daily, scale=1.40, extra_noise_sigma=0.002,
    )


@pytest.fixture
def tmp_cache_path(tmp_path: Path) -> Path:
    """Temp parquet path where tests can stash a synthetic ICE DXY cache."""
    return tmp_path / "icedxy_close.parquet"


def _write_cache(daily: pd.Series, path: Path) -> None:
    """Write the test cache parquet using the loader's helper."""
    lc.write_icedxy_cache_parquet(daily, cache_path=path, source_label="test_synthetic")


# ===========================================================================
# T-N* — Source priority chain
# ===========================================================================


def test_TN1_norgate_injected_synthetic_fetches_correctly(
    synthetic_dxy_daily: pd.Series,
    synthetic_dtwexbgs_daily: pd.Series,
) -> None:
    """T-N1: Norgate-injected synthetic series fetches correctly."""
    spliced = lc.build_lc_icedxy_master(
        norgate_data=synthetic_dxy_daily,
        dtwexbgs_data=synthetic_dtwexbgs_daily,
        splice_dtwexbgs=True,
    )
    assert isinstance(spliced, pd.Series)
    assert len(spliced) > 0
    assert spliced.attrs["source"] == "norgate_injected"
    # Spliced output is monthly EOM by construction.
    diffs = spliced.index.to_series().diff().dropna()
    assert (diffs > pd.Timedelta(days=20)).all()


def test_TN2_yfinance_injected_synthetic_fetches_correctly(
    synthetic_dxy_daily: pd.Series,
    synthetic_dtwexbgs_daily: pd.Series,
) -> None:
    """T-N2: yfinance-injected synthetic series fetches correctly."""
    spliced = lc.build_lc_icedxy_master(
        yfinance_data=synthetic_dxy_daily,
        dtwexbgs_data=synthetic_dtwexbgs_daily,
        splice_dtwexbgs=True,
    )
    assert spliced.attrs["source"] == "yfinance_injected"
    assert len(spliced) > 0


def test_TN3_local_parquet_read_path_works(
    synthetic_dxy_daily: pd.Series,
    synthetic_dtwexbgs_daily: pd.Series,
    tmp_cache_path: Path,
) -> None:
    """T-N3: Local-parquet read path works when both Norgate + yfinance disabled."""
    _write_cache(synthetic_dxy_daily, tmp_cache_path)
    spliced = lc.build_lc_icedxy_master(
        cache_parquet_path=tmp_cache_path,
        dtwexbgs_data=synthetic_dtwexbgs_daily,
        splice_dtwexbgs=True,
    )
    assert spliced.attrs["source"].startswith("cache:")
    assert tmp_cache_path.name in spliced.attrs["source"]


def test_TN4_priority_norgate_beats_yfinance(
    synthetic_dxy_daily: pd.Series,
    synthetic_dtwexbgs_daily: pd.Series,
) -> None:
    """T-N4: Norgate beats yfinance when both supplied."""
    norgate_series = synthetic_dxy_daily * 1.0  # canonical
    # Make yfinance distinguishable — same shape but 10x scale.
    yf_series = synthetic_dxy_daily * 10.0

    spliced = lc.build_lc_icedxy_master(
        norgate_data=norgate_series,
        yfinance_data=yf_series,
        dtwexbgs_data=synthetic_dtwexbgs_daily,
        splice_dtwexbgs=False,
    )
    # Without splice, output is log of monthly EOM of the Norgate series.
    expected = np.log(norgate_series.resample("ME").last().dropna())
    pd.testing.assert_series_equal(
        spliced, expected, check_names=False, check_exact=False, atol=1e-12,
    )


def test_TN5_priority_yfinance_beats_local_parquet(
    synthetic_dxy_daily: pd.Series,
    synthetic_dtwexbgs_daily: pd.Series,
    tmp_cache_path: Path,
) -> None:
    """T-N5: yfinance beats local-parquet when Norgate disabled."""
    # Cache has DIFFERENT data than yfinance series so we can tell them apart.
    cache_series = synthetic_dxy_daily * 0.5
    _write_cache(cache_series, tmp_cache_path)

    spliced = lc.build_lc_icedxy_master(
        yfinance_data=synthetic_dxy_daily,
        cache_parquet_path=tmp_cache_path,
        dtwexbgs_data=synthetic_dtwexbgs_daily,
        splice_dtwexbgs=False,
    )
    expected = np.log(synthetic_dxy_daily.resample("ME").last().dropna())
    pd.testing.assert_series_equal(
        spliced, expected, check_names=False, check_exact=False, atol=1e-12,
    )


def test_TN6_runtime_error_when_all_sources_disabled_and_cache_missing(
    tmp_cache_path: Path,
) -> None:
    """T-N6: RuntimeError when all sources disabled and cache missing."""
    assert not tmp_cache_path.exists()
    with pytest.raises(RuntimeError, match="ICE DXY cache parquet missing"):
        lc.build_lc_icedxy_master(
            cache_parquet_path=tmp_cache_path,
            splice_dtwexbgs=False,
        )


# ===========================================================================
# T-S* — DTWEXBGS splice algorithm + gates
# ===========================================================================


def test_TS1_splice_pass_case_returns_continuous_spliced_series(
    synthetic_dxy_daily: pd.Series,
    synthetic_dtwexbgs_daily: pd.Series,
) -> None:
    """T-S1: Splice gate corr > 0.85 PASS case — output is continuous."""
    spliced = lc.build_lc_icedxy_master(
        norgate_data=synthetic_dxy_daily,
        dtwexbgs_data=synthetic_dtwexbgs_daily,
        splice_dtwexbgs=True,
    )
    # Verify the splice metadata was recorded.
    assert "splice_additive" in spliced.attrs["transform"]
    assert spliced.attrs["splice_date"] == str(lc.ICEDXY_SPLICE_DATE.date())
    # Spliced series should span both pre- and post-splice dates.
    pre = spliced.loc[spliced.index < lc.ICEDXY_SPLICE_DATE]
    post = spliced.loc[spliced.index >= lc.ICEDXY_SPLICE_DATE]
    assert len(pre) > 0
    assert len(post) > 0


def test_TS2_splice_gate_corr_fail_raises_valueerror() -> None:
    """T-S2: corr < 0.85 → ValueError."""
    # Build two log series that are nearly anti-correlated in the overlap window.
    idx_monthly = pd.date_range("2005-09-30", "2006-04-30", freq="ME")
    log_dxy = pd.Series(
        [4.50, 4.52, 4.50, 4.52, 4.50, 4.52, 4.50, 4.52], index=idx_monthly,
    )
    log_dtw = pd.Series(
        [4.81, 4.79, 4.81, 4.79, 4.81, 4.79, 4.81, 4.79], index=idx_monthly,
    )
    with pytest.raises(ValueError, match="GATE FAIL: corr="):
        lc._splice_log_dxy_with_dtwexbgs(log_dxy, log_dtw)


def test_TS3_splice_gate_z_divergence_fail_raises_valueerror() -> None:
    """T-S3: z-divergence ≥ 0.30 → ValueError (corr gate passes first).

    Construction targets the 4-point overlap (±2 months around 2006-01-04 on
    monthly EOM grid: 2005-11, 2005-12, 2006-01, 2006-02). dxy is a linear
    ramp, dtw is a linear ramp with a single shape-disturbing outlier at the
    2006-01 row — this keeps corr above 0.85 (linear structure dominates)
    while pushing mean |z-divergence| above the 0.30 gate.
    """
    idx_monthly = pd.date_range("2005-09-30", "2006-04-30", freq="ME")
    # 8 monthly EOM points: ..., 11-30, 12-31, 01-31, 02-28, ...
    # Only the middle 4 fall inside the ±2-month overlap window.
    # Use matching slopes (0.02 per step) so baseline corr is ~1; the outlier
    # then perturbs z-divergence past 0.30 while corr drops only to ~0.88.
    log_dxy = pd.Series(
        np.linspace(4.40, 4.54, len(idx_monthly)), index=idx_monthly,
    )
    log_dtw_values = np.linspace(4.80, 4.94, len(idx_monthly))
    pos_jan = idx_monthly.get_loc(pd.Timestamp("2006-01-31"))
    log_dtw_values[pos_jan] += 0.035  # tuned: corr ~0.876, z-div ~0.351
    log_dtw = pd.Series(log_dtw_values, index=idx_monthly)

    with pytest.raises(ValueError, match=r"GATE FAIL: mean\|z-div\|"):
        lc._splice_log_dxy_with_dtwexbgs(log_dxy, log_dtw)


def test_TS4_spliced_series_continuous_at_boundary(
    synthetic_dxy_daily: pd.Series,
    synthetic_dtwexbgs_daily: pd.Series,
) -> None:
    """T-S4: Spliced series has continuous values at 2006-01-04 boundary
    (consecutive-row delta bounded vs typical monthly volatility)."""
    spliced = lc.build_lc_icedxy_master(
        norgate_data=synthetic_dxy_daily,
        dtwexbgs_data=synthetic_dtwexbgs_daily,
        splice_dtwexbgs=True,
    )
    # The boundary occurs at the first row >= 2006-01-04.
    spliced_sorted = spliced.sort_index()
    deltas = spliced_sorted.diff().abs().dropna()
    # Quantile of typical monthly log-return moves elsewhere in the series.
    p99 = float(deltas.quantile(0.99))
    # Find the row at or just after the splice date.
    post_idx = spliced_sorted.index >= lc.ICEDXY_SPLICE_DATE
    if post_idx.any():
        first_post = spliced_sorted.loc[post_idx].index[0]
        # The row immediately before first_post is the last pre-splice row.
        i_raw = spliced_sorted.index.get_loc(first_post)
        # get_loc returns int for unique indices (our case); cast for mypy.
        assert isinstance(i_raw, int)
        i: int = i_raw
        if i > 0:
            boundary_jump = abs(spliced_sorted.iloc[i] - spliced_sorted.iloc[i - 1])
            assert boundary_jump <= p99 * 1.5, (
                f"Boundary jump {boundary_jump:.4f} > 1.5 × p99={p99:.4f} "
                f"(spec §2.4.6 gate 4 continuity)"
            )


def test_TS5_transform_attr_format(
    synthetic_dxy_daily: pd.Series,
    synthetic_dtwexbgs_daily: pd.Series,
) -> None:
    """T-S5: ``Series.attrs['transform']`` correctly records
    ``splice_additive:+{c:.6f}@2006-01-04`` per master spec §2.4.3."""
    spliced = lc.build_lc_icedxy_master(
        norgate_data=synthetic_dxy_daily,
        dtwexbgs_data=synthetic_dtwexbgs_daily,
        splice_dtwexbgs=True,
    )
    transform = spliced.attrs["transform"]
    # Format: splice_additive:+{c:.6f}@YYYY-MM-DD or splice_additive:-{...}@...
    assert transform.startswith("splice_additive:")
    assert transform.endswith(f"@{lc.ICEDXY_SPLICE_DATE.date()}")
    # The c value is also stored separately as a float.
    assert isinstance(spliced.attrs["splice_c"], float)


# ===========================================================================
# T-A* — Look-ahead audit
# ===========================================================================


def test_TA1_lookahead_no_rows_past_input_horizon(
    synthetic_dxy_daily: pd.Series,
    synthetic_dtwexbgs_daily: pd.Series,
) -> None:
    """T-A1: Vintage-T snapshot contains no rows with date > T.

    The splice algorithm depends only on the overlap window (±2 months around
    2006-01-04). If we truncate inputs to date T, the output extends no
    further than T (modulo month-end alignment).
    """
    T = pd.Timestamp("2020-12-31")
    dxy_trunc = synthetic_dxy_daily.loc[synthetic_dxy_daily.index <= T]
    dtw_trunc = synthetic_dtwexbgs_daily.loc[synthetic_dtwexbgs_daily.index <= T]
    spliced = lc.build_lc_icedxy_master(
        norgate_data=dxy_trunc,
        dtwexbgs_data=dtw_trunc,
        splice_dtwexbgs=True,
    )
    # Output must not contain any date > T (allowing for EOM normalization).
    assert (spliced.index <= T).all(), (
        f"Look-ahead violation: {(spliced.index > T).sum()} output rows past T={T.date()}"
    )


# ===========================================================================
# Error-path coverage for live fetchers + helpers
# ===========================================================================


def test_TN7_norgate_live_raises_when_package_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-N7: ``use_norgate_live=True`` with norgatedata absent → RuntimeError."""
    monkeypatch.setattr(lc, "_norgatedata", None)
    with pytest.raises(RuntimeError, match="norgatedata package not installed"):
        lc.build_lc_icedxy_master(use_norgate_live=True, splice_dtwexbgs=False)


def test_TN8_yfinance_live_raises_when_package_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-N8: ``use_yfinance_live=True`` with yfinance absent → RuntimeError."""
    monkeypatch.setattr(lc, "_yfinance", None)
    with pytest.raises(RuntimeError, match="yfinance package not installed"):
        lc.build_lc_icedxy_master(use_yfinance_live=True, splice_dtwexbgs=False)


def test_TN9_cache_parquet_missing_value_column_raises(tmp_path: Path) -> None:
    """T-N9: cache parquet without a 'value' column → DataValidationError."""
    bad_path = tmp_path / "broken.parquet"
    df = pd.DataFrame({"close": [1.0, 2.0]}, index=pd.date_range("2020-01-01", periods=2))
    df.to_parquet(bad_path)
    from src.ingest._base import DataValidationError
    with pytest.raises(DataValidationError, match="missing 'value' column"):
        lc.build_lc_icedxy_master(
            cache_parquet_path=bad_path, splice_dtwexbgs=False,
        )


def test_TS6_splice_insufficient_overlap_raises() -> None:
    """T-S6: <2 overlap rows → ValueError (insufficient overlap)."""
    # Singleton overlap point — no way to compute corr / std.
    idx = pd.DatetimeIndex([pd.Timestamp("2006-01-31")])
    log_dxy = pd.Series([4.50], index=idx)
    log_dtw = pd.Series([4.80], index=idx)
    with pytest.raises(ValueError, match="insufficient overlap"):
        lc._splice_log_dxy_with_dtwexbgs(log_dxy, log_dtw)


def test_TS7_splice_zero_std_raises() -> None:
    """T-S7: zero std in overlap → ValueError (zero/NaN std gate)."""
    idx = pd.date_range("2005-09-30", "2006-04-30", freq="ME")
    # Constant series → std = 0.
    log_dxy = pd.Series([4.50] * len(idx), index=idx)
    log_dtw = pd.Series([4.80] * len(idx), index=idx)
    with pytest.raises(ValueError, match="zero/NaN std"):
        lc._splice_log_dxy_with_dtwexbgs(log_dxy, log_dtw)


def test_TN10_dtwexbgs_resolver_loads_via_load_master(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_dxy_daily: pd.Series,
    synthetic_dtwexbgs_daily: pd.Series,
) -> None:
    """T-N10: ``dtwexbgs_data=None`` triggers a load_master() fallback."""

    class _FakeMaster:
        def __init__(self, data: pd.Series) -> None:
            self.data = data

    def _fake_load_master(series_id: str, **kwargs: object) -> _FakeMaster:
        assert series_id == "dtwexbgs"
        return _FakeMaster(synthetic_dtwexbgs_daily)

    # The function uses a lazy import inside the function body, so patch the
    # source module attribute (the one returned by `from src.ingest.master_archive
    # import load_master`).
    import src.ingest.master_archive as ma
    monkeypatch.setattr(ma, "load_master", _fake_load_master)

    spliced = lc.build_lc_icedxy_master(
        norgate_data=synthetic_dxy_daily,
        # dtwexbgs_data deliberately omitted → resolver hits load_master.
        splice_dtwexbgs=True,
    )
    assert len(spliced) > 0
    assert "splice_additive" in spliced.attrs["transform"]


def test_TW1_write_cache_rejects_empty_series(tmp_path: Path) -> None:
    """T-W1: write_icedxy_cache_parquet rejects an empty input series."""
    from src.ingest._base import DataValidationError
    empty = pd.Series([], dtype="float64", index=pd.DatetimeIndex([]))
    with pytest.raises(DataValidationError, match="input series is empty"):
        lc.write_icedxy_cache_parquet(empty, cache_path=tmp_path / "empty.parquet")


# ===========================================================================
# Integration tests (gated by INTEGRATION_TESTS=1).
# ===========================================================================


@pytest.mark.integration
def test_TI3_real_yfinance_dxy_returns_non_empty_series() -> None:
    """T-I3: Real yfinance fetch for DX-Y.NYB returns non-empty series 1985+."""
    if os.environ.get("INTEGRATION_TESTS") != "1":
        pytest.skip("set INTEGRATION_TESTS=1 to run")
    if getattr(lc, "_yfinance", None) is None:
        pytest.skip("yfinance package not installed")
    series = lc._fetch_yfinance_dxy_live()
    assert len(series) > 1000
    assert series.index.min() <= pd.Timestamp("1990-01-01")
