# REVIEW v12 Design — ChatGPT 5.5 Pro — Methodology Review

**Reviewer role:** Methodology reviewer  
**Target:** `REVIEW_REQUEST_ChatGPT55Pro_v12_design.md`  
**Date:** 2026-05-25  
**Scope interpreted:** methodology review of the v11.x FAIL arc and the v12 / retirement design decision. No code review, no v2.0 verdict recomputation.

---

## 0. Executive verdict

**Recommendation:** `PURSUE_v12-A_PRIME_WITH_STRICT_PRECONDITIONS` **and simultaneously publish the 3-of-3 v11.x FAIL as an interim null finding.**

I do **not** recommend jumping directly to v12-B/C/D/E as verdict-bearing designs. I also do **not** recommend formal retirement today without one final narrow test, because v11.4 had a large `NOT_EVALUABLE` component and the proposed rate-family correction targets a coherent methodological mismatch. However, the next iteration must be framed as a **last confirmatory salvage test**, not a broad exploration of velocity/M3/liquidity variants.

**Most defensible design:** `v12-A′` — a constrained variant of v12-A:

1. Convert only the pre-specified problematic level-family components to a flow / rate / shock transform.
2. Fix the PIT z-score warmup contradiction before sealing.
3. Do **not** add M2V or M3 as verdict-bearing components in the same sprint.
4. Keep a legacy comparability readout, but add a stricter confirmatory success rule requiring genuine predictive evidence.
5. Pre-register an alpha-spending / multiple-testing ledger across v11.2 → v12.
6. Pre-register that **if v12-A′ fails, the LC predictive research line is retired** except for the already-sealed 2029 v2.0 re-evaluation.

**Confidence in top pick:** 72 / 100.  
**Conviction:** 4 / 5.  
**Core reason:** v12-A′ is the only design that plausibly addresses v11.4's diagnosed failure modes while minimizing new researcher degrees of freedom. v12-G is almost as defensible, but likely premature because v11.4 was partly not-evaluable rather than purely falsifying.

---

## 1. Headline scorecard of v12 options

| Option | Methodological defensibility | Verdict-bearing recommendation | Confidence | Key reason |
|---|---:|---|---:|---|
| **v12-A′** constrained rate-family repair | **High** | **YES, but only once preconditions are met** | 72% | Smallest perturbation; directly targets level/stationarity/window problem. |
| **v12-G** formal retirement / publish null | High | YES as interim publication, not sole next step | 68% | The 3-of-3 FAIL is real and publishable; but v11.4 not-evaluable status leaves unresolved claims. |
| **v12-F** 2029 sealed re-run | Medium-high | YES as parallel commitment | 65% | Good prospective discipline; too slow and does not address transform mismatch. |
| **v12-B** add M2V | Medium-low | NO as primary v12 | 42% | Theoretically suggestive, but derived from GDP/M2 and quarterly/revision-heavy. |
| **v12-C** add OECD M3 YoY | Low-medium | NO as primary v12 | 30% | M3 is discontinued by Fed; OECD reconstruction has data-quality and vintage concerns. |
| **v12-D** pure velocity redesign | Low | NO | 22% | Too much post-hoc redesign after FAIL; too many new degrees of freedom. |
| **v12-E** stock + flow two-stage | Low-medium | NO unless explicitly exploratory | 35% | Scientifically interesting but doubles multiplicity and invites either-composite cherry-picking. |

---

## 2. Calibrated meta-assessment

| Outcome | P | 95% CI | Confidence | Conviction |
|---|---:|---:|---:|---:|
| v12-A′ is more defensible than immediate retirement alone | 62% | [45%, 77%] | 84% | 4/5 |
| v12-A as written is sealable without modification | 18% | [8%, 33%] | 88% | 4/5 |
| Adding M2V or M3 as verdict-bearing v12 components would materially increase post-hoc-selection criticism | 78% | [61%, 90%] | 86% | 4/5 |
| A 3-of-3 FAIL write-up is publishable as an interim null / methods note | 70% | [52%, 84%] | 84% | 3.5/5 |
| If v12-A′ fails, the LC predictive research line should be retired | 82% | [66%, 92%] | 87% | 4.5/5 |
| v12-A′ will empirically PASS under a strict confirmatory standard | 25% | [12%, 43%] | 84% | 3/5 |
| v12-A′ will be scientifically useful even if it FAILs | 80% | [63%, 91%] | 86% | 4/5 |

---

## 3. Blocking preconditions before any v12 seal

These are not suggestions. If v12 proceeds, these are **must-fix before seal**.

1. **Resolve the PIT z-score warmup contradiction.** v12-A says PIT z-score construction is unchanged, while the root-cause narrative says rate transforms would avoid the 120-month warmup. Both cannot be true if the strict 120-month shift remains.
2. **Define a non-redundant confirmatory decision rule.** The legacy `n_pass ≥ 4 of 7` can remain as a comparability readout, but v12's primary PASS should require stronger predictive evidence than two predictive criteria plus stationarity/VIF.
3. **Create a cross-iteration alpha-spending / data-snooping ledger.** Pre-registration alone does not erase the fact that the same data substrate has been used repeatedly.
4. **Freeze the transform family before viewing any v12 return-prediction outputs.** Codex feasibility diagnostics may examine data availability/stationarity, but not return-prediction performance before pre-registration.
5. **Do not use post-2024 OOS as the sole confirmatory window.** It is too short for 1Y+ horizons as of 2026-05.
6. **Define a retirement trigger.** Suggested: if v12-A′ fails under the primary confirmatory rule, retire US LC predictive claims based on standard FRED liquidity composites, while preserving v2.0's 2029 re-run as an already-sealed prospective check.

---

## 4. Comment-by-comment review

### 1. [§17 / §4.Q6 REFINE + MAJOR] Pursue one final narrow v12, but publish the 3-of-3 FAIL now

**Issue.** The request frames a binary decision: pursue v12 or retire. The cleanest scientific posture is a hybrid: publish the 3-of-3 v11.x FAIL as the current result, while allowing exactly one narrowly constrained v12-A′ as a final diagnostic repair. This avoids pretending the FAILs did not happen, while acknowledging that v11.4 had unresolved not-evaluable claims.

