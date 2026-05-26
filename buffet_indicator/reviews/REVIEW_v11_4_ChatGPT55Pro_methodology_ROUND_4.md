# REVIEW v11.4 — ChatGPT 5.5 Pro — Methodology — Round 4 (NARROW)

## Headline

- §2.1 wording fix: **VERIFY-PASS**
- §2.2 arithmetic fix: **VERIFY-PASS**
- §10.2 row deletion: **VERIFY-PASS**
- Regression check: **CLEAN**
- NEW findings: **None**
- Recommendation: **SEAL_AS_DRAFTED**

## Calibrated meta-assessment

| Outcome | P | 95% CI | Confidence | Conviction |
|---|---:|---:|---:|---:|
| DRAFT_v4 is sealable as-drafted (zero further methodology changes) | 92% | [82%, 97%] | 85% | 4.5/5 |
| §2.2 arithmetic now correct (independent recomputation matches 0.0275660) | 99.5% | [98.5%, 99.9%] | 99% | 5/5 |
| Round-5 needed | 3% | [1%, 8%] | 93% | 4.5/5 |
| At sprint close, v2.0 PASS | 26% | [13%, 44%] | 55% | 3/5 |

## Verification of round-3 findings

### 1. §2.2 arithmetic correction — VERIFY-PASS

DRAFT_v4 now displays the required four Poisson-binomial tail terms:

```text
P(N = 4) = 0.0254580
P(N = 5) = 0.0020277
P(N = 6) = 0.0000791
P(N = 7) = 0.0000012
```

I independently recomputed the tail for `p = [0.10, 0.10, 0.05, 0.10, 0.60, 0.80, 0.05]` using exact rational arithmetic:

```text
P(N ≥ 4) = 13783 / 500000 = 0.0275660 = 2.7566% ≈ 2.8%
```

This matches DRAFT_v4's reported value exactly at the displayed precision. The accompanying interpretation is now methodologically acceptable: the calculation is framed as descriptive calibration under an independence approximation, not as a sealed invariant or formal familywise-error guarantee.

### 2. §2.1 predictive-subset wording — VERIFY-PASS

DRAFT_v4 replaces the logically loose phrase from DRAFT_v3 with:

```text
cases where n_pass = 4 depends on C5–C6 admissibility criteria and only two predictive criteria pass
```

This is logically tight. Since C5 and C6 are the only two non-predictive criteria, a four-pass outcome that depends on both admissibility checks necessarily contains exactly two predictive criterion passes. DRAFT_v4 also preserves the key methodological boundary: `n_pass_predictive` remains a transparency field and never gates, vetoes, or modifies the binary verdict.

### 3. §10.2 decision-rule row deletion — VERIFY-PASS

DRAFT_v4 deletes the struck-through `~~Decision rule~~` row entirely from the §10.2 delta table. The remaining explanatory note below the table is appropriate because it records the round history without making the decision rule a v1.0→v2.0 delta.

The §10.2 table now contains only true deltas: conditional forecast distribution, Criterion 4 wording, component sign priors, insufficient-sample gate, HAC-lag restatement, fixed bootstrap count, and verdict JSON state representation. No decision-rule row remains.

## Regression check

- **§2.2 calibration block consistency: CLEAN.** The marginal-probability table in §2.2 matches the §5 criterion thresholds: C1 `> 0.005`, C2 `> 0.020`, C3 `> 0.040`, C4 `|t_NW| > 1.65`, C5 Holm-Šidák-adjusted `α = 0.05`, C6 `max VIF < 5`, and C7 Bonferroni `α/20 = 0.0025`. I found no contradiction introduced by the explicit term breakdown.

- **§2.1 + §8.1 + §12 decision-rule coherence: CLEAN.** §2.1 states the operative rule as `PASS ⇔ n_pass ≥ 4 of 7`; §8.1 invariant #3 freezes the same binary rule; §12's `decision_rule_check.rule` is `"n_pass >= 4 of 7"`. The JSON schema still reports `n_pass_predictive`, but only as a transparency count, not as a decision gate.

- **Residual two-tier language: CLEAN.** Static scan found no operative two-tier rule and no `predictive_passed` field. The remaining `two-tier` occurrences are historical/explanatory only: §2.1 says the DRAFT_v2 rule is withdrawn, §8.1 says the invariant was corrected from DRAFT_v2's redundant rule, and §10.2's note explains why no decision-rule delta exists. This is consistent with the Round-4 request, which explicitly expected an explanatory note containing the withdrawn two-tier rule text.

- **§10.2 table integrity: CLEAN.** Removing the decision-rule row did not orphan any remaining delta. All retained rows correspond to methodology changes or representation changes that are still present elsewhere in DRAFT_v4.

## NEW findings

None.

## Out-of-scope notes

I did not re-review Codex-owned implementation details: §3.8 `arch.bootstrap.optimal_block_length` column behavior, §11.2 heading/test-tolerance updates, §12 enum rename, §9 item #11 cross-reference, or the §3.7/§3.8/§3.9 implementation mechanics. Codex should evaluate those mechanically in the parallel round-4 review.

## Falsification criterion for this round-4 review

This review should be revised if any of the following is observed before sealing or within the next six months:

1. An independent exact Poisson-binomial implementation under the stated marginal vector returns a value other than `0.0275660` for `P(N ≥ 4)`.
2. Seal-time static checks or schema tests reveal active verdict logic equivalent to `(n_pass ≥ 4) AND (n_pass_predictive ≥ 2)`.
3. A later pre-seal edit reintroduces a decision-rule row into §10.2 or makes `n_pass_predictive` verdict-bearing rather than descriptive.
4. Codex's parallel round-4 execution review finds an implementation issue that changes the methodology semantics reviewed here.

## Final recommendation

**SEAL_AS_DRAFTED** from the methodology-review perspective. DRAFT_v4 resolves the Round-3 methodology findings without introducing a new methodology regression.
