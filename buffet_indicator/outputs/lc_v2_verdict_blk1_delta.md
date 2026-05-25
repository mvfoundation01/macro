# Phase F-BLK1 verdict delta analysis

**Timestamp**: 2026-05-25T21:00Z
**BLK-1 HEAD commit**: `22f2cad`
**Pre-BLK-1 baseline commit**: `f6c341f` (verdict authored from `f3659a3`; Codex review `3abf22f`)
**Sealed pre-reg**: UNCHANGED at SHA-256 `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` (immutable)

---

## Verdict outcome

| Item | Original | BLK-1 fixed | Δ |
|---|---|---|---|
| `verdict` | `FAIL` | `FAIL` | **UNCHANGED** |
| `n_pass_total` | `1/7` | `1/7` | **UNCHANGED** |
| `n_pass_predictive` | `0` | `0` | **UNCHANGED** |
| `evidence_status` | `MIXED` | `MIXED` | **UNCHANGED** |
| `retest_status` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | **UNCHANGED** |
| `data_cutoff` | `2026-03-31` | `2026-03-31` | **UNCHANGED** |
| file-byte SHA-256 | `6671cc9ff7…` | `df54264099…` | new under §7 byte-exact writer |
| sidecar SHA-256 | `84a457e3f4…` (mismatch) | `df54264099…` (matches file) | **fixed** |

The BLK-1 fixes confirm the v2.0 FAIL verdict under implementation that is now compliant with the sealed pre-reg.

---

## Per-criterion deltas

| # | Criterion | Original status (value) | BLK-1 status (value) | Δ value |
|---|---|---|---|---|
| C1 | OOS R² @ 1Y on LC_TIER2 > 0.005 | `NOT_EVALUABLE_COUNTED_FAIL` (—) | `NOT_EVALUABLE_COUNTED_FAIL` (—) | **UNCHANGED** (n_obs gate determinative; R² not surfaced) |
| C2 | OOS R² @ 3Y on LC_TIER2 > 0.020 | `NOT_EVALUABLE_COUNTED_FAIL` (—) | `NOT_EVALUABLE_COUNTED_FAIL` (—) | **UNCHANGED** |
| C3 | OOS R² @ 5Y on LC_TIER2 > 0.040 | `NOT_EVALUABLE_COUNTED_FAIL` (—) | `NOT_EVALUABLE_COUNTED_FAIL` (—) | **UNCHANGED** |
| C4 | LC_FULL \|t_NW\| > 1.65 any horizon | `NOT_EVALUABLE_COUNTED_FAIL` (—) | `NOT_EVALUABLE_COUNTED_FAIL` (—) | **UNCHANGED** |
| C5 | ADF rejects all 5 (Holm-Šidák α=0.05) | `FAIL_STATISTICAL` (max p ≈ 0.7648) | `FAIL_STATISTICAL` (max p ≈ 0.7648) | **UNCHANGED** (identical to 14 sig figs) |
| C6 | max VIF < 5.0 | `PASS` (1.6951) | `PASS` (1.6951) | **UNCHANGED** (identical) |
| C7 | Bonferroni any p < 0.0025 | `NOT_EVALUABLE_COUNTED_FAIL` (—) | `NOT_EVALUABLE_COUNTED_FAIL` (—) | **UNCHANGED** |

Strategist's per-criterion predictions (§10.2 of prompt) **all held**:

| Prediction | P(stated) | Held? |
|---|---|---|
| Verdict outcome UNCHANGED (FAIL) | 92% | ✓ |
| n_pass_total UNCHANGED (1/7) | 90% | ✓ |
| C1–C4 status UNCHANGED (NOT_EVALUABLE) | 88% | ✓ |
| C5 status UNCHANGED (FAIL_STATISTICAL) | 95% | ✓ |
| C6 status UNCHANGED (PASS) | 99% | ✓ |
| C7 status UNCHANGED (NOT_EVALUABLE) | 92% | ✓ |

