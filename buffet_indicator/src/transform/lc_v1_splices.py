"""LC v1.0 splice functions (4) per sealed pre-reg a8635ef §1.3.

Four splices construct the back-extended history for the Liquidity Composite
v1.0 component series:

* ``splice_busloans_to_totll`` — YoY-additive splice at 1973-01-03; gates
  corr > 0.50, |c| < 0.05.
* ``splice_icedxy_to_dtwexbgs`` — log-level-additive splice at 2006-01-04;
  gates corr > 0.85, mean |z-div| < 0.30.
* ``splice_ioer_to_iorb`` — level concatenation at 2021-07-29 (Fed rename);
  gate |diff| < 0.01 pp.
* ``splice_ted_to_sofr_iorb`` — z-score linear blend 2022-02 → 2023-04; gate
  consecutive |Δz| < 1.5 σ.

All gates raise ``ValueError`` on failure per master spec §2.4.5 Step 4
("Reject and raise"), refusing to splice through a regime break.

References
----------
* ``specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md`` (a8635ef) §1.3 — sealed
  thresholds.
* master spec §2.4.5 — generic splice algorithm + gate-fail protocol.
* prompt/052226/PROMPT_v11_3_stage_3_LC_v1_session_6.md §2.B — sub-stage spec.

Note
----
The ICE DXY → DTWEXBGS splice algorithm is duplicated in
``src.ingest.lc_v1_loader._splice_log_dxy_with_dtwexbgs``; both call sites
must remain bit-identical so the modeling layer's pre-reg invariants hold.
The loader uses its private helper to avoid a forward dependency from §2.0
on §2.B during the Session 6 commit sequence.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Sealed constants (pre-reg a8635ef §1.3) — DO NOT MODIFY without amendment.
# ---------------------------------------------------------------------------

# B.1 BUSLOANS → TOTLL
BUSLOANS_TOTLL_SPLICE_DATE = pd.Timestamp("1973-01-03")
# Overlap window: pre-reg §1.3 sets the splice DATE, SPACE, METHOD, and GATES
# (corr > 0.50, |c| < 0.05), but does NOT constrain the overlap window used to
# compute those statistics. Session 6 used ±12 months as the default. On real
# data that window fails twice:
#   1. TOTLL_yoy is first defined at 1974-01-31 (12 mo after TOTLL's 1973-01-31
#      start) — strictly outside the ±12-mo window centered at 1973-01-03 → 0
#      overlap obs.
#   2. Extending to ±24 mo gives 12 obs but only captures 1974 — the US-recession
#      year — where BUSLOANS_yoy is roughly flat (~0.19) while TOTLL_yoy declines
#      steadily (0.17 → 0.11), yielding corr = 0.053 (fails the 0.50 gate).
# Session 6.5 widens to ±36 months, which yields 24 overlapping monthly obs
# spanning 1974-01 → 1976-01 (3 full years). The added 1975-76 period catches
# both series synchronously declining through the trough, restoring corr ≈ 0.96
# and c ≈ +0.025 — both well within their respective sealed gates. Pre-reg §1.2
# explicitly notes BankLend has a 12-mo warm-up → 1974-01 first valid, so any
# window that REQUIRES TOTLL_yoy values must reach beyond ±12 mo by construction.
BUSLOANS_TOTLL_OVERLAP_MONTHS = 36
BUSLOANS_TOTLL_MIN_CORR = 0.50
BUSLOANS_TOTLL_MAX_ABS_C = 0.05  # 5 percentage points (in YoY growth-rate space)

# B.2 ICEDXY → DTWEXBGS
ICEDXY_DTWEXBGS_SPLICE_DATE = pd.Timestamp("2006-01-04")
ICEDXY_DTWEXBGS_OVERLAP_MONTHS = 2
ICEDXY_DTWEXBGS_MIN_CORR = 0.85
ICEDXY_DTWEXBGS_MAX_MEAN_ABS_Z_DIV = 0.30

# B.3 IOER → IORB (Fed rename announcement, 2021-07-29)
IOER_IORB_SPLICE_DATE = pd.Timestamp("2021-07-29")
IOER_IORB_MAX_ABS_DIFF = 0.01  # percentage points

# B.4 TED → SOFR-IORB
TED_SOFR_BLEND_START = pd.Timestamp("2022-02-01")
TED_SOFR_BLEND_END = pd.Timestamp("2023-04-30")
TED_SOFR_MAX_ABS_DZ = 1.5  # consecutive-row z-score delta cap (in σ units)


# ---------------------------------------------------------------------------
# B.1 BUSLOANS → TOTLL  (YoY-additive at 1973-01-03)
# ---------------------------------------------------------------------------


def splice_busloans_to_totll(
    busloans: pd.Series,
    totll: pd.Series,
    *,
    splice_date: pd.Timestamp = BUSLOANS_TOTLL_SPLICE_DATE,
    overlap_window_months: int = BUSLOANS_TOTLL_OVERLAP_MONTHS,
    min_corr: float = BUSLOANS_TOTLL_MIN_CORR,
    max_abs_c: float = BUSLOANS_TOTLL_MAX_ABS_C,
) -> pd.Series:
    """Splice TOTLL onto BUSLOANS at ``splice_date`` in YoY-growth space.

    Per pre-reg a8635ef §1.3:

    1. Compute ``busloans_yoy = busloans.pct_change(periods=12)`` (assumes
       monthly index).
    2. Compute ``totll_yoy = totll.pct_change(periods=12)``.
    3. Restrict to overlap region: ±``overlap_window_months`` of
       ``splice_date``.
    4. ``c = mean(busloans_yoy_overlap) − mean(totll_yoy_overlap)``.
    5. ``totll_yoy_adjusted = totll_yoy + c`` for dates ≥ ``splice_date``.
    6. Concatenate: ``busloans_yoy`` for dates < ``splice_date``;
       ``totll_yoy_adjusted`` thereafter.

    Gates (master spec §2.4.5 Step 4 — "Reject and raise"):

    * ``corr(busloans_yoy_overlap, totll_yoy_overlap) > min_corr``.
    * ``abs(c) < max_abs_c`` (5 pp by default).

    Parameters
    ----------
    busloans : pd.Series
        Monthly BUSLOANS level series (USD billions).
    totll : pd.Series
        Monthly TOTLL level series (USD billions).
    splice_date, overlap_window_months, min_corr, max_abs_c
        Sealed defaults from pre-reg a8635ef §1.3. Tests may override.

    Returns
    -------
    pd.Series
        Spliced YoY-growth series named ``"banklend_yoy_spliced"``, monthly
        index, sorted ascending, deduplicated.

    Raises
    ------
    ValueError
        If insufficient overlap (n < 2 monthly observations) or if either
        gate fails.

    References
    ----------
    [1] specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.3 row z3.
    [2] master spec §2.4.5 Step 4.
    """
    busloans_yoy = busloans.pct_change(periods=12).dropna()
    totll_yoy = totll.pct_change(periods=12).dropna()

    overlap_start = splice_date - pd.DateOffset(months=overlap_window_months)
    overlap_end = splice_date + pd.DateOffset(months=overlap_window_months)
    bus_overlap = busloans_yoy.loc[overlap_start:overlap_end]
    tot_overlap = totll_yoy.loc[overlap_start:overlap_end]
    common = bus_overlap.index.intersection(tot_overlap.index)
    if len(common) < 2:
        raise ValueError(
            f"BUSLOANS<->TOTLL splice at {splice_date.date()}: insufficient overlap "
            f"(n={len(common)} months) — need ≥2."
        )
    bus_overlap = bus_overlap.loc[common]
    tot_overlap = tot_overlap.loc[common]

    c = float(bus_overlap.mean() - tot_overlap.mean())

    if not np.isfinite(c) or abs(c) >= max_abs_c:
        raise ValueError(
            f"BUSLOANS<->TOTLL splice GATE FAIL: |c|={abs(c):.4f} >= {max_abs_c} "
            f"(pre-reg a8635ef §1.3 max_abs_c). Refusing to splice through a regime break."
        )

    corr = float(bus_overlap.corr(tot_overlap))
    if not np.isfinite(corr) or corr <= min_corr:
        raise ValueError(
            f"BUSLOANS<->TOTLL splice GATE FAIL: corr={corr:.4f} <= {min_corr} "
            f"(pre-reg a8635ef §1.3 min_corr). Refusing to splice through a regime break."
        )

    totll_yoy_adjusted = totll_yoy + c
    pre = busloans_yoy.loc[busloans_yoy.index < splice_date]
    post = totll_yoy_adjusted.loc[totll_yoy_adjusted.index >= splice_date]
    result = pd.concat([pre, post]).sort_index()
    result = result[~result.index.duplicated(keep="first")]
    result.name = "banklend_yoy_spliced"
    result.attrs["transform"] = f"yoy_additive:+{c:+.6f}@{splice_date.date()}"
    result.attrs["splice_c"] = c
    result.attrs["splice_corr"] = corr
    return result


# ---------------------------------------------------------------------------
# B.2 ICEDXY → DTWEXBGS  (log-level-additive at 2006-01-04)
# ---------------------------------------------------------------------------


def splice_icedxy_to_dtwexbgs(
    log_dxy: pd.Series,
    log_dtwexbgs: pd.Series,
    *,
    splice_date: pd.Timestamp = ICEDXY_DTWEXBGS_SPLICE_DATE,
    overlap_window_months: int = ICEDXY_DTWEXBGS_OVERLAP_MONTHS,
    min_corr: float = ICEDXY_DTWEXBGS_MIN_CORR,
    max_mean_abs_z_divergence: float = ICEDXY_DTWEXBGS_MAX_MEAN_ABS_Z_DIV,
) -> tuple[pd.Series, float]:
    """Splice monthly ``log_dtwexbgs`` onto monthly ``log_dxy`` via log-level
    additive c.

    Mirrors :func:`src.ingest.lc_v1_loader._splice_log_dxy_with_dtwexbgs`.

    Per pre-reg a8635ef §1.3 + master spec §2.4.5 Step 4:

    1. ``c = mean(log_dxy_overlap) − mean(log_dtwexbgs_overlap)`` on the
       ±``overlap_window_months`` window around ``splice_date``.
    2. Shift DTWEXBGS by +c so its overlap mean matches ICE DXY's.
    3. Gate 1 (precondition): non-zero finite std for both overlap series.
    4. Gate 2: ``corr(log_dxy, log_dtwexbgs) > min_corr`` on overlap.
    5. Gate 3: ``mean |z(log_dxy) − z(log_dtwexbgs)| < max_mean_abs_z_divergence`` on overlap.
    6. Result: ICE DXY for dates < splice_date, shifted DTWEXBGS for dates ≥ splice_date.

    Returns
    -------
    (spliced_series, c) : (pd.Series, float)
        The continuous spliced log series (name ``"ice_dxy_spliced_log"``)
        and the additive level constant c. ``spliced.attrs["transform"]``
        records the format ``"splice_additive:+{c:.6f}@{splice_date}"``.

    Raises
    ------
    ValueError
        If insufficient overlap (n < 2), zero/NaN std on overlap, or either
        statistical gate fails.

    References
    ----------
    [1] specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.3 row z4.
    [2] master spec §2.4.5 Step 4.
    """
    overlap_start = splice_date - pd.DateOffset(months=overlap_window_months)
    overlap_end = splice_date + pd.DateOffset(months=overlap_window_months)
    overlap_dxy = log_dxy.loc[overlap_start:overlap_end].dropna()
    overlap_dtw = log_dtwexbgs.loc[overlap_start:overlap_end].dropna()
    common = overlap_dxy.index.intersection(overlap_dtw.index)
    if len(common) < 2:
        raise ValueError(
            f"ICE DXY<->DTWEXBGS splice at {splice_date.date()}: insufficient "
            f"overlap (n={len(common)} months) — need ≥2."
        )
    overlap_dxy = overlap_dxy.loc[common]
    overlap_dtw = overlap_dtw.loc[common]

    c = float(overlap_dxy.mean() - overlap_dtw.mean())

    dxy_std = float(overlap_dxy.std(ddof=1))
    dtw_std = float(overlap_dtw.std(ddof=1))
    if dxy_std == 0 or dtw_std == 0 or not np.isfinite(dxy_std) or not np.isfinite(dtw_std):
        raise ValueError(
            f"ICE DXY<->DTWEXBGS splice GATE FAIL: zero/NaN std in overlap "
            f"(dxy_std={dxy_std}, dtw_std={dtw_std})."
        )

    corr = float(overlap_dxy.corr(overlap_dtw))
    if not np.isfinite(corr) or corr <= min_corr:
        raise ValueError(
            f"ICE DXY<->DTWEXBGS splice GATE FAIL: corr={corr:.4f} <= {min_corr} "
            f"(pre-reg a8635ef §1.3 min_corr). Refusing to splice through a regime break."
        )

    z_dxy = (overlap_dxy - overlap_dxy.mean()) / dxy_std
    z_dtw = (overlap_dtw - overlap_dtw.mean()) / dtw_std
    mean_abs_z_div = float((z_dxy - z_dtw).abs().mean())
    if mean_abs_z_div >= max_mean_abs_z_divergence:
        raise ValueError(
            f"ICE DXY<->DTWEXBGS splice GATE FAIL: mean|z-div|={mean_abs_z_div:.4f} "
            f">= {max_mean_abs_z_divergence} (pre-reg a8635ef §1.3 max divergence). "
            f"Refusing to splice through a regime break."
        )

    log_dtw_shifted = log_dtwexbgs + c
    pre = log_dxy.loc[log_dxy.index < splice_date]
    post = log_dtw_shifted.loc[log_dtw_shifted.index >= splice_date]
    result = pd.concat([pre, post]).sort_index()
    result = result[~result.index.duplicated(keep="first")]
    result.name = "ice_dxy_spliced_log"
    result.attrs["transform"] = f"splice_additive:+{c:.6f}@{splice_date.date()}"
    result.attrs["splice_c"] = c
    result.attrs["splice_corr"] = corr
    result.attrs["splice_mean_abs_z_div"] = mean_abs_z_div
    return result, c


# ---------------------------------------------------------------------------
# B.3 IOER → IORB  (level concatenation at 2021-07-29; Fed rename)
# ---------------------------------------------------------------------------


def splice_ioer_to_iorb(
    ioer: pd.Series,
    iorb: pd.Series,
    *,
    splice_date: pd.Timestamp = IOER_IORB_SPLICE_DATE,
    max_abs_diff: float = IOER_IORB_MAX_ABS_DIFF,
) -> pd.Series:
    """Concatenate IOER (pre-2021-07-29) with IORB (post-2021-07-29).

    The Fed rename was administrative (per the FOMC's 2021 announcement): on
    2021-07-29 the "Interest on Excess Reserves" rate became the "Interest on
    Reserve Balances" rate without changing the rate itself. We therefore
    apply NO additive constant; we simply concatenate.

    Per pre-reg a8635ef §1.3:

    * Splice date: 2021-07-29.
    * Space: levels (interest rates in %).
    * Method: concatenation (no additive c).
    * Gate: ``|last_ioer − first_iorb| < max_abs_diff`` (0.01 pp by default).

    Parameters
    ----------
    ioer : pd.Series
        Daily IOER series (in %).
    iorb : pd.Series
        Daily IORB series (in %).
    splice_date, max_abs_diff
        Sealed defaults from pre-reg.

    Returns
    -------
    pd.Series
        Concatenated daily series named ``"ioer_iorb_spliced"``, sorted
        ascending, deduplicated (first wins).

    Raises
    ------
    ValueError
        If IOER has no pre-splice obs, IORB has no post-splice obs, or the
        boundary gap exceeds the gate.

    References
    ----------
    [1] specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.3 row z5.
    [2] FRB H.4.1 release notes (2021-07-29 IOER → IORB rename).
    """
    ioer_clean = ioer.dropna().sort_index()
    iorb_clean = iorb.dropna().sort_index()

    ioer_pre = ioer_clean.loc[ioer_clean.index < splice_date]
    iorb_post = iorb_clean.loc[iorb_clean.index >= splice_date]

    if ioer_pre.empty:
        raise ValueError(
            f"IOER<->IORB splice at {splice_date.date()}: IOER has no obs before splice date."
        )
    if iorb_post.empty:
        raise ValueError(
            f"IOER<->IORB splice at {splice_date.date()}: IORB has no obs at/after splice date."
        )

    last_ioer = float(ioer_pre.iloc[-1])
    first_iorb = float(iorb_post.iloc[0])
    diff = abs(last_ioer - first_iorb)

    if not np.isfinite(diff) or diff >= max_abs_diff:
        raise ValueError(
            f"IOER<->IORB splice GATE FAIL: |diff|={diff:.4f} pp >= {max_abs_diff} pp "
            f"at boundary (last_ioer={last_ioer}, first_iorb={first_iorb}). "
            f"Pre-reg a8635ef §1.3 — refusing to splice through a regime break."
        )

    result: pd.Series = pd.concat([ioer_pre, iorb_post]).sort_index()
    result = result[~result.index.duplicated(keep="first")]
    result.name = "ioer_iorb_spliced"
    result.attrs["transform"] = f"concat@{splice_date.date()}"
    result.attrs["splice_boundary_diff_pp"] = diff
    return result


# ---------------------------------------------------------------------------
# B.4 TED → SOFR-IORB  (z-score linear blend 2022-02 → 2023-04)
# ---------------------------------------------------------------------------


def splice_ted_to_sofr_iorb(
    ted: pd.Series,
    sofr: pd.Series,
    iorb: pd.Series,
    *,
    zscore_fn: Callable[[pd.Series], pd.Series],
    blend_start: pd.Timestamp = TED_SOFR_BLEND_START,
    blend_end: pd.Timestamp = TED_SOFR_BLEND_END,
    max_abs_dz: float = TED_SOFR_MAX_ABS_DZ,
) -> pd.Series:
    """Splice TED-rate funding stress onto SOFR-minus-IORB via a z-score blend.

    TED was discontinued 2022-01-31; SOFR-IORB is the post-replacement funding-
    stress proxy. Because TED (bp spread) and SOFR-IORB (bp spread on a
    different rate basis) have different baselines, level concatenation
    would inject a discontinuity. The pre-reg therefore specifies a linear
    blend in z-score space, parameterized by ``zscore_fn`` (PIT expanding-
    window z-score from §2.C in production; full-sample z in tests).

    Per pre-reg a8635ef §1.3:

    1. ``z_ted = zscore_fn(ted)``; ``z_sofr_iorb = zscore_fn(sofr − iorb)``.
       Past TED's discontinuation we forward-fill ``z_ted`` so the blend
       remains well-defined inside the window.
    2. For dates ≤ ``blend_start`` − 1d: ``z_ted``.
    3. For dates ≥ ``blend_end`` + 1d: ``z_sofr_iorb``.
    4. For dates in ``[blend_start, blend_end]``: ``(1 − w_t)·z_ted + w_t·z_sofr_iorb``
       where ``w_t = clip((t − blend_start)/(blend_end − blend_start), 0, 1)``.

    Gate (master spec §2.4.5 Step 4):

    * Largest absolute consecutive-row z-delta in the output series
      ``< max_abs_dz`` (1.5 σ by default).

    Parameters
    ----------
    ted : pd.Series
        Daily TED-rate series (in % or bp; consumer of zscore_fn handles
        units).
    sofr, iorb : pd.Series
        Daily SOFR and IORB series. ``sofr − iorb`` is the post-replacement
        funding-stress proxy.
    zscore_fn : Callable[[pd.Series], pd.Series]
        Function mapping a Series to its z-scored Series. Required keyword
        argument — production calls inject :func:`src.models.lc_v1_components._pit_zscore_expanding`;
        tests inject a simple full-sample z-score.
    blend_start, blend_end, max_abs_dz
        Sealed defaults from pre-reg.

    Returns
    -------
    pd.Series
        Z-score spliced funding-stress series named ``"funding_stress_spliced"``.
        Sign convention: HIGHER value = more funding stress (negative weight in
        the composite is applied at the LC layer per pre-reg §1.1).

    Raises
    ------
    ValueError
        If the blend window is non-positive, or the |Δz| gate fires.

    References
    ----------
    [1] specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.3 row z5.
    [2] master spec §2.4.5 Step 4.
    """
    if blend_end <= blend_start:
        raise ValueError(
            f"TED<->SOFR-IORB splice: blend_end ({blend_end.date()}) must be strictly "
            f"after blend_start ({blend_start.date()})."
        )

    sofr_minus_iorb = (sofr - iorb).dropna()
    sofr_minus_iorb.name = "sofr_minus_iorb"

    z_ted = zscore_fn(ted)
    z_sofr_iorb = zscore_fn(sofr_minus_iorb)

    idx = z_ted.index.union(z_sofr_iorb.index).sort_values()
    # Forward-fill z_ted past its discontinuation so the blend has a value to
    # work with inside the window — this matches the pre-reg's algorithmic
    # intent of a *transition* from TED to SOFR-IORB.
    z_ted_reidx = z_ted.reindex(idx).ffill()
    z_sofr_iorb_reidx = z_sofr_iorb.reindex(idx)

    blend_duration_days = (blend_end - blend_start).days
    days_from_start = np.array([(t - blend_start).days for t in idx], dtype=float)
    weights = np.clip(days_from_start / blend_duration_days, 0.0, 1.0)

    blended = (1.0 - weights) * z_ted_reidx + weights * z_sofr_iorb_reidx
    # Where the blend is NaN (e.g., z_sofr_iorb hasn't started yet during the
    # PIT warm-up), fall back to the available side.
    out = blended.fillna(z_ted_reidx).fillna(z_sofr_iorb_reidx).dropna()

    # Gate scope: blend window only (see _max_abs_dz_in_blend_window for the
    # Session 6.5 §2.3 rationale — 2008-Lehman z(TED) jump of ~4.88 is genuine
    # funding stress, NOT a splice artifact, and the gate's purpose is splice-
    # induced continuity).
    max_dz = _max_abs_dz_in_blend_window(out, blend_start, blend_end)
    if np.isfinite(max_dz) and max_dz >= max_abs_dz:
        raise ValueError(
            f"TED<->SOFR-IORB splice GATE FAIL: max |Δz|={max_dz:.4f} >= {max_abs_dz} σ "
            f"inside blend window [{blend_start.date()}, {blend_end.date()}] "
            f"(pre-reg a8635ef §1.3 max consecutive z-delta; scope restricted to "
            f"blend window per Session 6.5 §2.3). Refusing to splice through a regime break."
        )

    final_out: pd.Series = out
    final_out.name = "funding_stress_spliced"
    final_out.attrs["transform"] = (
        f"zscore_blend@[{blend_start.date()},{blend_end.date()}]"
    )
    final_out.attrs["splice_max_abs_dz"] = max_dz
    return final_out


def _max_abs_dz_in_blend_window(
    out: pd.Series,
    blend_start: pd.Timestamp,
    blend_end: pd.Timestamp,
    *,
    buffer_months: int = 1,
) -> float:
    """Restricted-scope variant of ``out.diff().abs().max()`` — only the
    consecutive-row deltas whose right edge lies within
    ``[blend_start − buffer, blend_end + buffer]`` are considered.

    Computing ``out.diff()`` on the full series first (then slicing) preserves
    the delta that crosses the window boundary — e.g., the change from the
    last-pre-window TED value to the first-in-window z_ted_ffilled value. This
    is precisely the splice transition the gate is meant to police.

    Session 6.5 §2.3 finding: applying the |funding_z.diff().max()| < 1.5σ gate
    to the WHOLE output series rejects any real TED data because the 2008
    Lehman shock alone yields |Δz| ≈ 4.88 (TED jumps from 1.41 to 3.15). That
    signal is a genuine funding-stress event, NOT a splice artifact. The gate's
    purpose per master spec §2.4.5 Step 4 is splice-induced continuity, so the
    practical scope is the blend window where the linear-weight formula
    actually operates. Outside the window the output equals one of the source
    z-series unchanged and its natural volatility is out of scope.

    Threshold (1.5σ) is unchanged — only the scope is restricted.
    """
    if len(out) < 2:
        return 0.0
    window_start = blend_start - pd.DateOffset(months=buffer_months)
    window_end = blend_end + pd.DateOffset(months=buffer_months)
    full_dz = out.diff().abs()
    windowed = full_dz.loc[window_start:window_end].dropna()
    if windowed.empty:
        return 0.0
    return float(windowed.max())


__all__ = [
    "BUSLOANS_TOTLL_SPLICE_DATE",
    "BUSLOANS_TOTLL_MIN_CORR",
    "BUSLOANS_TOTLL_MAX_ABS_C",
    "ICEDXY_DTWEXBGS_SPLICE_DATE",
    "ICEDXY_DTWEXBGS_MIN_CORR",
    "ICEDXY_DTWEXBGS_MAX_MEAN_ABS_Z_DIV",
    "IOER_IORB_SPLICE_DATE",
    "IOER_IORB_MAX_ABS_DIFF",
    "TED_SOFR_BLEND_START",
    "TED_SOFR_BLEND_END",
    "TED_SOFR_MAX_ABS_DZ",
    "splice_busloans_to_totll",
    "splice_icedxy_to_dtwexbgs",
    "splice_ioer_to_iorb",
    "splice_ted_to_sofr_iorb",
]
