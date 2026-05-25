"""v2.0 sprint Phase B.2 — splice helper tests.

Per sealed pre-reg §10.1 + PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md §3.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.transform.splice import (  # noqa: E402
    SpliceValidationError,
    _concat_ioer_iorb_impl,
    _splice_busloans_totll_yoy_impl,
    _splice_icedxy_dtwexbgs_log_impl,
    _splice_ted_sofr_iorb_zblend_impl,
    _yoy_growth,
    concat_ioer_iorb,
)


# ===========================================================================
# Splice 1: BUSLOANS -> TOTLL @ 1973-01-03 (YoY-growth-rate space)
# ===========================================================================


def _monthly(start: str, n: int) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="ME")


def test_busloans_totll_yoy_happy_path() -> None:
    """Synthetic series with high corr + small c -> gates pass, splice succeeds."""
    idx = _monthly("1955-01-31", 360)  # 30 years through 1984
    rng = np.random.default_rng(seed=11)
    base = pd.Series(0.03 + 0.001 * rng.normal(size=360), index=idx)
    bus_yoy = base + 0.0005 * rng.normal(size=360)
    tot_yoy = base + 0.005 + 0.0005 * rng.normal(size=360)  # constant offset c~=0.005

    spliced, meta = _splice_busloans_totll_yoy_impl(
        bus_yoy, tot_yoy, pd.Timestamp("1973-01-03")
    )
    assert meta["gates_passed"] is True
    assert meta["overlap_corr"] > 0.50
    assert abs(meta["constant_c"]) < 0.05
    assert spliced.name == "banklend_growth_yoy"
    # Pre-splice values shifted by c.
    assert spliced.loc[idx[0]] == pytest.approx(bus_yoy.loc[idx[0]] + meta["constant_c"], rel=1e-9)
    # Post-splice = TOTLL_yoy unchanged.
    post_dates = idx[idx >= pd.Timestamp("1973-01-03")]
    if len(post_dates) > 0:
        d = post_dates[0]
        assert spliced.loc[d] == pytest.approx(tot_yoy.loc[d], rel=1e-9)


def test_busloans_totll_yoy_low_corr_raises() -> None:
    """Uncorrelated series -> SpliceValidationError on corr gate."""
    idx = _monthly("1965-01-31", 200)
    rng = np.random.default_rng(seed=42)
    bus_yoy = pd.Series(rng.normal(size=200) * 0.02, index=idx)
    tot_yoy = pd.Series(rng.normal(size=200) * 0.02, index=idx)  # independent
    with pytest.raises(SpliceValidationError, match="correlation"):
        _splice_busloans_totll_yoy_impl(bus_yoy, tot_yoy, pd.Timestamp("1973-01-03"))


def test_busloans_totll_yoy_large_constant_raises() -> None:
    """|c| >= 0.05 -> SpliceValidationError on additive-constant gate."""
    idx = _monthly("1965-01-31", 200)
    rng = np.random.default_rng(seed=3)
    base = pd.Series(0.03 + 0.001 * rng.normal(size=200), index=idx)
    bus_yoy = base.copy()
    tot_yoy = base + 0.10  # huge constant offset
    with pytest.raises(SpliceValidationError, match=r"constant.*\|c\|"):
        _splice_busloans_totll_yoy_impl(bus_yoy, tot_yoy, pd.Timestamp("1973-01-03"))


def test_busloans_totll_yoy_insufficient_overlap_raises() -> None:
    """<6 overlapping observations -> SpliceValidationError."""
    bus_yoy = pd.Series(
        [0.03, 0.04], index=pd.DatetimeIndex(["1972-11-30", "1972-12-31"])
    )
    tot_yoy = pd.Series([0.03, 0.04], index=pd.DatetimeIndex(["1973-01-31", "1973-02-28"]))
    with pytest.raises(SpliceValidationError, match="insufficient overlap"):
        _splice_busloans_totll_yoy_impl(bus_yoy, tot_yoy, pd.Timestamp("1973-01-03"))


def test_yoy_growth_helper_matches_pct_change() -> None:
    s = pd.Series(np.arange(20.0) + 1.0, index=_monthly("2020-01-31", 20))
    yoy = _yoy_growth(s, periods=12)
    expected = s.pct_change(periods=12)
    pd.testing.assert_series_equal(yoy, expected, check_names=False)


# ===========================================================================
# Splice 2: ICE_DXY -> DTWEXBGS @ 2006-01-04 (log-levels space)
# ===========================================================================


def _bdays(start: str, n: int) -> pd.DatetimeIndex:
    return pd.bdate_range(start, periods=n)


def test_icedxy_dtwexbgs_log_happy_path() -> None:
    """Tight ICE/DTW relationship + small log-c -> gates pass."""
    idx = _bdays("2005-07-01", 400)
    rng = np.random.default_rng(seed=5)
    log_base = pd.Series(np.log(100.0) + 0.01 * np.cumsum(rng.normal(size=400)), index=idx)
    ice = pd.Series(np.exp(log_base + 0.005 * rng.normal(size=400)), index=idx)
    dtw = pd.Series(np.exp(log_base + 0.02 + 0.005 * rng.normal(size=400)), index=idx)

    spliced, meta = _splice_icedxy_dtwexbgs_log_impl(ice, dtw, pd.Timestamp("2006-01-04"))
    assert meta["gates_passed"] is True
    assert meta["overlap_corr"] > 0.85
    assert meta["mean_abs_z_divergence"] < 0.30
    assert spliced.name == "log_dxy_extended"


def test_icedxy_dtwexbgs_log_low_corr_raises() -> None:
    idx = _bdays("2005-07-01", 400)
    rng = np.random.default_rng(seed=99)
    ice = pd.Series(np.exp(np.log(100.0) + 0.05 * rng.normal(size=400)), index=idx)
    dtw = pd.Series(
        np.exp(np.log(120.0) + 0.05 * rng.normal(size=400)), index=idx
    )  # independent
    with pytest.raises(SpliceValidationError, match="correlation"):
        _splice_icedxy_dtwexbgs_log_impl(ice, dtw, pd.Timestamp("2006-01-04"))


def test_icedxy_dtwexbgs_log_insufficient_overlap_raises() -> None:
    ice = pd.Series([100.0, 101.0], index=pd.DatetimeIndex(["2005-12-30", "2006-01-02"]))
    dtw = pd.Series([100.0, 101.0], index=pd.DatetimeIndex(["2006-01-05", "2006-01-06"]))
    with pytest.raises(SpliceValidationError, match="insufficient overlap"):
        _splice_icedxy_dtwexbgs_log_impl(ice, dtw, pd.Timestamp("2006-01-04"))


# ===========================================================================
# Splice 3 pre-step: IOER -> IORB level concat @ 2021-07-29
# ===========================================================================


def test_concat_ioer_iorb_happy_path_synthetic() -> None:
    """Boundary diff < 0.01pp -> concat succeeds with gates_passed=True."""
    pre_idx = pd.bdate_range("2021-01-01", "2021-07-28")
    post_idx = pd.bdate_range("2021-07-29", "2021-12-31")
    ioer = pd.Series(0.10, index=pre_idx)  # 0.10%
    iorb = pd.Series(0.10, index=post_idx)  # 0.10%

    concat, meta = _concat_ioer_iorb_impl(ioer, iorb, pd.Timestamp("2021-07-29"))
    assert meta["gates_passed"] is True
    assert meta["boundary_diff_pp"] < 0.01
    assert concat.name == "iorb_extended"
    # Length = pre + post.
    assert len(concat) == len(pre_idx) + len(post_idx)
    # Pre values come from ioer.
    assert float(concat.loc[pd.Timestamp("2021-07-28")]) == 0.10
    # Post values come from iorb.
    assert float(concat.loc[pd.Timestamp("2021-07-29")]) == 0.10


def test_concat_ioer_iorb_boundary_too_large_raises() -> None:
    """Boundary diff >= 0.01pp -> SpliceValidationError."""
    pre_idx = pd.bdate_range("2021-01-01", "2021-07-28")
    post_idx = pd.bdate_range("2021-07-29", "2021-12-31")
    ioer = pd.Series(0.10, index=pre_idx)
    iorb = pd.Series(0.50, index=post_idx)  # 0.40pp jump
    with pytest.raises(SpliceValidationError, match="boundary discrepancy"):
        _concat_ioer_iorb_impl(ioer, iorb, pd.Timestamp("2021-07-29"))


def test_concat_ioer_iorb_with_real_data() -> None:
    """Integration test using actual IOER + IORB master parquets.

    Validates the canonical 2021-07-29 boundary on the real ingested data.
    """
    try:
        concat = concat_ioer_iorb()
    except Exception as exc:
        pytest.skip(f"real IOER/IORB data not available: {exc}")
    assert concat.name == "iorb_extended"
    # Should span ~2008-10 (ioer start) through ~2026-05 (iorb latest).
    assert concat.index.min() < pd.Timestamp("2010-01-01")
    assert concat.index.max() > pd.Timestamp("2024-01-01")
    # Boundary should be present.
    assert pd.Timestamp("2021-07-29") in concat.index


# ===========================================================================
# Splice 3 main: TED -> (SOFR - IORB_extended) z-score blend
# ===========================================================================


def test_zblend_pre_blend_uses_z_ted_only() -> None:
    """Before blend_start -> output equals z_TED."""
    idx = pd.bdate_range("2021-01-01", "2023-12-31")
    z_ted = pd.Series(0.5, index=idx)
    z_sofr = pd.Series(-0.5, index=idx)
    out, _meta = _splice_ted_sofr_iorb_zblend_impl(
        z_ted,
        z_sofr,
        pd.Timestamp("2022-02-01"),
        pd.Timestamp("2023-04-01"),
    )
    # Pre-blend (before 2022-02-01) should be 0.5 (z_ted).
    pre = out.loc[out.index < pd.Timestamp("2022-02-01")]
    assert (pre == 0.5).all()


def test_zblend_post_blend_uses_z_sofr_only() -> None:
    """After blend_end -> output equals z_SOFR_IORB."""
    idx = pd.bdate_range("2021-01-01", "2024-06-30")
    z_ted = pd.Series(0.5, index=idx)
    z_sofr = pd.Series(-0.5, index=idx)
    out, _meta = _splice_ted_sofr_iorb_zblend_impl(
        z_ted,
        z_sofr,
        pd.Timestamp("2022-02-01"),
        pd.Timestamp("2023-04-01"),
    )
    post = out.loc[out.index > pd.Timestamp("2023-04-01")]
    assert (post == -0.5).all()


def test_zblend_linear_ramp_in_blend_window() -> None:
    """Within blend window, lambda ramps linearly from 0 -> 1."""
    blend_start = pd.Timestamp("2022-02-01")
    blend_end = pd.Timestamp("2023-04-03")  # Monday (Apr 1 is Saturday)
    span_days = (blend_end - blend_start).days
    idx = pd.bdate_range("2022-01-01", "2023-05-01")
    z_ted = pd.Series(1.0, index=idx)
    z_sofr = pd.Series(0.0, index=idx)  # difference of 1.0
    out, _meta = _splice_ted_sofr_iorb_zblend_impl(
        z_ted, z_sofr, blend_start, blend_end
    )
    # At blend_start -> lambda=0 -> output = z_ted = 1.0.
    assert out.loc[blend_start] == pytest.approx(1.0, rel=1e-9)
    # At blend_end -> lambda=1 -> output = z_sofr = 0.0.
    assert out.loc[blend_end] == pytest.approx(0.0, abs=1e-9)
    # Midpoint -> lambda ~= 0.5.
    midpoint = blend_start + pd.Timedelta(days=span_days // 2)
    closest = idx[idx.searchsorted(midpoint, side="left")]
    lam_expected = (closest - blend_start).days / span_days
    expected = (1.0 - lam_expected) * 1.0 + lam_expected * 0.0
    assert out.loc[closest] == pytest.approx(expected, rel=1e-9)


def test_zblend_large_discontinuity_raises() -> None:
    """abs(diff().max()) >= 1.5 sigma within blend window -> SpliceValidationError."""
    blend_start = pd.Timestamp("2022-02-01")
    blend_end = pd.Timestamp("2023-04-01")
    idx = pd.bdate_range("2022-01-01", "2023-05-01")

    # Make a hard jump in z_sofr at one date to trigger gate fail.
    z_ted = pd.Series(1.0, index=idx)
    z_sofr_vals = np.where(idx < pd.Timestamp("2022-08-01"), 0.0, 100.0)
    z_sofr = pd.Series(z_sofr_vals, index=idx)
    with pytest.raises(SpliceValidationError, match="max"):
        _splice_ted_sofr_iorb_zblend_impl(
            z_ted, z_sofr, blend_start, blend_end
        )


def test_zblend_rejects_bad_blend_window() -> None:
    """blend_end <= blend_start -> ValueError."""
    idx = pd.bdate_range("2022-01-01", "2023-05-01")
    z_ted = pd.Series(0.5, index=idx)
    z_sofr = pd.Series(-0.5, index=idx)
    with pytest.raises(ValueError, match="blend_end"):
        _splice_ted_sofr_iorb_zblend_impl(
            z_ted, z_sofr,
            pd.Timestamp("2023-01-01"),
            pd.Timestamp("2022-01-01"),
        )
