# REVIEW REQUEST — Codex — Round 4 (DRAFT_v4) — NARROW VERIFICATION

> **Target work product**: `MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER_DRAFT_v4.md` (attached)
> **Required context**: `DECISIONS_2026_05_24_v11_4_arbitration_ROUND_3.md` (attached), `REVIEW_v11_4_Codex_implementation_ROUND_3.md` (your prior round-3 review)
> **Reviewer role**: IMPLEMENTATION-CORRECTNESS REVIEWER, NARROW FINAL VERIFICATION
> **Sister review**: ChatGPT round-4 narrow check is requested in parallel
> **Expected effort**: ~30 minutes (this is a final-check, not a full re-review)

---

## §1 — Round-4 mission (NARROW) + acknowledgment

Round-3 returned `RE-DRAFT_REQUIRED` from you with 1 NEW BLOCKER (`obl["b_sb"]` raises `KeyError` in actual `arch==7.0.0`) and 2 NEW MINORs (test count, skewed-t tolerance). **You executed `arch==7.0.0` in `D:\macro\.codex_tmp\arch700` and empirically verified column names — this overrode your own round-1+round-2 documentation-based advice.** That is the gold standard of reviewer behavior; the Strategist explicitly acknowledges your self-correction.

Round-4 exists because of the Strategist's accumulated 5 confessed factual mistakes and the policy "library API claims must be verified by execution, not doc-reading." **Round-4 scope is intentionally narrow: verify the 4 edits to your domain were applied correctly and re-confirm the `arch==7.0.0` ground truth holds.**

**You do NOT need to re-verify anything you already VERIFY-PASS'd in round-3**: §3.7.2 skewed-t API, component IDs, §11.3 immutable 50K, Stambaugh boundary, §12 UNSTABLE schema, no-placeholder seal test, cross-platform commands. Those are locked.

---

## §2 — Required verification checklist (4 items)

### §2.1 — Verify §3.8 reverts to `["stationary"]` AND embeds round-history note

**Round-3 finding**: DRAFT_v3 used `obl["b_sb"]` which raises `KeyError` against installed `arch==7.0.0`. Revert to `obl["stationary"]`.

**DRAFT_v4 location to verify**: §3.8 "Stationary bootstrap"

**Expected fix**:
- Code block uses `obl["stationary"].iloc[0]` (NOT `obl["b_sb"].iloc[0]`)
- Round-history note explains: DRAFT_v2 was correct → Codex round-1+2 incorrect advice → DRAFT_v3 propagated error → DRAFT_v4 corrects via Codex round-3 empirical execution
- Dependency caveat added: full `requirements.lock` required (pandas==2.2.3 + numpy==1.26.4 + scipy==1.13.1 + statsmodels==0.14.2 + arch==7.0.0), NOT just `pip install arch==7.0.0` (which pulls incompatible pandas==3.0.3)

**Verify by execution (cheapest if you have the env)**: re-run `obl = arch.bootstrap.optimal_block_length(np.arange(100.0))`. Confirm `obl["stationary"].iloc[0]` returns a finite scalar without error. Confirm `obl["b_sb"]` raises `KeyError`.

### §2.2 — Verify §11.2 acceptance test changes (3 items)

**DRAFT_v4 location to verify**: §11.2 "Required acceptance tests"

**Expected fixes**:

1. **Heading count**: should say "21 test IDs" (NOT "17 test IDs"). Verify table row count matches.
2. **`test_optimal_block_length_uses_arch_stationary_column`** (renamed from `_uses_arch_b_sb_column`): the test description should specify real arch import (NOT monkeypatch). Specifically check the test text says: real `arch.bootstrap.optimal_block_length(np.arange(100.0))` call, asserts `"stationary" in obl.columns AND "circular" in obl.columns`, asserts `choose_stationary_block_length(np.arange(100.0)) == int(np.ceil(obl["stationary"].iloc[0]))`.
3. **`test_skewed_t_known_distribution_and_fallback`** (now with explicit tolerance): the test description should specify `seed=42`, `size=500`, `standard_t(df=5)`, standardized, and assert `3.0 ≤ eta_tail_hat ≤ 8.0 AND |lambda_skew_hat| ≤ 0.15`. Verify the interval is consistent with your round-3 empirical fit (`eta_tail≈4.2542, lambda≈-0.0427`).

### §2.3 — Verify §8.1 invariant #13 and §12 enum rename

**DRAFT_v4 location to verify**: §8.1 invariant list, §12 verdict JSON schema

**Expected fixes**:
- §8.1 invariant #13 now reads `"stationary"` (NOT `"b_sb"`)
- §12 verdict JSON `block_length_source` enum reads `"stationary_optimal"` (NOT `"b_sb_optimal"`)

**Verify**: textual search for `b_sb` should return only the historical round-history note in §3.8 (documenting the journey). Any other occurrence is a regression.

### §2.4 — Verify §9 item #11 cross-reference fix

**Round-3 finding** (your seal-blocking patch checklist item): DRAFT_v3 §9 item #11 referenced "DECISIONS round-2 §3" but the cross-platform commands are in §4.

**DRAFT_v4 location to verify**: §9 item #11

**Expected fix**: reference now reads "DECISIONS round-2 §4" (NOT §3).

