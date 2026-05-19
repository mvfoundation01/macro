# REVIEW_PACKAGE_v8a.1 — Critical Visual Patch (Hero Charts + Mean Reversion)

Generated: 2026-05-18 (UTC). Working dir: `D:\macro\buffet_indicator`. Patch on v8a.

## 1 — Three deliverables, all green

| # | Deliverable | Status | Where to verify |
| --- | --- | --- | --- |
| A | Hero chart system on every tab | ✓ | 5 `id="hero-chart-*"` containers present in `outputs/dashboard.html` |
| B | Sparkline bug fix | ✓ | CSS rule `[id^="sparkline-"] { height: 60px; ... }` now correctly inlined (Jinja autoescape bug fixed); 6 sparkline DIVs rendered on Overview |
| C | Mean Reversion variant + tab + 7-constituent MVCI | ✓ | `mean_reversion` in `headline.variants`; `cross_variant_long_run.n_variants = 7`; dedicated tab with real S&P+trend hero chart |

## 2 — Root cause of the missing-sparklines bug

The v8a smoke produced HTML with the CSS attribute selector escaped:

```css
[id^=&#34;sparkline-&#34;] { height: 60px; ... }
```

Jinja2's default autoescape escaped the `"` characters even inside the `<style>` block. Browsers don't parse that selector → sparkline DIVs had 0px height → Plotly drew the line but the container clipped it to zero. Fix: mark `inline_css` and `inline_js` with `|safe` in `base.html` so the inlined content is preserved literally. Also added a defensive guard in `renderPlot()` that exits cleanly when the target DOM node is missing.

The fix is verified in this run: searching `outputs/dashboard.html` for `[id^="sparkline-"]` finds the literal rule (not `&#34;`).

## 3 — Hero chart system

A new `make_hero_chart()` in `src/viz/chart_specs.py` produces a scaled-up Panel A with:

- `height = 400` (vs 350 in v8a)
- Title + subtitle annotation
- Larger current-point marker (size 16, white outline) with text label
- Regime bands at 0.15 opacity (vs 0.10)
- Range selector defaults to "All"
- Plot/paper backgrounds transparent so dark mode inherits page colors

`make_mean_reversion_hero()` is the variant-specific hero for the new MR tab: two lines (real S&P + log-linear trend) on a log y-axis, with a centered annotation `Currently +181.0% from long-run trend` (red because deviation is positive).

Per-tab hero data is built in `build_hero_specs()` in `src/viz/data_extraction.py`, keyed by tab name (`overview`, `mvci`, `cape`, `buffett`→dict-of-sub-tabs, `mean_reversion`). The JS `renderHeroForTab()` routes to the right container on tab switch.

## 4 — Mean Reversion variant — module + numerics

`src/transform/mean_reversion_compute.py` (~50 LoC, 100% covered) extracts Shiller's `real_price` (or reconstructs from `price_nominal × CPI_latest / CPI_t` when `real_price` is missing). Series is monthly, month-end indexed, strictly positive, 1871-present.

The orchestrator now treats `mean_reversion` like any other variant:
- Full dual-frame analysis (log-linear on real-price → residuals → Huber z)
- Bai-Perron breaks on the log-real-price
- Forward-outlook regression vs primary FR (spliced TR)
- Full §6.3 conviction
- Added to `_CONSTITUENT_KEYS` so MVCI rebuilds with 7 constituents

### 4.1 Mean Reversion headline numbers (real data, 2026-05-31)

```
Real S&P 500           : 6,575.32
LR z-score (Huber)     : +2.106  (Strongly Overvalued)
LR percentile          : 99.6
Hero annotation         : "Currently +181.0% from long-run trend"
β (10Y forward CAGR)    : -0.0142
t_NW                    : -3.16
R²_OOS                  : 0.154
P(<5% CAGR)            : 47.2%
Full conviction (10Y)  : 3.27 / 5.00
```

Mean Reversion is the **only variant in the v8a.1 suite reading "Strongly Overvalued"** — its z exceeds +2.0σ where the other 6 sit in the +0.4 to +1.8 range. Independently of MVCI it's the strongest single-variant signal of stretched valuations.

