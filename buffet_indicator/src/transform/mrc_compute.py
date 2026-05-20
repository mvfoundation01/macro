"""v11.0 Macro Risk Composite (MRC).

MRC aggregates 7 macro indicators -- 2 yield curve spreads, 4 credit spreads,
1 margin debt growth -- into a single z-score using the same three weighting
schemes that MVCI uses for valuation:

    equal_weight     : MRC_t = mean(z_i,t)
    inv_variance     : MRC_t = sum(w_i * z_i,t),  w_i ~ 1/Var_expanding(z_i)
    pca_pc1          : MRC_t = sum(loadings_t[i] * z_i,t)

The scheme functions are reused unchanged from :mod:`src.transform.mvci_compute`;
this module is responsible only for assembling the constituent z_panel from
the raw signal series of each macro indicator.

Per the spec PART 10 §10:
- Each indicator's ``signal`` column already encodes the canonical
  HIGH = BEARISH direction (yield curve negated, credit spreads log, margin
  debt 12M log growth), so we apply the same expanding-window robust
  z-score to all 7 without per-variant handling.
- The acceptance gate is corr(MVCI, MRC) < 0.8 over the common window
  (verified externally in tests; MRC is supposed to add independent
  information, not just restate the valuation signal).
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.models.zscore import expanding_zscore
from src.transform.credit_spread_compute import compute_all_credit_spreads
from src.transform.margin_debt_compute import compute_margin_debt_growth
from src.transform.mvci_compute import (
    equal_weight_mvci,
    inv_variance_mvci,
    pca_pc1_mvci,
)
from src.transform.yield_curve_compute import compute_all_yield_curves


MRC_CONSTITUENTS: tuple[str, ...] = (
    "yc_10y3m",
    "yc_10y2y",
    "cs_hy_master",
    "cs_ig_master",
    "cs_hy_bb",
    "cs_hy_ccc",
    "margin_debt_growth",
)


def _signals_to_panel(
    signals: dict[str, pd.Series],
    *,
    min_periods: int = 60,
) -> pd.DataFrame:
    """Convert each indicator's signal series into an expanding-window z-score.

    The robust scale estimator is Huber (the default for MVCI).
    Constituents missing from ``signals`` are simply absent from the panel
    (best-effort: MRC can compute with a subset).
    """
    z_columns: dict[str, pd.Series] = {}
    for key, sig in signals.items():
        if sig is None or sig.empty:
            continue
        z = expanding_zscore(
            sig.dropna(), min_periods=min_periods, scale_method="huber"
        )
        z.name = key
        z_columns[key] = z
    if not z_columns:
        return pd.DataFrame()
    panel = pd.concat(z_columns.values(), axis=1).sort_index()
    return panel


def _signal_from_compute_outputs(
    yield_curves: dict[str, pd.DataFrame],
    credit_spreads: dict[str, pd.DataFrame],
    margin_debt: pd.DataFrame | None,
) -> dict[str, pd.Series]:
    """Assemble the raw signal series (one per constituent)."""
    sigs: dict[str, pd.Series] = {}
    for key, df in yield_curves.items():
        sigs[key] = df["signal"].astype("float64")
    for key, df in credit_spreads.items():
        sigs[key] = df["signal"].astype("float64")
    if margin_debt is not None and "signal" in margin_debt.columns:
        sigs["margin_debt_growth"] = margin_debt["signal"].astype("float64")
    return sigs


def compute_mrc(
    *,
    api_key: str | None = None,
    min_periods: int = 60,
    raw_signals: dict[str, pd.Series] | None = None,
) -> dict[str, Any]:
    """Compute the Macro Risk Composite from the 7 macro indicators.

    Parameters
    ----------
    api_key : str | None
        FRED API key (required for ``yc_10y2y``; without it the panel will
        have 6 of 7 constituents).
    min_periods : int
        Minimum observations before expanding-window z-scores are emitted.
    raw_signals : dict | None
        Optional override for testing -- if supplied, bypasses the
        :func:`compute_*` calls below and uses the provided signals directly.

    Returns
    -------
    dict
        ``{"constituents": list[str], "z_panel": pd.DataFrame, "schemes":
        {"equal_weight": {...}, "inv_variance": {...}, "pca_pc1": {...}}}``
    """
    if raw_signals is None:
        yc = compute_all_yield_curves(api_key=api_key)
        cs = compute_all_credit_spreads()
        try:
            md = compute_margin_debt_growth()
        except Exception:  # pragma: no cover - best-effort
            md = None
        raw_signals = _signal_from_compute_outputs(yc, cs, md)

    z_panel = _signals_to_panel(raw_signals, min_periods=min_periods)
    z_aligned = z_panel.dropna(how="all")

    schemes: dict[str, dict[str, Any]] = {}
    if not z_aligned.empty:
        schemes["equal_weight"] = equal_weight_mvci(z_aligned)
        schemes["inv_variance"] = inv_variance_mvci(z_aligned, min_periods=min_periods)
        schemes["pca_pc1"] = pca_pc1_mvci(z_aligned, min_periods=min_periods)

    return {
        "constituents": list(z_aligned.columns),
        "z_panel": z_aligned,
        "schemes": schemes,
    }


def latest_mrc_z(result: dict[str, Any], *, scheme: str = "equal_weight") -> float:
    """Convenience accessor: latest MRC z-score for the named scheme."""
    sch = result.get("schemes", {}).get(scheme)
    if sch is None:
        return float("nan")
    return float(sch.get("z_score", float("nan")))


def correlation_with(other_z: pd.Series, result: dict[str, Any], *, scheme: str = "equal_weight") -> float:
    """Pearson correlation between MRC[scheme] series and another z-series.

    Used by the acceptance gate that MRC ≠ MVCI (corr < 0.8).
    """
    mrc_series = result["schemes"][scheme]["z_score_series"].dropna()
    common = mrc_series.index.intersection(other_z.dropna().index)
    if len(common) < 24:
        return float("nan")
    return float(mrc_series.loc[common].corr(other_z.loc[common]))


__all__ = [
    "MRC_CONSTITUENTS",
    "compute_mrc",
    "latest_mrc_z",
    "correlation_with",
]