---

## Per-cell deltas (criteria-touched cells only)

The 12-cell panel is preserved by BLK-1.A. Below shows the cells surfaced via C1–C4 (LC_TIER2 1Y/3Y/5Y for C1/C2/C3; LC_FULL 1Y/3Y/5Y/10Y for C4). LC_DEEP horizons exist in the panel but are not surfaced by C1–C4. C5/C6/C7 cells are per-component, not per (scope, horizon).

| Cell | gate_status (orig→new) | n_obs_oos | feature_vintage_max | β_OLS (orig→new) | t_NW (orig→new) | oos_r2 (orig→new) | clark_west (orig→new) |
|---|---|---|---|---|---|---|---|
| LC_FULL × 1Y | `not_evaluable`→same | 37 | `2025-05-31` | `0.0846…`→same | `0.8259…`→same | `-0.147` → `-0.051` | `0.154` → `0.815` |
| LC_FULL × 3Y | `not_evaluable`→same | 13 | `2023-05-31` | `0.0832…`→same | `1.7761…`→same | `-3.256` → `null` | `-5.297` → `null` |
| LC_FULL × 5Y | `not_evaluable`→same | 4 | `2021-05-31` | `null`→same | `null`→same | `null`→same | `null`→same |
| LC_FULL × 10Y | `not_evaluable`→same | 0 | `2016-05-31` | `null`→same | `null`→same | `null`→same | `null`→same |
| LC_TIER2 × 1Y | `not_evaluable`→same | 37 | `2025-05-31` | `-0.0283…`→same | `-0.290…`→same | `-0.053` → `+0.035` | `-0.674` → `+1.063` |
| LC_TIER2 × 3Y | `not_evaluable`→same | 13 | `2023-05-31` | `0.0569…`→same | `1.1508…`→same | `-1.969` → `null` | `-4.621` → `null` |
| LC_TIER2 × 5Y | `not_evaluable`→same | 4 | `2021-05-31` | `null`→same | `null`→same | `null`→same | `null`→same |

**Interpretation of `oos_r2` / `clark_west` changes**:
- β_OLS, t_NW, p_NW, n_obs_*, feature_vintage_max, gate_status are **IDENTICAL** — the panel + regression fit + HAC + Stambaugh / CY are deterministic and unchanged.
- `oos_r2` and `clark_west` shift in **evaluable** cells because BLK-1.D replaces the fixed `mean(y_train)` benchmark with the expanding prevailing mean per sealed §3.3 + Goyal-Welch (2008). At short OOS lengths (3Y / 36-month: only 13 OOS rows) the prevailing-mean cutoff `y[s] : s + h ≤ s_oos` produces NaN at early OOS rows (no fully-realized y by then), so R² gates to `null` per the BLK-1.D spec.
- None of these cells **pass** the n_obs gate (`n_obs_oos ≥ 60` required at 1Y horizon; 13 / 4 at longer horizons). Verdict is unaffected — the criterion still counts as NOT_EVALUABLE_COUNTED_FAIL, identical to original.
- This is exactly the "doesn't affect current verdict; unsafe for v12" pattern Codex flagged as MAJOR CR-2.

---

## Audit deltas

| Item | Original | BLK-1 |
|---|---|---|
| Audit method | Tautological iteration (checked `pd.Timestamp(fvm)` parseability only; no inequality) | Per-(origin, cell) `fvm[t] <= t` assertion |
| `all_cells_pit_compliant` | `true` (tautological) | `true` (genuine; verified by synthetic-violation test) |
| `audit_status` | (absent) | `"PASS"` |
| `n_cells_audited` | (absent) | `12` (3 scopes × 4 horizons) |
| `n_origins_audited` | (absent) | `756` (sum of per-cell origin counts) |
| `n_violations` | (absent) | `0` |
| `pit_audit_construction` | (absent) | `"per_origin_non_tautological_F_BLK1_A"` |
| Synthetic-violation detection | (no test) | **PASS** — `test_pit_audit_catches_synthetic_look_ahead` plants a 2099-12-31 fvm; audit catches and reports the cell/origin pair |

