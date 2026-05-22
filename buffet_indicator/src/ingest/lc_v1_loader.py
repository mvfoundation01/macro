"""LC v1.0 ingestion — Master-of-Data-History (MoDH) builders for the
11 FRED + 1 ICE DXY series required by the Liquidity Composite (spec §1.1).

References
----------
- spec_v11_3__liquidity_composite.md §1.1 — per-series data ranges
- specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) — sealed components
- specs/RECON_lc_v1_2026-05-22.md §2 — data sources required
- Session 6 §2.0 — ICE DXY blocker resolution (Norgate primary + yfinance + cache).

Public API
----------
- LC_V1_FRED_CATALOG: dict mapping LC series id → FRED spec.
- LC_V1_ICEDXY_SPEC: legacy spec describing the (deprecated) Stooq ICE DXY source.
- build_lc_fred_master: fetch a single FRED series and persist as master parquet.
- build_lc_icedxy_master: build the model-ready spliced log(ICE DXY) series via
  Norgate (deep history primary) → yfinance (tail update) → local-parquet (cached)
  priority, then splice with DTWEXBGS at 2006-01-04 per pre-reg a8635ef §1.3.
- build_lc_icedxy_stooq_master_legacy: DEPRECATED Stooq path retained for audit.
- build_all_lc_v1_masters: orchestrator that builds the 11 FRED master parquets.

ICE DXY source policy (Session 6 §2.0)
--------------------------------------
The ICE DXY deep history (1971+) lives in ``data/master/icedxy_close.parquet``,
populated ONCE by ``scripts/bootstrap_icedxy_from_norgate.py`` while a Norgate
Diamond subscription is active. After that one-time bootstrap, the subscription
can be canceled and the cached parquet remains the canonical source.
``build_lc_icedxy_master`` reads the cache by default; yfinance is an optional
runtime tail-update for dates post-1985. See ``data/master/_source_policy.json``
for the formal priority record.

Persistence
-----------
FRED masters go to ``data/master/<lc_id>.parquet`` via
:func:`src.ingest.master_archive._update_master_atomically`, which records:
- ``value``: the observation
- ``source``: a stable label identifying the source ("fred:<SERIES_ID>")
- ``vintage``: retrieval timestamp (UTC). For LC v1 backtest correctness, ALFRED
  vintages are layered on top in sub-stage A2 via
  :func:`src.ingest.fred_alfred_loader.build_lc_alfred_vintages`.
- ``transform``: "none" for raw fetches; later sub-stages may add splice labels.

The ICE DXY cache (``icedxy_close.parquet``) uses the same MoDH schema; it is
written ONCE by the Norgate bootstrap script and read by ``build_lc_icedxy_master``.

No look-ahead bias is possible at A1 — these are LATEST-vintage descriptive
fetches. Look-ahead-safe vintages are built separately in A2.
"""
from __future__ import annotations

import io
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import requests

from src.config import MASTER_DIR, RAW_CACHE
from src.ingest._base import (
    DataValidationError,
    NetworkError,
    atomic_write_parquet,
    get_logger,
    retryable,
    utcnow,
)
from src.ingest.fred_loader import load_fred_series
from src.ingest.master_archive import (
    MASTER_COLUMNS,
    MasterSeries,
    _update_master_atomically,
)

# Gated imports — Norgate Diamond subscription is owner-only; yfinance is free.
# When these packages are not installed the module still loads, and only the
# live-fetch code paths (use_norgate_live=True / use_yfinance_live=True) error.
try:  # pragma: no cover - exercised in bootstrap env, not in test CI
    import norgatedata as _norgatedata  # type: ignore  # pragma: no cover
except ImportError:  # pragma: no cover
    _norgatedata = None  # pragma: no cover

try:  # pragma: no cover - yfinance is optional at runtime
    import yfinance as _yfinance  # type: ignore  # pragma: no cover
except ImportError:  # pragma: no cover
    _yfinance = None  # pragma: no cover

logger = get_logger("buffett.ingest.lc_v1")


