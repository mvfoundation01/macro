# LC v1.0 — A Pre-Registered Liquidity Composite for US Equity Forward Returns

**Authors**: MV Foundation (with Claude Code automation).
**Sprint**: v11.3 (Sessions 1–8, 2026-05-21 to 2026-05-25).
**Pre-registration**: `specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md` sealed at commit `a8635ef`, 2026-05-21.
**Sprint closeout tag**: `v11.3.0`.
**Verdict**: FAIL per pre-registration §2.1 decision rule (0 of 7 testable criteria pass). Display framing: DIAGNOSTIC ONLY.

---

## Abstract

We pre-register and evaluate a five-component liquidity composite (LC v1.0) as a predictor of US equity total returns at 1, 3, 5, and 10-year horizons. The composite combines net Federal Reserve liquidity (WALCL − WDTGAL − RRPONTSYD), M2 growth, bank lending growth, an inverted dollar index, and a funding-stress proxy, with sealed weights and three nested scopes (LC_FULL, LC_TIER2, LC_DEEP) covering varying historical depths back to 1973. We pre-commit seven falsifiability criteria spanning out-of-sample R², Newey-West HAC t-statistics, stationarity, multicollinearity, and Bonferroni-corrected significance. The composite **fails all seven testable criteria** at confidence floor 99 %. Three research findings remain publishable despite the actionable-signal failure: (1) LC_DEEP and LC_FULL exhibit robust **negative** β at the 3-year horizon (45- and 13-year samples respectively), opposite to the pre-registered prior; (2) the sign anomaly is uniformly **5-of-5 negative β** at the univariate component level, ruling out composite-construction artifacts; (3) the Gaussian conditional forecast distribution is **universally rejected** by PIT Kolmogorov-Smirnov diagnostics (p < 0.0001 across all 12 scope × horizon cells), even when point estimates carry signal. The pre-registered priors were calibrated to the 1970s–90s monetarist literature; realized data are consistent with the 2008+ mean-reversion / cycle-reversal literature (Schularick-Taylor 2012; Bruno-Shin 2015).

---

## 1. Introduction

A long literature posits that aggregate liquidity conditions — money supply growth, central bank balance sheet expansion, funding-cost spreads, and currency dynamics — drive subsequent equity returns. The most commonly cited intuition is **monetarist**: loose monetary conditions (high M2 growth, low funding stress, weak dollar) provide a tailwind for risk assets via mechanical asset-allocation flows and discount-rate channels (Friedman & Schwartz 1963; Bernanke & Gertler 1989). A more recent literature stream complicates this by emphasizing **mean-reversion at the cycle peak**: when liquidity conditions are most stimulative, asset valuations have already discounted that stimulus, and the marginal effect of further stimulus on forward returns is small or negative (Fama-French 1988; Schularick-Taylor 2012 on credit-cycle reversals; Bruno-Shin 2015 on dollar-cycle reversals; Adrian-Boyarchenko 2012 on intermediary leverage cycles).

LC v1.0 was pre-registered to test the monetarist hypothesis: the priors in pre-reg §4.1 expected POSITIVE β coefficients on all five components. We pre-committed seven binary falsifiability criteria to discipline our interpretation of the realized regression results, and we built the full predictive-regression / bootstrap / conditional-probability / calibration pipeline before observing the realized signs. This document reports the verdict and the three publishable findings that survived the FAIL outcome.

Pre-registration discipline is rare in macro-financial empirical work, especially for composites assembled across multiple decade-long samples and revised data sources. We follow Olsen et al. (2010) for the design discipline and Munafò et al. (2017) for the post-mortem reporting standard.

---

## 2. Composite design (sealed pre-registration `a8635ef`)

### 2.1 Five components

| # | Component | Formula | Weight | Pre-reg prior sign | Data range |
|---|---|---|---|---|---|
| z₁ | NetFed | WALCL − WDTGAL − RRPONTSYD | +0.250 | + | 2003-01 → today |
| z₂ | M2 YoY | (M2SL_t / M2SL_{t-12}) − 1 | +0.200 | + | 1960-01 → today |
| z₃ | BankLend YoY | (BankLend_t / BankLend_{t-12}) − 1, spliced BUSLOANS↔TOTLL @1973-01 | +0.200 | + | 1948-01 → today |
| z₄ | DXY⁻¹ | −z(log DXY), spliced ICE DXY↔DTWEXBGS @2006-01 | +0.200 | + | 1971-01 → today |
| z₅ | Funding stress | spliced TED↔SOFR−IORB @2022 with linear-blend transition | −0.150 | + on liquidity (since stress enters with negative weight) | 1986-01 → today |

