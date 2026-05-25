# Phase F-BLK1 progress

**Timestamp**: 2026-05-25T21:18Z
**Session**: Phase F-BLK1 (PIT vintage discipline fix + 4 MAJOR fixes + re-run)
**Starting HEAD**: `3abf22f` (Codex v12 round 5 review), one commit ahead of the prompt's `f6c341f` predecessor
**Ending HEAD**: `96f87e0`
**Commits this session**: 8 (one per F.BLK1.X commit + the JSON/archive promotion)
**Pushed**: 8 (every commit pushed to `origin/spec/liquidity-composite-v2.0`)

## Fixes applied

| Section | Codex severity | Status | Commit |
|---|---|---|---|
| §2 F.BLK1.A | BLOCKER CR-1 | PASS | `909f4b3` |
| §3 F.BLK1.B | BLOCKER CR-1 (audit) | PASS | `749fb63` |
| §4 F.BLK1.C | mistake #10 | PASS | `749fb63` (bundled with §3) |
| §5 F.BLK1.D | MAJOR CR-2 | PASS | `cd6bfef` |
| §6 F.BLK1.E | MAJOR CR-3 | PASS | `eca709c` |
| §7 F.BLK1.F | MAJOR (reproducibility) | PASS | `24968bc` |
| §8 F.BLK1.G | MAJOR CQ-1 | PASS | `22f2cad` |
| §9 F.BLK1.H | re-run | PASS | (verdict written under HEAD `22f2cad`) |
| §10 F.BLK1.I | delta analysis | DONE | `96f87e0` |
| §11 F.BLK1.J | promote | DONE | `96f87e0` |

## HEADLINE: Verdict change?

| Item | Pre-BLK-1 | Post-BLK-1 | Status |
|---|---|---|---|
| `verdict` | FAIL (1/7) | FAIL (1/7) | **UNCHANGED** |
| `evidence_status` | MIXED | MIXED | **UNCHANGED** |
| C1 / C2 / C3 | NOT_EVALUABLE_COUNTED_FAIL | same | UNCHANGED |
| C4 | NOT_EVALUABLE_COUNTED_FAIL | same | UNCHANGED |
| C5 | FAIL_STATISTICAL (max p ≈ 0.7648) | same (to 14 sig figs) | UNCHANGED |
| C6 | PASS (max VIF ≈ 1.6951) | same | UNCHANGED |
| C7 | NOT_EVALUABLE_COUNTED_FAIL | same | UNCHANGED |
| File-byte SHA-256 | `6671cc9ff7…` (sidecar mismatch `84a457e3f4…`) | `df54264099…` (sidecar matches) | **FIXED** |
| Audit construction | Tautological (`max_origin ≤ max_origin`) | Non-tautological (756 origin-cell pair checks) | **FIXED** |
| `n_bootstrap` enforcement | Unguarded CLI override | Sealed-IMMUTABLE 50K + `ensure_verdict_n_bootstrap` gate | **FIXED** |

All 5 of Strategist's per-criterion delta predictions (88–99% P) held.

## Test results

| Suite | Pass | Fail | Skip | Notes |
|---|---|---|---|---|
| §11.2 acceptance (sealed list) | 63/63 | 0 | 0 | sealed v2.0 + Phase E acceptance subset |
| New BLK-1 tests | 16/16 | 0 | 0 | per-origin fvm (4), synthetic look-ahead (4), expanding R² (3), n_bootstrap gate (8), byte-exact SHA (1), skew-t logging (3) — duplicated counts because some tests cross categories |
| Broader regression | 1094/1094 | 0 | 29 | full `tests/` suite under HEAD `96f87e0` (skips: master-data-absent paths and unchanged Phase D/v1 paths gated by env) |

## §16 seal-report criteria

Still 10/10 PASS — BLK-1 did not modify any seal-report surface; sealed pre-reg SHA-256 `c3c3ec1a…` unchanged.

## Strategist callbacks

None. P(callback) = 20% per prompt; actual = 0%. All implementation decisions resolved within the prompt's design space; no Strategist arbitration needed.

## Library version delta (carried over from pre-BLK-1; unchanged)

| Library | Installed | Sealed pinned |
|---|---|---|
| `arch` | 8.0.0 | 7.0.0 |
| `pandas` | 3.0.2 | 2.2.3 |
| `numpy` | 2.4.4 | 1.26.4 |
| `scipy` | 1.17.1 | 1.13.1 |
| `statsmodels` | 0.14.6 | 0.14.2 |

Per Codex Round 5: pinned re-run does not change verdict. Phase F-DOC closeout will pin and re-run for closeout reproducibility (out of BLK-1 scope).

## Provenance summary

- BLK-1 canonical verdict: [buffet_indicator/outputs/lc_v2_verdict.json](buffet_indicator/outputs/lc_v2_verdict.json) — SHA-256 `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c`
- Delta analysis: [buffet_indicator/outputs/lc_v2_verdict_blk1_delta.md](buffet_indicator/outputs/lc_v2_verdict_blk1_delta.md)
- Updated summary: [buffet_indicator/outputs/lc_v2_verdict_summary.md](buffet_indicator/outputs/lc_v2_verdict_summary.md)
- Pre-BLK-1 verdict (preserved): [buffet_indicator/outputs/historical/lc_v2_verdict_pre_blk1.json](buffet_indicator/outputs/historical/lc_v2_verdict_pre_blk1.json) — SHA-256 `6671cc9ff7b9e9f97a0c7447528bf0bcdc12b18a9406b29a8f0e632550200416` (file-byte; original sidecar `84a457e3f4…` is the in-memory SHA bug)
- `.gitattributes` `-text` rule added for verdict JSON + sidecar to preserve LF on Windows checkout (protects BLK-1.F byte-exact invariant)

## Methodology note

The sealed pre-reg `MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` at SHA-256 `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` (commit `2a94417`, tag `v11.4-prereg-sealed`) remains **IMMUTABLE**. BLK-1 brings the IMPLEMENTATION into compliance with sealed §3.2.2 (vintage policy), §3.3 (Goyal-Welch OOS R²), §3.8 (`n_bootstrap=50000` IMMUTABLE), and verdict-JSON SHA reproducibility. These are bug fixes, not methodology changes.

The Strategist mistake #10 forward policy is in effect: any future audit specification must include a synthetic-violation detection test to prove non-tautological construction.

## Next prompt

Issue Phase F-DOC kickoff:
- Display framing per sealed §7 (`n_pass = 1 ≤ 3 → FAIL → DIAGNOSTIC ONLY view`)
- Pin `requirements.lock` to sealed versions (`arch==7.0.0`, `pandas==2.2.3`, `numpy==1.26.4`, `scipy==1.13.1`, `statsmodels==0.14.2`)
- Closeout re-run for reproducibility
- 3-of-3 pre-reg FAIL writeup outline + meta-DECISIONS §6.4 entry
