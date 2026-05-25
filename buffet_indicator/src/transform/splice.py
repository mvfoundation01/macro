"""Splice helpers per sealed pre-reg §10.1 (seal 2a94417).

Four helpers + one exception class:

1. :func:`splice_busloans_totll_yoy` (z3) — BUSLOANS -> TOTLL @ 1973-01-03
   in YoY growth-rate space, additive constant ``c``; gates
   ``corr > 0.50`` AND ``abs(c) < 0.05``.
2. :func:`splice_icedxy_dtwexbgs_log` (z4) — ICE_DXY -> DTWEXBGS
   @ 2006-01-04 in log-levels space, additive constant ``c``; gates
   ``corr > 0.85`` AND ``mean(abs(z-divergence)) < 0.30``.
3. :func:`concat_ioer_iorb` (z5 pre-step) — IOER -> IORB @ 2021-07-29
   level concat (no splice adjustment); gate
   ``abs(IOER@2021-07-28 - IORB@2021-07-29) < 0.01pp``.
4. :func:`splice_ted_sofr_iorb_zblend` (z5) — TED -> (SOFR - IORB) z-score
   linear blend Feb 2022 -> Apr 2023 (14 months); gate
   ``abs(funding_z.diff().max()) < 1.5 sigma`` within blend window.

Per ``PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md`` §3 Option C1.

Each PUBLIC function loads its source series via
:func:`src.ingest.master_archive.load_master` and produces a single
``pd.Series`` of the spliced quantity. Each function has a corresponding
private ``_..._impl`` helper that takes pre-loaded series and returns
``(spliced_series, splice_metadata_dict)`` — used by the test suite to
exercise the splicing math against synthetic data.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

from src.ingest.master_archive import load_master
from src.transform.pit_zscore import pit_zscore


class SpliceValidationError(ValueError):
    """Raised when a splice's continuity / correlation / discrepancy gate fails.

    Per sealed pre-reg §10.1 splice validation gates.
    """


# ---------------------------------------------------------------------------
# Splice 1: BUSLOANS -> TOTLL @ 1973-01-03 in YoY-growth-rate space
# ---------------------------------------------------------------------------


def _yoy_growth(series: pd.Series, periods: int = 12) -> pd.Series:
    """Year-over-year growth rate (pct_change with default 12-period lag).

    For monthly data, ``periods=12`` is the canonical convention.
    """
    return series.pct_change(periods=periods)


def _splice_busloans_totll_yoy_impl(
    busloans_yoy: pd.Series,
    totll_yoy: pd.Series,
    splice_date: pd.Timestamp,
    overlap_months: int = 18,
) -> Tuple[pd.Series, dict]:
    """Pure implementation of splice 1; testable against synthetic inputs.

    Returns
    -------
    spliced : pd.Series
        BUSLOANS_yoy (with additive c applied) for ``index < splice_date``,
        concatenated with TOTLL_yoy for ``index >= splice_date``.
    meta : dict
        Splice metadata including ``constant_c``, ``overlap_corr``,
        ``overlap_n``, ``splice_date``.
    """
    splice_date = pd.Timestamp(splice_date)
    overlap_start = splice_date - pd.DateOffset(months=overlap_months)
    overlap_end = splice_date + pd.DateOffset(months=overlap_months)
    bus_o = busloans_yoy.loc[overlap_start:overlap_end].dropna()
    tot_o = totll_yoy.loc[overlap_start:overlap_end].dropna()
    common = bus_o.index.intersection(tot_o.index)
    if len(common) < 6:
        raise SpliceValidationError(
            f"insufficient overlap between BUSLOANS_yoy and TOTLL_yoy around "
            f"{splice_date.date()}: {len(common)} common obs (need >= 6)"
        )
    bus_aligned = bus_o.loc[common]
    tot_aligned = tot_o.loc[common]
    corr = float(bus_aligned.corr(tot_aligned))
    c = float(np.median(tot_aligned - bus_aligned))

    if not (corr > 0.50):
        raise SpliceValidationError(
            f"BUSLOANS/TOTLL YoY correlation {corr:.4f} <= 0.50 over splice window "
            f"around {splice_date.date()} (n={len(common)})"
        )
    if not (abs(c) < 0.05):
        raise SpliceValidationError(
            f"BUSLOANS/TOTLL YoY additive constant |c|={abs(c):.4f} >= 0.05 "
            f"over splice window around {splice_date.date()}"
        )

    pre = (busloans_yoy + c).loc[busloans_yoy.index < splice_date]
    post = totll_yoy.loc[totll_yoy.index >= splice_date]
    spliced = pd.concat([pre, post]).sort_index()
    spliced = spliced[~spliced.index.duplicated(keep="last")]
    spliced.name = "banklend_growth_yoy"
    meta = {
        "splice_id": "busloans_totll_yoy",
        "splice_date": str(splice_date.date()),
        "method": "yoy_additive_constant",
        "constant_c": c,
        "overlap_corr": corr,
        "overlap_n": int(len(common)),
        "gates_passed": True,
    }
    return spliced, meta


def splice_busloans_totll_yoy(
    splice_date: pd.Timestamp = pd.Timestamp("1973-01-03"),
) -> pd.Series:
    """Splice BUSLOANS -> TOTLL @ 1973-01-03 in YoY-growth-rate space.

    Per sealed §10.1: additive constant ``c`` in YoY space; validation
    gates ``corr(BUSLOANS_yoy, TOTLL_yoy) > 0.50`` AND ``abs(c) < 0.05``.

    Returns
    -------
    pd.Series
        Spliced YoY growth-rate series named ``"banklend_growth_yoy"``.
        Pre-1973-01-03: BUSLOANS YoY + c. Post-1973-01-03: TOTLL YoY.

    Raises
    ------
    SpliceValidationError
        If correlation or constant-magnitude gates fail.
    """
    busloans = load_master("busloans").data
    totll = load_master("totll").data
    bus_yoy = _yoy_growth(busloans)
    tot_yoy = _yoy_growth(totll)
    spliced, _meta = _splice_busloans_totll_yoy_impl(bus_yoy, tot_yoy, splice_date)
    return spliced


# ---------------------------------------------------------------------------
# Splice 2: ICE_DXY -> DTWEXBGS @ 2006-01-04 in log-levels space
# ---------------------------------------------------------------------------


def _splice_icedxy_dtwexbgs_log_impl(
    ice_dxy: pd.Series,
    dtwexbgs: pd.Series,
    splice_date: pd.Timestamp,
    overlap_days: int = 90,
) -> Tuple[pd.Series, dict]:
    """Pure implementation of splice 2; testable against synthetic inputs."""
    splice_date = pd.Timestamp(splice_date)
    log_ice = np.log(ice_dxy)
    log_dtw = np.log(dtwexbgs)

    overlap_start = splice_date - pd.Timedelta(days=overlap_days)
    overlap_end = splice_date + pd.Timedelta(days=overlap_days)
    ice_o = log_ice.loc[overlap_start:overlap_end].dropna()
    dtw_o = log_dtw.loc[overlap_start:overlap_end].dropna()
    common = ice_o.index.intersection(dtw_o.index)
    if len(common) < 10:
        raise SpliceValidationError(
            f"insufficient overlap between ICE_DXY and DTWEXBGS around "
            f"{splice_date.date()}: {len(common)} common obs (need >= 10)"
        )
    ice_aligned = ice_o.loc[common]
    dtw_aligned = dtw_o.loc[common]
    corr = float(ice_aligned.corr(dtw_aligned))
    c = float(np.median(dtw_aligned - ice_aligned))

    if not (corr > 0.85):
        raise SpliceValidationError(
            f"ICE_DXY/DTWEXBGS log-level correlation {corr:.4f} <= 0.85 over "
            f"splice window around {splice_date.date()} (n={len(common)})"
        )

    # z-divergence: z-score each log-level series over the overlap window
    # independently, then take mean(|z_dtw - z_ice|). Small mean = the two
    # series move in lock-step in z-space.
    def _z(x: pd.Series) -> pd.Series:
        sd = x.std(ddof=1)
        if sd <= 0:
            return x * 0.0
        return (x - x.mean()) / sd

    z_ice_o = _z(ice_aligned)
    z_dtw_o = _z(dtw_aligned)
    mean_abs_z = float((z_dtw_o - z_ice_o).abs().mean())
    if not (mean_abs_z < 0.30):
        raise SpliceValidationError(
            f"ICE_DXY/DTWEXBGS log-level mean(abs(z-divergence)) {mean_abs_z:.4f} "
            f">= 0.30 over splice window"
        )

    pre = (log_ice + c).loc[log_ice.index < splice_date]
    post = log_dtw.loc[log_dtw.index >= splice_date]
    spliced = pd.concat([pre, post]).sort_index()
    spliced = spliced[~spliced.index.duplicated(keep="last")]
    spliced.name = "log_dxy_extended"
    meta = {
        "splice_id": "icedxy_dtwexbgs_log",
        "splice_date": str(splice_date.date()),
        "method": "log_additive_constant",
        "constant_c": c,
        "overlap_corr": corr,
        "overlap_n": int(len(common)),
        "mean_abs_z_divergence": mean_abs_z,
        "gates_passed": True,
    }
    return spliced, meta


def splice_icedxy_dtwexbgs_log(
    splice_date: pd.Timestamp = pd.Timestamp("2006-01-04"),
) -> pd.Series:
    """Splice ICE_DXY -> DTWEXBGS @ 2006-01-04 in log-levels space.

    Per sealed §10.1: additive constant ``c`` in log-levels; gates
    ``corr(log_ICE_DXY, log_DTWEXBGS) > 0.85`` AND
    ``mean(abs(z-divergence)) < 0.30``.

    Returns
    -------
    pd.Series
        Spliced log-level series named ``"log_dxy_extended"``.
        Pre-2006-01-04: log(ICE_DXY) + c. Post: log(DTWEXBGS).

    Raises
    ------
    SpliceValidationError
        Correlation or z-divergence gate failure.

    Notes
    -----
    ICE_DXY data is not yet built into the master archive (only DTWEXBGS
    is present, starting at the splice date). Calling this function on
    real data currently raises ``SourceMissingError`` for ``ice_dxy``.
    The function and its pure-data impl are exercised in tests via
    synthetic ICE_DXY-like fixtures.
    """
    ice_dxy = load_master("ice_dxy").data
    dtwexbgs = load_master("dtwexbgs").data
    spliced, _meta = _splice_icedxy_dtwexbgs_log_impl(ice_dxy, dtwexbgs, splice_date)
    return spliced


# ---------------------------------------------------------------------------
# Splice 3 (pre-step): IOER -> IORB @ 2021-07-29 level concat (no splice)
# ---------------------------------------------------------------------------


def _concat_ioer_iorb_impl(
    ioer: pd.Series,
    iorb: pd.Series,
    splice_date: pd.Timestamp,
    threshold_pp: float = 0.01,
) -> Tuple[pd.Series, dict]:
    """Pure implementation of z5 pre-step (level concat, no adjustment)."""
    splice_date = pd.Timestamp(splice_date)

    # Gate: difference at the boundary < threshold_pp.
    last_ioer = ioer.loc[ioer.index < splice_date]
    first_iorb = iorb.loc[iorb.index >= splice_date]
    if last_ioer.empty:
        raise SpliceValidationError(
            f"IOER series has no observations strictly before {splice_date.date()}"
        )
    if first_iorb.empty:
        raise SpliceValidationError(
            f"IORB series has no observations at or after {splice_date.date()}"
        )
    boundary_diff = abs(float(first_iorb.iloc[0]) - float(last_ioer.iloc[-1]))
    if not (boundary_diff < threshold_pp):
        raise SpliceValidationError(
            f"IOER->IORB boundary discrepancy {boundary_diff:.4f}pp >= "
            f"{threshold_pp:.4f}pp threshold at {splice_date.date()} "
            f"(IOER last={float(last_ioer.iloc[-1]):.4f}, "
            f"IORB first={float(first_iorb.iloc[0]):.4f})"
        )

    pre = ioer.loc[ioer.index < splice_date]
    post = iorb.loc[iorb.index >= splice_date]
    concat = pd.concat([pre, post]).sort_index()
    concat = concat[~concat.index.duplicated(keep="last")]
    concat.name = "iorb_extended"
    meta = {
        "splice_id": "ioer_iorb_concat",
        "splice_date": str(splice_date.date()),
        "method": "level_concat_no_adjustment",
        "boundary_diff_pp": boundary_diff,
        "threshold_pp": threshold_pp,
        "gates_passed": True,
    }
    return concat, meta


def concat_ioer_iorb(
    splice_date: pd.Timestamp = pd.Timestamp("2021-07-29"),
) -> pd.Series:
    """Concat IOER (pre-2021-07-29) + IORB (2021-07-29+) into ``iorb_extended``.

    Per sealed §10.1: IOER and IORB are different names for the same Fed
    rate (rebranded 2021-07-29). No splice adjustment is applied; the
    boundary continuity is validated via
    ``abs(IOER@2021-07-28 - IORB@2021-07-29) < 0.01pp``.

    Returns
    -------
    pd.Series
        Concatenated series named ``"iorb_extended"``.

    Raises
    ------
    SpliceValidationError
        Boundary discrepancy exceeds 0.01pp threshold.
    """
    ioer = load_master("ioer").data
    iorb = load_master("iorb").data
    concat, _meta = _concat_ioer_iorb_impl(ioer, iorb, splice_date)
    return concat


# ---------------------------------------------------------------------------
# Splice 3 (main): TED -> (SOFR - IORB_extended) z-score blend over 14 months
# ---------------------------------------------------------------------------


def _splice_ted_sofr_iorb_zblend_impl(
    z_ted: pd.Series,
    z_sofr_iorb: pd.Series,
    blend_start: pd.Timestamp,
    blend_end: pd.Timestamp,
    diff_sigma_threshold: float = 1.5,
) -> Tuple[pd.Series, dict]:
    """Pure implementation of z5 main splice; testable with synthetic inputs.

    Both inputs are PIT z-scored series of TED and (SOFR - IORB_extended).
    """
    blend_start = pd.Timestamp(blend_start)
    blend_end = pd.Timestamp(blend_end)
    if blend_end <= blend_start:
        raise ValueError(
            f"blend_end ({blend_end.date()}) must be strictly after blend_start "
            f"({blend_start.date()})"
        )

    union = z_ted.index.union(z_sofr_iorb.index).sort_values()
    out = pd.Series(np.nan, index=union, name="funding_z")

    pre_mask = union < blend_start
    blend_mask = (union >= blend_start) & (union <= blend_end)
    post_mask = union > blend_end

    # Pre-blend: use z_TED.
    z_ted_aligned = z_ted.reindex(union)
    z_sofr_aligned = z_sofr_iorb.reindex(union)
    out.loc[pre_mask] = z_ted_aligned.loc[pre_mask]

    # Blend: linear lambda from 0 at blend_start -> 1 at blend_end.
    blend_idx = union[blend_mask]
    if len(blend_idx) > 0:
        span_days = (blend_end - blend_start).days
        if span_days <= 0:
            raise ValueError("blend window has non-positive duration in days")
        lam = (blend_idx - blend_start).days.astype("float64") / float(span_days)
        lam_series = pd.Series(lam, index=blend_idx)
        out.loc[blend_mask] = (1.0 - lam_series) * z_ted_aligned.loc[
            blend_mask
        ] + lam_series * z_sofr_aligned.loc[blend_mask]

    # Post-blend: use z_SOFR_IORB.
    out.loc[post_mask] = z_sofr_aligned.loc[post_mask]

    # Validation gate: max |diff| within blend window < diff_sigma_threshold.
    blend_out = out.loc[blend_mask].dropna()
    max_abs_diff = float(blend_out.diff().abs().max()) if len(blend_out) > 1 else 0.0
    if max_abs_diff >= diff_sigma_threshold:
        raise SpliceValidationError(
            f"funding_z max |Δ| within blend window {max_abs_diff:.4f} "
            f">= {diff_sigma_threshold:.4f} sigma; possible regime break"
        )

    meta = {
        "splice_id": "ted_sofr_iorb_zblend",
        "blend_start": str(blend_start.date()),
        "blend_end": str(blend_end.date()),
        "method": "z_score_linear_blend",
        "blend_window_obs": int(blend_mask.sum()),
        "max_abs_diff_within_blend": max_abs_diff,
        "diff_sigma_threshold": diff_sigma_threshold,
        "gates_passed": True,
    }
    return out, meta


def splice_ted_sofr_iorb_zblend(
    blend_start: pd.Timestamp = pd.Timestamp("2022-02-01"),
    blend_end: pd.Timestamp = pd.Timestamp("2023-04-01"),
) -> pd.Series:
    """Splice TED -> (SOFR - IORB_extended) via 14-month z-score linear blend.

    Per sealed §10.1: PIT z-score each spread separately, then linearly
    blend with weight ``lambda_t = (t - 2022-02) / (2023-04 - 2022-02)``
    so that pre-blend is z(TED), the blend window mixes both, and
    post-blend is z(SOFR - IORB_extended).

    Validation gate: ``abs(funding_z.diff().max()) < 1.5 sigma`` within
    the blend window.

    Returns
    -------
    pd.Series
        Funding-stress z-score series named ``"funding_z"``.

    Raises
    ------
    SpliceValidationError
        Blend-window discontinuity exceeds 1.5 sigma threshold.

    Notes
    -----
    This function depends on :func:`concat_ioer_iorb` (z5 pre-step) and
    :func:`src.transform.pit_zscore.pit_zscore`. PIT z-scoring uses
    ``min_window=120`` and ``strict_shift=True`` per sealed §10.1.

    The TED master parquet ends 2022-01-21 and SOFR / IORB start in
    2018-04-03 / 2021-07-29 respectively, so the splice operates on
    real data spanning 1986 -> present.
    """
    ted = load_master("tedrate").data
    sofr = load_master("sofr").data
    iorb_extended = concat_ioer_iorb()
    spread = (sofr - iorb_extended).dropna()
    z_ted = pit_zscore(ted)
    z_spread = pit_zscore(spread)
    spliced, _meta = _splice_ted_sofr_iorb_zblend_impl(
        z_ted, z_spread, blend_start, blend_end
    )
    return spliced
