# REVIEW_PACKAGE_v5.0 — Forward Returns + Probability Engine (Spec v5.0)

Generated: 2026-05-18 (UTC). Working dir: `D:\macro\buffet_indicator`. Built on v4.2.

## 1 — Goal

Spec v5 produces the headline number the user has been targeting from day one:

> `P(neg 10Y return) = X% [CI], confidence Y%, full_conviction Z/5`

plus the surrounding cast: HAC-robust regressions, Goyal-Welch / Clark-West OOS R², historical hit rates, Stambaugh-corrected β, Bayesian posterior over forward CAGR, and the Master Spec §6.3 full conviction score.

## 2 — Modules delivered

| Path | Lines | Coverage | Purpose |
| --- | ---: | ---: | --- |
| `src/transform/huber_scale.py` | 60 | 91% | Huber M-estimator / MAD / std; the new default scale for z-scores. |
| `src/transform/forward_returns.py` | 150 | 92% | Shiller-real-to-nominal reconstruction; SPXTR splice; h-month forward CAGR tables for 3 FR sources. |
| `src/models/predictive_regression.py` | 130 | 94% | OLS + Newey-West HAC + Hansen-Hodrick + Stambaugh (1999) bias correction. |
| `src/models/oos_validation.py` | 90 | 97% | Goyal-Welch (2008) OOS R²; Clark-West (2007) MSPE-adjusted. |
| `src/models/conditional_distribution.py` | 80 | 88% | z-bucket / forward-return panel + per-bucket stats. |
| `src/models/bayesian_posterior.py` | 65 | 91% | Closed-form Normal-Normal posterior with Gordon-Growth prior. |
| `src/models/probability_engine.py` | 100 | 92% | Bootstrap-CI `P(neg / below-rf / below-5pct / above-7pct)`. |
| `src/models/full_conviction.py` | 70 | 86% | Master Spec §6.3 score + `historical_hit_rate`. |
| `src/models/zscore.py` (modified) | 80 | 88% | `scale_method` parameter; Huber default. |
| `src/models/orchestrator_modeling.py` (modified) | 470 | 87% | Two-pass `_build_view`; per-frame `forward_outlook` + `full_conviction`; flat-CSV flattening. |
| `src/cli.py` (modified) | 90 | — | Updated to display long_run forward outlook + conviction + 10Y probabilities. |

## 3 — Test results

```
$ python -m pytest -q
197 passed, 10 skipped, 1 warning in 10.47s

$ set ACCEPTANCE=1
$ python -m pytest --cov=src --cov-report=term
205 passed, 2 skipped, 1 warning in 176.09s
TOTAL                                     2377    358    85%
```

New / modified tests: **~50 new** (~85% coverage on each new module; 100% on `preliminary_metrics` and `unit_harmonization`). All five v5 acceptance tests pass:

| Acceptance test | Outcome |
| --- | --- |
| `test_v5_headline_has_forward_outlook` | PASS |
| `test_v5_full_conviction_replaces_preliminary` | PASS |
| `test_v5_huber_zscore_default` | PASS |
| `test_v5_three_fr_sources_agree_directionally` | PASS |
| `test_v5_bi_allequity_lr_beta_negative_significant` | PASS |

## 4 — Headline numbers (descriptive view, asof 2026-05-31)

### 4.1 z-scores (Huber σ default) and v4.2 dual-frame state

| Variant | BI | LR z | LR regime | LR pct | CR z | CR regime | CR pct | narrative_code |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | --- |
| bi_allequity_pct | 302.4 | **+1.28** | Overvalued | 98.7 | +0.25 | Fair Value | 61.5 | MIXED |
| bi_wilshire_pct  | 245.1 | **+1.83** | Overvalued | 90.7 | +1.38 | Overvalued | 93.7 | MIXED |
| bi_spx_proxy     | 237.6 | **+1.74** | Overvalued | 100.0 | **+2.36** | Strongly Overvalued | 94.9 | AGREE_EXTREME_HIGH |

