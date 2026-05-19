"""Plain-language captions + per-chart interpretations (Spec v8b §4).

v8b adds the three-block interpretation system:
  - what_this_shows: definition + data range + source
  - how_to_read: regime interpretation + historical context
  - current_reading: current value, percentile, regime, historical analog

Plus per-indicator "Why does this matter?" expandable copy.
"""
from __future__ import annotations

from typing import Any


REGIME_COLORS: dict[str, str] = {
    "Strongly Overvalued": "#C8102E",
    "Overvalued": "#E87722",
    "Fair Value": "#9AA0A6",
    "Undervalued": "#5DBB63",
    "Strongly Undervalued": "#1B7A3E",
    "Insufficient Data": "#000000",
}


def regime_color(regime_label: str) -> str:
    return REGIME_COLORS.get(regime_label, "#000000")


# ---------------------------------------------------------------------------
# Legacy short captions (kept for backwards compatibility with v8a templates)
# ---------------------------------------------------------------------------


PANEL_A_CAPTIONS: dict[str, str] = {
    "mvci": (
        "The MV Composite Index aggregates six valuation indicators into a single "
        "z-score. A reading above +1.5 standard deviations means the US stock "
        "market is currently more expensive than at most points in the past 75 "
        "years. Similar historical episodes preceded the 1929, 2000, and 2021 peaks."
    ),
    "bi_allequity_pct": (
        "Buffett's All-Equity ratio (total US corporate equities divided by GDP) "
        "is the broadest market-cap-to-GDP measure. High readings have "
        "historically been followed by lower forward returns."
    ),
    "bi_wilshire_pct": (
        "The Wilshire 5000 (the broadest US public equity index) divided by GDP. "
        "Closer to Buffett's original 'best single measure' framing but constrained "
        "to public companies."
    ),
    "bi_spx_proxy": (
        "S&P 500 level divided by GDP, mean-matched to the Wilshire 5000 ratio "
        "over their common window. Scale-invariant statistics are unchanged; only "
        "the absolute level is rescaled."
    ),
    "cape": (
        "Shiller's Cyclically Adjusted P/E ratio (P/E10): price divided by the "
        "10-year trailing average of real earnings. The textbook long-horizon "
        "predictor for US equities."
    ),
    "qratio": (
        "Tobin's Q-Ratio compares the market value of US nonfinancial corporate "
        "equity to the replacement cost of the underlying assets. Quarterly Z.1 "
        "data with monthly forward-fill."
    ),
    "ey_deficit": (
        "Equity Yield Deficit = real 10Y yield minus CAPE earnings yield. "
        "Positive readings mean bonds are more attractive than equities on a real "
        "yield basis; negative readings mean equities still earn more."
    ),
    "mean_reversion": (
        "Real (CPI-adjusted) S&P 500 deviation from its long-run exponential "
        "trend. The simplest valuation indicator: when the price-trend gap grows "
        "large, gravity has historically pulled it back."
    ),
}


PANEL_B_CAPTIONS: dict[str, str] = {
    "mvci": (
        "Each dot is a historical month. The x-axis is the MVCI z-score on that "
        "date; the y-axis is the actual 10-year annualized total return that "
        "followed. The downward slope indicates that high valuations have "
        "historically predicted lower forward returns."
    ),
    "default": (
        "Each dot is a historical month: x = the variant z-score at that date; "
        "y = the next 10-year annualized total-return CAGR. A negative slope "
        "indicates valuations have historically predicted lower forward returns."
    ),
}


PANEL_C_CAPTIONS: dict[str, str] = {
    "default": (
        "S&P 500 monthly close on a log scale. Each point is colored by the "
        "MVCI long-run regime at that date. The pattern shows how stretched "
        "valuations (red) and depressed valuations (green) have aligned with "
        "subsequent price action."
    ),
}


def panel_a_caption(variant_key: str) -> str:
    return PANEL_A_CAPTIONS.get(
        variant_key,
        "Z-score time series for this variant, with horizontal regime bands.",
    )


def panel_b_caption(variant_key: str) -> str:
    return PANEL_B_CAPTIONS.get(variant_key, PANEL_B_CAPTIONS["default"])


def panel_c_caption(variant_key: str = "mvci") -> str:
    return PANEL_C_CAPTIONS["default"]


def all_captions_for(variant_key: str) -> dict[str, str]:
    return {
        "panel_a": panel_a_caption(variant_key),
        "panel_b": panel_b_caption(variant_key),
        "panel_c": panel_c_caption(variant_key),
    }


