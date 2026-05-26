# REVIEW REQUEST — ChatGPT 5.5 Pro (Methodology Reviewer)

> **Target work product**: `STRATEGIST_HANDOFF_v11_4_seal_package.md` (attached)
> **Companion context**: `ROADMAP_v11_2_to_v12_0.md` (attached, for project context)
> **Master spec authority**: the project's master system prompt (separately provided by the owner)
> **Strategist (author of work product)**: Claude AI
> **Reviewer role per §0.5 of master spec**: METHODOLOGY REVIEWER
> **Sister review**: Codex is reviewing the same package in parallel from the IMPLEMENTATION-CORRECTNESS angle. Do NOT duplicate Codex's scope; focus strictly on statistical / methodological / pre-registration-discipline issues.

---

## 1. Your mission, in one sentence

Conduct a rigorous, skeptical, peer-review-grade methodological audit of the v11.4 seal package — sufficient to either greenlight Claude Code's seal commit or surface BLOCKER/MAJOR issues that require the Strategist to re-draft before sealing.

The package is composed of three deliverables; review each:
1. **§1** — a `DECISIONS.md` arbitration entry for the v11.3.0 LC v1.0 merge-to-main decision.
2. **§2** — the DRAFT v2.0 sealed pre-registration (`MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md`). **This is the primary review target — ~80% of your effort should sit here.**
3. **§3** — a `TECH_DEBT.md` guardrail patch (two new guardrails).

---

## 2. Your authority and posture

- **Default posture: skeptical**. Anchor every comment in a reference (paper, master spec section, or empirical observation from project files).
- **You are not a yes-man**. The Strategist has already self-reviewed and surfaced 3 push-backs (reproduced in §9 below). Your job is to surface what the Strategist missed, NOT to ratify the self-review. If your independent review finds the Strategist's self-review insufficient, say so directly.
- **You may push back on the Strategist's pre-empt of your review** (§2 §4.1 anticipated-challenge note proposed in push-back 3 below) — if the pre-empt is itself unconvincing, flag it.
- **No PASS-by-default**. The handoff is currently in DRAFT status. The default outcome should be "at least MINOR fixes before seal" unless every checklist item in §6 below comes back clean.

---

## 3. Severity convention (per master spec §0.5.3) — STRICTLY enforced

Use **exactly** these four tags on every comment. No other severities.

| Tag | Meaning | Required action |
|---|---|---|
| `BLOCKER` | Must fix before seal. Methodology is wrong, would invalidate the verdict, or violates pre-registration discipline. | Strategist re-drafts. New ChatGPT review pass. |
| `MAJOR` | Should fix before seal. Significant methodology weakness, defensible alternative exists, current draft is sub-optimal. | Strategist evaluates; either fixes or documents rebuttal in `DECISIONS.md`. |
| `MINOR` | Nice-to-fix. Wording, structure, completeness improvements. | Claude Code incorporates during seal. |
| `NIT` | Cosmetic. Typos, formatting. | Claude Code incorporates during seal. |

**Calibration anchor**: a `BLOCKER` on a sealed pre-reg should be a rare event. If you find > 3 BLOCKERs, ask yourself whether some are MAJORs. Conversely, do NOT downgrade BLOCKERs to MAJORs to be polite — a genuine BLOCKER must be tagged as such.

---

## 4. MANDATORY output format per comment

Every comment must contain the following 7 fields. Comments not in this format will be returned for re-drafting.

```
### Comment #<N> — <SEVERITY> — <one-line title>

**Section reference**: §<X.Y> of handoff (and master spec §<A.B> if relevant)

**Issue**: <2–4 sentence description of the problem; cite specific lines or claims from the draft>

**Evidence / reference**:
  - Paper or master spec section: <author year, page; or master spec §X.Y>
  - Empirical anchor (if any): <observation from project files, e.g., realized n_obs from v11.3.0 verdict.json>

**Proposed solution**: <2–6 sentence concrete fix. NO "consider revising" hand-waving. Either give the exact replacement text, or specify the algorithm in pseudocode.>

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---|---|---|---|
| Proposed solution is the right fix (no better alternative exists at this severity) | XX% | [LL%, UU%] | XX% | X/5 |
| Proposed solution causes downstream issue not yet identified | XX% | [LL%, UU%] | XX% | X/5 |
| Original draft was actually correct and this comment is wrong | XX% | [LL%, UU%] | XX% | X/5 |
| Alternative solution Y (specify): would be preferable | XX% | [LL%, UU%] | XX% | X/5 |

**Falsification criterion for this comment**: <what observation would convince you the comment is wrong?>
```