# ---------------------------------------------------------------------------
# ICE DXY cache + splice constants (Session 6 §2.0; pre-reg a8635ef §1.3)
# ---------------------------------------------------------------------------

#: Filename for the cached ICE DXY deep-history master parquet under MASTER_DIR.
ICEDXY_CACHE_FILENAME = "icedxy_close.parquet"

#: ICE DXY ↔ DTWEXBGS splice date, sealed per pre-reg a8635ef §1.3.
ICEDXY_SPLICE_DATE = pd.Timestamp("2006-01-04")

#: Splice gates per pre-reg a8635ef §1.3 + master spec §2.4.5 Step 4.
ICEDXY_SPLICE_MIN_CORR = 0.85
ICEDXY_SPLICE_MAX_MEAN_ABS_Z_DIVERGENCE = 0.30

#: Overlap-window radius (months) around the splice date used to compute the
#: additive level constant c on the monthly-EOM grid.
ICEDXY_SPLICE_OVERLAP_MONTHS = 2

#: yfinance ticker for the ICE DXY (post-1985 only).
YFINANCE_DXY_TICKER = "DX-Y.NYB"

#: Default Norgate symbol; owner can override with --symbol in the bootstrap script.
NORGATE_DEFAULT_SYMBOL = "DXY"


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


def build_lc_icedxy_stooq_master_legacy(
    *,
    stooq_body: bytes | None = None,
) -> MasterSeries:
    """LEGACY: build the ICE DXY master parquet from Stooq daily prices.

    .. deprecated:: v11.3 (Session 6 §2.0)
        Stooq's free CSV endpoint for ``dx.f`` / ``^dxy`` returns empty/gated
        content as of 2026-05-22 (see ``specs/BLOCKED_v11_3_A1_icedxy_stooq.md``).
        The ICE DXY deep history is now sourced via Norgate Diamond (one-time
        bootstrap, see ``scripts/bootstrap_icedxy_from_norgate.py``) with yfinance
        as a Tier-4 runtime tail-update fallback. See ``data/master/_source_policy.json``.

        This function is retained behind an explicit opt-in flag for AUDIT REPLAY
        only — to be able to reproduce the Session 5 master state if Stooq ever
        starts honoring requests again.

    Parameters
    ----------
    stooq_body : bytes or None
        For tests: pre-fetched Stooq CSV bytes. If None, fetched live (will fail
        against the current Stooq endpoint).

    Returns
    -------
    MasterSeries

    References
    ----------
    [1] spec_v11_3__liquidity_composite.md §1.1 row s4b (pre-Session 6 abstract spec)
    [2] specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md §1.1 row z4 (vendor-agnostic)
    [3] Session 6 §2.0 — blocker resolution (Norgate + yfinance + cache).
    """
    warnings.warn(
        "build_lc_icedxy_stooq_master_legacy is deprecated; use "
        "scripts/bootstrap_icedxy_from_norgate.py to populate "
        f"data/master/{ICEDXY_CACHE_FILENAME} and then call build_lc_icedxy_master(). "
        "Retained for audit replay only.",
        DeprecationWarning,
        stacklevel=2,
    )
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
# ICE DXY Norgate / yfinance / cache loaders (Session 6 §2.0)
# ---------------------------------------------------------------------------


