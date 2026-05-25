"""Master History Archive (MoDH) for the Buffett Indicator pipeline.

Per Master Spec section 2.4, this module maintains a persistent, append-only
spliced master parquet for each canonical series. Downstream code consumes
series via :func:`load_master` only -- raw or cache files are never read directly.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from src.config import CATALOG, MASTER_DIR, SCALING_ANCHORS, ensure_skeleton
from src.ingest._base import (
    DataValidationError,
    IntegrityError,
    SourceMissingError,
    atomic_write_json,
    atomic_write_parquet,
    file_lock,
    get_logger,
    utcnow,
)
from src.ingest.csv_loader import load_tradingview_file
from src.config import TV_WILSHIRE
from src.ingest.yahoo_loader import load_wilshire_yahoo, YahooSeries

logger = get_logger("buffett.ingest.master")

SCHEMA_VERSION = 1
MASTER_COLUMNS = ["value", "source", "vintage", "transform"]


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MasterSeries:
    series_id: str
    data: pd.Series
    sources_used: tuple[str, ...]
    earliest: pd.Timestamp
    latest: pd.Timestamp
    n_observations: int
    schema_version: int = SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Catalog + scaling-anchor helpers
# ---------------------------------------------------------------------------


def _read_catalog() -> dict[str, dict]:
    if CATALOG.exists():
        return json.loads(CATALOG.read_text() or "{}")
    return {}


def _write_catalog(catalog: dict[str, dict]) -> None:
    atomic_write_json(CATALOG, catalog)


def _read_anchors() -> dict[str, dict]:
    if SCALING_ANCHORS.exists():
        return json.loads(SCALING_ANCHORS.read_text() or "{}")
    return {}


def _write_anchors(anchors: dict[str, dict]) -> None:
    atomic_write_json(SCALING_ANCHORS, anchors)


def _master_path(series_id: str) -> Path:
    return MASTER_DIR / f"{series_id}.parquet"


def _empty_master_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "value": pd.Series(dtype="float64"),
            "source": pd.Series(dtype="string"),
            "vintage": pd.Series(dtype="datetime64[ns]"),
            "transform": pd.Series(dtype="string"),
        }
    )


# ---------------------------------------------------------------------------
# Splice algorithm (Spec section 8.4)
# ---------------------------------------------------------------------------


def _splice_two_series(
    base: pd.Series,
    extension: pd.Series,
    base_label: str,
    ext_label: str,
    *,
    overlap_min_days: int = 60,
    mad_tolerance: float = 0.05,
) -> tuple[pd.Series, dict]:
    """Splice ``extension`` onto ``base`` after computing a robust scale factor.

    Returns the combined series and a metadata dict describing the splice.
    """
    base = base.dropna().sort_index()
    extension = extension.dropna().sort_index()

    if base.empty:
        raise DataValidationError(f"Splice base series ({base_label}) is empty")
    if extension.empty:
        raise DataValidationError(f"Splice extension series ({ext_label}) is empty")

    common_idx = base.index.intersection(extension.index)
    overlap_n = len(common_idx)
    if overlap_n < overlap_min_days:
        raise DataValidationError(
            f"Insufficient splice overlap between {base_label} and {ext_label}: "
            f"{overlap_n} days < {overlap_min_days}"
        )

    ratios = (extension.loc[common_idx] / base.loc[common_idx]).replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    if ratios.empty:
        raise DataValidationError(
            f"Splice overlap contains no usable rows for {base_label} vs {ext_label}"
        )
    k = float(ratios.median())
    if k == 0 or not np.isfinite(k):
        raise DataValidationError(
            f"Splice scale factor k is degenerate (k={k}) for {base_label} vs {ext_label}"
        )
    mad_r = float((ratios - k).abs().median())
    if mad_r / k > mad_tolerance:
        raise DataValidationError(
            f"Unstable splice ratio for {base_label}->{ext_label}: "
            f"MAD/k = {mad_r/k:.3f} > {mad_tolerance:.2f}"
        )

    extension_rescaled = extension / k
    base_last = base.index.max()
    extension_tail = extension_rescaled.loc[extension_rescaled.index > base_last]
    spliced = pd.concat([base, extension_tail]).sort_index()

    # Cosmetic dedupe (in case base and ext share the exact last date).
    spliced = spliced[~spliced.index.duplicated(keep="first")]

    metadata: dict = {
        "splice_date": str(base_last.date()),
        "overlap_n_days": int(overlap_n),
        "scale_factor_k": k,
        "scale_factor_mad": mad_r,
        "rescale_target": f"extension scaled by 1/{k:.6f} to match {base_label}",
        "base_label": base_label,
        "ext_label": ext_label,
        "computed_at": utcnow().isoformat(),
    }
    return spliced, metadata


# ---------------------------------------------------------------------------
# Atomic merge (Spec section 8.5)
# ---------------------------------------------------------------------------


def _update_master_atomically(series_id: str, candidate: pd.DataFrame) -> pd.DataFrame:
    """Merge ``candidate`` into the existing master parquet (append-only)."""
    ensure_skeleton()
    path = _master_path(series_id)

    if not isinstance(candidate.index, pd.DatetimeIndex):
        raise IntegrityError("candidate index must be DatetimeIndex")
    if candidate.index.name != "date":
        candidate = candidate.copy()
        candidate.index.name = "date"
    missing_cols = set(MASTER_COLUMNS) - set(candidate.columns)
    if missing_cols:
        raise IntegrityError(
            f"candidate missing required columns: {sorted(missing_cols)}"
        )
    candidate = candidate[MASTER_COLUMNS].sort_index()
    if candidate.index.has_duplicates:
        raise IntegrityError("candidate has duplicate dates")

    with file_lock(path):
        if path.exists():
            existing = pd.read_parquet(path)
            existing.index = pd.DatetimeIndex(existing.index)
            existing.index.name = "date"
        else:
            existing = _empty_master_frame()
            existing.index = pd.DatetimeIndex([], name="date")

        merged_rows: list[pd.DataFrame] = []

        # Append: only the truly NEW dates.
        new_mask = ~candidate.index.isin(existing.index)
        new_rows = candidate.loc[new_mask]

        # Verify that any overlapping dates carry the same value (idempotent re-write).
        common = candidate.index.intersection(existing.index)
        for d in common:
            old_val = float(existing.loc[d, "value"])
            new_val = float(candidate.loc[d, "value"])
            if pd.isna(old_val) and pd.isna(new_val):
                continue
            if abs(old_val - new_val) > 1e-9 * max(abs(old_val), 1.0):
                # Different value -- compare vintages.
                old_vintage = pd.to_datetime(existing.loc[d, "vintage"])
                new_vintage = pd.to_datetime(candidate.loc[d, "vintage"])
                if pd.isna(new_vintage) or new_vintage <= old_vintage:
                    raise IntegrityError(
                        f"{series_id}: refuse to overwrite {d.date()} with same/older "
                        f"vintage (old={old_val}, new={new_val})"
                    )
                # Snapshot old.
                snap_dir = MASTER_DIR / "_vintages"
                snap_dir.mkdir(parents=True, exist_ok=True)
                snap = snap_dir / f"{series_id}_{old_vintage.date()}.parquet"
                if not snap.exists():
                    atomic_write_parquet(snap, existing)
                existing.loc[d, "value"] = new_val
                existing.loc[d, "source"] = candidate.loc[d, "source"]
                existing.loc[d, "vintage"] = new_vintage
                existing.loc[d, "transform"] = candidate.loc[d, "transform"]

        merged_rows.append(existing)
        if not new_rows.empty:
            merged_rows.append(new_rows)
        merged = pd.concat(merged_rows).sort_index()
        merged = merged[~merged.index.duplicated(keep="first")]

        # Length non-decreasing.
        if len(merged) < len(existing):
            raise IntegrityError(
                f"{series_id}: merged length {len(merged)} < existing {len(existing)}"
            )

        atomic_write_parquet(path, merged)

        # Update catalog.
        catalog = _read_catalog()
        catalog[series_id] = {
            "path": str(path),
            "earliest": str(merged.index.min().date()),
            "latest": str(merged.index.max().date()),
            "n_observations": int(len(merged)),
            "schema_version": SCHEMA_VERSION,
            "sources_used": sorted(set(merged["source"].dropna().astype(str).tolist())),
            "last_refresh": utcnow().isoformat(),
        }
        _write_catalog(catalog)
        return merged


# ---------------------------------------------------------------------------
# Build: Wilshire master (Spec section 8.6)
# ---------------------------------------------------------------------------


def build_wilshire_master(
    *,
    force_rebuild: bool = False,
    tv_path: Path | None = None,
    yahoo_loader: callable | None = None,
) -> MasterSeries:
    """Build/refresh the spliced Wilshire 5000 master parquet."""
    ensure_skeleton()
    series_id = "wilshire_5000"
    path = _master_path(series_id)

    tv_file = tv_path or TV_WILSHIRE
    if not tv_file.exists():
        raise SourceMissingError(
            f"Wilshire TradingView export not found: {tv_file}",
            user_message=(
                f"Missing TradingView Wilshire file ({tv_file.name}); cannot build "
                "deep-history portion of the master."
            ),
        )

    # The TV Wilshire mirror is monthly in 1970-1975, then daily. Allow ~35-day
    # gaps so the early monthly portion survives validation.
    tv = load_tradingview_file(tv_file, expected_frequency="D", max_gap_days=35)
    tv_close = tv.data["close"].dropna()
    tv_label = "tv_FRED_WILL5000PRFC"

    fetch = yahoo_loader if yahoo_loader is not None else load_wilshire_yahoo
    yh: YahooSeries = fetch()
    yh_close = yh.data["Close"].dropna()
    yh_label = f"yahoo_{yh.symbol}"

    # Re-use saved scale factor on subsequent runs (unless force_rebuild).
    anchors = _read_anchors()
    saved = anchors.get(series_id) if not force_rebuild else None

    if saved and saved.get("tv_label") == tv_label and saved.get("yh_label") == yh_label:
        k = float(saved["scale_factor_k"])
        logger.info(
            "Using cached splice scale_factor_k=%.6f from anchors for %s",
            k,
            series_id,
        )
        common = tv_close.index.intersection(yh_close.index)
        meta = {
            "splice_date": saved.get("splice_date"),
            "overlap_n_days": saved.get("overlap_n_days", len(common)),
            "scale_factor_k": k,
            "scale_factor_mad": saved.get("scale_factor_mad", 0.0),
            "rescale_target": f"extension scaled by 1/{k:.6f} to match {tv_label}",
            "base_label": tv_label,
            "ext_label": yh_label,
            "computed_at": saved.get("computed_at"),
            "reused": True,
        }
        yh_rescaled = yh_close / k
        base_last = tv_close.index.max()
        ext_tail = yh_rescaled.loc[yh_rescaled.index > base_last]
        spliced = pd.concat([tv_close, ext_tail]).sort_index()
        spliced = spliced[~spliced.index.duplicated(keep="first")]
    else:
        spliced, meta = _splice_two_series(
            tv_close, yh_close, base_label=tv_label, ext_label=yh_label
        )

    tv_last = tv_close.index.max()
    base_mask = spliced.index <= tv_last
    sources = np.where(base_mask, tv_label, yh_label)
    splice_label = (
        f"splice_scaled:x{1/meta['scale_factor_k']:.6f}@{meta['splice_date']}"
    )
    transforms = np.where(base_mask, "none", splice_label)
    vintages = np.where(
        base_mask,
        np.datetime64(pd.Timestamp(tv.retrieval_timestamp)),
        np.datetime64(pd.Timestamp(yh.retrieval_timestamp)),
    )

    candidate = pd.DataFrame(
        {
            "value": spliced.astype("float64").values,
            "source": pd.array(sources, dtype="string"),
            "vintage": pd.to_datetime(vintages),
            "transform": pd.array(transforms, dtype="string"),
        },
        index=spliced.index,
    )
    candidate.index.name = "date"

    if force_rebuild and path.exists():
        with file_lock(path):
            path.unlink()
            anchors.pop(series_id, None)
            _write_anchors(anchors)

    merged = _update_master_atomically(series_id, candidate)

    # Persist the splice anchor (only on fresh compute).
    if not meta.get("reused"):
        anchors[series_id] = {
            "splice_date": meta["splice_date"],
            "tv_label": tv_label,
            "yh_label": yh_label,
            "scale_factor_k": meta["scale_factor_k"],
            "scale_factor_mad": meta["scale_factor_mad"],
            "overlap_n_days": meta["overlap_n_days"],
            "computed_at": meta["computed_at"],
        }
        _write_anchors(anchors)

    series = merged["value"].astype("float64")
    series.name = series_id

    return MasterSeries(
        series_id=series_id,
        data=series,
        sources_used=tuple(sorted(set(merged["source"].dropna().astype(str).tolist()))),
        earliest=merged.index.min(),
        latest=merged.index.max(),
        n_observations=int(len(merged)),
    )


# ---------------------------------------------------------------------------
# Public read API (Spec section 8.3)
# ---------------------------------------------------------------------------


def load_master(
    series_id: str,
    *,
    start: str | None = None,
    end: str | None = None,
    frequency: Literal["D", "W", "M", "Q", "A"] | None = None,
    fill: Literal["none", "ffill", "interpolate"] = "none",
    vintage: pd.Timestamp | str = "latest",
) -> MasterSeries:
    """Read a master series. THE single API for downstream consumers.

    Vintage semantics (v2.0 approximation per PHASE_B_C_RESUME §2):
    -----------------------------------------------------------------
    The ``vintage`` kwarg filters to rows where ``date <= vintage``. This is
    the OBSERVATION DATE approximation of "as known at time t" - NOT true
    ALFRED-style release-vintage filtering. For revisable FRED series
    (M2SL, BUSLOANS, TOTLL, WALCL, WDTGAL), the current value at ``date``
    is the LATEST REVISION published as of ingestion time, not necessarily
    the value that was known to a forecaster at ``date``.

    This is a deliberate v2.0 approximation per sealed pre-reg §3.2.2 and
    ``PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md`` §2. True ALFRED-aware
    ingestion is deferred to a future sub-sprint as documented in
    ``outputs/v2_sprint_vintage_approximation_note.md``.

    - ``vintage="latest"`` (default) -> no filter; preserves pre-v2.0 behavior.
    - ``vintage=pd.Timestamp(...)``  -> filter ``series.loc[index <= vintage]``.
    - ``vintage`` in the future       -> raises ``ValueError``.
    """
    path = _master_path(series_id)
    if not path.exists():
        raise SourceMissingError(
            f"Master not built for series_id='{series_id}'. Run build_all_masters() first.",
            user_message=(
                f"Master parquet for '{series_id}' is missing. Run the orchestrator to build it."
            ),
        )
    df = pd.read_parquet(path)
    df.index = pd.DatetimeIndex(df.index)
    df.index.name = "date"

    series = df["value"].astype("float64").copy()
    series.name = series_id

    if start is not None:
        series = series.loc[series.index >= pd.Timestamp(start)]
    if end is not None:
        series = series.loc[series.index <= pd.Timestamp(end)]

    if isinstance(vintage, str):
        if vintage != "latest":
            raise ValueError(
                f"vintage must be 'latest' or a pd.Timestamp; got string {vintage!r}"
            )
    else:
        vintage_ts = pd.Timestamp(vintage)
        if vintage_ts > pd.Timestamp.now():
            raise ValueError(
                f"vintage={vintage_ts!s} is in the future (now={pd.Timestamp.now()!s})"
            )
        series = series.loc[series.index <= vintage_ts]

    if frequency is not None:
        freq_alias = {"D": "D", "W": "W-FRI", "M": "M", "Q": "Q", "A": "Y"}[frequency]
        series = series.resample(freq_alias).last()

    if fill == "ffill":
        series = series.ffill()
    elif fill == "interpolate":
        series = series.interpolate(method="time")

    sources_in_window = (
        df.loc[series.index.intersection(df.index), "source"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    return MasterSeries(
        series_id=series_id,
        data=series,
        sources_used=tuple(sorted(sources_in_window)),
        earliest=series.index.min() if not series.empty else pd.Timestamp("NaT"),
        latest=series.index.max() if not series.empty else pd.Timestamp("NaT"),
        n_observations=int(len(series)),
    )


# ---------------------------------------------------------------------------
# Build everything
# ---------------------------------------------------------------------------


def build_all_masters(
    *,
    force_rebuild: bool = False,
    yahoo_loader: callable | None = None,
) -> dict[str, MasterSeries]:
    """Build every known master series. Currently: wilshire_5000."""
    out: dict[str, MasterSeries] = {}
    out["wilshire_5000"] = build_wilshire_master(
        force_rebuild=force_rebuild, yahoo_loader=yahoo_loader
    )
    return out


__all__ = [
    "MasterSeries",
    "build_wilshire_master",
    "build_all_masters",
    "load_master",
    "_splice_two_series",
    "_update_master_atomically",
    "SCHEMA_VERSION",
]
