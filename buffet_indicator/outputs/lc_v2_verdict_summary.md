# v2.0 Liquidity Composite verdict — v11.4 sprint

**Run timestamp**: 2026-05-25T18:05:13Z
**Verdict-run commit**: `f3659a3` (Phase E.2/E.3 complete; verdict-bearing run executed at this HEAD)
**Verdict-bearing commit (this output)**: `9759146` (Phase E.4/E.5/E.6 with verdict JSON + sidecar committed)
**Sealed pre-reg commit**: `2a94417` (tag `v11.4-prereg-sealed`)
**Sealed SHA-256**: `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05`
**Data cutoff**: 2026-03-31
**Decision rule**: `n_pass >= 4 of 7` (sealed §2.1)

## Headline

**Outcome**: **FAIL**

**n_pass_total**: **1 / 7**
**n_pass_predictive**: **0 / 5**
**evidence_status**: **MIXED** (one criterion FAIL_STATISTICAL, one PASS, five NOT_EVALUABLE_COUNTED_FAIL)

## Criteria results

| # | Criterion | Status | Value | Threshold | Operator |
|---|---|---|---|---|---|
| C1 | OOS R² @ 1Y on LC_TIER2 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.005 | `>` |
| C2 | OOS R² @ 3Y on LC_TIER2 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.020 | `>` |
| C3 | OOS R² @ 5Y on LC_TIER2 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.040 | `>` |
| C4 | LC_FULL \|t_NW\| > 1.65 (any horizon, Amendment 2 two-sided) | NOT_EVALUABLE_COUNTED_FAIL | — | 1.65 | `>` |
| C5 | ADF rejects null for all 5 components (Holm-Šidák α=0.05) | FAIL_STATISTICAL | max p ≈ 0.7648 | 0.05 (post-adjust) | `<` |
| C6 | max VIF across 5 components | **PASS** | ≈ 1.70 | 5.0 | `<` |
| C7 | any Bonferroni-significant cell at α/20 = 0.0025 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.0025 | `<` |

## Why most criteria are `NOT_EVALUABLE_COUNTED_FAIL`

Per sealed §3.4 (Amendment 4) the evaluability gate requires
`n_obs_oos >= max(60, 3 * HAC_lag)` AND `n_eff >= 30`. In the v2.0
post-Phase-B/C data environment:

- **z4 (DXY⁻¹)** is bottlenecked: the v2.0 master archive contains
  `DTWEXBGS` (2006-01+) but no `ICE_DXY` parquet, so z4 has no pre-2006
  back-extension. Combined with the sealed §10.1 120-month PIT z-score
  warm-up, z4 is first non-NaN at 2016-01. All 3 composites (LC_FULL,
  LC_TIER2, LC_DEEP) require z4, so the composite valid window is
  2016-01..2026-03 (~123 monthly obs).
- **OOS split** moved to 2021-01-31 (mid-range of the v2.0 valid window)
  per sealed §3.2.1: *"estimation expands from the longest jointly-available
  date"*. The v1.0 sealed split dates (2011-01/2013-01) pre-date the
  v2.0 composite valid start and so are not applicable.
- **n_obs_oos** with split at 2021-01 yields 64 oos rows for LC_DEEP × 1Y,
  49 for LC_FULL/LC_TIER2 × 1Y, 49–28 for 3Y, 4 for 5Y, 0 for 10Y. Of
  these, only the LC_DEEP × 1Y (64 ≥ 60) clears the n_obs_oos floor for
  short HAC_lag — but its `n_eff ≈ 14.9 < 30` fails the autocorrelation-
  adjusted floor.
- **z5** SOFR-IORB monthly history is also short (2021-07+); pre-blend
  z_TED honors the sealed 120-month PIT floor, post-blend z_spread
  uses a relaxed 24-month warm-up per Phase E methodology note.

Sealed §3.4's *"Disclosure"* paragraph anticipated this kind of structural
not_evaluable outcome at the 10Y horizon; Phase E observes it now extends
to most cells under v2.0's stricter OOS gate combined with the post-Phase-B
data availability.