def _fetch_norgate_dxy_live(symbol: str = NORGATE_DEFAULT_SYMBOL) -> pd.Series:
    """Fetch daily close prices for ``symbol`` from Norgate Diamond.

    Only callable when the ``norgatedata`` package is installed (i.e., the
    Owner's bootstrap environment with an active Norgate Diamond subscription).
    The standard test environment has ``norgatedata`` absent and this function
    raises ``RuntimeError`` immediately.

    Returns
    -------
    pd.Series
        Daily close prices, indexed by date (DatetimeIndex, ascending).

    Raises
    ------
    RuntimeError
        If ``norgatedata`` is not installed.
    DataValidationError
        If the Norgate response is empty.
    """
    if _norgatedata is None:
        raise RuntimeError(
            "norgatedata package not installed; cannot fetch live Norgate DXY. "
            "Run `pip install norgatedata` (requires active Norgate Diamond subscription)."
        )
    # Below: only exercised in the Owner's bootstrap environment with the
    # ``norgatedata`` package installed AND an active Norgate Diamond
    # subscription. The test CI cannot install or call the API.
    raw = _norgatedata.price_timeseries(  # pragma: no cover
        symbol,
        start_date="1971-01-01",
        end_date=str(pd.Timestamp(utcnow()).date()),
        timeseriesformat="pandas-dataframe",
    )
    if raw is None or len(raw) == 0:  # pragma: no cover - depends on live API
        raise DataValidationError(
            f"Norgate returned no observations for symbol '{symbol}'"
        )
    close_col = "Close" if "Close" in raw.columns else raw.columns[-1]  # pragma: no cover
    series_out: pd.Series = raw[close_col].astype("float64").dropna()  # pragma: no cover
    series_out.index = pd.DatetimeIndex(series_out.index).normalize()  # pragma: no cover
    series_out.name = "icedxy_close"  # pragma: no cover
    return series_out  # pragma: no cover


def _fetch_yfinance_dxy_live(ticker: str = YFINANCE_DXY_TICKER) -> pd.Series:
    """Fetch daily close prices for ``ticker`` from yfinance.

    yfinance only honors the ICE DXY (``DX-Y.NYB``) back to 1985-01, so this
    source cannot satisfy LC_DEEP (1973+) or the pre-1985 portion of LC_TIER2.
    It is used as a runtime tail-update fallback when the local cache is stale
    or unavailable, never as a primary deep-history source.

    Returns
    -------
    pd.Series
        Daily close prices, indexed by date.

    Raises
    ------
    RuntimeError
        If ``yfinance`` is not installed.
    DataValidationError
        If the yfinance response is empty.
    """
    if _yfinance is None:
        raise RuntimeError(
            "yfinance package not installed; cannot fetch live yfinance DXY. "
            "Run `pip install yfinance`."
        )
    # Below: live-network code path, only exercised via the integration-tests
    # gate (INTEGRATION_TESTS=1) in ``test_TI3_real_yfinance_dxy_...``.
    raw = _yfinance.download(  # pragma: no cover
        ticker,
        start="1985-01-01",
        progress=False,
        auto_adjust=False,
    )
    if raw is None or len(raw) == 0:  # pragma: no cover - depends on live API
        raise DataValidationError(
            f"yfinance returned no observations for ticker '{ticker}'"
        )
    close_col = ("Close", ticker) if isinstance(raw.columns, pd.MultiIndex) else "Close"  # pragma: no cover
    series_out: pd.Series = raw[close_col].astype("float64").dropna()  # pragma: no cover
    series_out.index = pd.DatetimeIndex(series_out.index).normalize()  # pragma: no cover
    series_out.name = "icedxy_close"  # pragma: no cover
    return series_out  # pragma: no cover


def _read_icedxy_cache_parquet(cache_path: Path) -> pd.Series:
    """Read the cached ICE DXY deep-history parquet into a daily price Series."""
    df = pd.read_parquet(cache_path)
    if "value" not in df.columns:
        raise DataValidationError(
            f"ICE DXY cache at {cache_path} missing 'value' column; "
            f"got columns {list(df.columns)}. Re-run the Norgate bootstrap."
        )
    df.index = pd.DatetimeIndex(df.index)
    series: pd.Series = df["value"].astype("float64").dropna()
    series.name = "icedxy_close"
    return series.sort_index()


