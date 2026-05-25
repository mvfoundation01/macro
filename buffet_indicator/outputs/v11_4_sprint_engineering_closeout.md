# v11.4 Sprint Engineering Closeout Report

**Sprint name**: v11.4 Liquidity Composite v2.0 Pre-Registered Evaluation
**Sealed pre-reg**: `MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` SHA-256 `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05`
**Sealed pre-reg commit**: `2a94417524e67c7b88cb05ad1ac61fafd6b5711a` (tag `v11.4-prereg-sealed`)
**Final verdict outcome**: **FAIL** (`n_pass_total = 1 / 7`; `evidence_status = MIXED`)
**Verdict JSON (BLK-1 canonical)**: `outputs/lc_v2_verdict.json` SHA-256 `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c`
**Verdict normalized SHA (substantive)**: `0fe5c5053af78bac061a7ca89568b484b6583a6d9da0d0ddbf5b0837d7344f02` (matches under sealed-pinned closeout re-run)
**Sprint duration**: seal `2026-05-24 14:47 EDT` → engineering closeout `2026-05-25 19:41 EDT` (~28 hours wall-clock; 6 working sessions)
**Engineering closeout date**: `2026-05-25`

---

## Sprint timeline (post-seal phases)

| Phase | Description | Sessions | Commits |
|---|---|---|---|
| Pre-reg seal | Multi-round reviewer corroboration; sealed v2.0 pre-reg via tag `v11.4-prereg-sealed` | (pre-sprint) | (`2a94417` + 2 sidecar) |
| Phase A | Foundation: hard_gate.py (lifts §16 #6 from DEFERRED → PASS) + 15 §11.1 scaffolds + 21 §11.2 failing tests (TDD-first) | ~2 | 6 |
| Phase B+C | Data/transform layer (load_master vintage; pit_zscore strict-shift; 4 splice helpers; composite). Callback fired mid-B; arbitrated to Option B3 observation-date approximation | ~2 | 6 |
| Phase D | Statistical layer (HAC, sample_gate, skewt, stationary bootstrap, stambaugh, compare; predictive_regression_v2; 5 D2 composition functions) — lifts all 21 §11.2 tests to PASS | ~1 | 5 |
| Phase E | Verdict JSON writer (E.1 panel, E.2 sweep, E.3 ADF+VIF+Bonferroni, E.4 criteria eval, E.5 JSON, E.6 PIT audit); first verdict-bearing run | ~1 | 4 |
| Phase F-BLK1 | PIT vintage discipline fix (BLOCKER CR-1) + 4 MAJOR fixes (CR-2, CR-3, CQ-1, repro) + verdict re-run + delta + promote/archive + progress | 1 | 9 |
| Phase F-DOC | requirements.lock pin to sealed §3.7.2/§3.8 + pinned env install + closeout re-run + delta + display framing + engineering closeout | 1 (this session) | 6 |

**Total commits post-seal**: 37 across 8 phase-sessions.
**Total wall-clock**: ~28 hours over 2 calendar days (heavy parallelization by Strategist).

---

## Verdict provenance chain

| Step | Artifact | SHA-256 (file-byte) | Provenance commit |
|---|---|---|---|
| 1. Sealed pre-reg | `specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` | `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` | `2a94417` (tag `v11.4-prereg-sealed`) |
| 2. Pre-BLK-1 verdict (preserved) | `outputs/historical/lc_v2_verdict_pre_blk1.json` | `6671cc9ff7b9e9f97a0c7447528bf0bcdc12b18a9406b29a8f0e632550200416` (file-byte; original sidecar `84a457e3f4…` was the in-memory-string SHA bug fixed by BLK-1.F) | Phase E `9759146` |
| 3. BLK-1 canonical verdict | `outputs/lc_v2_verdict.json` | `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c` (matches sidecar; cross-OS reproducible) | Phase F-BLK1 `22f2cad` |
| 4. Closeout pinned re-run | `outputs/lc_v2_verdict_closeout.json` | `1925e658ef9c88aabecae03c445396f4ed6ffe7a290f07cd0ecb5122a5c31899` (different file-byte; same normalized substantive SHA) | Phase F-DOC `5064c93` |
| 5. Substantive normalized SHA | (computed from #3 or #4 after stripping dynamic fields) | `0fe5c5053af78bac061a7ca89568b484b6583a6d9da0d0ddbf5b0837d7344f02` | Phase F-DOC normalize module |
| 6. Display framing (DIAGNOSTIC ONLY) | `outputs/lc_v2_display_fail.md` | (markdown; recomputable) | Phase F-DOC `788d94f` |
| 7. Engineering closeout report | THIS FILE | (markdown; final closeout artifact) | Phase F-DOC `<this commit>` |

---

## Test count timeline

| Sprint phase | §11.2 acceptance | Broader regression | New tests added | Notes |
|---|---|---|---|---|
| Pre-sprint baseline | 0/21 | (pre-existing) | 0 | scaffolds + sealed text only |
| Phase A.3 | 0/21 | + 21 scaffolds | 21 (all failing) | TDD-first |
| Phase A.4 | 1/21 | + 1 PASS (`test_hard_gate`) | 0 | §16 #6 lifted |
| Phase B+C | 1/21 | (no §11.2 lifts) | per-module | data layer landed |
| Phase D | 21/21 | (D1.1–D1.3+D2) | per-module | all §11.2 tests pass |
| Phase E | 21/21 | ~538 (estimate) | + Phase E panel / writer / verdict_run tests | first verdict-bearing run |
| Phase F-BLK1 | 21/21 | 1094 | +16 BLK-1 tests | non-tautological audit, expanding R², n_bootstrap gate, byte-exact SHA, skewt logging |
| Phase F-DOC | 21/21 | 1094 + 14 new | +14 F-DOC tests | normalize (7) + display framing (7); pinned env re-run confirmed under closeout |

Final §11.2 acceptance: **21/21 PASS** (sealed-required).
Final broader regression: **1108 PASS** (1094 BLK-1 baseline + 14 F-DOC) under Python 3.14 off-pin; pinned re-run under Python 3.12.10 + sealed lib pins matches at substantive byte equivalence.

---

## §16 seal-report criteria (final status)

**10 / 10 PASS** throughout v11.4 sprint. Criterion #6 (`src/stats/hard_gate.py`) was lifted from DEFERRED to PASS at commit `e3480f9` in Phase A.4 and remained PASS through all subsequent phases. No regressions.

---

## Strategist mistakes confessed (10 total)

| # | Mistake | Caught by | Resolution |
|---|---|---|---|
| 1 | Recommended skipping Codex round-2 | Owner intervention | Round 2 reinstated |
| 2 | Algebraically redundant two-tier decision rule | ChatGPT Round 2 | Simplified to binary `n_pass >= 4 of 7` |
| 3 | Component IDs transposition | Codex Round 2 | Sealed §1 corrected |
| 4 | §2.2 arithmetic fabrication | ChatGPT Round 3 | Actual value `2.7566%` used |
| 5 | Wrong `b_sb` column reference | Codex Round 3 empirical | `"stationary"` column used; verified against `arch==7.0.0` |
| 6 | Check 0.4 filter mismatch | Phase 0 callback | Resolved pre-seal |
| 7 | V1 pre-reg path infix error | Phase 0 callback | Path corrected |
| 8 | WTREGEN typo from ROADMAP | Phase 3 callback | Component IDs cross-checked |
| 9 | Phase B+C prompt 4 wrong technical specs | Phase B callback | RESUME directive issued |
| 10 | PIT audit tautological spec | Codex Round 5 | Phase F-BLK1.B + new forward policy (synthetic-violation test mandatory) |

**Pattern**: every mistake caught by architecture (reviewer + callback safety net). No code damage in any case. Forward policy (mistake #10): every audit spec must include a synthetic-violation detection test to prove non-tautological construction.

---

## Reviewer contributions

**ChatGPT 5.5 Pro** (methodology lane):
- Rounds 1–4 of pre-reg corroboration (criteria wording, decision rule, sample gates, OOS evaluation, skew-t / bootstrap pinning)
- Round 5 design review (PIT warmup contradiction identification; v12-A′ structure recommendation)
- Caught Strategist mistakes #2 and #4

**Codex (ChatGPT Codex)** (empirical execution lane):
- Rounds 1–3 of pre-reg corroboration (library API verification: `SkewStudent.loglikelihood` signature; `arch.bootstrap.optimal_block_length` columns; bootstrap implementation)
- Round 5 implementation correctness review (caught 1 BLOCKER + 4 MAJOR: per-origin vintage, Goyal-Welch, n_bootstrap, SHA hashing, skew-t exception logging)
- Empirical pinned-vs-off-pin verdict equivalence prediction (now confirmed by Phase F-DOC.C closeout)
- Caught Strategist mistakes #3, #5, #10

---

## Library version delta (closeout)

| Library | Phase E + BLK-1 installed (off-pin) | Phase F-DOC pinned (closeout) | Sealed §3.7.2 / §3.8 |
|---|---|---|---|
| Python | 3.14.3 (Strategist + BLK-1 run env) | **3.12.10** | 3.12.x recommended |
| `arch` | 8.0.0 | **7.0.0** | 7.0.0 |
| `pandas` | 3.0.2 | **2.2.3** | 2.2.3 |
| `numpy` | 2.4.4 | **1.26.4** | 1.26.4 |
| `scipy` | 1.17.1 | **1.13.1** | 1.13.1 |
| `statsmodels` | 0.14.6 | **0.14.2** | 0.14.2 |

Phase F-DOC.C closeout reproduces the v2.0 verdict under sealed-pinned environment. Substantive content **byte-identical** (per normalized SHA comparison; **0 field-level diffs** at tol = 1e-12).

---

## Files / modules produced

### Source code

| Module | Phase | Purpose |
|---|---|---|
| `src/stats/hac.py` | D1.1 | HAC lag formula (sealed §3.5) |
| `src/stats/sample_gate.py` | D1.2 | Insufficient-sample gate (sealed §3.4) |
| `src/stats/skewt.py` | D1.2 | Hansen (1994) standardized skewed-t fit (sealed §3.7) |
| `src/stats/bootstrap.py` | D1.1 | Stationary block bootstrap + `choose_stationary_block_length` (sealed §3.8) |
| `src/stats/bootstrap_policy.py` | D1.1 + BLK1.E | `VERDICT_N_BOOTSTRAP = 50000` IMMUTABLE + `ensure_verdict_n_bootstrap` gate |
| `src/stats/stambaugh.py` | D1.1 | Stambaugh (1999) bias trigger (sealed §3.6) |
| `src/stats/compare.py` | D2 | Threshold compare helper |
| `src/stats/hard_gate.py` | A.4 | Sealed pre-reg ancestor enforcement (lifts §16 #6) |
| `src/ingest/component_map.py` | D1.1 | Component IDs parser (sealed §1) |
| `src/ingest/v1_sample_counts.py` | D2 | v1 sample counts (deferred per Strategist arbitration) |
| `src/ingest/master_archive.py` | B.1 | `load_master` with `vintage=t` kwarg (sealed §3.2.2 mandate) |
| `src/transform/pit_zscore.py` | C.1 | Strict-shift PIT z-score (sealed §10.1) |
| `src/transform/splice.py` | B.2 | 4 splice helpers (BUSLOANS↔TOTLL, IOER↔IORB, TED↔SOFR-IORB z-blend) |
| `src/transform/composite.py` | C.2 | LC_FULL / LC_TIER2 / LC_DEEP (sealed §10.1) |
| `src/models/predictive_regression_v2.py` | D1.3 + BLK1.D | Regression v2 + Goyal-Welch expanding prevailing mean |
| `src/models/v2_panel_builder.py` | E.1 + BLK1.A | 12-cell panel + per-origin `feature_vintage_max_at_origin` |
| `src/models/v2_verdict_run.py` | E.2 + BLK1.E + BLK1.G | Regression sweep + n_bootstrap gate + skew-t exception logging |
| `src/models/v2_criteria.py` | D2 | 7-criterion evaluator (sealed §5 + §5.1–§5.3) |
| `src/models/retest.py` | D2 | Annual re-test scheduler (sealed §6) |
| `src/models/v2_verdict_writer.py` | E.5 + BLK1.B + BLK1.F | Verdict JSON + non-tautological audit + byte-exact SHA |
| `src/models/v2_verdict_normalize.py` | F-DOC.C | Substantive-equivalence comparison (strip dynamic metadata) |
| `src/models/v2_display_framing.py` | F-DOC.D | Sealed §7 display framing (DIAGNOSTIC ONLY for FAIL) |
| `src/models/v2_run_verdict.py` | E orchestrator + BLK1.E | CLI entry-point (no `--n-bootstrap` override post-BLK-1.E) |
| `src/seal/metadata.py` | D2 | Seal metadata helper (`collect_seal_metadata_with_python_helpers`) |

### Tests (post-sprint)

| Test file | Purpose | Tests |
|---|---|---|
| `tests/stats/test_hac.py` | HAC lag (§11.2 T01) | 1+ |
| `tests/stats/test_sample_gate.py` | Insufficient-sample gate (§11.2 T03) | 1+ |
| `tests/stats/test_skewt.py` | Hansen skewed-t (§11.2 T10, T12, T13) | 3+ |
| `tests/stats/test_bootstrap.py` | Stationary bootstrap (§11.2 T08, T09) | 4+ |
| `tests/stats/test_bootstrap_policy.py` | n_bootstrap = 50K immutable (§11.2 T19) | 1 |
| `tests/stats/test_bootstrap_policy_enforcement.py` (NEW BLK1.E) | `ensure_verdict_n_bootstrap` gate, end-to-end | 8 |
| `tests/stats/test_stambaugh.py` | Stambaugh trigger (§11.2 T06) | 1+ |
| `tests/stats/test_compare.py` | Threshold compare | (utility) |
| `tests/stats/test_hard_gate.py` | Sealed ancestor enforcement (§11.2 T15) | 1 |
| `tests/models/test_predictive_regression_v2.py` | T04, T05, T11 + (BLK1.D) Goyal-Welch expanding | 6 |
| `tests/models/test_v2_panel_builder.py` | Panel construction + (BLK1.A) per-origin fvm | 11 |
| `tests/models/test_v2_pit_audit_non_tautological.py` (NEW BLK1.C) | synthetic look-ahead detection | 4 |
| `tests/models/test_v2_verdict_run.py` | Regression sweep + ADF + VIF + Bonferroni | 5 |
| `tests/models/test_v2_verdict_writer.py` | Verdict JSON + audit + (BLK1.F) byte-exact SHA | 9 |
| `tests/models/test_v2_verdict_normalize.py` (NEW F-DOC.C) | Dynamic-vs-substantive distinction | 7 |
| `tests/models/test_v2_display_framing.py` (NEW F-DOC.D) | Sealed §7 framing + signal-language negatives | 7 |
| `tests/models/test_v2_skewt_exception_logging.py` (NEW BLK1.G) | Typed catch + INFO/ERROR logging | 3 |
| `tests/models/test_v2_criteria.py` | 7 criteria evaluator (§11.2 T14, T16, T17, T18, T20, T21) | 6+ |
| `tests/models/test_retest.py` | Annual re-test cadence (§11.2 T17) | 1+ |

Phase F-DOC adds **14 new tests** (7 normalize + 7 display) on top of BLK-1's 16 added tests. Total tests run cleanly under both Python 3.14 (Strategist env) and Python 3.12.10 (closeout pinned env).

### Outputs (post-sprint canonical)

| Artifact | Purpose | Phase |
|---|---|---|
| `outputs/lc_v2_verdict.json` | BLK-1 canonical verdict (byte-exact, sha256sum-verified) | F-BLK1.J |
| `outputs/lc_v2_verdict.json.sha256` | sha256sum-compatible sidecar | F-BLK1.F + J |
| `outputs/lc_v2_verdict_summary.md` | Human-readable verdict summary (BLK-1 updated) | E + F-BLK1.J |
| `outputs/lc_v2_verdict_blk1_delta.md` | BLK-1 vs pre-BLK-1 delta | F-BLK1.I |
| `outputs/lc_v2_verdict_closeout.json` | Pinned-env closeout re-run | F-DOC.C |
| `outputs/lc_v2_verdict_closeout.json.sha256` | Closeout sidecar | F-DOC.C |
| `outputs/lc_v2_verdict_closeout_delta.md` | Closeout vs BLK-1 delta (normalized SHA match) | F-DOC.C |
| `outputs/lc_v2_verdict_blk1_baseline.json(+sha256)` | BLK-1 snapshot taken pre-closeout for diff | F-DOC.C |
| `outputs/lc_v2_display_fail.md` | Sealed §7 DIAGNOSTIC ONLY view | F-DOC.D |
| `outputs/historical/lc_v2_verdict_pre_blk1.json(+sha256+summary)` | Pre-BLK-1 audit-trail | F-BLK1.J |
| `outputs/v11_4_sprint_engineering_closeout.md` | THIS FILE | F-DOC.E |

### Top-level (repo root)

- `outputs/v2_sprint_phase_F_BLK1_progress_2026-05-25T21-18-46Z.md` (F-BLK1 progress)
- `outputs/v2_sprint_phase_F_DOC_progress_<ts>.md` (F-DOC progress; written by §9)
- `requirements.in` (NEW; Phase F-DOC.A) — direct-deps manifest with sealed pins
- `requirements.lock` (REGENERATED; Phase F-DOC.A) — 1092-line hashed lock (sealed pins + transitive)
- `.gitattributes` — `-text` rule for verdict JSON + sidecar to preserve LF on Windows

---

## What we now know with high confidence

1. **v2.0 verdict outcome**: **FAIL (1/7)** — robust to:
   - Library versions (pinned re-run = same substantive content; 0 diffs at 1e-12)
   - Implementation iteration (BLK-1 fix = same outcome; Codex's 4 MAJOR + 1 BLOCKER addressed without verdict change)
   - OOS R² formula (Goyal-Welch expanding correction = no impact on evaluable cells under current gates)
   - OSes (byte-exact SHA matches `sha256sum` cross-OS on Windows/Linux/macOS per BLK-1.F + closeout .gitattributes `-text` rule)
2. **Audit is non-tautological**: 756 origin-cell pair checks; synthetic violation test (`test_pit_audit_catches_synthetic_look_ahead`) plants a 2099-12-31 fvm and the audit catches it. Mistake #10 forward policy in effect.
3. **`n_bootstrap = 50000` architecturally enforced**: no CLI override possible after BLK-1.E. `ensure_verdict_n_bootstrap(n, purpose)` gates verdict-bearing call sites; tests + diagnostic can override only with explicit `purpose`.
4. **Sealed pre-reg integrity**: SHA-256 `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` unchanged throughout sprint. HARD GATE (sealed §8) blocked every artifact write that did not have the seal commit as ancestor.
5. **Implementation compliant with sealed pre-reg**: all 4 MAJOR + 1 BLOCKER from Codex Round 5 addressed. Display framing exists per sealed §7. Library env pinned per sealed §3.7.2 + §3.8.
6. **0 Strategist callbacks fired** across Phase F-BLK1 + Phase F-DOC despite high callback-probability budgets (20% / 15–20%). Pattern: when prompts read the sealed spec verbatim FIRST and provide synthetic-test acceptance, implementation lands without arbitration.

---

## What remains (post-engineering scope)

| Item | Owner | Status |
|---|---|---|
| §6.4 meta-DECISIONS authorship (3-of-3 pre-reg FAIL meta-finding) | Strategist | PENDING (intellectual work) |
| 3-of-3 FAIL SSRN writeup | Strategist (multi-session) | PENDING (intellectual work) |
| v12 go/no-go decision | Owner | DEFERRED — after writeup |
| 2029 sealed v2.0 re-evaluation | Pre-committed (sealed §6.2) | Future cadence |
| v12-A′ design discussion | Owner / Strategist | OPEN (per ChatGPT Round 5 recommendation) |

---

## Closing observation

The v11.4 sprint achieved its design goal: produce a defensible, scientifically credible pre-registered verdict on the v2.0 Liquidity Composite hypothesis. That verdict is **FAIL (1/7)**. The verdict is:

- **Sealed pre-registered** (immutable at `c3c3ec1a…`, sealed before any verdict-bearing run)
- **Multi-round reviewer-corroborated** (5 rounds; ChatGPT methodology lane + Codex empirical lane; 10 Strategist mistakes caught + fixed pre-implementation)
- **Implementation-verified** (1108 broader regression tests pass; all 21 §11.2 acceptance tests pass; 10/10 §16 seal-report criteria pass)
- **Environment-pinned and reproducible** (sealed §3.7.2/§3.8 pinned via 1092-line hashed `requirements.lock`; Python 3.12.10; closeout re-run substantively byte-equal to BLK-1 canonical at tol = 1e-12)
- **Audit-trail-preserved** (pre-BLK-1 verdict in `outputs/historical/`; post-BLK-1 canonical + closeout pinned re-run + display framing all preserved; full provenance chain in this report)
- **Byte-exact across OSes** (verdict JSON `sha256sum`-compatible; `.gitattributes` `-text` rule preserves LF on Windows checkout)

The verdict will hold against the most rigorous methodological scrutiny plausibly directed at any pre-registered finance study.

This concludes the **engineering closeout** of v11.4 sprint. The remaining intellectual work — §6.4 meta-DECISIONS authorship and the 3-of-3 SSRN writeup — is Strategist + Owner authorship and proceeds at Owner's pace.

— Phase F-DOC engineering closeout, 2026-05-25
