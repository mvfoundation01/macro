# REVIEW REQUEST — Codex (Implementation-Correctness Reviewer)

> **Target work product**: `STRATEGIST_HANDOFF_v11_4_seal_package.md` (attached)
> **Companion context**: `ROADMAP_v11_2_to_v12_0.md` (attached, for project context)
> **Master spec authority**: the project's master system prompt (separately provided by the owner)
> **Strategist (author of work product)**: Claude AI
> **Reviewer role per §0.5 of master spec**: IMPLEMENTATION-CORRECTNESS + SECURITY REVIEWER
> **Sister review**: ChatGPT 5.5 Pro is reviewing the same package in parallel from the METHODOLOGY angle. Do NOT duplicate ChatGPT's scope; focus strictly on whether this spec can be turned into correct, secure, reproducible, performant code by Claude Code without ambiguity.

---

## 1. Your mission, in one sentence

Audit the v11.4 seal package through the lens of an implementation engineer about to write code from it: identify every ambiguity, edge case, numerical-stability concern, determinism gap, security exposure, performance risk, git-workflow trap, and untestable specification that would cause Claude Code to either (a) write incorrect code, (b) write non-deterministic / non-reproducible code, (c) write code that silently violates pre-registration discipline, or (d) ship code that introduces security/data-exposure risk.

The package contains three artifacts; review each from the implementation lens:
1. **§1** — a `DECISIONS.md` arbitration entry. Implementation impact: minimal, but the falsification criterion may need code hooks if it requires automated detection.
2. **§2** — the DRAFT v2.0 sealed pre-registration. **This is the primary review target — ~85% of your effort sits here, because almost every clause becomes executable code.**
3. **§3** — a `TECH_DEBT.md` guardrail patch. Implementation impact: guardrail 1 requires a reproducible-evidence-attachment workflow that may need tooling support.

---

## 2. Your authority and posture

- **Default posture: pedantic and adversarial.** You are looking for ambiguities a careless implementer could resolve in the wrong direction.
- **Do not assume Claude Code will infer correctly.** If a clause has two plausible interpretations, flag it. Even if one interpretation is "obvious" to a human reviewer, the cost of ambiguity in a sealed pre-reg is high (an ambiguous spec implemented one way and reviewed another way is a pre-registration discipline failure).
- **Look for what is missing.** A specification can be wrong by what it omits as easily as by what it states incorrectly. Master spec §0.5.1 requires the spec to enumerate edge cases; flag every edge case the v2.0 pre-reg leaves un-enumerated.
- **Security is part of your remit.** Even a methodology spec has security implications when it references API keys, file paths, secrets, network calls, and arbitrary git operations. Flag any.

---

## 3. Severity convention (per master spec §0.5.3) — STRICTLY enforced

Use **exactly** these four tags on every comment.

| Tag | Meaning | Required action |
|---|---|---|
| `BLOCKER` | Implementation cannot proceed correctly without resolving this. Spec is ambiguous, formula is unspecifiable, numerical method is non-convergent, security exposure is present, or determinism is broken. | Strategist clarifies or re-drafts before seal. |
| `MAJOR` | Implementation will likely fail or produce a non-reproducible result, but can be patched. | Strategist or Claude Code addresses at seal time with a documented decision. |
| `MINOR` | Edge case or precision issue not affecting headline results. | Claude Code handles during implementation. |
| `NIT` | Style or naming. | Claude Code handles during implementation. |

**Calibration anchor**: in a typical 200-line sealed pre-reg, expect 0–2 BLOCKERs, 2–5 MAJORs, 5–15 MINORs. If your counts are wildly off, sanity-check your tagging.

---

## 4. MANDATORY output format per comment

Every comment must contain these 8 fields. Comments not in this format will be returned for re-drafting.