def _splice_log_dxy_with_dtwexbgs(
    log_dxy: pd.Series,
    log_dtwexbgs: pd.Series,
    *,
    splice_date: pd.Timestamp = ICEDXY_SPLICE_DATE,
    overlap_window_months: int = ICEDXY_SPLICE_OVERLAP_MONTHS,
    min_corr: float = ICEDXY_SPLICE_MIN_CORR,
    max_mean_abs_z_divergence: float = ICEDXY_SPLICE_MAX_MEAN_ABS_Z_DIVERGENCE,
) -> tuple[pd.Series, float]:
    """Splice monthly ``log_dtwexbgs`` onto monthly ``log_dxy`` via log-level additive c.

    Per pre-reg a8635ef §1.3 + master spec §2.4.5 Step 4:

    1. Compute c = mean(log_dxy_overlap) − mean(log_dtwexbgs_overlap) on the
       ±``overlap_window_months`` window around ``splice_date``.
    2. Shift DTWEXBGS by +c so its overlap mean matches ICE DXY's.
    3. Gate 1: corr(log_dxy, log_dtwexbgs) > ``min_corr`` on the overlap.
    4. Gate 2: mean |z(log_dxy) − z(log_dtwexbgs)| < ``max_mean_abs_z_divergence`` on overlap.
    5. Result: ICE DXY for dates < splice_date, shifted DTWEXBGS for dates ≥ splice_date.

    Returns
    -------
    (spliced_series, c) : (pd.Series, float)
        The continuous spliced log series and the additive level constant c.

    Raises
    ------
    ValueError
        If either gate fails (master spec §2.4.5 "Reject and raise"), refusing
        to splice through a regime break.

    Notes
    -----
    Sub-stage B (``src/transform/lc_v1_splices.py``) extracts this algorithm
    into a reusable splice function. Both call sites must remain bit-identical
    so the modeling layer's pre-reg invariants hold.
    """
    overlap_start = splice_date - pd.DateOffset(months=overlap_window_months)
    overlap_end = splice_date + pd.DateOffset(months=overlap_window_months)
    overlap_dxy = log_dxy.loc[overlap_start:overlap_end].dropna()
    overlap_dtw = log_dtwexbgs.loc[overlap_start:overlap_end].dropna()
    common = overlap_dxy.index.intersection(overlap_dtw.index)
    if len(common) < 2:
        raise ValueError(
            f"ICE DXY <-> DTWEXBGS splice at {splice_date.date()}: insufficient "
            f"overlap (n={len(common)} months) — need ≥2 to compute corr/z-divergence."
        )
    overlap_dxy = overlap_dxy.loc[common]
    overlap_dtw = overlap_dtw.loc[common]

    c = float(overlap_dxy.mean() - overlap_dtw.mean())

    # Precondition: both overlap series must have non-zero finite std for corr
    # and z-divergence to be meaningful.
    dxy_std = float(overlap_dxy.std(ddof=1))
    dtw_std = float(overlap_dtw.std(ddof=1))
    if dxy_std == 0 or dtw_std == 0 or not np.isfinite(dxy_std) or not np.isfinite(dtw_std):
        raise ValueError(
            f"ICE DXY <-> DTWEXBGS splice GATE FAIL: zero/NaN std in overlap "
            f"(dxy_std={dxy_std}, dtw_std={dtw_std})."
        )

    corr = float(overlap_dxy.corr(overlap_dtw))
    if not np.isfinite(corr) or corr <= min_corr:
        raise ValueError(
            f"ICE DXY <-> DTWEXBGS splice GATE FAIL: corr={corr:.4f} <= {min_corr} "
            f"(pre-reg a8635ef §1.3 min_corr). Refusing to splice through a regime break."
        )
    z_dxy = (overlap_dxy - overlap_dxy.mean()) / dxy_std
    z_dtw = (overlap_dtw - overlap_dtw.mean()) / dtw_std
    mean_abs_z_div = float((z_dxy - z_dtw).abs().mean())
    if mean_abs_z_div >= max_mean_abs_z_divergence:
        raise ValueError(
            f"ICE DXY <-> DTWEXBGS splice GATE FAIL: mean|z-div|={mean_abs_z_div:.4f} "
            f">= {max_mean_abs_z_divergence} (pre-reg a8635ef §1.3 max divergence). "
            f"Refusing to splice through a regime break."
        )

    log_dtw_shifted = log_dtwexbgs + c
    pre = log_dxy.loc[log_dxy.index < splice_date]
    post = log_dtw_shifted.loc[log_dtw_shifted.index >= splice_date]
    result = pd.concat([pre, post]).sort_index()
    result = result[~result.index.duplicated(keep="first")]
    result.name = "ice_dxy_spliced_log"
    return result, c