# ===========================================================================
# v8b — per-chart 3-block interpretations
# ===========================================================================


def _historical_analog(percentile: float | None) -> str:
    """Return a short historical comparison string."""
    if percentile is None:
        return ""
    if percentile >= 98:
        return "Comparable peaks: 1929, 2000, 2021."
    if percentile >= 90:
        return "Few historical analogs; closest comps include 1929, 1965-66, 1999-2000, 2021."
    if percentile >= 75:
        return "Above-average valuations, but well short of the historical peaks."
    if percentile >= 25:
        return "Within the typical historical valuation range."
    if percentile >= 10:
        return "Cheaper than historical norms; comps include 1949, 1974, 1982, 2009."
    return "Among the cheapest readings in history; comps include 1932, 1949, 1974, 1982."


def mvci_hero_interpretation(
    z: float | None,
    regime: str,
    percentile: float | None,
) -> dict[str, str]:
    z_fmt = f"{z:+.2f}" if z is not None else "n/a"
    pct_fmt = f"{percentile:.0f}" if percentile is not None else "n/a"
    return {
        "what_this_shows": (
            "The MV Composite Index (MVCI) aggregates seven valuation indicators "
            "— Buffett Indicator (3 variants), CAPE, Tobin's Q, Equity Yield Deficit, "
            "and Mean Reversion — into a single z-score deviation from the long-run "
            "trend. Data is monthly back to 1881."
        ),
        "how_to_read": (
            "Values above +1σ (orange band) indicate overvaluation; above +2σ (red band) "
            "indicates extreme overvaluation similar to 1929, 2000, and 2021. Below −1σ "
            "(green band) indicates undervaluation; below −2σ (dark green) is rare and "
            "has historically preceded strong forward returns."
        ),
        "current_reading": (
            f"Currently {z_fmt}σ ({pct_fmt}th percentile) — **{regime}**. The market "
            f"is more expensive than at {pct_fmt}% of historical monthly observations "
            f"since 1881. {_historical_analog(percentile)}"
        ),
    }


def cape_hero_interpretation(
    value: float | None,
    z: float | None,
    percentile: float | None,
    regime: str,
) -> dict[str, str]:
    val_fmt = f"{value:.1f}" if value is not None else "n/a"
    z_fmt = f"{z:+.2f}" if z is not None else "n/a"
    pct_fmt = f"{percentile:.0f}" if percentile is not None else "n/a"
    return {
        "what_this_shows": (
            "Shiller's Cyclically Adjusted Price-to-Earnings ratio (CAPE / P/E10): "
            "the S&P 500 price divided by the 10-year trailing average of real earnings. "
            "Robert Shiller's iconic metric, computed monthly since 1881. Lower is cheaper."
        ),
        "how_to_read": (
            "Historical mean is roughly 17. Readings above 25 have historically preceded "
            "sub-par 10-year returns. Above 30 has only occurred three times in 145 years: "
            "1929 (peaked 32, then a −89% crash), 2000 (peaked 44, then −50%), and 2021 "
            "(peaked 38)."
        ),
        "current_reading": (
            f"CAPE = {val_fmt}, z = {z_fmt}σ, {pct_fmt}th percentile — **{regime}**. "
            f"This is one of the highest CAPE readings in history. Forward 10Y CAGR from "
            f"comparable starting points has historically averaged +1% to +3% real."
        ),
    }


def buffett_hero_interpretation(
    label: str,
    value: float | None,
    z: float | None,
    percentile: float | None,
    regime: str,
) -> dict[str, str]:
    val_fmt = f"{value:.1f}%" if value is not None else "n/a"
    z_fmt = f"{z:+.2f}" if z is not None else "n/a"
    pct_fmt = f"{percentile:.0f}" if percentile is not None else "n/a"
    return {
        "what_this_shows": (
            f"The {label} variant of the Buffett Indicator: total market capitalization "
            "divided by US GDP. Buffett called this measure 'probably the best single "
            "measure of where valuations stand at any given moment.' Higher means more "
            "expensive."
        ),
        "how_to_read": (
            "Below 75% has historically signaled undervaluation. Around 100% (one-to-one "
            "with GDP) is approximate fair value. Above 200% — where we are now — has "
            "occurred only in the late 1990s, 2021, and the present, all of which were "
            "followed by significant drawdowns."
        ),
        "current_reading": (
            f"Ratio = {val_fmt}, z = {z_fmt}σ, {pct_fmt}th percentile — **{regime}**. "
            f"US stocks are worth approximately {val_fmt} of annual GDP. "
            f"{_historical_analog(percentile)}"
        ),
    }