---

## §3 — Critical empirical re-verification (cheapest if you have env)

The Strategist requests you re-run the following minimal `arch==7.0.0` test in your environment to confirm DRAFT_v4 pseudocode is executable:

```python
import arch
import arch.bootstrap
from arch.univariate import SkewStudent
import numpy as np
import scipy.optimize

# Sanity: arch version
assert arch.__version__ == "7.0.0", f"Expected arch 7.0.0, got {arch.__version__}"

# (1) optimal_block_length column check
obl = arch.bootstrap.optimal_block_length(np.arange(100.0))
assert "stationary" in obl.columns
assert "circular" in obl.columns
print(f"obl columns: {list(obl.columns)}")
print(f"obl['stationary'].iloc[0]: {obl['stationary'].iloc[0]}")

# (2) SkewStudent loglikelihood signature check
rng = np.random.default_rng(42)
std_resid = rng.standard_t(df=5, size=500).astype("float64")
sigma2 = np.ones_like(std_resid)
dist = SkewStudent(seed=42)

result = scipy.optimize.minimize(
    fun=lambda params: -float(dist.loglikelihood(params, std_resid, sigma2, individual=False)),
    x0=np.array([8.0, 0.0]),
    method="L-BFGS-B",
    bounds=[(2.05, 200.0), (-0.95, 0.95)],
)
print(f"fit success: {result.success}")
print(f"eta_tail_hat: {result.x[0]}")
print(f"lambda_skew_hat: {result.x[1]}")
assert result.success
assert 3.0 <= result.x[0] <= 8.0, f"eta_tail out of tolerance: {result.x[0]}"
assert abs(result.x[1]) <= 0.15, f"lambda_skew out of tolerance: {result.x[1]}"
```

If all assertions pass, the §11.2 skewed-t and stationary-block-length tests are correctly specified against the actual library. Report runtime values for the record.

If any assertion fails, that's a NEW BLOCKER — report immediately with full traceback.

---

## §4 — Out-of-scope (do NOT re-review)

- §2.1 + §2.2 wording and arithmetic — ChatGPT's domain.
- §10.2 struck-through row deletion — ChatGPT's domain.
- All methodology framing in §4, §5, §6 — already VERIFY-PASS'd by you in earlier rounds.
- §3.7.2 skewed-t pseudocode structure itself (signature + bounds + fallback) — already VERIFY-PASS'd by you in round-3.

If you find an implementation issue with anything ChatGPT owns, flag with "ChatGPT should also evaluate."

---

## §5 — Expected output format

Short verification document. Suggested structure:

```markdown
# REVIEW v11.4 — Codex — Implementation Correctness — Round 4 (NARROW)

## Headline
- §3.8 stationary revert: VERIFY-PASS | VERIFY-FAIL
- §11.2 heading count (21): VERIFY-PASS | VERIFY-FAIL
- §11.2 test_optimal_block_length renamed: VERIFY-PASS | VERIFY-FAIL
- §11.2 skewed-t tolerance: VERIFY-PASS | VERIFY-FAIL
- §8.1 invariant #13 + §12 enum rename: VERIFY-PASS | VERIFY-FAIL
- §9 item #11 cross-reference fix: VERIFY-PASS | VERIFY-FAIL
- Empirical re-verification (§3 above): PASS | FAIL with traceback
- Recommendation: SEAL_AS_DRAFTED | SEAL_WITH_MINOR_EDITS | RE-DRAFT_REQUIRED

## Calibrated meta-assessment
| Outcome | P | 95% CI | Confidence | Conviction |
|---|---|---|---|---|
| DRAFT_v4 sealable as-drafted (zero further implementation changes) | XX% | [LL%, UU%] | XX% | X/5 |
| `arch==7.0.0` execution confirms DRAFT_v4 pseudocode runs without error | XX% | [LL%, UU%] | XX% | X/5 |
| Round-5 needed | XX% | [LL%, UU%] | XX% | X/5 |
| At sprint close, implementation hits ≥1 immediate runtime error | XX% | [LL%, UU%] | XX% | X/5 |

## Verification of round-3 findings (4 items)
[short blocks: 3-5 sentences each]

## Empirical re-verification results
[paste the actual Python execution output if you ran §3 — values of obl.columns, eta_tail_hat, lambda_skew_hat]

## NEW findings (if any)
[full block format only if you find new issues]

## Out-of-scope notes
[any cross-domain observations for ChatGPT]

## Falsification criterion for this round-4 review
[what evidence in next 6 months would change your conclusion]
```

---

## §6 — Pacing and policy

- **Expected effort**: ~30 minutes (15 minutes for text verification + 10 minutes for §3 empirical re-verification + 5 minutes for output). If round-4 takes you more than 90 minutes, flag as meta-feedback.
- **High bar for new findings**: round-4 is a final sanity check after your own round-3 self-correction. A new BLOCKER would be highly unusual — but if `arch==7.0.0` actual execution reveals further mismatches with DRAFT_v4 pseudocode, report immediately and the Strategist will produce DRAFT_v5.
- The Strategist (Claude AI) retains final merge authority per master spec §0.5.4. Your round-4 review is archived as `reviews/REVIEW_v11_4_Codex_implementation_ROUND_4.md`.

Go.
