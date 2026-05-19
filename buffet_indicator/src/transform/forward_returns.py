"""Forward-return reconstruction and h-month-ahead CAGR tables.

Three series are produced (Spec v5 section 3):
    - ``fr_spliced``        : Shiller real-TR x CPI -> nominal (pre-1988) +
                              SPXTR (1988+). Primary input for predictive
                              regressions.
    - ``fr_spxtr_only``     : SPXTR daily resampled to month-end, 1988+.
    - ``fr_shiller_only``   : Shiller real_total_return (CPI-adjusted),
                              1871+. Real-return panel for cross-check.

Each base series is converted into an h-month forward annualized-CAGR
DataFrame by :func:`forward_returns`. ``build_forward_returns`` wires up
all three.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from src.ingest._base import IngestError, get_logger
from src.ingest.shiller_loader import ShillerData

logger = get_logger("buffett.transform.forward_returns")


DEFAULT_HORIZONS: tuple[int, ...] = (1, 3, 12, 36, 60, 84, 120)
SPLICE_BOUNDARY = pd.Timestamp("1988-01-31")


class ForwardReturnSpliceError(IngestError):
    """Splice continuity gate failed (Shiller vs SPXTR diverge in overlap)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_month_end(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return idx.to_period("M").to_timestamp(how="end").normalize()


def shiller_nominal_total_return(sh: ShillerData) -> pd.Series:
    """Reconstruct Shiller's nominal total-return level series.

    ``real_TR`` is CPI-adjusted (Shiller's base date). To get nominal:
        nominal_TR_t = real_TR_t * CPI_t / CPI_base
    """
    df = sh.data
    required = {"real_total_return", "cpi"}
    if not required <= set(df.columns):
        missing = required - set(df.columns)
        raise ForwardReturnSpliceError(
            f"Shiller data is missing columns for nominal TR reconstruction: {missing}"
        )
    real_tr = df["real_total_return"].dropna()
    cpi = df["cpi"].dropna()
    common = real_tr.index.intersection(cpi.index)
    if common.empty:
        raise ForwardReturnSpliceError(
            "Shiller real_total_return and CPI have no overlap"
        )
    real_tr = real_tr.loc[common]
    cpi = cpi.loc[common]
    cpi_base = float(cpi.iloc[0])
    nominal = real_tr * (cpi / cpi_base)
    nominal.name = "nominal_total_return"
    return nominal


def spxtr_monthly_level(spxtr_daily: pd.Series) -> pd.Series:
    """Resample SPXTR daily close to month-end (last business day)."""
    if spxtr_daily.empty:
        return spxtr_daily.copy()
    idx = pd.DatetimeIndex(spxtr_daily.index)
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    s = pd.Series(spxtr_daily.to_numpy(), index=idx, name="spxtr")
    monthly = s.resample("ME").last().dropna()
    monthly.name = "spxtr_monthly"
    return monthly


def shiller_real_total_return_monthly(sh: ShillerData) -> pd.Series:
    """Shiller's real_total_return at month-end (cumulative level series, REAL)."""
    df = sh.data
    if "real_total_return" not in df.columns:
        raise ForwardReturnSpliceError(
            "Shiller data is missing real_total_return column"
        )
    s = df["real_total_return"].dropna().copy()
    s.index = _to_month_end(pd.DatetimeIndex(s.index))
    s.name = "real_total_return_monthly"
    return s


# ---------------------------------------------------------------------------
# Splice continuity gate
# ---------------------------------------------------------------------------


def _splice_continuity_check(
    shiller_nominal: pd.Series,
    spxtr_monthly: pd.Series,
    *,
    overlap_months: int = 12,
    max_mean_abs_diff: float = 0.005,
    min_corr: float = 0.95,
) -> dict[str, float]:
    """Compare Shiller-derived and SPXTR-derived monthly returns in their overlap.

    Raises :class:`ForwardReturnSpliceError` if the two series diverge.
    """
    ret_sh = shiller_nominal.pct_change().dropna()
    ret_sp = spxtr_monthly.pct_change().dropna()
    common = ret_sh.index.intersection(ret_sp.index)
    if len(common) < overlap_months:
        raise ForwardReturnSpliceError(
            f"Splice overlap only {len(common)} months; need >= {overlap_months}"
        )
    a = ret_sh.loc[common[:overlap_months]]
    b = ret_sp.loc[common[:overlap_months]]
    mean_abs_diff = float((a - b).abs().mean())
    corr = float(a.corr(b)) if a.std() > 0 and b.std() > 0 else 0.0
    if mean_abs_diff > max_mean_abs_diff or corr < min_corr:
        raise ForwardReturnSpliceError(
            f"Shiller/SPXTR splice diverges in overlap: "
            f"mean_abs_diff={mean_abs_diff:.4f} (max {max_mean_abs_diff:.4f}); "
            f"corr={corr:.3f} (min {min_corr})"
        )
    return {"mean_abs_diff": mean_abs_diff, "corr": corr, "n_overlap": int(len(common))}


def splice_shiller_spxtr(
    shiller_nominal: pd.Series,
    spxtr_monthly: pd.Series,
    *,
    boundary: pd.Timestamp = SPLICE_BOUNDARY,
    check_continuity: bool = True,
) -> pd.Series:
    """Build the spliced nominal total-return level.

    Uses Shiller-derived nominal before ``boundary`` and SPXTR thereafter.
    Levels are rescaled at the boundary so the splice is continuous.
    """
    if check_continuity:
        _splice_continuity_check(shiller_nominal, spxtr_monthly)

    s_pre = shiller_nominal.loc[shiller_nominal.index < boundary]
    s_post = spxtr_monthly.loc[spxtr_monthly.index >= boundary]
    if s_pre.empty or s_post.empty:
        raise ForwardReturnSpliceError(
            f"Empty pre/post segment around boundary {boundary.date()}"
        )

    # Anchor: align levels at the first point of s_post so the splice is continuous.
    # Use Shiller's last pre-boundary level as the anchor.
    pre_last = float(s_pre.iloc[-1])
    post_first = float(s_post.iloc[0])
    if post_first == 0:
        raise ForwardReturnSpliceError("SPXTR starts at zero level")
    k = pre_last / post_first
    s_post_rescaled = s_post * k

    spliced = pd.concat([s_pre, s_post_rescaled]).sort_index()
    spliced = spliced[~spliced.index.duplicated(keep="first")]
    spliced.name = "spliced_nominal_tr"
    return spliced


# ---------------------------------------------------------------------------
# Forward-return tables
# ---------------------------------------------------------------------------


def forward_returns(
    total_return_series: pd.Series,
    horizons_months: Iterable[int] = DEFAULT_HORIZONS,
) -> pd.DataFrame:
    """Annualized h-month forward CAGR for each ``t`` in the input series.

    Output is indexed by the prediction date ``t`` (when state is observed);
    each column ``r_{h}m`` is ``((TR[t+h] / TR[t]) ** (12/h)) - 1``. The last
    ``h`` rows of each column are NaN (future is not observable).
    """
    horizons = list(horizons_months)
    s = total_return_series.copy()
    cols: dict[str, pd.Series] = {}
    for h in horizons:
        future = s.shift(-h)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = future / s
            cagr = np.where(
                (s > 0) & (future > 0),
                ratio ** (12.0 / h) - 1.0,
                np.nan,
            )
        cols[f"r_{h}m"] = pd.Series(cagr, index=s.index)
    return pd.DataFrame(cols, index=s.index)


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------


def build_forward_returns(
    shiller_data: ShillerData,
    spxtr_daily: pd.Series | None,
    horizons_months: Iterable[int] = DEFAULT_HORIZONS,
    *,
    check_continuity: bool = True,
) -> dict[str, pd.DataFrame]:
    """Build all three forward-return panels.

    Returns dict with keys ``fr_spliced``, ``fr_spxtr_only``,
    ``fr_shiller_only``. Each value is a DataFrame indexed by month-end with
    columns ``r_{h}m`` for h in ``horizons_months``.

    If ``spxtr_daily`` is None or empty, ``fr_spxtr_only`` is omitted and the
    spliced series is built from Shiller alone (logged WARNING).
    """
    horizons = list(horizons_months)
    out: dict[str, pd.DataFrame] = {}

    # 1. Shiller nominal TR -> r_{h}m table (real units cross-check).
    shiller_real_tr = shiller_real_total_return_monthly(shiller_data)
    out["fr_shiller_only"] = forward_returns(shiller_real_tr, horizons)

    # 2. SPXTR-only (if present)
    spxtr_monthly: pd.Series | None = None
    if spxtr_daily is not None and not spxtr_daily.empty:
        spxtr_monthly = spxtr_monthly_level(spxtr_daily)
        out["fr_spxtr_only"] = forward_returns(spxtr_monthly, horizons)

    # 3. Spliced nominal TR
    shiller_nominal = shiller_nominal_total_return(shiller_data)
    shiller_nominal.index = _to_month_end(pd.DatetimeIndex(shiller_nominal.index))

    if spxtr_monthly is not None:
        spliced_level = splice_shiller_spxtr(
            shiller_nominal, spxtr_monthly, check_continuity=check_continuity
        )
    else:
        logger.warning(
            "SPXTR not available -- using Shiller-only nominal series for fr_spliced"
        )
        spliced_level = shiller_nominal
    out["fr_spliced"] = forward_returns(spliced_level, horizons)
    # Stash the underlying level series on the DataFrame so consumers can persist it.
    out["fr_spliced"].attrs["level_series"] = spliced_level
    return out


__all__ = [
    "DEFAULT_HORIZONS",
    "SPLICE_BOUNDARY",
    "ForwardReturnSpliceError",
    "shiller_nominal_total_return",
    "shiller_real_total_return_monthly",
    "spxtr_monthly_level",
    "splice_shiller_spxtr",
    "forward_returns",
    "build_forward_returns",
]
