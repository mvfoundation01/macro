"""Mean Reversion valuation indicator (real S&P composite vs exponential trend).

CMV's iconic indicator: real (CPI-adjusted) S&P 500 composite plotted on a
log scale, with an exponential regression line through the full history.
Downstream ``trend_battery`` fits log-linear / HP / Bai-Perron trends on the
real-price series; the residuals are then z-scored exactly like the other
variants.

Conceptually distinct from ``bi_spx_proxy`` (SPX/GDP) -- this variant is
purely autoregressive (price vs its own long-run trend), no GDP anchor.
"""
from __future__ import annotations

import pandas as pd

from src.ingest._base import get_logger
from src.ingest.shiller_loader import ShillerData

logger = get_logger("buffett.transform.mean_reversion")


def compute_mean_reversion_variant(
    shiller_data: ShillerData,
) -> dict[str, pd.Series]:
    """Return the real S&P 500 composite as the Mean Reversion input series.

    Prefers Shiller's ``real_price`` column when available; otherwise
    reconstructs from nominal ``price_nominal`` and ``cpi``::

        real_price_t = price_nominal_t * CPI_latest / CPI_t

    (rebases to the latest CPI so the series ends at present-day dollars).

    Returns dict with key ``mean_reversion`` mapping to a monthly Series,
    1871-present.
    """
    df = shiller_data.data

    if "real_price" in df.columns and df["real_price"].notna().any():
        s = df["real_price"].dropna().astype("float64").copy()
    else:
        if "price_nominal" not in df.columns or "cpi" not in df.columns:
            logger.warning(
                "mean_reversion: neither real_price nor (price_nominal + cpi) "
                "available; returning empty dict"
            )
            return {}
        price = df["price_nominal"].dropna().astype("float64")
        cpi = df["cpi"].dropna().astype("float64")
        common = price.index.intersection(cpi.index)
        if common.empty:
            logger.warning(
                "mean_reversion: price/CPI series share no index; returning empty"
            )
            return {}
        price = price.loc[common]
        cpi = cpi.loc[common]
        cpi_latest = float(cpi.iloc[-1])
        s = price * cpi_latest / cpi

    s.name = "mean_reversion"
    # Normalise to month-end so downstream alignment is consistent with other
    # monthly Shiller-derived variants.
    s.index = (
        pd.DatetimeIndex(s.index)
        .to_period("M")
        .to_timestamp(how="end")
        .normalize()
    )
    s = s[s > 0]
    return {"mean_reversion": s}


__all__ = ["compute_mean_reversion_variant"]