```
### Comment #<N> — <SEVERITY> — <one-line title>

**Section reference**: §<X.Y> of handoff (and master spec §<A.B> if relevant)

**Issue**: <2–4 sentence description of the implementation problem; cite specific lines or formulas from the draft>

**Failure mode if shipped as-is**: <what would actually break? Be concrete: "skewed-t ML fit will fail to converge for the bottom-decile residuals at horizons ≥ 5Y because n < 30 and η is on the boundary η = ±1." Not: "could be problematic.">

**Reference**: <library docs, numerical-recipe citation, security advisory, master spec section, or empirical evidence>

**Proposed solution**: <2–6 sentence concrete fix. Either give exact replacement text for the spec, or specify the algorithm in unambiguous pseudocode with explicit edge-case handling and fallback logic. Include the test that would verify the fix.>

**Calibrated assessment of the proposed solution**:
| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---|---|---|---|
| Proposed solution eliminates the failure mode | XX% | [LL%, UU%] | XX% | X/5 |
| Proposed solution introduces a new failure mode | XX% | [LL%, UU%] | XX% | X/5 |
| Original spec was implementable correctly and this comment is wrong | XX% | [LL%, UU%] | XX% | X/5 |
| Alternative solution Y (specify): would be preferable for this issue | XX% | [LL%, UU%] | XX% | X/5 |

**Test that proves the fix** (pseudocode or pytest skeleton):
```python
def test_<descriptor>():
    # arrange: <minimal inputs>
    # act: <call the function>
    # assert: <expected output, exact numerical value where possible>
```

**Falsification criterion for this comment**: <what would convince you this comment is wrong?>
```

**Definitions for the triple** (per master spec §6 + standing user preference):
- **% Probability**: your point estimate of the probability the outcome holds, calibrated to a Brier-score interpretation.
- **95% CI on the probability**: your uncertainty about your own point estimate.
- **% Confidence**: a single derived number, default `100% − (CI_width / 2)`, modulated downward by numerical-fragility and edge-case-density of the affected code path.
- **Conviction (1–5)**: composite holistic judgment per master spec §6.3.

**Do not skip the table or the test.** A comment without both is incomplete.

---

## 5. Implementation-correctness checklist — exhaustive, work through every item

### 5.1 Algorithmic specifiability (can the spec produce code?)

For each clause below, evaluate: is there exactly one correct implementation?

- [ ] **§3.4 sample gate `n_obs_oos < 5 × HAC_lag`**: at the exact boundary `n_obs_oos = 5 × HAC_lag`, does the cell pass or fail? `<` vs `≤` matters. The current spec uses `<` (fail if less than). Confirm or flag.
- [ ] **§3.4 `HAC_lag = floor(1.5 × h)` in months**: what is `floor(1.5 × 1) = 1`? Is `HAC_lag = 1` for 1Y horizon a defensible Newey-West specification, or should there be a floor like `max(1, floor(1.5 × h))`? Inspect every horizon: h ∈ {12, 36, 60, 120} months → HAC_lag ∈ {18, 54, 90, 180}. OK at those values. But spec should be explicit.
- [ ] **§3.4 unit conventions**: `horizon_months` is unambiguous. But `n_obs_oos` — is this monthly observations of OOS test points, or all observations including overlap? Different definitions yield wildly different gate behavior. Specify.
- [ ] **§3.5 Newey-West**: which library? `statsmodels.regression.linear_model.OLS(...).fit(cov_type='HAC', cov_kwds={'maxlags': L})` is the standard. Spec doesn't specify. Add.
- [ ] **§3.6 Stambaugh AR(1) > 0.85 trigger**: AR(1) estimated on what window? Expanding through `t`, or full-sample? Different windows → different coefficients → different trigger states. Specify.
- [ ] **§3.6 Campbell-Yogo CIs "for all coefficients regardless"**: which implementation? There is no canonical Python package; Campbell-Yogo requires solving a numerical equation for the critical-value bounds. Specify the source code or library.
- [ ] **§3.7 skewed-t Hansen (1994) parameters**: η ∈ [−1, 1], ν > 2. ML fit on residuals: what optimizer? `scipy.optimize.minimize` with which method? L-BFGS-B with bounds? Trust-constr? Specify. Fallback on non-convergence (per master spec §3.7 of methodology doc): refit Gaussian — is this fallback in the v2.0 pre-reg or only in the master spec?
- [ ] **§3.7 conditional forecast formula `regression_mean(t) + skewed_t(η_t, ν_t) · σ_t`**: is σ_t the OLS residual SD or the HAC-adjusted? Is it the in-sample residual SD or the forward-projected SD? Specify.
- [ ] **§3.8 stationary bootstrap**: which implementation? `arch.bootstrap.StationaryBootstrap` requires a block-length parameter; spec says "Politis-White (2004) automatic bandwidth" — is the implementation `arch.bootstrap.optimal_block_length`? Confirm.
- [ ] **§3.8 `n_bootstrap = 50,000`**: with what RNG seed? Master spec §8.3 says `numpy.random.default_rng(seed=42)` globally — does this propagate into `arch.bootstrap`? Audit.
- [ ] **§4.1 priors as 0.5/0.5**: are these used anywhere in §5 criteria evaluation? If not, they are purely declarative. If they ARE used (e.g., for a Bayesian posterior in §5), specify where.
- [ ] **§5 Criterion 4 `|t_NW| > 1.65 at any evaluable horizon`**: at exactly t_NW = 1.65, pass or fail? Specify (`>` strict).
- [ ] **§5 Criterion 7 Bonferroni p < 0.0025**: where does 0.0025 come from algorithmically? 0.05 / 20 = 0.0025. Is the 20 the number of (component × horizon) cells (5 × 4 = 20)? Or something else? Specify the multiplicity denominator explicitly.
- [ ] **§6.2 annual re-test**: triggered by what — a calendar date, a git tag, a cron job? Specify the trigger.
- [ ] **§6.3 bullet 3 Brier score "worse than Gaussian fallback"**: by how much? Any positive difference? A statistically significant difference? Specify the threshold.
- [ ] **§8 invariant 1 "sealing commit hash"**: what is the comparison op at write-time? `git merge-base --is-ancestor <pre_reg_commit> HEAD` — is this exactly the check? Or is it something else (e.g., a hardcoded SHA in code)? Specify.