## 5 — 8-variant headline (real data, 2026-05-31)

| # | Variant | Value | LR z | LR pct | LR regime |
|---|---|---:|---:|---:|---|
| 1 | bi_allequity_pct | 302.37% | +1.28 | 98.7 | Overvalued |
| 2 | bi_wilshire_pct  | 245.07% | +1.83 | 90.7 | Overvalued |
| 3 | bi_spx_proxy     | 237.61% | +1.74 | 100.0 | Overvalued |
| 4 | cape             | 36.48 | +1.22 | 93.4 | Overvalued |
| 5 | qratio           | 1.98 | +1.03 | 87.1 | Overvalued |
| 6 | ey_deficit       | -0.80% | +0.39 | 65.5 | Fair Value |
| 7 | **mean_reversion** | **6,575.32** | **+2.11** | **99.6** | **Strongly Overvalued** |
| 8 | mvci             | +1.79σ | +1.79 | 97.4 | Overvalued |

### MVCI schemes (now 7 constituents)

| Scheme | z_score | Notes |
|---|---:|---|
| equal_weight | +1.79 | Default headline (essentially unchanged from v7's +1.79 — MR adds modest orthogonal info) |
| inv_variance | +1.36 | Down-weighting BI-SPX, EY-Deficit; up-weighting MR slightly |
| pca_pc1 | +1.78 | PC1 explained variance **87.57%** |

### PCA explained variance comparison

| Spec | n constituents | PCA pc1 explained variance |
|---|---:|---:|
| v7 (no MR) | 6 | 0.872 |
| **v8a.1 (with MR)** | **7** | **0.876** |

Adding Mean Reversion did NOT lower the PCA explained variance (target was < 0.85). Reason: real S&P 500's log-linear residual is structurally similar to the BI-SPX-proxy variant's residual — both are price-driven and share the post-2010 surge. Spec §4.7 said "if still > 0.85, document and continue" — done. The constituents are mathematically related; further true orthogonality would require fundamentally different indicators (Crestmont P/E, asset-allocation surveys, sentiment), deferred to v9.

### Cross-variant LR

```
n_variants  : 7  (mean_reversion added, MVCI excluded)
mean_z      : +1.37
agreement   : 0.58
combined    : Overvalued
```

## 6 — Dashboard HTML structure verification

```
HTML size                            : 2,665,757 bytes (2.54 MB)

Tab markers (5 tabs × 2 occurrences each)
  data-tab="overview"                : 2 ✓
  data-tab="mvci"                    : 2 ✓
  data-tab="buffett"                 : 2 ✓
  data-tab="cape"                    : 2 ✓
  data-tab="mean_reversion"          : 2 ✓

Hero chart containers
  id="hero-chart-overview"           : YES
  id="hero-chart-mvci"               : YES
  id="hero-chart-buffett"            : YES
  id="hero-chart-cape"               : YES
  id="hero-chart-mean-reversion"     : YES

Sparkline DIVs on Overview cards
  sparkline-mvci                     : present
  sparkline-bi_allequity_pct         : present
  sparkline-bi_wilshire_pct          : present
  sparkline-bi_spx_proxy             : present
  sparkline-cape                     : present
  sparkline-mean_reversion           : present
  (qratio + ey_deficit cards intentionally don't render sparklines —
   they fire the "Coming in v8b" modal per v8a §13)

CSS (inline, unescaped)
  [id^="sparkline-"] { height: 60px; ... }  ✓
  .hero-chart-container { height: 400px; ... }  ✓
  @media (max-width: 640px) {
    .hero-chart-container { height: 300px; ... }  ✓
  }

JS (inline, unescaped)
  renderHeroForTab(tabName)          : present
  renderSparklines()                 : present
  Plotly.Plots.resize on tab switch  : present

Embedded JSON payload
  variants                           : 8
  hero_specs keys                    : overview, mvci, buffett, cape, mean_reversion
  sparklines keys                    : 8
  MR hero annotation                 : "Currently +181.0% from long-run trend"
```

## 7 — Visual acceptance checklist (spec §7.1)

Headless browser automation (`playwright` / `selenium`) is not installed on this host, so visual sign-off relies on inspecting the generated HTML. Spec §10.3 of v8a (carried into v8a.1) authorizes this fallback.

| Item | Verified by |
|---|---|
| Overview tab: hero chart at top is visible | `id="hero-chart-overview"` container present with `class="hero-chart-container"` (400px height in CSS); inline JS calls `renderHeroForTab("overview")` on initial load |
| Overview cards: all 8 have rendered sparklines | 6 sparkline DIVs (the 6 non-deferred variants). Q-Ratio + EY-Deficit cards are present with their numbers but link to the v8b coming-soon modal; spec §13 of v8a designs this. |
| Mean Reversion tab: real S&P 500 + trend line on log scale | `id="hero-chart-mean-reversion"` container present; `data["hero_specs"]["mean_reversion"]` has 2 traces (`Real S&P 500`, `Exponential trend`), yaxis type=`log` |
| Annotation: "Currently X% above long-run trend" | Verified literally in the JSON payload: `Currently +181.0% from long-run trend` (red because positive) |
| MVCI tab: hero chart bigger than v8a's Panel A | Hero default height = 400px (vs v8a Panel A's 350px); regime bands at 0.15 opacity (vs 0.10); current marker size 16 (vs 12) |
| All 5 tabs visible in nav | 5 `data-tab="..."` buttons in `_header.html` |
| Dark mode toggle still works | `applyDarkMode()` function and `id="dark-toggle"` button preserved from v8a; tests `test_V8A11_dark_mode_js_present` still pass |
| Mobile (360px): hero chart 300px tall, no horizontal scroll | CSS `@media (max-width: 640px) { .hero-chart-container { height: 300px } }` rule present |