---

## Library version delta (carried over from pre-BLK-1; out-of-scope for BLK-1)

| Library | Installed (BLK-1 run env) | Sealed pinned (§3.7.2 + §3.8) |
|---|---|---|
| `arch` | 8.0.0 | 7.0.0 |
| `pandas` | 3.0.2 | 2.2.3 |
| `numpy` | 2.4.4 | 1.26.4 |
| `scipy` | 1.17.1 | 1.13.1 |
| `statsmodels` | 0.14.6 | 0.14.2 |

Library environment off-pin — same as pre-BLK-1. Per Codex Round 5, a pinned
re-run produces the same verdict; the library delta is not material for the
outcome. Phase F closeout will pin `requirements.lock` and re-run for
closeout reproducibility (deferred per the existing summary's Next-step section).

---

## Fixes applied (summary)

| Fix | Codex finding | Description | Verdict-affecting? |
|---|---|---|---|
| §2 F.BLK1.A | BLOCKER CR-1 | Per-origin vintage discipline (`feature_vintage_max_at_origin`) | Audit-affecting only (no verdict change) |
| §3 F.BLK1.B | BLOCKER CR-1 | Non-tautological audit (`run_pit_audit_non_tautological`) | Audit-affecting only |
| §4 F.BLK1.C | Strategist mistake #10 | Synthetic look-ahead detection test | Test-only |
| §5 F.BLK1.D | MAJOR CR-2 | OOS R² Goyal-Welch expanding prevailing mean | Yes for evaluable cells (none currently pass n_obs gate) |
| §6 F.BLK1.E | MAJOR CR-3 | `n_bootstrap=50_000` immutable enforced; CLI flag removed | Architectural only |
| §7 F.BLK1.F | MAJOR (reproducibility) | Byte-exact SHA-256 (binary write + LF newlines + read-back verify) | Hashing-only |
| §8 F.BLK1.G | MAJOR CQ-1 | Skew-t exception logging (no broad silent catch) | Logging-only |

---

## Interpretation

The post-BLK-1 verdict **confirms the v2.0 FAIL outcome** (1/7 criteria pass) on a now-compliant implementation. All Strategist predictions for per-criterion stability held at the stated probabilities. The audit, previously a tautology, now genuinely iterates 756 (origin, cell) pairs across 12 cells and records `audit_status=PASS` because strict-shift PIT z-score in `pit_zscore` correctly enforces `fvm[t] <= t` per sealed §3.2.2 + Phase B+C arbitration §B.

The OOS R² and Clark-West shifts in the four evaluable-but-gated cells (LC_FULL × 1Y/3Y, LC_TIER2 × 1Y/3Y) reflect the expanding-prevailing-mean benchmark replacing the fixed mean; none affect the verdict because all four cells fail the `n_obs_oos ≥ max(60, 3 × HAC_lag)` gate. The change brings the implementation in line with sealed §3.3 Goyal-Welch (2008) specification and unblocks safe evaluable cells under v12.

`n_bootstrap` is now architecturally pinned to 50_000 in verdict-bearing paths; the CLI no longer exposes an override. The verdict JSON SHA is now byte-reproducible across OSes — `sha256sum lc_v2_verdict.json` matches the sidecar (and matches the writer's return value) on Windows for the first time.

---

## Conclusion

The v2.0 verdict can be claimed **implementation-clean post-BLK-1**. The pre-BLK-1 verdict (`outputs/historical/lc_v2_verdict_pre_blk1.json`) is preserved as an audit-trail artifact of the buggy implementation. The current canonical `outputs/lc_v2_verdict.json` is the verdict produced by the BLK-1-compliant implementation; SHA-256 `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c`.
