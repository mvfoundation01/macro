"""Trend battery: log-linear OLS, HP filter, Bai-Perron piecewise log-linear.

Per Spec v4.1, Bai-Perron is the PRIMARY trend driving the headline z-score.
Rationale: log-linear assumes a single regime since the series began, which
mis-specifies BI behavior post-1990s. Bai-Perron reduces to log-linear when
no breaks are detected (m=0), so this is a strict generalization.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger("buffett.models.trend")


# ---------------------------------------------------------------------------
# Primary: log-linear OLS
# ---------------------------------------------------------------------------


def log_linear_trend(s: pd.Series) -> dict[str, Any]:
    """log(s_t) = alpha + beta * t + eps_t via OLS."""
    import statsmodels.api as sm

    s_clean = s.dropna()
    if s_clean.empty:
        raise ValueError("log_linear_trend: empty series")
    if (s_clean <= 0).any():
        raise ValueError("log_linear_trend: all values must be positive (log domain)")

    log_s = np.log(s_clean.values)
    t = np.arange(len(log_s), dtype="float64")
    X = sm.add_constant(t)
    model = sm.OLS(log_s, X).fit()
    fitted_log = model.predict(X)
    return {
        "fitted": pd.Series(np.exp(fitted_log), index=s_clean.index, name="trend"),
        "residuals": pd.Series(log_s - fitted_log, index=s_clean.index, name="resid"),
        "alpha": float(model.params[0]),
        "beta": float(model.params[1]),
        "r_squared": float(model.rsquared),
    }


# ---------------------------------------------------------------------------
# HP filter
# ---------------------------------------------------------------------------


def hp_filter_trend(s: pd.Series, lamb: float = 14400.0) -> dict[str, Any]:
    """HP filter on log(s). lambda=14400 for monthly per Ravn-Uhlig 2002."""
    from statsmodels.tsa.filters.hp_filter import hpfilter

    s_clean = s.dropna()
    if s_clean.empty:
        raise ValueError("hp_filter_trend: empty series")
    if (s_clean <= 0).any():
        raise ValueError("hp_filter_trend: all values must be positive (log domain)")

    log_s = np.log(s_clean.values)
    cycle, trend = hpfilter(log_s, lamb=lamb)
    return {
        "fitted": pd.Series(np.exp(np.asarray(trend)), index=s_clean.index, name="trend"),
        "residuals": pd.Series(np.asarray(cycle), index=s_clean.index, name="resid"),
        "lambda": float(lamb),
    }


# ---------------------------------------------------------------------------
# Bai-Perron piecewise log-linear (canonical structural-break-aware trend)
# ---------------------------------------------------------------------------


def bai_perron_trend(s: pd.Series, **kw: Any) -> dict[str, Any]:
    """Bai-Perron piecewise log-linear trend.

    Wraps :func:`src.models.bai_perron.bai_perron`, applied to ``log(s)``. The
    DP runs on the log scale; ``fitted`` is converted back to the original
    units. Residuals stay on the log scale (so they're comparable to those of
    ``log_linear_trend`` / ``hp_filter_trend``).
    """
    from src.models.bai_perron import bai_perron

    s_clean = s.dropna()
    if s_clean.empty:
        raise ValueError("bai_perron_trend: empty series")
    if (s_clean <= 0).any():
        raise ValueError("bai_perron_trend: all values must be positive (log domain)")

    log_s = pd.Series(np.log(s_clean.values), index=s_clean.index, name="log_s")
    bp = bai_perron(log_s, **kw)
    return {
        "fitted": pd.Series(
            np.exp(bp["fitted"].values), index=log_s.index, name="trend"
        ),
        "residuals": bp["residuals"],
        "break_dates": bp["break_dates"],
        "n_breaks": bp["m_optimal"],
        "segments": bp["segments"],
        "method": bp["method"],
        "criterion_values": bp["criterion_values"],
    }


# Backwards-compatibility alias for any v4.0 callers.
bai_perron_piecewise = bai_perron_trend


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


def trend_battery(s: pd.Series) -> dict[str, Any]:
    """Run all three trend specs. **Bai-Perron is the primary** (Spec v4.1).

    Returns a dict containing the three sub-results plus:
        primary           -- name of the primary spec (``"bai_perron"``)
        primary_residuals -- residuals from the primary spec
        agreement         -- mean of pairwise abs-correlations between the
                              three fitted trend lines (0..1)
    """
    ll = log_linear_trend(s)
    hp = hp_filter_trend(s)
    bp = bai_perron_trend(s)

    fits = pd.DataFrame(
        {
            "loglinear": ll["fitted"],
            "hp": hp["fitted"],
            "bai_perron": bp["fitted"],
        }
    ).dropna()
    if len(fits) >= 5:
        corr = fits.corr().abs().values
        # Mean of off-diagonal entries.
        n = corr.shape[0]
        mask = ~np.eye(n, dtype=bool)
        agreement = float(corr[mask].mean()) if mask.any() else 1.0
    else:
        agreement = 0.0

    return {
        "loglinear": ll,
        "hp": hp,
        "bai_perron": bp,
        "primary": "bai_perron",
        "primary_residuals": bp["residuals"],
        "agreement": float(agreement),
    }


def frames(battery: dict[str, Any]) -> dict[str, pd.Series]:
    """Spec v4.2 dual-frame accessor.

    Returns the two canonical residual streams from a ``trend_battery`` result:
        - ``long_run``       -- log-linear OLS residuals (full-sample trend)
        - ``current_regime`` -- Bai-Perron piecewise residuals (regime-aware)
    """
    return {
        "long_run": battery["loglinear"]["residuals"],
        "current_regime": battery["bai_perron"]["residuals"],
    }


__all__ = [
    "log_linear_trend",
    "hp_filter_trend",
    "bai_perron_trend",
    "bai_perron_piecewise",  # back-compat alias
    "trend_battery",
    "frames",
]


# ---------------------------------------------------------------------------
# Internal helper retained for back-compat with tests that exercise it.
# ---------------------------------------------------------------------------


def _trend_agreement(specs: list[pd.Series]) -> float:
    """Pairwise R^2 between trend lines (used by older trend_battery tests)."""
    if len(specs) < 2:
        return 1.0
    idx = specs[0].index
    for s in specs[1:]:
        idx = idx.intersection(s.index)
    if len(idx) < 5:
        return 0.0
    arrays = [np.log(s.loc[idx].values) for s in specs]
    pairwise: list[float] = []
    for i in range(len(arrays)):
        for j in range(i + 1, len(arrays)):
            a, b = arrays[i], arrays[j]
            denom = float(np.var(a) * np.var(b))
            if denom == 0:
                pairwise.append(1.0)
                continue
            corr = float(np.corrcoef(a, b)[0, 1])
            pairwise.append(max(0.0, corr) ** 2)
    return float(np.mean(pairwise)) if pairwise else 1.0
