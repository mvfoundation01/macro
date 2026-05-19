"""Probability engine: P(event | current z-bucket) with bootstrap CIs."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger("buffett.models.probability_engine")


def _confidence_pct(point: float, ci_lo: float, ci_hi: float) -> float:
    """Smooth scale-invariant confidence in (0, 100], reusing the v4.1 formula."""
    width = max(0.0, float(ci_hi - ci_lo))
    denom = max(abs(float(point)), 0.1)  # probabilities live in [0, 1]; floor of 0.1
    return float(100.0 / (1.0 + width / denom))


def compute_probabilities(
    cond_dist: dict[str, Any],
    *,
    risk_free_rate_decimal: float = 0.043,
    cagr_thresholds: tuple[float, ...] = (0.0, 0.05, 0.07),
    drawdown_thresholds: tuple[float, ...] = (-0.20, -0.30, -0.50),
    n_bootstrap: int = 10_000,
    seed: int = 42,
) -> dict[str, Any]:
    """Bootstrap-CI probabilities for events conditioned on the current bucket.

    Events computed:
      - ``P_neg_return``  -- P(r < 0)
      - ``P_below_rf``    -- P(r < risk_free_rate_decimal)
      - ``P_below_5pct``  -- P(r < 0.05)
      - ``P_above_7pct``  -- P(r > 0.07)

    Drawdown events (``P_dd_*``) are placeholders: full drawdown probabilities
    require path data and arrive in Spec v6.
    """
    rng = np.random.default_rng(seed)
    bucket_returns = np.asarray(cond_dist.get("current_dist") or [], dtype="float64")
    n = int(bucket_returns.size)

    events: dict[str, Any] = {}
    if n == 0:
        for name in ("P_neg_return", "P_below_rf", "P_below_5pct", "P_above_7pct"):
            events[name] = {
                "point": float("nan"),
                "ci95": (float("nan"), float("nan")),
                "n": 0,
                "confidence_pct": float("nan"),
            }
        return {
            "events": events,
            "bucket_n": 0,
            "n_bootstrap": int(n_bootstrap),
            "low_n_flag": True,
            "risk_free_rate_decimal": float(risk_free_rate_decimal),
        }

    def _event_value(arr: np.ndarray, name: str) -> float:
        if name == "P_neg_return":
            return float((arr < 0.0).mean())
        if name == "P_below_rf":
            return float((arr < risk_free_rate_decimal).mean())
        if name == "P_below_5pct":
            return float((arr < 0.05).mean())
        if name == "P_above_7pct":
            return float((arr > 0.07).mean())
        raise KeyError(name)

    event_names = ("P_neg_return", "P_below_rf", "P_below_5pct", "P_above_7pct")
    samples = rng.choice(bucket_returns, size=(n_bootstrap, n), replace=True)
    for name in event_names:
        point = _event_value(bucket_returns, name)
        if name == "P_neg_return":
            boot = (samples < 0.0).mean(axis=1)
        elif name == "P_below_rf":
            boot = (samples < risk_free_rate_decimal).mean(axis=1)
        elif name == "P_below_5pct":
            boot = (samples < 0.05).mean(axis=1)
        else:  # P_above_7pct
            boot = (samples > 0.07).mean(axis=1)
        lo, hi = np.quantile(boot, [0.025, 0.975])
        events[name] = {
            "point": float(point),
            "ci95": (float(lo), float(hi)),
            "n": n,
            "confidence_pct": _confidence_pct(point, float(lo), float(hi)),
        }

    drawdown_events: dict[str, Any] = {}
    for dd in drawdown_thresholds:
        drawdown_events[f"P_dd_lt_{int(dd * 100)}pct"] = {
            "point": float("nan"),
            "ci95": (float("nan"), float("nan")),
            "note": "drawdown probability requires path data -- Spec v6",
        }

    if n < 20:
        logger.warning(
            "probability_engine: current bucket n=%d (<20); CIs will be wide", n
        )

    return {
        "events": events,
        "drawdown_events": drawdown_events,
        "bucket_n": n,
        "n_bootstrap": int(n_bootstrap),
        "low_n_flag": bool(n < 20),
        "risk_free_rate_decimal": float(risk_free_rate_decimal),
    }


__all__ = ["compute_probabilities"]
