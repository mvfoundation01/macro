"""Resample mixed-frequency series to a common month-end grid.

Two views are supported:

- ``descriptive`` -- latest-vintage data, forward-filled within each quarter.
  Suitable for dashboards / current-state reporting. Has implicit look-ahead.
- ``backtest``    -- quarterly series enter the monthly grid only after a
  release-lag (GDP ~30d, Z.1 ~75d). Suitable for predictive claims.
"""
from __future__ import annotations

from typing import Literal

import pandas as pd


GDP_RELEASE_LAG = pd.Timedelta(days=30)   # GDP advance estimate ~30d after Q end
Z1_RELEASE_LAG = pd.Timedelta(days=75)    # FRB Z.1 ~75d after Q end


def resample_daily_to_monthly(s: pd.Series, agg: str = "last") -> pd.Series:
    """Daily series -> month-end. ``agg`` in {"last", "mean"}; default last value."""
    if s.empty:
        return s.copy()
    return s.resample("ME").agg(agg).dropna()


def resample_quarterly_descriptive(s: pd.Series) -> pd.Series:
    """Quarterly -> monthly, latest-vintage. Each month in a quarter takes
    that quarter's value (look-ahead: in real time Q value would not be known
    until after Q ends; descriptive view uses the published vintage for every
    month within the quarter). Months AFTER the last observed quarter take
    the last observed quarter's value (forward fill to today), so dashboards
    have a current-state reading using the latest available GDP estimate."""
    if s.empty:
        return s.copy()
    s = s.copy()
    s.index = s.index.to_period("Q").to_timestamp(how="end").normalize()
    # Build a monthly grid covering every month inside every observed quarter,
    # plus 3 months of forward-fill beyond the last quarter (so April-May-June
    # 2026 can still see Q1 2026's GDP while Q2 is in progress).
    start_q = pd.Period(s.index.min(), freq="Q")
    end_q = pd.Period(s.index.max(), freq="Q")
    monthly_end = end_q.end_time + pd.offsets.MonthEnd(3)
    monthly_idx = pd.date_range(start_q.start_time, monthly_end, freq="ME")
    quarter_end_lookup = s.to_dict()
    last_value: float | None = None
    out_values: list[float] = []
    out_index: list[pd.Timestamp] = []
    for m in monthly_idx:
        q_end = pd.Period(m, freq="Q").end_time.normalize()
        if q_end in quarter_end_lookup:
            last_value = float(quarter_end_lookup[q_end])
        # If we're past the last observed quarter, fall through to last_value.
        if last_value is None:
            continue
        out_index.append(m)
        out_values.append(last_value)
    out = pd.Series(out_values, index=pd.DatetimeIndex(out_index), name=s.name)
    return out


def resample_quarterly_backtest(s: pd.Series, release_lag: pd.Timedelta) -> pd.Series:
    """Quarterly -> monthly with a release-lag. Eliminates look-ahead.

    For month-end ``m``, the value used is the most-recent quarter ``q`` where
    ``q + release_lag <= m``.
    """
    if s.empty:
        return s.copy()
    s = s.copy()
    s.index = s.index.to_period("Q").to_timestamp(how="end").normalize()
    monthly_idx = pd.date_range(
        s.index.min(),
        pd.Timestamp.today().normalize() + pd.offsets.MonthEnd(0),
        freq="ME",
    )
    quarter_dates = s.index.to_numpy()
    lag_days = release_lag.days
    available_at = s.index + pd.Timedelta(days=lag_days)
    available_at_np = available_at.to_numpy()
    values_np = s.to_numpy()

    out_values: list[float] = []
    out_index: list[pd.Timestamp] = []
    for m in monthly_idx:
        mask = available_at_np <= m.to_numpy()
        if mask.any():
            # Pick the most recent quarter that is available by ``m``.
            last_idx = mask.nonzero()[0][-1]
            out_index.append(m)
            out_values.append(float(values_np[last_idx]))
    out = pd.Series(out_values, index=pd.DatetimeIndex(out_index), name=s.name)
    return out


def align_to_monthly_grid(
    series_dict: dict[str, pd.Series],
    view: Literal["descriptive", "backtest"],
    lags: dict[str, pd.Timedelta] | None = None,
    daily_keys: frozenset[str] = frozenset({"wilshire_usd_t", "spx", "spxtr"}),
    quarterly_keys: frozenset[str] = frozenset(
        {"gdp_t", "equities_all_t", "equities_public_t", "equities_nonfin_t"}
    ),
) -> pd.DataFrame:
    """Build aligned monthly DataFrame from a dict of mixed-frequency series.

    ``lags`` is a per-key override; defaults: GDP -> 30d, Z.1 -> 75d, others -> 0.
    Series not listed in ``daily_keys`` or ``quarterly_keys`` are treated as
    already-monthly (Shiller-style) and re-indexed to month-end.
    """
    if lags is None:
        lags = {
            "gdp_t": GDP_RELEASE_LAG,
            "equities_all_t": Z1_RELEASE_LAG,
            "equities_public_t": Z1_RELEASE_LAG,
            "equities_nonfin_t": Z1_RELEASE_LAG,
        }

    out: dict[str, pd.Series] = {}
    for key, s in series_dict.items():
        if s is None or s.empty:
            continue
        if key in daily_keys:
            out[key] = resample_daily_to_monthly(s, agg="last")
        elif key in quarterly_keys:
            if view == "descriptive":
                out[key] = resample_quarterly_descriptive(s)
            else:
                lag = lags.get(key, pd.Timedelta(days=0))
                out[key] = resample_quarterly_backtest(s, lag)
        else:
            s2 = s.copy()
            s2.index = s2.index.to_period("M").to_timestamp(how="end").normalize()
            out[key] = s2

    if not out:
        return pd.DataFrame()

    df = pd.DataFrame(out)
    return df.dropna(how="all")


__all__ = [
    "GDP_RELEASE_LAG",
    "Z1_RELEASE_LAG",
    "resample_daily_to_monthly",
    "resample_quarterly_descriptive",
    "resample_quarterly_backtest",
    "align_to_monthly_grid",
]
