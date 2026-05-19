# Spec v9.0 — Crestmont P/E + MVCI 8-constituent

> Predecessor: v8b.1 (7-constituent MVCI). This spec adds Crestmont P/E (Easterling 2010)
> as the 8th MVCI valuation indicator and propagates the change through orchestrator,
> dashboard, diagnostics, and visual gate.

---

## 1 — Scope

| Stage | Deliverable |
|---|---|
| 1 | `src/transform/crestmont_compute.py` + 6+ unit tests + persisted parquets |
| 2 | Integrate Crestmont as 8th MVCI constituent (orchestrator + MVCI compute + data_extraction) |
| 3 | Dashboard: new `tab_crestmont.html`, header nav, overview grid, methodology, captions, rebuilt HTML |
| 4 | Full test + lint suite (target 325+ pass, ruff/bandit clean) |
| 5 | Visual gate: 10 screenshots (8 indicator tabs + diagnostics + mobile) + console log |
| 6 | REVIEW_PACKAGE_v9.0.md + commit + tag |

## 2 — Methodology (frozen)

**Crestmont P/E** (Easterling 2010, *Probable Outcomes*, ch. 6): a cyclically-adjusted P/E
that normalizes real S&P 500 price by a **smooth exponential trend** of real earnings,
rather than Shiller's 10-year trailing moving average.

Algorithm:

1. Load `real_price_t` and `real_eps_t` (real earnings) from Shiller's monthly composite
   (1871-present) via the project's existing `ShillerData` abstraction.

2. Fit a log-linear OLS regression of log earnings on time:

   ```
   log(real_eps_t) = α + β · t + ε_t
   ```

   where `t` is months elapsed since the first observation (integer).

3. Trend earnings: `trend_eps_t = exp(α̂ + β̂ · t)` — a smooth exponential growth path.

4. **Crestmont P/E**: `crestmont_pe_t = real_price_t / trend_eps_t`.

5. Standardize via the existing dual-frame z-score infrastructure (long_run +
   current_regime, Huber σ).

### Data-access note (v9.0 deviation)

The original spec language used `load_master("shiller_sp500_real", ...)`. The current
project ships Shiller data via the `ShillerData` dataclass (only `wilshire_5000` is
canonicalized as a master parquet today). v9.0 follows the existing project pattern
(`compute_cape_variants(shiller_data)` / `compute_mean_reversion_variant(shiller_data)`
style) until Shiller series are migrated to the master archive. This deviation is
recorded in REVIEW_PACKAGE_v9.0.md §9.

## 3 — Integration points

### 3.1 `src/transform/crestmont_compute.py`

- `compute_crestmont_pe(shiller_data, *, start=None, end=None) -> pd.DataFrame`
  Returns DataFrame with columns
  `{real_price, real_eps, trend_eps, crestmont_pe, log_crestmont_pe, alpha, beta, n_fit}`.
- `compute_crestmont_variant(shiller_data) -> dict[str, pd.Series]`
  Project-pattern wrapper returning `{"crestmont": pd.Series}` of the level series.
- Raises `ValueError` if fewer than 60 monthly observations after dropna.
- `_MIN_OBS_FOR_TREND_FIT = 60` (documented constant; 5-year minimum per Easterling 2008).

### 3.2 Orchestrator

In `src/models/orchestrator_modeling.py`:

- Add `"crestmont"` to `HEADLINE_LABELS` (`"Crestmont P/E"`, unit `""`).
- Add `"crestmont": +1` to `HEADLINE_DIRECTION`.
- Add `"crestmont"` to `_CONSTITUENT_KEYS` tuple (8th).
- Add `"crestmont": "ratio"` to `_HEADLINE_LABELS_FOR_VALUE_HISTORY`.
- After mean-reversion variant computation, call `compute_crestmont_variant(sh)` and
  merge into both `bi_desc` and `bi_bt`.

### 3.3 Data extraction

In `src/viz/data_extraction.py`:

- Append `"crestmont"` to `_DASHBOARD_VARIANTS` (after `cape`).
- Append `"crestmont"` to `_OVERVIEW_VARIANTS` (overview card display order).
- In `build_hero_specs`, add a `make_hero_chart(crestmont_z, title="Crestmont P/E", chart_name="crestmont_hero")`
  entry on `out["crestmont"]`.

