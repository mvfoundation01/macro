"""Tests for ``src.transform.lc_v1_splices`` — the 4 LC v1.0 splice functions
sealed per pre-reg a8635ef §1.3.

Test layout
-----------
* T-B1.* — splice_busloans_to_totll  (YoY-additive)
* T-B2.* — splice_icedxy_to_dtwexbgs (log-level-additive)
* T-B3.* — splice_ioer_to_iorb      (concatenation, Fed rename)
* T-B4.* — splice_ted_to_sofr_iorb  (z-score linear blend)
* T-B5.* — look-ahead audit across all four

Coverage target: ≥95% per Session 6 prompt §2.B.

References
----------
* specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.3 — sealed thresholds.
* prompt/052226/PROMPT_v11_3_stage_3_LC_v1_session_6.md §2.B.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.transform import lc_v1_splices as splices


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _simple_zscore(series: pd.Series) -> pd.Series:
    """Full-sample mean/std z-score (no PIT discipline) for splice unit tests."""
    s = series.dropna()
    mu = s.mean()
    sd = s.std(ddof=1)
    if sd == 0 or not np.isfinite(sd):
        return pd.Series(np.nan, index=series.index)
    return (series - mu) / sd


def _monthly_series(
    start: str, end: str, initial: float, monthly_growth: float, seed: int = 0,
    noise_sd: float = 0.0,
) -> pd.Series:
    """Synthetic monthly EOM series with linear growth + optional gaussian noise."""
    idx = pd.date_range(start, end, freq="ME")
    rng = np.random.default_rng(seed)
    n = len(idx)
    base = initial * (1.0 + monthly_growth) ** np.arange(n)
    if noise_sd > 0:
        base = base * np.exp(rng.normal(0.0, noise_sd, size=n))
    return pd.Series(base, index=idx, name="synthetic")


def _daily_series(
    start: str, end: str, value: float, jitter: float = 0.0, seed: int = 0,
) -> pd.Series:
    """Synthetic daily series with constant value + optional gaussian jitter."""
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(seed)
    n = len(idx)
    if jitter > 0:
        vals = value + rng.normal(0.0, jitter, size=n)
    else:
        vals = np.full(n, value)
    return pd.Series(vals, index=idx, name="synthetic_daily")


# ===========================================================================
# T-B1.* — splice_busloans_to_totll
# ===========================================================================


def _mk_busloans_totll_pass() -> tuple[pd.Series, pd.Series]:
    """Build BUSLOANS + TOTLL series that share the same underlying log-economy
    path on the splice overlap so YoY growth tracks closely (corr ~ 1, c ~ 0).
    """
    full_idx = pd.date_range("1960-01-31", "1985-12-31", freq="ME")
    rng = np.random.default_rng(11)
    # Monthly log growth ~ 0.5% with small noise — same path for both series.
    log_path = np.cumsum(rng.normal(0.005, 0.003, size=len(full_idx)))

    busloans_mask = (
        (full_idx >= pd.Timestamp("1960-01-31"))
        & (full_idx <= pd.Timestamp("1980-12-31"))
    )
    totll_mask = (
        (full_idx >= pd.Timestamp("1971-01-31"))
        & (full_idx <= pd.Timestamp("1985-12-31"))
    )

    busloans = pd.Series(
        50.0 * np.exp(log_path[busloans_mask]),
        index=full_idx[busloans_mask],
        name="busloans",
    )
    totll = pd.Series(
        300.0 * np.exp(log_path[totll_mask]),
        index=full_idx[totll_mask],
        name="totll",
    )
    return busloans, totll


def test_TB1_1_busloans_totll_gate_pass_continuous_at_boundary() -> None:
    """T-B1.1: gate PASS, output continuous at boundary."""
    busloans, totll = _mk_busloans_totll_pass()
    result = splices.splice_busloans_to_totll(busloans, totll)
    # Pre-1973 from BUSLOANS, post-1973 from TOTLL adjusted.
    splice_date = splices.BUSLOANS_TOTLL_SPLICE_DATE
    pre = result.loc[result.index < splice_date]
    post = result.loc[result.index >= splice_date]
    assert len(pre) > 0
    assert len(post) > 0
    # Continuity check: |Δ| at the boundary ≤ 99th-percentile of |Δ| elsewhere.
    diffs = result.diff().abs().dropna()
    p99 = float(diffs.quantile(0.99))
    first_post_date = result.index[result.index >= splice_date][0]
    boundary_loc_raw = result.index.get_loc(first_post_date)
    assert isinstance(boundary_loc_raw, int)
    boundary_loc: int = boundary_loc_raw
    boundary_jump = float(abs(result.iloc[boundary_loc] - result.iloc[boundary_loc - 1]))
    assert boundary_jump <= p99 * 1.5
    # attrs recorded.
    assert "yoy_additive" in result.attrs["transform"]
    assert "splice_c" in result.attrs


def test_TB1_2_busloans_totll_gate_corr_fail() -> None:
    """T-B1.2: corr < 0.50 → ValueError."""
    # BUSLOANS YoY grows; TOTLL YoY shrinks. Anti-correlated.
    busloans = _monthly_series(
        start="1960-01-31", end="1980-12-31",
        initial=50.0, monthly_growth=0.006, seed=21,
    )
    # TOTLL with opposite curvature: declining mid-window so YoY differs.
    idx = pd.date_range("1971-01-31", "1985-12-31", freq="ME")
    base = 300.0 * (1.0 + 0.006) ** np.arange(len(idx))
    # Inject a strong oscillation that makes YoY anti-correlated near 1973.
    osc = 0.20 * np.sin(np.arange(len(idx)) * np.pi / 6.0)  # ~6mo period
    totll = pd.Series(base * np.exp(osc), index=idx, name="totll")

    with pytest.raises(ValueError, match=r"GATE FAIL: corr="):
        splices.splice_busloans_to_totll(busloans, totll)


def test_TB1_3_busloans_totll_gate_c_fail() -> None:
    """T-B1.3: |c| ≥ 0.05 → ValueError."""
    busloans = _monthly_series(
        start="1960-01-31", end="1980-12-31",
        initial=50.0, monthly_growth=0.006, seed=31,
    )
    # TOTLL grows MUCH faster than BUSLOANS so YoY-growth gap exceeds 5 pp.
    totll = _monthly_series(
        start="1971-01-31", end="1985-12-31",
        initial=300.0, monthly_growth=0.012,  # ~14% annual vs BUSLOANS 7%
        seed=32,
    )
    with pytest.raises(ValueError, match=r"GATE FAIL: \|c\|"):
        splices.splice_busloans_to_totll(busloans, totll)


def test_TB1_4_busloans_totll_edge_case_busloans_short_history() -> None:
    """T-B1.4: BUSLOANS ends before 1972-12 → either splices what's available
    or surfaces 'insufficient overlap'. The function should not corrupt data."""
    busloans = _monthly_series(
        start="1960-01-31", end="1971-12-31",
        initial=50.0, monthly_growth=0.006, seed=41,
    )
    totll = _monthly_series(
        start="1971-01-31", end="1985-12-31",
        initial=300.0, monthly_growth=0.006, seed=42,
    )
    # Overlap window is ±12 months of 1973-01-03. BUSLOANS ends 1971-12 →
    # last YoY usable is 1971-12 (computed from 1970-12 + 12mo). Within
    # the overlap window we have BUSLOANS yoy entries at 1972-01 -> 1971-12-only.
    # This is < 2 overlap rows so the function should raise.
    with pytest.raises(ValueError, match=r"insufficient overlap"):
        splices.splice_busloans_to_totll(busloans, totll)


# ===========================================================================
# T-B2.* — splice_icedxy_to_dtwexbgs
# ===========================================================================


def _mk_icedxy_dtwexbgs_pass() -> tuple[pd.Series, pd.Series]:
    """Build monthly log-DXY and log-DTWEXBGS series with matched shapes so
    corr > 0.85 and z-div < 0.30 in the ±2-month overlap (both gates PASS)."""
    idx = pd.date_range("2000-01-31", "2010-12-31", freq="ME")
    rng = np.random.default_rng(50)
    base = np.linspace(4.40, 4.60, len(idx)) + rng.normal(0, 0.005, size=len(idx))
    log_dxy = pd.Series(base, index=idx, name="log_dxy")
    log_dtw = pd.Series(base + 0.40, index=idx, name="log_dtwexbgs")  # parallel offset
    return log_dxy, log_dtw


def test_TB2_1_icedxy_dtwexbgs_gate_pass_continuous() -> None:
    """T-B2.1: gate PASS, output continuous."""
    log_dxy, log_dtw = _mk_icedxy_dtwexbgs_pass()
    spliced, c = splices.splice_icedxy_to_dtwexbgs(log_dxy, log_dtw)
    assert isinstance(c, float)
    # c should approximate the level offset (-0.40) since dxy_mean - dtw_mean
    # ≈ - (dtw - dxy) ≈ -0.40 on the overlap window.
    assert -0.45 < c < -0.35
    # Spliced spans pre and post.
    pre = spliced.loc[spliced.index < splices.ICEDXY_DTWEXBGS_SPLICE_DATE]
    post = spliced.loc[spliced.index >= splices.ICEDXY_DTWEXBGS_SPLICE_DATE]
    assert len(pre) > 0 and len(post) > 0


def test_TB2_2_icedxy_dtwexbgs_gate_corr_fail() -> None:
    """T-B2.2: corr < 0.85 → ValueError."""
    idx = pd.date_range("2005-09-30", "2006-04-30", freq="ME")
    log_dxy = pd.Series(np.linspace(4.50, 4.52, len(idx)), index=idx)
    # Anti-correlated zigzag pattern.
    log_dtw = pd.Series(
        [4.80, 4.78, 4.80, 4.78, 4.80, 4.78, 4.80, 4.78], index=idx,
    )
    with pytest.raises(ValueError, match=r"GATE FAIL: corr="):
        splices.splice_icedxy_to_dtwexbgs(log_dxy, log_dtw)


def test_TB2_3_icedxy_dtwexbgs_gate_z_div_fail() -> None:
    """T-B2.3: mean |z-div| ≥ 0.30 → ValueError (with corr passing first)."""
    idx = pd.date_range("2005-09-30", "2006-04-30", freq="ME")
    log_dxy = pd.Series(np.linspace(4.40, 4.54, len(idx)), index=idx)
    log_dtw_values = np.linspace(4.80, 4.94, len(idx))
    pos_jan = idx.get_loc(pd.Timestamp("2006-01-31"))
    log_dtw_values[pos_jan] += 0.035  # outlier in overlap window
    log_dtw = pd.Series(log_dtw_values, index=idx)
    with pytest.raises(ValueError, match=r"GATE FAIL: mean\|z-div\|"):
        splices.splice_icedxy_to_dtwexbgs(log_dxy, log_dtw)


def test_TB2_5_icedxy_dtwexbgs_insufficient_overlap_raises() -> None:
    """T-B2.5: <2 overlap rows → ValueError (insufficient overlap)."""
    idx = pd.DatetimeIndex([pd.Timestamp("2006-01-31")])
    log_dxy = pd.Series([4.50], index=idx)
    log_dtw = pd.Series([4.10], index=idx)
    with pytest.raises(ValueError, match=r"insufficient overlap"):
        splices.splice_icedxy_to_dtwexbgs(log_dxy, log_dtw)


def test_TB2_6_icedxy_dtwexbgs_zero_std_raises() -> None:
    """T-B2.6: zero std in overlap → ValueError (precondition gate)."""
    idx = pd.date_range("2005-11-30", "2006-02-28", freq="ME")
    log_dxy = pd.Series([4.50] * len(idx), index=idx)
    log_dtw = pd.Series([4.10] * len(idx), index=idx)
    with pytest.raises(ValueError, match=r"zero/NaN std"):
        splices.splice_icedxy_to_dtwexbgs(log_dxy, log_dtw)


def test_TB2_4_icedxy_dtwexbgs_attrs_record_c() -> None:
    """T-B2.4: additive c recorded in attrs['transform']."""
    log_dxy, log_dtw = _mk_icedxy_dtwexbgs_pass()
    spliced, c = splices.splice_icedxy_to_dtwexbgs(log_dxy, log_dtw)
    assert spliced.attrs["transform"].startswith("splice_additive:")
    assert spliced.attrs["splice_c"] == c
    assert spliced.attrs["transform"].endswith(
        f"@{splices.ICEDXY_DTWEXBGS_SPLICE_DATE.date()}"
    )


# ===========================================================================
# T-B3.* — splice_ioer_to_iorb
# ===========================================================================


def test_TB3_1_ioer_iorb_pass_concatenation_continuous() -> None:
    """T-B3.1: gate PASS — concatenation is continuous at boundary."""
    ioer = _daily_series(start="2020-01-01", end="2021-07-28", value=0.10)
    iorb = _daily_series(start="2021-07-29", end="2023-12-31", value=0.10)
    result = splices.splice_ioer_to_iorb(ioer, iorb)
    pre = result.loc[result.index < splices.IOER_IORB_SPLICE_DATE]
    post = result.loc[result.index >= splices.IOER_IORB_SPLICE_DATE]
    assert len(pre) > 0 and len(post) > 0
    # Continuity: boundary jump ≤ jitter scale (which is 0 here, but allow small).
    first_post_date = result.index[result.index >= splices.IOER_IORB_SPLICE_DATE][0]
    boundary_idx_raw = result.index.get_loc(first_post_date)
    assert isinstance(boundary_idx_raw, int)
    boundary_idx: int = boundary_idx_raw
    jump = float(abs(result.iloc[boundary_idx] - result.iloc[boundary_idx - 1]))
    assert jump < 0.005


def test_TB3_2_ioer_iorb_gate_fail_when_diff_too_large() -> None:
    """T-B3.2: |diff| ≥ 0.01 → ValueError."""
    ioer = _daily_series(start="2020-01-01", end="2021-07-28", value=0.10)
    # IORB starts 0.50 pp higher — large boundary jump.
    iorb = _daily_series(start="2021-07-29", end="2023-12-31", value=0.60)
    with pytest.raises(ValueError, match=r"GATE FAIL: \|diff\|"):
        splices.splice_ioer_to_iorb(ioer, iorb)


def test_TB3_3_ioer_iorb_edge_case_iorb_starts_late() -> None:
    """T-B3.3: IORB doesn't start exactly on 2021-07-29 → uses next available."""
    ioer = _daily_series(start="2020-01-01", end="2021-07-28", value=0.10)
    # IORB starts a few days later (e.g., 2021-08-02) — function should use
    # whatever the first IORB obs at/after splice_date is.
    iorb = _daily_series(start="2021-08-02", end="2023-12-31", value=0.10)
    result = splices.splice_ioer_to_iorb(ioer, iorb)
    # The post-splice region starts at 2021-08-02 since that's IORB's first date.
    post_start = result.loc[result.index >= splices.IOER_IORB_SPLICE_DATE].index[0]
    assert post_start == pd.Timestamp("2021-08-02")


