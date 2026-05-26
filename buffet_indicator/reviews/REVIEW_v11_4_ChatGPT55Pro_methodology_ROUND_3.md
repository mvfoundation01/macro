# REVIEW v11.4 — ChatGPT 5.5 Pro — Methodology — Round 3

## Headline summary

- **VERIFY-PASS**: 4
  - Round-2 New-1 — `n_bootstrap = 50,000` immutability / no 10K fallback
  - Round-2 New-2 — fifth provenance invariant B-1.5
  - Round-2 New-3 — Stambaugh `ρ̂ = 0.85` boundary correction
  - Round-2 New-4 — `train_cutoff_inclusive` wording/schema correction
- **VERIFY-MODIFIED-OK**: 0
- **VERIFY-FAIL**: 1
  - Round-2 #6 — the binary decision-rule revert is correct, but the §2.2 null-calibration arithmetic is wrong under the stated marginals.
- **NEW BLOCKERs**: 0
- **NEW MAJORs**: 1
  - New-1 — §2.2 reports `P(n_pass ≥ 4) ≈ 8.9%`; independent recomputation gives `2.7566% ≈ 2.8%`.
- **NEW MINORs**: 1
  - New-2 — §10.2 still includes a struck-through “Decision rule” delta row; delete it entirely to satisfy the requested “no decision-rule delta row” condition and avoid parser ambiguity.
- **Recommendation**: `SEAL_WITH_MINOR_EDITS`

DRAFT_v3 is not sealable **as drafted** because §2.2 contains a numerical calibration error. The correction is surgical: replace `8.9%` and its interpretive sentence with the exact Poisson-binomial calculation under the stated marginal probabilities, and remove the residual struck-through §10.2 decision-rule row. I do **not** recommend Round 4 if those edits are made and checked.

## Calibrated meta-assessment

| Outcome | P | 95% CI | Confidence | Conviction |
|---|---:|---:|---:|---:|
| DRAFT_v3 is sealable as-drafted (zero further changes) | 4% | [1%, 12%] | 88% | 4.5/5 |
| Round-4 needed | 12% | [4%, 27%] | 85% | 3.5/5 |
| At sprint close, v2.0 PASS | 26% | [13%, 44%] | 84% | 3/5 |
| At sprint close, v2.0 FAIL → 3-of-3 meta-finding | 68% | [50%, 82%] | 84% | 3.5/5 |
| The §2.2 8.9% calibration number is correct under stated marginals | 0.5% | [0%, 3%] | 98% | 5/5 |

## Verification of round-2 findings (5 items)

### Verify Round-2 #6 — VERIFY-FAIL — Decision rule fixed, null-calibration arithmetic wrong

**Round-2 reference**: Comment #6 / VERIFY-FAIL, upgraded to BLOCKER in arbitration — “Two-tier decision rule algebraically redundant.”

**DRAFT_v3 location**: §2.1 “Binary verdict”; §2.2 “Null calibration of the binary rule”; §8.1 invariant #3; §10.2 “Explicit deltas.”

**Round-2 proposed fix**: Preserve v1.0 target comparability by reverting to plain `n_pass ≥ 4 of 7`, report `n_pass_predictive` only as transparency, delete claims that the redundant gate is stricter, and recompute/null-calibrate the plain rule under a stated vector of marginal probabilities.

**DRAFT_v3 actual fix**: §2.1 correctly restores `PASS ⇔ n_pass ≥ 4 of 7`, withdraws the two-tier rule, and states `n_pass_predictive` is not a gate. §8.1 invariant #3 correctly makes the plain rule immutable. §10.2 mostly reflects the revert, but still carries a struck-through decision-rule row. §2.2’s stated marginal table is clear, but the reported `≈ 8.9%` probability is arithmetically incorrect.

**Verdict**: VERIFY-FAIL, with **NEW severity: MAJOR**. The main algebraic/procedural fix is correct, but the requested recalibration is not. Under the stated marginal probabilities:

```text
p = [0.10, 0.10, 0.05, 0.10, 0.60, 0.80, 0.05]
N = number of passing criteria, assuming independence
P(N ≥ 4) = P(N=4) + P(N=5) + P(N=6) + P(N=7)
         = 0.0254580 + 0.0020277 + 0.0000791 + 0.0000012
         = 0.0275660
         = 2.7566% ≈ 2.8%
```