**Reasoning.** Three pre-registered failures are strong evidence against broad macro/liquidity composite predictability, but v11.4 was not a clean all-cells statistical rejection: 4 of 7 criteria were `NOT_EVALUABLE_COUNTED_FAIL`. That makes immediate total retirement defensible but slightly premature. The correct framing is: “The original v11.x hypothesis class failed; a final transform-family repair is now being pre-registered because the failure mode was diagnosed, not because results were cherry-picked.”

**Proposed action.** Write a meta-DECISIONS entry now titled approximately: `Three Pre-Registered Null Results in Macro/Liquidity Equity Prediction: Current Scientific Record and One Final Narrow Extension`. Then seal v12-A′ only if the rest of this review's blockers are addressed.

**Calibration.** P(this hybrid posture is superior to either pure v12 or pure retirement) = 66%, 95% CI [48%, 80%], confidence 84%, conviction 4/5.

**Falsification criterion.** If v2.0's `NOT_EVALUABLE` cells would have remained non-evaluable even under a correctly specified rate-family transform and fixed warmup, then the case for v12-A′ weakens materially.

---

### 2. [§4.Q1 CHALLENGE + MAJOR] The post-hoc-selection defense is plausible but incomplete

**Issue.** The Strategist's defense of v12-A is directionally right but not sufficient. A theory-motivated modification can still be post-hoc if the theory becomes salient only after observing failure.

**Reasoning.** The garden-of-forking-paths critique is not limited to picking variables that passed. It also applies when researchers reinterpret the failed model and select a new transform that would likely make admissibility criteria easier. White (2000) defines data snooping broadly as using the same data more than once for inference or model selection. v12-A therefore needs an explicit “why this transform and no others” rule.

**Proposed action.** Add a sealed section called `Transform-Family Rationale and Anti-Forking Ledger` with:

```text
v12-A′ is not authorized to add/remove components after seal.
Only transformations allowed:
  - For strictly positive stock variables: Δ12 log(x).
  - For potentially nonpositive stock/spread variables: pre-specified signed/asinh or scaled-difference transform.
No transformation may be selected based on return-prediction performance.
All candidate transformations considered and rejected are listed before any return backtest.
```

**Calibration.** P(v12-A without this ledger is vulnerable to p-hacking critique) = 74%, 95% CI [58%, 87%], confidence 85%, conviction 4/5.

**Falsification criterion.** If the rate-transform rule was documented in project materials before v11.4 results were known, the post-hoc-selection concern drops substantially.

---

### 3. [§4.Q2 BLOCKER] Pre-registration is not “absolution”; v12 needs an alpha-spending / data-snooping policy

**Issue.** Option (d), “pre-registration absolution,” is not defensible. Pre-registration sharply reduces selective reporting risk, but it does not remove cross-iteration multiplicity when hypotheses are iteratively revised using the same historical data.

**Reasoning.** Empirical finance has strong warnings about repeated testing and factor discovery. Harvey, Liu, and Zhu argue that conventional significance thresholds are too permissive after many tested factors. White's Reality Check and Hansen's SPA test were designed specifically for comparing many models/strategies against a benchmark under data-snooping risk. The project already recognizes White's Reality Check in its roadmap; v12 should extend that logic to the research-program level.

**Proposed action.** Before seal, create an `ALPHA_SPENDING_LEDGER.md` with rows for v11.2, v11.3, v11.4, v12-A′ and columns:

```text
sprint_id | hypothesis_family | variables | transforms | criteria_count |
primary_success_rule | data_window | OOS_window | statistical correction |
result | whether this informed the next design
```

Then set v12's primary success rule as one of:

1. **Model-family Reality Check / SPA:** v12-A′ must beat historical-mean benchmark and prior LC variants under a bootstrap data-snooping correction; or
2. **Alpha-spending rule:** the primary predictive criterion alpha is reduced, e.g. from 5% to 2.5%, and the final report explicitly states this is the last LC iteration.

**Calibration.** P(v12 needs a cross-iteration multiplicity correction to be methodologically credible) = 82%, 95% CI [67%, 92%], confidence 87%, conviction 4.5/5.

**Falsification criterion.** If v12 is purely descriptive and never produces a PASS/FAIL predictive claim, this blocker becomes a MAJOR rather than BLOCKER.

---

### 4. [§4.Q5 REFINE + MAJOR] Do not mechanically tighten OOS R² thresholds; tighten the decision/inference layer

**Issue.** The Strategist's leaning toward tighter OOS R² thresholds is understandable but not the best penalty mechanism. Raising thresholds changes the economic estimand and may turn v12 into a near-certain FAIL without improving inferential cleanliness.

**Reasoning.** OOS R² thresholds are economic effect-size bars; multiple-testing penalties should usually operate on inferential claims or model-selection claims. Tightening `OOS R² > 0.04` to `>0.06` at 5Y may punish iteration but also makes comparability to v11.4 worse. A better solution is to keep legacy thresholds for comparability but add a stricter primary confirmatory rule.

**Proposed action.** Report two verdict layers:

1. **Legacy-comparable readout:** the old seven criteria, unchanged, reported as `legacy_v11_comparable_verdict`.
2. **Primary v12 confirmatory verdict:** `PASS` only if:
   - admissibility checks pass,
   - at least 3 of 5 predictive criteria pass, and
   - the best v12-A′ specification survives a Reality Check / SPA or equivalent alpha-spending correction.

**Calibration.** P(decision-layer tightening is superior to mechanical OOS R² threshold tightening) = 70%, 95% CI [52%, 84%], confidence 84%, conviction 4/5.

**Falsification criterion.** If the project can justify each higher OOS R² threshold from pre-v11.x literature rather than from iteration penalty, then threshold tightening becomes more defensible.

---

### 5. [§4.Q4 BLOCKER] Post-2024 OOS alone is not an adequate v12 confirmatory sample

**Issue.** Post-2024 OOS is too short as of 2026-05 for any serious 1Y/3Y/5Y forward-return claim. It can be a prospective monitoring window, but not the main v12 PASS authority.

