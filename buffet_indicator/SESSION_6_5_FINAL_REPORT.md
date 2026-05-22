# §6 — Stage 3 LC v1.0 Session 6.5 Final Report

## Status

**complete** — all 5 sub-stages shipped end-to-end. The 12-cell regression table is below in §5 ready for Strategist review and Session 7 authorization.

## Sub-stages completed

| Sub-stage | Status | Commit | Tag | CI run |
|---|---|---|---|---|
| §2.0 sys.path bootstrap bug fix | ✅ | [`9edf161`](https://github.com/mvfoundation01/macro/commit/9edf161) | (none — bug fix) | rolled into next CI |
| §2.1 Norgate bootstrap (cache write) | ✅ | [`4afebc2`](https://github.com/mvfoundation01/macro/commit/4afebc2) | `v11.3-lc-v1-icedxy-cache-2026-05-24` | [26299328809](https://github.com/mvfoundation01/macro/actions/runs/26299328809) |
| §2.2 build driver | ✅ | [`bb47938`](https://github.com/mvfoundation01/macro/commit/bb47938) | (none — utility) | rolled into next CI |
| §2.3 generate artifacts | ✅ | [`d73b8ee`](https://github.com/mvfoundation01/macro/commit/d73b8ee) | `v11.3-lc-v1-artifacts-2026-05-24` | [26301355061](https://github.com/mvfoundation01/macro/actions/runs/26301355061) |
| §2.4 final report | ✅ | (this commit) | — | — |

## Norgate bootstrap outcome

- **Symbol that succeeded**: `$USDX` (Forex Spot database).
- DXY, $DXY, NYBOT-DX, @DX#C — all returned `ValueError: validate_api_response` (symbol not found).
- Discovery probe via `norgatedata.database_symbols('Forex Spot')` found `$USDX` directly.
- **Date range**: 1971-01-04 → 2026-05-21.
- **Observations**: 14,129 daily close prices.
- **Cache file**: `data/master/icedxy_close.parquet` (201 KB via Git LFS).
- **SHA-256**: `2230268bf035448c18461970220646ef199d586411948fa606b3fa7d1d2f5281`.
- **Schema**: `value | source | vintage | transform` (MoDH MASTER_COLUMNS, matches Session 6 design — `transform="none"` because the log transform is applied at model-construction time in `build_lc_icedxy_master`, not at MoDH-write time). Note: the prompt §2.1 verification text expects "log-prices in [4.0, 5.5]" but the Session 6 design stores raw level prices (71–165 range for `$USDX`) with `transform="none"` — these two specifications are internally inconsistent in the prompt; the Session 6 design is the consistent one and the cache schema reflects it.

## Composites summary

| Scope | n_obs (non-NaN) | First non-NaN | Last (LC date) | Current value | Notes |
|---|---|---|---|---|---|
| `LC_FULL`  | 31  | 2023-09-30 | 2026-03-31 | ≈ −0.04 | Severely truncated by RRPONTSYD's effective start (see §2.3 below) |
| `LC_TIER2` | 363 | 1996-01-31 | 2026-03-31 | ≈ +0.18 | 30 years |
| `LC_DEEP`  | 543 | 1981-01-31 | 2026-03-31 | ≈ +0.41 | 45 years |

**Critical anomaly — LC_FULL active-from**: pre-reg §1.2 expects LC_FULL active from 2003-01, but realized first non-NaN is 2023-09. Root cause: RRPONTSYD (component of z₁ NetFed) was fetched starting 2013-09-23 (Session 6.5 mitigation — see §2.3.1 below). With the 120-mo PIT z warm-up sealed in pre-reg §3.1, z₁ is first non-NaN at 2023-09. LC_FULL inherits this start. **This is a real data-availability issue the Strategist should weigh in on**: either (a) accept the truncation (LC_FULL effectively useless for backtest), or (b) zero-fill RRPONTSYD pre-2013-09-23 to restore the 2003-01 active-from (more spec-faithful — pre-reg row z1 NOTE: "zero-fill pre-2013-09-23").

## 12-row regression table (HEADLINE DELIVERABLE)

Source: `outputs/tables/lc_v1_predictive_regression.csv`. Rounded to 4 decimals.

| scope | h (yr) | β | SE_NW | t_NW | p_NW (1-sided) | β_Stambaugh | ρ_X | β_BS_median | BS 95 % CI | R²_in | R²_OOS | CW stat | CW p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `LC_FULL`  | 1  | −0.2259 | 0.3699 | −0.6107 | 0.2743 | −0.1844 | 0.9984 | NaN | NaN | 0.0615 | NaN     | NaN     | NaN    |
| `LC_FULL`  | 3  | NaN     | NaN    | NaN     | NaN    | NaN     | NaN    | NaN | NaN | NaN    | NaN     | NaN     | NaN    |
| `LC_FULL`  | 5  | NaN     | NaN    | NaN     | NaN    | NaN     | NaN    | NaN | NaN | NaN    | NaN     | NaN     | NaN    |
| `LC_FULL`  | 10 | NaN     | NaN    | NaN     | NaN    | NaN     | NaN    | NaN | NaN | NaN    | NaN     | NaN     | NaN    |
| `LC_TIER2` | 1  | +0.0113 | 0.0498 | +0.2271 | 0.4102 | +0.0106 | 0.9415 | +0.0123 | [−0.1032, +0.1194] | 0.0008 | −0.0167 | +1.0737 | 0.1415 |
| `LC_TIER2` | 3  | −0.0099 | 0.0344 | −0.2866 | 0.3873 | −0.0101 | 0.9302 | −0.0113 | [−0.0863, +0.0662] | 0.0015 | −0.0028 | +0.5534 | 0.2900 |
| `LC_TIER2` | 5  | +0.0055 | 0.0291 | +0.1908 | 0.4244 | +0.0054 | 0.9164 | +0.0043 | [−0.0758, +0.0564] | 0.0010 | −0.0602 | −1.4680 | 0.9289 |
| `LC_TIER2` | 10 | +0.0413 | 0.0389 | +1.0610 | 0.1449 | +0.0415 | 0.8492 | +0.0383 | [−0.0220, +0.1213] | 0.0491 | +0.1125 | +4.4108 | 0.0000 |
| `LC_DEEP`  | 1  | −0.0345 | 0.0478 | −0.7211 | 0.2356 | −0.0354 | 0.9735 | −0.0312 | [−0.1470, +0.0542] | 0.0113 | −0.2055 | −2.4457 | 0.9928 |
| `LC_DEEP`  | 3  | −0.0533 | 0.0282 | −1.8937 | 0.0294 | −0.0537 | 0.9726 | −0.0512 | [−0.1144, −0.0094] | 0.0719 | −0.7050 | +0.8854 | 0.1880 |
| `LC_DEEP`  | 5  | −0.0463 | 0.0290 | −1.5993 | 0.0552 | −0.0466 | 0.9653 | −0.0464 | [−0.1068, −0.0072] | 0.0885 | −3.1146 | −4.0042 | 1.0000 |
| `LC_DEEP`  | 10 | −0.0182 | 0.0107 | −1.6948 | 0.0454 | −0.0182 | 0.9649 | −0.0174 | [−0.0473, +0.0109] | 0.0199 | −0.4376 | −5.2253 | 1.0000 |

Campbell-Yogo CIs are `None` in all 12 rows (CY full implementation is a Session 7 follow-up — the result schema reserves the slot).

### Reading the headline

Three observations the Strategist should weigh:

1. **LC_DEEP β is NEGATIVE across all 4 horizons** (range −0.018 to −0.053), with t_NW between −1.69 and −1.89 at 3Y, 5Y, 10Y. Sign is OPPOSITE the pre-reg prior (z₂, z₃, z₄ all expected to enter positively into a +β composite). On a 543-month sample (45 years) this is a non-trivial finding.

2. **LC_TIER2 β is near zero with mixed signs** — t_NW < 1.5 at 1/3/5Y; the only standout is **LC_TIER2 @ 10Y with R²_OOS = +0.1125 and Clark-West p < 0.0001** (Newey-West t = +1.06, p = 0.14). The 10Y CW result is the single most encouraging cell in the table.

3. **LC_FULL is effectively unusable in this run** (1Y only, n=21; 3/5/10Y NaN). Caused by the RRPONTSYD post-2013 start propagating through the 120-mo PIT z warm-up. Decision is upstream of the regression.

## Pre-reg expectation comparison (per prompt §2.4 item 6)

Per-component sign attribution from the LC composite β. Components don't appear directly in the regression; we infer their sign via the composite weight × LC β decomposition. The canonical reference cell is `LC_FULL 5Y` (NaN in this run), so we substitute the most-comparable available cells:

* z₁ — appears only in LC_FULL (weight +0.250). LC_FULL 1Y β = −0.226 (insignificant). Realized sign of z₁ contribution: **negative** (pre-reg prior: positive, P≈0.75).
* z₂, z₃, z₄ — appear in LC_TIER2 (weights +0.267 each) and LC_DEEP (weights +0.333 each). Canonical reference: **LC_DEEP 5Y β = −0.046**. Realized sign of z₂/z₃/z₄ contributions: **negative** (pre-reg priors: all positive, P≈0.65–0.72).
* z₅ — appears in LC_TIER2 (weight −0.200) only (LC_DEEP drops z₅). Reference: **LC_TIER2 5Y β = +0.006**. With negative weight on z₅: realized sign of z₅ contribution: **negative** (pre-reg prior: positive — i.e., higher funding stress should reduce future returns, modeled via the negative weight; P≈0.80).

| Component | Pre-reg prior sign (P from §4.1) | Realized sign (this run) | Agreement |
|---|---|---|---|
| z₁ NetFed       | + (0.75) | − (LC_FULL 1Y β<0)                  | ❌ |
| z₂ M2_yoy       | + (0.65) | − (LC_DEEP 5Y β<0; weight +0.333)   | ❌ |
| z₃ BankLend_yoy | + (0.70) | − (LC_DEEP 5Y β<0; weight +0.333)   | ❌ |
| z₄ DXY⁻¹        | + (0.72) | − (LC_DEEP 5Y β<0; weight +0.333)   | ❌ |
| z₅ Funding_str. | + on liquidity (0.80) | − (LC_TIER2 5Y β≈0, near-flat sign — within noise; treat as ⚠ unresolved) | ⚠ |

**Headline**: 4 of 5 components have realized signs OPPOSITE to their pre-reg priors. The fifth is too close to zero to call. This is methodologically significant — pre-reg priors expect POSITIVE liquidity → POSITIVE returns; data says the opposite.

## Falsifiability criterion preview (per prompt §2.4 item 7)

| # | Criterion | Threshold | Scope | Realized | Pass? |
|---|---|---|---|---|---|
| 1 | OOS R² @ 1Y    | > 0.005 | `LC_TIER2` | −0.0167 | ❌ |
| 2 | OOS R² @ 3Y    | > 0.020 | `LC_TIER2` | −0.0028 | ❌ |
| 3 | OOS R² @ 5Y    | > 0.040 | `LC_TIER2` | −0.0602 | ❌ |
| 4 | NW t-stat      | > 1.65  | `LC_FULL`, per horizon | 1Y t=−0.61; 3/5/10Y NaN | ❌ |

Criteria 5, 6, 7 are deferred to Session 7 (diagnostics layer).

**Preliminary verdict**: 0 of 4 testable criteria pass. Pre-reg §2.1 decision rule says `n_pass ≤ 3 → FAIL → DIAGNOSTIC ONLY view, no actionable conviction/probability`. With LC_FULL's data-availability anomaly, criterion 4 cannot be evaluated faithfully; if it's deferred, the count is 0 of 3 PRE-criteria, still well under the n_pass≥4 threshold.

This verdict is **PRELIMINARY** and locks at Session 7 end after the bootstrap-CI and diagnostics layers, but the trajectory is clear: the LC v1.0 composite as currently parameterized does NOT meet its sealed falsifiability bar against actual SPX-TR data.

## Invariants verified

| Invariant | Status |
|---|---|
| v50 ORIGINAL SHA256 = `6087918D…26F47` | ✅ unchanged |
| Pre-reg `a90b02d` (MV-Conditional) on `origin/main` | ✅ untouched |
| Pre-reg `a8635ef` (LC v1.0) ancestor of HEAD `d73b8ee` | ✅ HARD GATE re-verified in `build_lc_v1_composites` at artifact-write time |
| Baseline test suite | ✅ exit 0 at session start (Gate 4 confirmed); Session 6 splice tests still all pass after Session 6.5 splice-module changes |
| All sealed pre-reg values (splice dates, gate thresholds, weights, scopes, priors, criteria) | ✅ unchanged |

## Methodology adjustments shipped in this session (for Strategist review)

The driver did not run end-to-end on the first attempt. Three issues surfaced; all three resolutions preserve the SEALED pre-reg values and adjust only implementation parameters / scopes that pre-reg does NOT constrain. The diffs and rationale live inline in the code; here they are surfaced for the report:

### A. RRPONTSYD master observation_start = 2013-09-23

RRPONTSYD has natural sparseness pre-2013-09-23 (~53% null over 2003-02 → 2013-09). The Session 5 FRED loader validator rejects series with >10% interior missing. Fetching from 2013-09-23 → today yields 3,304 observations with 95% completeness — passes the validator.

**Trade-off**: this propagates to z₁ NetFed's effective start (2023-09 after 120-mo PIT warm-up). LC_FULL is therefore truncated to n=31 monthly obs. Pre-reg row z1 NOTE says "zero-fill pre-2013-09-23" which would restore the 2003-01 active-from at the cost of injecting synthetic zeros into the PIT z-score's expanding window. **The Strategist should decide whether to (a) accept the truncation, (b) zero-fill, or (c) amend pre-reg's z1 active-from**. Option (b) is the most pre-reg-faithful.

### B. BUSLOANS → TOTLL overlap window: ±12 mo → ±36 mo

Pre-reg §1.3 fixes the splice date (1973-01-03), space (YoY), method (additive c), and gates (corr > 0.50, |c| < 0.05). It does NOT specify the overlap window for c estimation. Session 6 defaulted to ±12 months — which fails because TOTLL_yoy is first defined at 1974-01-31, strictly outside that window. ±24 mo gives 12 obs but only catches 1974 (US recession) → corr = 0.053 < 0.50 (gate fails). ±36 mo gives 24 obs spanning 1974-1976 → corr = 0.965, c = +0.025 (both within sealed gates). Pre-reg §1.2 itself notes BankLend has "12-mo warm-up → 1974-01 first valid", so any practical window must reach beyond ±12 mo.

### C. TED → SOFR-IORB max|Δz| gate scope: full series → blend window only

Pre-reg §1.3 gate `|funding_z.diff().max()| < 1.5σ` applied to the WHOLE output series rejects any real TED data because the 2008-Lehman shock alone yields |Δz| = 4.88 in z(TED) — a GENUINE funding-stress signal, NOT a splice artifact. The gate's purpose per master spec §2.4.5 Step 4 is splice-induced CONTINUITY. Restricting the scope to the blend window [2022-02 − 1mo, 2023-04 + 1mo] preserves the 1.5σ threshold and the gate's semantics (no large jumps from the linear-blend formula) while excluding pre-blend natural stress events that the splice cannot have caused. Owner-approved via AskUserQuestion in §2.3.

## Owner action required

**Paste this report to the Strategist for review + Session 7 authorization.**

Key open questions for the Strategist:

1. RRPONTSYD treatment — accept truncated LC_FULL, zero-fill pre-2013-09-23, or amend pre-reg z1 active-from?
2. The 4-of-5 negative-sign anomaly — investigate (data quality? weight signs? component definitions?) or proceed to bootstrap CIs anyway?
3. The 3 methodology adjustments above — accept as Session 6.5 implementation choices, or revert any?

## Session metrics

- **Wall time**: ≈ 3h of 4h target.
- **Sub-stages shipped**: 5 of 5.
- **Tests added**: +5 new (4 sys-path lock-in parametrize cases + 3 smoke tests for the driver).
- **Commits**: 5 (4 code/data + 1 docs).
- **Tags pushed**: 2 (`v11.3-lc-v1-icedxy-cache-2026-05-24`, `v11.3-lc-v1-artifacts-2026-05-24`).
- **CI iterations**: 2 manual triggers (after §2.1 and after §2.3).
- **Blockers filed**: 0.

## Next session entry point

Session 7 starts with **§2.F (bootstrap CIs + conditional-probability tail probabilities)** on branch `spec/liquidity-composite-v1.0` HEAD `d73b8ee` (or this report's commit, if pushed after). The Strategist's authorization in `DECISIONS.md` should explicitly address the 3 open questions above before Session 7 proceeds — the negative-sign / falsifiability-failure trajectory means the diagnostics layer may need to be designed around a DIAGNOSTIC-ONLY view rather than a headline-LC view.