## 8 — Test results

```
$ python -m pytest -q
247 passed, 27 skipped, 1 warning in 11.66s         (unit suite)

$ set ACCEPTANCE=1
$ python -m pytest tests/test_v4_acceptance.py tests/test_v5_acceptance.py \
                    tests/test_v6_acceptance.py tests/test_v7_acceptance.py \
                    tests/test_v8a_acceptance.py tests/test_v8a_1_acceptance.py -v
26 passed in 1837s (0:30:37)
```

Per-suite acceptance results:

| Suite | Pass | Total |
|---|---:|---:|
| `test_v4_acceptance.py` | 4 | 4 |
| `test_v5_acceptance.py` | 5 | 5 |
| `test_v6_acceptance.py` | 4 | 4 |
| `test_v7_acceptance.py` | 6 | 6 |
| `test_v8a_acceptance.py` | 4 | 4 |
| **`test_v8a_1_acceptance.py`** | **3** | **3** |
| **TOTAL** | **26** | **26** |

### Per-new-module test coverage

| Module | Coverage |
|---|---:|
| `src/transform/mean_reversion_compute.py` (NEW) | 100% |
| `src/viz/chart_specs.py` (extended) | maintained ≥96% |
| `src/viz/data_extraction.py` (extended) | maintained ≥95% |
| `src/viz/build_dashboard.py` (extended) | maintained ≥95% |

5 new MR unit tests (MR1-MR4 + empty-fallback edge case) + 3 v8a.1 acceptance tests, all green.

## 9 — Two prior-spec acceptance tests adjusted (≤-style upgrades, not regressions)

The expansion to 8 variants required two small in-place adjustments:

1. **`test_v7_seven_variants_in_headline`** — changed `==` to `<=` so the 7-variant required set is now a strict subset of the actual 8-variant headline. The semantic of the v7 acceptance ("these 7 must exist") is preserved.

2. **`test_v7_cross_variant_six_way`** — changed `cv["n_variants"] == 6` to `>= 6` because adding MR raised the cross-variant constituent count to 7. v7's "≥ 6" reading still holds.

No threshold was loosened. No regression hidden.

## 10 — Files delivered