**Reasoning.** For a 1Y horizon, post-2024 gives only a small number of realized annual forward returns; for 3Y/5Y it is essentially unusable now. A “clean” untouched window that is too short is not actually clean evidence; it is just low-powered evidence.

**Proposed action.** Use a three-layer validation plan:

1. **Historical locked walk-forward:** pre-registered expanding-window or blocked time-series CV over all available US history, with all folds and embargoes frozen before execution.
2. **External validity:** international or cross-market test as descriptive/secondary if data quality is high enough.
3. **Prospective monitoring:** post-2024 / 2026-forward observations accumulated annually through 2029, explicitly labeled prospective but not sufficient for immediate PASS unless horizon-specific sample gates are met.

**Calibration.** P(post-2024-only OOS would be underpowered / misleading) = 90%, 95% CI [78%, 96%], confidence 91%, conviction 5/5.

**Falsification criterion.** If v12 is limited to 1M/3M horizons with enough independent post-2024 observations, this concern weakens; but that would be a different hypothesis than the 1Y/3Y/5Y LC thesis.

---

### 6. [§3 v12-A BLOCKER] v12-A contains an internal contradiction: “PIT z-score unchanged” vs “no 120-month warmup”

**Issue.** The request says v12-A keeps PIT z-score construction unchanged, but the root-cause narrative says rate-of-change transforms would avoid the 120-month warmup. If PIT z-scoring still requires a 120-month strict-shift window, a DXY series starting in 2006 still yields a composite valid start around 2016, even if the raw component is a rate of change.

**Reasoning.** Rate-of-change reduces unit-root risk and may reduce transform-level warmup, but it does not by itself eliminate standardization warmup. If v12-A leaves the standardization rule unchanged, the main not-evaluable problem may persist. This must be resolved before seal because it directly determines whether v12 is scientifically testable.

**Proposed action.** Choose one of two explicit paths:

- **Path 1: comparability priority.** Keep the 120-month PIT z-score warmup and admit v12-A′ may still be sample-constrained. Then v12-A′ is mainly a stationarity test, not a window-repair test.
- **Path 2: evaluability priority.** Pre-register a new PIT standardization rule, e.g. expanding PIT z-score with `min_periods = 36` or 60, strict-shifted, and declare this a v12 methodological change requiring its own sensitivity / robustness table.

My preference: Path 2, but only if the warmup change is treated as a first-class v12 amendment, not hidden inside “rate transform.”

**Calibration.** P(the current v12-A description is internally inconsistent on warmup) = 88%, 95% CI [75%, 95%], confidence 90%, conviction 5/5.

**Falsification criterion.** If sealed v11.4 already used an expanding standardization with much shorter minimum period for rate variables, then the contradiction is reduced.

---

### 7. [§3 v12-A REFINE + MAJOR] `Δ12 log(NetFed)` may be an unsafe transform without a positivity rule

**Issue.** v12-A proposes `Δ12 log(NetFed)`. NetFed is a derived balance-sheet difference, not a simple strictly positive money stock by definition. A log transform is invalid if the series can be zero or negative, and fragile if the denominator gets very small.

**Reasoning.** Even if historical NetFed has been positive in the current sample, the transform should be defined by admissibility logic rather than empirical luck. A signed macro-liquidity aggregate may require a scaled difference or asinh transform.

**Proposed action.** Add a transform decision tree before seal:

```text
If component is strictly positive by construction across all possible valid observations:
    transform = Δ12 log(x)
Else:
    transform = Δ12 asinh(x / scale_t)
    where scale_t is pre-specified using only prior data, e.g. rolling 120m median absolute level.
```

Alternatively, define NetFed flow as `Δ12(NetFed) / nominal_GDP_lagged` if GDP-vintage handling is available; otherwise avoid GDP normalization until v11.5 vintage infrastructure exists.

**Calibration.** P(`Δ12 log(NetFed)` needs a positivity/transform rule before seal) = 76%, 95% CI [57%, 89%], confidence 84%, conviction 4/5.

**Falsification criterion.** If NetFed is proven strictly positive by construction, not merely in observed data, then `Δ12 log` is acceptable.

---

### 8. [§3 v12-A REFINE + MAJOR] Funding stress is not obviously “rate-family” if left unchanged

**Issue.** v12-A says all five components are converted to rate-of-change, while z5 funding stress is left unchanged because it is “already rate-family.” A spread is a difference between rates, but it is still a level of the spread. It may be stationary, but it is not a rate-of-change or velocity variable.

**Reasoning.** If v12's scientific claim is “flow/shock family beats level family,” z5 needs a clear classification. A rate spread can be stationary and economically meaningful as a state variable, but then v12-A′ is not purely rate-of-change; it is “non-integrated / stationary-transform family.” That is a better label.

**Proposed action.** Rename v12-A from “all converted to rate-of-change” to **“stationarity-preserving liquidity transform family.”** Classify each component as one of:

- stock-level transformed to flow: z1, z4;
- already flow: z2, z3;
- stationary state/spread: z5.

Then pre-register whether z5 is kept as level spread or converted to `Δ12 spread` in a sensitivity-only appendix.

**Calibration.** P(current z5 wording is conceptually loose) = 72%, 95% CI [54%, 86%], confidence 84%, conviction 4/5.

**Falsification criterion.** If v11.4's sealed taxonomy already defined spreads as rate-family and this taxonomy is reused consistently across the project, this is a wording refinement rather than a major issue.

---

### 9. [§4.Q3 LITERATURE + REFINE] The literature supports shocks/flows more than money-stock levels, but not necessarily M2V/M3 equity prediction

**Issue.** The Strategist's literature read is directionally correct: the stronger empirical asset-pricing evidence is in leverage shocks, credit-market sentiment, funding liquidity, and constrained-intermediary channels. But that does not automatically validate M2V or OECD M3 as equity predictors.

**Reasoning.** Adrian-Etula-Muir uses broker-dealer leverage shocks / intermediary balance sheets, not M2 velocity. Brunnermeier-Pedersen gives a mechanism for market/funding liquidity spirals, not a direct M2V-to-SPX rule. Campbell-Thompson shows stock-return prediction may work under restrictions but with small OOS explanatory power. Goyal-Welch is the canonical warning that many predictors fail to beat the historical mean out of sample.

