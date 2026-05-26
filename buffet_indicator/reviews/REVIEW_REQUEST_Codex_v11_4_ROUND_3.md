# REVIEW REQUEST — Codex — Round 3 (DRAFT_v3)

> **Target work product**: `MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER_DRAFT_v3.md` (attached)
> **Required context**: `DECISIONS_2026_05_24_v11_4_arbitration_ROUND_2.md` (attached), `REVIEW_v11_4_Codex_implementation_ROUND_2.md` (your prior round-2 review), `REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_2.md` (ChatGPT round-2 for context — ChatGPT is reviewing DRAFT_v3 in parallel)
> **Reviewer role**: IMPLEMENTATION-CORRECTNESS REVIEWER, round 3 of expected 3
> **Sister review**: ChatGPT round-3 is requested in parallel

---

## §1 — Strategist mea culpa (read first)

In the round-2 review-request package, the Strategist explicitly wrote *"Codex round-2 is NOT requested."* The owner sent to you anyway, and your round-2 review caught 2 NEW BLOCKERs that ChatGPT had no scope to find:

- **Round-2 New-1**: `arch.univariate.SkewStudent.loglikelihood` signature was wrong; `eta`/`lambda` parameter names were inverted.
- **Round-2 New-2**: Component IDs `z1..z5` were transposed across §1, §4.1, §5.3, §10.1.

The Strategist was wrong to recommend skipping you. **Forward policy: every major draft goes to BOTH reviewers, no exception.**

