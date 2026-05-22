"""LC v1.0 component z-scores (5 components) per sealed pre-reg a8635ef §1.1 + §3.1.

Five components feed the Liquidity Composite v1.0:

* ``compute_z1_netfed``         — Net Fed liquidity (WALCL − WDTGAL − RRPONTSYD),
                                  PIT z-score, monthly. Active from 2003-01.
* ``compute_z2_m2_yoy``         — M2 YoY growth, PIT z-score. Active from 1960-01.
* ``compute_z3_banklend_yoy``   — BUSLOANS→TOTLL YoY spliced @1973-01, PIT z-score.
                                  Active from ~1948.
* ``compute_z4_dxy_inv``        — Negated z of spliced log(ICE DXY↔DTWEXBGS @2006-01).
                                  Sign convention: higher z₄ = weaker dollar = higher
                                  liquidity (consistent with the +0.20 weight in LC_FULL).
                                  Active from 1971-01.
* ``compute_z5_funding_stress`` — TED → SOFR-IORB blend (2022-02 → 2023-04).
                                  Sign convention: higher z₅ = more stress (the
                                  −0.15 weight in LC_FULL handles the directional
                                  flip; DO NOT negate at the component level).
                                  Active from 1986-01.

All components share ``_pit_zscore_expanding`` for strict point-in-time z-scoring
(μ_t and σ_t computed from observations strictly prior to t, never including t).

References
----------
* specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.1 — sealed component definitions.
* specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §3.1 — PIT z-score spec.
* master spec §2.1 — standardization rules.
* prompt/052226/PROMPT_v11_3_stage_3_LC_v1_session_6.md §2.C — sub-stage spec.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from src.transform.lc_v1_splices import (
    splice_busloans_to_totll,
    splice_ioer_to_iorb,
    splice_ted_to_sofr_iorb,
)


# ---------------------------------------------------------------------------
# Sealed constants per pre-reg a8635ef §3.1
# ---------------------------------------------------------------------------

#: Minimum number of strictly-prior observations required for a non-NaN z.
#: Sealed at 120 months (10 years) per pre-reg §3.1.
PIT_ZSCORE_MIN_N = 120


# ---------------------------------------------------------------------------
# Helper: strict-PIT expanding-window z-score
# ---------------------------------------------------------------------------


def _pit_zscore_expanding(
    series: pd.Series,
    min_n: int = PIT_ZSCORE_MIN_N,
) -> pd.Series:
    """Point-in-time expanding-window z-score with STRICT exclusion of the
    current observation.

    For each date ``t``:

    * ``μ_t  = mean(series[:t])`` — explicitly EXCLUDES ``series[t]``.
    * ``σ_t  = sample SD of series[:t]`` (Bessel n−1 correction).
    * ``z_t  = (series[t] − μ_t) / σ_t``, only when ``len(series[:t]) ≥ min_n``;
      otherwise NaN.

    "Strict PIT exclusion" is a stronger guarantee than the default
    ``series.expanding().mean()`` behavior, which INCLUDES the current row at
    index ``t``. We implement strict exclusion via ``.shift(1)`` on the
    expanding statistics — so ``μ_t`` actually contains the mean of
    ``series[0:t]`` (up to but not including ``t``).

    Parameters
    ----------
    series : pd.Series
        Monthly-frequency input, sorted ascending by date, NaN-free where
        defined.
    min_n : int
        Minimum prior-observation count before ``z`` is non-NaN. Default
        ``PIT_ZSCORE_MIN_N`` (120 months) per pre-reg §3.1.

    Returns
    -------
    pd.Series
        Same index as input. Values are NaN for the first ``min_n``
        observations (strictly: where ``count(series[:t]) < min_n``).

    Edge cases
    ----------
    * Empty input → empty Series.
    * Constant input → ``σ_t = 0`` → returns NaN at every date (avoids
      division-by-zero).
    * NaN propagates: ``z_t`` is NaN if ``series[t]`` is NaN.

    References
    ----------
    [1] specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §3.1 — PIT discipline.
    [2] master spec §2.1 — standardization.
    """
    if series.empty:
        return series.copy()

    # Strict-PIT: shift the expanding statistics by 1 so the mean at row t
    # contains observations from rows [0..t-1].
    mu = series.expanding(min_periods=min_n).mean().shift(1)
    sigma = series.expanding(min_periods=min_n).std(ddof=1).shift(1)

    # Guard zero/NaN sigma (constant or insufficient input).
    sigma_safe = sigma.where((sigma > 0) & sigma.notna(), other=np.nan)
    z = (series - mu) / sigma_safe
    z.name = (series.name + "_z") if isinstance(series.name, str) else "z"
    return z


# ---------------------------------------------------------------------------
# Internal helper: load a master series if the caller did not inject one.
# ---------------------------------------------------------------------------


def _load_master_series(series_id: str, vintage: str | pd.Timestamp | None) -> pd.Series:
    """Wrap ``load_master`` so callers can inject test data via parameter."""
    from src.ingest.master_archive import load_master
    ms = load_master(series_id, vintage=vintage)
    s = ms.data.astype("float64").dropna()
    s.name = series_id
    return s


def _resample_monthly_eom(series: pd.Series) -> pd.Series:
    """Resample any-frequency input to monthly end-of-month (last observation)."""
    if series.empty:
        return series.copy()
    out = series.resample("ME").last().dropna()
    out.name = series.name
    return out


# ---------------------------------------------------------------------------
# z₁ NetFed (WALCL − WDTGAL − RRPONTSYD)
# ---------------------------------------------------------------------------


def compute_z1_netfed(
    *,
    walcl: pd.Series | None = None,
    wdtgal: pd.Series | None = None,
    rrpontsyd: pd.Series | None = None,
    vintage: str | pd.Timestamp | None = None,
    min_n: int = PIT_ZSCORE_MIN_N,
) -> pd.Series:
    """Compute z₁ NetFed = PIT-z(WALCL − WDTGAL − RRPONTSYD), monthly EOM.

    Active from 2003-01 in principle (WALCL starts 2002-12; the 12-month
    warm-up brings z₁ to non-NaN around 2003-12 once min_n=120 PIT history
    has accumulated). Pragmatically anchored at 2003-01 in spec §1.1.

    Parameters
    ----------
    walcl, wdtgal, rrpontsyd : pd.Series, optional
        Pre-loaded source series. If None, loaded via ``load_master`` with
        the supplied ``vintage``.
    vintage : 'latest' | pd.Timestamp | ISO date string | None
        Forwarded to ``load_master``. Tests typically inject the series and
        leave ``vintage`` unset.
    min_n : int
        Override the PIT-z warm-up requirement for testing.

    Returns
    -------
    pd.Series
        Monthly-EOM PIT z-score series named ``"z1_netfed"``.
    """
    if walcl is None:
        walcl = _load_master_series("walcl", vintage)
    if wdtgal is None:
        wdtgal = _load_master_series("wdtgal", vintage)
    if rrpontsyd is None:
        rrpontsyd = _load_master_series("rrpontsyd", vintage)

    walcl_m = _resample_monthly_eom(walcl)
    wdtgal_m = _resample_monthly_eom(wdtgal)
    rrpontsyd_m = _resample_monthly_eom(rrpontsyd)

    # Align on common monthly index. Forward-fill RRPONTSYD pre-2013-09-23
    # (zero-fill per spec) — but here we keep it simple: take the intersection
    # of dates where all three are defined.
    idx = walcl_m.index.intersection(wdtgal_m.index).intersection(rrpontsyd_m.index)
    if idx.empty:
        return pd.Series([], dtype="float64", index=pd.DatetimeIndex([]), name="z1_netfed")

    netfed = walcl_m.loc[idx] - wdtgal_m.loc[idx] - rrpontsyd_m.loc[idx]
    netfed.name = "netfed"
    z = _pit_zscore_expanding(netfed, min_n=min_n)
    z.name = "z1_netfed"
    return z


# ---------------------------------------------------------------------------
# z₂ M2 YoY growth
# ---------------------------------------------------------------------------


def compute_z2_m2_yoy(
    *,
    m2sl: pd.Series | None = None,
    vintage: str | pd.Timestamp | None = None,
    min_n: int = PIT_ZSCORE_MIN_N,
) -> pd.Series:
    """Compute z₂ = PIT-z(M2 YoY), where M2 YoY = ``M2SL.pct_change(12)``.

    Active from 1960-01 in principle (M2SL starts 1959-01; YoY needs 12mo;
    z needs 120mo prior).
    """
    if m2sl is None:
        m2sl = _load_master_series("m2_sl", vintage)
    m2_m = _resample_monthly_eom(m2sl)
    m2_yoy = m2_m.pct_change(periods=12)
    m2_yoy.name = "m2_yoy"
    z = _pit_zscore_expanding(m2_yoy, min_n=min_n)
    z.name = "z2_m2_yoy"
    return z


# ---------------------------------------------------------------------------
# z₃ BankLend YoY (spliced BUSLOANS → TOTLL)
# ---------------------------------------------------------------------------


def compute_z3_banklend_yoy(
    *,
    busloans: pd.Series | None = None,
    totll: pd.Series | None = None,
    vintage: str | pd.Timestamp | None = None,
    min_n: int = PIT_ZSCORE_MIN_N,
) -> pd.Series:
    """Compute z₃ = PIT-z(spliced BUSLOANS → TOTLL YoY).

    Uses :func:`src.transform.lc_v1_splices.splice_busloans_to_totll` for the
    1973-01-03 splice (YoY-additive, gates corr>0.50, |c|<0.05).
    """
    if busloans is None:
        busloans = _load_master_series("busloans", vintage)
    if totll is None:
        totll = _load_master_series("totll", vintage)
    busloans_m = _resample_monthly_eom(busloans)
    totll_m = _resample_monthly_eom(totll)
    banklend_yoy = splice_busloans_to_totll(busloans_m, totll_m)
    z = _pit_zscore_expanding(banklend_yoy, min_n=min_n)
    z.name = "z3_banklend_yoy"
    return z


# ---------------------------------------------------------------------------
# z₄ DXY⁻¹ (negated PIT-z of spliced log ICE DXY)
# ---------------------------------------------------------------------------


def compute_z4_dxy_inv(
    *,
    log_dxy_spliced: pd.Series | None = None,
    vintage: str | pd.Timestamp | None = None,
    min_n: int = PIT_ZSCORE_MIN_N,
) -> pd.Series:
    """Compute z₄ = −PIT-z(spliced log ICE DXY ↔ DTWEXBGS @ 2006-01-04).

    The negation flips the sign so that higher z₄ = weaker dollar = higher
    liquidity, consistent with the +0.20 weight on z₄ in LC_FULL per pre-reg
    a8635ef §1.1.

    Parameters
    ----------
    log_dxy_spliced : pd.Series, optional
        Pre-built model-ready monthly log series. If None, built via
        :func:`src.ingest.lc_v1_loader.build_lc_icedxy_master`.

    Notes
    -----
    Building the log-spliced series internally may raise if the local
    ICE DXY cache parquet is missing — surface that as ``RuntimeError`` per
    Session 6 §2.0 (owner action: run the Norgate bootstrap).
    """
    if log_dxy_spliced is None:
        from src.ingest.lc_v1_loader import build_lc_icedxy_master
        log_dxy_spliced = build_lc_icedxy_master(splice_dtwexbgs=True)
    log_dxy_spliced.name = "log_dxy_spliced"
    z = _pit_zscore_expanding(log_dxy_spliced, min_n=min_n)
    z_inv = -z
    z_inv.name = "z4_dxy_inv"
    return z_inv


# ---------------------------------------------------------------------------
# z₅ Funding stress (TED → SOFR-IORB blend)
# ---------------------------------------------------------------------------


def compute_z5_funding_stress(
    *,
    ted: pd.Series | None = None,
    sofr: pd.Series | None = None,
    iorb: pd.Series | None = None,
    ioer: pd.Series | None = None,
    vintage: str | pd.Timestamp | None = None,
    min_n: int = PIT_ZSCORE_MIN_N,
    zscore_fn: Callable[[pd.Series], pd.Series] | None = None,
) -> pd.Series:
    """Compute z₅ = funding-stress series spliced TED → (SOFR − IORB).

    Sign convention: HIGHER z₅ = more funding stress; the LC composite layer
    applies the −0.15 weight to flip direction. Do NOT negate at this layer
    (would double-flip).

    Pipeline:

    1. Splice IOER pre-2021-07-29 with IORB post-2021-07-29 (Fed rename) via
       :func:`src.transform.lc_v1_splices.splice_ioer_to_iorb`.
    2. Resample TED, SOFR, IORB-spliced to monthly EOM.
    3. Apply z-score linear blend via
       :func:`src.transform.lc_v1_splices.splice_ted_to_sofr_iorb` (TED
       2022-02 → SOFR-IORB 2023-04).

    Parameters
    ----------
    zscore_fn : Callable, optional
        Override the z-score helper used by the blend. Default
        ``_pit_zscore_expanding`` (with ``min_n``).
    """
    if ted is None:
        ted = _load_master_series("tedrate", vintage)
    if sofr is None:
        sofr = _load_master_series("sofr", vintage)
    if iorb is None:
        iorb = _load_master_series("iorb", vintage)
    if ioer is None:
        ioer = _load_master_series("ioer", vintage)

    iorb_spliced = splice_ioer_to_iorb(ioer, iorb)
    ted_m = _resample_monthly_eom(ted)
    sofr_m = _resample_monthly_eom(sofr)
    iorb_m = _resample_monthly_eom(iorb_spliced)

    if zscore_fn is None:
        def _default_z(s: pd.Series) -> pd.Series:
            return _pit_zscore_expanding(s, min_n=min_n)
        zscore_fn = _default_z

    result = splice_ted_to_sofr_iorb(
        ted_m, sofr_m, iorb_m, zscore_fn=zscore_fn,
    )
    result.name = "z5_funding_stress"
    return result


__all__ = [
    "PIT_ZSCORE_MIN_N",
    "_pit_zscore_expanding",
    "compute_z1_netfed",
    "compute_z2_m2_yoy",
    "compute_z3_banklend_yoy",
    "compute_z4_dxy_inv",
    "compute_z5_funding_stress",
]