```
src/transform/
  mean_reversion_compute.py            NEW (~50 LoC, 100% cov)

src/viz/chart_specs.py                 + make_hero_chart, make_mean_reversion_hero (~150 LoC added)
src/viz/data_extraction.py             + build_hero_specs, _z_series_for; +mean_reversion in variant lists
src/viz/build_dashboard.py             + mean_reversion overview card + tab partial rendering
src/viz/static/dashboard.css           + .hero-chart-container, [id^="sparkline-"] height rules
src/viz/static/dashboard.js            + renderHeroForTab, renderSparklines (rewrite),
                                          renderPlot now guards missing DOM nodes
src/viz/templates/
  base.html                            + tab_mean_reversion_html slot;
                                          inline_css/js marked |safe (FIX for the Jinja autoescape bug)
  _header.html                         + Mean Reversion tab button
  tab_overview.html                    + hero chart section at top; added MR card to grid
  tab_mvci.html                        + hero chart at top; Panel A's <div> removed (hero replaces it)
  tab_buffett.html                     + hero-chart-buffett container (one chart, updates on sub-tab switch)
  tab_cape.html                        + hero chart at top
  tab_mean_reversion.html              NEW

src/models/orchestrator_modeling.py    + compute_mean_reversion_variant integration;
                                          mean_reversion added to _CONSTITUENT_KEYS, HEADLINE_LABELS,
                                          HEADLINE_DIRECTION, _HEADLINE_LABELS_FOR_VALUE_HISTORY

tests/transform/test_mean_reversion_compute.py   NEW (5 tests)
tests/test_v8a_1_acceptance.py                   NEW (3 tests)
tests/test_v7_acceptance.py                      modified (2 tests: == → <= and == → >=)

outputs/
  dashboard.html                       rebuilt (2.54 MB, all 5 tabs + sparklines + hero charts)
  tables/headline.json                 rebuilt with 8 variants
  charts/{z_history, value_history, sp500_with_regime, scatter_data}.parquet  rebuilt

REVIEW_PACKAGE_v8a.1.md                this document
```

## 11 — Deviations / notes

1. **PCA explained variance 0.876 vs spec target < 0.85.** Adding Mean Reversion did not meaningfully reduce indicator redundancy because MR's log-linear residual co-moves with BI-SPX-proxy and the other price-driven variants. Spec §4.7 anticipated this case ("if still > 0.85, document and continue") — flagged for v9 (add Crestmont P/E, dividend yield, or sentiment indicators).

2. **Q-Ratio + EY-Deficit Overview cards still render WITHOUT sparklines** in v8a.1 (they show the "Coming in v8b" modal on click instead). Spec §4.6 of v8a.1 says "expand to 8 cards" — done; all 8 cards render with their value + z + regime + percentile. Only the deferred 2 lack sparklines. The 6 active sparklines all render with explicit 60px height now that the CSS attribute selector is no longer escaped.

3. **The Mean Reversion hero deviation reads +181%** vs spec's expected illustrative figure (which it doesn't pin down). With real S&P 500 at 6,575 and the 1871-2026 log-linear trend extrapolating to ~2,340, the price is roughly 2.81× trend — i.e., +181%. This is consistent with the variant's z = +2.11 (Strongly Overvalued at the 99.6th percentile of its own residual history).

4. **No headless browser screenshots.** `selenium` / `playwright` are not installed; spec §0 of v8a.1 explicitly accepts the "HTML structure summary" fallback under those conditions. The user can open `outputs/dashboard.html` locally to verify visually.

5. **Visual hierarchy restructure (§5):** Overview now shows the hero chart FIRST (full-width, 400px) above the card grid. MVCI tab renders the hero in place of the old Panel A. Panels B (z vs 10Y CAGR scatter) and C (S&P 500 by regime) remain below as supporting content. CAPE and Mean Reversion tabs follow the same pattern.

## 12 — Implications for next spec

- v9 should add a truly orthogonal valuation indicator (Crestmont P/E or a fundamentals-vs-price spread) to pull PCA explained variance below 0.78.
- v8b can now build Q-Ratio + EY-Deficit dedicated tabs, Diagnostics tab, Data tab, Methodology tab on top of the v8a.1 architecture (every piece — variant analysis, sparklines, hero charts, JSON payload, JS routing — is already plumbed for 8 variants).

End of REVIEW_PACKAGE_v8a.1.