DRAFT_v3 incorporates both your BLOCKERs and all your other round-2 findings (7 VERIFY-FAILs, 5 NEW MAJORs, 2 NEW MINORs = 14 total accepted, plus ChatGPT's 1 VERIFY-FAIL + 1 NEW MAJOR + 3 NEW MINORs).

---

## §2 — Round-3 mission

Round-3 is **focused implementation-correctness re-verification**. Two goals:

1. **Did DRAFT_v3 correctly fix your 14 round-2 findings?** (especially the 2 BLOCKERs)
2. **Did DRAFT_v3's surgical patches introduce code-level regressions?** (the §3.7.2 rewrite, the §3.8 `b_sb` column fix, the §12 schema extension, the new acceptance tests)

You do NOT need to re-verify items you already VERIFY-PASS'd in round-2. Trust your prior judgment on §3.2.2 (vintage policy), §3.2.3 (RRPONTSYD), §8.2 (HARD GATE), §6.2.1 (idempotency), §13 (security).

Round-3 is expected to be the **final review**. The bar for `RE-DRAFT_REQUIRED` should be higher than round-2: only NEW BLOCKERs or clear `arch` API mismatches justify it. Boundary-table contradictions or test-coverage gaps should be MAJOR/MINOR.

---

## §3 — Severity convention (unchanged from rounds 1–2)

`BLOCKER` / `MAJOR` / `MINOR` / `NIT` per master spec §0.5.3.

**Round-3 calibration anchor**: expected outcome is 0 BLOCKER + 0–2 MAJORs + a few MINORs. If you find ≥1 BLOCKER, the most likely cause is a new code-level bug in the surgically-patched §3.7.2 / §3.8 / §12. Document precisely.

---

## §4 — MANDATORY output format

### §4.1 — For findings that VERIFY round-2 items

```
### Verify Codex Round-2 #<N or NEW-N> — <VERIFY-PASS | VERIFY-MODIFIED-OK | VERIFY-FAIL> — <one-line>

**Round-2 reference**: Comment #N (severity SEV) — "<title>"
**DRAFT_v3 location**: §<X.Y>
**Round-2 proposed fix**: <one-sentence summary>
**DRAFT_v3 actual fix**: <one-sentence summary>
**Verdict**:
  - VERIFY-PASS / VERIFY-MODIFIED-OK / VERIFY-FAIL (with new severity tag)

**Calibrated assessment** (only required if VERIFY-FAIL or VERIFY-MODIFIED-OK with concerns):
| Outcome | P | 95% CI | Confidence | Conviction |
|---|---|---|---|---|
| Redraft fix is incomplete | XX% | [LL%, UU%] | XX% | X/5 |
| Redraft introduces new failure mode | XX% | [LL%, UU%] | XX% | X/5 |
```

### §4.2 — For NEW findings introduced by DRAFT_v3

Full round-1 format (8 fields: section ref, issue, failure-mode, reference, proposed solution, calibrated assessment, test, falsification criterion).

---

## §5 — Required verification checklist (14 round-2 findings)

### §5.1 — Round-2 BLOCKERs (2)

| # | Round-2 finding | DRAFT_v3 location to verify |
|---|---|---|
| BLOCKER New-1 | `arch.SkewStudent` API mismatch | §3.7.1 parameter naming (`eta_tail`, `lambda_skew`); §3.7.2 pseudocode (`loglikelihood(parameters, resids, sigma2, individual=False)`); §12 verdict JSON fields (`skewt_eta_tail`, `skewt_lambda_skew`); §11.2 test `test_skewstudent_loglikelihood_signature_is_used_correctly` |
| BLOCKER New-2 | Component IDs transposed | §1 canonical component table; §4.1 prior table; §4.3 sensitivity table; §5.3 Criterion 7 cell enumeration; §10.1 transcription placeholders; §10.2 delta table; §12 `component_id_map` field; §8.1 invariant #12; §11.2 test `test_prereg_component_id_map_matches_v1_sealed_catalog` |

### §5.2 — Round-2 MAJORs (5)

| # | Round-2 finding | DRAFT_v3 location to verify |
|---|---|---|
| New-3 | `optimal_block_length` column name | §3.8 (changed to `["b_sb"]`); §11.2 test `test_optimal_block_length_uses_arch_b_sb_column` |
| New-4 | `n_bootstrap = 50,000` immutable vs 10K downsample | §3.8; §8.1 invariant #10 strengthened; §11.3 (no downsample option); §11.2 test `test_bootstrap_count_policy_is_not_runtime_dependent` |
| New-5 | Stambaugh exact-boundary contradiction | §3.9 row corrected (`ρ̂ = 0.85 → Stambaugh NOT applied`); §11.2 test `test_stambaugh_exact_boundary_not_applied` |
| New-6 | `UNSTABLE` cannot be schema-represented | §12 verdict enum extended; `retest_status` field added; §11.2 test `test_retest_unstable_verdict_is_schema_valid` |
| New-7 | No no-placeholder seal test | §11.2 test `test_sealed_prereg_contains_no_unresolved_placeholders` |

### §5.3 — Round-2 MINORs (2)

| # | Round-2 finding | DRAFT_v3 location to verify |
|---|---|---|
| New-8 | Sample-gate boundary tests missing | §11.2 test `test_sample_gate_boundaries_include_hac_and_neff` |
| New-9 | Unix-only seal commands on Windows workspace | DECISIONS round-2 §4 (PowerShell + Bash + Python helpers); §9 item #11; §11.2 test `test_seal_helpers_do_not_require_unix_only_tools` |

### §5.4 — Round-2 VERIFY-FAILs from your prior review (5 additional items not yet covered above)

| # | Round-2 finding | DRAFT_v3 status |
|---|---|---|
| Codex #1 (BLOCKER) | Skewed-t executable algorithm | Covered by BLOCKER New-1 fix; verify §3.7.2 pseudocode is now executable against arch==7.0.0 |
| Codex #3 (MAJOR) | Self-containment + component ID drift | Covered by BLOCKER New-2 fix; verify all placeholders use correct IDs |
| Codex #4 (MAJOR) | Stambaugh/CY boundary | Covered by New-5; verify §3.6 + §3.9 consistent |
| Codex #5 (MAJOR) | Bootstrap determinism + block length | Covered by New-3 + New-4; verify §3.8 pseudocode |
| Codex #7 (MAJOR) | Acceptance tests + performance budget | Covered by §11.2 (21 tests, expanded from 13); verify completeness |
| Codex #8 (MINOR) | Comparator semantics | §3.9 — verify boundary table self-consistent |
| Codex #9 (MINOR) | Verdict JSON distinct states + UNSTABLE | Covered by New-6 |

---

## §6 — Specific cross-checks the Strategist requests

### §6.1 — `arch==7.0.0` actual behavior verification

The Strategist cannot run `pip install arch==7.0.0` to verify. **You can.** Please confirm by execution (or by inspecting installed arch in your environment):

1. `arch.univariate.SkewStudent().loglikelihood(parameters=..., resids=..., sigma2=..., individual=False)` accepts these kwargs and returns a finite scalar for a small residual array.
2. `arch.bootstrap.optimal_block_length(x)` returns a DataFrame with `b_sb` and `b_cb` columns (not `stationary`/`circular` or other names).
3. `arch.univariate.SkewStudent` parameter order is `[eta, lambda]` where `eta` is tail and `lambda` is skew (not `[lambda, eta]` or `[nu, eta]`).

If any of the above is FALSE in arch==7.0.0, that is a **BLOCKER** that DRAFT_v3 missed. Surface immediately with exact arch version and error trace.

### §6.2 — §3.7.2 pseudocode unit-test simulation

Mentally execute the §3.7.2 pseudocode on the following synthetic input and predict the outcome:

```python
import numpy as np
rng = np.random.default_rng(42)
standardized_residuals = rng.standard_t(df=5, size=500)
# Apply §3.7.2 procedure...
```

Expected: `distribution_family = "skewed_t"`, `eta_tail_hat` close to 5 (since input is t with df=5), `lambda_skew_hat` close to 0 (since input is symmetric). Confirm or flag deviation.

### §6.3 — §11.3 50K immutability completeness

Verify that no clause in DRAFT_v3 contradicts the §8.1 invariant #10 "TRULY IMMUTABLE." Specifically search for any mention of `n_bootstrap` ≠ 50,000 in:
- §3.8 (should say 50,000 only)
- §11.3 (no downsample — runtime overrun → `BLOCKED_PERFORMANCE_BUDGET`)
- §12 verdict JSON (`n_bootstrap_used: 50000` only)
- §6.3 falsification (Brier comparison uses 50K)
- §15 appendix (literature-tilt sensitivity — must also use 50K or be labeled diagnostic-only)

If any reference still allows 10K for verdict-bearing quantities, that's a MAJOR regression.

### §6.4 — Component ID consistency sweep

Run a textual grep mentally on DRAFT_v3 for every occurrence of `z1`, `z2`, `z3`, `z4`, `z5` and verify each maps consistently to:
```
z1 → NetFed liquidity
z2 → M2 growth y/y
z3 → Bank lending growth y/y
z4 → Dollar-strength-inverse
z5 → Funding stress
```

Sections to check: §1, §4.1, §4.3, §5.3, §10.1, §10.2, §12 `component_id_map`. Any deviation is a BLOCKER.

---

## §7 — Out-of-scope (do NOT re-review)

- Methodology of the §2.1 decision-rule revert — ChatGPT's domain.
- §2.2 null calibration arithmetic — ChatGPT's domain.
- §4.3 wording fix — ChatGPT's domain.
- §6.3 falsification methodology — ChatGPT's domain.
- The decision to keep 10Y horizon in C4's search (vs explicit exclusion) — already arbitrated.
- The §1 DECISIONS RESEARCH_RECORD.md location — already arbitrated.
- TECH_DEBT YAML schema — already arbitrated.

If you find a code-level issue with any of the above, surface it as a NEW finding tagged with "ChatGPT should also evaluate."

---

## §8 — Specific anti-rubber-stamp clauses

- **Even if every checkbox passes, run one final smell-test**: would a developer implementing DRAFT_v3 produce a passing acceptance test suite on the first try? If you have ≥30% probability of "no" for any test, surface the specific risk.
- **Verify the new tests in §11.2 are EXECUTABLE as pseudocode**: function names exist in §11.1 signature list, expected inputs/outputs are plausible, no test has impossible assertions.
- **Verify the §12 verdict JSON schema is parseable**: every field has a defined type or enum, no contradictions between `verdict` and `retest_status` cardinality.
- **Verify the §13.2 redaction regex patterns don't false-positive** on the literal text of DRAFT_v3 itself (the prereg should not block its own commit).
- **Verify §0.2 invariants are independent** (no two invariants are tautologically the same).

---

## §9 — Expected output structure

Produce `REVIEW_v11_4_Codex_implementation_ROUND_3.md` with:

```markdown
# REVIEW v11.4 — Codex — Implementation Correctness — Round 3

## Headline summary
- VERIFY-PASS / VERIFY-MODIFIED-OK / VERIFY-FAIL counts
- NEW BLOCKER / MAJOR / MINOR counts
- Recommendation: SEAL_AS_DRAFTED | SEAL_WITH_MINOR_EDITS | RE-DRAFT_REQUIRED

## Calibrated meta-assessment
| Outcome | P | 95% CI | Confidence | Conviction |
|---|---|---|---|---|
| DRAFT_v3 sealable as-drafted | XX% | [LL%, UU%] | XX% | X/5 |
| If sealed, implementation will hit ≥1 immediate runtime error | XX% | [LL%, UU%] | XX% | X/5 |
| If sealed, implementation will produce ≥1 silent semantic mismatch | XX% | [LL%, UU%] | XX% | X/5 |
| `arch==7.0.0` actual API matches §3.7.2 pseudocode | XX% | [LL%, UU%] | XX% | X/5 |
| `arch==7.0.0` actual returns `b_sb` column (not `stationary`) | XX% | [LL%, UU%] | XX% | X/5 |
| Round-4 needed | XX% | [LL%, UU%] | XX% | X/5 |

## Verification of round-2 findings (14 items)
[blocks per §4.1]

## NEW findings introduced by DRAFT_v3 (if any)
[blocks per §4.2]

## Cross-check responses (per §6.1–§6.4)
[paragraph per cross-check with probability/confidence/conviction triple]
[Critical: if §6.1 arch API verification finds DRAFT_v3 pseudocode does not match arch==7.0.0 actual behavior, that is a BLOCKER and must be reported with exact API trace.]

## Test scaffold gaps (if §11.2 has gaps)
[bullet list]

## Out-of-scope notes (optional)
[any methodology-domain observations to relay to ChatGPT]

## Performance budget re-estimate
| Operation | Est. runtime | Confidence in estimate |
|---|---|---|
| Skewed-t ML fits | XX min | XX% |
| Bootstrap 50K | XX min | XX% |
| Total v11.4 sprint | XX min | XX% |

## Falsification criterion for this round-3 review
What evidence in next 6 months would convince you round-3 was mis-calibrated?
```

---

## §10 — Pacing

Round-3 is faster than rounds 1–2: ~1.5–3 hours expected. The verification checklist is concrete (14 items); the main analytical work is the §6.1 `arch==7.0.0` API verification.

If you can actually run a Python interpreter with `arch==7.0.0` installed, the §6.1 verification can be done programmatically in 10 minutes. If not, perform best-effort doc-based verification and flag remaining uncertainty.

---

## §11 — Final reminders

- The Strategist (Claude AI) retains final merge authority per master spec §0.5.4.
- Your round-3 review is archived as `reviews/REVIEW_v11_4_Codex_implementation_ROUND_3.md`.
- If both you and ChatGPT recommend SEAL (`SEAL_AS_DRAFTED` or `SEAL_WITH_MINOR_EDITS`), the Strategist proceeds to seal authorization.

Go.
