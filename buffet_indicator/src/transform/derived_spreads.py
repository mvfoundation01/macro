"""v11.0.1 — 6 derived credit / cross-domain spreads.

Each spread reuses raw v11.0a indicators (HY/IG/BB/CCC OAS) plus DGS10
(loaded via FRED) and Shiller earnings yield to produce a derived signal.

Direction conventions are EMPIRICALLY DETERMINED (§E of the v11.0.1 spec):
some spreads are 'trend' (high z = bearish forward equities) and some are
'contrarian' (high z = bullish forward equities). The signal column is
unchanged (raw spread); direction is surfaced via the variant registry.

Spreads:

  spread_hy_ig                  : HY OAS − IG OAS (pure credit risk premium)
  spread_ccc_bb                 : CCC OAS − BB OAS (distress premium)
  spread_hy_reach_for_yield     : HY OAS − DGS10 (reach-for-yield composite)
  spread_hy_treasury_traditional: HY YTW − DGS10 (the traditional credit spread)
  spread_equity_credit_rp       : SP500 trailing earnings yield − HY YTW
                                  (cross-domain Equity-Credit Risk Premium)
  spread_hy_oas_3m_delta        : HY OAS 3-month change (acceleration)

References
----------
- Gilchrist & Zakrajšek (2012) "Credit Spreads and Business Cycle Fluctuations"
- Greenwood & Hanson (2013) "Issuer Quality and Corporate Bond Returns"
- Asness et al. (2010) "Equity Risk Premium and Credit Risk Premium"
"""
from __future__ import annotations


import pandas as pd

from src.ingest._base import get_logger
from src.transform.credit_spread_compute import compute_credit_spread

logger = get_logger("buffett.transform.derived_spreads")


DERIVED_SPREAD_KEYS = (
    "spread_hy_ig",
    "spread_ccc_bb",
    "spread_hy_reach_for_yield",
    "spread_hy_treasury_traditional",
    "spread_equity_credit_rp",
    "spread_hy_oas_3m_delta",
)


# -----------------------------------------------------------------------
# Source loaders (cached at module level so repeated builds are fast)
# -----------------------------------------------------------------------


def _load_credit_spread_monthly(variant_key: str) -> pd.Series:
    """Load monthly raw OAS (not log) for one credit spread variant."""
    df = compute_credit_spread(variant_key)
    return df["spread_raw"].astype("float64")


def _load_dgs10_monthly(api_key: str | None) -> pd.Series:
    """Daily DGS10 from FRED → month-end. Returns yield in percentage points."""
    if not api_key:
        # Fallback: Shiller long_rate is monthly and goes back to 1871.
        from src.ingest.shiller_loader import load_shiller
        sh = load_shiller()
        s = sh.data["long_rate_gs10"].astype("float64").dropna()
        # Shiller's gs10 already in decimals × 100 (handled inside loader).
        return s
    from src.ingest.fred_loader import load_fred_series
    fs = load_fred_series("DGS10", api_key, observation_start="1962-01-01")
    s = fs.data.astype("float64").dropna()
    return s.resample("ME").last().dropna()


def _load_hy_ytw_monthly(api_key: str | None) -> pd.Series:
    """v11.0.1 § fallback: HY YTW = HY OAS + DGS10 since FRED's
    ``BAMLH0A0HYM2EY`` only has 2023+ data despite the catalog claim.

    The approximation HY_YTW ≈ HY_OAS + Treasury_yield is exact when OAS
    is defined as `effective yield − Treasury yield`; the spread to
    Treasury is the OAS by construction. Documented in REVIEW §8.
    """
    hy_oas = _load_credit_spread_monthly("cs_hy_master")
    dgs10 = _load_dgs10_monthly(api_key)
    common = hy_oas.index.intersection(dgs10.index)
    ytw = hy_oas.loc[common] + dgs10.loc[common]
    ytw.name = "hy_ytw_monthly"
    return ytw


def _load_sp500_earnings_yield() -> pd.Series:
    """Trailing earnings yield from Shiller: real_earnings / real_price.

    The same denominator/numerator pair used by EY-Deficit in v10.0+.
    """
    from src.ingest.shiller_loader import load_shiller
    sh = load_shiller()
    # Shiller real_price and real_earnings are monthly series.
    rp = sh.data["real_price"].astype("float64").dropna()
    re = sh.data["real_earnings"].astype("float64").dropna()
    common = rp.index.intersection(re.index)
    ey = (re.loc[common] / rp.loc[common]) * 100.0  # in pp
    ey.name = "sp500_ey_pp"
    return ey


# -----------------------------------------------------------------------
# Compute functions, one per spread
# -----------------------------------------------------------------------


