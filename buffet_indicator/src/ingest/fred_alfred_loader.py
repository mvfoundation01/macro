"""ALFRED vintage loader for LC v1.0 backtest (sub-stage A2).

The Liquidity Composite v1.0 spec (§1.2) MANDATES real-time vintages for the
5 revisable series — M2SL, BUSLOANS, TOTLL, WALCL, WDTGAL — so the predictive
backtest at decision date *t* uses only data that was actually known on date *t*,
not later-revised values.

This module provides:

1. :func:`fetch_alfred_all_releases` — pull the full ALFRED vintage history
   for one FRED series in a single API call (via ``fredapi``).
2. :func:`store_vintage_snapshots` — break the vintage long-frame into
   per-vintage parquet snapshots under ``data/master/_vintages/``.
3. :func:`build_lc_alfred_vintages` — orchestrator: fetch + store for the 5
   spec-mandated series.

Vintage storage format (per spec §1.2 + master spec §2.4.7):

    data/master/_vintages/<series_id>__YYYYMMDD.parquet

where ``YYYYMMDD`` is the ALFRED `realtime_start` date for that vintage.
Each parquet has the standard master schema (``value``, ``source``, ``vintage``,
``transform``) restricted to the observations as-known on that vintage date.

The ``vintage='YYYYMMDD'`` parameter of :func:`src.ingest.master_archive.load_master`
(extended in this same sub-stage) reads from these files for look-ahead-safe
backtests.

References
----------
- spec_v11_3__liquidity_composite.md §1.2 — ALFRED vintage requirements
- master spec §2.4.7 — vintage storage convention
- specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md §1.4 — PIT z-score requires vintages
- specs/RECON_lc_v1_2026-05-22.md §9 open question 2 (load_master(vintage=) extension)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.ingest._base import (
    DataValidationError,
    atomic_write_parquet,
    get_logger,
)
from src.ingest.master_archive import MASTER_COLUMNS, MASTER_DIR

logger = get_logger("buffett.ingest.fred_alfred")


# ---------------------------------------------------------------------------
# Spec-mandated vintage targets (sealed per pre-reg a8635ef §1.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AlfredTarget:
    """One series whose ALFRED vintages must be backfilled."""
    lc_id: str
    fred_id: str
    vintage_start: str
    reason: str


LC_V1_ALFRED_TARGETS: tuple[AlfredTarget, ...] = (
    AlfredTarget(
        lc_id="m2_sl", fred_id="M2SL", vintage_start="1980-01-01",
        reason="Frequent M2 revisions including May 2020 redefinition",
    ),
    AlfredTarget(
        lc_id="busloans", fred_id="BUSLOANS", vintage_start="1980-01-01",
        reason="H.8 revision 2010-Q1",
    ),
    AlfredTarget(
        lc_id="totll", fred_id="TOTLL", vintage_start="1980-01-01",
        reason="H.8 revision 2010-Q1",
    ),
    AlfredTarget(
        lc_id="walcl", fred_id="WALCL", vintage_start="2002-12-18",
        reason="Minor weekly revisions",
    ),
    AlfredTarget(
        lc_id="wdtgal", fred_id="WDTGAL", vintage_start="2002-12-18",
        reason="Minor weekly revisions",
    ),
)


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------


def fetch_alfred_all_releases(
    fred_id: str,
    api_key: str,
    *,
    fred_client_factory: object | None = None,
) -> pd.DataFrame:
    """Pull the full ALFRED vintage history for one FRED series.

    Parameters
    ----------
    fred_id : str
        FRED series id, e.g., "M2SL".
    api_key : str
        FRED API key (32-char hex). ALFRED uses the same key as FRED.
    fred_client_factory : callable or None
        For tests: zero-arg callable returning an object with a
        ``get_series_all_releases(series_id)`` method. If None,
        instantiates ``fredapi.Fred(api_key=api_key)``.

    Returns
    -------
    pd.DataFrame
        Long-format DataFrame with columns ``date``, ``realtime_start`` (vintage
        date), and ``value``. Sorted by (realtime_start, date).

    Raises
    ------
    DataValidationError
        If the response is empty or missing expected columns.

    References
    ----------
    [1] spec_v11_3__liquidity_composite.md §1.2
    [2] fredapi docs: https://github.com/mortada/fredapi#get-series-as-of-current
    """
    if fred_client_factory is None:
        from fredapi import Fred
        client = Fred(api_key=api_key)
    else:
        client = fred_client_factory()  # type: ignore[operator]
    raw = client.get_series_all_releases(fred_id)  # type: ignore[attr-defined]
    if raw is None or len(raw) == 0:
        raise DataValidationError(
            f"ALFRED returned no observations for {fred_id}"
        )
    df = pd.DataFrame(raw).copy()
    expected_cols = {"date", "realtime_start", "value"}
    if not expected_cols.issubset(df.columns):
        raise DataValidationError(
            f"ALFRED response missing required columns; got {list(df.columns)}, "
            f"expected at least {sorted(expected_cols)}"
        )
    df["date"] = pd.to_datetime(df["date"])
    df["realtime_start"] = pd.to_datetime(df["realtime_start"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.sort_values(["realtime_start", "date"]).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Snapshot storer
# ---------------------------------------------------------------------------


def _vintage_path(lc_id: str, vintage: pd.Timestamp) -> Path:
    """Per master spec §2.4.7: ``_vintages/<lc_id>__YYYYMMDD.parquet``."""
    return MASTER_DIR / "_vintages" / f"{lc_id}__{vintage.strftime('%Y%m%d')}.parquet"


def store_vintage_snapshots(
    lc_id: str,
    fred_id: str,
    long_frame: pd.DataFrame,
    *,
    vintage_start: pd.Timestamp | None = None,
    vintage_dir: Path | None = None,
) -> dict[pd.Timestamp, Path]:
    """Split a long-format ALFRED frame into per-vintage parquets.

    Each snapshot file contains the master schema for all observations whose
    ``realtime_start <= vintage`` — i.e., the data as it would have been known
    on that vintage date.

    Parameters
    ----------
    lc_id : str
        LC v1 series id (e.g., "m2_sl"). Used in the output filename.
    fred_id : str
        Original FRED series id; recorded in the ``source`` column.
    long_frame : pd.DataFrame
        Output of :func:`fetch_alfred_all_releases`.
    vintage_start : pd.Timestamp or None
        Earliest vintage date to materialize. If None, takes the earliest
        ``realtime_start`` in the frame.
    vintage_dir : Path or None
        Override for ``MASTER_DIR/_vintages`` (test fixture).

    Returns
    -------
    dict
        Mapping vintage date → on-disk parquet path.

    References
    ----------
    [1] spec_v11_3__liquidity_composite.md §1.2
    [2] master spec §2.4.7
    """
    if long_frame.empty:
        raise DataValidationError(f"ALFRED long frame is empty for {fred_id}")
    vintages_dir = vintage_dir or (MASTER_DIR / "_vintages")
    vintages_dir.mkdir(parents=True, exist_ok=True)
    # Defensive: coerce to datetime (the long frame may arrive untyped, e.g.,
    # from synthetic test fixtures or non-fredapi sources).
    long_frame = long_frame.copy()
    long_frame["date"] = pd.to_datetime(long_frame["date"])
    long_frame["realtime_start"] = pd.to_datetime(long_frame["realtime_start"])
    if vintage_start is None:
        vintage_start = pd.Timestamp(long_frame["realtime_start"].min())
    unique_vintages = sorted(
        v for v in long_frame["realtime_start"].dropna().unique()
        if pd.Timestamp(v) >= vintage_start
    )
    written: dict[pd.Timestamp, Path] = {}
    for v in unique_vintages:
        v_ts = pd.Timestamp(v)
        # Data as known on vintage v: all rows whose realtime_start <= v.
        as_of = long_frame[long_frame["realtime_start"] <= v_ts]
        # Keep the LATEST realtime_start per date (the most recent revision known by v).
        as_of = as_of.sort_values("realtime_start").drop_duplicates(
            subset=["date"], keep="last",
        )
        as_of = as_of.dropna(subset=["value"]).sort_values("date")
        if as_of.empty:
            continue
        snapshot = pd.DataFrame(
            {
                "value": as_of["value"].astype("float64").values,
                "source": pd.array(
                    [f"alfred:{fred_id}"] * len(as_of), dtype="string",
                ),
                "vintage": pd.to_datetime([v_ts] * len(as_of)),
                "transform": pd.array(["none"] * len(as_of), dtype="string"),
            },
            index=pd.DatetimeIndex(as_of["date"].values, name="date"),
        )
        snapshot = snapshot[MASTER_COLUMNS]
        out = vintage_dir / f"{lc_id}__{v_ts.strftime('%Y%m%d')}.parquet" \
            if vintage_dir is not None else _vintage_path(lc_id, v_ts)
        atomic_write_parquet(out, snapshot)
        written[v_ts] = out
    return written


# ---------------------------------------------------------------------------
# load_master(vintage=) extension shim
# ---------------------------------------------------------------------------


def load_master_at_vintage(
    lc_id: str,
    vintage: pd.Timestamp,
    *,
    vintage_dir: Path | None = None,
) -> pd.Series:
    """Load the ``lc_id`` series as it was known on the supplied vintage date.

    Picks the snapshot whose vintage date is the latest one ≤ supplied vintage.

    Parameters
    ----------
    lc_id : str
        LC v1 series id (e.g., "m2_sl").
    vintage : pd.Timestamp
        Decision date for the backtest.
    vintage_dir : Path or None
        Override for ``MASTER_DIR/_vintages`` (test fixture).

    Returns
    -------
    pd.Series
        Float64 series indexed by date, named ``lc_id``.

    Raises
    ------
    FileNotFoundError
        If no vintage snapshot exists with date ≤ ``vintage``.

    References
    ----------
    [1] spec_v11_3__liquidity_composite.md §1.2 ``load_master(vintage=...)``
    [2] master spec §2.4.10 (consumer API)
    """
    base = vintage_dir or (MASTER_DIR / "_vintages")
    if not base.exists():
        raise FileNotFoundError(
            f"No vintage directory at {base}; run build_lc_alfred_vintages first"
        )
    candidates: list[tuple[pd.Timestamp, Path]] = []
    for p in base.glob(f"{lc_id}__*.parquet"):
        # Filename: <lc_id>__YYYYMMDD.parquet
        stem = p.stem
        try:
            date_part = stem.split("__", 1)[1]
            v = pd.Timestamp(date_part)
        except (IndexError, ValueError):
            continue
        if v <= vintage:
            candidates.append((v, p))
    if not candidates:
        raise FileNotFoundError(
            f"No vintage snapshot for {lc_id} at or before {vintage.date()}; "
            f"earliest available may be later than requested vintage"
        )
    candidates.sort()
    _, chosen = candidates[-1]
    df = pd.read_parquet(chosen)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"
    series = df["value"].astype("float64").copy()
    series.name = lc_id
    return series


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build_lc_alfred_vintages(
    api_key: str,
    *,
    targets: tuple[AlfredTarget, ...] = LC_V1_ALFRED_TARGETS,
    fred_client_factory: object | None = None,
    vintage_dir: Path | None = None,
) -> dict[str, dict[pd.Timestamp, Path]]:
    """Backfill ALFRED vintage snapshots for the 5 spec-mandated series.

    NOTE: this is a slow operation (one network call per series, then potentially
    thousands of small parquets written). The spec budgets 1-2h for A2.

    Parameters
    ----------
    api_key : str
        FRED API key.
    targets : tuple of AlfredTarget
        Defaults to :data:`LC_V1_ALFRED_TARGETS` (the 5 spec-mandated series).
    fred_client_factory : callable or None
        See :func:`fetch_alfred_all_releases`.
    vintage_dir : Path or None
        Override storage location (test fixture).

    Returns
    -------
    dict
        Outer key: lc_id. Inner: vintage date → snapshot path.

    References
    ----------
    [1] spec_v11_3__liquidity_composite.md §16 sub-stage A2
    """
    out: dict[str, dict[pd.Timestamp, Path]] = {}
    for tgt in targets:
        logger.info(
            "ALFRED backfill: %s (lc_id=%s) starting from %s",
            tgt.fred_id, tgt.lc_id, tgt.vintage_start,
        )
        long_frame = fetch_alfred_all_releases(
            tgt.fred_id,
            api_key,
            fred_client_factory=fred_client_factory,
        )
        snapshots = store_vintage_snapshots(
            tgt.lc_id,
            tgt.fred_id,
            long_frame,
            vintage_start=pd.Timestamp(tgt.vintage_start),
            vintage_dir=vintage_dir,
        )
        out[tgt.lc_id] = snapshots
        logger.info(
            "ALFRED backfill: %s wrote %d vintage snapshots",
            tgt.lc_id, len(snapshots),
        )
    return out


__all__ = [
    "AlfredTarget",
    "LC_V1_ALFRED_TARGETS",
    "fetch_alfred_all_releases",
    "store_vintage_snapshots",
    "load_master_at_vintage",
    "build_lc_alfred_vintages",
]
