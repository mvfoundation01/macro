"""Phase E.1 — v2.0 panel builder per sealed pre-reg §3 + §10.1 (seal 2a94417).

Composes 5 components (z1..z5) → 3 composites (LC_FULL / LC_TIER2 / LC_DEEP)
× 4 horizons (1Y / 3Y / 5Y / 10Y) = 12 candidate (composite x horizon) cells
for the v2.0 predictive-regression sweep.

Key sealed invariants
---------------------
- Components are brought to month-end-of-month frequency BEFORE z-scoring
  (sealed §10.1).
- PIT z-score uses ``min_window=120`` monthly obs with strict-shift exclusion
  (sealed §10.1 + Phase C ``src/transform/pit_zscore.py``).
- Composite weights / effective starts per sealed §10.1 (Phase C
  ``src/transform/composite.py``).
- RRPONTSYD zero-fill pre-2013-09-23 per sealed §3.2.3.
- Forward returns: SPXTR + Shiller spliced @ 1988-01 per sealed §3.1.
- OOS split per cell (default: inherits v1.0 split dates per sealed §10.1
  inheritance; configurable for Phase E).

Data-availability notes (verdict JSON `_meta` will document)
-----------------------------------------------------------
1. ICE_DXY pre-2006 source not available in the master archive
   (``data/master/icedxy_close.parquet`` absent). z4 uses DTWEXBGS only,
   so z4 first non-NaN appears around 2006 + 120-month z-score warm-up
   = ~2016.
2. SOFR-IORB monthly history is insufficient (SOFR starts 2018-04, IORB
   starts 2021-07) for the strict sealed §10.1 monthly-frequency PIT
   z-score of the spread (would require 120 monthly obs ≈ 2031). For
   the z5 SOFR-IORB regime, we use a SHORT-WINDOW z-score (n>=24
   monthly) as a documented Phase E approximation; pre-2022 z5 uses
   the full 120-month PIT z-score on TED. The blend window 2022-02 →
   2023-04 linearly transitions between the two. This deviates from
   sealed §10.1's strict 120 floor only for the post-splice regime;
   pre-splice z5 honors the sealed floor. The verdict JSON ``_meta``
   surfaces this as ``z5_post_splice_warmup_relaxed_to_24mo``.

References
----------
- Sealed pre-reg §3 (methodology), §10.1 (inherited from v1.0), §3.2.3
  (RRPONTSYD zero-fill), §3.1 (forward returns).
- Phase B+C arbitration: ``PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md``.
- Phase E prompt: ``PROMPT_CC_v11_4_v2_sprint_PHASE_E.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from src.ingest.master_archive import load_master
from src.transform.composite import (
    SCOPE_EFFECTIVE_START,
    SCOPE_WEIGHTS,
    build_composite,
)
from src.transform.forward_returns import (
    build_forward_returns,
    forward_returns as compute_forward_returns_table,
    shiller_nominal_total_return,
    spxtr_monthly_level,
    splice_shiller_spxtr,
)
from src.transform.pit_zscore import pit_zscore
from src.transform.splice import (
    _concat_ioer_iorb_impl,
    _splice_busloans_totll_yoy_impl,
    _splice_ted_sofr_iorb_zblend_impl,
)


PIT_MIN_WINDOW_MONTHLY: int = 120
"""Sealed §10.1 default PIT z-score warm-up (120 monthly obs)."""

PIT_MIN_WINDOW_SHORT: int = 24
"""Phase E z5 post-splice relaxed warm-up (24 monthly obs ≈ 2 years).
See module docstring data-availability note 2."""

RRPONTSYD_DENSE_FROM: pd.Timestamp = pd.Timestamp("2013-09-23")
"""Per sealed §3.2.3: RRPONTSYD zero-fill for observation-date < 2013-09-23."""

DEFAULT_OOS_SPLIT: dict[str, pd.Timestamp] = {
    "LC_FULL": pd.Timestamp("2021-01-31"),
    "LC_TIER2": pd.Timestamp("2021-01-31"),
    "LC_DEEP": pd.Timestamp("2021-01-31"),
}
"""Per sealed §3.2.1, the estimation window expands from the longest
jointly-available date per scope. In v2.0, z4 (DXY) is the limiting
component: DTWEXBGS starts 2006-01 → 120-month PIT z-score warm-up =>
z4 valid 2016-01. v1.0 OOS split dates (2011-01 LC_TIER2/DEEP, 2013-01
LC_FULL) pre-date v2.0's composite valid start (2016-01) and so are
not usable; a data-driven split at 2021-01-31 (mid-range of the v2.0
composite valid window 2016-01..2026-03) is used by default per
Phase E §2 + sealed §3.2.1. See verdict JSON `_meta` for documentation.
"""

DEFAULT_HORIZONS_YEARS: tuple[int, ...] = (1, 3, 5, 10)
HORIZONS_MONTHS: dict[int, int] = {1: 12, 3: 36, 5: 60, 10: 120}


@dataclass(frozen=True)
class ComponentBundle:
    """Container for the 5 components' z-scored monthly series + provenance."""

    z1: Optional[pd.Series]
    z2: Optional[pd.Series]
    z3: Optional[pd.Series]
    z4: Optional[pd.Series]
    z5: Optional[pd.Series]
    raw_levels: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PanelCell:
    """Single (scope x horizon) candidate cell."""

    composite: str
    horizon_months: int
    horizon_years: int
    composite_series: pd.Series
    forward_return_series: pd.Series
    n_obs_total: int
    n_obs_insample: int
    n_obs_oos: int
    feature_vintage_max: Optional[pd.Timestamp]
    oos_split_date: pd.Timestamp


