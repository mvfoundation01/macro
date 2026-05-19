"""Compute the 3 BI variants (AllEquity, Wilshire, SPX-proxy) from aligned data.

Per Spec v4.1, ``bi_spx_proxy`` is mean-matched to ``bi_wilshire_pct`` over the
two series' common window. This preserves z-scores and percentiles (which are
scale-invariant) while putting the SPX-proxy on a comparable interpretable
level so a dashboard can show all three variants in the same units.
"""
from __future__ import annotations

import pandas as pd


def compute_bi_variants(aligned: pd.DataFrame) -> dict[str, pd.Series]:
    """Compute three BI variants from the aligned monthly DataFrame.

    Required columns in ``aligned``:
        gdp_t           -- GDP USD trillions (annualized SAAR)
        equities_all_t  -- all-domestic-sectors corporate equities USD T
        wilshire_usd_t  -- Wilshire 5000 in USD trillions (after scaling)
        spx             -- S&P 500 index level (unconverted)

    Output dict (keys present only when the underlying columns are):
        bi_allequity_pct -- equities_all / gdp x 100
        bi_wilshire_pct  -- wilshire_usd_t / gdp x 100
        bi_spx_proxy     -- (spx / gdp_t x 100) rescaled by a constant k so the
                            historical mean matches ``bi_wilshire_pct`` over
                            the two series' common window. Scale-invariant
                            statistics (z, percentile) are unchanged by the
                            rescale; only the absolute level is shifted to
                            something interpretable. The rescale factor and
                            anchor description are stored on
                            ``bi_spx_proxy.attrs``.
    """
    out: dict[str, pd.Series] = {}
    cols = set(aligned.columns)

    if {"equities_all_t", "gdp_t"} <= cols:
        s = (aligned["equities_all_t"] / aligned["gdp_t"] * 100.0).dropna()
        s.name = "bi_allequity_pct"
        out["bi_allequity_pct"] = s

    if {"wilshire_usd_t", "gdp_t"} <= cols:
        s = (aligned["wilshire_usd_t"] / aligned["gdp_t"] * 100.0).dropna()
        s.name = "bi_wilshire_pct"
        out["bi_wilshire_pct"] = s

    if {"spx", "gdp_t"} <= cols:
        bi_spx_raw = (aligned["spx"] / aligned["gdp_t"] * 100.0).dropna()
        bi_spx_raw.name = "bi_spx_proxy"

        if "bi_wilshire_pct" in out:
            wilshire = out["bi_wilshire_pct"]
            common = bi_spx_raw.index.intersection(wilshire.index)
            if len(common) >= 60:
                wilshire_mean = float(wilshire.loc[common].mean())
                spx_raw_mean = float(bi_spx_raw.loc[common].mean())
                if spx_raw_mean > 0:
                    k = wilshire_mean / spx_raw_mean
                    bi_spx_scaled = (bi_spx_raw * k).copy()
                    bi_spx_scaled.name = "bi_spx_proxy"
                    bi_spx_scaled.attrs["scale_factor_vs_raw"] = float(k)
                    bi_spx_scaled.attrs["scale_anchor"] = (
                        "mean-match BI-Wilshire over common window"
                    )
                    bi_spx_scaled.attrs["common_window_n"] = int(len(common))
                    out["bi_spx_proxy"] = bi_spx_scaled
                else:
                    out["bi_spx_proxy"] = bi_spx_raw
                    out["bi_spx_proxy"].attrs["scale_factor_vs_raw"] = 1.0
                    out["bi_spx_proxy"].attrs["scale_anchor"] = (
                        "raw (BI-Wilshire mean over overlap is non-positive)"
                    )
            else:
                out["bi_spx_proxy"] = bi_spx_raw
                out["bi_spx_proxy"].attrs["scale_factor_vs_raw"] = 1.0
                out["bi_spx_proxy"].attrs["scale_anchor"] = (
                    "raw (insufficient overlap for scaling)"
                )
        else:
            out["bi_spx_proxy"] = bi_spx_raw
            out["bi_spx_proxy"].attrs["scale_factor_vs_raw"] = 1.0
            out["bi_spx_proxy"].attrs["scale_anchor"] = (
                "raw (no BI-Wilshire to anchor against)"
            )

    return out


__all__ = ["compute_bi_variants"]
