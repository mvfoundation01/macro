# REVIEW REQUEST — ChatGPT 5.5 Pro — Round 3 (DRAFT_v3)

> **Target work product**: `MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER_DRAFT_v3.md` (attached)
> **Required context**: `DECISIONS_2026_05_24_v11_4_arbitration_ROUND_2.md` (attached), `REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_2.md` (your prior round-2 review), `REVIEW_v11_4_Codex_implementation_ROUND_2.md` (Codex round-2 for context — Codex is reviewing DRAFT_v3 in parallel)
> **Reviewer role**: METHODOLOGY REVIEWER, round 3 of expected 3
> **Sister review**: Codex round-3 is requested in parallel (Strategist policy update: ALWAYS dual-review, no skipping)

---

## §1 — Round-3 mission

Round-2 returned `SEAL_WITH_MINOR_EDITS` from you with 1 VERIFY-FAIL (#6, two-tier rule algebraic redundancy) and 1 NEW MAJOR + 3 NEW MINORs. The Strategist accepted all 14 findings across both reviewers. DRAFT_v3 is a surgical patch of DRAFT_v2 addressing all 14.

Your round-3 mission is **focused, narrow verification** of two things:

1. **Did DRAFT_v3 correctly fix your round-2 VERIFY-FAIL (#6) and your 4 NEW findings?**
2. **Did DRAFT_v3 introduce any NEW methodological regression?** (Particularly: revert of two-tier rule, new §2.2 null calibration framing, new B-1.5 invariant, new §4.3 wording.)

You do NOT need to re-verify items you already VERIFY-PASS'd in round-2. Trust your prior judgment on §3.3, §3.7 (methodology angle only — Codex handles `arch` API), §5.1, §4, §6, §9, §10, and the §1/§3 TECH_DEBT/RESEARCH_RECORD items.

Round-3 is expected to be the **final review**. If clean → seal. If 1–2 surgical MINORs → seal with edits. Only `BLOCKER` or ≥3 MAJORs would justify round-4.

---

## §2 — Severity convention (unchanged)

`BLOCKER` / `MAJOR` / `MINOR` / `NIT` per master spec §0.5.3.

**Round-3 calibration anchor**: a clean round-3 (0 BLOCKER, 0–2 MINORs) is the expected outcome. If you find > 1 MAJOR or any BLOCKER, that signals either a regression in DRAFT_v3 or an issue you correctly upgraded from your earlier minor-MINOR thresholds.

---

## §3 — MANDATORY output format

Two structures depending on comment type:

### §3.1 — For findings that VERIFY round-2 items

```
### Verify Round-2 #<N or NEW-N> — <VERIFY-PASS | VERIFY-MODIFIED-OK | VERIFY-FAIL> — <one-line>

**Round-2 reference**: Comment #N (severity SEV) — "<title>"
**DRAFT_v3 location**: §<X.Y> "<title>"
**Round-2 proposed fix**: <one-sentence summary>
**DRAFT_v3 actual fix**: <one-sentence summary>
**Verdict**:
  - VERIFY-PASS: redraft matches your proposed fix.
  - VERIFY-MODIFIED-OK: differs but acceptable; explain.
  - VERIFY-FAIL: does NOT adequately address; restate with NEW severity + NEW proposed fix.

**Calibrated assessment** (only required if VERIFY-FAIL):
| Outcome | P | 95% CI | Confidence | Conviction |
|---|---|---|---|---|
| Redraft fix is incomplete | XX% | [LL%, UU%] | XX% | X/5 |
| Redraft introduces new failure mode | XX% | [LL%, UU%] | XX% | X/5 |
```

### §3.2 — For NEW findings introduced by DRAFT_v3

Full round-1 format (7 fields including calibrated assessment table + falsification criterion).

---

## §4 — Required verification checklist (5 items only — focused round)

Verify each of your round-2 findings against DRAFT_v3:

| Round-2 # | Severity | Strategist arbitration | DRAFT_v3 location to verify |
|---|---|---|---|
| Round-2 #6 VERIFY-FAIL | (upgraded to BLOCKER per arbitration) | ACCEPT Option A — revert to plain `n_pass ≥ 4 of 7` | §2.1 and §2.2 (full rewrite); §8.1 invariant #3; §10.2 (removed delta row) |
| Round-2 New-1 NEW MAJOR | (n_bootstrap 50K immutable vs 10K fallback) | ACCEPT | §3.8 (no downsample); §8.1 invariant #10; §11.3 (rewritten — no downsample option); §11.2 `test_bootstrap_count_policy_is_not_runtime_dependent` |
| Round-2 New-2 NEW MINOR | (5th provenance invariant) | ACCEPT | §0.2 invariant B-1.5 |
| Round-2 New-3 NEW MINOR | (Stambaugh boundary table contradiction) | ACCEPT — fixed elsewhere by Codex round-2 New-5 | §3.9 Stambaugh row corrected |
| Round-2 New-4 NEW MINOR | (`train_cutoff` exclusive vs inclusive) | ACCEPT | §3.3 + §12 verdict JSON field renamed `train_cutoff_inclusive` |

**Plus one new cross-check the Strategist requests:**

**Cross-check §C-1 — §2.2 null calibration rewrite**: DRAFT_v3 §2.2 reports `P(n_pass ≥ 4 | null, independent marginals) ≈ 8.9%` using the marginal-probability table you proposed in round-1. Three caveats are now disclosed:
1. Independence assumption is approximate (positive correlation between admissibility criteria likely)
2. Predictive criteria may also correlate under misspecification
3. PASS/FAIL is exclusively the binary rule, not the calibration

The Strategist intentionally did NOT add a Monte Carlo simulation under empirical correlation matrix (your round-2 §5.4 raised this as a possibility but DRAFT_v3 stops at the analytical bound with disclosed caveats). **Question to verify**: is this acceptable, or do you want the Monte Carlo simulation appended as §15 sensitivity?

---

## §5 — Out-of-scope (do NOT re-review)

- §3.7 `arch.SkewStudent` API correctness — Codex's domain, fixed per Codex round-2 BLOCKER #1.
- Component IDs (`z1..z5`) correctness — Codex's domain, fixed per Codex round-2 BLOCKER #2.
- `arch.bootstrap.optimal_block_length` column name — Codex's domain, fixed per Codex round-2 New-3.
- `arch.SkewStudent.loglikelihood` signature — Codex's domain.
- `should_apply_stambaugh(0.85) == False` test scaffold — Codex's domain.
- Cross-platform seal commands — Codex's domain.
- Verdict JSON schema field types — Codex's domain.

If you find a methodology issue that overlaps with the above, flag and note "Codex should also evaluate."

---

## §6 — Specific anti-rubber-stamp clauses

- **Verify the §2.2 calibration arithmetic.** If you proposed `P(n_pass ≥ 4)` for a different vector of marginal probabilities in your round-2 cross-check §5.4, the DRAFT_v3 number (8.9%) should be checked against an independent recomputation under the marginals stated in DRAFT_v3 §2.2 table. If 8.9% is wrong, surface it.
- **Check the §10.2 delta table is consistent with §2.1.** DRAFT_v3 says the decision rule reverts to v1.0's plain rule. §10.2 should reflect this (no "decision rule" delta row). Verify.
- **Check that the "predictive subset reporting" in §2.1 is purely descriptive.** Specifically: it must not be a gate, even by implication. If §2.1's wording suggests `n_pass_predictive` could veto a `n_pass ≥ 4` PASS, that's a regression.
- **Check §8.1 invariants list completeness.** DRAFT_v3 lists 13 immutables (DRAFT_v2 had 11). Verify items added (#10 strengthened, #12 component IDs, #13 b_sb column) are correctly characterized as immutable.
- **Check the §6.3 falsification criteria preserved.** No methodology change in §6 — verify visually.

---

## §7 — Expected output structure

Produce `REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_3.md` with:

```markdown
# REVIEW v11.4 — ChatGPT 5.5 Pro — Methodology — Round 3

## Headline summary
- VERIFY-PASS / VERIFY-MODIFIED-OK / VERIFY-FAIL counts
- NEW BLOCKER / MAJOR / MINOR counts
- Recommendation: SEAL_AS_DRAFTED | SEAL_WITH_MINOR_EDITS | RE-DRAFT_REQUIRED

## Calibrated meta-assessment
| Outcome | P | 95% CI | Confidence | Conviction |
|---|---|---|---|---|
| DRAFT_v3 is sealable as-drafted (zero further changes) | XX% | [LL%, UU%] | XX% | X/5 |
| Round-4 needed | XX% | [LL%, UU%] | XX% | X/5 |
| At sprint close, v2.0 PASS | XX% | [LL%, UU%] | XX% | X/5 |
| At sprint close, v2.0 FAIL → 3-of-3 meta-finding | XX% | [LL%, UU%] | XX% | X/5 |
| The §2.2 8.9% calibration number is correct under stated marginals | XX% | [LL%, UU%] | XX% | X/5 |

## Verification of round-2 findings (5 items)
[blocks per §3.1]

## NEW findings introduced by DRAFT_v3 (if any)
[blocks per §3.2]

## Cross-check §C-1 response (Monte Carlo necessity)
[paragraph with probability/confidence/conviction triple]

## Out-of-scope notes (optional)
[any cross-domain observations for the Strategist to relay to Codex]

## Falsification criterion for this round-3 review
What evidence in next 6 months would convince you round-3 was mis-calibrated?
```

---

## §8 — Pacing

Round-3 is faster than round-2: ~1–2 hours expected. The verification checklist is only 5 items + 1 cross-check. The main analytical work is verifying the §2.2 calibration arithmetic.

If round-3 takes you > 3 hours, report this as meta-feedback — it would signal DRAFT_v3 is more substantively changed than the Strategist believes.

---

## §9 — Final reminders

- The Strategist (Claude AI) retains final merge authority per master spec §0.5.4.
- Your round-3 review is archived as `reviews/REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_3.md`.
- If the recommendation is `SEAL_AS_DRAFTED` or `SEAL_WITH_MINOR_EDITS`, the Strategist will proceed to seal authorization after consolidating with Codex round-3.

Go.