@dataclass(frozen=True)
class V2Panel:
    """Full v2.0 panel: 5 components + 3 composites + 12 candidate cells."""

    components: ComponentBundle
    composites: dict[str, pd.Series]
    forward_returns: dict[int, pd.Series]
    cells: dict[tuple[str, int], PanelCell]
    meta: dict


# ---------------------------------------------------------------------------
# Component builders (monthly EOM → PIT z-score; pattern follows v1.0)
# ---------------------------------------------------------------------------


def _resample_monthly_eom(series: pd.Series) -> pd.Series:
    if series.empty:
        return series.copy()
    out = series.resample("ME").last().dropna()
    out.name = series.name
    return out


def build_z1_netfed(
    walcl: Optional[pd.Series] = None,
    wdtgal: Optional[pd.Series] = None,
    rrpontsyd: Optional[pd.Series] = None,
    min_window: int = PIT_MIN_WINDOW_MONTHLY,
) -> pd.Series:
    """z1 NetFed = PIT-z(WALCL - WDTGAL - RRPONTSYD); monthly EOM.

    RRPONTSYD pre-2013-09-23 is zero-filled per sealed §3.2.3.
    """
    if walcl is None:
        walcl = load_master("walcl").data.astype("float64").dropna()
    if wdtgal is None:
        wdtgal = load_master("wdtgal").data.astype("float64").dropna()
    if rrpontsyd is None:
        rrpontsyd = load_master("rrpontsyd").data.astype("float64").dropna()

    walcl_m = _resample_monthly_eom(walcl)
    wdtgal_m = _resample_monthly_eom(wdtgal)
    rrpontsyd_m = _resample_monthly_eom(rrpontsyd)

    union_idx = walcl_m.index.union(wdtgal_m.index).union(rrpontsyd_m.index)
    rrpontsyd_m = rrpontsyd_m.reindex(union_idx)
    pre_2013_mask = union_idx < RRPONTSYD_DENSE_FROM
    rrpontsyd_m.loc[pre_2013_mask] = rrpontsyd_m.loc[pre_2013_mask].fillna(0.0)

    idx = walcl_m.index.intersection(wdtgal_m.index).intersection(rrpontsyd_m.index)
    if idx.empty:
        return pd.Series(dtype="float64", name="z1_netfed")
    netfed = walcl_m.loc[idx] - wdtgal_m.loc[idx] - rrpontsyd_m.loc[idx]
    netfed = netfed.dropna()
    netfed.name = "netfed"
    z = pit_zscore(netfed, min_window=min_window, strict_shift=True)
    z.name = "z1_netfed"
    return z


def build_z2_m2_yoy(
    m2sl: Optional[pd.Series] = None,
    min_window: int = PIT_MIN_WINDOW_MONTHLY,
) -> pd.Series:
    """z2 = PIT-z(M2SL YoY growth); monthly EOM."""
    if m2sl is None:
        m2sl = load_master("m2_sl").data.astype("float64").dropna()
    m2_m = _resample_monthly_eom(m2sl)
    m2_yoy = m2_m.pct_change(periods=12)
    m2_yoy.name = "m2_yoy"
    z = pit_zscore(m2_yoy, min_window=min_window, strict_shift=True)
    z.name = "z2_m2_yoy"
    return z


