# spec_v11_0_macro_risk.md — Macro Risk Module

**Spec version:** v11.0 (FROZEN)
**Predecessor:** v10.0 (tactical backtest, merged)
**Status:** First scope expansion beyond pure valuation — adds yield curve,
credit spread, and sentiment indicators in their own composite (MRC),
running alongside the unchanged MVCI valuation composite.

---

## 1. New indicators

### 1.1 Yield curve (2 variants)

| Variant key | Source | Resampling | Range |
|---|---|---|---|
| `yc_10y3m` | TradingView CSVs (`TVC_US10Y`, `TVC_US03MY`) | daily → month-end | 1954-01 to current |
| `yc_10y2y` | FRED `T10Y2Y` (already a spread) | daily → month-end | 1976-06 to current |

For both:
- `spread_raw = 10Y - short_yield` (pp)
- **Direction = INVERTED**: `signal = -spread_raw` (high signal = inversion = bearish)
- No log transform (spread can be negative)

### 1.2 Credit spreads (4 variants)

| Variant key | FRED series | Description |
|---|---|---|
| `cs_hy_master` | `BAMLH0A0HYM2` | ICE BofA US High Yield OAS (master) |
| `cs_ig_master` | `BAMLC0A0CM` | ICE BofA US Corporate OAS (IG master) |
| `cs_hy_bb` | `BAMLH0A1HYBB` | ICE BofA US HY BB OAS |
| `cs_hy_ccc` | `BAMLH0A3HYC` | ICE BofA US HY CCC & lower OAS |

For all 4:
- Daily CSVs (FRED-sourced) resampled to month-end
- **Direction = STANDARD**: `signal = log(spread_raw)` (high spread = bearish, no inversion)
- Log transform OK because OAS is strictly positive

### 1.3 Margin debt

| Variant key | Source | Resampling |
|---|---|---|
| `margin_debt_growth` | FINRA `margin-statistics.xlsx`, "Debit Balances ..." column | monthly |

- `signal = log(level_t / level_{t-12})` (12-month log-growth)
- Why 12M growth not level: margin debt grows secularly with market cap; a
  level-based z-score mis-classifies trends. Canonical sentiment signal per
  Schwab/Yardeni/FINRA conventions is the 12-month rate of change.
- First 12 rows NaN by construction.

---

## 2. Macro Risk Composite (MRC)

MRC aggregates the 7 macro indicators above via three weighting schemes:

- **equal_weight** (default headline): mean across constituents
- **inv_variance**: weights ~ 1/Var_expanding(z_i), renormalized on availability
- **pca_pc1**: first principal component, sign-fixed to "high = bearish"

Scheme implementations are reused unchanged from `mvci_compute.py`; MRC is a
clean clone over the macro z_panel.

### 2.1 Acceptance gate

`|corr(MVCI_equal_weight, MRC_equal_weight)| < 0.8` over the common window.

**Empirically: 0.159 → PASS.** MVCI and MRC capture distinctly different
risk dimensions (valuation level vs. financial-system regime).

---

## 3. Recession overlay infrastructure

- `src/ingest/nber_recessions.py` loads the canonical NBER 1857-2020
  peak/trough table (34 recessions) and persists to
  `data/master/nber_recessions.parquet`.
- `src/viz/chart_overlays.py::add_recession_bands(layout, x_range)` mutates a
  Plotly layout's `shapes` list with grey vertical rectangles (tailwind
  gray-400 @ 25% opacity, `layer: "below"`).
- All 8 time-series chart factories in `src/viz/chart_specs.py` accept a new
  `show_recessions: bool = True` parameter and call the overlay before
  returning.
- Excluded chart types: Panel B (scatter), correlation heatmap, PCA loadings
  bar, ACF/PACF stems, calibration plots, sparklines.

---

## 4. Direction conventions (per Hard Rule §10)

| Indicator | Signal definition | Direction |
|---|---|---|
| yc_10y3m, yc_10y2y | `-spread_raw` | INVERTED (negation in signal column) |
| cs_* (all 4) | `log(spread_raw)` | STANDARD (high = bearish) |
| margin_debt_growth | `log(level_t / level_{t-12})` | STANDARD |

Per the banned-anti-patterns list, the canonical mechanism for sign handling
is the signal column, not silent sign-flipping mid-pipeline.

---

## 5. Invariance gate

The 8 MVCI valuation constituents are **untouched** by v11.0. MVCI z
(long-run, equal_weight) must equal the v10.0 reading to within ±0.001σ.

**Empirically: v10.0 = +1.787σ, v11.0 = +1.786718σ → PASS.**

---

## 6. Data inventory (raw files used)

- `D:\macro\raw data\TVC_US10Y, 1D.csv` (10805 rows)
- `D:\macro\raw data\TVC_US03MY, 1D.csv` (18095 rows; replaces the spec's
  `TVC_US03Y` reference, which does not exist)
- `D:\macro\raw data\FRED_BAMLH0A0HYM2, 1D.csv` (7671 rows)
- `D:\macro\raw data\FRED_BAMLC0A0CM, 1D.csv` (7670 rows)
- `D:\macro\raw data\FRED_BAMLH0A1HYBB, 1D.csv` (7671 rows)
- `D:\macro\raw data\FRED_BAMLH0A3HYC, 1D.csv` (7671 rows)
- `D:\macro\raw data\margin-statistics.xlsx` (352 rows, sheet
  "Customer Margin Balances")

The 2Y Treasury TradingView CSV is absent; FRED `T10Y2Y` is used directly as
spec'd.

---

## 7. v11.x candidates (not in this release)

- **v11.1**: Full orchestrator integration of macro constituents into the
  dual-frame predictive-regression / conditional-distribution / Bayesian /
  conviction pipeline. The compute modules and MRC composite are in place;
  this is wiring work.
- **v11.2**: 8 new dashboard tab templates + nav restructure + overview
  Macro Risk snapshot section. Captions and indicator data are persisted;
  this is template work.
- **v11.3**: White's Reality Check on multi-rule MVCI+MRC backtest.
- **v11.x**: Cross-composite joint distribution analysis (MVCI × MRC
  bivariate regimes).

---

End of spec_v11_0_macro_risk.md