def build_lc_icedxy_master(
    *,
    norgate_data: pd.Series | None = None,
    yfinance_data: pd.Series | None = None,
    use_norgate_live: bool = False,
    use_yfinance_live: bool = False,
    splice_dtwexbgs: bool = True,
    cache_parquet_path: Path | None = None,
    dtwexbgs_data: pd.Series | None = None,
) -> pd.Series:
    """Construct the model-ready spliced log(ICE DXY) series.

    Source priority (highest first), per ``data/master/_source_policy.json``:

      1. Norgate Diamond (Tier 3, 1971+, via ``norgatedata`` package).
         Only consulted when ``norgate_data`` is injected (tests) or
         ``use_norgate_live=True`` (bootstrap script).
      2. yfinance ``DX-Y.NYB`` (Tier 4, 1985+).
         Only consulted when ``yfinance_data`` is injected (tests) or
         ``use_yfinance_live=True`` (runtime tail-update).
      3. Local MoDH parquet at ``data/master/icedxy_close.parquet``.
         Default runtime source — cached deep history from prior Norgate
         bootstrap; survives subscription cancellation.

    After source selection the function resamples to monthly EOM,
    log-transforms, and (if ``splice_dtwexbgs=True``) splices with DTWEXBGS at
    ``ICEDXY_SPLICE_DATE`` (2006-01-04) via log-level additive c, applying
    gates per pre-reg a8635ef §1.3 (``corr > 0.85``, ``mean |z-div| < 0.30``).

    Parameters
    ----------
    norgate_data, yfinance_data : pd.Series or None
        Pre-fetched daily price series — used by tests for dependency injection.
        Priority chain: Norgate beats yfinance beats local cache.
    use_norgate_live : bool
        Only set True by ``scripts/bootstrap_icedxy_from_norgate.py``.
    use_yfinance_live : bool
        Set True for runtime tail-update fetches from yfinance.
    splice_dtwexbgs : bool
        Apply the ICE DXY → DTWEXBGS log-level-additive splice at 2006-01-04.
        Default True for model construction; False to inspect raw log(DXY).
    cache_parquet_path : Path or None
        Override the default cache location (``MASTER_DIR / ICEDXY_CACHE_FILENAME``).
        Used by tests; production callers should leave None.
    dtwexbgs_data : pd.Series or None
        Daily DTWEXBGS price series for the splice. If None and ``splice_dtwexbgs``
        is True, the function loads it via ``load_master('dtwexbgs')``.

    Returns
    -------
    pd.Series
        Monthly-end-of-month log(DXY) series, indexed by date. If
        ``splice_dtwexbgs=True``, dates ≥ 2006-01-04 use shifted DTWEXBGS;
        dates < 2006-01-04 use the source-selected ICE DXY.

    Raises
    ------
    RuntimeError
        If no source yields data (Norgate disabled, yfinance disabled, cache missing).
    ValueError
        If a splice gate fails (per pre-reg a8635ef §1.3).

    References
    ----------
    [1] specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.3 — splice spec.
    [2] specs/RECON_lc_v1_2026-05-22.md §2 — data sources required.
    [3] Session 6 prompt §2.0 — blocker resolution.
    [4] data/master/_source_policy.json — priority record.
    """
    raw_daily, source_label = _select_icedxy_source(
        norgate_data=norgate_data,
        yfinance_data=yfinance_data,
        use_norgate_live=use_norgate_live,
        use_yfinance_live=use_yfinance_live,
        cache_parquet_path=cache_parquet_path,
    )
    logger.info("build_lc_icedxy_master: source=%s n=%d", source_label, len(raw_daily))

    monthly = raw_daily.resample("ME").last().dropna()
    if monthly.empty:
        raise DataValidationError(
            f"build_lc_icedxy_master: monthly EOM resample yielded empty series "
            f"(source={source_label})."
        )
    log_dxy: pd.Series = np.log(monthly)
    log_dxy.name = "log_ice_dxy_monthly"

    if not splice_dtwexbgs:
        return log_dxy

    dtw_series = _resolve_dtwexbgs_for_splice(dtwexbgs_data)
    dtw_monthly = dtw_series.resample("ME").last().dropna()
    if dtw_monthly.empty:
        raise DataValidationError(
            "build_lc_icedxy_master: DTWEXBGS resample yielded empty series."
        )
    log_dtwexbgs = np.log(dtw_monthly)

    spliced, c_const = _splice_log_dxy_with_dtwexbgs(log_dxy, log_dtwexbgs)
    logger.info(
        "build_lc_icedxy_master: spliced ICE DXY <-> DTWEXBGS at %s with c=%+.6f",
        ICEDXY_SPLICE_DATE.date(), c_const,
    )
    # Attach splice metadata to the Series.attrs per master spec §2.4.3 — this is
    # the in-memory analogue of the MoDH ``transform`` column for the spliced output.
    spliced.attrs["transform"] = (
        f"splice_additive:+{c_const:.6f}@{ICEDXY_SPLICE_DATE.date()}"
    )
    spliced.attrs["splice_c"] = c_const
    spliced.attrs["splice_date"] = str(ICEDXY_SPLICE_DATE.date())
    spliced.attrs["source"] = source_label
    return spliced