**Proposed action.** In the v12 pre-reg, separate literature into three buckets:

1. **Directly relevant to equity-return prediction:** OOS predictive regression literature and intermediary asset pricing.
2. **Relevant to macro/liquidity mechanism, indirect to equities:** money velocity, quantity theory, credit cycles.
3. **Data construction / measurement only:** M3, M2V definitions, monetary aggregate measurement.

Only bucket 1 should justify primary verdict-bearing components.

**Calibration.** P(rate/shock literature supports v12-A′ more than v12-B/C) = 75%, 95% CI [58%, 88%], confidence 85%, conviction 4/5.

**Falsification criterion.** A high-quality paper showing M2V or reconstructed M3 robustly predicts aggregate US equity returns OOS, with multiple-testing control, would change this assessment.

---

### 10. [§3 v12-B CHALLENGE + MAJOR] M2V should not be a primary v12 component

**Issue.** M2V is theoretically interesting but methodologically dangerous as a verdict-bearing v12 addition immediately after v11.4 FAIL.

**Reasoning.** M2V is calculated as nominal GDP divided by M2; FRED describes it exactly this way. That means Δlog(M2V) is mechanically Δlog(nominal GDP) − Δlog(M2). It imports GDP revisions, quarterly frequency, interpolation choices, and business-cycle information. It may add real information, but the burden is to prove incremental value beyond M2 growth and nominal GDP cycle, not to assume it.

**Proposed action.** Put M2V in an **exploratory appendix only** unless it passes a pre-sealed incremental-information test:

```text
M2V can become verdict-bearing in v13 only if, in v12 exploratory diagnostics,
its incremental predictive content vs {M2 YoY, nominal GDP YoY, NBER recession proxy}
passes a pre-specified out-of-sample test with multiple-testing correction.
```

For v12, do not add it to the main composite.