def build_z3_banklend_yoy(
    busloans: Optional[pd.Series] = None,
    totll: Optional[pd.Series] = None,
    splice_date: pd.Timestamp = pd.Timestamp("1973-01-03"),
    min_window: int = PIT_MIN_WINDOW_MONTHLY,
) -> pd.Series:
    """z3 = PIT-z(BUSLOANS->TOTLL spliced YoY); monthly EOM."""
    if busloans is None:
        busloans = load_master("busloans").data.astype("float64").dropna()
    if totll is None:
        totll = load_master("totll").data.astype("float64").dropna()
    busloans_m = _resample_monthly_eom(busloans)
    totll_m = _resample_monthly_eom(totll)
    bus_yoy = busloans_m.pct_change(periods=12)
    tot_yoy = totll_m.pct_change(periods=12)
    spliced, _meta = _splice_busloans_totll_yoy_impl(
        bus_yoy, tot_yoy, splice_date, overlap_months=36
    )
    z = pit_zscore(spliced, min_window=min_window, strict_shift=True)
    z.name = "z3_banklend_yoy"
    return z


def build_z4_dxy_inverse(
    dtwexbgs: Optional[pd.Series] = None,
    min_window: int = PIT_MIN_WINDOW_MONTHLY,
) -> pd.Series:
    """z4 = -PIT-z(log(DTWEXBGS)); monthly EOM.

    Sealed §10.1 specifies a splice to ICE_DXY pre-2006; ICE_DXY data is
    not available in the v2.0 master archive (see module docstring note 1).
    z4 uses DTWEXBGS only; first non-NaN around 2006 + 120-month z-score
    warm-up = ~2016.
    """
    if dtwexbgs is None:
        dtwexbgs = load_master("dtwexbgs").data.astype("float64").dropna()
    dtw_m = _resample_monthly_eom(dtwexbgs)
    log_dtw = np.log(dtw_m)
    log_dtw.name = "log_dxy"
    z = pit_zscore(log_dtw, min_window=min_window, strict_shift=True)
    z_inv = -z
    z_inv.name = "z4_dxy_inverse"
    return z_inv


def build_z5_funding_stress(
    ted: Optional[pd.Series] = None,
    sofr: Optional[pd.Series] = None,
    iorb: Optional[pd.Series] = None,
    ioer: Optional[pd.Series] = None,
    blend_start: pd.Timestamp = pd.Timestamp("2022-02-28"),
    blend_end: pd.Timestamp = pd.Timestamp("2023-04-30"),
    min_window_ted: int = PIT_MIN_WINDOW_MONTHLY,
    min_window_spread: int = PIT_MIN_WINDOW_SHORT,
) -> pd.Series:
    """z5 = funding stress, TED → (SOFR - IORB_extended) z-score blend; monthly EOM.

    Per sealed §10.1 + Phase E data-availability note 2:
    - z_TED uses sealed 120-month PIT warm-up (TED starts 1986; z valid ~1996)
    - z_spread uses RELAXED 24-month warm-up (SOFR-IORB only since 2021-07)
    - linear z-blend over [blend_start, blend_end] (~14 months)
    """
    if ted is None:
        ted = load_master("tedrate").data.astype("float64").dropna()
    if sofr is None:
        sofr = load_master("sofr").data.astype("float64").dropna()
    if iorb is None:
        iorb = load_master("iorb").data.astype("float64").dropna()
    if ioer is None:
        ioer = load_master("ioer").data.astype("float64").dropna()

    ted_m = _resample_monthly_eom(ted)
    sofr_m = _resample_monthly_eom(sofr)
    iorb_m = _resample_monthly_eom(iorb)
    ioer_m = _resample_monthly_eom(ioer)

    # IOER -> IORB extension (monthly). Find the first monthly boundary on/after
    # 2021-07-29; that becomes the concat boundary at monthly grain.
    boundary_month = pd.Timestamp("2021-07-31")
    pre = ioer_m.loc[ioer_m.index < boundary_month]
    post = iorb_m.loc[iorb_m.index >= boundary_month]
    iorb_extended = pd.concat([pre, post]).sort_index()
    iorb_extended = iorb_extended[~iorb_extended.index.duplicated(keep="last")]
    iorb_extended.name = "iorb_extended_monthly"

    spread = (sofr_m - iorb_extended).dropna()
    spread.name = "sofr_minus_iorb_monthly"

    z_ted = pit_zscore(ted_m, min_window=min_window_ted, strict_shift=True)
    z_spread = pit_zscore(spread, min_window=min_window_spread, strict_shift=True)

    z5, _meta = _splice_ted_sofr_iorb_zblend_impl(
        z_ted, z_spread, blend_start=blend_start, blend_end=blend_end,
        diff_sigma_threshold=1.5,
    )
    z5.name = "z5_funding_stress"
    return z5