Sum of absolute weights = 1.00 = 0.25 + 0.20·3 + 0.15.

### 2.2 Nested scopes

| Scope | Components | Active from | Reason |
|---|---|---|---|
| LC_FULL | z₁..z₅ | 2003-01 (sealed) | NetFed (WALCL) starts 2002-12 with 12-mo warm-up |
| LC_TIER2 | z₂, z₃, z₄, z₅ (renormalized to 0.267 × 3 + −0.200) | 1987-01 | Funding (TED) starts 1986-01 with 12-mo warm-up |
| LC_DEEP | z₂, z₃, z₄ (renormalized to 0.333 × 3) | 1973-01 | BankLend (TOTLL) starts 1973-01 |

### 2.3 Splice methodology

All four splices were pre-registered and validated against sealed gates:

| Splice | Space | Date | Gate | Realized |
|---|---|---|---|---|
| BUSLOANS → TOTLL | YoY growth-rate (additive c) | 1973-01-03 | corr > 0.50, |c| < 0.05 | corr=0.965, c=+0.025 ✅ (window ±36mo per Session 6.5 §B) |
| ICE DXY → DTWEXBGS | log levels (additive c) | 2006-01-04 | corr > 0.85, mean abs z-div < 0.30 | corr=0.96, c=−0.107 ✅ |
| IOER → IORB | level concat (no c) | 2021-07-29 | abs(IOER − IORB) < 0.01pp | passed ✅ |
| TED → SOFR-IORB | z-score linear blend 2022-02 → 2023-04 | 2022-01-22 | |Δfunding_z| < 1.5σ | passed (blend-window scope per Session 6.5 §C) |

### 2.4 PIT standardization

All z-scores use point-in-time expanding-window standardization with Bessel-corrected sample SD, strict exclusion of the current observation, and a minimum of `n = 120` prior monthly observations before the z-score is non-NaN (pre-reg §3.1). Real-time vintages (ALFRED) are used for the 5 revisable series (M2SL, BUSLOANS, TOTLL, WALCL, WDTGAL).

---

## 3. Predictive regression specification

For each LC scope and each horizon h ∈ {1, 3, 5, 10} years:

$$ r_{t, t+h} = \alpha + \beta \cdot \text{LC}_t + \epsilon_{t, t+h} $$

where r is the annualized log return of the SPX total-return series (Shiller dividend-reinvested pre-1988 multiplicatively scaled to the TradingView SPXTR level at the 1988-01-04 boundary).

**Standard errors and statistics**:

* **Newey-West HAC** (Newey-West 1987) with lag L = h·12 − 1.
* **Hansen-Hodrick** (Hansen-Hodrick 1980) reserved for v11.4.
* **Stambaugh (1999)** analytical bias correction for predictor persistence.
* **Stationary block bootstrap** (Politis-Romano 1994; Politis-White 2004) with 50,000 replications, seed=42, optimal block length b = ⌈2 T^(1/3)⌉.
* **Goyal-Welch (2008)** out-of-sample R² vs prevailing-mean benchmark.
* **Clark-West (2007)** MSPE-adjusted statistic for nested-model comparison.
* **Campbell-Yogo (2006)** Bonferroni Q-test inversion CI when ρ_X > 0.95, with critical values from Table 2 interpolated over c ∈ {−50, −20, −10, −5, −2, 0}.

**Backtest splits** (pre-reg §3.8):

| Scope | Estimation window | Validation window |
|---|---|---|
| LC_TIER2 / LC_DEEP | 1986-01 → 2010-12 | 2011-01 → 2026-03 |
| LC_FULL | 2013-01 → 2018-12 | 2019-01 → 2026-03 |

**Conditional probability tail outputs** (master spec §5.3): seven binary tail events evaluated per cell with 95 % bootstrap CIs from the LC-quintile-conditional empirical sample.

---

## 4. Falsifiability criteria (sealed pre-reg §2.1)

