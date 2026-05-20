"""v11.0b — Emit the 8 new macro-indicator tab templates.

Each template follows the 9-section structure from PROMPT_v11_0_b §C.1:

  1. Header strip (regime callout + 4 pills: z-score, P(neg 10Y), Confidence, Conviction)
  2. Hero chart
  3. 3-panel block (Panel A z-score TS, Panel B scatter, Panel C S&P regime)
  4. Horizon selector pills
  5. Predictive regression results table
  6. Conditional distribution panel
  7. Probability table
  8. Interpretation section
  9. About section

The MRC tab adds 5 special sub-sections.
"""
from __future__ import annotations

from pathlib import Path

TEMPLATE_DIR = Path("src/viz/templates")

INDICATORS = [
    {
        "key": "yc_10y3m",
        "label": "Yield Curve 10Y-3M",
        "data_source": "TradingView TVC_US10Y - TVC_US03MY (1954-present)",
        "direction_note": (
            "Signal is the negated spread. High signal = inverted curve = "
            "bearish for equities (every US recession since 1955 was "
            "preceded by an inversion)."
        ),
        "references": "Estrella & Mishkin (1998), Bauer & Mertens (2018)",
    },
    {
        "key": "yc_10y2y",
        "label": "Yield Curve 10Y-2Y",
        "data_source": "FRED T10Y2Y (1976-present)",
        "direction_note": (
            "Market-standard yield curve measure. More responsive to Fed "
            "policy expectations than 10Y-3M."
        ),
        "references": "Estrella & Mishkin (1998)",
    },
    {
        "key": "cs_hy_master",
        "label": "HY OAS (master)",
        "data_source": "FRED BAMLH0A0HYM2 (1996-12-present)",
        "direction_note": (
            "Log-transformed (OAS strictly positive). High = bearish. "
            "Peaked near 20pp in Nov 2008 and ~10pp in Mar 2020."
        ),
        "references": "ICE BofA OAS methodology",
    },
    {
        "key": "cs_ig_master",
        "label": "IG OAS (master)",
        "data_source": "FRED BAMLC0A0CM (1996-12-present)",
        "direction_note": (
            "Investment-grade credit; slower than HY but most sensitive to "
            "systemic banking stress."
        ),
        "references": "ICE BofA OAS methodology",
    },
    {
        "key": "cs_hy_bb",
        "label": "HY BB OAS",
        "data_source": "FRED BAMLH0A1HYBB (1996-12-present)",
        "direction_note": (
            "Best-quality bucket inside HY. When BB widens sharply, it "
            "signals broader bear-market repricing."
        ),
        "references": "ICE BofA OAS methodology",
    },
    {
        "key": "cs_hy_ccc",
        "label": "HY CCC OAS",
        "data_source": "FRED BAMLH0A3HYC (1996-12-present)",
        "direction_note": (
            "Lowest credit quality. Most volatile; peaked at ~44pp in 2008."
        ),
        "references": "ICE BofA OAS methodology",
    },
    {
        "key": "margin_debt_growth",
        "label": "Margin Debt 12M Growth",
        "data_source": "FINRA Customer Margin Balances (1997-01-present)",
        "direction_note": (
            "12-month log growth (not level). Growth >+30% marks late-cycle "
            "leverage frenzies (1999, 2007, 2021)."
        ),
        "references": "Schwab and Yardeni sentiment frameworks; FINRA monthly releases",
    },
    # v11.0.1 — 6 derived credit/cross-domain spreads.
    {
        "key": "spread_hy_ig",
        "label": "HY-IG Spread",
        "data_source": "Derived: BAMLH0A0HYM2 − BAMLC0A0CM (1996-12-present)",
        "direction_note": (
            "Pure credit risk premium — strips out the Treasury rate level. "
            "Trend convention: high spread = bearish equities."
        ),
        "references": "Gilchrist & Zakrajšek (2012)",
        "interpretation": (
            "The pure credit risk premium: how much extra yield investors "
            "demand for junk bonds over investment-grade, with Treasury "
            "duration stripped out. Historically widens to &gt;5pp during "
            "recessions and compresses below 2pp in late-cycle euphoria."
        ),
    },
    {
        "key": "spread_ccc_bb",
        "label": "CCC-BB Distress",
        "data_source": "Derived: BAMLH0A3HYC − BAMLH0A1HYBB (1996-12-present)",
        "direction_note": (
            "Distress premium within junk. Trend convention; lead time 3-6M "
            "before recession per Gilchrist-Zakrajšek 2012."
        ),
        "references": "Gilchrist & Zakrajšek (2012)",
        "interpretation": (
            "The distress premium within junk: how much wider CCC-rated "
            "yields are versus BB-rated. Historically leads recessions by "
            "3-6 months (Gilchrist–Zakrajšek 2012). Sharp widening signals "
            "late-cycle credit deterioration starting."
        ),
    },
    {
        "key": "spread_hy_reach_for_yield",
        "label": "HY Reach-for-Yield",
        "data_source": "Derived: HY OAS − DGS10 (1996-12-present)",
        "direction_note": (
            "v11.0.2: reclassified as CONTRARIAN. Composite reading "
            "(HY OAS minus 10Y Treasury yield), NOT a bond-math spread. "
            "LOW value = investors accepting credit risk for too little "
            "above cash = complacency = bearish forward equities; HIGH "
            "value = late-cycle stress = contrarian buy signal."
        ),
        "references": "Greenwood & Hanson (2013)",
        "interpretation": (
            "A composite reading combining HY credit risk premium with the "
            "prevailing Treasury rate level. Low values mean investors are "
            "accepting credit risk for very little compensation above cash — "
            "historically a complacency signal that precedes drawdowns."
        ),
    },
    {
        "key": "spread_hy_treasury_traditional",
        "label": "HY-Treasury (Trad.)",
        "data_source": "Derived: HY YTW − DGS10 (HY YTW = HY OAS + DGS10; 1996-12-present)",
        "direction_note": (
            "The longtermtrends 'Credit Spreads' standard. CONTRARIAN "
            "empirically: wide = trough/buy signal; tight = late-cycle "
            "complacency."
        ),
        "references": "longtermtrends.net Credit Spreads",
        "interpretation": (
            "The classic credit spread: how much more junk bonds yield "
            "versus 10-year Treasuries. Wide spreads historically marked "
            "recession troughs (good entry points for equities); tight "
            "spreads marked late-cycle complacency."
        ),
    },
    {
        "key": "spread_equity_credit_rp",
        "label": "Equity-Credit Risk Premium",
        "data_source": (
            "Derived: SP500 trailing earnings yield − HY YTW (1996-12-present)"
        ),
        "direction_note": (
            "Cross-domain bridge between MVCI and MRC. CONTRARIAN: deeply "
            "negative = equities expensive vs credit = bearish; near zero or "
            "positive = equities cheap vs credit = bullish."
        ),
        "references": "Asness et al. (2010); MV v11.0.1 cross-domain bridge",
        "interpretation": (
            "The cross-domain bridge: S&amp;P 500 earnings yield minus the "
            "high-yield bond yield. When negative, equities are paying you "
            "less than junk bonds for similar (or worse) drawdown risk. "
            "Reached −8pp at the 2000 dot-com peak and is currently negative."
        ),
    },
    {
        "key": "spread_hy_oas_3m_delta",
        "label": "HY OAS 3M Δ",
        "data_source": "Derived: HY OAS.diff(3) (1997-03-present)",
        "direction_note": (
            "Acceleration measure. Trend at 1M-6M horizons (positive Δ = "
            "stress building, dangerous); contrarian at 5Y-10Y (after a big "
            "Δ, you may already be near the trough)."
        ),
        "references": "MV master spec §11.0.1",
        "interpretation": (
            "The acceleration of credit stress: how much HY spreads have "
            "widened over the prior 3 months. Captures regime-switch "
            "dynamics that static levels miss. Lead-time strongest at 1M-3M; "
            "mean-reverts at 5Y-10Y horizons."
        ),
    },
]