**Definitions to use for the triple** (per master spec §6 + standing user preference):
- **% Probability**: your point estimate of the probability the outcome holds, calibrated to a Brier-score interpretation (i.e., if you said 70% across 100 such claims, ~70 should be true).
- **95% CI on the probability**: your uncertainty about your own point estimate. Wider CI = lower confidence.
- **% Confidence**: a single derived number, default `100% − (CI_width / 2)`, modulated downward by sample size and distributional fit quality if relevant.
- **Conviction (1–5)**: a composite holistic judgment combining z-score-magnitude analog (|claim strength|), cross-reference agreement (does literature support?), and historical hit rate of similar past claims you've made. Default formula in master spec §6.3.

**Do not skip the table.** A comment without the calibrated assessment table is incomplete and will be returned.

---

## 5. The owner's specific questions (from §4 Step 2 of handoff)

Address each of these in your review, even if no specific finding surfaces. Tag each with severity (use NIT if the draft is clean on that item).

**(a)** Are the 4 amendments correctly translated from the `_amendments.md` reference (referenced in §2 preamble but not transcribed) into:
- §3.4 (insufficient-sample gate) — amendment 4
- §3.7 (skewed-t conditional forecast distribution) — amendment 3
- §4.1 (0.5/0.5 sign priors) — amendment 1
- §5 Criterion 4 (sign-agnostic |t| > 1.65 wording) — amendment 2

**(b)** Are the 4 STRATEGIST_VERIFICATION items listed in §9 of the v2.0 pre-reg the right items to flag, or are there others the Strategist missed? In particular, evaluate whether item #5 (n_obs_oos boundary check per push-back 2) should be added.

**(c)** Is the falsification window design in §6 sound for a pre-registration that does NOT reserve a held-out window? Specifically:
- Is the annual re-test cadence (§6.2) a legitimate substitute for a reserved OOS window?
- Is the §6.3 definitive-falsification criterion (3-bullet list) complete?
- Should the Brier score comparison in §6.3 bullet 3 specify a confidence interval around the Gaussian-vs-skewed-t difference, not just "is worse"?

**(d)** Is the 0.5/0.5 prior in §4.1 defensible, or should asymmetric priors based on a-priori literature be used?
- If asymmetric: which components and by how much? Cite specific literature (Schularick-Taylor 2012 weighting? Adrian-Boyarchenko 2012?).
- If symmetric is correct: is the Strategist's argument (post-hoc adjustment avoidance) the strongest one, or is there a stronger justification (e.g., Bayesian model averaging across both literature streams)?

---

## 6. Exhaustive review checklist — work through every item

### 6.1 §1 DECISIONS entry (merge-to-main arbitration)

- [ ] Is the 5-year horizon for option (b) the right horizon? Should it be 10 years (matching the longest forward-return horizon in the system)?
- [ ] Is the 25–40% probability of feature-flag drift under option (a) calibrated? Does it match published evidence on feature-flag lifecycle (e.g., Optimizely or LaunchDarkly studies on flag staleness)?
- [ ] Is option (b′) [(b) + `RESEARCH_RECORD.md`] from Strategist push-back 1 a strict improvement, a strict harm, or context-dependent?
- [ ] Is the falsification criterion ("revisit if a closely related composite passes" + "if a second researcher requests" + "if LFS storage becomes a billing concern") complete? Is there a "if a third sprint also FAILs" criterion that should be added? (Note: P(v2.0 FAIL) = 65% per handoff §4 outcome table.)
- [ ] Does the pharma Phase-II analogy (§1 rationale point 5) hold? Pharma trials publish FAIL data to public registries (ClinicalTrials.gov), which argues for option (c) discoverability. Address.

### 6.2 §2 v2.0 §0–§2 (preamble, metadata, decision rule)

- [ ] §0 metadata "HARD GATE invariant": is "ancestor of writing commit's HEAD" the right invariant? What if implementation uses worktrees or detached HEAD? Is `git merge-base --is-ancestor` the right check?
- [ ] §2 decision rule `n_pass ≥ 4 of 7`: what is the Type I error rate under the null hypothesis (LC has no predictive content)? Compute or estimate.
- [ ] §2 "not_evaluable counts as FAIL": is this consistent with the standard convention in pre-reg literature? Cite (e.g., Munafò et al. 2017 "Manifesto for reproducible science").