The old DRAFT_v2 `≈ 2.7%` number was not the consequence of the redundant two-tier gate; it was already the plain `n_pass ≥ 4` probability under the stated marginals. DRAFT_v3’s `8.9%` appears to come from a different, unstated probability vector or a calculation error. Also, §2.1’s phrase “cases where `n_pass = 4` was reached only via admissibility criteria” should be tightened, because with only C5–C6 non-predictive, a 4-pass verdict cannot be reached *only* via admissibility criteria.

**New proposed fix**:

1. Replace §2.2’s displayed calibration with:

   ```text
   P(n_pass ≥ 4 | null, independent marginals)
     = Σ_{k=4}^{7} P(exactly k pass | independent marginals above)
     = 2.7566% ≈ 2.8%
   ```

2. Replace the final §2.2 interpretive paragraph with:

   > Under the stated independent-marginal approximation, the plain `n_pass ≥ 4` rule has an approximately 2.8% null-pass probability. This is descriptive, not a sealed invariant and not a formal familywise-error guarantee, because the criteria are not independent and empirical dependence could move the realized null tail probability. The PASS/FAIL determination remains exclusively the binary rule in §2.1.

3. In §2.1, replace “cases where `n_pass = 4` was reached only via admissibility criteria (C5, C6)” with:

   > cases where `n_pass = 4` depends on C5–C6 admissibility criteria and only two predictive criteria pass

4. In §10.2, delete the struck-through “Decision rule” delta row entirely rather than retaining it as a historical note.

**Calibrated assessment**:

| Outcome | P | 95% CI | Confidence | Conviction |
|---|---:|---:|---:|---:|
| Redraft fix is incomplete | 96% | [88%, 99%] | 94% | 5/5 |
| Redraft introduces new failure mode | 42% | [25%, 61%] | 82% | 3.5/5 |

### Verify Round-2 New-1 — VERIFY-PASS — Bootstrap count immutability conflict removed

**Round-2 reference**: New-1 (MAJOR) — “`n_bootstrap = 50,000` invariant conflicts with the 10,000-rep performance fallback.”

**DRAFT_v3 location**: §3.8 “Stationary bootstrap”; §8.1 invariant #10; §11.2 `test_bootstrap_count_policy_is_not_runtime_dependent`; §11.3 “Performance budget.”

**Round-2 proposed fix**: Remove the runtime-conditional 10K downsample for all verdict-bearing quantities; if runtime is exceeded, cache, parallelize, or return a blocked performance-budget status rather than silently reducing bootstrap reps.

**DRAFT_v3 actual fix**: §3.8 states `n_bootstrap = 50,000` is truly immutable for verdict-bearing quantities and has no downsample option. §8.1 invariant #10 repeats the immutable rule. §11.2 adds a test forbidding runtime-dependent count policy. §11.3 says budget failure yields `BLOCKED_PERFORMANCE_BUDGET`, not a downsampled CI, while allowing lower bootstrap counts only for separately labeled diagnostic-only outputs.

**Verdict**: VERIFY-PASS. This matches the preferred fix and removes the internal contradiction.

### Verify Round-2 New-2 — VERIFY-PASS — Fifth provenance invariant added

**Round-2 reference**: New-2 (MINOR) — “Add a v1.0 verdict-descends-from-seal provenance invariant.”

**DRAFT_v3 location**: §0.2 invariant B-1.5.

**Round-2 proposed fix**: Add `git merge-base --is-ancestor a8635ef d56174c` as a seal-blocking invariant and log `v1_verdict_descends_from_v1_seal = true`.

**DRAFT_v3 actual fix**: §0.2 adds B-1.5 exactly: `git merge-base --is-ancestor a8635ef d56174c` must return exit code 0, and the seal-time provenance block logs `v1_verdict_descends_from_v1_seal = true`.

**Verdict**: VERIFY-PASS. This closes the provenance hardening gap.

### Verify Round-2 New-3 — VERIFY-PASS — Stambaugh boundary table corrected

**Round-2 reference**: New-3 (MINOR) — “Comparator table contradicts the Stambaugh `ρ̂ > 0.85` rule at the boundary.”