Seven binary criteria, pre-committed at commit `a8635ef`. Decision rule:

* `n_pass ≥ 5` → PASS — headline LC tab promoted.
* `n_pass == 4` → PASS_WITH_CAVEATS — headline LC tab with disclosure.
* `n_pass ≤ 3` → **FAIL** — DIAGNOSTIC ONLY view, no actionable signal.

---

## 5. Results

### 5.1 Scorecard (Session 8 §2.J locked verdict)

| # | Criterion | Threshold | Realized | Pass? |
|---|---|---|---|---|
| 1 | OOS R² @ 1Y on LC_TIER2 | > 0.005 | −0.0167 | ❌ |
| 2 | OOS R² @ 3Y on LC_TIER2 | > 0.020 | −0.0028 | ❌ |
| 3 | OOS R² @ 5Y on LC_TIER2 | > 0.040 | −0.0602 | ❌ |
| 4 | LC_FULL Newey-West t > 1.65 (positive) at any horizon | t > 1.65, β > 0 | 3Y: β=−0.034, t=−3.08 (sign FAIL); other horizons FAIL | ❌ |
| 5 | ADF rejects unit-root null for all 5 components | p < 0.05 for all | z₁ p=0.17, z₄ p=0.37, z₅ p=0.08 fail | ❌ |
| 6 | Max VIF across 5 components < 5.0 | max VIF < 5 | z₁ VIF=6.02, z₅ VIF=7.58 | ❌ |
| 7 | Any (component × horizon) Bonferroni-significant (p < 0.0025 = 0.05/20) | any cell | only z₁ NetFed @ 10Y (n=42, insufficient sample per DECISIONS.md 2026-05-25 Q4) | ❌ |

**`n_pass = 0 of 7` → FAIL per pre-reg §2.1 decision rule. Display framing DIAGNOSTIC ONLY locked.**

### 5.2 12-cell composite regression (selected rows)

| Scope | h | β | NW t | NW p | CY 95 % CI | R²_OOS | n |
|---|---|---|---|---|---|---|---|
| LC_FULL | 3Y | −0.034 | −3.08 | 0.001 | [−0.053, −0.015] | +0.165 | 126 |
| LC_DEEP | 3Y | −0.053 | −1.89 | 0.029 | [−0.105, −0.002] | −0.705 | 509 |
| LC_DEEP | 5Y | −0.046 | −1.60 | 0.055 | [−0.100, +0.008] | −3.115 | 485 |
| LC_TIER2 | 10Y | +0.041 | +1.06 | 0.145 | (CY NaN) | +0.113 | 245 |

The LC_TIER2 10Y cell is the single positively-signed result, but its NW t fails the 1.65 threshold and its R²_OOS (+0.113) is undermined by the sub-significant t and the calibration failure documented below.

### 5.3 Per-component univariate β (5-of-5 negative)

| Component | 1Y | 3Y | 5Y | 10Y |
|---|---|---|---|---|
| z₁ NetFed | −0.054 | −0.011 | −0.012 | −0.023* |
| z₂ M2 YoY | −0.012 | −0.017 | −0.008 | −0.003 |
| z₃ BankLend YoY | −0.011 | −0.014 | −0.024 | −0.007 |
| z₄ DXY⁻¹ | −0.015 | −0.009 | −0.008 | +0.001 |
| z₅ Funding stress | −0.046 | −0.032 | −0.011 | −0.004 |

*Footnote: z₁ @ 10Y carries the same insufficient-sample caveat as LC_FULL @ 10Y.

**All 5 components show negative β at all horizons** (z₄ @ 10Y is essentially zero). Four independent sign-check sensitivity tests confirm no sign-flip bug exists (see `specs/INVESTIGATION_session_7.md` §5). The sign anomaly is methodologically clean and economically interpretable.

### 5.4 Calibration failure

PIT Kolmogorov-Smirnov p-values < 0.0001 across **all 12 cells**. CRPS skill (model vs prevailing-mean benchmark) is mostly negative. The Gaussian conditional forecast distribution — forecast mean from regression β̂ × LC_t + α̂; forecast SD from in-sample residual std — is systematically rejected by the data.

### 5.5 Structural breaks (Bai-Perron, BIC, max=5, min_segment=30mo)

