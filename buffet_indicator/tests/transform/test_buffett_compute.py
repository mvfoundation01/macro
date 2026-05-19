"""Tests for src.transform.buffett_compute."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.transform.buffett_compute import compute_bi_variants


def _mk_aligned(n: int = 24) -> pd.DataFrame:
    idx = pd.date_range("2024-01-31", periods=n, freq="ME")
    return pd.DataFrame(
        {
            "gdp_t": [30.0 + 0.1 * i for i in range(n)],
            "equities_all_t": [90.0 + 0.5 * i for i in range(n)],
            "wilshire_usd_t": [70.0 + 0.3 * i for i in range(n)],
            "spx": [5000.0 + 50.0 * i for i in range(n)],
        },
        index=idx,
    )


def test_B1_all_three_keys_present() -> None:
    out = compute_bi_variants(_mk_aligned())
    assert set(out.keys()) == {"bi_allequity_pct", "bi_wilshire_pct", "bi_spx_proxy"}


def test_B2_missing_wilshire_drops_that_variant() -> None:
    df = _mk_aligned().drop(columns=["wilshire_usd_t"])
    out = compute_bi_variants(df)
    assert "bi_wilshire_pct" not in out
    assert "bi_allequity_pct" in out
    assert "bi_spx_proxy" in out


def test_B3_known_inputs_known_output() -> None:
    df = pd.DataFrame(
        {"gdp_t": [32.0], "equities_all_t": [96.0]},
        index=pd.DatetimeIndex([pd.Timestamp("2026-04-30")]),
    )
    out = compute_bi_variants(df)
    assert out["bi_allequity_pct"].iloc[0] == pytest.approx(300.0, abs=0.1)


def test_B3_bi_spx_mean_matches_wilshire_over_common_window() -> None:
    # Build a long aligned DF with all 4 columns; common window length must be >= 60.
    n = 240
    idx = pd.date_range("2005-01-31", periods=n, freq="ME")
    df = pd.DataFrame(
        {
            "gdp_t": [20.0 + 0.05 * i for i in range(n)],
            "wilshire_usd_t": [25.0 + 0.07 * i for i in range(n)],
            "spx": [1000.0 + 5.0 * i for i in range(n)],
        },
        index=idx,
    )
    out = compute_bi_variants(df)
    common = out["bi_spx_proxy"].index.intersection(out["bi_wilshire_pct"].index)
    spx_mean = float(out["bi_spx_proxy"].loc[common].mean())
    wil_mean = float(out["bi_wilshire_pct"].loc[common].mean())
    # Within 1% of each other -- the spec target.
    assert abs(spx_mean - wil_mean) / wil_mean < 0.01


def test_B4_nan_in_input_drops_from_output() -> None:
    df = _mk_aligned()
    df.loc[df.index[5], "gdp_t"] = float("nan")
    out = compute_bi_variants(df)
    # The row with NaN should not appear in any output series.
    for s in out.values():
        assert pd.Timestamp(df.index[5]) not in s.index


def test_B5_output_indices_align_with_input() -> None:
    df = _mk_aligned()
    out = compute_bi_variants(df)
    for s in out.values():
        assert s.index.isin(df.index).all()


def test_B6_scale_factor_vs_raw_recorded() -> None:
    n = 200
    idx = pd.date_range("2005-01-31", periods=n, freq="ME")
    df = pd.DataFrame(
        {
            "gdp_t": [20.0 + 0.05 * i for i in range(n)],
            "wilshire_usd_t": [30.0 + 0.07 * i for i in range(n)],
            "spx": [1500.0 + 8.0 * i for i in range(n)],
        },
        index=idx,
    )
    out = compute_bi_variants(df)
    k = out["bi_spx_proxy"].attrs.get("scale_factor_vs_raw")
    assert k is not None
    # k should be non-trivial (raw SPX/gdp x100 is ~7500 here; wilshire is ~150).
    assert k > 0
    assert abs(k - 1.0) > 0.01


def test_B7_no_wilshire_overlap_yields_raw_proxy_with_attrs() -> None:
    # bi_wilshire_pct present but ZERO overlap with bi_spx_proxy.
    df = pd.DataFrame(
        {
            "gdp_t": [20.0] * 240,
            "wilshire_usd_t": [25.0] * 240,
        },
        index=pd.date_range("1990-01-31", periods=240, freq="ME"),
    )
    spx_df = pd.DataFrame(
        {
            "gdp_t": [20.0] * 60,
            "spx": [3000.0] * 60,
        },
        index=pd.date_range("2030-01-31", periods=60, freq="ME"),
    )
    combined = pd.concat([df, spx_df])
    out = compute_bi_variants(combined)
    assert "bi_spx_proxy" in out
    # No overlap window -> raw fallback flagged in attrs.
    assert out["bi_spx_proxy"].attrs["scale_factor_vs_raw"] == 1.0
    assert "insufficient overlap" in out["bi_spx_proxy"].attrs["scale_anchor"]


def test_B8_zscore_invariance_under_spx_rescale() -> None:
    """Scaling by a positive constant must not change z-scores or percentiles."""
    n = 240
    idx = pd.date_range("2005-01-31", periods=n, freq="ME")
    df = pd.DataFrame(
        {
            "gdp_t": [20.0 + 0.05 * i for i in range(n)],
            "wilshire_usd_t": [25.0 + 0.07 * i for i in range(n)],
            "spx": [1000.0 + 5.0 * i for i in range(n)],
        },
        index=idx,
    )
    out = compute_bi_variants(df)
    scaled = out["bi_spx_proxy"]
    k = scaled.attrs["scale_factor_vs_raw"]
    raw = scaled / k
    # Z-scores
    z_scaled = (scaled - scaled.mean()) / scaled.std(ddof=1)
    z_raw = (raw - raw.mean()) / raw.std(ddof=1)
    pd.testing.assert_series_equal(z_scaled, z_raw, check_names=False, atol=1e-12)


def test_B_no_wilshire_in_input_yields_raw_proxy() -> None:
    """If no bi_wilshire_pct can be computed, bi_spx_proxy stays raw."""
    df = pd.DataFrame(
        {
            "gdp_t": [20.0 + 0.05 * i for i in range(200)],
            "spx": [3000.0 + 5.0 * i for i in range(200)],
        },
        index=pd.date_range("2005-01-31", periods=200, freq="ME"),
    )
    out = compute_bi_variants(df)
    assert "bi_wilshire_pct" not in out
    assert out["bi_spx_proxy"].attrs["scale_factor_vs_raw"] == 1.0
    assert "no BI-Wilshire" in out["bi_spx_proxy"].attrs["scale_anchor"]