### 5.2 Edge case enumeration

- [ ] **§3.2 RRPONTSYD zero-fill pre-2013-09-23**: what about the exact boundary date? Spec says "pre-2013-09-23" — does 2013-09-23 itself zero-fill or take the source value? Specify (`<` strict).
- [ ] **§3.4 cells where `n_obs_oos = 0`** (e.g., very short OOS window): spec says count as `not_evaluable` → FAIL. Is `not_evaluable` distinguishable from a normal FAIL in the output verdict JSON? Per audit trail, they should be distinct.
- [ ] **§3.7 skewed-t fit on a sample where all residuals are identical** (degenerate; pathological but possible at sample edges): ML fit explodes. Fallback required.
- [ ] **§3.7 skewed-t fit on n < some minimum** (Hansen 1994 requires n > some floor for ML stability): not specified. Add minimum-n requirement, with fallback.
- [ ] **§3.8 bootstrap on a sample where the optimal block length returns 0 or >= n**: edge case. Specify clamping.
- [ ] **§5 if ALL 7 criteria are `not_evaluable`** (extreme — would require zero data): what is the verdict? Spec says `not_evaluable` counts as FAIL per criterion → all FAIL → n_pass = 0 → FAIL. Is this the intended behavior, or should "all not_evaluable" be a special UNDEFINED state?
- [ ] **§6.2 annual re-test with no new data** (e.g., FRED outage at re-test date): does the cadence skip and re-trigger next year, or run on stale data?
- [ ] **§8 HARD GATE: what if a developer writes a commit DIRECTLY on `spec/liquidity-composite-v2.0` BEFORE the seal commit?** Pre-reg commit isn't an ancestor of HEAD until after seal. Implementation must handle the pre-seal state — e.g., a flag `SEALED=False` in `_catalog.json` that disables the HARD GATE until the seal commit exists.

### 5.3 Numerical stability & convergence

- [ ] **§3.7 skewed-t ML**: η near ±1 causes likelihood gradient instability. ν near 2 (heavy tails) causes integration issues. Specify bounded parameter constraints AND a non-convergence fallback.
- [ ] **§3.6 Stambaugh bias correction**: the analytical formula has a `1 / (1 − ρ)` term — divergent as ρ → 1. Threshold at 0.85 only partially mitigates; what about ρ = 0.99? Specify max-ρ clamp or alternative bias-correction method.
- [ ] **§3.5 Newey-West with very small T**: lag selection breaks if T < lag. Verify `statsmodels` behavior or specify guard.
- [ ] **§3.8 bootstrap with 50,000 reps × 5 horizons × 3 composites**: is there a numerical-precision issue in averaging 50K Brier scores? `np.mean` is fine but `np.sum` on float32 may accumulate error. Specify float64.