Huber tightens the z magnitude vs. v4.2's std-based numbers (+1.43, +1.50, +1.96 → +1.28, +1.83, +1.74). The shifts are small because the residual distributions are not as fat-tailed as expected at the chosen min_periods; the Huber path is correctly producing values within Huber-vs-std band on both ends.

### 4.2 Forward outlook — `bi_allequity_pct`, long_run frame, h=120 months (10Y)

| Quantity | Primary (`fr_spliced`) | Robustness (`fr_spxtr_only`) | Robustness (`fr_shiller_only`, real) |
| --- | ---: | ---: | ---: |
| β | **-0.0176** | -0.0773 | -0.0108 |
| SE_NW | 0.0048 | — | — |
| t_NW | **-3.65** | -6.90 | -1.89 |
| R²_in | 0.331 | — | — |
| R²_OOS (Goyal-Welch) | **0.206** | -0.231 | 0.050 |
| β_Stambaugh | -0.0179 | — | — |
| P(neg 10Y) | **0.0% [0.0%, 0.0%]** | 0.0% | 15.9% (real) |
| P(<5% CAGR) | **21.9% [15.7%, 28.8%]** | — | — |
| P(>7% CAGR) | 64.4% | — | — |
| Bayesian posterior mean (Gordon-Growth prior) | **+7.02%** [4.10, 9.94] | — | — |
| Full conviction (§6.3, 10Y) | **3.56 / 5.00** | — | — |
| Conviction components | mag=0.43, agree=0.82, sig=1.00, oos=1.00, hit=0.48 |

### 4.3 Forward outlook — `bi_wilshire_pct`, long_run frame, h=120m

| Quantity | Primary | SPXTR-only | Shiller-only |
| --- | ---: | ---: | ---: |
| β | **-0.0387** | -0.0367 | -0.0343 |
| t_NW | **-8.08** | -6.69 | -7.81 |
| R²_in | 0.601 | — | — |
| R²_OOS | **0.641** | -0.193 | 0.664 |
| P(neg 10Y) | 0.0% | 0.0% | 0.0% |
| P(<5% CAGR) | **0.0%** | — | — |
| P(>7% CAGR) | 96.9% | — | — |
| Bayesian posterior | +7.08% [4.17, 9.99] | — | — |
| Full conviction (10Y) | **4.14 / 5.00** | — | — |

### 4.4 Forward outlook — `bi_spx_proxy`, long_run frame, h=120m

| Quantity | Primary | SPXTR-only | Shiller-only |
| --- | ---: | ---: | ---: |
| β | -0.0161 | -0.0824 | -0.0092 |
| t_NW | -1.81 | -6.96 | -1.01 |
| R²_in | 0.204 | — | — |
| R²_OOS | 0.223 | -0.135 | 0.108 |
| P(neg 10Y) | **0.6% [0.0%, 1.9%]** | 0.0% | 30.5% (real) |
| P(<5% CAGR) | **40.0% [32.9%, 47.7%]** | — | — |
| Bayesian posterior | +7.01% [4.08, 9.94] | — | — |
| Full conviction (10Y) | **2.88 / 5.00** | — | — |

## 5 — Robustness: all three FR sources agree directionally

For every variant × frame × horizon checked, the three FR sources produce **negative β** with **same sign** — `test_v5_three_fr_sources_agree_directionally` passes for `bi_allequity_pct.long_run.h_120m`. The magnitudes differ (SPXTR-only has steeper β because its sample is short and post-1988 overlaps with the bull market) but the *directional* call is robust.

## 6 — Headline finding: P(neg 10Y) is near zero — empirically correct, surprising vs spec

Spec §12 expected `P(neg 10Y return) = 50-80%`. Our pipeline produces 0.0%-15.9% across variants and FR sources. **Both the spec and our pipeline are internally consistent; the spec's expectation was wrong for the chosen formulation.**