**Calibration.** P(adding M2V now would materially weaken v12's anti-p-hacking posture) = 80%, 95% CI [64%, 91%], confidence 86%, conviction 4.5/5.

**Falsification criterion.** If M2V was listed as a future component in the approved roadmap before any LC results were known, the post-hoc concern drops, but the frequency/revision concerns remain.

---

### 11. [§3 v12-C / §14 CLAIM-3 CHALLENGE + MAJOR] OECD-derived M3 is not fit as a primary v12 predictor without a data-quality audit

**Issue.** US M3 is not Fed-published after 2006; the FRED MABMM301USM189S series is OECD-derived. The Federal Reserve discontinued M3 because it judged M3 did not add information beyond M2 for economic activity and did not play a role in monetary policy.

**Reasoning.** That does not prove M3 has no equity-predictive content, but it raises the prior burden sharply. If M3 is used, the pre-reg must address reconstruction methodology, vintage availability, publication lag, splice behavior at 2006, and whether the OECD series is stable enough for PIT predictive analysis.

**Proposed action.** Treat M3 as `RESEARCH_ONLY_NOT_VERDICT_BEARING` in v12. Codex can run a data-quality audit, but the audit should not view SPX return-prediction performance. If M3 survives measurement scrutiny, make it a v13 candidate with a separate pre-reg.

**Calibration.** P(M3 should be excluded from v12 primary verdict) = 83%, 95% CI [68%, 93%], confidence 87%, conviction 4.5/5.

**Falsification criterion.** A documented OECD vintage methodology proving stable PIT availability and incremental information beyond M2 would move this from MAJOR to MINOR.

---

### 12. [§3 v12-D / v12-E CHALLENGE + MAJOR] Radical redesign and two-stage composites are too fork-prone for the next step

**Issue.** v12-D and v12-E are scientifically interesting, but not appropriate as the immediate follow-up to v11.4. They introduce too many new component-selection and decision-rule degrees of freedom.

**Reasoning.** v12-D changes the hypothesis class so much that a PASS would be hard to interpret relative to the v11.x FAIL arc. v12-E doubles the tested objects and creates a dangerous `EITHER` vs `BOTH` decision choice. If `EITHER` passes, Type I error inflates; if `BOTH` passes, power collapses.

**Proposed action.** If the project wants stock-vs-flow separation, do it as a **diagnostic decomposition inside v12-A′**, not as a separate verdict. Example: report LC_FLOW and LC_STOCK panels descriptively, but primary PASS authority remains only with the pre-sealed v12-A′ composite.

**Calibration.** P(v12-D/E would face stronger post-hoc-selection criticism than v12-A′) = 85%, 95% CI [70%, 94%], confidence 88%, conviction 4.5/5.

**Falsification criterion.** If v12-D/E were fully specified in the roadmap before v11.4 and not derived from observed failure modes, they become more defensible.

---

### 13. [§4.Q8 / §14 CLAIM-2 CHALLENGE + MAJOR] Velocity is distinct economically, but mechanically entangled with M2 growth and GDP

**Issue.** The owner's velocity intuition is real, but its empirical test is not clean. M2V is mathematically linked to nominal GDP and M2. Adding both M2 YoY and M2V can double-count a GDP-cycle residual.

**Reasoning.** `M2V = nominal GDP / M2`, so `Δlog(M2V) = Δlog(nominal GDP) − Δlog(M2)`. If z2 is M2 YoY, then ΔM2V embeds the negative of z2 plus nominal GDP growth. A PASS driven by M2V may be a disguised macro-growth signal, not liquidity-speed alpha.

**Proposed action.** If velocity is studied, pre-register one of these tests:

1. **Residual velocity:** regress Δlog(M2V) on Δlog(M2) and nominal GDP growth using only prior data, then test the residual.
2. **Horse race:** compare `{M2 YoY}` vs `{M2V}` vs `{M2 YoY + M2V}` under identical OOS folds with Reality Check correction.
3. **Macro-channel framing:** reclassify M2V as a macro-economy component, not liquidity component.

**Calibration.** P(M2V adds limited independent information unless residualized/horse-raced) = 68%, 95% CI [49%, 83%], confidence 83%, conviction 3.5/5.

**Falsification criterion.** If M2V materially improves OOS forecasts after controlling for M2 YoY and nominal GDP growth under sealed folds, this comment is wrong.

---

### 14. [§12 ESCALATE + MAJOR] Same data substrate is acceptable, but cross-iteration learning must be charged to the research program

**Issue.** Using FRED/M2/BUSLOANS/DXY repeatedly is not “leakage” in the strict PIT sense, but it is information reuse at the researcher level. The modeler has learned from previous failures on the same historical sample.

**Reasoning.** The correct concept is not data leakage inside a backtest; it is research-program data snooping. The remedy is not to ban data reuse, because financial history is finite. The remedy is to document the reuse and penalize claims accordingly.

**Proposed action.** Add a section to v12 pre-reg:

```text
Cross-Iteration Learning Disclosure:
The v12 transform family was selected after observing v11.4 failure modes.
This is a confirmatory repair test, not an independent discovery test.
Primary claims will be discounted via <chosen correction> and v12 is final for this research line if it fails.
```

**Calibration.** P(data-substrate sharing is acceptable with explicit correction/disclosure) = 78%, 95% CI [61%, 90%], confidence 86%, conviction 4/5.

**Falsification criterion.** If v12 chooses variables/transforms after viewing new return-prediction diagnostics, the concern escalates to BLOCKER.

---

### 15. [§13 ENDORSE + MAJOR] The 3-of-3 null finding should be written up regardless of v12

**Issue.** The v11.x results are already scientifically meaningful. Delaying publication until v12 risks turning the null result into a moving target.

**Reasoning.** The architecture itself is valuable: sealed pre-regs, mechanical verdicts, reviewer arbitration, and failed tests preserved. Registered Reports and preregistration initiatives explicitly aim to reduce publication bias against negative results. Finance has fewer such examples than psychology/medicine, which makes this contribution more, not less, valuable.

**Proposed action.** Draft a working paper / research note now:

> “Three Pre-Registered Tests of Macro/Liquidity Composite Predictability for U.S. Equity Returns: Null Results and Lessons for Financial Signal Design.”

Label v12-A′ as a planned extension, not as a condition for whether the null paper exists.

**Calibration.** P(the 3-of-3 FAIL is publishable as an interim null/methodology note) = 70%, 95% CI [52%, 84%], confidence 84%, conviction 3.5/5.

**Falsification criterion.** If the project cannot make the sealed artifacts independently auditable outside the private repo, publication value drops.

---

### 16. [§4.Q7 REFINE + MINOR] Publication venue: SSRN first, then targeted outlet; do not aim first at JFE

**Issue.** JFE/JF/RFS are unlikely first targets for a private-system negative-result note unless the contribution is broadly novel. The most pragmatic path is SSRN + a responsible-science / empirical finance outlet.

**Reasoning.** Pacific-Basin Finance Journal has a pre-registration initiative, but may not fit a US-only study. A methods-oriented paper could target an open-science, replication, or empirical finance venue; a working paper is the correct initial vehicle.

**Proposed action.** Publish in stages:

1. SSRN / OSF archive with sealed artifacts and hashes.
2. Short methodology note around pre-registration architecture and null findings.
3. Later journal submission only after v12-A′ or 2029 re-run clarifies the unresolved claims.

**Calibration.** P(SSRN/OSF first is superior to immediate top-journal submission) = 78%, 95% CI [60%, 90%], confidence 85%, conviction 4/5.

**Falsification criterion.** If an editor explicitly invites a registered/negative empirical-finance submission, move directly to journal.

---

### 17. [§14 CLAIM-1 CHALLENGE + MAJOR] “Converting z1/z4 would fix the failure modes” is too strong

**Issue.** Rate transforms may fix the admissibility and data-window symptoms, but they do not imply predictive signal. The phrase “would fix the failure modes” should be softened.

**Reasoning.** It likely improves stationarity for DXY and may reduce the component-level warmup, but if the PIT z-score warmup remains, data-window constraints can persist. Also, even stationary predictors may have zero OOS return-predictive content.

**Proposed action.** Replace the claim with:

> “Converting z1/z4 to pre-specified stationary/flow transforms is expected to reduce unit-root and evaluability failures. It does not, by itself, increase the prior probability of equity-return predictability enough to justify a PASS claim without new OOS evidence.”

**Calibration.** P(original claim is overstated) = 86%, 95% CI [72%, 94%], confidence 89%, conviction 4.5/5.

**Falsification criterion.** If Codex's admissibility audit shows all v12-A′ cells become evaluable and the stationarity/VIF criteria pass without weakening sample gates, “fixes failure modes” becomes mostly correct for admissibility only.

---

### 18. [§14 CLAIM-2 CHALLENGE + MAJOR] M2V and M2 YoY may capture different stories, but not independent evidence by default

**Issue.** The claim that velocity and money-stock growth both belong in v12 overstates the case. They may belong in the broader research agenda, but adding both to one confirmatory composite risks overweighting monetary aggregates.

**Reasoning.** Since ΔM2V already contains −ΔM2 mechanically, a composite with both M2 YoY and M2V may partially create a long/short combination of M2 and nominal GDP. That can be legitimate, but the hypothesis should then be “nominal spending pressure relative to money supply predicts equities,” not generic liquidity.

**Proposed action.** Defer M2V to a v13 or appendix horse race. Do not put it in the primary v12-A′ composite.

**Calibration.** P(adding both as primary components causes double-counting/misinterpretation risk) = 72%, 95% CI [53%, 86%], confidence 84%, conviction 4/5.

**Falsification criterion.** If component correlation and incremental OOS tests show M2V is orthogonal to M2 growth in the relevant windows, this concern weakens.

---

### 19. [§14 CLAIM-3 CHALLENGE + MAJOR] M3 legitimacy is the weakest of the three provocations

**Issue.** M3 can be studied, but the burden of proof is high. The Fed's own discontinuation rationale directly undermines an assumption that M3 adds material information beyond M2.

**Reasoning.** The Fed said M3 did not appear to convey additional information about economic activity not already in M2 and had not played a role in monetary policy for many years. That is not the same target as equity returns, but it is a strong prior against using M3 as a primary predictor without a data-quality and incremental-value case.

**Proposed action.** Exclude M3 from v12 primary design. Require a separate M3 feasibility note covering:

- OECD construction and revision history;
- exact release calendar / vintage availability;
- comparison to official discontinued Fed M3 through 2006;
- incremental information relative to M2 and institutional MMF/repo components.

**Calibration.** P(M3 should not be a v12 primary predictor) = 85%, 95% CI [70%, 94%], confidence 88%, conviction 4.5/5.

**Falsification criterion.** If OECD M3 has high-quality ALFRED-like vintages and materially different component exposure from M2 post-2006, this moves to a lower-severity concern.

---

### 20. [§4.Q4 REFINE + MAJOR] International OOS is valuable but should be secondary, not the primary PASS authority

**Issue.** International validation is a good external validity check, but it may not be directly comparable to the US LC hypothesis because central-bank balance sheets, money aggregates, DXY exposure, and equity-market structures differ.

**Reasoning.** If v12-A′ fails internationally but passes in the US, that could be because the US liquidity channel is unique. If it passes internationally but fails in the US, the original US hypothesis still fails. International evidence should strengthen or weaken interpretation, not replace the US test.

**Proposed action.** Use international OOS as `secondary_external_validity`. Pre-register no primary PASS solely from international data unless the hypothesis is rewritten as a global LC hypothesis.

**Calibration.** P(international OOS is useful as secondary but not primary validation) = 74%, 95% CI [55%, 88%], confidence 83%, conviction 4/5.

**Falsification criterion.** If v12 is explicitly reframed as “global liquidity predicts global equity returns,” then international data can become primary.

---

### 21. [§4.Q3 LITERATURE + MINOR] Level predictors exist, but they are usually valuation/ratio levels, not raw monetary levels

**Issue.** The request asks whether papers support LEVEL-family variables predicting equity returns. Yes, but the better-known level predictors are valuation ratios: dividend-price, earnings-price, term spread, default spread, book-to-market, CAPE-type variables — not raw M2 or DXY levels as liquidity stocks.

**Reasoning.** This matters because “level vs flow” is not a universal rule. Some levels are theoretically stationary valuation ratios; others are integrated nominal aggregates. The v12 lesson should be “avoid nonstationary level aggregates,” not “levels never predict returns.”

**Proposed action.** In v12, use the term **integrated stock variables** rather than “level-family” when criticizing z1/z4. This avoids overgeneralizing beyond the LC context.

**Calibration.** P(wording should distinguish integrated stocks from stationary ratios) = 78%, 95% CI [61%, 90%], confidence 86%, conviction 4/5.

**Falsification criterion.** If the project taxonomy already defines “level-family” narrowly as integrated stock variables, this is just wording.

---

### 22. [§4.Q6 REFINE + MAJOR] Retirement should be rule-based, not mood-based

**Issue.** The project needs a formal stopping rule. Otherwise every FAIL can generate a new “diagnosed and addressable” story.

**Reasoning.** The v11.4 process has high integrity, but the research line is now close to the boundary where further iteration becomes self-justifying. A pre-registered retirement rule protects the owner from the sunk-cost fallacy.

**Proposed action.** Add this to meta-DECISIONS:

```text
Stopping rule:
If v12-A′ fails under its primary confirmatory decision rule, the US LC predictive research line using standard public macro/liquidity aggregates is retired for at least 24 months, except for the already-sealed 2029 v2.0 re-run. Future liquidity work must be either (a) non-predictive diagnostic dashboarding, or (b) a genuinely new data domain, not another transformation of the same FRED components.
```

**Calibration.** P(a formal stopping rule is necessary before v12) = 84%, 95% CI [69%, 93%], confidence 88%, conviction 4.5/5.

**Falsification criterion.** If v12-A′ produces a mixed result with clear prospective validation constraints, a softer stop/pause rule may be appropriate.

---

### 23. [§5 REFINE + MINOR] Pre-commitments are strong; add one sentence forbidding predictive exploratory peeking

**Issue.** The stated pre-commitments are strong but do not explicitly prohibit predictive exploration during Codex feasibility work.

**Reasoning.** The parallel Codex request includes candidate-data diagnostics. This is acceptable if limited to data availability, stationarity, frequency, vintage, and transform feasibility. It becomes problematic if return-prediction performance is inspected before the v12 pre-reg is sealed.

**Proposed action.** Add:

> “Before the v12 pre-registration seals, any empirical feasibility work may inspect candidate series availability, missingness, release/vintage behavior, stationarity, autocorrelation, and transform validity, but may not inspect SPX forward-return predictability, OOS R², t-statistics against returns, or return-conditioned plots.”

**Calibration.** P(this added sentence materially improves pre-reg discipline) = 77%, 95% CI [59%, 89%], confidence 85%, conviction 4/5.

**Falsification criterion.** If Codex's scope is already explicitly non-predictive in its own request, this is a NIT.

---

### 24. [§7 / Codex parallel review ESCALATE + MAJOR] Codex feasibility diagnostics must not become informal model selection

**Issue.** The review request says Codex may pull candidate v12 data and compute ADF/KPSS/autocorrelation. That can be legitimate feasibility analysis, but it can also influence design selection.

**Reasoning.** If Codex reports “M2V looks stationary and M3 looks great,” even without returns, the Strategist may pick variables based on sample behavior. This is less severe than predictive p-hacking, but still a design-selection path.

**Proposed action.** Require Codex to separate outputs into:

- `ADMISSIBILITY_ONLY`: missingness, frequency, vintages, stationarity, transform validity;
- `NO_RETURN_LINKAGE`: explicitly no SPX/return data loaded;
- `CANDIDATE_NOT_SELECTED`: if a variable is rejected, document why;
- `SELECTION_RULE`: final v12 component selection must follow pre-written design principles, not empirical attractiveness.

**Calibration.** P(Codex diagnostics could accidentally bias v12 design if unconstrained) = 63%, 95% CI [44%, 79%], confidence 82%, conviction 3.5/5.

**Falsification criterion.** If component selection is already frozen before Codex diagnostics, the concern disappears.

---

### 25. [§4.Q10 ESCALATE + MAJOR] Missing methodology angle: negative controls and placebo horizons

**Issue.** The request does not mention negative controls. Given repeated iteration, v12 should include placebo tests to detect spurious composite construction.

**Reasoning.** A liquidity composite that “predicts” impossible or irrelevant outcomes is not credible. Negative controls can reveal overfit structure even when formal OOS metrics look acceptable.

**Proposed action.** Add non-verdict but mandatory diagnostics:

1. **Temporal placebo:** future LC should not predict past returns after alignment checks.
2. **Outcome placebo:** LC should not predict a deliberately unrelated transformed series.
3. **Component permutation:** randomly permuted component dates should not pass C1-C4/C7.
4. **Sign placebo:** if all component signs are randomly flipped, performance should degrade or become unstable.

These do not replace primary criteria but should be reported.

**Calibration.** P(negative controls improve credibility without excessive complexity) = 74%, 95% CI [56%, 87%], confidence 84%, conviction 4/5.

**Falsification criterion.** If implementation budget is too constrained and v12 is only a final narrow test, these can move to appendix rather than seal-blocking.

---

## 5. Direct answers to Q1–Q10

### Q1 — Post-hoc selection critique

**Answer:** The defense is partially adequate but not complete. v12-A differs from p-hacking only if the transform rule is frozen before return-predictive analysis, the full candidate-set ledger is disclosed, and v12 is labeled a final confirmatory repair test rather than a clean independent discovery. Without those constraints, the critique remains valid.

**Rating:** `REFINE / MAJOR`  
**Probability defense is adequate after my proposed safeguards:** 72% [55%, 86%].

### Q2 — Multiple-testing correction across sprint iterations

**Answer:** Use option (b), not (d). Pre-registration does not absolve cross-iteration multiplicity. A full Bonferroni across all criteria is probably too blunt, but v12 needs a program-level alpha ledger plus Reality Check / SPA or a clearly stated alpha-spending penalty. Treat v12 as a final alpha spend, not a fresh independent test.

**Rating:** `BLOCKER` before v12 seal.

### Q3 — Literature on velocity vs level

**Answer:** The Strategist is right that flows/shocks/intermediary balance-sheet changes have stronger asset-pricing support than raw monetary levels. M2V support is mostly macro/inflation/nominal-spending support, not direct equity-prediction support. M3 is weakest because it is discontinued/reconstructed and must pass a measurement audit before serious use.

**Rating:** `LITERATURE / REFINE`.

### Q4 — Held-out OOS period

**Answer:** The cleanest path is not post-2024 alone. Use locked historical walk-forward as primary, post-2024 as prospective monitoring, and international OOS as secondary external validity. Pre-1970 is elegant but likely infeasible for NetFed-style components.

**Rating:** `REFINE / BLOCKER` if post-2024-only is proposed.

### Q5 — Significance thresholds

**Answer:** Do not mechanically tighten OOS R² thresholds. Keep legacy thresholds for comparability, but tighten the primary decision rule and model-family inference. A non-redundant predictive-evidence gate is better than arbitrary higher effect-size bars.

**Rating:** `REFINE / MAJOR`.

### Q6 — When is 3-of-3 FAIL enough?

**Answer:** It is enough to publish a null finding now. It is not quite enough to ban one final narrow v12-A′ repair, because v11.4 had not-evaluable claims. If v12-A′ fails, it is enough to retire the US LC predictive line.

**Rating:** `REFINE / MAJOR`.

### Q7 — Publication strategy

**Answer:** SSRN/OSF working paper first, then a responsible-science / empirical-finance / replication outlet. Do not lead with JFE unless the paper is reframed as a broader methodological contribution with independently auditable artifacts.

**Rating:** `REFINE / MINOR`.

### Q8 — Velocity theoretical grounding

**Answer:** Velocity is economically meaningful but mechanically entangled with M2 and nominal GDP. It should be treated as a separate macro-channel hypothesis or residualized/horse-raced, not simply added to LC.

**Rating:** `CHALLENGE / MAJOR`.

### Q9 — Pushback on Strategist's leaning

**Answer:** v12-A is the right direction, but four parts need correction:

1. `v12-A` must become `v12-A′` with a fixed warmup/transform rule.
2. Tighter thresholds are less clean than a stricter decision/inference layer.
3. Post-2024 OOS cannot carry near-term PASS authority.
4. “If v12-A fails, retire” is correct and should be sealed before v12 starts.

**Rating:** `REFINE / MAJOR`.

### Q10 — Missing angles

**Answer:** Add negative controls, a research-program alpha ledger, a retirement rule, and a strict boundary on Codex pre-seal diagnostics. Also distinguish integrated-stock variables from valuation-ratio levels; the project should not learn the wrong lesson that all levels are bad.

**Rating:** `ESCALATE / MAJOR`.

---

## 6. Recommended v12-A′ skeleton

This is the design I would be willing to review for sealing.

### 6.1 Hypothesis

> Stationarity-preserving liquidity transforms — rather than mixed integrated-stock and flow transforms — predict forward U.S. equity total returns at 1Y/3Y/5Y horizons under PIT construction and pre-registered OOS evaluation.

### 6.2 Component transform policy

| Component | v11.4 issue | v12-A′ transform policy | Verdict-bearing? |
|---|---|---|---|
| z1 NetFed | Level stock; possible nonstationarity; log safety issue | Use pre-sealed positive-log or signed/asinh scaled-change rule | Yes |
| z2 M2 YoY | Already flow | Keep unchanged | Yes |
| z3 Bank lending YoY | Already flow | Keep unchanged | Yes |
| z4 DXY inverse | Integrated price-index level; ADF failure | Use `-Δ12 log(DXY)` or equivalent pre-sealed DXY depreciation transform | Yes |
| z5 Funding stress | Spread level; likely stationary but not flow | Keep as stationary spread, or pre-specify Δspread as sensitivity only | Yes, if taxonomy clarified |
| M2V | Derived GDP/M2 | Exploratory appendix only | No |
| M3 YoY | OECD reconstructed / Fed discontinued | Data-quality appendix only | No |

### 6.3 Standardization

Choose before seal:

- **Option A:** 120-month strict-shift PIT z-score for comparability; admits possible sample constraints.
- **Option B:** expanding strict-shift PIT z-score with `min_periods = 60` or 36; increases evaluability but is a v12 methodology change.

Do not claim rate transforms solve warmup unless Option B is adopted and defended.

### 6.4 Primary success rule

Recommended:

```text
Primary v12-A′ PASS iff all conditions hold:
1. Admissibility: C5 stationarity and C6 VIF pass.
2. Predictive evidence: at least 3 of 5 predictive criteria {C1,C2,C3,C4,C7} pass.
3. Model-family correction: v12-A′ survives pre-specified Reality Check / SPA / alpha-spending correction against historical mean and prior LC variants.
4. No sample-gate loophole: a PASS cannot depend on a criterion whose relevant horizon has fewer than the sealed minimum effective observations.
```

Also report the old `n_pass ≥ 4 of 7` as `legacy_v11_comparable_verdict`, not as the primary v12 claim.

### 6.5 Retirement rule

```text
If primary v12-A′ verdict is FAIL, retire the U.S. LC predictive research line using standard public macro/liquidity aggregates for at least 24 months, except for the sealed v2.0 2029 re-evaluation.
```

---

## 7. Suggested source/literature anchors for the v12 pre-reg

### Multiple testing / data snooping

- White, H. (2000). “A Reality Check for Data Snooping.” *Econometrica*.  
  Use for: research-program data reuse and model-family correction.
- Hansen, P. R. (2005). “A Test for Superior Predictive Ability.” *Journal of Business & Economic Statistics*.  
  Use for: SPA correction as less sensitive to poor alternatives.
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). “… and the Cross-Section of Expected Returns.” *Review of Financial Studies*.  
  Use for: higher hurdles after many tested factors.