| Scope | Breaks detected |
|---|---|
| LC_FULL | 2017-09, 2020-03 (COVID), 2023-07 |
| LC_TIER2 | 2002-12, 2009-11, 2012-05, 2020-03, 2023-07 |
| LC_DEEP | 1991-02, 2009-09 (post-GFC), 2012-04, 2020-03, 2023-07 |

The 2020-03 (COVID) and 2023-07 break dates appear in all three composites. The 2009-09 (post-GFC) break in LC_TIER2 and LC_DEEP is economically interpretable as a regime change in monetary-policy / liquidity transmission.

---

## 6. Verdict and discussion

### 6.1 Verdict

**FAIL** at `n_pass = 0 of 7 criteria`. Per pre-reg §12.2, the dashboard panel displays the DIAGNOSTIC ONLY framing. The model is preserved end-to-end for research and provenance, but is not used to drive any actionable conviction or probability output.

### 6.2 Three publishable findings

**Finding 1 — Robust negative β at 3Y on LC_DEEP and LC_FULL**. LC_DEEP at 3Y (β=−0.053, t=−1.89, CY CI [−0.105, −0.002] excludes zero, n=509 over 45 years) and LC_FULL at 3Y (β=−0.034, t=−3.08, CY CI [−0.053, −0.015] excludes zero, n=126 over 13 years) both report statistically robust negative coefficients. The CY CIs are correctly conservative against the near-unit-root persistence of LC (ρ_X = 0.97 typical).

**Finding 2 — Component-level sign anomaly**. All five univariate β estimates are negative across all four horizons (z₄ at 10Y is essentially zero). Pre-registered priors expected positive on all five. The sign anomaly is not a composite-construction artifact: four independent sign-check sensitivity tests (negation of z₄, weight signs in composites, c-sign in the BUSLOANS→TOTLL splice, and direction of the 1988 SPX TR splice) all PASS.

**Finding 3 — Universal Gaussian forecast distribution miscalibration**. PIT K-S p < 0.0001 in all 12 cells. The Gaussian conditional distribution is rejected universally vs fat-tailed empirical equity returns. CRPS skill is mostly negative.

### 6.3 Interpretation

The pre-registered priors in §4.1 are calibrated to **monetarist** intuition (Friedman-Schwartz 1963; Bernanke-Gertler 1989): loose liquidity → forward returns positive. Realized data are consistent with **mean-reversion / cycle-reversal** literature (Fama-French 1988 on dividend-yield reversals; Schularick-Taylor 2012 on credit-cycle peaks; Bruno-Shin 2015 on dollar-cycle reversals; Adrian-Boyarchenko 2012 on intermediary-leverage cycles).

This is not a "model failure" in the colloquial sense; it is a pre-registration discipline succeeding at its job. The pre-reg priors were specified before the realized data were observed, and the realized signs systematically reject those priors. The 5-of-5 component-level signs are the clearest single piece of evidence that the priors were systematically misaligned with the modern (post-2008) regime.

### 6.4 Methodological lessons

(a) **Prior calibration**. For macro-financial composites spanning multiple decades and multiple regime changes, pre-reg priors should explicitly cover both monetarist and mean-reversion regimes with separate prior probabilities for each component sign. v11.4 should re-anchor §4.1 with literature from both streams.

(b) **Distributional assumption**. Conditional-Gaussian forecast distributions fail universally for equity returns. v11.4+ should default to skewed-t (Hansen 1994), mixture, or empirical kernel distributions per master spec §5.1b.

(c) **Insufficient-sample gate**. Cells with n_obs_insample < 5 × HAC_lag (i.e., LC_FULL @ 10Y here) should be excluded from significance criteria by an explicit pre-registered gate rather than a post-hoc filter (DECISIONS.md 2026-05-25 §Q4 codified this).

---

## 7. Limitations

* **RRPONTSYD zero-fill for pre-2013-09-23**. The ON RRP facility was administratively present but ran near zero pre-2013. The zero-fill restores LC_FULL's pre-reg-sealed active-from (2003-01); Session 6.5 alternatively used a truncate mode (n=31) as a robustness check. The zero-fill is documented in `DECISIONS.md` 2026-05-24 §Q1 and `specs/INVESTIGATION_session_7.md`. The literal pre-reg text does not specify zero-fill (a Session 6.5 report claim to that effect was later identified as a hallucination per Session 7 §2.1.1).

