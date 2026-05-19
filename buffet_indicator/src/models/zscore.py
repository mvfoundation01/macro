"""Z-score and empirical-percentile helpers.

Spec v5 default scale estimator is Huber M (`scale_method="huber"`). This
addresses the fat-tail-compression problem that pulled v4.2's bi_allequity z
to +1.43 even at the 98.7th percentile of the residual distribution.
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from src.transform.huber_scale import robust_scale

ScaleMethod = Literal["huber", "mad", "std"]


def expanding_zscore(
    residuals: pd.Series,
    *,
    min_periods: int = 60,
    scale_method: ScaleMethod = "huber",
) -> pd.Series:
    """Expanding-window z-score with a robust scale estimator.

    For each ``t``, compute ``(loc, scale)`` via :func:`robust_scale` over
    ``residuals[:t+1]`` then ``z_t = (resid_t - loc) / scale``. The first
    ``min_periods - 1`` observations return NaN.

    Note: this is the v5 vectorized rewrite; the v4 fast-path (using pandas
    ``expanding().mean()/.std()``) is preserved when ``scale_method="std"`` for
    performance, but the canonical default is the Huber loop.
    """
    if scale_method == "std":
        mu = residuals.expanding(min_periods=min_periods).mean()
        sig = residuals.expanding(min_periods=min_periods).std(ddof=1)
        out = (residuals - mu) / sig
        out.name = "z_expanding"
        return out

    values = residuals.to_numpy(dtype="float64", na_value=np.nan)
    out_arr = np.full(values.shape, np.nan, dtype="float64")
    for i in range(len(values)):
        if i + 1 < min_periods:
            continue
        window = values[: i + 1]
        window = window[~np.isnan(window)]
        if window.size < 2:
            continue
        loc, sc = robust_scale(window, method=scale_method)
        if sc > 0 and not np.isnan(values[i]):
            out_arr[i] = (values[i] - loc) / sc
    out = pd.Series(out_arr, index=residuals.index, name="z_expanding")
    return out


def full_sample_zscore(
    residuals: pd.Series,
    *,
    scale_method: ScaleMethod = "huber",
) -> pd.Series:
    """Standard z-score over the entire series. LOOK-AHEAD; descriptive only."""
    clean = residuals.dropna()
    if clean.empty:
        return pd.Series(
            [float("nan")] * len(residuals), index=residuals.index, name="z_full"
        )
    if scale_method == "std":
        mu = clean.mean()
        sc = clean.std(ddof=1)
    else:
        loc, sc = robust_scale(clean.to_numpy(), method=scale_method)
        mu = loc
    if sc == 0 or pd.isna(sc):
        return pd.Series(
            [float("nan")] * len(residuals), index=residuals.index, name="z_full"
        )
    out = (residuals - mu) / sc
    out.name = "z_full"
    return out


def empirical_percentile(
    residuals: pd.Series, value: float | None = None
) -> float | pd.Series:
    """Empirical CDF rank.

    Scalar ``value`` -> percent of dropna'd series at or below ``value``.
    ``None`` -> expanding-rank Series (each entry = running percentile rank
    of that observation).
    """
    if value is not None:
        clean = residuals.dropna()
        if clean.empty:
            return float("nan")
        return float((clean <= value).mean() * 100.0)

    out = residuals.expanding().apply(
        lambda window: (window <= window.iloc[-1]).mean() * 100.0, raw=False
    )
    out.name = "empirical_pct"
    return out


__all__ = ["expanding_zscore", "full_sample_zscore", "empirical_percentile"]