**DRAFT_v3 location**: §3.9 “Comparator semantics.”

**Round-2 proposed fix**: Preserve the strict `>` operator and state that `ρ̂ = 0.85` exactly does **not** trigger Stambaugh correction, or else change both the prose and table to `≥`. My preferred fix was strict `>`.

**DRAFT_v3 actual fix**: §3.9 now says `ρ̂ = 0.85` exactly → “Stambaugh NOT applied,” with strict `>` enforced.

**Verdict**: VERIFY-PASS. The boundary inconsistency is resolved.

### Verify Round-2 New-4 — VERIFY-PASS — `train_cutoff` now inclusive and schema-aligned

**Round-2 reference**: New-4 (MINOR) — “`train_cutoff = t − h` wording should be inclusive, not exclusive.”

**DRAFT_v3 location**: §3.3 OOS evaluation; §12 verdict JSON schema.

**Round-2 proposed fix**: Rename or relabel the field as `train_cutoff_inclusive = t − h`, explicitly defined as the last allowed training forecast-origin `s` under `s+h≤t`.

**DRAFT_v3 actual fix**: §3.3 defines `train_cutoff_inclusive = t - h` as “inclusive: last allowed training forecast-origin `s` under `s+h≤t`,” and §12 uses the `train_cutoff_inclusive` field in the verdict-cell schema.

**Verdict**: VERIFY-PASS. The off-by-one ambiguity is fixed.

## NEW findings introduced by DRAFT_v3

### Comment New-1 — MAJOR — §2.2 null-calibration arithmetic is wrong under the stated marginals

**Section reference**: DRAFT_v3 §2.2 “Null calibration of the binary rule.”

**Issue**: DRAFT_v3 reports `P(n_pass ≥ 4 | null, independent marginals) ≈ 8.9%`. Under the seven marginal probabilities printed immediately above that equation — `[0.10, 0.10, 0.05, 0.10, 0.60, 0.80, 0.05]` — the exact independent Poisson-binomial tail is `0.027566`, or `2.7566%`. The decision rule itself remains correct, but the calibration paragraph is numerically wrong and should not be sealed.

**Evidence / reference**:
  - Internal arithmetic: coefficient tail of `∏ᵢ[(1-pᵢ)+pᵢx]` for degrees `k ≥ 4` equals `0.027566`.
  - Round-2 review: the prior `≈2.7%` value was explicitly characterized as the plain `n_pass ≥ 4` probability under the stated marginals, not as a genuine reduction from the redundant two-tier gate.
  - DRAFT_v3 evidence: §2.1 restores the plain `n_pass ≥ 4` rule and §2.2 states the exact marginal probabilities used for calibration.

**Proposed solution**: Replace `8.9%` with `2.7566% ≈ 2.8%`; remove the sentence “Compared to a Bonferroni-corrected familywise 5% target, the 8.9% rate is moderately permissive”; and use the replacement paragraph given in the Verify Round-2 #6 block above. Optionally include the four tail terms (`0.0254580`, `0.0020277`, `0.0000791`, `0.0000012`) in a footnote or appendix for auditability.

**Calibrated assessment of the proposed solution**:

| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 94% | [85%, 98%] | 93% | 5/5 |
| Proposed solution causes downstream issue not yet identified | 5% | [1%, 14%] | 91% | 2/5 |
| Original draft was actually correct and this comment is wrong | 0.5% | [0%, 3%] | 98% | 5/5 |
| Alternative solution: append empirical-correlation Monte Carlo in §15 before seal | 18% | [7%, 35%] | 86% | 2.5/5 |

**Falsification criterion for this comment**: Show a reproducible computation using exactly the printed DRAFT_v3 marginal vector that yields `0.089`, or show that DRAFT_v3 intended a different marginal vector and documents that vector before the equation. A Monte Carlo simulation under empirical inter-criterion correlations would not falsify this arithmetic comment unless §2.2 is relabeled as an empirical-correlation calibration rather than an independent-marginal calibration.

### Comment New-2 — MINOR — §10.2 should delete, not strike through, the removed decision-rule delta row