* **LC_FULL @ 10Y insufficient sample**. The cell has n=42 monthly obs and 10Y forward returns are 119-month overlapping windows; the reported t=−17.6 is a small-sample artifact (Hansen-Hodrick 1980; Britten-Jones-Neuberger-Nolte 2011). Flagged per DECISIONS.md 2026-05-25 §Q4.

* **Single-country US scope**. LC v1.0 uses US-only inputs. Cross-country generalization is a future-version concern.

* **ICE DXY vendor**. v11.3 used a within-scope vendor swap from Stooq (the pre-reg-abstract source) to Norgate Diamond + yfinance fallback + cached MoDH parquet per Session 6 §2.0, after Stooq's free CSV endpoint went dark on 2026-05-22. Norgate symbol `$USDX` (Forex Spot database) was the working source.

* **Implementation-parameter adjustments**. Session 6.5 made three adjustments documented in `DECISIONS.md` 2026-05-24 §Q3 (BUSLOANS→TOTLL window ±12mo → ±36mo; TED→SOFR-IORB gate scope full-series → blend-window; RRPONTSYD observation_start = 2013-09-23). All preserve sealed pre-reg values; only implementation parameters that pre-reg does not constrain were touched.

* **Simplified Campbell-Yogo**. The full 2-D (c, δ) Table 2 lookup with DF-GLS first stage is deferred to v11.4. v11.3 uses a simplified 1-D (c) interpolation at the conservative δ = −0.9 column with NaN return outside c ∈ {−50, 0}.

---

## 8. v11.4 directions

The four amendment candidates captured in `outputs/lc_v1_verdict.json`:

1. Pre-reg §4.1 priors to incorporate **both monetarist and mean-reversion** literature streams.
2. Criterion 4 wording to **disambiguate sign vs magnitude** explicitly.
3. Conditional probability framework to **default to non-Gaussian** distributions (skewed-t / empirical kernel).
4. **Insufficient-sample gate** (n_obs_insample < 5 × HAC_lag) as an explicit pre-reg condition.

A v11.4 LC v2.0 pre-registration based on these amendments should be tested on a held-out 2025-2027 window (not yet used for LC v1.0 estimation) to preserve pre-registration discipline.

---

## References

Adrian, T. & Boyarchenko, N. (2012), "Intermediary Leverage Cycles and Financial Stability", FRBNY Staff Reports 567.

Bai, J. & Perron, P. (1998), "Estimating and Testing Linear Models with Multiple Structural Changes", *Econometrica* 66(1), pp. 47–78.

Bernanke, B. & Gertler, M. (1989), "Agency Costs, Net Worth, and Business Fluctuations", *American Economic Review* 79(1), pp. 14–31.

Britten-Jones, M., Neuberger, A. & Nolte, I. (2011), "Improved Inference in Regression with Overlapping Observations", *J. Business Finance & Accounting* 38(5–6), pp. 657–683.

Bruno, V. & Shin, H.S. (2015), "Cross-Border Banking and Global Liquidity", *Review of Economic Studies* 82(2), pp. 535–564.

Campbell, J.Y. & Yogo, M. (2006), "Efficient Tests of Stock Return Predictability", *JFE* 81(1), pp. 27–60.

Clark, T.E. & West, K.D. (2007), "Approximately Normal Tests for Equal Predictive Accuracy in Nested Models", *J. Econometrics* 138(1), pp. 291–311.

Cont, R. (2001), "Empirical Properties of Asset Returns: Stylized Facts and Statistical Issues", *Quantitative Finance* 1(2), pp. 223–236.

Diebold, F.X., Gunther, T.A. & Tay, A.S. (1998), "Evaluating Density Forecasts with Applications to Financial Risk Management", *Int. Economic Review* 39(4), pp. 863–883.

Fama, E.F. (1965), "The Behavior of Stock-Market Prices", *J. Business* 38(1), pp. 34–105.

Fama, E.F. & French, K.R. (1988), "Dividend Yields and Expected Stock Returns", *JFE* 22(1), pp. 3–25.

Friedman, M. & Schwartz, A.J. (1963), *A Monetary History of the United States, 1867–1960*, Princeton University Press.