### 6.3 §2 v2.0 §3 (methodology)

- [ ] §3.3 OOS evaluation: does "expanding-window refit at each test date" implicitly use look-ahead via expanding-window choice (the Strategist *chose* expanding over rolling AFTER observing v1.0)? Or is this inherited unchanged from v1.0 (which would make it pre-registration-clean)?
- [ ] §3.4 sample gate `5 × HAC_lag`: is `5×` the right multiplier? Literature anchors (Andrews 1991, Newey-West 1987, Stock-Watson 2007) suggest the standard floor is `T^(1/3)` for the lag itself, not a sample-size requirement for the inference. Is `5×` over-conservative? Is `3×` defensible? Compute the gate's by-construction-FAIL rate for criteria 1–3 given LC's data availability (~1986–2026).
- [ ] §3.4 `HAC_lag = floor(1.5 × h)` for h in months: is this consistent with v1.0? Master spec §3.5 lists `lag = h·12 − 1` (daily) and `lag = h − 1` (monthly) as standard. Address.
- [ ] §3.5 Newey-West vs Hansen-Hodrick: which does v1.0 use? The handoff says "Newey-West with lag = floor(1.5 × h)" but for overlapping returns Hansen-Hodrick is often preferred. Is the choice consistent with v1.0?
- [ ] §3.6 Stambaugh AR(1) threshold 0.85: is 0.85 the right cutoff? Stambaugh (1999) does not specify a threshold (the bias correction is continuous in ρ). Why 0.85 and not, e.g., apply correction unconditionally?
- [ ] §3.6 Campbell-Yogo (2006) confidence intervals for "all coefficients regardless": is this correct? CY intervals are specifically for near-unit-root regressors; applying to all coefficients regardless of persistence may be inefficient (wider CI than necessary). Address.
- [ ] §3.7 skewed-t (Hansen 1994) parameterization: 4 parameters μ, σ, η, ν is standard. Is ML fit on residuals guaranteed to converge? Are bounds enforced (η ∈ [−1, 1], ν > 2)? Is there a fallback if fit fails (refit Gaussian)?
- [ ] §3.7 conditional forecast = `regression_mean(t) + skewed_t(η_t, ν_t) · σ_t`: is the addition of skewness in the SHOCK consistent with the mean specification? Or should the conditional mean itself shift?
- [ ] §3.8 bootstrap `n_bootstrap = 50,000`: justified per master spec §3.6 ("50K for tail probabilities"). Is 50K enough for the Brier score difference in §6.3 bullet 3?

### 6.4 §2 v2.0 §4 (priors)

- [ ] §4.1 Strategist note on 0.5/0.5: is the post-hoc-adjustment-avoidance argument valid? Counter-argument: a-priori literature priors set NOW (without re-reading v1.0) is the correct disciplined choice; the impossibility argument is rhetorical, not formal. Address.
- [ ] §4.2 composite-level prior from component-level: "5 independent symmetric priors → composite prior also 0.5" — is the independence assumption valid? Components 1 (NetFed) and 2 (M2) are correlated by construction. Address.
- [ ] Is there a missing §4.3 on the **interaction between priors and the decision rule**? If priors are 0.5/0.5 and the decision rule is a deterministic n_pass ≥ 4, do the priors actually do any work?

### 6.5 §2 v2.0 §5 (seven testable criteria)

- [ ] Criterion 1 OOS R² > 0.005 @ 1Y: is this threshold calibrated to the noise floor at 1Y? Goyal-Welch (2008) typical OOS R² for ANY predictor at 1Y is ~0.005, so this threshold is "barely passes the kitchen-sink baseline." Is that the intended bar?
- [ ] Criterion 2 OOS R² > 0.020 @ 3Y: similarly, calibrate to literature.
- [ ] Criterion 3 OOS R² > 0.040 @ 5Y: see push-back 2 — by-construction-rejection risk.
- [ ] Criterion 4 (amended): |t_NW| > 1.65 corresponds to one-sided p = 0.05 OR two-sided p = 0.10. Now that the test is sign-agnostic (two-sided), is 1.65 still the right threshold or should it be 1.96 (two-sided p = 0.05)?
- [ ] Criterion 5 ADF for all 5 components: ADF null is unit-root; rejecting at p < 0.05 for ALL 5 is a strong joint test. Is Holm-Šidák correction applied across the 5 tests? If not, should be.
- [ ] Criterion 6 max VIF < 5: standard but tight. Why 5 not 10 (Hair et al. 2010 says VIF > 10 is "significant" multicollinearity)?
- [ ] Criterion 7 Bonferroni at p < 0.0025: 0.0025 = 0.05/20. Where does 20 come from? Document the multiplicity correction logic.
- [ ] **Multiplicity across criteria 1–7**: is the n_pass ≥ 4 rule itself subject to a meta-multiplicity correction? Joint probability under null that ≥ 4 of 7 marginally significant criteria fire?