### 5.4 Determinism & reproducibility

- [ ] **Global RNG seed**: master spec §8.3 specifies `numpy.random.default_rng(seed=42)`. Does the v2.0 pre-reg confirm this is the seed for the 50,000-rep bootstrap and any MCMC?
- [ ] **`arch.bootstrap.StationaryBootstrap` seed**: needs to be passed `seed=42` (or derived) explicitly; not all `arch` versions propagate numpy's default.
- [ ] **MCMC in §3.7 if used**: PyMC defaults to non-deterministic chain seeds; require explicit `random_seed=42`.
- [ ] **scipy.optimize for skewed-t ML**: needs a deterministic starting point; specify (e.g., method-of-moments seed).
- [ ] **pandas operations on a multi-source dataset**: dict-iteration order, set-comprehension order — are all derived series reproducible byte-for-byte across runs?
- [ ] **Floating-point summation order**: aggregation of n_pass criteria must be order-deterministic.

### 5.5 Look-ahead audit at the formula level

(Master spec §2.3 says: "For every model output at date *t*, you must be able to answer: 'What information was available at the close of day *t*?'")

- [ ] **§3.2 expanding window estimation through `t`**: does "through `t`" include or exclude `t`? Strictly, predicting `r_{t,t+h}` requires features known AT `t`, so the regression should use data up to and INCLUDING `t`. Confirm.
- [ ] **§3.4 sample gate `n_obs_oos`**: counted as of `t` or as of the end of the full sample? Critical for vintage analysis.
- [ ] **§3.7 skewed-t fit "on expanding-window training residuals"**: training window goes through `t` or through `t − 1`? At each new test date, the most recent residual is fresh — is it included in the fit at `t`?
- [ ] **§3.6 Stambaugh ρ estimate**: same question — through `t` or `t − 1`.
- [ ] **§3.8 bootstrap on what sample**: the full sample, or expanding through `t`? The latter is the only PIT-compliant choice for OOS evaluation.
- [ ] **GDP / macro data vintage**: §3.2 is silent on vintage. For revisable series (BUSLOANS, M2SL are revised), does the pre-reg specify latest-vintage or real-time-vintage? If silent, default behavior may use latest-vintage → look-ahead bias. Flag for clarification.
- [ ] **The HARD GATE itself is a look-ahead protection**: does the implementation actually run the ancestor check before EVERY artifact write, or only at session start? Per-write is the safe choice.

### 5.6 Test scaffold adequacy

For each major specification, is there at least one test specified?

- [ ] §3.4 gate: test at boundary `n_obs_oos = 5 × HAC_lag − 1` (fail) and `= 5 × HAC_lag` (need to know: pass or fail).
- [ ] §3.7 skewed-t: test on a known-distribution (e.g., scipy `t.rvs(df=5, size=1000)`) and verify fitted ν is close to 5.
- [ ] §3.7 fallback to Gaussian: test on degenerate sample, verify Gaussian fallback fires.
- [ ] §3.8 bootstrap: test that two runs with the same seed produce byte-identical samples.
- [ ] §5 each of 7 criteria: test on a known-pass and known-fail synthetic input.
- [ ] §6.2 annual re-test trigger: test that the trigger fires exactly once per year.
- [ ] §8 HARD GATE: test that an artifact write fails if pre-reg commit is not an ancestor of HEAD.

The spec does not list these tests. Flag as `MAJOR` and propose test scaffold inline.

### 5.7 Performance budget

- [ ] **§3.8 bootstrap 50,000 reps × 4 horizons × 3 composites**: is this 600,000 bootstrap applications. Is each ~1 sec → 7 days? Or ~10 ms → 100 min? Estimate, propose budget, propose parallelization (joblib.Parallel) if needed.
- [ ] **§3.7 skewed-t fit at every test date in expanding-window OOS**: ~480 test dates × 4 horizons × 3 composites = 5,760 ML fits. Budget?
- [ ] **§3.6 Stambaugh + Campbell-Yogo at every test date**: similar count, more numerical solves. Budget?
- [ ] **Total v11.4 sprint runtime**: Strategist did not specify a performance budget. Master spec §0.5.1 requires "Performance budget: <expected runtime, memory ceiling>" per spec. Flag the absence.

### 5.8 Git workflow / HARD GATE implementation hooks