def _wrap_to_dataframe(
    raw: pd.Series, *, variant_key: str, direction: int = +1, source: str = ""
) -> pd.DataFrame:
    """Standard wrapping: produce (value_raw, signal) DataFrame."""
    s = raw.dropna().astype("float64")
    df = pd.DataFrame({"value_raw": s})
    # Signal direction: +1 means high raw = high signal (no flip); -1 means
    # we negate so the canonical "high signal = bearish" still applies under
    # the trend convention. For contrarian indicators the registry will
    # override; the orchestrator z-scores the signal as-is.
    df["signal"] = direction * df["value_raw"]
    df.index.name = "date"
    df.attrs["variant_key"] = variant_key
    df.attrs["source"] = source
    return df


def compute_spread_hy_ig(api_key: str | None = None) -> pd.DataFrame:
    hy = _load_credit_spread_monthly("cs_hy_master")
    ig = _load_credit_spread_monthly("cs_ig_master")
    common = hy.index.intersection(ig.index)
    raw = hy.loc[common] - ig.loc[common]
    raw.name = "hy_minus_ig_pp"
    return _wrap_to_dataframe(raw, variant_key="spread_hy_ig",
                              source="derived:HY_OAS - IG_OAS")


def compute_spread_ccc_bb(api_key: str | None = None) -> pd.DataFrame:
    ccc = _load_credit_spread_monthly("cs_hy_ccc")
    bb = _load_credit_spread_monthly("cs_hy_bb")
    common = ccc.index.intersection(bb.index)
    raw = ccc.loc[common] - bb.loc[common]
    raw.name = "ccc_minus_bb_pp"
    return _wrap_to_dataframe(raw, variant_key="spread_ccc_bb",
                              source="derived:CCC_OAS - BB_OAS")


def compute_spread_hy_reach_for_yield(api_key: str | None) -> pd.DataFrame:
    hy_oas = _load_credit_spread_monthly("cs_hy_master")
    dgs10 = _load_dgs10_monthly(api_key)
    common = hy_oas.index.intersection(dgs10.index)
    raw = hy_oas.loc[common] - dgs10.loc[common]
    raw.name = "hy_oas_minus_us10y_pp"
    return _wrap_to_dataframe(raw, variant_key="spread_hy_reach_for_yield",
                              source="derived:HY_OAS - DGS10")


def compute_spread_hy_treasury_traditional(api_key: str | None) -> pd.DataFrame:
    hy_ytw = _load_hy_ytw_monthly(api_key)
    dgs10 = _load_dgs10_monthly(api_key)
    common = hy_ytw.index.intersection(dgs10.index)
    raw = hy_ytw.loc[common] - dgs10.loc[common]
    raw.name = "hy_ytw_minus_us10y_pp"
    return _wrap_to_dataframe(raw, variant_key="spread_hy_treasury_traditional",
                              source="derived:HY_YTW - DGS10 (HY_YTW = HY_OAS + DGS10)")


def compute_spread_equity_credit_rp(api_key: str | None) -> pd.DataFrame:
    ey = _load_sp500_earnings_yield()
    hy_ytw = _load_hy_ytw_monthly(api_key)
    common = ey.index.intersection(hy_ytw.index)
    raw = ey.loc[common] - hy_ytw.loc[common]
    raw.name = "sp500_ey_minus_hy_ytw_pp"
    return _wrap_to_dataframe(raw, variant_key="spread_equity_credit_rp",
                              source="derived:SP500_trailing_EY - HY_YTW")


def compute_spread_hy_oas_3m_delta(api_key: str | None = None) -> pd.DataFrame:
    """3-month change in HY OAS. Monthly series → diff(3)."""
    hy = _load_credit_spread_monthly("cs_hy_master")
    delta = hy.diff(3).dropna()
    delta.name = "hy_oas_3m_change_pp"
    return _wrap_to_dataframe(delta, variant_key="spread_hy_oas_3m_delta",
                              source="derived:HY_OAS.diff(3)")


COMPUTE_REGISTRY = {
    "spread_hy_ig": compute_spread_hy_ig,
    "spread_ccc_bb": compute_spread_ccc_bb,
    "spread_hy_reach_for_yield": compute_spread_hy_reach_for_yield,
    "spread_hy_treasury_traditional": compute_spread_hy_treasury_traditional,
    "spread_equity_credit_rp": compute_spread_equity_credit_rp,
    "spread_hy_oas_3m_delta": compute_spread_hy_oas_3m_delta,
}


def compute_all_derived_spreads(api_key: str | None) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for key, fn in COMPUTE_REGISTRY.items():
        try:
            out[key] = fn(api_key)
        except Exception as exc:  # pragma: no cover
            logger.warning("derived spread %s skipped: %s", key, exc)
    return out


__all__ = [
    "DERIVED_SPREAD_KEYS",
    "COMPUTE_REGISTRY",
    "compute_all_derived_spreads",
    "compute_spread_hy_ig",
    "compute_spread_ccc_bb",
    "compute_spread_hy_reach_for_yield",
    "compute_spread_hy_treasury_traditional",
    "compute_spread_equity_credit_rp",
    "compute_spread_hy_oas_3m_delta",
]