def qratio_hero_interpretation(
    value: float | None,
    z: float | None,
    percentile: float | None,
    regime: str,
) -> dict[str, str]:
    val_fmt = f"{value:.2f}" if value is not None else "n/a"
    z_fmt = f"{z:+.2f}" if z is not None else "n/a"
    pct_fmt = f"{percentile:.0f}" if percentile is not None else "n/a"
    return {
        "what_this_shows": (
            "Tobin's Q-Ratio compares the market value of US nonfinancial corporate "
            "equity to the replacement cost of the underlying assets. Quarterly data "
            "from the Fed's Z.1 Financial Accounts release, 1952-present, "
            "forward-filled to monthly frequency."
        ),
        "how_to_read": (
            "Q = 1.0 is theoretical equilibrium: paying exactly what it would cost to "
            "rebuild the businesses. Q > 1 means investors are paying above replacement "
            "cost (a premium). Historically, Q > 1.5 has preceded weak returns; the only "
            "comparable peak was 1999-2000."
        ),
        "current_reading": (
            f"Q = {val_fmt}, z = {z_fmt}σ, {pct_fmt}th percentile — **{regime}**. "
            f"Investors are paying about {val_fmt}× replacement cost for US equity. "
            f"{_historical_analog(percentile)}"
        ),
    }


def ey_deficit_hero_interpretation(
    value: float | None,
    z: float | None,
    percentile: float | None,
    regime: str,
) -> dict[str, str]:
    val_fmt = f"{value:.2f}%" if value is not None else "n/a"
    z_fmt = f"{z:+.2f}" if z is not None else "n/a"
    pct_fmt = f"{percentile:.0f}" if percentile is not None else "n/a"
    return {
        "what_this_shows": (
            "Equity Yield Deficit = real 10-year Treasury yield minus the CAPE earnings "
            "yield (1/CAPE). Compares the real return on long bonds against the equity "
            "earnings yield. Data uses Shiller's CAPE plus FRED's real yield series."
        ),
        "how_to_read": (
            "Positive readings mean Treasury real yields exceed the equity earnings "
            "yield, signaling bonds are relatively attractive. Negative readings mean "
            "equities still earn more than real bonds. The metric has been near zero "
            "for most of 2024-2025 — the first time bonds have been competitive since "
            "2002."
        ),
        "current_reading": (
            f"EY Deficit = {val_fmt}, z = {z_fmt}σ, {pct_fmt}th percentile — **{regime}**. "
            f"Real bonds and equity earnings yield are close to parity, an unusual "
            f"condition relative to history."
        ),
    }


def mean_reversion_hero_interpretation(
    deviation_pct: float | None,
    z: float | None,
    percentile: float | None,
    regime: str,
) -> dict[str, str]:
    dev_fmt = f"{deviation_pct:+.1f}%" if deviation_pct is not None else "n/a"
    z_fmt = f"{z:+.2f}" if z is not None else "n/a"
    pct_fmt = f"{percentile:.0f}" if percentile is not None else "n/a"
    return {
        "what_this_shows": (
            "Mean Reversion plots the inflation-adjusted S&P 500 against its long-term "
            "exponential growth trend (1871-present). The deviation between the real "
            "price and the fitted trend is the valuation signal."
        ),
        "how_to_read": (
            "Markets cluster around the long-run trend over multi-decade periods. The "
            "further the gap above the trend, the stronger the historical reversion "
            "pressure. Deviations above +100% are historically rare — 1929, 1999-2000, "
            "and the present (+150% to +180%)."
        ),
        "current_reading": (
            f"Currently {dev_fmt} above trend, z = {z_fmt}σ, {pct_fmt}th percentile — "
            f"**{regime}**. This is among the largest gaps in 150 years. "
            f"{_historical_analog(percentile)}"
        ),
    }


# ---------------------------------------------------------------------------
# Panel-level (3-block) interpretations
# ---------------------------------------------------------------------------