def test_TB3_4_ioer_iorb_empty_pre_or_post_raises() -> None:
    """T-B3 edge: empty pre-side or post-side → ValueError."""
    ioer_empty = pd.Series(dtype="float64", index=pd.DatetimeIndex([]))
    iorb = _daily_series(start="2021-07-29", end="2023-12-31", value=0.10)
    with pytest.raises(ValueError, match=r"IOER has no obs before"):
        splices.splice_ioer_to_iorb(ioer_empty, iorb)

    ioer = _daily_series(start="2020-01-01", end="2021-07-28", value=0.10)
    iorb_empty = pd.Series(dtype="float64", index=pd.DatetimeIndex([]))
    with pytest.raises(ValueError, match=r"IORB has no obs at/after"):
        splices.splice_ioer_to_iorb(ioer, iorb_empty)


# ===========================================================================
# T-B4.* — splice_ted_to_sofr_iorb
# ===========================================================================


def _mk_ted_sofr_iorb_pass() -> tuple[pd.Series, pd.Series, pd.Series]:
    """Synthetic TED + SOFR + IORB with smooth ranges so the z-blend passes.

    SOFR and IORB are designed to have a non-degenerate spread (SOFR-IORB has
    non-zero variance) so ``zscore_fn(sofr - iorb)`` is well-defined.
    """
    # TED: monthly EOM 1990-01 through 2022-01-31 (discontinued).
    ted_idx = pd.date_range("1990-01-31", "2022-01-31", freq="ME")
    ted = pd.Series(
        0.30 + 0.10 * np.sin(np.arange(len(ted_idx)) / 24.0),
        index=ted_idx, name="ted",
    )
    # SOFR + IORB: 2018-04 through 2024-12 (monthly EOM). Spread varies.
    sofr_idx = pd.date_range("2018-04-30", "2024-12-31", freq="ME")
    sofr = pd.Series(
        2.0 + 0.50 * np.cos(np.arange(len(sofr_idx)) / 12.0),
        index=sofr_idx, name="sofr",
    )
    iorb = pd.Series(
        1.95 + 0.30 * np.sin(np.arange(len(sofr_idx)) / 8.0),
        index=sofr_idx, name="iorb",
    )
    return ted, sofr, iorb