def _select_icedxy_source(
    *,
    norgate_data: pd.Series | None,
    yfinance_data: pd.Series | None,
    use_norgate_live: bool,
    use_yfinance_live: bool,
    cache_parquet_path: Path | None,
) -> tuple[pd.Series, str]:
    """Resolve the daily ICE DXY price series via the 3-tier priority chain.

    Returns the daily price Series + a string label for the chosen source.
    """
    if norgate_data is not None:
        return norgate_data.sort_index(), "norgate_injected"
    if use_norgate_live:
        return _fetch_norgate_dxy_live(), "norgate_live"
    if yfinance_data is not None:
        return yfinance_data.sort_index(), "yfinance_injected"
    if use_yfinance_live:
        return _fetch_yfinance_dxy_live(), "yfinance_live"
    cache_path = cache_parquet_path or (MASTER_DIR / ICEDXY_CACHE_FILENAME)
    if not cache_path.exists():
        raise RuntimeError(
            f"ICE DXY cache parquet missing at {cache_path}. Run "
            f"`python scripts/bootstrap_icedxy_from_norgate.py` while Norgate "
            f"Diamond subscription is active to populate it. See "
            f"`data/master/_source_policy.json` for the source priority record."
        )
    return _read_icedxy_cache_parquet(cache_path), f"cache:{cache_path.name}"


def _resolve_dtwexbgs_for_splice(dtwexbgs_data: pd.Series | None) -> pd.Series:
    """Resolve the DTWEXBGS daily price series for the splice.

    Used by tests for dependency injection; production calls load via
    :func:`src.ingest.master_archive.load_master` to honor any vintage hooks.
    """
    if dtwexbgs_data is not None:
        return dtwexbgs_data.sort_index()
    # Lazy import to avoid circular import (master_archive depends on this module
    # only at runtime via vintage shim).
    from src.ingest.master_archive import load_master
    ms = load_master("dtwexbgs")
    s: pd.Series = ms.data.astype("float64").dropna()
    s.name = "dtwexbgs"
    return s