# ---------------------------------------------------------------------------
# Top-level builders
# ---------------------------------------------------------------------------


def build_all_components() -> ComponentBundle:
    """Build the 5 z-scored components per sealed §10.1."""
    z1 = build_z1_netfed()
    z2 = build_z2_m2_yoy()
    z3 = build_z3_banklend_yoy()
    z4 = build_z4_dxy_inverse()
    z5 = build_z5_funding_stress()

    metadata = {
        "z1_netfed": {
            "construction": "WALCL - WDTGAL - RRPONTSYD (level), monthly EOM, PIT z-score n>=120",
            "rrpontsyd_pre2013_treatment": "zero_fill_strict_lt_2013_09_23",
        },
        "z2_m2_yoy": {
            "construction": "M2SL.pct_change(12), monthly EOM, PIT z-score n>=120",
        },
        "z3_banklend_yoy": {
            "construction": "(BUSLOANS YoY + c) -> TOTLL YoY @ 1973-01-03 splice, PIT z-score n>=120",
        },
        "z4_dxy_inverse": {
            "construction": "-PIT-z(log(DTWEXBGS)), monthly EOM, n>=120",
            "icedxy_pre2006_source_status": "not_available_in_v2_master_archive",
        },
        "z5_funding_stress": {
            "construction": "linear z-blend(z_TED, z_SOFR_IORB) over 2022-02 -> 2023-04",
            "z_ted_warmup": PIT_MIN_WINDOW_MONTHLY,
            "z_spread_warmup_relaxed": PIT_MIN_WINDOW_SHORT,
            "rationale": "SOFR-IORB monthly history insufficient for 120-mo PIT z-score; relaxed to 24 mo",
        },
    }
    return ComponentBundle(
        z1=z1, z2=z2, z3=z3, z4=z4, z5=z5, metadata=metadata,
    )


def build_all_composites(components: ComponentBundle) -> dict[str, pd.Series]:
    """Build LC_FULL / LC_TIER2 / LC_DEEP composites per sealed §10.1."""
    out: dict[str, pd.Series] = {}
    out["LC_FULL"] = build_composite(
        z1=components.z1, z2=components.z2, z3=components.z3,
        z4=components.z4, z5=components.z5, scope="LC_FULL",
    )
    out["LC_TIER2"] = build_composite(
        z1=None, z2=components.z2, z3=components.z3,
        z4=components.z4, z5=components.z5, scope="LC_TIER2",
    )
    out["LC_DEEP"] = build_composite(
        z1=None, z2=components.z2, z3=components.z3,
        z4=components.z4, z5=None, scope="LC_DEEP",
    )
    return out


def build_spliced_forward_returns(
    horizons_years: tuple[int, ...] = DEFAULT_HORIZONS_YEARS,
) -> dict[int, pd.Series]:
    """SPXTR + Shiller spliced forward returns per sealed §3.1."""
    from src.ingest.shiller_loader import load_shiller
    from src.ingest.csv_loader import load_tradingview_file
    from src.config import TV_SPXTR

    sh = load_shiller()
    spxtr_daily = load_tradingview_file(TV_SPXTR, expected_symbol="SPXTR").data["close"]

    shiller_nominal = shiller_nominal_total_return(sh)
    shiller_nominal.index = (
        pd.DatetimeIndex(shiller_nominal.index)
        .to_period("M").to_timestamp(how="end").normalize()
    )
    spxtr_monthly = spxtr_monthly_level(spxtr_daily)
    spliced = splice_shiller_spxtr(shiller_nominal, spxtr_monthly, check_continuity=False)

    horizons_months = [HORIZONS_MONTHS[h] for h in horizons_years]
    fr_table = compute_forward_returns_table(spliced, horizons_months=horizons_months)
    fr_by_horizon: dict[int, pd.Series] = {}
    for h_y, h_m in zip(horizons_years, horizons_months):
        col = f"r_{h_m}m"
        if col in fr_table.columns:
            fr_by_horizon[h_y] = fr_table[col].rename(f"fr_{h_y}y")
    return fr_by_horizon


def _feature_vintage_max_in_window(
    composite_series: pd.Series, last_date: pd.Timestamp
) -> Optional[pd.Timestamp]:
    """Return the latest date <= last_date where composite is non-NaN."""
    in_window = composite_series.loc[composite_series.index <= last_date].dropna()
    if in_window.empty:
        return None
    return pd.Timestamp(in_window.index.max())


