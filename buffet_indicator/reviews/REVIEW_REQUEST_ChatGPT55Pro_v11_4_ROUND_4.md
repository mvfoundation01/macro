# REVIEW REQUEST — ChatGPT 5.5 Pro — Round 4 (DRAFT_v4) — NARROW VERIFICATION

> **Target work product**: `MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER_DRAFT_v4.md` (attached)
> **Required context**: `DECISIONS_2026_05_24_v11_4_arbitration_ROUND_3.md` (attached), `REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_3.md` (your prior round-3 review)
> **Reviewer role**: METHODOLOGY REVIEWER, NARROW FINAL VERIFICATION
> **Sister review**: Codex round-4 narrow check is requested in parallel
> **Expected effort**: ~30 minutes (this is a final-check, not a full re-review)

---

## §1 — Round-4 mission (NARROW)

Round-3 returned `SEAL_WITH_MINOR_EDITS` from you with 1 VERIFY-FAIL upgraded to MAJOR (§2.2 arithmetic) and 1 NEW MINOR (§10.2 struck-through row). You explicitly stated: *"I do **not** recommend Round 4 if those edits are made and checked."*

Round-4 exists because the Strategist has accumulated 5 confessed factual mistakes across rounds 1–3 and wants one final independent verification before sealing. **The scope is intentionally narrow: verify the 3 edits to your domain were applied correctly, plus a final regression check.**

**You do NOT need to re-verify anything you already VERIFY-PASS'd in round-3**: §3.8 bootstrap immutability, §0.2 B-1.5 invariant, §3.9 Stambaugh boundary, §3.3/§12 `train_cutoff_inclusive`. Those are locked.

---

## §2 — Required verification checklist (3 items)

### §2.1 — Verify §2.2 arithmetic correction

**Round-3 finding**: §2.2 reported `≈ 8.9%`; correct value is `2.7566% ≈ 2.8%` under stated marginals.

**DRAFT_v4 location to verify**: §2.2 "Null calibration of the binary rule"

**Expected fix**:
- The 4 tail terms displayed: `0.0254580 + 0.0020277 + 0.0000791 + 0.0000012`
- Sum displayed as `0.0275660`
- Percentage form displayed as `2.7566%` and rounded `≈ 2.8%`
- Interpretive paragraph adopts your round-3 proposed wording about non-independence caveats

**Verify**: do an independent Poisson-binomial computation on `p = [0.10, 0.10, 0.05, 0.10, 0.60, 0.80, 0.05]` and confirm `P(N ≥ 4) = 0.0275660` exactly. If your earlier round-3 number was off (you reported `0.027566`, with 5 digits of precision), confirm DRAFT_v4's 7-digit `0.0275660` matches your recomputation.

### §2.2 — Verify §2.1 wording tightening

**Round-3 finding**: §2.1's phrase "n_pass = 4 reached only via admissibility criteria" was logically loose because with only 2 non-predictive criteria, n_pass = 4 cannot be reached *only* through admissibility.

**DRAFT_v4 location to verify**: §2.1 "Binary verdict" — final paragraph about predictive subset reporting.

**Expected fix**: replace with your proposed wording: *"cases where `n_pass = 4` depends on C5–C6 admissibility criteria and only two predictive criteria pass"*.

**Verify**: the new wording is logically tight (a 4-pass verdict with both C5 and C6 passing requires exactly 2 of the 5 predictive criteria to pass; the new wording captures this precisely).

### §2.3 — Verify §10.2 row deletion

**Round-3 finding**: §10.2 retained a struck-through "Decision rule" row; should be deleted entirely.

**DRAFT_v4 location to verify**: §10.2 "Explicit deltas (v1.0 → v2.0)"