def panel_a_interpretation(variant_key: str, z: float | None, regime: str, percentile: float | None) -> dict[str, str]:
    z_fmt = f"{z:+.2f}" if z is not None else "n/a"
    pct_fmt = f"{percentile:.0f}" if percentile is not None else "n/a"
    return {
        "what_this_shows": (
            f"The historical z-score time series for the {variant_key} variant on its "
            "long-run frame. Each point is the standardized deviation from the long-run "
            "trend on that month. Coloured horizontal bands mark valuation regimes "
            "(red = strongly overvalued, green = strongly undervalued)."
        ),
        "how_to_read": (
            "Use the range buttons (1Y/5Y/10Y/30Y/All) above the chart, or drag the slider "
            "at the bottom to zoom into specific episodes. Hover over any point to see "
            "the z-score, regime, and historical percentile rank for that month."
        ),
        "current_reading": (
            f"The current reading is {z_fmt}σ ({pct_fmt}th percentile of all historical "
            f"months), which classifies as **{regime}**."
        ),
    }


def panel_b_interpretation(variant_key: str, beta: float | None, r_squared: float | None, t_nw: float | None) -> dict[str, str]:
    beta_fmt = f"{beta:+.3f}" if beta is not None else "n/a"
    r2_fmt = f"{r_squared:.2f}" if r_squared is not None else "n/a"
    tnw_fmt = f"{t_nw:+.2f}" if t_nw is not None else "n/a"
    return {
        "what_this_shows": (
            "A scatter plot of historical z-scores (x-axis) against the subsequent "
            "10-year annualized total return (y-axis). Each point is one historical "
            "month, colored by year (Turbo colorscale, dark = old, bright = recent). "
            "The dashed red line is the OLS fit; the dotted black vertical line marks "
            "today's z."
        ),
        "how_to_read": (
            f"A negative slope means high valuations have historically predicted lower "
            f"forward returns. The OLS slope (β) is {beta_fmt}, R² = {r2_fmt}, "
            f"Newey-West t = {tnw_fmt}. Strong |t| (typically > 2) signals the "
            f"relationship is unlikely to be due to chance."
        ),
        "current_reading": (
            "Look where the dotted vertical line crosses the dashed regression line — "
            "that intercept is the model's central 10Y CAGR estimate. The vertical "
            "spread of historical points at the same x level shows the realized "
            "outcome range."
        ),
    }


def panel_c_interpretation() -> dict[str, str]:
    return {
        "what_this_shows": (
            "S&P 500 monthly close on a log scale, with each segment colored by the "
            "MVCI regime in force that month. Red runs (overvalued) often precede "
            "drawdowns; green runs (undervalued) often precede recoveries."
        ),
        "how_to_read": (
            "Pattern recognition: long sequences of red typically transition into "
            "drawdown peaks (1929, 2000, 2007, 2021). Long sequences of green tend "
            "to follow major lows (1932, 1949, 1974, 1982, 2009). Hover over any "
            "point to see the price level and the regime for that date."
        ),
        "current_reading": (
            "The right edge of the chart shows the current regime. Look at the most "
            "recent sequence of regime colors to gauge how persistent the current "
            "valuation environment has been."
        ),
    }


# ---------------------------------------------------------------------------
# "Why does this matter?" expandable copy (per indicator)
# ---------------------------------------------------------------------------


WHY_IT_MATTERS: dict[str, str] = {
    "mvci": (
        "The MV Composite Index aggregates evidence across seven independent valuation "
        "metrics. Any single indicator can be misled by composition shifts (CAPE in a "
        "buyback-heavy regime, Q in a software-asset-light economy), but when six or "
        "seven independent measures agree, the signal is robust. The MVCI's first PCA "
        "component typically explains 70-90% of the variance across constituents, "
        "validating that they share a common latent valuation factor. Predictive R² "
        "for 10-year CAGR is roughly 0.40 — the strongest of any single valuation "
        "indicator in the literature."
    ),
    "cape": (
        "CAPE addresses the biggest weakness of traditional P/E: earnings volatility. "
        "A company that just had a bad year looks expensive on P/E even if it's "
        "fundamentally cheap. By averaging 10 years of real earnings, CAPE smooths the "
        "cycle and reveals the true price you're paying for a long-run earnings stream. "
        "Shiller's research (Nobel Prize 2013) shows CAPE is one of the strongest "
        "long-horizon predictors of stock returns ever discovered: high CAPE today → "
        "low returns over the next 10 years, with R² around 0.30."
    ),
    "buffett": (
        "Warren Buffett called it 'probably the best single measure of where valuations "
        "stand at any given moment.' It compares total stock market value to GDP — the "
        "total economic output the businesses listed on the market produce from. When "
        "the ratio is above 100%, stocks are worth more than the entire economy "
        "generates in a year; above 200% (where we are) means stocks are valued at "
        "more than 2× annual GDP, which is historically extreme. Three Buffett "
        "variants (All-Equity, Wilshire, SPX proxy) trade coverage breadth for series "
        "length."
    ),
    "qratio": (
        "Tobin's Q-Ratio compares the market value of corporate equity to the "
        "replacement cost of the underlying assets. At Q = 1, the market is paying "
        "exactly what it would cost to rebuild every business; above Q = 1, investors "
        "are paying a premium, which historically requires either elevated future "
        "growth or compressed risk premia. The ratio comes from the Fed's Z.1 "
        "Financial Accounts and was popularized by Andrew Smithers; it has a strong "
        "and persistent relationship with subsequent long-horizon equity returns."
    ),
    "ey_deficit": (
        "The Equity Yield Deficit compares the real return on long Treasuries against "
        "the CAPE earnings yield. When real bond yields exceed the equity earnings "
        "yield (positive deficit), bonds offer a competitive return without equity "
        "risk — historically a contractionary force for stock multiples. The metric "
        "captures the cross-asset opportunity cost that is missing from any "
        "stock-only valuation indicator (CAPE, Q, Buffett), and is particularly "
        "useful in the post-2022 high-rate regime."
    ),
    "mean_reversion": (
        "The simplest valuation indicator: how far is the inflation-adjusted S&P 500 "
        "above its long-term exponential growth trend? Markets historically cluster "
        "around this trend over very long periods — the further away, the stronger "
        "the 'gravitational pull' back. Currently +150-180% above trend is among the "
        "largest gaps in 150 years. The metric is purely autoregressive: it uses no "
        "earnings, dividends, or balance-sheet data; just price and inflation."
    ),
}