- [ ] **§8 HARD GATE ancestor check**: what command? `git merge-base --is-ancestor <seal_commit> HEAD` returns 0 if ancestor, 1 if not. Specify.
- [ ] **What if the local clone has shallow history** (`git clone --depth 1`)? Ancestor check would fail spuriously. Implementation must `git fetch --unshallow` or document the requirement.
- [ ] **What if HEAD is detached?** `git merge-base` should still work, but verify.
- [ ] **What if `<seal_commit>` is rewritten** (e.g., a rebase) post-seal? HARD GATE invariant says immutable — must specify branch protection or signed-tag enforcement. Master spec §1.6.9 specifies "Disallow force-push to `main`" but the seal commit will be on `spec/liquidity-composite-v2.0`. Branch protection rules on the spec branch?
- [ ] **Auto-push on every successful run (master spec §1.6.3)**: does v11.4 sprint run produce a commit even during partial-failure runs? Specify atomicity.
- [ ] **Git LFS quota**: 50,000-rep bootstrap output if stored as parquet at every test date could be GB-scale. LFS free tier is 1 GB storage + 1 GB bandwidth/month. Forecast LFS consumption for v11.4 sprint. Flag if > budget.

### 5.9 Security & secrets

- [ ] **Does the spec reference any secrets** (FRED API key, GitHub token, deploy token)? Pre-reg is committed to git — any secret value embedded is a leak.
- [ ] **`config.yaml` references** in master spec §1.5.1: confirm `.gitignore` excludes it (master spec §1.6.4 says yes). Cross-check that the v2.0 pre-reg does not require any new secret-bearing file.
- [ ] **Bandit security scan**: master spec §1.6.6 pre-commit runs `bandit -r src/`. The v2.0 pre-reg does not introduce new code; but the eventual implementation will. Flag any spec clause that would require `eval`/`exec`, deserialization of untrusted parquet, subprocess with user input, etc.
- [ ] **`detect-secrets` pre-commit**: master spec §1.6.6 lists this. Will the eventual implementation include any pattern (e.g., a test fixture containing a fake API key) that would trip `detect-secrets`? Pre-empt with allowlist guidance.

### 5.10 §3 TECH_DEBT guardrails (implementation impact)

- [ ] **Guardrail 1 reproducible-evidence requirement**: enforcement mechanism? A pre-commit hook that checks every TECH_DEBT.md entry for required fields? Or manual? Specify.
- [ ] **Guardrail 2 "RESOLVED-by-reclassification" status**: is this tracked in a structured field, or free-text? Suggest a YAML front-matter schema for TECH_DEBT.md entries.

---

## 6. Specific concerns about implementability of Strategist push-backs

### Push-back 1 — `RESEARCH_RECORD.md`

- [ ] File location: repo root. Conflicts with `README.md`, `README_USER.md`, `CHANGELOG.md`, `DECISIONS.md` already at root. Adding another root-level `.md` increases repo-root clutter; alternative: `docs/RESEARCH_RECORD.md`.
- [ ] Format: structured (YAML/JSON front-matter for each entry) or free-text? Structured allows automated cross-linking from dashboard footer.
- [ ] Update workflow: who updates this file when a sprint closes FAIL? Should the closeout-report script auto-append?

### Push-back 2 — Add §9 verification item #5 (realized `n_obs_oos` check)

- [ ] Implementation: Claude Code must `git checkout spec/liquidity-composite-v1.0`, read `outputs/lc_v1_verdict.json`, extract per-cell `n_obs_oos`, write summary into v2.0 pre-reg's §9 as a transcribed table BEFORE sealing. This is a non-trivial workflow step. Specify the sub-tasks for Claude Code.
- [ ] What if the v1.0 verdict.json does not contain `n_obs_oos` per cell? Need to recompute from `model_scores.parquet`. Flag.

### Push-back 3 — `§4.1` pre-empt note

- [ ] Implementation: free-text insertion at end of §4.1's Strategist note. No code impact. Confirm.

---

## 7. Out-of-scope items — DO NOT review these

ChatGPT 5.5 Pro is handling these in parallel. Do not duplicate:

- Whether the prior choice (0.5/0.5 vs asymmetric) is **methodologically** correct.
- Whether the Brier score comparison **statistically** distinguishes Gaussian from skewed-t.
- Whether the n_pass ≥ 4 of 7 rule **statistically** has appropriate Type I error.
- Whether the falsification window design is **methodologically** sufficient.
- Whether the merge-to-main option (b′) **strategically** dominates option (b).