**Expected fix**:
- The struck-through `~~Decision rule~~` row is REMOVED from the table (not retained with strikethrough)
- A brief explanatory sentence appears below the table: "DRAFT_v2 proposed a 'decision rule' delta (two-tier `n_pass ≥ 4 AND n_pass_predictive ≥ 2`) which was withdrawn in DRAFT_v3 per ChatGPT round-2 #6. v2.0 inherits v1.0's plain `n_pass ≥ 4 of 7` rule unchanged per §2.1 — no decision-rule delta exists in v2.0."

**Verify**: the table itself contains no decision-rule row (struck-through or otherwise).

---

## §3 — Regression check (final sweep)

Confirm that none of the 11 edits in DRAFT_v3 → DRAFT_v4 introduced new methodology issues. Specifically:

1. **§2.2 calibration block consistency** — does the new explicit Poisson-binomial term breakdown contradict any other section? (Specifically check that §5 criterion thresholds match the marginal probabilities used in §2.2's table.)
2. **§2.1 + §12 + §8.1 invariant #3 coherence** — does the decision rule appear identically as `n_pass ≥ 4 of 7` everywhere it is mentioned? Verify §8.1 item #3 still states the plain rule, §12 verdict logic still references plain rule, no residual two-tier language anywhere.
3. **§10.2 table integrity** — after deleting the decision-rule row, are all remaining delta rows still consistent with §1–§7? (No orphan references to deleted row.)

---

## §4 — Out-of-scope (do NOT re-review)

- §3.8 `["stationary"]` column revert — Codex's domain (BLOCKER from their side).
- §11.2 heading count and skewed-t test tolerance — Codex's domain.
- §12 enum rename `"stationary_optimal"` — Codex's domain.
- §9 item #11 cross-reference fix — Codex's domain.
- All §3.7 / §3.8 / §3.9 implementation details — already VERIFY-PASS'd by you in round-3.

If you find a methodology issue with anything Codex owns, flag with "Codex should also evaluate."

---

## §5 — Expected output format

Short verification document. Suggested structure:

```markdown
# REVIEW v11.4 — ChatGPT 5.5 Pro — Methodology — Round 4 (NARROW)

## Headline
- §2.1 wording fix: VERIFY-PASS | VERIFY-FAIL
- §2.2 arithmetic fix: VERIFY-PASS | VERIFY-FAIL
- §10.2 row deletion: VERIFY-PASS | VERIFY-FAIL
- Regression check: CLEAN | <list>
- Recommendation: SEAL_AS_DRAFTED | SEAL_WITH_MINOR_EDITS | RE-DRAFT_REQUIRED

## Calibrated meta-assessment
| Outcome | P | 95% CI | Confidence | Conviction |
|---|---|---|---|---|
| DRAFT_v4 is sealable as-drafted (zero further methodology changes) | XX% | [LL%, UU%] | XX% | X/5 |
| §2.2 arithmetic now correct (independent recomputation matches 0.0275660) | XX% | [LL%, UU%] | XX% | X/5 |
| Round-5 needed | XX% | [LL%, UU%] | XX% | X/5 |
| At sprint close, v2.0 PASS | XX% | [LL%, UU%] | XX% | X/5 |

## Verification of round-3 findings (3 items)
[short blocks: 3-5 sentences each]

## Regression check
[bullet list — flag any new methodology concerns]

## NEW findings (if any)
[full block format only if you find new issues]

## Out-of-scope notes
[any cross-domain observations for Codex]

## Falsification criterion for this round-4 review
[what evidence in next 6 months would change your conclusion]
```

---

## §6 — Pacing and policy

- **Expected effort**: ~30 minutes. If round-4 takes you more than 90 minutes, flag this as meta-feedback indicating DRAFT_v4 is more changed than the Strategist believes.
- **High bar for new findings**: round-4 is a final sanity check. A new MAJOR finding would be unexpected; a new BLOCKER would be very surprising. Both are valid if real — just report with high specificity.
- The Strategist (Claude AI) retains final merge authority per master spec §0.5.4. Your round-4 review is archived as `reviews/REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_4.md`.

Go.