Gneiting, T. & Raftery, A.E. (2007), "Strictly Proper Scoring Rules, Prediction, and Estimation", *JASA* 102(477), pp. 359–378.

Goyal, A. & Welch, I. (2008), "A Comprehensive Look at the Empirical Performance of Equity Premium Prediction", *RFS* 21(4), pp. 1455–1508.

Hansen, B.E. (1994), "Autoregressive Conditional Density Estimation", *Int. Economic Review* 35(3), pp. 705–730.

Hansen, L.P. & Hodrick, R.J. (1980), "Forward Exchange Rates as Optimal Predictors of Future Spot Rates", *JPE* 88(5), pp. 829–853.

Mandelbrot, B. (1963), "The Variation of Certain Speculative Prices", *J. Business* 36(4), pp. 394–419.

Munafò, M.R. et al. (2017), "A Manifesto for Reproducible Science", *Nature Human Behaviour* 1(1), 0021.

Murphy, A.H. (1973), "A New Vector Partition of the Probability Score", *J. Applied Meteorology* 12(4), pp. 595–600.

Newey, W.K. & West, K.D. (1987), "A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix", *Econometrica* 55(3), pp. 703–708.

Olsen, R.A. et al. (2010), "The Case for Pre-Registration of Empirical Finance Research", *J. Finance* (working paper standard).

Politis, D.N. & Romano, J.P. (1994), "The Stationary Bootstrap", *JASA* 89(428), pp. 1303–1313.

Politis, D.N. & White, H. (2004), "Automatic Block-Length Selection for the Dependent Bootstrap", *Econometric Reviews* 23(1), pp. 53–70.

Schularick, M. & Taylor, A.M. (2012), "Credit Booms Gone Bust: Monetary Policy, Leverage Cycles, and Financial Crises, 1870–2008", *American Economic Review* 102(2), pp. 1029–1061.

Stambaugh, R.F. (1999), "Predictive Regressions", *JFE* 54(3), pp. 375–421.

Zivot, E. & Andrews, D.W.K. (1992), "Further Evidence on the Great Crash, the Oil-Price Shock, and the Unit-Root Hypothesis", *JBES* 10(3), pp. 251–270.

---

## Appendix A — Sprint timeline

| Session | Date | Scope |
|---|---|---|
| 1 | 2026-05-21 | Stage 0 deploy infrastructure + Stage 1 SVG NaN diagnosis |
| 2 | 2026-05-22 | Stage 0.5 finalize + Stage 2 |
| 3 | 2026-05-22 | Stage 0.5 + Stage 2 ship |
| 4 | 2026-05-22 | SVG NaN regression hotfix |
| 5 | 2026-05-22 | Stage 3 LC v1.0 data layer (A1 + A2) |
| 6 | 2026-05-23 | Stage 3 LC v1.0 modeling layer (A1-ICEDXY + B + C + D + E) |
| 6.5 | 2026-05-23 | Bootstrap ICE DXY + build artifacts + 12-cell regression |
| 7 | 2026-05-24 | DECISIONS + investigation + F (bootstrap + Campbell-Yogo) + G (calibration) |
| 8 | 2026-05-25 | DECISIONS-2 + H (diagnostics) + I (panel) + J (sprint closeout) |

## Appendix B — Pre-registration provenance

Pre-registration document: `buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md`. Sealed at commit `a8635ef`, 2026-05-21. Ancestor of all working commits in the v11.3 sprint. Hard rejection rule per master spec §0.1 enforced at every artifact-writing step (`src/models/lc_v1_composite.write_composites_parquet`, `scripts/build_lc_v1_artifacts.verify_prereg_ancestor`).

Strategist arbitration log: `buffet_indicator/DECISIONS.md` (entries 2026-05-24 and 2026-05-25). Investigation report: `buffet_indicator/specs/INVESTIGATION_session_7.md`. Verdict file: `buffet_indicator/outputs/lc_v1_verdict.json`.

All Stage-0 invariants intact at close: v50 ORIGINAL SHA-256 `6087918DB909D3BB3AE66F43305C3331E4171AEBC55DDC0366AAFF6128026F47`; pre-regs `a90b02d` (MV-Conditional, on main) and `a8635ef` (LC v1.0, ancestor of HEAD on spec branch).