def build_v2_panel(
    horizons_years: tuple[int, ...] = DEFAULT_HORIZONS_YEARS,
    scopes: tuple[str, ...] = ("LC_FULL", "LC_TIER2", "LC_DEEP"),
    data_cutoff: Optional[pd.Timestamp] = None,
    oos_split_by_scope: Optional[dict[str, pd.Timestamp]] = None,
) -> V2Panel:
    """Build the full v2.0 panel: 5 components, 3 composites, 12 candidate cells.

    Parameters
    ----------
    horizons_years : tuple[int, ...], default (1, 3, 5, 10)
        Horizons in years per sealed §3.1.
    scopes : tuple[str, ...], default ("LC_FULL", "LC_TIER2", "LC_DEEP")
    data_cutoff : pd.Timestamp, optional
        Latest forecast-origin date to consider; default = latest composite
        observation across all 3 scopes.
    oos_split_by_scope : dict[str, pd.Timestamp], optional
        Per-scope OOS split date; default = v1.0 inheritance per sealed §10.1.

    Returns
    -------
    V2Panel
    """
    if oos_split_by_scope is None:
        oos_split_by_scope = DEFAULT_OOS_SPLIT

    components = build_all_components()
    composites = build_all_composites(components)
    fr_by_horizon = build_spliced_forward_returns(horizons_years=horizons_years)

    if data_cutoff is None:
        latest_dates = [s.dropna().index.max() for s in composites.values() if s.dropna().size > 0]
        data_cutoff = pd.Timestamp(max(latest_dates)) if latest_dates else pd.Timestamp.now()
    data_cutoff = pd.Timestamp(data_cutoff)

    cells: dict[tuple[str, int], PanelCell] = {}
    for scope in scopes:
        composite = composites[scope]
        scope_oos_split = pd.Timestamp(oos_split_by_scope.get(scope, DEFAULT_OOS_SPLIT[scope]))
        for h_y in horizons_years:
            h_m = HORIZONS_MONTHS[h_y]
            fr = fr_by_horizon.get(h_y)
            if fr is None:
                continue

            # Align on inner-join, drop NaN. Restrict to dates <= data_cutoff.
            aligned = pd.concat(
                [composite.rename("composite"), fr.rename("fr")],
                axis=1, join="inner",
            ).dropna()
            aligned = aligned[aligned.index <= data_cutoff]

            n_obs_total = int(aligned.shape[0])
            in_sample = aligned[aligned.index <= scope_oos_split]
            oos = aligned[aligned.index > scope_oos_split]
            n_obs_insample = int(in_sample.shape[0])
            n_obs_oos = int(oos.shape[0])

            # PIT feature_vintage_max for the cell: the latest forecast-origin
            # date in the cell. Under strict-shift PIT z-score, the underlying
            # data used at row t is observation-dated < t — so this date is an
            # upper bound on the underlying observation dates used.
            fvm: Optional[pd.Timestamp] = None
            if aligned.shape[0] > 0:
                fvm = pd.Timestamp(aligned.index.max())

            cells[(scope, h_y)] = PanelCell(
                composite=scope,
                horizon_months=h_m,
                horizon_years=h_y,
                composite_series=aligned["composite"],
                forward_return_series=aligned["fr"],
                n_obs_total=n_obs_total,
                n_obs_insample=n_obs_insample,
                n_obs_oos=n_obs_oos,
                feature_vintage_max=fvm,
                oos_split_date=scope_oos_split,
            )

    meta = {
        "data_cutoff": str(data_cutoff.date()),
        "forecast_origin_grid": "monthly_end_of_month",
        "feature_vintage_basis": "observation_date_approximation",
        "feature_vintage_basis_note": (
            "v2.0 approximates vintage by observation date per sealed §3.2.2 + "
            "PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md §2 (Option B3)."
        ),
        "horizons_years": list(horizons_years),
        "scopes": list(scopes),
        "oos_split_by_scope": {k: str(v.date()) for k, v in oos_split_by_scope.items()},
        "pit_min_window_monthly": PIT_MIN_WINDOW_MONTHLY,
        "z5_post_splice_warmup_relaxed_to_24mo": True,
        "icedxy_pre2006_status": "not_available",
        "rrpontsyd_pre2013_treatment": "zero_fill_strict_lt_2013_09_23",
    }
    return V2Panel(
        components=components,
        composites=composites,
        forward_returns=fr_by_horizon,
        cells=cells,
        meta=meta,
    )