HORIZON_PILLS = ["1m", "3m", "12m", "36m", "60m", "84m", "120m"]
HORIZON_LABELS = {
    "1m": "1MO", "3m": "3MO", "12m": "1YR",
    "36m": "3YR", "60m": "5YR", "84m": "7YR", "120m": "10YR",
}


INDICATOR_TEMPLATE = """\
{% import "_macros.html" as m %}
<section data-tab="__KEY__" data-tab-group="macro_risk" class="tab-content px-4 py-4">

  {% set v = variants.get("__KEY__") %}
  {% if not v %}
  <div class="rounded-lg border bg-white p-4 mb-6 shadow-sm">
    <p class="text-sm text-gray-500">No data for __LABEL__ (variant missing).</p>
  </div>
  {% else %}

  <!-- 1. Header strip -->
  <div class="rounded-lg border p-4 mb-4 bg-white"
       style="border-left: 4px solid {{ v.regime_color }};">
    <div class="text-sm text-gray-500 mb-1">__LABEL__</div>
    <div class="text-2xl font-bold mb-3">{{ v.regime }}</div>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div>
        <div class="text-xs text-gray-500">Z-score (long-run)</div>
        <div class="text-xl font-semibold">{{ v.z_fmt }}</div>
      </div>
      <div>
        <div class="text-xs text-gray-500">P(&lt; 5% 10Y CAGR)</div>
        <div class="text-xl font-semibold">{{ v.p_neg_fmt }}</div>
        <div class="text-xs text-gray-400">{{ v.p_neg_ci_fmt }}</div>
      </div>
      <div>
        <div class="text-xs text-gray-500">Confidence</div>
        <div class="text-xl font-semibold">{{ v.confidence_fmt }}</div>
      </div>
      <div>
        <div class="text-xs text-gray-500">Conviction</div>
        <div class="text-xl font-semibold">{{ v.conviction_fmt }} / 5</div>
      </div>
    </div>
  </div>

  <!-- 2. Hero chart -->
  <div class="rounded-lg border bg-white p-4 mb-6 shadow-sm chart-card">
    <h2 class="text-xl font-bold mb-1">__LABEL__ &mdash; full history</h2>
    <p class="text-sm text-gray-500 mb-3">
      Raw signal level on left axis; standardised z-score on right.
      NBER recession bands shaded.
    </p>
    <div id="hero-chart-__KEY__" class="hero-chart-container"></div>
  </div>

  {{ m.why_it_matters_card("__LABEL__", v.interpretation.why_it_matters) }}

  <!-- 3. Three-panel block -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
    <div class="rounded-lg border bg-white p-4 chart-card">
      <h3 class="text-md font-semibold mb-2">Panel A &mdash; Standardised signal</h3>
      <div id="__KEY__-panel-a" class="panel-chart-container"></div>
    </div>
    <div class="rounded-lg border bg-white p-4 chart-card">
      <h3 class="text-md font-semibold mb-2">Panel B &mdash; Z vs forward return</h3>
      <div id="__KEY__-panel-b" class="panel-chart-container"></div>
    </div>
    <div class="rounded-lg border bg-white p-4 chart-card">
      <h3 class="text-md font-semibold mb-2">Panel C &mdash; S&amp;P 500 by __LABEL__ regime</h3>
      <div id="__KEY__-panel-c" class="panel-chart-container"></div>
    </div>
  </div>

  <!-- 4. Horizon selector pills -->
  <div class="mb-4 flex flex-wrap gap-2">
    <span class="text-xs text-gray-500 self-center mr-2">Horizon:</span>
__HORIZON_PILLS__
  </div>

  <!-- 5. Predictive regression results table -->
  <div class="rounded-lg border bg-white p-4 mb-6">
    <h3 class="text-lg font-semibold mb-3">Predictive regression results</h3>
    <table class="text-sm w-full">
      <thead>
        <tr class="text-left text-gray-500 border-b">
          <th class="py-1 pr-3">Horizon</th>
          <th class="py-1 pr-3">&beta;</th>
          <th class="py-1 pr-3">SE_HH</th>
          <th class="py-1 pr-3">t_HH</th>
          <th class="py-1 pr-3">p</th>
          <th class="py-1 pr-3">R&sup2;_in</th>
          <th class="py-1 pr-3">R&sup2;_OOS</th>
          <th class="py-1 pr-3">n_obs</th>
          <th class="py-1 pr-3">Conviction</th>
        </tr>
      </thead>
      <tbody>
        {% for row in v.regression_rows %}
        <tr class="border-b text-xs">
          <td class="py-1 pr-3 font-medium">{{ row.horizon_label }}</td>
          <td class="py-1 pr-3">{{ row.beta_fmt }}</td>
          <td class="py-1 pr-3">{{ row.se_hh_fmt }}</td>
          <td class="py-1 pr-3">{{ row.t_hh_fmt }}</td>
          <td class="py-1 pr-3">{{ row.p_fmt }}</td>
          <td class="py-1 pr-3">{{ row.r2_in_fmt }}</td>
          <td class="py-1 pr-3">{{ row.r2_oos_fmt }}</td>
          <td class="py-1 pr-3">{{ row.n_obs }}</td>
          <td class="py-1 pr-3">{{ row.conviction_fmt }} / 5</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- 6. Conditional distribution panel -->
  <div class="rounded-lg border bg-white p-4 mb-6 chart-card">
    <h3 class="text-lg font-semibold mb-2">Conditional return distribution (current bucket)</h3>
    <p class="text-sm text-gray-500 mb-2">
      Empirical histogram of forward returns observed when this indicator was in
      the current quintile, overlaid with the parametric AIC-selected fit.
    </p>
    <div id="__KEY__-cond-dist" class="panel-chart-container"></div>
  </div>

  <!-- 7. Probability table -->
  <div class="rounded-lg border bg-white p-4 mb-6">
    <h3 class="text-lg font-semibold mb-3">Conditional outcome probabilities</h3>
    <table class="text-sm w-full">
      <thead>
        <tr class="text-left text-gray-500 border-b">
          <th class="py-1 pr-3">Horizon</th>
          <th class="py-1 pr-3">P(neg)</th>
          <th class="py-1 pr-3">CI95</th>
          <th class="py-1 pr-3">P(&lt; RF)</th>
          <th class="py-1 pr-3">P(&lt; 5%)</th>
          <th class="py-1 pr-3">P(&gt; 7%)</th>
        </tr>
      </thead>
      <tbody>
        {% for row in v.probability_rows %}
        <tr class="border-b text-xs">
          <td class="py-1 pr-3 font-medium">{{ row.horizon_label }}</td>
          <td class="py-1 pr-3">{{ row.p_neg_fmt }}</td>
          <td class="py-1 pr-3 text-gray-500">{{ row.p_neg_ci_fmt }}</td>
          <td class="py-1 pr-3">{{ row.p_below_rf_fmt }}</td>
          <td class="py-1 pr-3">{{ row.p_below_5_fmt }}</td>
          <td class="py-1 pr-3">{{ row.p_above_7_fmt }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- 8. Interpretation -->
  <div class="rounded-lg border bg-white p-4 mb-6">
    <h3 class="text-lg font-semibold mb-2">Interpretation</h3>
    <p class="text-sm leading-relaxed">__INTERPRETATION_TEXT__</p>
  </div>

  <!-- 9. About -->
  <div class="rounded-lg border bg-white p-4">
    <h3 class="text-lg font-semibold mb-2">About this indicator</h3>
    <p class="text-sm leading-relaxed">
      <strong>Source:</strong> __DATA_SOURCE__
    </p>
    <p class="text-sm leading-relaxed mt-2">
      <strong>Direction convention:</strong> __DIRECTION_NOTE__
    </p>
    <p class="text-sm leading-relaxed mt-2">
      <strong>Methodology:</strong> Daily series resampled to month-end. Z-score
      via expanding-window Huber on the canonical signal column. Predictive
      regression uses Hansen&ndash;Hodrick (1980) HAC standard errors as primary
      SE, with Newey&ndash;West (1987) as cross-check and Stambaugh (1999) bias
      correction for highly persistent regressors. OOS R&sup2; per
      Goyal&ndash;Welch (2008); Clark&ndash;West (2007) MSPE-adjusted statistic
      for nested-model comparison. Bootstrap CIs via Politis&ndash;Romano (1994)
      stationary bootstrap, 10,000 replications, seed=42. Sample-size penalty per
      master spec &sect;6.2 when n_obs &lt; 100.
    </p>
    <p class="text-sm leading-relaxed mt-2">
      <strong>References:</strong> __REFERENCES__
    </p>
  </div>

  {% endif %}
</section>
"""