- McLean, R. D., & Pontiff, J. (2016). “Does Academic Research Destroy Stock Return Predictability?” *Journal of Finance*.  
  Use for: out-of-sample/post-publication decay and data-mining upper-bound logic.

### Equity return prediction

- Goyal, A., & Welch, I. (2008). “A Comprehensive Look at The Empirical Performance of Equity Premium Prediction.” *Review of Financial Studies*.  
  Use for: historical mean benchmark and difficulty of OOS equity-premium prediction.
- Campbell, J. Y., & Thompson, S. B. (2008). “Predicting Excess Stock Returns Out of Sample.” *Review of Financial Studies*.  
  Use for: economically motivated restrictions and small but meaningful OOS explanatory power.

### Liquidity / intermediary mechanism

- Adrian, T., Etula, E., & Muir, T. (2014). “Financial Intermediaries and the Cross-Section of Asset Returns.” *Journal of Finance*.  
  Use for: intermediary leverage shocks, not direct M2V.
- Brunnermeier, M. K., & Pedersen, L. H. (2009). “Market Liquidity and Funding Liquidity.” *Review of Financial Studies*.  
  Use for: liquidity spirals and funding-market mechanism.
- López-Salido, D., Stein, J. C., & Zakrajšek, E. (2017). “Credit-Market Sentiment and the Business Cycle.” *Quarterly Journal of Economics*.  
  Use for: credit-market sentiment and macro cycle, not direct equity-return proof.

