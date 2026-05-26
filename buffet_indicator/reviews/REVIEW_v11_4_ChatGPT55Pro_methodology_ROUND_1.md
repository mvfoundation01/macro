# REVIEW v11.4 — ChatGPT 5.5 Pro — Methodology

## Headline summary
- BLOCKERs: 2 (Comments #1, #2)
- MAJORs: 8 (Comments #3–#10)
- MINORs: 2 (Comments #11–#12)
- NITs: 0
- Recommendation: RE-DRAFT_REQUIRED

I do **not** recommend sealing the v2.0 pre-registration as drafted. The two BLOCKERs are narrow but fundamental: the chronology/provenance of the v1.0 verdict appears impossible as written, and the proposed sample gate is likely to make at least Criterion 3 fail by construction before the model is evaluated. The MAJOR comments are mostly fixable pre-seal, but they should be resolved in a revised draft rather than left to implementation interpretation.

### Reviewer calculations performed

**Sample-gate upper-bound check.** Using the roadmap component dates supplied in the review request—NetFed starts 2003-02 and funding stress starts 1986-01—and assuming an analysis-as-of monthly endpoint of 2026-05, the maximum possible OOS counts before any initial-training holdout are:

| Sample start assumption | Total monthly observations | 1Y max OOS vs gate | 3Y max OOS vs gate | 5Y max OOS vs gate | 10Y max OOS vs gate |
|---|---:|---:|---:|---:|---:|
| 2003-02 joint start (if LC_TIER2 includes NetFed) | 280 | 268 vs 90 PASS | 244 vs 270 FAIL | 220 vs 450 FAIL | 160 vs 900 FAIL |
| 1986-01 deep start (if LC_TIER2 excludes NetFed) | 485 | 473 vs 90 PASS | 449 vs 270 PASS | 425 vs 450 FAIL | 365 vs 900 FAIL |

Therefore Criterion 3 is by-construction `not_evaluable` even under the more favorable 1986-start assumption, and Criteria 2–3 are by-construction `not_evaluable` if LC_TIER2 uses the NetFed joint-start sample. Because `not_evaluable` counts as FAIL, the current gate materially predetermines the verdict.

**Decision-rule Type I check.** Under independent identical marginal pass probability `p`, `P(n_pass ≥ 4 of 7)` is:

| Marginal criterion pass probability p | P(n_pass ≥ 4) |
|---:|---:|
| 0.05 | 0.019% |
| 0.10 | 0.273% |
| 0.20 | 3.334% |
| 0.30 | 12.604% |
| 0.50 | 50.000% |

The identical-`p` calculation is too optimistic if non-predictive validity criteria such as stationarity and VIF have high null pass rates. For example, with C5 and C6 pass rates at 0.80, C4 at 0.10, C7 at 0.05, and C1–C3 at 0.10, the independent-null false PASS probability is 4.48%; if C1–C3 are 0.20, it is 11.15%. This is not necessarily fatal, but the pre-reg should document the intended calibration.

## Calibrated meta-assessment

| Outcome | P | 95% CI | Confidence | Conviction |
|---|---:|---:|---:|---:|
| My review will hold up under Strategist arbitration (no BLOCKERs overturned) | 78% | [62%, 90%] | 76% | 4/5 |
| v2.0 sprint will close FAIL despite my recommended fixes | 60% | [43%, 75%] | 72% | 3.5/5 |
| Sealing with my MINOR/NIT-only edits incurs zero re-seal risk over 12 months | 18% | [7%, 34%] | 78% | 4/5 |

## Comment-by-comment review

### Comment #1 — BLOCKER — Chronology and provenance are impossible as written

**Section reference**: §1 Context; §2 v2.0 PREAMBLE; §2 v2.0 §0 metadata

**Issue**: The handoff is dated 2026-05-23, but the v2.0 preamble and metadata say v1.0 was “closed FAIL 2026-05-25” and that the four amendments were extracted from v11.3.0's `verdict.json`. If the package is actually being reviewed and sealed on 2026-05-23, a 2026-05-25 verdict cannot yet be an empirical input. This is either a simple date typo or a serious pre-registration-provenance violation; the draft cannot be sealed until the chronology is made internally consistent.

**Evidence / reference**:
  - Paper or master spec section: Master spec pre-registration discipline, including timestamp/commit proof before backtest execution; Munafò et al. (2017) on prospective specification and transparent reporting.
  - Empirical anchor: Handoff header date is 2026-05-23; §2 preamble says v1.0 was sealed 2026-05-22 and “verdict FAIL on 2026-05-25”; §0 repeats “closed FAIL 2026-05-25.”

**Proposed solution**: Before seal, verify the actual timestamp of `outputs/lc_v1_verdict.json` at commit `d56174c`. Replace all v1.0 verdict dates with the actual commit timestamp. Add this invariant to v2.0 §0: `source_verdict_commit = d56174c; source_verdict_timestamp <= v2_seal_timestamp; source_amendments_file_sha256 = <hash>; source_amendments_commit is ancestor of v2_seal_commit`. If the actual verdict timestamp is after the proposed v2.0 seal timestamp, stop the seal and issue a new handoff after v1.0 is actually closed.

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 91% | [78%, 97%] | 84% | 5/5 |
| Proposed solution causes downstream issue not yet identified | 6% | [1%, 16%] | 86% | 2/5 |
| Original draft was actually correct and this comment is wrong | 12% | [3%, 26%] | 82% | 3.5/5 |
| Alternative solution Y (specify): only correct the displayed date without adding provenance invariants | 18% | [7%, 34%] | 80% | 2.5/5 |

**Falsification criterion for this comment**: Produce repository evidence that `d56174c` and `outputs/lc_v1_verdict.json` were actually created no later than 2026-05-23, and that “2026-05-25” is merely a copied typo not used in any seal/provenance record.

### Comment #2 — BLOCKER — The `5 × HAC_lag` gate creates by-construction FAILs

**Section reference**: §2 v2.0 §3.4; §2 v2.0 §5 Criteria 1–3; roadmap LC component inventory

**Issue**: The sample gate uses `n_obs_oos < 5 × HAC_lag` with `HAC_lag = floor(1.5 × h)`. This yields minimum OOS counts of 90 at 1Y, 270 at 3Y, 450 at 5Y, and 900 at 10Y. Given the LC component availability, the 5Y criterion is not evaluable even under the favorable 1986-start sample, and the 3Y and 5Y criteria are not evaluable under the NetFed joint-start sample; because `not_evaluable` counts as FAIL, the gate predetermines a material share of the verdict.

**Evidence / reference**:
  - Paper or master spec section: Newey and West (1987) and Andrews (1991) concern HAC bandwidth/lag truncation, not a general rule that sample size must exceed `5 × lag`. Hansen and Hodrick (1980) and long-horizon predictive-regression practice typically motivate overlap correction around `h - 1` monthly lags, not `1.5h` plus a separate 5× sample gate.
  - Empirical anchor: NetFed starts 2003-02; funding-stress deep sample starts 1986-01. With an as-of endpoint of 2026-05, max OOS counts are 220 at 5Y from 2003 and 425 at 5Y from 1986, both below the 450 gate.

**Proposed solution**: Replace §3.4 with: `For a monthly h-month forward-return regression, HAC_lag = h - 1 unless v1.0's sealed spec is proven to use a different lag; any deviation must be stated as v1.0 inheritance, not as Andrews automatic bandwidth. A cell is not_evaluable only if n_obs_oos < max(60, 3 × HAC_lag) OR if HAC-adjusted effective sample size n_eff < 30, where n_eff = n_obs_oos / (1 + 2 × sum_{k=1}^{HAC_lag} rho_hat_k) estimated on training residuals with negative autocorrelations truncated at zero for conservatism. The verdict must report raw n_obs_oos, HAC_lag, gate threshold, and n_eff for every composite × horizon cell.` Add a §9 verification item requiring Claude Code to transcribe realized v1.0 `n_obs_oos` by criterion before seal; if Criterion 3 would still be automatically rejected, the Strategist must either relax the gate or explicitly document that Criterion 3 is intentionally non-evaluable.

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 82% | [66%, 92%] | 77% | 4.5/5 |
| Proposed solution causes downstream issue not yet identified | 18% | [7%, 34%] | 80% | 3/5 |
| Original draft was actually correct and this comment is wrong | 8% | [2%, 20%] | 82% | 4/5 |
| Alternative solution Y (specify): keep `1.5h` lag but reduce multiplier from 5× to 3× | 34% | [18%, 53%] | 75% | 3/5 |

**Falsification criterion for this comment**: Produce v1.0 `verdict.json` or v2.0 branch data showing that LC_TIER2 has `n_obs_oos ≥ 270` at 3Y and `n_obs_oos ≥ 450` at 5Y under the exact same expanding-window procedure, without using future or unreleased data.

### Comment #3 — MAJOR — OOS refit timing must specify `s + h ≤ t`

**Section reference**: §2 v2.0 §3.3; roadmap methodological commitment to PIT compliance

**Issue**: §3.3 says that at date `t`, parameters are estimated “using data through `t`” and the prediction is for `t + horizon`. For forward-return regressions, the training pair `(x_s, r_{s,s+h})` is only observable at time `s + h`; using all predictors dated `s ≤ t` would leak future returns into the regression. The draft likely intends PIT evaluation, but the pre-reg must specify the training-set index explicitly because Criteria 1–4 and 7 rely on OOS inference.

**Evidence / reference**:
  - Paper or master spec section: Master spec §2.3 PIT compliance; Goyal and Welch (2008) use historical-mean OOS comparisons that require forecast formation with information available at forecast time.
  - Empirical anchor: v2.0 §3.3 says “parameters are estimated using data through `t`; prediction is for `t + horizon`,” while §3.1 uses horizons up to 10Y.

**Proposed solution**: Replace §3.3 with: `For a forecast origin t and horizon h, the model predicts r_{t,t+h}. The training set at t is {(x_s, r_{s,s+h}) : s + h ≤ t}. Feature values x_t may be used only for the forecast being scored, not as a training observation until r_{t,t+h} is realized. OOS R² is computed from forecasts whose training set satisfied this rule at the forecast origin; the prevailing-mean benchmark is estimated using the same realized-return cutoff s + h ≤ t.` Add `train_cutoff = t - h` and `score_date = t + h` fields to `outputs/lc_v2_verdict.json`.

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 88% | [74%, 96%] | 83% | 5/5 |
| Proposed solution causes downstream issue not yet identified | 7% | [2%, 18%] | 86% | 2/5 |
| Original draft was actually correct and this comment is wrong | 18% | [7%, 34%] | 80% | 3/5 |
| Alternative solution Y (specify): require rolling-window rather than expanding-window refit | 22% | [10%, 39%] | 79% | 2.5/5 |

**Falsification criterion for this comment**: Show that v1.0's sealed spec already contains the exact `s + h ≤ t` training-set rule and that v2.0 will transcribe it verbatim before seal.

### Comment #4 — MAJOR — Skewed-t forecast distribution has a mean/standardization ambiguity

**Section reference**: §2 v2.0 §3.7; §2 v2.0 §6.3 bullet 3

**Issue**: §3.7 names a 4-parameter skewed-t distribution with location `μ`, scale `σ`, skewness `η`, and degrees-of-freedom `ν`, but then defines the conditional forecast as `regression_mean(t) + skewed_t(η_t, ν_t) · σ_t`, omitting `μ_t`. If `skewed_t(η,ν)` is Hansen's standardized zero-mean, unit-variance innovation, then `μ` should be fixed at zero in residual space; if ML estimates a residual location, it must either be added or constrained. As written, the conditional distribution can double-count or ignore the residual mean, which affects probability forecasts and the Brier comparison.

**Evidence / reference**:
  - Paper or master spec section: Hansen (1994) models the full conditional density via a small number of parameters; the standardized skewed-t parameterization is commonly implemented with zero mean/unit variance after transformation. Proper scoring comparisons require comparable predictive distributions.
  - Empirical anchor: v2.0 §3.7 explicitly lists `μ` and `σ` but the forecast equation includes only `σ_t`, `η_t`, and `ν_t` around `regression_mean(t)`.

**Proposed solution**: Replace the forecast equation with one of two explicit choices. Preferred: `Let z ~ HansenSkewT(η_t, ν_t) be standardized to E[z]=0 and Var[z]=1. Fit η_t and ν_t on standardized training residuals e_s = (r_s - regression_mean_s)/sigma_t. Conditional return distribution is r_{t,t+h} = regression_mean(t) + sigma_t z.` Alternative: `If μ_t is estimated on residuals, forecast distribution is regression_mean(t) + μ_t + sigma_t z`, and report a diagnostic that `μ_t` is statistically indistinguishable from zero. Also pre-specify Gaussian fallback scoring only as a diagnostic distribution, not as an unbounded implementation fallback.

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 84% | [68%, 94%] | 77% | 4/5 |
| Proposed solution causes downstream issue not yet identified | 14% | [5%, 29%] | 82% | 2.5/5 |
| Original draft was actually correct and this comment is wrong | 16% | [6%, 31%] | 81% | 3/5 |
| Alternative solution Y (specify): use a Student-t without skewness until residual skew is proven | 30% | [15%, 48%] | 74% | 3/5 |

**Falsification criterion for this comment**: Produce the exact v1.0/v2.0 implementation convention showing `skewed_t(η,ν)` is already defined as standardized zero-mean/unit-variance and that `μ` in §3.7 is only a descriptive label, not an estimated parameter.

### Comment #5 — MAJOR — Criterion 4 uses a one-sided threshold after becoming two-sided

**Section reference**: §2 v2.0 §5 Criterion 4; amendment 2

**Issue**: v2.0 changes Criterion 4 from a positive-sign test to a sign-agnostic magnitude test but keeps `|t_NW| > 1.65`. A threshold of 1.65 corresponds approximately to a one-sided 5% test or a two-sided 10% test, not a two-sided 5% test. This may be acceptable if v2.0 explicitly wants a 10% two-sided evidence threshold, but the draft currently presents the amendment as a semantic correction rather than a loosening of the false-positive rate.

**Evidence / reference**:
  - Paper or master spec section: Standard normal approximation: `P(Z > 1.65) ≈ 0.0495`; `P(|Z| > 1.65) ≈ 0.0989`; `P(|Z| > 1.96) ≈ 0.0500`.
  - Empirical anchor: Criterion 4 table says amended sign-agnostic `|t-statistic| > 1.65` at any evaluable horizon.

**Proposed solution**: Choose and state one of two options. Preferred if Criterion 4 is meant to be a 5% significance criterion: replace `|t_NW| > 1.65` with `|t_NW| > 1.96`. Preferred if maintaining v1.0 target difficulty is more important than classical 5% two-sided inference: keep 1.65 but rename the criterion `two-sided 10% screen` and explicitly state that it is a weak-evidence criterion balanced by the 4-of-7 decision rule and Bonferroni Criterion 7.

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 79% | [62%, 91%] | 76% | 4/5 |
| Proposed solution causes downstream issue not yet identified | 20% | [9%, 37%] | 78% | 2.5/5 |
| Original draft was actually correct and this comment is wrong | 21% | [9%, 38%] | 77% | 3/5 |
| Alternative solution Y (specify): use horizon-level bootstrap p-values instead of t-thresholds | 36% | [19%, 55%] | 73% | 3/5 |

**Falsification criterion for this comment**: Produce the amendment source showing that amendment 2 explicitly intended a two-sided 10% threshold, not a two-sided 5% test, and that this was part of the sealed v2.0 evidentiary design.

### Comment #6 — MAJOR — The 4-of-7 decision rule lacks null calibration and mixes predictive with validity criteria

**Section reference**: §2 v2.0 §2; §2 v2.0 §5 Criteria 1–7

**Issue**: The decision rule treats all seven criteria as interchangeable votes, but Criteria 5 and 6 are validity/diagnostic criteria rather than evidence that LC predicts returns. Under the null of no predictive content, stationarity and low VIF can still pass with high probability, meaning the true false-PASS probability can be materially higher than the all-criteria-nominal calculation. The pre-reg should include a null calibration table and should define whether a PASS requires a minimum number of predictive criteria, not merely total criteria.

**Evidence / reference**:
  - Paper or master spec section: Master spec multi-rule correction commitments; White (2000) on data-snooping adjustment; Holm–Šidák logic for multiple comparisons.
  - Empirical anchor: Criteria 5 (ADF rejects for all components) and 6 (VIF < 5) are not return-predictability tests, but each contributes equally to `n_pass ≥ 4`.

**Proposed solution**: Add §2.1 `Decision-rule calibration` with: `(i) exact independent-null P(n_pass ≥ 4) under stated marginal pass probabilities; (ii) a two-tier PASS definition: total n_pass ≥ 4 AND at least 2 of predictive Criteria {1,2,3,4,7} pass; (iii) a statement that Criteria 5–6 are admissibility checks, not direct predictive evidence.` If the Strategist refuses to change the rule because v1.0 retained the 4-of-7 target, then at minimum add the calibration table and state that v2.0's PASS is a composite-evidence verdict, not a classical familywise 5% significance claim.

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 73% | [55%, 87%] | 74% | 4/5 |
| Proposed solution causes downstream issue not yet identified | 28% | [13%, 47%] | 73% | 3/5 |
| Original draft was actually correct and this comment is wrong | 22% | [9%, 40%] | 76% | 3/5 |
| Alternative solution Y (specify): keep 4-of-7 but publish only criterion-level verdicts, not a binary PASS | 33% | [17%, 52%] | 74% | 3/5 |

**Falsification criterion for this comment**: Provide a simulation or historical-null calibration using v1.0 code showing that the current 4-of-7 rule has an acceptable false-PASS rate under no predictive content even when C5 and C6 are allowed to pass at their empirical rates.

### Comment #7 — MAJOR — The priors section is rhetorically defensive and operationally inert

**Section reference**: §2 v2.0 §4.1–§4.2; owner's question (d)

**Issue**: The 0.5/0.5 priors are defensible, but not for the strongest reason given. The strongest justification is Bayesian model averaging/equipoise across conflicting literature streams and across horizon-dependent mechanisms, not the claim that asymmetric priors are impossible after reading v1.0. In addition, §4.2 says five independent symmetric priors imply a 0.5 composite sign prior, but the independence assumption is false or unnecessary; a symmetric joint distribution can imply a symmetric aggregate sign even with correlated components, while correlated components can still change prior mass on magnitude and evidence strength. Finally, the deterministic 4-of-7 decision rule does not use these priors, so the pre-reg must state what the priors do.

**Evidence / reference**:
  - Paper or master spec section: Schularick and Taylor (2012) support credit-cycle/financial-crisis mechanisms; Adrian and Boyarchenko (2012) support intermediary leverage/risk channels; Fama and French (1988) support long-horizon expected-return/mean-reversion predictability; monetarist/liquidity mechanisms support positive short-horizon priors.
  - Empirical anchor: §4.2 asserts “5 independent symmetric priors → composite prior also 0.5,” while the roadmap anticipates correlated liquidity components and includes a constituent correlation heatmap.

**Proposed solution**: Replace the Strategist note with sealed text, not out-of-band text: `The sign prior is set to 0.5/0.5 as a model-averaging prior across two ex ante plausible mechanisms: liquidity-beta/asset-inflation at short horizons and credit-cycle/discount-rate mean reversion at multi-year horizons. These priors are interpretive only; they do not alter Criteria 1–7 or the PASS/FAIL threshold. They are used to prevent sign-based cherry-picking in narrative interpretation and to justify the sign-agnostic Criterion 4.` Replace §4.2 with: `Because the component priors are symmetric by design, the composite sign prior is also symmetric under the maintained no-directional-tilt assumption; independence is not required for this statement. Correlations affect uncertainty and magnitude, not the 0.5 sign prior.` Add optional literature-tilt sensitivity in an appendix: bank credit and funding stress negative 60/40 at 3Y–10Y; M2 positive 60/40 at 1Y; NetFed and DXY inverse 50/50 absent stronger pre-v1.0 evidence. Do not use these asymmetric priors in the verdict unless the decision rule is explicitly Bayesian.

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 81% | [64%, 92%] | 76% | 4.5/5 |
| Proposed solution causes downstream issue not yet identified | 12% | [4%, 26%] | 83% | 2/5 |
| Original draft was actually correct and this comment is wrong | 17% | [7%, 33%] | 80% | 3/5 |
| Alternative solution Y (specify): use asymmetric priors directly in a Bayesian sign-evidence criterion | 26% | [12%, 44%] | 75% | 3/5 |

**Falsification criterion for this comment**: Show that the master spec or v1.0 pre-reg requires priors to feed a Bayesian scoring rule and that the current 0.5/0.5 priors are already mathematically used in Criteria 1–7 or the verdict.

### Comment #8 — MAJOR — Annual re-test is stability monitoring, not a held-out OOS substitute

**Section reference**: §2 v2.0 §6.1–§6.3; owner's question (c)

**Issue**: The draft acknowledges that no held-out test set is reserved, then says annual re-test “functions as an ongoing falsification window.” That is acceptable as stability monitoring but not as a substitute for a reserved confirmatory OOS window, especially when one calendar year adds only 12 monthly forecast origins and overlapping 1Y returns have far fewer effective independent observations. The Brier-score falsification bullet is also under-specified because it says “is worse” without a confidence interval, effective-sample adjustment, or event definition.

**Evidence / reference**:
  - Paper or master spec section: Munafò et al. (2017) on prospective design and transparent falsification; Goyal and Welch (2008) on OOS equity-premium predictability; proper scoring-rule comparisons require uncertainty quantification when observations are dependent.
  - Empirical anchor: §6.3 uses `n_obs ≥ 36` for 1Y Brier comparison, but 36 overlapping monthly 1Y forecasts are roughly three non-overlapping annual outcome windows.

**Proposed solution**: Reword §6.1–§6.2: `No held-out confirmatory window is reserved; the v2.0 verdict is therefore a sealed re-analysis of existing data plus prospective stability monitoring, not a fresh-OOS confirmation.` Replace §6.3 bullet 3 with: `Let ΔBrier = mean(Brier_skewed_t - Brier_Gaussian) for the pre-specified 1Y event [define event, e.g., SPXTR forward return < 0]. Estimate a 95% CI for ΔBrier using stationary block bootstrap with block length ≥ 12 months, preserving overlapping-return dependence. Amendment 3 is definitively falsified only if the lower bound of the CI is > 0 and n_eff = floor(n_obs/12) ≥ 10; if n_eff < 10, label the comparison PROVISIONAL.` Add a third-FAIL meta-finding criterion: if v2.0 FAILs, write a meta-DECISIONS entry documenting 3-of-3 pre-reg FAILs and what claims remain falsified versus unresolved.

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 86% | [71%, 95%] | 82% | 4.5/5 |
| Proposed solution causes downstream issue not yet identified | 10% | [3%, 23%] | 84% | 2/5 |
| Original draft was actually correct and this comment is wrong | 12% | [4%, 27%] | 83% | 3.5/5 |
| Alternative solution Y (specify): reserve all 2027+ 1Y outcomes as formal holdout and defer PASS until 2028+ | 38% | [21%, 58%] | 73% | 3/5 |

**Falsification criterion for this comment**: Provide a pre-existing master-spec rule explicitly allowing annual re-test with 12 new monthly origins to be called a held-out OOS substitute, or show that the Brier comparison is only descriptive and cannot affect `DEFINITIVELY FALSIFIED` status.

### Comment #9 — MAJOR — Predictive-regression inference corrections are over-broad or under-justified

**Section reference**: §2 v2.0 §3.5–§3.6; §2 v2.0 §9 item 3

**Issue**: The draft says Newey-West with `floor(1.5 × horizon_months)` is identical to v1.0, applies Stambaugh correction only when AR(1) exceeds 0.85, and computes Campbell-Yogo intervals “for all coefficients regardless.” Stambaugh bias is continuous in persistence and residual innovation correlation; Campbell-Yogo is specifically designed for persistent predictors and invalid conventional t-tests, not as a blanket interval for all coefficients. The inference section should distinguish v1.0 inheritance from new methodological justification and should pre-specify when each correction is used.

**Evidence / reference**:
  - Paper or master spec section: Stambaugh (1999) derives finite-sample bias in predictive regressions with lagged stochastic regressors; Campbell and Yogo (2006) develop a pretest and efficient tests for persistent predictors where conventional t-tests over-reject; Hansen-Hodrick/Newey-West overlap correction should match monthly horizon structure.
  - Empirical anchor: §3.6 threshold `AR(1) > 0.85` is not justified by the cited papers; §9 item 3 already admits HAC_lag convention may conflict with master spec §3.5.

**Proposed solution**: Replace §3.6 with: `For each regressor/composite, estimate AR(1) persistence ρ and residual innovation correlation with returns. Report ordinary NW intervals for all coefficients. Apply Stambaugh bias correction and Campbell-Yogo intervals when ρ ≥ 0.80 or when the Campbell-Yogo pretest rejects validity of the conventional t-test; otherwise report CY as not applicable. A sensitivity table reports results under unconditional Stambaugh correction for all horizons but does not determine PASS/FAIL unless pre-specified above.` For §3.5, either transcribe v1.0's exact HAC convention verbatim or adopt the master-spec monthly overlap lag `h - 1` with a DECISIONS entry explaining the change.

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 74% | [56%, 88%] | 74% | 4/5 |
| Proposed solution causes downstream issue not yet identified | 21% | [9%, 39%] | 77% | 3/5 |
| Original draft was actually correct and this comment is wrong | 24% | [11%, 43%] | 75% | 3/5 |
| Alternative solution Y (specify): inherit v1.0 inference verbatim and only document known limitations | 39% | [22%, 58%] | 73% | 3/5 |

**Falsification criterion for this comment**: Show that v1.0's sealed pre-reg already specified the 0.85 threshold and all-coefficient Campbell-Yogo intervals with Strategist rationale, and that v2.0's purpose is strict inheritance rather than methodological correction for inference.

### Comment #10 — MAJOR — Verification items miss source-amendment and realized-boundary checks

**Section reference**: §2 v2.0 §8–§9; owner's questions (a)–(b); Strategist push-back 2

**Issue**: The four §9 verification items are necessary but not sufficient. The draft references an amendments file that is not transcribed, so reviewers cannot verify the four amendments against the source. It also omits the sample-gate boundary check that the Strategist self-review identified, plus invariants for bootstrap count, Brier comparison, training-set timing, and source-amendment hash.

**Evidence / reference**:
  - Paper or master spec section: Master spec pre-registration discipline and immutable threshold requirements; Munafò et al. (2017) on complete transparent reporting.
  - Empirical anchor: §9 currently lists display wording, composite scopes, HAC_lag convention, and unchanged component definitions; §8 invariants omit `n_bootstrap = 50,000` and the exact OOS training-set cutoff.

**Proposed solution**: Add these §9 items before seal: `5. Transcribe realized v1.0 n_obs_oos by composite × horizon and show whether the §3.4 gate would have changed v1.0 Criteria 1–3. 6. Transcribe or hash the amendment source file and include a four-row amendment mapping table. 7. Transcribe exact v1.0 OOS training-set timing; if absent, insert the s+h≤t rule from this review. 8. Add §8 invariants for n_bootstrap=50,000, block-bootstrap family, Brier-score CI algorithm, and source-amendments SHA. 9. Verify Criterion 7's p<0.0025 derives from 20 tests and list the 20 tests. 10. Document whether ADF p<0.05 across five components uses unadjusted, Bonferroni, or Holm–Šidák logic.`

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 88% | [74%, 96%] | 83% | 4.5/5 |
| Proposed solution causes downstream issue not yet identified | 8% | [2%, 20%] | 84% | 2/5 |
| Original draft was actually correct and this comment is wrong | 10% | [3%, 24%] | 84% | 3/5 |
| Alternative solution Y (specify): defer these to Claude Code without sealing them into pre-reg | 19% | [8%, 36%] | 78% | 2/5 |

**Falsification criterion for this comment**: Attach the actual `v11_4_amendment_candidates_FROM_v11_3_0.md`, v1.0 spec, and v1.0 verdict showing that all proposed verification items are already resolved and do not affect any sealed threshold or inference rule.

### Comment #11 — MINOR — Merge-to-main decision should improve discoverability without marketing failed models

**Section reference**: §1 DECISIONS entry; Strategist push-back 1

**Issue**: Option (b) is defensible, but the pharma Phase-II analogy is incomplete: failed clinical trials are not production labels, but they are expected to be publicly discoverable in registries/results databases. A branch-only research record is preservation, not discoverability. The proposed option (b′)—a minimal `RESEARCH_RECORD.md` linked from a low-prominence README footer—is context-dependent but likely a strict improvement if it is constrained to archival metadata and not framed as a product feature.

**Evidence / reference**:
  - Paper or master spec section: ClinicalTrials.gov/FDAAA results-reporting norm that trial results are part of a public research record; LaunchDarkly/Optimizely documentation that stale feature flags add technical debt supports avoiding option (a), but does not support hiding research records entirely.
  - Empirical anchor: §1 says option (b) preserves branch/tag artifacts and estimates 25–40% feature-flag drift risk under option (a); push-back 1 proposes b′ with a root research record and footer link.

**Proposed solution**: Modify §1 Decision to: `Option (b′) — keep v1.0 off production code paths, preserve branch/tag, and add a non-product research index.` Add `RESEARCH_RECORD.md` with fields only: sprint, status FAIL, branch, tag, verdict commit, pre-reg commit, short falsified claim, artifact paths, and “not production / not dashboard signal.” Link it from the README footer as `Research archive` with no dashboard copy and no feature flag. Extend the falsification criterion to include: `If v2.0 also FAILs, write a meta-DECISIONS entry and add it to RESEARCH_RECORD.md.`

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 61% | [42%, 77%] | 68% | 3.5/5 |
| Proposed solution causes downstream issue not yet identified | 24% | [11%, 42%] | 76% | 3/5 |
| Original draft was actually correct and this comment is wrong | 31% | [16%, 50%] | 73% | 3/5 |
| Alternative solution Y (specify): keep option (b) but add only a DECISIONS pointer, no root file | 45% | [27%, 64%] | 72% | 3/5 |

**Falsification criterion for this comment**: Show that adding a tightly scoped research index materially confuses end users or increases production DIAGNOSTIC surfacing risk relative to branch-only preservation.

### Comment #12 — MINOR — TECH_DEBT guardrails need an enforcement owner and more visible misdiagnosis status

**Section reference**: §3 TECH_DEBT guardrail patch

**Issue**: The two guardrails are directionally correct, but enforceability is underspecified. A rule that P0/P1 entries must include reproducible evidence needs a checker or review owner, otherwise it becomes another documentation norm. The misdiagnosis closeout status `RESOLVED-by-reclassification` preserves the lesson, but a distinct `MISDIAGNOSIS` or `RESOLVED-MISDIAGNOSIS` status is more searchable and less likely to be mistaken for a normal fix.

**Evidence / reference**:
  - Paper or master spec section: Master spec REVIEW_PACKAGE disclosure and reproducible pipeline norms; general reproducibility principles from Munafò et al. (2017).
  - Empirical anchor: §3 describes two prior P1 misdiagnoses: CI reported as failing 10/10 when main CI was actually 4/4 success, and Surface timing reported as 30 sec/test when measured at 0.053 sec/test.

**Proposed solution**: Add: `Enforcement: any PR/session that adds or upgrades a P0/P1 TECH_DEBT item must include a CI or reviewer checklist line: evidence_command, expected_output_snippet, audit_artifact_path. Missing fields cause automatic downgrade to P2 until evidence is supplied.` Replace status text with `RESOLVED-MISDIAGNOSIS` and require an audit note with the disproving command. Add Guardrail 3: `Before declaring CI, performance, or bundle-size failures, record a fresh source-of-truth check from the canonical branch and commit, including command, timestamp, and artifact path.`

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 76% | [58%, 89%] | 75% | 4/5 |
| Proposed solution causes downstream issue not yet identified | 11% | [4%, 25%] | 84% | 2/5 |
| Original draft was actually correct and this comment is wrong | 20% | [8%, 37%] | 78% | 3/5 |
| Alternative solution Y (specify): keep wording but enforce via human Strategist review only | 29% | [14%, 48%] | 75% | 2.5/5 |

**Falsification criterion for this comment**: Show that TECH_DEBT.md already has an enforced schema/checker for P0/P1 evidence fields and that `RESOLVED-by-reclassification` is already indexed distinctly in project tooling.

## Specific responses to owner's questions (a)–(d)

**(a) Amendment translation — MAJOR.** I cannot fully verify correctness because `_amendments.md` / `v11_4_amendment_candidates_FROM_v11_3_0.md` was referenced but not transcribed. On internal consistency, §4.1 appears to implement amendment 1, §5 implements amendment 2 directionally but has the 1.65 two-sided-threshold issue, §3.7 implements amendment 3 directionally but has the `μ`/standardization ambiguity, and §3.4 implements amendment 4 in a way that likely makes Criterion 3 fail by construction. Probability the four amendments are correctly translated without further change: 38% [20%, 59%], confidence 70%, conviction 4/5.

**(b) Verification items — MAJOR.** The four §9 items are right but incomplete. Add at least item #5 for realized `n_obs_oos` boundary checks; I would also add source-amendment hash/transcription, OOS training-set timing, `n_bootstrap` invariant, Criterion 7 multiplicity mapping, and ADF multiplicity rule. Probability this expanded verification list is the right fix: 86% [72%, 95%], confidence 82%, conviction 4.5/5.

**(c) Falsification window — MAJOR.** The annual re-test cadence is legitimate as prospective stability monitoring, but it is not a substitute for a reserved OOS window. §6.3 is incomplete because Brier-score “worse” needs a block-bootstrap confidence interval, an event definition, and an effective-sample threshold; criterion reversals based on one year of new 1Y data are too noise-prone to be called definitive. Probability the current falsification design needs revision before seal: 83% [68%, 93%], confidence 78%, conviction 4.5/5.

**(d) 0.5/0.5 priors — MAJOR.** Symmetric 0.5/0.5 priors are defensible, but the best argument is Bayesian model averaging/equipoise across conflicting mechanisms, not “we already saw v1.0 so asymmetry is impossible.” If asymmetric priors were used, I would use mild horizon-specific tilts only: bank credit and funding stress 60/40 toward negative at 3Y–10Y; M2 60/40 toward positive at 1Y; NetFed and DXY inverse 50/50 absent stronger pre-v1.0 evidence. Because the deterministic 4-of-7 rule does not use priors, I recommend keeping 0.5/0.5 and explicitly stating the priors are interpretive anti-cherry-picking constraints. Probability this is the right treatment: 78% [61%, 90%], confidence 75%, conviction 4/5.

## Specific assessment of Strategist push-backs 1–3

**Push-back 1 — option (b′): partial / context-dependent — MINOR.** I do not accept “strictly dominates” as proven, because a root-level research record can become a marketing surface if written loosely. With tight archival schema and a low-prominence README footer, b′ is likely better than branch-only preservation because it matches the clinical-trial norm that failed results remain discoverable while not becoming production claims. P(b′ strictly dominates b under constrained archival design) = 58% [39%, 75%], confidence 68%, conviction 3.5/5.

**Push-back 2 — gate verification: correct but understated — BLOCKER.** Adding item #5 is necessary, but not sufficient. My calculation suggests Criterion 3 is not merely at 35% risk of auto-rejection; it is likely auto-rejected under both the 2003 and 1986 start assumptions, and Criterion 2 is auto-rejected if LC_TIER2 includes NetFed. P(current gate auto-rejects C3 by construction) = 82% [66%, 93%], confidence 78%, conviction 4.5/5.

**Push-back 3 — prior pre-empt note: mostly wrong as drafted — MAJOR.** The note looks defensive and should not be out-of-band. It should be replaced with a sealed Bayesian-model-averaging/equipoise rationale and a clear statement that priors do not enter the deterministic verdict. P(current pre-empt note increases reviewer acceptance without weakening the draft) = 35% [19%, 54%], confidence 74%, conviction 3.5/5; P(rewritten BMA rationale is accepted) = 78% [61%, 90%], confidence 75%, conviction 4/5.

## Items I flagged that the Strategist's self-review missed

- BLOCKER — v1.0 verdict chronology appears impossible as written: 2026-05-25 verdict date in a 2026-05-23 handoff.
- BLOCKER — the `5 × floor(1.5h)` gate likely auto-fails Criterion 3 and possibly Criterion 2 before any model performance is observed.
- MAJOR — OOS training-set timing must state `s + h ≤ t` to avoid look-ahead leakage.
- MAJOR — skewed-t distribution omits/ambiguates residual location `μ` in the forecast equation.
- MAJOR — Criterion 4 changed from one-sided to two-sided without adjusting or disclosing the nominal alpha.
- MAJOR — the decision rule mixes predictive and non-predictive criteria without null calibration.
- MAJOR — 0.5/0.5 priors are operationally inert under the deterministic decision rule and should be explained as interpretive constraints.
- MAJOR — annual re-test cadence is stability monitoring, not a held-out OOS substitute; Brier comparison needs CI and effective-sample threshold.
- MAJOR — Stambaugh and Campbell-Yogo corrections are applied/triggered in a way not justified by the cited methods.
- MAJOR — amendment source hash/transcription and realized n_obs_oos verification are missing from §9.
- MINOR — option (b′) likely improves research discoverability if constrained to archival metadata.
- MINOR — TECH_DEBT guardrails need an enforcement schema and a `RESOLVED-MISDIAGNOSIS` status.

## Falsification criterion for this entire review

Evidence over the next 6 months that would convince me this review was mis-calibrated:

1. Repository provenance shows the 2026-05-25 v1.0 verdict date is a harmless typo and all source amendment files were committed before the v2.0 seal with verifiable hashes.
2. v1.0 or v2.0 realized data show LC_TIER2 has enough OOS observations to satisfy the current 5× gate at 3Y and 5Y without using unreleased future returns.
3. The sealed v1.0 spec already contains unambiguous `s + h ≤ t` OOS training-set timing, standardized skewed-t residual conventions, and the exact HAC/Stambaugh/Campbell-Yogo rules now inherited by v2.0.
4. A simulation using v1.0 code and null predictors shows the current 4-of-7 decision rule has acceptable false-PASS probability after accounting for empirical pass rates of ADF and VIF criteria.
5. Annual post-seal re-tests produce stable criterion-level conclusions with confidence intervals despite the small effective sample, and the Brier comparison is demonstrably insensitive to overlap.

## References consulted

- Adrian, T., & Boyarchenko, N. (2012/2015). *Intermediary Leverage Cycles and Financial Stability*. FRBNY Staff Report No. 567.
- Andrews, D. W. K. (1991). “Heteroskedasticity and Autocorrelation Consistent Covariance Matrix Estimation.” *Econometrica*.
- Campbell, J. Y., & Yogo, M. (2006). “Efficient Tests of Stock Return Predictability.” *Journal of Financial Economics*.
- Fama, E. F., & French, K. R. (1988). “Dividend Yields and Expected Stock Returns.” *Journal of Financial Economics*.
- Goyal, A., & Welch, I. (2008). “A Comprehensive Look at the Empirical Performance of Equity Premium Prediction.” *Review of Financial Studies*.
- Hansen, B. E. (1994). “Autoregressive Conditional Density Estimation.” *International Economic Review*.
- Hansen, L. P., & Hodrick, R. J. (1980). “Forward Exchange Rates as Optimal Predictors of Future Spot Rates.” *Journal of Political Economy*.
- Munafò, M. R., et al. (2017). “A Manifesto for Reproducible Science.” *Nature Human Behaviour*.
- Newey, W. K., & West, K. D. (1987/1994). HAC covariance estimation.
- Politis, D. N., & Romano, J. P. (1994). “The Stationary Bootstrap.” *Journal of the American Statistical Association*.
- Politis, D. N., & White, H. (2004); Patton, Politis, & White (2009 correction). Automatic block-length selection for dependent bootstrap.
- Schularick, M., & Taylor, A. M. (2012). “Credit Booms Gone Bust.” *American Economic Review*.
- Stambaugh, R. F. (1999). “Predictive Regressions.” *Journal of Financial Economics*.
- White, H. (2000). “A Reality Check for Data Snooping.” *Econometrica*.
- LaunchDarkly and Optimizely documentation on stale feature flags and technical debt.
- ClinicalTrials.gov/FDA materials on registration and results-reporting expectations.