MRC_TEMPLATE = """\
{% import "_macros.html" as m %}
<section data-tab="mrc" data-tab-group="macro_risk" class="tab-content px-4 py-4">

  {% set v = variants.get("mrc") %}
  {% if not v %}
  <div class="rounded-lg border bg-white p-4 mb-6 shadow-sm">
    <p class="text-sm text-gray-500">No data for MRC composite.</p>
  </div>
  {% else %}

  <!-- 1. Header strip -->
  <div class="rounded-lg border p-4 mb-4 bg-white"
       style="border-left: 4px solid {{ v.regime_color }};">
    <div class="text-sm text-gray-500 mb-1">MV Macro Risk Composite (MRC)</div>
    <div class="text-2xl font-bold mb-3">{{ v.regime }}</div>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div>
        <div class="text-xs text-gray-500">Z (equal weight, long-run)</div>
        <div class="text-xl font-semibold">{{ v.z_fmt }}</div>
      </div>
      <div>
        <div class="text-xs text-gray-500">P(&lt; 5% 10Y CAGR)</div>
        <div class="text-xl font-semibold">{{ v.p_neg_fmt }}</div>
        <div class="text-xs text-gray-400">{{ v.p_neg_ci_fmt }}</div>
      </div>
      <div>
        <div class="text-xs text-gray-500">Confidence</div>
        <div class="text-xl font-semibold">{{ v.confidence_fmt }}</div>
      </div>
      <div>
        <div class="text-xs text-gray-500">Conviction</div>
        <div class="text-xl font-semibold">{{ v.conviction_fmt }} / 5</div>
      </div>
    </div>
  </div>

  <!-- 2. Hero chart -->
  <div class="rounded-lg border bg-white p-4 mb-6 shadow-sm chart-card">
    <h2 class="text-xl font-bold mb-1">MRC composite z-score &mdash; full history</h2>
    <p class="text-sm text-gray-500 mb-3">
      Equal-weight composite of the 7 macro indicators. Inverse-variance and
      PCA-PC1 alternative weightings shown in the variant table below.
    </p>
    <div id="hero-chart-mrc" class="hero-chart-container"></div>
  </div>

  {{ m.why_it_matters_card("the Macro Risk Composite", v.interpretation.why_it_matters) }}

  <!-- C.3: cross-variant comparison table -->
  <div class="rounded-lg border bg-white p-4 mb-6">
    <h3 class="text-lg font-semibold mb-3">MRC weighting variants</h3>
    <table class="text-sm w-full">
      <thead>
        <tr class="text-left text-gray-500 border-b">
          <th class="py-1 pr-3">Scheme</th>
          <th class="py-1 pr-3">Z-score</th>
          <th class="py-1 pr-3">P(neg 10Y)</th>
          <th class="py-1 pr-3">CI95</th>
          <th class="py-1 pr-3">Confidence</th>
          <th class="py-1 pr-3">Conviction</th>
        </tr>
      </thead>
      <tbody>
        {% for row in v.mrc_variants %}
        <tr class="border-b text-xs">
          <td class="py-1 pr-3 font-medium">{{ row.scheme_label }}</td>
          <td class="py-1 pr-3">{{ row.z_fmt }}</td>
          <td class="py-1 pr-3">{{ row.p_neg_fmt }}</td>
          <td class="py-1 pr-3 text-gray-500">{{ row.p_neg_ci_fmt }}</td>
          <td class="py-1 pr-3">{{ row.confidence_fmt }}</td>
          <td class="py-1 pr-3">{{ row.conviction_fmt }} / 5</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- C.3: constituent contribution bar chart -->
  <div class="rounded-lg border bg-white p-4 mb-6 chart-card">
    <h3 class="text-lg font-semibold mb-2">Constituent contributions (current month)</h3>
    <div id="mrc-constituent-bars" class="panel-chart-container"></div>
  </div>

  <!-- 3. Three-panel block -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
    <div class="rounded-lg border bg-white p-4 chart-card">
      <h3 class="text-md font-semibold mb-2">Panel A &mdash; MRC z-score over time</h3>
      <div id="mrc-panel-a" class="panel-chart-container"></div>
    </div>
    <div class="rounded-lg border bg-white p-4 chart-card">
      <h3 class="text-md font-semibold mb-2">Panel B &mdash; MRC vs forward return</h3>
      <div id="mrc-panel-b" class="panel-chart-container"></div>
    </div>
    <div class="rounded-lg border bg-white p-4 chart-card">
      <h3 class="text-md font-semibold mb-2">Panel C &mdash; S&amp;P 500 by MRC regime</h3>
      <div id="mrc-panel-c" class="panel-chart-container"></div>
    </div>
  </div>

  <!-- C.3: rolling correlation heatmap -->
  <div class="rounded-lg border bg-white p-4 mb-6 chart-card">
    <h3 class="text-lg font-semibold mb-2">Constituent co-movement (rolling 60-month correlation)</h3>
    <div id="mrc-corr-heatmap" class="panel-chart-container"></div>
  </div>

  <!-- C.3: PCA scree plot -->
  <div class="rounded-lg border bg-white p-4 mb-6 chart-card">
    <h3 class="text-lg font-semibold mb-2">PCA variance explained</h3>
    <div id="mrc-pca-scree" class="panel-chart-container"></div>
  </div>

  <!-- C.3: cross-composite quadrant chart -->
  <div class="rounded-lg border bg-white p-4 mb-6 chart-card">
    <h3 class="text-lg font-semibold mb-2">Cross-composite quadrant (MVCI &times; MRC)</h3>
    <div id="mrc-cross-composite" class="panel-chart-container"></div>
    {% if v.cross_composite_current %}
    <p class="text-xs text-gray-500 mt-2">
      Currently in <strong>{{ v.cross_composite_current.quadrant_label }}</strong>:
      historical mean forward-10Y return = {{ v.cross_composite_current.mean_ret_fmt }}
      (n = {{ v.cross_composite_current.n_months }} months).
    </p>
    {% endif %}
  </div>

  <!-- 4. Horizon selector pills -->
  <div class="mb-4 flex flex-wrap gap-2">
    <span class="text-xs text-gray-500 self-center mr-2">Horizon:</span>
__HORIZON_PILLS__
  </div>

  <!-- 5. Predictive regression -->
  <div class="rounded-lg border bg-white p-4 mb-6">
    <h3 class="text-lg font-semibold mb-3">Predictive regression results (equal weight)</h3>
    <table class="text-sm w-full">
      <thead>
        <tr class="text-left text-gray-500 border-b">
          <th class="py-1 pr-3">Horizon</th>
          <th class="py-1 pr-3">&beta;</th>
          <th class="py-1 pr-3">SE_HH</th>
          <th class="py-1 pr-3">t_HH</th>
          <th class="py-1 pr-3">R&sup2;_in</th>
          <th class="py-1 pr-3">R&sup2;_OOS</th>
          <th class="py-1 pr-3">n_obs</th>
          <th class="py-1 pr-3">Conviction</th>
        </tr>
      </thead>
      <tbody>
        {% for row in v.regression_rows %}
        <tr class="border-b text-xs">
          <td class="py-1 pr-3 font-medium">{{ row.horizon_label }}</td>
          <td class="py-1 pr-3">{{ row.beta_fmt }}</td>
          <td class="py-1 pr-3">{{ row.se_hh_fmt }}</td>
          <td class="py-1 pr-3">{{ row.t_hh_fmt }}</td>
          <td class="py-1 pr-3">{{ row.r2_in_fmt }}</td>
          <td class="py-1 pr-3">{{ row.r2_oos_fmt }}</td>
          <td class="py-1 pr-3">{{ row.n_obs }}</td>
          <td class="py-1 pr-3">{{ row.conviction_fmt }} / 5</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- 6. Conditional distribution -->
  <div class="rounded-lg border bg-white p-4 mb-6 chart-card">
    <h3 class="text-lg font-semibold mb-2">Conditional return distribution</h3>
    <div id="mrc-cond-dist" class="panel-chart-container"></div>
  </div>

  <!-- 7. Probability table -->
  <div class="rounded-lg border bg-white p-4 mb-6">
    <h3 class="text-lg font-semibold mb-3">Conditional outcome probabilities</h3>
    <table class="text-sm w-full">
      <thead>
        <tr class="text-left text-gray-500 border-b">
          <th class="py-1 pr-3">Horizon</th>
          <th class="py-1 pr-3">P(neg)</th>
          <th class="py-1 pr-3">CI95</th>
          <th class="py-1 pr-3">P(&lt; RF)</th>
          <th class="py-1 pr-3">P(&lt; 5%)</th>
          <th class="py-1 pr-3">P(&gt; 7%)</th>
        </tr>
      </thead>
      <tbody>
        {% for row in v.probability_rows %}
        <tr class="border-b text-xs">
          <td class="py-1 pr-3 font-medium">{{ row.horizon_label }}</td>
          <td class="py-1 pr-3">{{ row.p_neg_fmt }}</td>
          <td class="py-1 pr-3 text-gray-500">{{ row.p_neg_ci_fmt }}</td>
          <td class="py-1 pr-3">{{ row.p_below_rf_fmt }}</td>
          <td class="py-1 pr-3">{{ row.p_below_5_fmt }}</td>
          <td class="py-1 pr-3">{{ row.p_above_7_fmt }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- 8. Interpretation -->
  <div class="rounded-lg border bg-white p-4 mb-6">
    <h3 class="text-lg font-semibold mb-2">Interpretation</h3>
    <p class="text-sm leading-relaxed">{{ v.interpretation.panel_a }}</p>
  </div>

  <!-- 9. About -->
  <div class="rounded-lg border bg-white p-4">
    <h3 class="text-lg font-semibold mb-2">About the MRC composite</h3>
    <p class="text-sm leading-relaxed">
      <strong>Construction:</strong> Equal-weight mean across 7 macro
      indicators (2 yield-curve spreads, 4 ICE BofA OAS series, 1 FINRA
      margin-debt 12M log-growth), each expanding-window Huber z-scored on its
      canonical signal column.
    </p>
    <p class="text-sm leading-relaxed mt-2">
      <strong>Alternative weightings:</strong> inverse-variance and PCA-PC1
      schemes are reported in the variant table above. PCA-PC1 typically
      explains &gt;60% of cross-constituent variance.
    </p>
    <p class="text-sm leading-relaxed mt-2">
      <strong>Independence from MVCI:</strong> Acceptance gate
      |corr(MVCI, MRC)| &lt; 0.85. The two composites measure fundamentally
      different dimensions: MVCI measures the price of equities; MRC measures
      the financial-system regime.
    </p>
    <p class="text-sm leading-relaxed mt-2">
      <strong>v11.0.2 composition disclosure:</strong> The current MRC
      composite includes 13 inputs: 7 raw indicators (yield curves,
      credit OAS, margin debt) plus 6 derived spreads. Five of the 6
      derived spreads are linear combinations or transforms of the raw
      inputs, so the v11.0.2 MRC correlates ~0.99 with the v11.0c
      version. The derived spreads serve as <em>diagnostic
      decomposition</em> for the user, not as orthogonal information
      for the ensemble. The exception is the Equity-Credit Risk Premium
      spread, which uniquely brings S&amp;P 500 earnings yield into the
      macro composite as a cross-domain bridge to MVCI.
    </p>
    <p class="text-sm leading-relaxed mt-2">
      <strong>References:</strong> Estrella &amp; Mishkin (1998),
      Goyal &amp; Welch (2008), Stambaugh (1999), Clark &amp; West (2007),
      Politis &amp; Romano (1994).
    </p>
  </div>

  {% endif %}
</section>
"""


