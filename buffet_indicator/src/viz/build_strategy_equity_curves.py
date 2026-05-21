"""v11.2.2 B3 — cumulative equity curves for the Strategy Engine top chart.

Builds a JSON-serializable dict containing the cumulative growth of $10,000
invested 2000-08-31 (V1 Combination start date) in:
    - V1_Combination (from v50 monthly returns CSV)
    - V2_R-PRIMARY / V2_R-ALT1 / V2_R-ALT2 (from mv_conditional)
    - SPY (proxy: Shiller SP500 price + dividend → total-return monthly)

EW is currently OMITTED — v50 doesn't yet emit per-month EW returns; spec §A.5.2
allows surfacing as "see methodology" until v50 export is added. See REVIEW_PACKAGE.

Returns ``None`` when the upstream CSVs aren't present (Strategy Engine tab
also degrades gracefully in that case).
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


REPO_ROOT = Path(__file__).resolve().parents[2]
INITIAL_CAPITAL = 10_000.0


def _compute_spy_monthly_returns(start: pd.Timestamp) -> pd.Series:
    """Shiller SP500 monthly total return ≈ (price + dividend) / price[-1] − 1.

    Shiller's ``real_total_return`` is the canonical reinvested-dividend index
    (real). We derive nominal monthly returns from its month-on-month change
    plus inflation. For SPY-as-benchmark visual purposes this is precise enough;
    we deliberately avoid pulling Norgate SPY data here to keep this path
    dependency-free.
    """
    from src.ingest.shiller_loader import load_shiller

    sh = load_shiller()
    df = sh.data
    # Real total-return is the inflation-adjusted dividend-reinvested index.
    # To get NOMINAL monthly returns we add CPI inflation.
    rtr = df["real_total_return"].astype("float64").dropna().sort_index()
    cpi = df["cpi"].astype("float64").dropna().sort_index()
    nominal_idx = (rtr * cpi).dropna()
    # Snap index to month-end.
    nominal_idx.index = pd.DatetimeIndex(nominal_idx.index).to_period("M").to_timestamp(how="end").normalize()
    nominal_idx = nominal_idx[~nominal_idx.index.duplicated(keep="last")]
    ret = nominal_idx.pct_change().dropna()
    ret = ret[ret.index >= start]
    ret.name = "SPY_proxy"
    return ret


def _to_equity(returns: pd.Series, base_date: pd.Timestamp) -> pd.Series:
    """Cumulative $10k equity starting at base_date."""
    r = returns.copy()
    r = r[r.index >= base_date]
    if r.empty:
        return pd.Series(dtype="float64")
    # Insert base_date with 0 return so equity = $10k at base_date.
    if r.index[0] > base_date:
        r = pd.concat([pd.Series([0.0], index=[base_date]), r]).sort_index()
    nav = INITIAL_CAPITAL * (1.0 + r).cumprod()
    return nav


def build_strategy_equity_curves() -> dict | None:
    """Returns the JSON payload for DATA.strategy_equity_curves, or None on failure."""
    try:
        from src.quant_engine.mv_conditional import (
            RULE_REGISTRY,
            apply_mv_conditional,
            load_combo_monthly_returns,
            load_mvci_mrc_zscores_monthly,
            load_tbill_monthly_return,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("strategy_equity_curves: import failed (%s)", exc)
        return None

    try:
        v1 = load_combo_monthly_returns(period_label="FULL", costbps=15)
    except FileNotFoundError as exc:
        logger.warning("strategy_equity_curves: V1 returns missing (%s)", exc)
        return None

    base_date = v1.index.min().normalize()

    try:
        z = load_mvci_mrc_zscores_monthly()
        tbill = load_tbill_monthly_return()
    except Exception as exc:  # noqa: BLE001
        logger.warning("strategy_equity_curves: V2 dependencies missing (%s)", exc)
        z = None
        tbill = None

    v2_returns: dict[str, pd.Series] = {}
    if z is not None and tbill is not None:
        for rule_name, rule_fn in RULE_REGISTRY.items():
            try:
                # ALT1 only consumes z_mvci.
                if rule_name == "R-ALT1":
                    weights = rule_fn(z["z_mvci"])
                else:
                    weights = rule_fn(z["z_mvci"], z["z_mrc"])
                v2_returns[f"V2_{rule_name}"] = apply_mv_conditional(v1, weights, tbill)
            except Exception as exc:  # noqa: BLE001
                logger.warning("strategy_equity_curves: V2 %s failed (%s)", rule_name, exc)

    try:
        spy = _compute_spy_monthly_returns(base_date)
    except Exception as exc:  # noqa: BLE001
        logger.warning("strategy_equity_curves: SPY proxy failed (%s)", exc)
        spy = None

    # Build the unified date index = union of all series snapped to month-end.
    indices = [v1.index] + [s.index for s in v2_returns.values()]
    if spy is not None and not spy.empty:
        indices.append(spy.index)
    all_dates = pd.DatetimeIndex(sorted(set().union(*[set(i) for i in indices])))
    all_dates = all_dates[all_dates >= base_date]

    out: dict[str, list] = {"dates": [d.strftime("%Y-%m-%d") for d in all_dates]}

    def _series_to_list(s: pd.Series) -> list:
        nav = _to_equity(s, base_date).reindex(all_dates)
        return [None if (v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v)))) else round(float(v), 2)
                for v in nav.values]

    out["V1_Combination"] = _series_to_list(v1)
    for name, s in v2_returns.items():
        out[name] = _series_to_list(s)
    if spy is not None and not spy.empty:
        out["SPY"] = _series_to_list(spy)

    out["_metadata"] = {
        "initial_capital": INITIAL_CAPITAL,
        "start_date": base_date.strftime("%Y-%m-%d"),
        "end_date": all_dates[-1].strftime("%Y-%m-%d") if len(all_dates) else None,
        "n_months": len(all_dates),
        "series_emitted": [k for k in out.keys() if k not in ("dates", "_metadata")],
        "note": "EW currently OMITTED — v50 doesn't emit per-month EW returns; see methodology.",
    }
    return out


__all__ = ["build_strategy_equity_curves"]