## Why C5 is `FAIL_STATISTICAL`

ADF p-values per component (regression='c', autolag='AIC'):

| Component | ADF stat | p-value | Reject null at 5%? |
|---|---|---|---|
| z1 NetFed (level) | (per verdict JSON) | high | no |
| z2 M2 YoY | low | low | yes |
| z3 BankLend YoY | (varies) | (varies) | (varies) |
| z4 log(DXY) | ~ —1 | ~ 0.76 | **no** |
| z5 Funding-z | low | low | yes |

z4's near-unit-root level (logs of a broad-dollar index) drives the
Holm-Šidák-adjusted rejection failure for C5.

## Why C6 PASSES

Variance Inflation Factor across the 5 aligned z-scored components has
max ≈ 1.70 < 5.0. The components remain effectively orthogonal under v2.0's
z-score construction — consistent with their distinct economic content.

## Audit

- **PIT look-ahead audit**: **PASS** (0 violations). Strict-shift PIT z-score
  in `src.transform.pit_zscore.pit_zscore` (`strict_shift=True`,
  `min_window=120`) makes the cell-level `feature_vintage_max <= cell origin`
  invariant true by construction.
- **Sealed pre-reg integrity**: PASS (SHA-256 matches).
- **§16 seal-report criteria**: 10/10 PASS (no regression).
- **§11.2 acceptance tests**: 21/21 still PASS post-Phase-E.

## Implications

Per sealed §6.4 *"Meta-finding on 3-of-3 pre-reg FAIL"*:

> If v2.0 closes FAIL, that is the third consecutive pre-reg FAIL on this
> project (v11.2.0-stat, v11.3.0 LC v1.0, v11.4 LC v2.0). The Strategist
> commits to writing a meta-DECISIONS entry documenting that 3-of-3 FAIL
> is itself informative, enumerating remaining-falsified vs unresolved
> claims, and recommending pivots.

**Phase F** closeout will:
1. Display framing per sealed §7: `n_pass = 1 <= 3 → FAIL → DIAGNOSTIC ONLY view`.
2. Pin `requirements.lock` to sealed versions (`arch==7.0.0`, `pandas==2.2.3`,
   `numpy==1.26.4`, `scipy==1.13.1`, `statsmodels==0.14.2`) and re-run the
   verdict for closeout reproducibility.
3. Author the §6.4 meta-DECISIONS entry.
4. Compose the sprint closeout report.

## Provenance

- Verdict JSON: `buffet_indicator/outputs/lc_v2_verdict.json`
- Verdict JSON SHA-256: `buffet_indicator/outputs/lc_v2_verdict.json.sha256` →
  `84a457e3f47f5ad5e11f8fc2f86adf03ea25e30fead4a99c084e99ccfa6d4180`
- Phase E run directive: `prompt/052526/PROMPT_CC_v11_4_v2_sprint_PHASE_E.md`
- Phase D progress (full 21/21 acceptance tests + 14 of 15 functions):
  `outputs/v2_sprint_phase_progress_2026-05-25T16-11-42Z.md`
- Phase B+C arbitration: `prompt/052526/PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md`

## Library versions

- **Installed**: `arch=8.0.0`, `pandas=3.0.2`, `numpy=2.4.4`, `scipy=1.17.1`,
  `statsmodels=0.14.6`
- **Sealed §3.7.2 / §3.8 pinned**: `arch=7.0.0`, `pandas=2.2.3`, `numpy=1.26.4`,
  `scipy=1.13.1`, `statsmodels=0.14.2`
- **Delta**: Phase D methodology note 7 verified API compatibility for the
  two surfaces actually exercised (`SkewStudent.loglikelihood`,
  `optimal_block_length`). Phase F closeout will pin and re-run.

## Next step

Phase F: display framing (sealed §7) + `requirements.lock` pin + re-run +
sprint closeout report + §6.4 meta-DECISIONS entry.