**Section reference**: DRAFT_v3 §10.2 “Explicit deltas (v1.0 → v2.0) — UPDATED.”

**Issue**: Round-3 instructions asked to verify that §10.2 has no “decision rule” delta row after DRAFT_v3 reverts to v1.0’s plain rule. DRAFT_v3 marks the row as struck-through and says “REMOVED,” which is understandable to a human reader but can still be misread by automated parsers or future maintainers scanning the delta table. Since the decision rule is no longer a v1.0→v2.0 delta, it should not appear in the delta table at all.

**Evidence / reference**:
  - Round-3 anti-rubber-stamp clause: §10.2 should reflect the revert with no decision-rule delta row.
  - DRAFT_v3 §10.2: the table still contains a struck-through `~~Decision rule~~` row.

**Proposed solution**: Delete the struck-through `Decision rule` row from §10.2. If historical explanation is desired, move one sentence below the table: “DRAFT_v2’s proposed decision-rule delta was withdrawn; v2.0 inherits v1.0’s plain `n_pass ≥ 4 of 7` rule per §2.1.”

**Calibrated assessment of the proposed solution**:

| Outcome | P | 95% CI | Confidence | Conviction (1–5) |
|---|---:|---:|---:|---:|
| Proposed solution is the right fix (no better alternative exists at this severity) | 82% | [66%, 92%] | 87% | 3.5/5 |
| Proposed solution causes downstream issue not yet identified | 4% | [1%, 12%] | 91% | 1.5/5 |
| Original draft was actually correct and this comment is wrong | 12% | [4%, 26%] | 89% | 2/5 |
| Alternative solution: retain row but add `delta_active=false` machine-readable marker | 14% | [5%, 30%] | 88% | 2/5 |

**Falsification criterion for this comment**: Show that the seal-time parser explicitly ignores Markdown-struck rows in §10.2 and that future artifact generation does not parse the row as an active v1.0→v2.0 delta. Even then, deletion remains cleaner but would fall to NIT.

## Cross-check §C-1 response (Monte Carlo necessity)

A Monte Carlo simulation under an empirical inter-criterion correlation matrix is **not necessary before seal**, provided §2.2’s analytical arithmetic is corrected. The analytical independent-marginal calculation is transparent, easily audited, and sufficient for a descriptive calibration paragraph. The current `8.9%` number is not acceptable because it is wrong under the stated assumptions. After replacing it with `2.7566% ≈ 2.8%`, the three caveats about non-independence and non-verdict status are adequate. Probability that Monte Carlo should be required before seal after the arithmetic fix: **18%**; 95% CI **[7%, 35%]**; confidence **86%**; conviction **2.5/5**.

If the Strategist wants empirical-correlation Monte Carlo later, it belongs in §15 as a descriptive sensitivity, not as a seal-blocking requirement and not as an input to the binary verdict.

## Out-of-scope notes

- Codex should still evaluate the code-facing items it owns: `arch.SkewStudent` API details, component-ID parsing, `b_sb` block-length column, verdict-schema types, cross-platform seal helpers, and acceptance-test implementation.
- I did not re-review component-ID correctness, `arch` API correctness, or JSON schema type validity beyond the methodology implications explicitly requested for Round 3.
- If Codex owns a parser for §10.2, relay New-2 so it can either ignore struck-through rows or benefit from deleting the row entirely.

## Falsification criterion for this round-3 review

Evidence in the next 6 months that would convince me this Round-3 review was mis-calibrated:

1. A reproducible seal-time calculation using the exact DRAFT_v3 §2.2 marginal vector returns `P(n_pass ≥ 4) ≈ 8.9%` rather than `2.7566%`.
2. The final sealed pre-reg changes the marginal vector or labels §2.2 as an empirical-correlation Monte Carlo calibration, making my independent-marginal arithmetic objection no longer applicable.
3. A subsequent reviewer or Codex finds a BLOCKER in the same narrow Round-3 scope that I marked VERIFY-PASS, especially the bootstrap immutability, B-1.5 provenance invariant, Stambaugh boundary, or `train_cutoff_inclusive` schema alignment.
4. The sealed verdict implementation treats `n_pass_predictive` as a veto gate despite §2.1 and §12 saying the rule is plain `n_pass ≥ 4 of 7`.