### Monetary aggregates / velocity / M3

- FRED M2V documentation: M2V is nominal GDP divided by quarterly average M2.  
  Use for: mechanical identity and revision/frequency implications.
- Federal Reserve M3 discontinuation notice: M3 did not appear to add information beyond M2 for economic activity and did not play a policy role.  
  Use for: prior against M3 as primary predictor.
- Federal Reserve FEDS Note (2024) on monetary aggregates.  
  Use for: modern confirmation of M3 discontinuation rationale.

### Pre-registration / negative results

- Pacific-Basin Finance Journal pre-registration initiative / Faff (2023).  
  Use for: finance-specific preregistration precedent.
- Center for Open Science Registered Reports material.  
  Use for: publication of negative results and in-principle acceptance logic.

---

## 8. Final verdict

**Top pick:** `v12-A′` — constrained rate/stationarity-preserving repair of the same five-component LC, with M2V/M3 excluded from primary verdict.

**Confidence:** 72 / 100.

**Top 3 risks to mitigate:**

1. **Post-hoc transform selection.** Mitigation: transform ledger + no return-performance peeking + final-iteration status.
2. **False confidence from insufficient OOS evidence.** Mitigation: no post-2024-only PASS; use locked walk-forward + prospective monitoring.
3. **Multiplicity inflation across v11.x → v12.** Mitigation: alpha-spending ledger + Reality Check/SPA or equivalent correction.