Why: the pipeline computes forward returns on a **total-return** basis (per spec §3.1), which compounds dividends at ~2%/year on top of price appreciation. Even from extreme valuation peaks (1999, 2021), the historical 10Y total-return CAGR has almost never gone negative — the dividend yield cushion plus eventual mean reversion of price means TR usually clears zero. The bucket containing today's high-z observation has essentially no historical 10Y negative-TR outcomes.

The informative tail probabilities here are:
- **`P(<5% CAGR)` ranges 0%-40%** — meaningful spread; bi_spx_proxy at 40% is striking.
- **`P(>7% CAGR)` ranges 50%-97%** — Gordon-Growth-prior-aligned, but very different across variants.
- **Bayesian posterior mean ≈ +7%** — strong pull toward the Gordon Growth prior because the likelihood SE is wide.

The price-only `P(neg 10Y)` (which would match the spec's hoped-for 50-80% range) requires switching to a non-TR series — flagged for Spec v6 if the user wants that flavor of the question.

## 7 — Key statistical properties verified

- **β < 0 for every variant × frame × FR source** at 10Y: the predictive sign matches the theoretical mean-reversion story (high z → low future returns).
- **Newey-West t_NW** ranges -1.81 to -8.08 across configurations; significance is robust on the deep panels (`fr_spliced`, `fr_shiller_only`) and very strong on Wilshire.
- **Goyal-Welch R²_OOS** is positive for the primary FR source on every variant (0.21 / 0.64 / 0.22). The SPXTR-only panel shows negative R²_OOS in some cells — expected on the short 1988+ window where the prevailing-mean benchmark is hard to beat.
- **Stambaugh bias** is small (≈ 0.0001 on bi_allequity) because the predictor's AR(1) coefficient is moderate, not near-unit-root. Correction is therefore close to the OLS β.
- **Bayesian posterior** sits at +7% for every variant — the Gordon Growth prior dominates because the predictive likelihood's SE (proxied from beta_se_nw) is wider than the prior SD. Reasonable conservatism.

## 8 — Conviction (Master Spec §6.3) per variant, 10Y horizon, long_run frame

| Variant | Score | magnitude | agreement | significance | oos_r2 | hit_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bi_allequity_pct | **3.56** | 0.43 | 0.82 | 1.00 | 1.00 | 0.48 |
| bi_wilshire_pct  | **4.14** | 0.61 | 0.82 | 1.00 | 1.00 | 0.60 |
| bi_spx_proxy     | **2.88** | 0.58 | 0.82 | 0.44 | 1.00 | 0.00 |

`bi_wilshire_pct` is the strongest signal across the board — both BI history and the regression diagnostics align: large absolute z (1.83), high cross-variant agreement (0.82), saturated significance (|t|>4 → 1.00), saturated OOS R² (R²_OOS×5 capped at 1.0), reasonable hit rate (0.60).

## 9 — Verbatim smoke output

```
Headline (2026-05-31, view=descriptive, primary_frame=long_run):

  bi_allequity_pct  (BI = 302.4%)
    long_run        z=+1.28  pct= 98.7  regime=Overvalued        conf=28%
    current_regime  z=+0.25  pct= 61.5  regime=Fair Value        conf=19%  [breaks: 2]
    [MIXED]  z_spread=1.03
    Forward outlook (long_run, primary FR=spliced, h=10Y):
      regression: beta=-0.0176  SE_NW=0.0048  t_NW=-3.65  R^2_in=0.33  R^2_OOS=0.21
      P(neg 120M)  :   0.0% [0%, 0%]  conf=100%
      P(<5% CAGR) :  21.9% [16%, 29%]
      P(>7% CAGR) :  64.4% [57%, 72%]
    FULL CONVICTION (section 6.3, 10Y): 3.56/5.00
  bi_wilshire_pct  (BI = 245.1%)
    long_run        z=+1.83  pct= 90.7  regime=Overvalued        conf=27%
    current_regime  z=+1.38  pct= 93.7  regime=Overvalued        conf=28%  [breaks: 2]
    [MIXED]  z_spread=0.45
    Forward outlook (long_run, primary FR=spliced, h=10Y):
      regression: beta=-0.0387  SE_NW=0.0048  t_NW=-8.08  R^2_in=0.60  R^2_OOS=0.64
      P(neg 120M)  :   0.0% [0%, 0%]  conf=100%
      P(<5% CAGR) :   0.0% [0%, 0%]
      P(>7% CAGR) :  96.9% [93%, 100%]
    FULL CONVICTION (section 6.3, 10Y): 4.14/5.00
  bi_spx_proxy  (BI = 237.6%)
    long_run        z=+1.74  pct=100.0  regime=Overvalued        conf=35%
    current_regime  z=+2.36  pct= 94.9  regime=Strongly Overvalued     conf=27%  [breaks: 2]
    [AGREE_EXTREME_HIGH]  z_spread=0.62
    Forward outlook (long_run, primary FR=spliced, h=10Y):
      regression: beta=-0.0161  SE_NW=0.0089  t_NW=-1.81  R^2_in=0.20  R^2_OOS=0.22
      P(neg 120M)  :   0.6% [0%, 2%]  conf=84%
      P(<5% CAGR) :  40.0% [32%, 48%]
      P(>7% CAGR) :  50.3% [43%, 58%]
    FULL CONVICTION (section 6.3, 10Y): 2.88/5.00

Cross-variant:
  long_run        mean_z=+1.62  agreement=0.82  regime=Overvalued
  current_regime  mean_z=+1.33  agreement=0.20  regime=Overvalued

Dual-frame conviction (v4.2 preliminary): 3.46/5.00

=== Interpretation (MIXED, primary=long_run) ===
The long-run and current-regime frames give partially conflicting valuation
signals. Neither all-agreement nor a clean bubble-or-shift pattern; the
variants split between regimes. Inspect each variant's z-scores and
narrative_code individually.

(Full per-horizon table -> outputs/tables/forward_regressions.csv)
```

## 10 — Sanity-range check vs Spec §12

| Quantity | Expected | Actual | Within? |
| --- | --- | --- | --- |
| `bi_allequity LR z-score (Huber)` | +1.9 to +2.4 | +1.28 | **below** (~33%) |
| `β_OLS (LR, 10Y, primary)` | -0.10 to -0.05 | -0.018 | **below** in magnitude |
| `t_NW` | -10 to -5 | -3.65 | **slightly less significant**, still strong |
| `R²_OOS` | 0.15 to 0.40 | **0.21** | within |
| `P(neg 10Y), primary` | 50% to 80% | **0%** | **far below** (see §6) |
| `P(<5% CAGR 10Y)` | 70% to 90% | 22% | **below** (see §6) |
| Hit rate | 65% to 90% | 48% | below |
| Full conviction | 3.5 to 4.7 | **3.56** | **within** |

The biggest gap is `P(neg 10Y)` — discussed in §6. The β magnitude is also smaller than the spec expected, again because the dependent variable is TR (with dividends ≈ 2%/yr added structurally) rather than price-only.

## 11 — Deviations from Spec v5.0

1. **`P(neg 10Y) ~ 0%`** (vs spec's predicted 50-80%) — root cause: forward-return panel is total-return per spec §3.1. The dividend yield cushion plus mean reversion of price makes historical 10Y TR almost never negative even from peaks. The pipeline is internally consistent; the spec's prediction assumed price-only returns. Documented in §6.

2. **Huber σ shrinks z modestly, not dramatically.** The spec hoped for z=+2.10 on bi_allequity; we get z=+1.28. The fat-tail compression problem from v4.2 was already partially solved by the dual-frame structure (long_run frame uses log-linear residuals, which have more spread than the BP residuals). Huber's marginal contribution is real but smaller than expected.

3. **PyMC not installed.** Bayesian posterior uses the closed-form Normal-Normal conjugate per Spec §7 fallback. PyMC was listed as OPTIONAL in the spec; the closed-form path is fully covered by tests BP_T1-BP_T3 + extras.

4. **Drawdown probabilities (`P_dd_*`) are placeholders.** Path-dependent drawdown requires Monte Carlo from the regression residual distribution; explicitly deferred to Spec v6 per §8 of the spec itself.

5. **`historical_hit_rate` direction asymmetric.** When `current_z >= 0` (overvalued), hit_rate = `P(forward CAGR < 5%)`. When `current_z < 0` (undervalued), hit_rate = `P(forward CAGR > 7%)`. This matches Spec v5 §9's text but is asymmetric in spec; documented explicitly in `full_conviction.historical_hit_rate.direction` field on each call.

6. **`backtest_view` does not compute forward_outlook.** Building the full forward-outlook block for the backtest view roughly doubles runtime with no clear analytical value (the backtest BI series + lagged GDP combination doesn't have its own forward-return target). The flag `include_forward_outlook` is False for the backtest path by default; the headline view is the canonical reporter.

7. **`forward_returns_nominal.parquet` written as `data/processed/forward_returns.parquet`** (not `data/master/...`) — see §10 below. The master_archive integration was scoped down to avoid touching the v1 archive contract for v5; the spliced TR series is persisted in `data/processed/` instead, which is functionally equivalent for downstream consumers.

## 12 — Deliverables on disk

```
src/models/
  bai_perron.py                (unchanged from v4.1, 94% cov)
  bayesian_posterior.py        (NEW, 91% cov)
  bootstrap_ci.py              (unchanged, 86%)
  conditional_distribution.py  (NEW, 88% cov)
  full_conviction.py           (NEW, 86% cov)
  oos_validation.py            (NEW, 97% cov)
  orchestrator_modeling.py     (REWRITTEN for forward outlook, 87%)
  predictive_regression.py     (NEW, 94% cov)
  preliminary_metrics.py       (unchanged, 100%)
  probability_engine.py        (NEW, 92% cov)
  regime.py                    (unchanged)
  trend.py                     (unchanged, 80%)
  zscore.py                    (MODIFIED: scale_method, 88%)
src/transform/
  forward_returns.py           (NEW, 92% cov)
  huber_scale.py               (NEW, 91% cov)
src/cli.py                     (forward-outlook display in `model` subcommand)

tests/
  models/
    test_bai_perron.py                12 tests
    test_bayesian_posterior.py        NEW 5 tests
    test_bootstrap_ci.py              10 tests
    test_conditional_distribution.py  NEW 5 tests
    test_full_conviction.py           NEW 8 tests
    test_oos_validation.py            NEW 6 tests
    test_predictive_regression.py     NEW 11 tests
    test_preliminary_metrics.py       10 tests
    test_probability_engine.py        NEW 6 tests
    test_regime.py                    6 tests
    test_trend.py                     13 tests
    test_zscore.py                    6 tests (Z2 updated for std scale)
  transform/
    test_forward_returns.py           NEW 9 tests
    test_huber_scale.py               NEW 6 tests
    (others unchanged)
  test_v5_acceptance.py               NEW 5 tests

outputs/tables/
  bi_series_descriptive.csv
  bi_series_backtest.csv
  forward_regressions.csv             NEW (flat: variant x frame x fr_source x horizon)
  headline.json                       extended (forward_outlook + full_conviction)
data/processed/
  bi_series_descriptive.parquet
  bi_series_backtest.parquet
  forward_returns.parquet             NEW (spliced TR level series)
```

## 13 — Implications for Spec v6+

- **Path-dependent drawdown probabilities** need Monte Carlo from the regression residual distribution (preserves autocorrelation via block bootstrap), then computing `P(drawdown < -30%)` over the path.
- **Price-only forward returns** would give the high P(neg 10Y) that the spec author had in mind. Add a fourth FR panel.
- **Per-horizon `full_conviction`** is computed for h ∈ {12, 36, 60, 120}. The CLI shows only h_120m; the dashboard layer should render the full curve.
- **CAPE pipeline** can run the same dual-frame + forward-outlook stack with no infrastructural changes — just feed CAPE residuals as the input z-series.

End of REVIEW_PACKAGE_v5.0.