def _emit_indicator_tab(info: dict) -> str:
    pills = "\n".join(
        f'      <button class="horizon-pill" data-horizon="{h}" '
        f'data-tab-target="{info["key"]}">{HORIZON_LABELS[h]}</button>'
        for h in HORIZON_PILLS
    )
    # v11.0.2 §D: per-indicator Interpretation text; falls back to the
    # v.interpretation.panel_a template variable when an indicator-specific
    # paragraph isn't defined in the generator dict.
    interpretation = info.get("interpretation", "{{ v.interpretation.panel_a }}")
    return (
        INDICATOR_TEMPLATE
        .replace("__KEY__", info["key"])
        .replace("__LABEL__", info["label"])
        .replace("__DATA_SOURCE__", info["data_source"])
        .replace("__DIRECTION_NOTE__", info["direction_note"])
        .replace("__REFERENCES__", info["references"])
        .replace("__INTERPRETATION_TEXT__", interpretation)
        .replace("__HORIZON_PILLS__", pills)
    )


def _emit_mrc_tab() -> str:
    pills = "\n".join(
        f'      <button class="horizon-pill" data-horizon="{h}" '
        f'data-tab-target="mrc">{HORIZON_LABELS[h]}</button>'
        for h in HORIZON_PILLS
    )
    return MRC_TEMPLATE.replace("__HORIZON_PILLS__", pills)


def main() -> None:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    for info in INDICATORS:
        path = TEMPLATE_DIR / f"tab_{info['key']}.html"
        path.write_text(_emit_indicator_tab(info), encoding="utf-8")
        print(f"wrote {path}")
    mrc_path = TEMPLATE_DIR / "tab_mrc.html"
    mrc_path.write_text(_emit_mrc_tab(), encoding="utf-8")
    print(f"wrote {mrc_path}")


if __name__ == "__main__":
    main()
