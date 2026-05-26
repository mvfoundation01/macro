# REVIEW v11.4 — ChatGPT 5.5 Pro — Methodology — Round 2

## Headline summary
- VERIFY-PASS: 8 (#3, #4, #5, #7, #8, #10, #11, #12)
- VERIFY-MODIFIED-OK: 3 (#1, #2, #9)
- VERIFY-FAIL: 1 (#6)
- NEW BLOCKERs: 0
- NEW MAJORs: 1 (New-1)
- NEW MINORs: 3 (New-2, New-3, New-4)
- Recommendation: SEAL_WITH_MINOR_EDITS

DRAFT_v2 is much improved relative to DRAFT v1. The two Round-1 BLOCKERs are addressed well enough for seal after bounded edits. I do **not** recommend Round 3. The remaining issues are surgical: one decision-rule/null-calibration correction, one bootstrap-invariant consistency fix, and three small provenance/boundary wording fixes.

The only VERIFY-FAIL is Round-1 #6. The redraft implements the exact two-tier rule I proposed, but reviewing the algebra exposed that the proposed `n_pass_predictive ≥ 2` gate is redundant when only C5–C6 are non-predictive. Because a total count of four among seven criteria already implies at least two predictive criteria, DRAFT_v2's claim that the rule is stricter than plain `n_pass ≥ 4` is false. This should be corrected pre-seal, but it does not require a wholesale re-draft.

## Calibrated meta-assessment

| Outcome | P | 95% CI | Confidence | Conviction |
|---|---:|---:|---:|---:|
| DRAFT_v2 is sealable as-drafted (no further changes needed) | 42% | [25%, 61%] | 72% | 3/5 |
| Round-3 will be needed | 12% | [4%, 27%] | 82% | 4/5 |
| At sprint close, v2.0 verdict is PASS | 27% | [13%, 45%] | 72% | 3/5 |
| At sprint close, v2.0 verdict is FAIL → 3-of-3 meta-finding triggers | 68% | [50%, 82%] | 75% | 3.5/5 |

## Verification of round-1 findings

### Verify Round-1 #1 — VERIFY-MODIFIED-OK — Chronology and provenance

**Round-1 reference**: Comment #1 (BLOCKER) — "Chronology and provenance are impossible as written"

**DRAFT_v2 location**: §0.1 "Identifiers"; §0.2 "Chronology invariants"

**Round-1 proposed fix**: Verify actual v1.0 verdict/seal timestamps, replace impossible dates, add invariants tying `d56174c`, the amendments file, and the v2.0 seal commit into a chronological/provenance chain.

**DRAFT_v2 actual fix**: DRAFT_v2 replaces the hard-coded impossible dates with `<VERIFIED_BY_CLAUDE_CODE>` placeholders, requires `git log --format=%cI` extraction for `a8635ef` and `d56174c`, records the amendments-file SHA-256, and adds four chronology/ancestor invariants.

**Verdict**: VERIFY-MODIFIED-OK. The fix resolves the Round-1 BLOCKER. I would add one more invariant as a MINOR (New-2): `git merge-base --is-ancestor a8635ef d56174c` must hold, so the v1.0 verdict is proven to descend from the v1.0 sealed pre-reg. That is not a blocker because §0.1 already pins both commits and §0.2 blocks future-dated or out-of-order sealing.

### Verify Round-1 #2 — VERIFY-MODIFIED-OK — Sample gate no longer creates broad by-construction FAILs

**Round-1 reference**: Comment #2 (BLOCKER) — "The `5 × HAC_lag` gate creates by-construction FAILs"

**DRAFT_v2 location**: §3.4 "Insufficient-sample gate"; §3.5 "HAC standard errors"; §10.3 "Realized v1.0 sample-count audit"

**Round-1 proposed fix**: Replace `5 × HAC_lag` and `floor(1.5h)` with monthly `HAC_lag = h − 1`, gate on `n_obs_oos < max(60, 3 × HAC_lag)` or `n_eff < 30`, and report raw sample counts, HAC lag, gate threshold, and effective sample size.

**DRAFT_v2 actual fix**: DRAFT_v2 uses `HAC_lag = horizon_months − 1`, the revised `max(60, 3 × HAC_lag) OR n_eff < 30` gate, a cell-level `NOT_EVALUABLE_COUNTED_FAIL` status, explicit LC_FULL 10Y non-evaluability disclosure, and a v1.0 sample-count audit table.

**Verdict**: VERIFY-MODIFIED-OK. The modification is acceptable. I accept the explicit disclosure that LC_FULL 10Y is expected to be non-evaluable rather than excluding 10Y entirely from Criterion 4. Keeping 10Y in the table with a not-evaluable status is cleaner than silently dropping the horizon, provided §10.3 is filled before seal and the verdict JSON preserves the distinction between `FAIL_STATISTICAL` and `NOT_EVALUABLE_COUNTED_FAIL`.

### Verify Round-1 #3 — VERIFY-PASS — OOS training-set timing

**Round-1 reference**: Comment #3 (MAJOR) — "OOS refit timing must specify `s + h ≤ t`"

**DRAFT_v2 location**: §3.3 "OOS evaluation"; §12 "Verdict JSON schema"

**Round-1 proposed fix**: Define the training set at forecast origin `t` as `{(x_s, r_{s,s+h}) : s + h ≤ t}` and add `train_cutoff`, `score_date`, and `feature_origin` to the verdict output.

**DRAFT_v2 actual fix**: DRAFT_v2 states the exact `s + h ≤ t` rule, prohibits using `x_t` as a training observation until `r_{t,t+h}` is realized, and adds the requested fields.

**Verdict**: VERIFY-PASS. The methodological look-ahead issue is fixed. One phrasing edit remains: §3.3 says `train_cutoff = t − h` is "exclusive — last allowed `s`," but if `s + h ≤ t`, then `s = t − h` is allowed. New-4 gives the exact wording fix.

### Verify Round-1 #4 — VERIFY-PASS — Skewed-t mean/standardization ambiguity

**Round-1 reference**: Comment #4 (MAJOR) — "Skewed-t forecast distribution has a mean/standardization ambiguity"

**DRAFT_v2 location**: §3.7 "Conditional forecast distribution"

**Round-1 proposed fix**: Use a standardized Hansen skewed-t innovation with `E[z]=0` and `Var[z]=1`, estimate only skewness and tail parameters on standardized residuals, and define the forecast as `regression_mean(t) + σ_t z` with no separate residual-location parameter.

**DRAFT_v2 actual fix**: DRAFT_v2 adopts `arch.univariate.SkewStudent`, states zero-mean/unit-variance standardization, estimates only `η` and `ν`, specifies bounds and fallback, and states explicitly that no location parameter `μ` is estimated separately.

**Verdict**: VERIFY-PASS. The methodology ambiguity is resolved. Any remaining concern about the exact `arch` parameter order is implementation-level and should be handled by Codex/acceptance tests rather than by methodology review.

### Verify Round-1 #5 — VERIFY-PASS — Criterion 4 alpha disclosure

**Round-1 reference**: Comment #5 (MAJOR) — "Criterion 4 uses a one-sided threshold after becoming two-sided"

**DRAFT_v2 location**: §5.1 "Criterion 4 explicit semantics"

**Round-1 proposed fix**: Either raise the threshold to `|t| > 1.96` for a two-sided 5% criterion, or keep `1.65` but explicitly label it as a two-sided 10% weak-evidence screen balanced by other criteria.

**DRAFT_v2 actual fix**: DRAFT_v2 keeps `|t_NW| > 1.65`, labels it a "two-sided 10% screen," states `P(|Z| > 1.65) ≈ 0.099`, and calls it a weak-evidence criterion.

**Verdict**: VERIFY-PASS. The alpha shift is now disclosed. I do not require changing the threshold to `1.96`. I would, however, avoid relying on the current "two-tier rule" as a balancing argument until Round-1 #6 is corrected, because the two-tier gate is algebraically redundant as drafted.

### Verify Round-1 #6 — VERIFY-FAIL — Decision-rule calibration and predictive-evidence gate

**Round-1 reference**: Comment #6 (MAJOR) — "The 4-of-7 decision rule lacks null calibration and mixes predictive with validity criteria"

**DRAFT_v2 location**: §2.1 "Binary verdict"; §2.2 "Null calibration of the two-tier rule"

**Round-1 proposed fix**: Add a null-calibration table, classify C5–C6 as admissibility checks rather than predictive evidence, and require at least two predictive criteria from `{C1, C2, C3, C4, C7}` in addition to `n_pass ≥ 4`.

**DRAFT_v2 actual fix**: DRAFT_v2 implements `PASS ⇔ n_pass ≥ 4 AND n_pass_predictive ≥ 2`, provides stated marginal null pass probabilities, reports an approximate `P(PASS|null) ≈ 2.7%`, and claims the two-tier rule is stricter than plain `n_pass ≥ 4`.

**Verdict**: VERIFY-FAIL. The redraft matches my proposed structure, but the structure is algebraically redundant. Since only C5 and C6 are non-predictive, any verdict with `n_pass ≥ 4` already has `n_pass_predictive ≥ 2`:

```
n_pass_predictive = n_pass_total − n_pass_nonpredictive
n_pass_nonpredictive ≤ 2
therefore if n_pass_total ≥ 4, n_pass_predictive ≥ 2
```

So the redraft's statement that the rule is "stricter" is false, and the statement that the DRAFT v1 rule could pass with "zero predictive criteria" is also false. A zero-predictive result could pass at most C5 and C6, yielding `n_pass = 2`, not `4`. The 2.7% null probability may be a valid calculation under the stated marginals, but it is the probability of plain `n_pass ≥ 4` under those marginals, not a reduction caused by the two-tier gate. Likewise, the comparison to an 11.2% DRAFT v1 false-PASS probability is not attributable to the two-tier rule as drafted; it appears to arise from different marginal pass-probability assumptions.

**New severity tag**: MAJOR.

**New proposed fix**: Choose one of two explicit fixes before seal.

Preferred if the Strategist wants to preserve v1.0 target comparability: keep the binary rule effectively as `n_pass ≥ 4`, but remove all claims that the two-tier rule is stricter. Replace §2.1–§2.2 language with: `Because only C5–C6 are admissibility checks, n_pass ≥ 4 mechanically implies at least two predictive criteria. Therefore the predictive subset is reported for transparency but does not add an independent gate unless raised to ≥3.` Recompute/null-calibrate plain `n_pass ≥ 4` under one stated vector of marginal pass probabilities and delete the 11.2% comparison unless the exact assumptions producing 11.2% are shown.

Preferred if the Strategist wants a genuinely stricter predictive-evidence gate: change the rule to `n_pass ≥ 4 AND n_pass_predictive ≥ 3 of {C1,C2,C3,C4,C7}`. Under the DRAFT_v2 marginal probabilities, the independent-null false-PASS probability falls to approximately 0.39%. This is a meaningful target change, so the preamble and §10 delta table must explicitly disclose it and the Strategist should accept the Type II/power cost.

**Calibrated assessment**:

| Outcome | P | 95% CI | Confidence | Conviction |
|---|---:|---:|---:|---:|
| The redraft fix is incomplete (round-1 finding persists) | 76% | [58%, 89%] | 75% | 4/5 |
| The redraft fix introduces a new failure mode | 68% | [49%, 83%] | 73% | 4/5 |

### Verify Round-1 #7 — VERIFY-PASS — Priors and BMA rationale

**Round-1 reference**: Comment #7 (MAJOR) — "The priors section is rhetorically defensive and operationally inert"

**DRAFT_v2 location**: §4 "Priors"

**Round-1 proposed fix**: Replace the defensive out-of-band note with sealed BMA/equipoise rationale, clarify priors are interpretive only, fix the unnecessary independence claim, and add optional literature-tilt sensitivity outside the verdict.

**DRAFT_v2 actual fix**: DRAFT_v2 adopts a BMA equipoise rationale, states the priors do not alter Criteria 1–7 or the PASS/FAIL threshold, explains their anti-cherry-picking role, removes the independence assumption, and adds literature-tilt sensitivity.

**Verdict**: VERIFY-PASS. This is a strong fix. I would only rename "descriptive, not pre-registered" to "descriptive, not verdict-affecting" in §4.3/§15, because the sensitivity is in fact being pre-specified by the pre-reg document.

### Verify Round-1 #8 — VERIFY-PASS — Falsification window and Brier comparison

**Round-1 reference**: Comment #8 (MAJOR) — "Annual re-test is stability monitoring, not a held-out OOS substitute"

**DRAFT_v2 location**: §6.1 "Sealing-to-verdict design"; §6.3 "Definitive falsification criterion"; §6.4 "Meta-finding on 3-of-3 pre-reg FAIL"

**Round-1 proposed fix**: Reframe annual re-test as prospective stability monitoring rather than fresh-OOS confirmation, define the Brier event and paired block-bootstrap CI, require an effective-sample threshold, and add a 3-of-3 FAIL meta-finding.

**DRAFT_v2 actual fix**: DRAFT_v2 says the verdict is a sealed re-analysis plus prospective stability monitoring, defines `event_1Y`, specifies paired stationary block-bootstrap CI with `LB(95% CI ΔBrier) > 0`, requires `n_eff ≥ 10`, and adds §6.4 for 3-of-3 FAIL.

**Verdict**: VERIFY-PASS. The falsification design is now methodologically honest. It remains weaker than a reserved holdout, but it no longer pretends otherwise.

### Verify Round-1 #9 — VERIFY-MODIFIED-OK — Stambaugh/Campbell-Yogo inference inheritance

**Round-1 reference**: Comment #9 (MAJOR) — "Predictive-regression inference corrections are over-broad or under-justified"

**DRAFT_v2 location**: §3.5 "HAC standard errors"; §3.6 "Stambaugh bias and Campbell-Yogo intervals"; §10.2 "Explicit deltas"

**Round-1 proposed fix**: Either transcribe v1.0's exact inference conventions verbatim and document them as inheritance, or change the rules with an explicit v2.0 methodological rationale.

**DRAFT_v2 actual fix**: DRAFT_v2 chooses inheritance: it restores monthly `horizon_months − 1` HAC lags, states Stambaugh/CY rules are inherited verbatim, restricts CY to the v1.0 grid when `ρ̂_X > 0.95`, and defers inference-rule changes to v2.1.

**Verdict**: VERIFY-MODIFIED-OK. This is acceptable because v2.0's purpose is to test the four amendments, not overhaul inference. The HAC formula change from DRAFT v1's `floor(1.5h)` to `h−1` does not create a new methodology-drift concern if Claude Code verifies that `h−1` is v1.0's sealed convention. New-3 flags one small boundary-table contradiction.

### Verify Round-1 #10 — VERIFY-PASS — Verification items expanded

**Round-1 reference**: Comment #10 (MAJOR) — "Verification items miss source-amendment and realized-boundary checks"

**DRAFT_v2 location**: §9 "Open Strategist verification items"; §10 "v2.0 deltas from v1.0"

**Round-1 proposed fix**: Add realized `n_obs_oos` audit, source-amendment hash/mapping, OOS training-set timing, `n_bootstrap` invariant, Criterion 7 multiplicity mapping, and ADF multiplicity rule.

**DRAFT_v2 actual fix**: DRAFT_v2 expands §9 to 10 items, adds §10.2 explicit deltas, and includes §10.3 sample-count audit.

**Verdict**: VERIFY-PASS. The list is sufficiently complete for seal-time resolution. The remaining caveat is that §10.1 and §10.3 still contain placeholders; sealing must abort if any `<TRANSCRIBE>` or `<VERIFIED_BY_CLAUDE_CODE>` placeholder remains in the sealed pre-reg.

### Verify Round-1 #11 — VERIFY-PASS — Research-record discoverability

**Round-1 reference**: Comment #11 (MINOR) — "Merge-to-main decision should improve discoverability without marketing failed models"

**DRAFT_v2 location**: DECISIONS §3.1 "RESEARCH_RECORD.md"; DRAFT_v2 §7 "Display framing rules"

**Round-1 proposed fix**: Adopt option (b′): keep rejected research off production code paths while adding a constrained archival research index with sprint/status/branch/tag/verdict metadata and low-prominence README footer link.

**DRAFT_v2 actual fix**: DECISIONS §3.1 adopts `buffet_indicator/docs/RESEARCH_RECORD.md`, structured YAML blocks, a low-prominence footer discovery hook, and explicit non-dashboard/non-production surfacing.

**Verdict**: VERIFY-PASS. This balances archival discoverability with production-signal hygiene.

### Verify Round-1 #12 — VERIFY-PASS — TECH_DEBT guardrails

**Round-1 reference**: Comment #12 (MINOR) — "TECH_DEBT guardrails need an enforcement owner and more visible misdiagnosis status"

**DRAFT_v2 location**: DECISIONS §3.2 "TECH_DEBT.md guardrail patch"

**Round-1 proposed fix**: Require structured P0/P1 evidence fields, use `RESOLVED-MISDIAGNOSIS`, and add a source-of-truth check before declaring CI/performance/bundle-size failures.

**DRAFT_v2 actual fix**: DECISIONS §3.2 adds YAML front matter, a future lint script / manual checker, renames status to `RESOLVED-MISDIAGNOSIS`, and adds Guardrail 3.

**Verdict**: VERIFY-PASS. The fix is adequate for a v11.4 seal. Automated lint can remain v11.5+ as long as the schema is written now.

## NEW findings introduced by the redraft

### Comment New-1 — MAJOR — `n_bootstrap = 50,000` invariant conflicts with the 10,000-rep performance fallback

**Section reference**: DRAFT_v2 §3.8; §8.1 item 10; §10.2; §11.3

**Issue**: DRAFT_v2 repeatedly seals `n_bootstrap = 50,000`: §3.8 specifies 50,000, §8.1 makes it immutable post-seal, and §10.2 lists 50,000 as the v2.0 value. But §11.3 allows Claude Code to downsample bootstrap to `n_bootstrap = 10,000` for non-tail-probability quantities if the canonical run exceeds the wall-clock ceiling. That creates an internal contradiction: either 50,000 is immutable, or there is a pre-specified conditional exception.

**Evidence / reference**:
  - Paper or master spec section: Master spec bootstrap convention as represented in DRAFT_v2 §3.8: 10K minimum, 50K for tail probabilities. Pre-registration discipline requires numerical analysis parameters and exceptions to be sealed before execution.
  - Empirical anchor: DRAFT_v2 §3.8 says `n_bootstrap = 50,000`; §8.1 item 10 lists `n_bootstrap = 50,000` as immutable; §10.2 says v2.0 value is 50,000 fixed; §11.3 permits 10,000 under a performance contingency.

**Proposed solution**: Replace the last paragraph of §11.3 with one of the following.

Preferred: `If the canonical run exceeds the wall-clock ceiling, Claude Code must cache, parallelize, or mark the run BLOCKED_PERFORMANCE_BUDGET. It must not reduce n_bootstrap below 50,000 for any verdict-bearing or CI-bearing quantity.`

Acceptable alternative: `For diagnostic-only, non-verdict, non-CI display quantities, a 10,000-rep bootstrap may be used if and only if the output path is under outputs/diagnostics/ and the verdict JSON records n_bootstrap_used=10000 and purpose=descriptive_only. All criterion-level CIs, Brier-CI comparisons, and any artifact used in PASS/FAIL remain fixed at 50,000.` If this alternative is used, §8.1 item 10 must state the exception explicitly.

**Calibrated assessment of the proposed solution**:

| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 78% | [60%, 90%] | 75% | 4/5 |
| Proposed solution causes downstream issue not yet identified | 16% | [6%, 32%] | 80% | 2.5/5 |
| Original draft was actually correct and this comment is wrong | 14% | [5%, 30%] | 81% | 3/5 |
| Alternative solution Y (specify): make 10,000 the universal non-tail default | 24% | [10%, 43%] | 75% | 2.5/5 |

**Falsification criterion for this comment**: Show that no criterion-level, CI-bearing, or verdict-bearing artifact uses the §11.3 fallback, and that §11.3 applies only to separately labeled diagnostic artifacts already outside the sealed analysis path.

### Comment New-2 — MINOR — Add a v1.0 verdict-descends-from-seal provenance invariant

**Section reference**: DRAFT_v2 §0.2; REVIEW_REQUEST Round 2 §5.5

**Issue**: The four chronology invariants are good, but they do not prove that the v1.0 verdict commit `d56174c` descends from the v1.0 sealed pre-reg commit `a8635ef`. The current invariants prove date order and amendments-file ancestry into v2.0, but a history rewrite or wrong branch could in principle produce a verdict commit that is chronologically later without actually being downstream of the v1.0 sealed pre-reg.

**Evidence / reference**:
  - Paper or master spec section: Pre-registration provenance should prove the analysis artifact was created after and under the sealed spec; `git merge-base --is-ancestor` is already the chosen HARD GATE pattern in §8.
  - Empirical anchor: Round-2 request §5.5 specifically asks whether a fifth invariant should be added: "v1.0 verdict commit `d56174c` must be a descendant of v1.0 seal commit `a8635ef`."

**Proposed solution**: Add §0.2 invariant B-1.5: `git merge-base --is-ancestor a8635ef d56174c` must return exit code 0. Seal fails if not. Also log `v1_verdict_descends_from_v1_seal = true` in the seal-time provenance block.

**Calibrated assessment of the proposed solution**:

| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 86% | [71%, 95%] | 82% | 4/5 |
| Proposed solution causes downstream issue not yet identified | 5% | [1%, 15%] | 87% | 1.5/5 |
| Original draft was actually correct and this comment is wrong | 12% | [4%, 27%] | 83% | 2.5/5 |
| Alternative solution Y (specify): rely on timestamp-only chronology | 18% | [7%, 35%] | 80% | 2/5 |

**Falsification criterion for this comment**: Show that the seal-time script already verifies `a8635ef` is an ancestor of `d56174c` outside the pre-reg text and logs the result in an auditable artifact.

### Comment New-3 — MINOR — Comparator table contradicts the Stambaugh `ρ̂ > 0.85` rule at the boundary

**Section reference**: DRAFT_v2 §3.6; §3.9 comparator semantics

**Issue**: §3.6 says Stambaugh correction is applied when AR(1) `ρ̂ > 0.85`. §3.9's comparator table repeats operator `>` but says the boundary case "exact" is "Stambaugh applied." That is inconsistent: under a strict `>` comparator, `ρ̂ = 0.85` should not apply.

**Evidence / reference**:
  - Paper or master spec section: This is a threshold-semantics issue rather than a paper issue. The pre-reg's own §3.9 exists to eliminate boundary ambiguity.
  - Empirical anchor: DRAFT_v2 §3.6 uses `ρ̂ > 0.85`; DRAFT_v2 §3.9 maps exact boundary to "Stambaugh applied."

**Proposed solution**: Change the §3.9 row to either: `§3.6 Stambaugh ρ̂ > 0.85 | > | ρ̂ = 0.85 exactly | Stambaugh not applied`, or, if the Strategist intends inclusion at the boundary, change §3.6 and §3.9 to `ρ̂ ≥ 0.85` everywhere. I prefer the first because it preserves the written strict comparator.

**Calibrated assessment of the proposed solution**:

| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 91% | [79%, 97%] | 85% | 4.5/5 |
| Proposed solution causes downstream issue not yet identified | 3% | [0%, 11%] | 89% | 1/5 |
| Original draft was actually correct and this comment is wrong | 6% | [1%, 17%] | 87% | 2/5 |
| Alternative solution Y (specify): make the rule inclusive at `ρ̂ ≥ 0.85` | 22% | [9%, 40%] | 77% | 2.5/5 |

**Falsification criterion for this comment**: Produce v1.0 sealed text showing the Stambaugh rule was explicitly inclusive at `ρ̂ = 0.85` and that DRAFT_v2's `>` sign is the typo rather than the comparator-table boundary interpretation.

### Comment New-4 — MINOR — `train_cutoff = t − h` wording should be inclusive, not exclusive

**Section reference**: DRAFT_v2 §3.3; §12 verdict JSON schema

**Issue**: The `s + h ≤ t` rule means the last allowed training forecast-origin is `s = t − h` inclusive. DRAFT_v2's field note says `train_cutoff = t − h` with the phrase "exclusive — last allowed `s`," which mixes an exclusive label with an inclusive mathematical boundary. This can cause off-by-one disagreement between specification, implementation, and audit interpretation.

**Evidence / reference**:
  - Paper or master spec section: PIT training-set construction requires that all realized target returns in training be observable at the forecast origin. If `s + h = t`, the return ending at `t` is observable at `t` and is valid under the written rule.
  - Empirical anchor: DRAFT_v2 §3.3 states `training_set(t,h) = {(x_s, r_{s,s+h}) : s+h ≤ t}` and then labels `train_cutoff = t − h` as "exclusive — last allowed s."

**Proposed solution**: Replace the field note with: `train_cutoff = t − h (inclusive — last allowed training forecast-origin s under s+h≤t)`. If implementation prefers an exclusive upper-bound convention for slicing, use a separate field name such as `train_cutoff_exclusive = t − h + one_month` and document the transformation.

**Calibrated assessment of the proposed solution**:

| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 88% | [74%, 96%] | 83% | 4/5 |
| Proposed solution causes downstream issue not yet identified | 4% | [1%, 14%] | 88% | 1.5/5 |
| Original draft was actually correct and this comment is wrong | 10% | [3%, 23%] | 85% | 2.5/5 |
| Alternative solution Y (specify): keep wording but rely on tests | 16% | [6%, 32%] | 80% | 2/5 |

**Falsification criterion for this comment**: Show that the implementation and verdict schema define `train_cutoff` as an exclusive slice endpoint rather than the last allowed training forecast-origin, and that the schema separately reports the inclusive last training `s`.

## Cross-checks responses (per review request §5)

**Cross-check 1 — HAC lag formula choice**: Accepted. If Claude Code verifies v1.0 used `horizon_months − 1`, then DRAFT_v2's move from DRAFT v1's `floor(1.5h)` back to `h−1` is a restoration, not inference drift. P(acceptable as restoration) = 84% [68%, 94%], confidence 77%, conviction 4/5.

**Cross-check 2 — Criterion 4 alpha disclosure**: Accepted with one caveat. The two-sided 10% label and weak-evidence description are sufficient; no need to require `1.96`. The caveat is that §5.1 should not cite the two-tier rule as extra protection until Round-1 #6 is corrected, because the `≥2 predictive` gate is redundant. P(disclosure adequate after #6 wording fix) = 81% [64%, 92%], confidence 76%, conviction 4/5.

**Cross-check 3 — Sample-gate disclosure**: Accepted. Keeping 10Y in the evaluable horizon list and explicitly marking it expected-not-evaluable is better than excluding it, because exclusion would silently change the horizon universe. The verdict JSON's `NOT_EVALUABLE_COUNTED_FAIL` status is essential. P(disclosure adequate) = 78% [60%, 90%], confidence 75%, conviction 4/5.

**Cross-check 4 — Two-tier decision rule's null calibration**: Not accepted as written. The independence calculation is useful, but the two-tier rule is algebraically equivalent to plain `n_pass ≥ 4`; the draft must either disclose equivalence or raise the predictive gate to `≥3`. The claim that positive correlation makes the reported probability an upper bound is also too strong; dependence can raise or lower count-tail probabilities depending on which criteria cluster. P(current calibration language needs pre-seal edit) = 82% [66%, 93%], confidence 78%, conviction 4/5.

**Cross-check 5 — Provenance invariants**: The four invariants are good but should add a fifth: `a8635ef` must be an ancestor of `d56174c`. This is a MINOR provenance hardening, not a blocker. P(fifth invariant worth adding) = 86% [71%, 95%], confidence 82%, conviction 4/5.

## Out-of-scope comments

- I did not re-review the option (b′) merge-to-main decision beyond verifying that Round-1 #11 was implemented in DECISIONS §3.1.
- I did not re-litigate the TECH_DEBT YAML schema beyond verifying Round-1 #12. The proposed lint implementation remains a future-task detail.
- I did not rewrite §11 acceptance tests. The §11.3 bootstrap fallback contradiction is methodology-relevant because it conflicts with sealed numerical invariants, not because of test implementation.
- I did not inspect code-level `arch.univariate.SkewStudent` parameter ordering; Codex/acceptance tests should verify that.

## Falsification criterion for this round-2 review

This round-2 review is mis-calibrated if, within the next 6 months, any of the following occurs:

1. The Strategist proves that `n_pass ≥ 4 AND n_pass_predictive ≥ 2` is not algebraically equivalent to plain `n_pass ≥ 4` under the documented criterion partition `{C1,C2,C3,C4,C7}` predictive and `{C5,C6}` non-predictive.
2. The sealed v2.0 pre-reg resolves all four NEW comments and the Round-1 #6 VERIFY-FAIL exactly as proposed, but a subsequent reviewer still finds a BLOCKER in the same sections.
3. Claude Code demonstrates that the §11.3 10K fallback cannot affect any verdict-bearing, CI-bearing, or displayed research artifact, and that this exclusion was already encoded elsewhere before my review.
4. v2.0 closes PASS solely because my recommended #6 fix is adopted, and a retrospective shows that the fix created an unacknowledged target change rather than a disclosure/calibration correction.

