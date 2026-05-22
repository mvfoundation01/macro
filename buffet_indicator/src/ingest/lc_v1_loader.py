"""LC v1.0 ingestion — Master-of-Data-History (MoDH) builders for the
11 raw series required by the Liquidity Composite (spec §1.1).

References
----------
- spec_v11_3__liquidity_composite.md §1.1 — per-series data ranges
- specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) — sealed components
- specs/RECON_lc_v1_2026-05-22.md §2 — data sources required

Public API
----------
- LC_V1_FRED_CATALOG: dict mapping LC series id → FRED spec.
- LC_V1_ICEDXY_SPEC: dict describing the ICE DXY (Stooq) source.
- build_lc_fred_master: fetch a single FRED series and persist as master parquet.
- build_lc_icedxy_master: fetch ICE DXY narrow basket from Stooq, persist as master.
- build_all_lc_v1_masters: orchestrator that builds all 12 LC v1 masters.

Persistence
-----------
Each master goes to ``data/master/<lc_id>.parquet`` via
:func:`src.ingest.master_archive._update_master_atomically`, which records:
- ``value``: the observation
- ``source``: a stable label identifying the source ("fred:<SERIES_ID>" or "stooq:dx.f")
- ``vintage``: retrieval timestamp (UTC). For LC v1 backtest correctness, ALFRED
  vintages are layered on top in sub-stage A2 via
  :func:`src.ingest.fred_alfred_loader.build_lc_alfred_vintages`.
- ``transform``: "none" for raw fetches; later sub-stages may add splice labels.

No look-ahead bias is possible at A1 — these are LATEST-vintage descriptive
fetches. Look-ahead-safe vintages are built separately in A2.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
import requests

from src.config import RAW_CACHE
from src.ingest._base import (
    DataValidationError,
    NetworkError,
    get_logger,
    retryable,
    utcnow,
)
from src.ingest.fred_loader import load_fred_series
from src.ingest.master_archive import (
    MasterSeries,
    _update_master_atomically,
)

logger = get_logger("buffett.ingest.lc_v1")


# ---------------------------------------------------------------------------
# Catalog — frozen per pre-reg a8635ef + spec §1.1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FredSpec:
    """Spec for one FRED series consumed by LC v1.0.

    Attributes
    ----------
    fred_id : str
        FRED series id (e.g., "WALCL").
    frequency : str
        Native FRED frequency ("D" daily, "W" weekly, "M" monthly).
    units : str
        Human-readable units (for documentation; NOT used for parsing).
    earliest_expected : str
        ISO date of the earliest observation expected per spec §1.1.
        Used as a sanity-check upper bound after retrieval.
    role : str
        Short description of the component this series feeds.
    discontinued_at : str | None
        ISO date if the FRED series was discontinued (e.g., TEDRATE 2022-01-31).
    """
    fred_id: str
    frequency: Literal["D", "W", "M", "Q", "A"]
    units: str
    earliest_expected: str
    role: str
    discontinued_at: str | None = None


# Per pre-reg a8635ef §1.1 + spec_v11_3__liquidity_composite.md §1.1.
# DO NOT MODIFY these mappings without an amendment spec (per spec §0.2).
LC_V1_FRED_CATALOG: dict[str, FredSpec] = {
    "walcl": FredSpec(
        fred_id="WALCL", frequency="W", units="USD millions",
        earliest_expected="2002-12-18",
        role="z1 NetFed numerator (Fed balance sheet)",
    ),
    "wdtgal": FredSpec(
        fred_id="WDTGAL", frequency="W", units="USD millions",
        earliest_expected="2002-12-18",
        role="z1 NetFed: Treasury General Account (Wed level)",
    ),
    "rrpontsyd": FredSpec(
        fred_id="RRPONTSYD", frequency="D", units="USD billions",
        earliest_expected="2003-02-07",
        role="z1 NetFed: reverse-repo facility (zero-fill pre-2013-09-23)",
    ),
    "m2_sl": FredSpec(
        fred_id="M2SL", frequency="M", units="USD billions",
        earliest_expected="1959-01-01",
        role="z2 M2 growth YoY",
    ),
    "busloans": FredSpec(
        fred_id="BUSLOANS", frequency="M", units="USD billions",
        earliest_expected="1947-01-01",
        role="z3 BankLend pre-1973 (C&I loans, spliced to TOTLL at 1973-01)",
    ),
    "totll": FredSpec(
        fred_id="TOTLL", frequency="W", units="USD billions",
        earliest_expected="1973-01-03",
        role="z3 BankLend 1973+ (total loans & leases)",
    ),
    "dtwexbgs": FredSpec(
        fred_id="DTWEXBGS", frequency="D", units="Index",
        earliest_expected="2006-01-04",
        role="z4 DXY⁻¹: broad TWI 2006+ (spliced from ICE DXY at 2006-01)",
    ),
    "tedrate": FredSpec(
        fred_id="TEDRATE", frequency="D", units="Percent",
        earliest_expected="1986-01-02",
        role="z5 Funding stress pre-2022 (LIBOR − T-bill, discontinued 2022-01-31)",
        discontinued_at="2022-01-31",
    ),
    "sofr": FredSpec(
        fred_id="SOFR", frequency="D", units="Percent",
        earliest_expected="2018-04-03",
        role="z5 Funding 2018+ (Secured Overnight Financing Rate)",
    ),
    "ioer": FredSpec(
        fred_id="IOER", frequency="D", units="Percent",
        earliest_expected="2008-10-09",
        role="z5 Funding: Interest On Excess Reserves (discontinued 2021-07-28)",
        discontinued_at="2021-07-28",
    ),
    "iorb": FredSpec(
        fred_id="IORB", frequency="D", units="Percent",
        earliest_expected="2021-07-29",
        role="z5 Funding 2021+ (Interest On Reserve Balances)",
    ),
}


@dataclass(frozen=True)
class IceDxySpec:
    """Spec for ICE DXY (narrow 6-currency dollar index) from Stooq."""
    stooq_symbol: str
    frequency: Literal["D"]
    units: str
    earliest_expected: str
    role: str


LC_V1_ICEDXY_SPEC: IceDxySpec = IceDxySpec(
    stooq_symbol="dx.f",
    frequency="D",
    units="Index",
    earliest_expected="1971-01-04",
    role="z4 DXY⁻¹: ICE narrow basket pre-2006 (spliced to DTWEXBGS at 2006-01)",
)


# ---------------------------------------------------------------------------
# FRED builder
# ---------------------------------------------------------------------------


def _to_master_frame(
    series: pd.Series,
    source_label: str,
    vintage: pd.Timestamp,
    transform: str = "none",
) -> pd.DataFrame:
    """Wrap a value series in the master-archive schema (per master_archive §8.5)."""
    df = pd.DataFrame(
        {
            "value": series.astype("float64").values,
            "source": pd.array([source_label] * len(series), dtype="string"),
            "vintage": pd.to_datetime([vintage] * len(series)),
            "transform": pd.array([transform] * len(series), dtype="string"),
        },
        index=pd.DatetimeIndex(series.index, name="date"),
    )
    return df


def build_lc_fred_master(
    lc_id: str,
    api_key: str,
    *,
    cache_dir: Path = RAW_CACHE,
    cache_ttl_hours: int = 24,
    force_refresh: bool = False,
) -> MasterSeries:
    """Build one LC v1 FRED master parquet at ``data/master/<lc_id>.parquet``.

    Parameters
    ----------
    lc_id : str
        Key in :data:`LC_V1_FRED_CATALOG` (e.g., "walcl").
    api_key : str
        FRED API key (32-char hex). See :func:`src.ingest.fred_loader.load_fred_series`.
    cache_dir : Path
        Raw cache directory for the underlying FRED fetch.
    cache_ttl_hours : int
        Cache TTL for the raw FRED fetch.
    force_refresh : bool
        If True, bypass the raw cache.

    Returns
    -------
    MasterSeries
        Read back from the persisted master parquet.

    References
    ----------
    [1] spec_v11_3__liquidity_composite.md §1.1
    [2] specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md §1.1
    [3] Master spec §2.4 (MoDH master archive)
    """
    if lc_id not in LC_V1_FRED_CATALOG:
        raise KeyError(
            f"Unknown LC v1 series id '{lc_id}'. "
            f"Valid ids: {sorted(LC_V1_FRED_CATALOG.keys())}"
        )
    spec = LC_V1_FRED_CATALOG[lc_id]
    fetched = load_fred_series(
        spec.fred_id,
        api_key,
        cache_dir=cache_dir,
        cache_ttl_hours=cache_ttl_hours,
        observation_start=spec.earliest_expected,
        force_refresh=force_refresh,
    )
    if fetched.data.dropna().empty:
        raise DataValidationError(
            f"FRED returned no observations for {spec.fred_id} (lc_id={lc_id})"
        )
    first_obs = fetched.data.dropna().index.min()
    expected = pd.Timestamp(spec.earliest_expected)
    # FRED occasionally backfills 1-2 weeks earlier than spec records; allow 30d slack.
    if first_obs < expected - pd.Timedelta(days=30):
        logger.warning(
            "lc_v1.%s: first obs %s is earlier than expected %s (>30d slack)",
            lc_id, first_obs.date(), expected.date(),
        )
    elif first_obs > expected + pd.Timedelta(days=30):
        logger.warning(
            "lc_v1.%s: first obs %s is later than expected %s (>30d slack)",
            lc_id, first_obs.date(), expected.date(),
        )
    candidate = _to_master_frame(
        fetched.data,
        source_label=f"fred:{spec.fred_id}",
        vintage=pd.Timestamp(fetched.retrieval_timestamp),
        transform="none",
    )
    merged = _update_master_atomically(lc_id, candidate)
    series = merged["value"].astype("float64")
    series.name = lc_id
    return MasterSeries(
        series_id=lc_id,
        data=series,
        sources_used=(f"fred:{spec.fred_id}",),
        earliest=merged.index.min(),
        latest=merged.index.max(),
        n_observations=int(len(merged)),
    )


# ---------------------------------------------------------------------------
# Stooq ICE DXY builder
# ---------------------------------------------------------------------------


STOOQ_CSV_URL = "https://stooq.com/q/d/l/"


@retryable(max_attempts=3)
def _fetch_stooq_csv(symbol: str, *, timeout: int = 30) -> bytes:
    """Fetch a Stooq daily CSV for ``symbol``. Returns raw bytes."""
    params = {"s": symbol, "i": "d"}
    try:
        resp = requests.get(STOOQ_CSV_URL, params=params, timeout=timeout)
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise NetworkError(
            f"Stooq network error: {exc}",
            user_message="Could not reach Stooq; check your connection.",
        ) from exc
    if resp.status_code != 200:
        raise NetworkError(
            f"Stooq returned HTTP {resp.status_code} for {symbol}",
            user_message=f"Stooq is unreachable or rate-limited (HTTP {resp.status_code}).",
        )
    body: bytes = resp.content
    if not body or body.lower().startswith(b"<!doctype") or b"No data" in body[:200]:
        raise DataValidationError(
            f"Stooq returned no data for {symbol} (first 200 bytes: {body[:200]!r})",
        )
    return body


def _parse_stooq_csv(body: bytes) -> pd.Series:
    """Parse Stooq daily CSV bytes into a Close price series indexed by date."""
    df = pd.read_csv(io.BytesIO(body))
    expected_cols = {"Date", "Close"}
    if not expected_cols.issubset(df.columns):
        raise DataValidationError(
            f"Stooq CSV missing required columns; got {list(df.columns)}"
        )
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    close = df["Close"].astype("float64").dropna()
    close.index = pd.DatetimeIndex(close.index).normalize()
    close.name = "ice_dxy"
    return close


def build_lc_icedxy_master(
    *,
    stooq_body: bytes | None = None,
) -> MasterSeries:
    """Build the ICE DXY (narrow 6-currency basket) master parquet.

    Parameters
    ----------
    stooq_body : bytes or None
        For tests: pre-fetched Stooq CSV bytes. If None, fetched live.

    Returns
    -------
    MasterSeries

    Notes
    -----
    The spec §1.1 marks ICE DXY as Tier 3/4 (Stooq, intermittent). On Stooq
    failure, the caller should surface as a BLOCKER per spec §17 mitigation
    rather than silently degrade to a different basket.

    References
    ----------
    [1] spec_v11_3__liquidity_composite.md §1.1 row s4b
    [2] specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md §1.1 row z4
    """
    spec = LC_V1_ICEDXY_SPEC
    body = stooq_body if stooq_body is not None else _fetch_stooq_csv(spec.stooq_symbol)
    series = _parse_stooq_csv(body)
    if series.empty:
        raise DataValidationError("ICE DXY series is empty after parse")
    first_obs = series.index.min()
    expected = pd.Timestamp(spec.earliest_expected)
    if first_obs > expected + pd.Timedelta(days=365):
        logger.warning(
            "lc_v1.ice_dxy: first obs %s is more than 1 year after expected %s; "
            "Stooq endpoint may not be honoring full history",
            first_obs.date(), expected.date(),
        )
    candidate = _to_master_frame(
        series,
        source_label=f"stooq:{spec.stooq_symbol}",
        vintage=pd.Timestamp(utcnow()),
        transform="none",
    )
    merged = _update_master_atomically("ice_dxy", candidate)
    out = merged["value"].astype("float64")
    out.name = "ice_dxy"
    return MasterSeries(
        series_id="ice_dxy",
        data=out,
        sources_used=(f"stooq:{spec.stooq_symbol}",),
        earliest=merged.index.min(),
        latest=merged.index.max(),
        n_observations=int(len(merged)),
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build_all_lc_v1_masters(
    api_key: str,
    *,
    cache_dir: Path = RAW_CACHE,
    cache_ttl_hours: int = 24,
    force_refresh: bool = False,
    skip_icedxy: bool = False,
    stooq_body: bytes | None = None,
) -> dict[str, MasterSeries]:
    """Build all 12 LC v1 master parquets in one pass.

    Parameters
    ----------
    api_key : str
        FRED API key for the 11 FRED series.
    cache_dir, cache_ttl_hours, force_refresh
        Passed through to :func:`build_lc_fred_master`.
    skip_icedxy : bool
        If True, do not attempt ICE DXY (useful when Stooq is unreachable
        and the caller wants to keep the FRED masters fresh).
    stooq_body : bytes or None
        For tests: pre-fetched Stooq CSV bytes for the ICE DXY fetch.

    Returns
    -------
    dict
        Keys: lc_id (e.g., "walcl"). Values: :class:`MasterSeries`.

    References
    ----------
    [1] spec_v11_3__liquidity_composite.md §16 sub-stage A1
    [2] specs/RECON_lc_v1_2026-05-22.md §12 sub-stage A1 plan
    """
    out: dict[str, MasterSeries] = {}
    for lc_id in LC_V1_FRED_CATALOG:
        try:
            out[lc_id] = build_lc_fred_master(
                lc_id,
                api_key,
                cache_dir=cache_dir,
                cache_ttl_hours=cache_ttl_hours,
                force_refresh=force_refresh,
            )
        except Exception:
            logger.exception("lc_v1.%s build FAILED", lc_id)
            raise
    if not skip_icedxy:
        out["ice_dxy"] = build_lc_icedxy_master(stooq_body=stooq_body)
    return out


__all__ = [
    "FredSpec",
    "IceDxySpec",
    "LC_V1_FRED_CATALOG",
    "LC_V1_ICEDXY_SPEC",
    "build_lc_fred_master",
    "build_lc_icedxy_master",
    "build_all_lc_v1_masters",
]