def why_it_matters(indicator_key: str) -> str:
    return WHY_IT_MATTERS.get(indicator_key, "")


# ---------------------------------------------------------------------------
# Aggregate accessor used by build_dashboard
# ---------------------------------------------------------------------------


def all_interpretations_for(
    variant_key: str,
    *,
    value: float | None = None,
    z: float | None = None,
    percentile: float | None = None,
    regime: str = "Insufficient Data",
    beta: float | None = None,
    r_squared: float | None = None,
    t_nw: float | None = None,
    mr_deviation_pct: float | None = None,
    buffett_label: str = "",
) -> dict[str, Any]:
    """Build the full interpretation bundle for one variant.

    Returns:
        {
            "hero": {what_this_shows, how_to_read, current_reading},
            "panel_a": {...},
            "panel_b": {...},
            "panel_c": {...},
            "why_it_matters": "..."  # paragraph (HTML escapable)
        }
    """
    if variant_key == "mvci":
        hero = mvci_hero_interpretation(z, regime, percentile)
        why_key = "mvci"
    elif variant_key == "cape":
        hero = cape_hero_interpretation(value, z, percentile, regime)
        why_key = "cape"
    elif variant_key.startswith("bi_"):
        hero = buffett_hero_interpretation(buffett_label or variant_key, value, z, percentile, regime)
        why_key = "buffett"
    elif variant_key == "qratio":
        hero = qratio_hero_interpretation(value, z, percentile, regime)
        why_key = "qratio"
    elif variant_key == "ey_deficit":
        hero = ey_deficit_hero_interpretation(value, z, percentile, regime)
        why_key = "ey_deficit"
    elif variant_key == "mean_reversion":
        hero = mean_reversion_hero_interpretation(mr_deviation_pct, z, percentile, regime)
        why_key = "mean_reversion"
    else:
        hero = mvci_hero_interpretation(z, regime, percentile)
        why_key = variant_key

    return {
        "hero": hero,
        "panel_a": panel_a_interpretation(variant_key, z, regime, percentile),
        "panel_b": panel_b_interpretation(variant_key, beta, r_squared, t_nw),
        "panel_c": panel_c_interpretation(),
        "why_it_matters": why_it_matters(why_key),
    }


__all__ = [
    "REGIME_COLORS",
    "regime_color",
    "PANEL_A_CAPTIONS",
    "PANEL_B_CAPTIONS",
    "PANEL_C_CAPTIONS",
    "panel_a_caption",
    "panel_b_caption",
    "panel_c_caption",
    "all_captions_for",
    "mvci_hero_interpretation",
    "cape_hero_interpretation",
    "buffett_hero_interpretation",
    "qratio_hero_interpretation",
    "ey_deficit_hero_interpretation",
    "mean_reversion_hero_interpretation",
    "panel_a_interpretation",
    "panel_b_interpretation",
    "panel_c_interpretation",
    "why_it_matters",
    "WHY_IT_MATTERS",
    "all_interpretations_for",
]
