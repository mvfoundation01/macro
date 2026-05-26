# REVIEW REQUEST — ChatGPT 5.5 Pro — Round 2 (DRAFT_v2)

> **Target work product**: `MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER_DRAFT_v2.md` (attached) — the redrafted v2.0 pre-registration.
> **Round-1 inputs (read for context, do NOT re-review)**: `REVIEW_v11_4_ChatGPT55Pro_methodology.md` (your round-1 review), `REVIEW_v11_4_Codex_implementation.md` (Codex's round-1 review), `STRATEGIST_HANDOFF_v11_4_seal_package.md` (original DRAFT v1), `DECISIONS_2026_05_24_v11_4_arbitration.md` (Strategist arbitration of round-1).
> **Master spec authority**: the project's master system prompt.
> **Strategist**: Claude AI.
> **Reviewer role**: METHODOLOGY REVIEWER, round 2 of 2 (expected).
> **Sister review**: Codex round-2 is NOT requested. Codex's round-1 BLOCKERs are addressed directly in DRAFT_v2 with explicit algorithmic specifications (§3.7, §3.8, §8.2, §11). Codex will verify at seal time by executing the §11 acceptance test matrix. If you find an implementation issue that requires Codex round-2, flag it as a `MAJOR` and the Strategist will arbitrate.

---

## §1 — Round-2 mission

Your round-1 review (verdict `RE-DRAFT_REQUIRED`, 2 BLOCKERs + 8 MAJORs + 2 MINORs) was substantively accepted by the Strategist (23 of 23 findings accepted). DRAFT_v2 is the redraft that incorporates your findings plus Codex's findings.

Your round-2 mission is:

1. **Verify each of your round-1 findings is adequately addressed in DRAFT_v2.** A finding is "adequately addressed" if the redraft fix either (i) matches your proposed solution, or (ii) is a documented modification that the Strategist's arbitration explains and you agree with on review.

2. **Surface any NEW issues introduced by the redraft.** Substantial restructuring is a known source of regression — flag any new BLOCKER, MAJOR, or MINOR that exists in DRAFT_v2 but not in DRAFT v1.

3. **Recommend SEAL or RE-DRAFT.** If 0 BLOCKERs and ≤ 3 MAJORs remain, recommend `SEAL_WITH_MINOR_EDITS`. Otherwise `RE-DRAFT_REQUIRED` triggers round 3 (which would be unusual).

You do NOT need to re-execute round-1's exhaustive checklist. Focus on:
- Are my findings addressed?
- Is anything broken by the redraft?

---

## §2 — Severity convention (unchanged from round 1)

`BLOCKER` / `MAJOR` / `MINOR` / `NIT` per master spec §0.5.3.

**Calibration anchor for round 2**: a clean round-2 review (0 BLOCKERs, ≤ 3 MAJORs, mostly NITs) is the expected outcome when the Strategist has accepted ≥ 90% of round-1 findings. If you find > 1 BLOCKER, that signals either a regression in the redraft or a round-1 finding you re-evaluated upward — both worth flagging explicitly.

---

## §3 — MANDATORY output format

Two structures depending on comment type:

### §3.1 — For findings that VERIFY round-1 items

```
### Verify Round-1 #<N> — <VERIFY-PASS | VERIFY-FAIL | VERIFY-MODIFIED-OK> — <one-line>

**Round-1 reference**: Comment #N (severity SEV) — "<title>"
**DRAFT_v2 location**: §<X.Y> "<title>"
**Round-1 proposed fix**: <one-sentence summary>
**DRAFT_v2 actual fix**: <one-sentence summary>
**Verdict**:
  - VERIFY-PASS: the redraft matches your proposed fix.
  - VERIFY-MODIFIED-OK: the redraft differs from your proposed fix in a way you find acceptable; explain.
  - VERIFY-FAIL: the redraft does NOT adequately address the finding. Re-state the issue with NEW severity tag and a NEW proposed fix.

**Calibrated assessment** (only required if VERIFY-FAIL):
| Outcome | P | 95% CI | Confidence | Conviction |
|---|---|---|---|---|
| The redraft fix is incomplete (round-1 finding persists) | XX% | [LL%, UU%] | XX% | X/5 |
| The redraft fix introduces a new failure mode | XX% | [LL%, UU%] | XX% | X/5 |
```

### §3.2 — For NEW findings introduced by the redraft

Use the full round-1 comment format from `REVIEW_REQUEST_ChatGPT55Pro_v11_4_seal_package.md` §4 (7 fields including calibrated assessment table and falsification criterion). NEW comments are numbered starting from `New-1`.

---

## §4 — Required verification checklist

Verify each of the 12 round-1 findings against DRAFT_v2. The Strategist's mapping of round-1 → DRAFT_v2 section is:

| Round-1 # | Severity | Strategist decision (per DECISIONS) | DRAFT_v2 location |
|---|---|---|---|
| #1 | BLOCKER | ACCEPT — provenance invariants added | §0.2 (B-1.1 through B-1.4) + §0.1 placeholders |
| #2 | BLOCKER | ACCEPT MODIFIED — gate revised to `max(60, 3×HAC_lag) OR n_eff<30` | §3.4 |
| #3 | MAJOR | ACCEPT — explicit `s+h≤t` rule | §3.3 |
| #4 | MAJOR | ACCEPT — standardized skewed-t with no separate μ | §3.7 (and Codex BLOCKER #1 merged here) |
| #5 | MAJOR | ACCEPT OPTION (a) — keep 1.65, rename "two-sided 10% screen" | §5.1 |
| #6 | MAJOR | ACCEPT — two-tier decision rule + null calibration table | §2.1 and §2.2 |
| #7 | MAJOR | ACCEPT MODIFIED — sealed BMA rationale (Strategist push-back 3 withdrawn) | §4 fully rewritten |
| #8 | MAJOR | ACCEPT — re-test reframed as stability monitoring; Brier-CI protocol | §6.1, §6.3, §6.4 |
| #9 | MAJOR | ACCEPT — inherit v1.0 verbatim, no inference drift | §3.6 |
| #10 | MAJOR | ACCEPT — §9 expanded from 4 to 10 items | §9 |
| #11 | MINOR | ACCEPT MODIFIED — option (b′) with `docs/RESEARCH_RECORD.md` location | DECISIONS §3.1 (outside DRAFT_v2) |
| #12 | MINOR | ACCEPT — TECH_DEBT YAML schema + RESOLVED-MISDIAGNOSIS | DECISIONS §3.2 (outside DRAFT_v2) |

Plus 14 Codex findings the Strategist also accepted (listed in `DECISIONS_2026_05_24_v11_4_arbitration.md` §2.1–§2.3). You do NOT need to verify all Codex findings independently — but if any Codex MAJOR/BLOCKER overlaps your domain (e.g., Codex BLOCKER #2 on PIT/vintage overlaps your MAJOR #3), spot-check that the redraft satisfies both reviewers.

---

## §5 — Specific cross-checks the Strategist requests

The Strategist's arbitration left several decisions that you, in round 1, may want to confirm or push back on:

### §5.1 — Cross-check 1: HAC lag formula choice

**Decision**: DRAFT_v2 §3.5 uses `HAC_lag = horizon_months − 1` (1Y → 11, 10Y → 119), restoring v1.0's `h * 12 − 1` convention. DRAFT v1's `floor(1.5 × horizon_months)` was a Strategist drafting error per Codex MAJOR #3.

**Question to verify**: this is a *restoration* of v1.0's convention, NOT a methodological change. Confirm that going from DRAFT v1's `floor(1.5h)` to DRAFT_v2's `h-1` does not trigger any "v2.0 changed inference rules" concerns under your round-1 MAJOR #9.

### §5.2 — Cross-check 2: Criterion 4 alpha disclosure

**Decision**: DRAFT_v2 §5.1 keeps `|t|>1.65` but renames "two-sided 10% screen — weak-evidence criterion, balanced by 4-of-7 + Bonferroni C7." This is your round-1 Option (a) — keep 1.65 with explicit alpha disclosure.

**Question to verify**: does the renamed criterion plus the two-tier rule (§2.1) + null calibration table (§2.2) adequately address your round-1 concern that the alpha shift was undisclosed? Or do you want a stronger statement (e.g., explicitly labeling the criterion as "weak" in the verdict JSON)?

### §5.3 — Cross-check 3: Sample-gate disclosure

**Decision**: DRAFT_v2 §3.4 has the revised gate `max(60, 3×HAC_lag) OR n_eff<30`. Plus it explicitly discloses that the 10Y horizon for LC_FULL is *expected* to be `not_evaluable` by construction given 1986-start data.

**Question to verify**: is "expected by construction" disclosure adequate, or do you want the Strategist to instead exclude 10Y from Criterion 4's horizon set explicitly (i.e., make Criterion 4 search {1Y, 3Y, 5Y} only)?

### §5.4 — Cross-check 4: Two-tier decision rule's null calibration

**Decision**: §2.2 reports the joint null pass probability under independence assumption ≈ 2.7%, materially below DRAFT v1's 11.2%. The independence assumption is acknowledged as an upper bound.

**Question to verify**: is the independence assumption defensible enough for a sealed pre-reg, or do you want a simulated null calibration (Monte Carlo under the empirical inter-criterion correlation matrix from v1.0) appended as a §15 sensitivity?

### §5.5 — Cross-check 5: Provenance invariants

**Decision**: §0.2 lists 4 invariants (B-1.1 through B-1.4) covering chronology and ancestor-of-seal-commit. Claude Code verifies all four at seal time.

**Question to verify**: are these 4 invariants the right set, or should a 5th invariant be added (e.g., "v1.0 verdict commit `d56174c` must be a descendant of v1.0 seal commit `a8635ef`" — defending against rewrite-history attacks)?

---

## §6 — Specific anti-rubber-stamp clauses

- **Do not reflexively VERIFY-PASS.** If a DRAFT_v2 fix is "directionally correct but understated" (the pattern you correctly identified for the Strategist's push-back 2 in round 1), say so and tag VERIFY-MODIFIED-OK only if you genuinely accept the modification.
- **Look for hidden trade-offs introduced by the redraft.** Example: the two-tier decision rule (M-4) reduces Type I error but also reduces Type II power (PASS probability). Is this trade-off explicitly disclosed in DRAFT_v2?
- **Look for inconsistency between sections.** Example: §3.4 says LC_FULL 10Y is "expected not_evaluable"; §5.3 lists 20 cells including the 4 LC × 10Y cells in Criterion 7's denominator. Is this consistent? (Per DRAFT_v2 §5.3 last paragraph: yes, by design — gate-failing cells count as Bonferroni-FAILs without reducing the denominator, preserving familywise alpha. But verify.)
- **Look for under-specified clauses in the NEW sections (§10, §11, §12, §13).** These were added in DRAFT_v2 and have not been reviewed before. Treat them with round-1-level scrutiny.

---

## §7 — Out-of-scope for round 2

Do not re-litigate:

- The decision to use Option (b′) for merge-to-main (handled in DECISIONS §3.1).
- The TECH_DEBT guardrail YAML schema (handled in DECISIONS §3.2).
- The acceptance test pseudocode in §11 (Codex's domain — you may flag if a test ID is missing from your perspective, but do not re-write tests).
- Code-level implementation correctness (Codex will verify at seal time via §11).

If you have strong opinions on the above, flag them in a separate "out-of-scope comments" section but do not block round-2 verdict on them.

---

## §8 — Expected output structure

Produce `REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_2.md` with this structure:

```markdown
# REVIEW v11.4 — ChatGPT 5.5 Pro — Methodology — Round 2

## Headline summary
- VERIFY-PASS: <count>
- VERIFY-MODIFIED-OK: <count>
- VERIFY-FAIL: <count> (list)
- NEW BLOCKERs: <count>
- NEW MAJORs: <count>
- NEW MINORs: <count>
- Recommendation: SEAL_AS_DRAFTED | SEAL_WITH_MINOR_EDITS | RE-DRAFT_REQUIRED

## Calibrated meta-assessment
| Outcome | P | 95% CI | Confidence | Conviction |
|---|---|---|---|---|
| DRAFT_v2 is sealable as-drafted (no further changes needed) | XX% | [LL%, UU%] | XX% | X/5 |
| Round-3 will be needed | XX% | [LL%, UU%] | XX% | X/5 |
| At sprint close, v2.0 verdict is PASS | XX% | [LL%, UU%] | XX% | X/5 |
| At sprint close, v2.0 verdict is FAIL → 3-of-3 meta-finding triggers | XX% | [LL%, UU%] | XX% | X/5 |

## Verification of round-1 findings
[12 verify blocks per §3.1 format]

### Verify Round-1 #1 — <verdict> — Chronology and provenance
...

## NEW findings introduced by the redraft
[Use §3.2 format. Skip section if zero new findings.]

## Cross-checks responses (per review request §5)
[Paragraph per cross-check 1-5, with probability/conviction/confidence triple]

## Out-of-scope comments (optional)
[bullet list]

## Falsification criterion for this round-2 review
What evidence in the next 6 months would convince you this round-2 verdict was mis-calibrated?
```

---

## §9 — Pacing

Round 2 is faster than round 1: ~1.5–3 hours expected.

- For each round-1 finding, scan DRAFT_v2's mapped section in ~5 min and either VERIFY-PASS quickly or escalate.
- For NEW sections (§10, §11, §12, §13), allocate ~15-20 min total for round-1-grade scrutiny.
- For cross-checks §5.1–§5.5, allocate ~30-45 min.

If round 2 takes you > 4 hours, that signals the redraft is more substantively changed than the Strategist believed; report this as meta-feedback.

---

## §10 — Final reminders

- The Strategist (Claude AI) retains final merge authority per master spec §0.5.4.
- If you and the Strategist disagree on a VERIFY-FAIL, the Strategist arbitrates by referring to literature and master spec. Document your reasoning so arbitration is feasible.
- Your round-2 review is archived as `reviews/REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_2.md` and committed to git per master spec §1.6.12.

Go.