### 6.6 §2 v2.0 §6 (falsification window)

- [ ] §6.1 "no separate held-out test set is reserved" — is this justifiable? A strict pre-reg purist would say no. The Strategist's defense (annual re-test cadence) is in §6.2; evaluate.
- [ ] §6.2 annual re-test: at 1Y horizon, 1 year of fresh data adds only 12 monthly observations. Is the "downgrade to UNSTABLE on pass/fail reversal" criterion sensitive enough to detect a real reversal, or is it noise-prone?
- [ ] §6.3 bullet 3 Brier score comparison: as flagged in (c), needs a CI / statistical test, not just a level comparison. Specify.

### 6.7 §2 v2.0 §7–§9 (display, invariants, verification items)

- [ ] §7 inherits v1.0 §12.2: is this self-contained? The pre-reg should not depend on another document being in the same repo state.
- [ ] §8 invariants list (items 1–7): is any invariant missing? E.g., the n_bootstrap = 50,000 number — should this be in §8?
- [ ] §9 verification items (1–4): adequate? Strategist push-back 2 proposes adding item #5 (realized n_obs_oos check). Evaluate.

### 6.8 §3 TECH_DEBT guardrails

- [ ] Guardrail 1 reproducible-evidence requirement: is the requirement enforceable in practice? Who checks that P1 entries include evidence?
- [ ] Guardrail 2 misdiagnosis closeout: is "RESOLVED-by-reclassification" the right status, or should there be a separate "MISDIAGNOSIS" status (more visible)?
- [ ] Are there OTHER guardrails the v11.3.0 retrospective suggests (e.g., a mandatory CI-status double-check before declaring failures)?

### 6.9 Strategist push-backs (reproduced in §9 below) — evaluate independently

- [ ] **Push-back 1** (option b′): does it strictly dominate, or does it open new risks (e.g., RESEARCH_RECORD.md becomes a marketing surface)?
- [ ] **Push-back 2** (gate verification): does adding item #5 to §9 cover the risk, or does the gate threshold need to change pre-seal?
- [ ] **Push-back 3** (prior pre-empt note): does the pre-empt note in §4.1 actually help, or does it look defensive and weaken the draft?

---

## 7. Specific anti-rubber-stamp clauses

The Strategist has a known cognitive bias toward self-consistency (anchoring on own prior drafts). Mitigate by:

1. **Compute the gate's by-construction-FAIL rate for criteria 1–3 yourself**. Do not accept the Strategist's "35% probability" estimate uncritically. Use the LC component availability dates (component 5 funding stress starts 1986; component 1 NetFed starts 2003-02 per ROADMAP) and the expanding-window logic in §3.3.
2. **Compute Type I error of n_pass ≥ 4 of 7** yourself under the null that each criterion fires independently at its marginal rate. Even if criteria are not independent, the result is informative.
3. **Search for missing components in the pre-reg**: what would a Munafò-et-al-style pre-reg require that this draft lacks? (Hypothesis statement is in §1 but the *directional* hypothesis is sign-agnostic by design — flag if this weakens pre-reg discipline.)
4. **Ask "what would the third-FAIL outcome look like?"**: per handoff §4 outcome table, P(v2.0 FAIL) = 65%. If FAIL, the meta-finding is "3-of-3 FAIL on this project." Does the v2.0 pre-reg adequately set up the conditions for this meta-finding to be publishable, or does it leave the verdict ambiguous?

---

## 8. Out-of-scope items — DO NOT review these

Codex is handling these in parallel. Do not duplicate:

- Whether the §3.4 gate formula is *implementable* (yes/no, edge cases at the boundary `n_obs_oos = 5 × HAC_lag` exactly).
- Whether skewed-t ML fit converges numerically.
- Whether the HARD GATE git-ancestor check is correctly specifiable.
- Performance budget for 50,000 bootstrap × 4 horizons.
- Whether the spec is implementable in Python without ambiguity at the code level.
- Test scaffold completeness.

If you find an issue that straddles methodology and implementation, flag it under methodology with a note "Codex should also evaluate from implementation angle."

---

## 9. Strategist self-review push-backs (reproduced verbatim)

The Strategist surfaced 3 push-backs in self-review. Evaluate each independently — do NOT default to agreeing.

### Push-back 1 — §1 merge-to-main: option (b′) vs (b)

(b′) = (b) + new `RESEARCH_RECORD.md` at repo root, referenced only from `README_USER.md`'s bottom footer. Calibrated outcome: P(b′ strictly dominates b on 5y horizon) = 60% [42%, 76%], confidence 65%, conviction 3.5/5.

### Push-back 2 — §2 §3.4 sample gate by-construction-rejection risk

Add 5th verification item in §9: Claude Code transcribes realized n_obs_oos from v1.0's verdict.json. If gate would have rejected criteria 1–3 in v1.0, gate threshold must be relaxed pre-seal. Calibrated outcome: P(gate auto-rejects C3 by construction) = 35% [18%, 55%], confidence 60%, conviction 3/5.

### Push-back 3 — §2 §4.1 0.5/0.5 prior pre-empt

Add sentence at end of Strategist note explicitly addressing review-item (d). Calibrated outcome: P(ChatGPT 5.5 accepts 0.5/0.5 with pre-empt) = 70% [52%, 84%] vs 60% [43%, 76%] without. Confidence 70% / 65%. Conviction 4/5 / 3.5/5.

**Your job**: independently assess whether each push-back is correct, partial, or wrong. Tag your assessment with severity.

---

## 10. Expected output structure (template you will fill)

Produce a single markdown document titled `REVIEW_v11_4_ChatGPT55Pro_methodology.md` with this structure:

```markdown
# REVIEW v11.4 — ChatGPT 5.5 Pro — Methodology

## Headline summary
- BLOCKERs: <count> (list comment numbers)
- MAJORs: <count>
- MINORs: <count>
- NITs: <count>
- Recommendation: <SEAL_AS_DRAFTED | SEAL_WITH_MINOR_EDITS | RE-DRAFT_REQUIRED>

## Calibrated meta-assessment
| Outcome | P | 95% CI | Confidence | Conviction |
|---|---|---|---|---|
| My review will hold up under Strategist arbitration (no BLOCKERs overturned) | XX% | [LL%, UU%] | XX% | X/5 |
| v2.0 sprint will close FAIL despite my recommended fixes | XX% | [LL%, UU%] | XX% | X/5 |
| Sealing with my MINOR/NIT-only edits incurs zero re-seal risk over 12 months | XX% | [LL%, UU%] | XX% | X/5 |

## Comment-by-comment review

### Comment #1 — <SEVERITY> — <title>
[per format in §4 above]

### Comment #2 — ...
...

## Specific responses to owner's questions (a)–(d)
[concise paragraph per question, each with probability/confidence/conviction triple]

## Specific assessment of Strategist push-backs 1–3
[concise paragraph per push-back, each with probability/confidence/conviction triple]

## Items I flagged that the Strategist's self-review missed
[bullet list with severity tags]

## Falsification criterion for this entire review
What evidence in the next 6 months would convince me this review was mis-calibrated?
```

---

## 11. Pacing / time budget

- Allocate ~3–5 hours of careful review.
- Do NOT speed-read; the Strategist's draft is dense and assumes context.
- If you are unsure about a specific item, mark it as "NEEDS_STRATEGIST_CLARIFICATION" with the specific question rather than guessing.

---

## 12. Final reminder

Per the master spec §0.5.4: **the Strategist (Claude AI) owns the final merge decision**. Your review is consultative. The Strategist will arbitrate any reviewer-reviewer disagreement (between you and Codex) by referring back to the spec and methodology references. Document your reasoning thoroughly enough that the Strategist can use it.

Your review will be archived as `reviews/REVIEW_v11_4_ChatGPT55Pro_methodology.md` and committed to git per master spec §1.6.12.

Go.