### 3.4 Captions + interpretations

In `src/viz/captions.py`:

- Add `"crestmont"` short caption in `PANEL_A_CAPTIONS`.
- Add `crestmont_hero_interpretation(value, z, percentile, regime)` returning the
  standard `{what_this_shows, how_to_read, current_reading}` triple.
- Add `"crestmont"` entry in `WHY_IT_MATTERS` describing Crestmont vs CAPE.
- Wire `crestmont` branch in `all_interpretations_for`.

### 3.5 Templates

- `src/viz/templates/tab_crestmont.html`: new file mirroring `tab_cape.html` structure
  (hero, headline-tiles, Panel A/B/C, predictive regression box, "Why does..." card,
  About section). References Jinja variable `cr`.
- `src/viz/templates/_header.html`: insert `<button data-tab="crestmont">Crestmont</button>`
  between CAPE and Q-Ratio.
- `src/viz/templates/base.html`: add `{{ tab_crestmont_html|safe }}` slot.
- `src/viz/templates/tab_overview.html`: update header from "7-variant snapshot" to
  "8-variant snapshot"; cross-variant table caption from "6 constituents" → "8 constituents";
  card grid `xl:grid-cols-4` → 3-column (cleaner with 9 cards = 1 MVCI + 8 variants).
- `src/viz/templates/tab_methodology.html`: add a §3.6 "Crestmont P/E (v9.0)" paragraph
  describing the methodology; renumber MVCI to §3.7.

### 3.6 Dashboard JS

In `src/viz/static/dashboard.js`, extend `renderChartsForTab` with a `crestmont`
branch that calls `renderVariantPanels("crestmont", "crestmont")`.

### 3.7 Build dashboard

In `src/viz/build_dashboard.py`:

- After EY-Deficit tab block, add `if "crestmont" in variants:` branch that builds
  `cr_block = _build_variant_block(headline, "crestmont")` and renders `tab_crestmont.html`.
- Pass `tab_crestmont_html=crestmont_html` to `base.render`.

## 4 — Acceptance gates

| Gate | Target | Notes |
|---|---|---|
| `_CONSTITUENT_KEYS` length | 8 | includes `crestmont` |
| Correlation matrix shape | 8×8 (over constituents) | excluding MVCI itself |
| PCA loadings | 8 non-zero entries | use `loadings_full` (v8b.1 B.3 fix) |
| MVCI z-score shift | |Δz| ≤ 0.3σ vs v8b.1 baseline (1.787σ) | expect ~unchanged since Crestmont correlates strongly with existing constituents |
| Equal-weight vs PCA-PC1 schemes | abs diff < 0.05σ | inv-variance routinely diverges and is excluded from this tighter gate |
| New tests passing | ≥ 11 (6 compute + 5 integration) | spec §1.4 + §2.6 |
| Bundle size | ≤ 6.5 MB strict / ≤ 8 MB escape hatch | v8b.1 was 6.1 MB; +Crestmont adds ~0.9 MB |
| Console pageerror count | 0 | only Tailwind CDN warning acceptable |
| Screenshots | 10 (8 indicators + diagnostics + mobile) | all 1440 desktop / 360 mobile, > 50 KB, > 1500 px tall (desktop) |

## 5 — Out of scope (v9.x+)

- Migrating Shiller real_price / real_earnings into the master archive
  (`load_master("shiller_sp500_real")`).
- Drawdown probability simulation (Monte Carlo path).
- Margin Debt, Insider Selling, IPO Heat — sentiment constituents from CMV.
- WCAG accessibility audit.
- Plotly basic bundle swap (would require dropping heatmap chart type).

## 6 — References

- Easterling, E. (2010). *Probable Outcomes: Secular Stock Market Insights*. Crestmont
  Holdings, ch. 6.
- Easterling, E. (2008). "Crestmont Research: P/E Ratios and Stock Market Returns" —
  methodology notes on trend-earnings normalization.
- Shiller, R. (1996). "Long-Term Perspectives on the Current Boom in Home Prices."
  (P/E10 methodology baseline against which Crestmont is contrasted.)

---

**End of spec_v9_0_crestmont.md**