def write_icedxy_cache_parquet(
    series: pd.Series,
    *,
    cache_path: Path | None = None,
    source_label: str = "norgate_diamond",
    transform_label: str = "none",
) -> Path:
    """Write the daily ICE DXY cache parquet using the MoDH schema.

    Used by ``scripts/bootstrap_icedxy_from_norgate.py``. The file is written
    atomically via ``.tmp`` rename per master spec §2.4.4 Step 6.

    Parameters
    ----------
    series : pd.Series
        Daily close prices indexed by date.
    cache_path : Path or None
        Override the default cache path (``MASTER_DIR / ICEDXY_CACHE_FILENAME``).
    source_label : str
        Value for the ``source`` column. Default ``"norgate_diamond"``.
    transform_label : str
        Value for the ``transform`` column. Default ``"none"`` — splicing
        happens in :func:`build_lc_icedxy_master`, not at MoDH-write time.

    Returns
    -------
    Path
        The on-disk path of the written parquet.
    """
    path = cache_path or (MASTER_DIR / ICEDXY_CACHE_FILENAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    if series.empty:
        raise DataValidationError("write_icedxy_cache_parquet: input series is empty.")
    vintage = pd.Timestamp(utcnow())
    df = pd.DataFrame(
        {
            "value": series.astype("float64").values,
            "source": pd.array([source_label] * len(series), dtype="string"),
            "vintage": pd.to_datetime([vintage] * len(series)),
            "transform": pd.array([transform_label] * len(series), dtype="string"),
        },
        index=pd.DatetimeIndex(series.index, name="date"),
    )
    df = df[MASTER_COLUMNS]
    atomic_write_parquet(path, df)
    return path


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build_all_lc_v1_masters(
    api_key: str,
    *,
    cache_dir: Path = RAW_CACHE,
    cache_ttl_hours: int = 24,
    force_refresh: bool = False,
    skip_icedxy: bool = True,
    use_stooq_legacy: bool = False,
    stooq_body: bytes | None = None,
) -> dict[str, MasterSeries]:
    """Build the 11 LC v1 FRED master parquets in one pass.

    The ICE DXY master is NOT built by this orchestrator any more — per Session
    6 §2.0 it is populated ONCE by ``scripts/bootstrap_icedxy_from_norgate.py``
    while a Norgate Diamond subscription is active. The orchestrator only
    consults the legacy Stooq path when ``use_stooq_legacy=True`` is set
    explicitly (audit-replay only).

    Parameters
    ----------
    api_key : str
        FRED API key for the 11 FRED series.
    cache_dir, cache_ttl_hours, force_refresh
        Passed through to :func:`build_lc_fred_master`.
    skip_icedxy : bool
        If True (default — flipped from Session 5), do not attempt any ICE DXY
        build here. The deep-history cache is the responsibility of the
        Norgate bootstrap script.
    use_stooq_legacy : bool
        Audit-replay flag: when False (default) and ``skip_icedxy`` is False,
        the orchestrator logs and skips ICE DXY (the bootstrap script owns it).
        Set True to invoke :func:`build_lc_icedxy_stooq_master_legacy` for
        replaying the pre-Session-6 master-parquet state.
    stooq_body : bytes or None
        Pre-fetched Stooq CSV bytes; only honored when
        ``use_stooq_legacy=True``.

    Returns
    -------
    dict
        Keys: lc_id (e.g., ``"walcl"``). Values: :class:`MasterSeries`.

    References
    ----------
    [1] spec_v11_3__liquidity_composite.md §16 sub-stage A1
    [2] specs/RECON_lc_v1_2026-05-22.md §12 sub-stage A1 plan
    [3] Session 6 §2.0 — ICE DXY blocker resolution.
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
        if use_stooq_legacy:
            out["ice_dxy"] = build_lc_icedxy_stooq_master_legacy(stooq_body=stooq_body)
        else:
            logger.info(
                "build_all_lc_v1_masters: skip_icedxy=False but use_stooq_legacy=False; "
                "ICE DXY master parquet is owned by scripts/bootstrap_icedxy_from_norgate.py "
                "(Session 6 §2.0). Skipping ICE DXY in the orchestrator."
            )
    return out


__all__ = [
    "FredSpec",
    "IceDxySpec",
    "LC_V1_FRED_CATALOG",
    "LC_V1_ICEDXY_SPEC",
    "ICEDXY_CACHE_FILENAME",
    "ICEDXY_SPLICE_DATE",
    "ICEDXY_SPLICE_MIN_CORR",
    "ICEDXY_SPLICE_MAX_MEAN_ABS_Z_DIVERGENCE",
    "YFINANCE_DXY_TICKER",
    "NORGATE_DEFAULT_SYMBOL",
    "build_lc_fred_master",
    "build_lc_icedxy_master",
    "build_lc_icedxy_stooq_master_legacy",
    "build_all_lc_v1_masters",
    "write_icedxy_cache_parquet",
]