**Preconditions before v12 seal:**

1. Resolve the 120-month PIT z-score warmup contradiction.
2. Define a log-safety transform rule for NetFed.
3. Clarify whether funding-stress spread is stationary-state or flow-family.
4. Freeze v12-A′ component list; no M2V/M3 in primary verdict.
5. Add cross-iteration alpha-spending / data-snooping ledger.
6. Add non-redundant predictive evidence gate.
7. Add v12 failure → retirement rule.
8. Publish or at least draft the v11.x 3-of-3 FAIL meta-DECISIONS before v12 execution.

**Bottom line:** v12 should be pursued **only once** and **only narrowly**. If the owner wants to maximize scientific integrity, the v11.x null finding should be written up now, and v12-A′ should be treated as the final, pre-registered opportunity to show that the LC idea survives the most charitable stationary-transform repair.

---

## 9. Falsification criterion for this entire review

This review is materially miscalibrated if, within the next 6–12 months, one of the following occurs:

1. A pre-v11.4 artifact is found showing v12-A's rate-transform rule was specified before any LC failures were observed.
2. Codex proves that v12-A with unchanged PIT standardization fully resolves evaluability without modifying warmup rules.
3. High-quality empirical literature or sealed project diagnostics show M2V or OECD M3 has robust incremental OOS equity-return predictive power after controlling for M2 growth, nominal GDP growth, and multiple testing.
4. An external reviewer shows that cross-iteration multiplicity is already fully controlled by the existing v11.x decision architecture.
5. v12-A′ passes prospectively in genuinely untouched data with enough effective observations, while satisfying all primary confirmatory criteria.