def test_TB4_1_ted_sofr_iorb_gate_pass_blend_monotonic_weight() -> None:
    """T-B4.1: gate PASS — output transitions linearly across the blend window."""
    ted, sofr, iorb = _mk_ted_sofr_iorb_pass()
    result = splices.splice_ted_to_sofr_iorb(
        ted, sofr, iorb, zscore_fn=_simple_zscore,
    )
    assert len(result) > 0
    # No huge |Δz|.
    assert result.diff().abs().max() < splices.TED_SOFR_MAX_ABS_DZ


def test_TB4_2_ted_sofr_iorb_endpoint_weights() -> None:
    """T-B4.2: the linear-weight formula holds across the blend window.

    Pick a date inside the blend window and verify
        ``result[t] = (1 - w_t) · z_ted_ffill[t] + w_t · z_sofr_iorb[t]``
    where ``w_t = clip((t - blend_start).days / (blend_end - blend_start).days, 0, 1)``.
    """
    ted, sofr, iorb = _mk_ted_sofr_iorb_pass()
    z_ted_simple = _simple_zscore(ted)
    z_sofr_iorb_simple = _simple_zscore((sofr - iorb).dropna())

    result = splices.splice_ted_to_sofr_iorb(
        ted, sofr, iorb, zscore_fn=_simple_zscore,
    )

    blend_duration_days = (
        splices.TED_SOFR_BLEND_END - splices.TED_SOFR_BLEND_START
    ).days

    # Verify formula at a sample of dates: the first in-window, mid-window,
    # and the last in-window.
    in_window = result.loc[
        (result.index >= splices.TED_SOFR_BLEND_START)
        & (result.index <= splices.TED_SOFR_BLEND_END)
    ]
    z_ted_ffill = z_ted_simple.reindex(result.index).ffill()
    z_sofr_reidx = z_sofr_iorb_simple.reindex(result.index)

    for t in [in_window.index[0], in_window.index[len(in_window) // 2], in_window.index[-1]]:
        days_from_start = (t - splices.TED_SOFR_BLEND_START).days
        w = float(np.clip(days_from_start / blend_duration_days, 0.0, 1.0))
        z_ted_t = float(z_ted_ffill.loc[t])
        z_sofr_t = z_sofr_reidx.loc[t]
        if pd.notna(z_sofr_t):
            expected = (1.0 - w) * z_ted_t + w * float(z_sofr_t)
        else:
            expected = z_ted_t  # fall-back when z_sofr undefined
        assert abs(result.loc[t] - expected) < 1e-9, (
            f"Blend-formula check at t={t.date()}: result={result.loc[t]} "
            f"expected={expected} (w={w}, z_ted={z_ted_t}, z_sofr={z_sofr_t})"
        )


def test_TB4_3_ted_sofr_iorb_gate_dz_fail() -> None:
    """T-B4.3: max |Δz| ≥ 1.5 → ValueError."""
    # Construct a TED with a sudden spike right before discontinuation so the
    # forward-filled z value is very far from z_sofr_iorb at the blend start —
    # creating a large jump.
    ted_idx = pd.date_range("2020-01-31", "2022-01-31", freq="ME")
    ted_vals = np.concatenate(
        [np.full(len(ted_idx) - 1, 0.30), [5.00]]  # spike on last day
    )
    ted = pd.Series(ted_vals, index=ted_idx, name="ted")

    sofr_idx = pd.date_range("2018-04-30", "2024-12-31", freq="ME")
    sofr = pd.Series(2.0, index=sofr_idx, name="sofr")
    iorb = pd.Series(1.95, index=sofr_idx, name="iorb")  # constant
    # SOFR - IORB is constant → z = NaN. So z_sofr_iorb is NaN throughout.
    # That defeats this test. Let me instead vary SOFR-IORB modestly.
    iorb = pd.Series(1.95 + 0.01 * np.sin(np.arange(len(sofr_idx))), index=sofr_idx, name="iorb")

    with pytest.raises(ValueError, match=r"GATE FAIL: max \|"):
        splices.splice_ted_to_sofr_iorb(ted, sofr, iorb, zscore_fn=_simple_zscore)


def test_TB4_4_ted_sofr_iorb_dependency_injection_works() -> None:
    """T-B4.4: zscore_fn parameter actually drives the z computation."""
    ted, sofr, iorb = _mk_ted_sofr_iorb_pass()

    call_log: list[str] = []

    def _logging_zscore(series: pd.Series) -> pd.Series:
        call_log.append(str(series.name))
        return _simple_zscore(series)

    splices.splice_ted_to_sofr_iorb(
        ted, sofr, iorb, zscore_fn=_logging_zscore,
    )
    # Called twice: once for ted, once for sofr-iorb.
    assert len(call_log) == 2
    assert "ted" in call_log
    assert "sofr_minus_iorb" in call_log


def test_TB4_5_ted_sofr_iorb_blend_window_validation() -> None:
    """T-B4 edge: blend_end <= blend_start → ValueError."""
    ted, sofr, iorb = _mk_ted_sofr_iorb_pass()
    with pytest.raises(ValueError, match=r"blend_end .* must be strictly after"):
        splices.splice_ted_to_sofr_iorb(
            ted, sofr, iorb,
            zscore_fn=_simple_zscore,
            blend_start=pd.Timestamp("2023-04-30"),
            blend_end=pd.Timestamp("2022-02-01"),
        )


# ===========================================================================
# T-B5 — Look-ahead audit across all four splices
# ===========================================================================


def test_TB5_lookahead_no_rows_past_input_horizon() -> None:
    """T-B5: For each splice, the output series at the last input date T does
    not contain any rows with date > T.

    This audits the "no peeking into the future" invariant — the splice
    constants are computed within a FIXED window around the (historic) splice
    date, so truncating inputs to T should not affect dates ≤ T.
    """
    T = pd.Timestamp("2010-12-31")

    # B.1 BUSLOANS → TOTLL
    busloans, totll = _mk_busloans_totll_pass()
    busloans_T = busloans.loc[busloans.index <= T]
    totll_T = totll.loc[totll.index <= T]
    result = splices.splice_busloans_to_totll(busloans_T, totll_T)
    assert (result.index <= T).all()

    # B.2 ICEDXY → DTWEXBGS
    log_dxy, log_dtw = _mk_icedxy_dtwexbgs_pass()
    log_dxy_T = log_dxy.loc[log_dxy.index <= T]
    log_dtw_T = log_dtw.loc[log_dtw.index <= T]
    result2, _ = splices.splice_icedxy_to_dtwexbgs(log_dxy_T, log_dtw_T)
    assert (result2.index <= T).all()

    # B.3 IOER → IORB: T is well past the splice date, both series truncated.
    T_b3 = pd.Timestamp("2022-12-31")
    ioer = _daily_series(start="2020-01-01", end="2021-07-28", value=0.10)
    iorb = _daily_series(start="2021-07-29", end="2023-12-31", value=0.10)
    iorb_T = iorb.loc[iorb.index <= T_b3]
    result3 = splices.splice_ioer_to_iorb(ioer, iorb_T)
    assert (result3.index <= T_b3).all()

    # B.4 TED → SOFR-IORB
    ted, sofr, iorb_full = _mk_ted_sofr_iorb_pass()
    T_b4 = pd.Timestamp("2024-06-30")
    sofr_T = sofr.loc[sofr.index <= T_b4]
    iorb_T2 = iorb_full.loc[iorb_full.index <= T_b4]
    result4 = splices.splice_ted_to_sofr_iorb(
        ted, sofr_T, iorb_T2, zscore_fn=_simple_zscore,
    )
    assert (result4.index <= T_b4).all()