If you find an issue that straddles implementation and methodology, flag under implementation with a note "ChatGPT 5.5 Pro should also evaluate from methodology angle."

---

## 8. Specific anti-rubber-stamp clauses

- **Do not assume the Strategist's "Open Verification Items" cover all gaps.** The Strategist explicitly says §9 items are "what I identified during drafting." Your job is to identify what the Strategist did NOT identify.
- **Do not accept "TBD by Claude Code at seal time" as a resolution.** If something is genuinely deferred, it should be explicit (with a sub-task list). Vague deferral is a spec ambiguity → flag.
- **Do not assume any formula is implementable just because it has a paper citation.** Hansen (1994) skewed-t has published numerical pathologies; Campbell-Yogo (2006) requires custom numerical work. Flag every non-trivially-implementable reference.
- **Do not assume the master spec covers it.** The v2.0 pre-reg must be self-contained per master spec §0.5.1. Cross-reference is allowed, but a reader of the sealed pre-reg should not need to load the master spec to execute.

---

## 9. Expected output structure (template you will fill)

Produce a single markdown document titled `REVIEW_v11_4_Codex_implementation.md` with this structure:

```markdown
# REVIEW v11.4 — Codex — Implementation Correctness

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
| If sealed as-drafted, implementation will produce ≥ 1 silent bug (wrong numerical result, never crashes) | XX% | [LL%, UU%] | XX% | X/5 |
| If sealed as-drafted, implementation will produce ≥ 1 visible bug (crash, NaN, infinite loop) | XX% | [LL%, UU%] | XX% | X/5 |
| Sealing with my BLOCKER/MAJOR fixes incurs zero re-seal risk over 12 months | XX% | [LL%, UU%] | XX% | X/5 |
| Performance budget for v11.4 sprint exceeds 4 hours of wall-clock runtime on a 2020-class laptop | XX% | [LL%, UU%] | XX% | X/5 |

## Comment-by-comment review

### Comment #1 — <SEVERITY> — <title>
[per format in §4 above, INCLUDING the test pseudocode]

### Comment #2 — ...
...

## Cross-cutting concerns (issues that touch multiple sections)
[paragraph per concern, with probability/confidence/conviction triple]

## Specific assessment of Strategist push-backs 1–3 (implementation angle only)
[concise paragraph per push-back, each with probability/confidence/conviction triple]

## Performance budget estimate
| Operation | Est. runtime | Confidence in estimate |
|---|---|---|
| Skewed-t ML fits (5,760×) | XX min | XX% |
| Bootstrap (600K) | XX min | XX% |
| Stambaugh + Campbell-Yogo | XX min | XX% |
| Total v11.4 sprint | XX min | XX% |

## Security audit summary
[bullet list of any security-relevant findings, even if "no findings"]

## Test scaffold proposed (filling §5.6 gap)
[pytest-style test scaffold for every public function the v2.0 pre-reg implies]

## Items I flagged that the Strategist's self-review missed
[bullet list with severity tags]

## Falsification criterion for this entire review
What evidence in the next 6 months would convince me this review was mis-calibrated?
```

---

## 10. Pacing / time budget

- Allocate ~4–6 hours.
- For each numerical method (Stambaugh, Campbell-Yogo, skewed-t ML, stationary bootstrap), spend at least 15 minutes verifying library availability + numerical-stability characteristics + license compatibility.
- For the git workflow / HARD GATE items, write a small bash script to actually test `git merge-base --is-ancestor` behavior under edge cases (detached HEAD, shallow clone, force-push) — paste the output into the review.
- If you are unsure about a specific item, mark it as "NEEDS_STRATEGIST_CLARIFICATION" with the specific question rather than guessing.

---

## 11. Final reminder

Per master spec §0.5.4: **the Strategist (Claude AI) owns the final merge decision**. Your review is consultative. The Strategist will arbitrate any reviewer-reviewer disagreement (between you and ChatGPT 5.5 Pro) by referring back to the spec and methodology references.

Your review will be archived as `reviews/REVIEW_v11_4_Codex_implementation.md` and committed to git per master spec §1.6.12.

Go.
