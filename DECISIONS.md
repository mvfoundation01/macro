# DECISIONS — Strategist Arbitration Log

This file is the canonical record of Strategist arbitrations per master spec §0.5.4. Each decision has a unique ID (e.g., `v11.4-D10`). **Drafts pending Owner approval are referenced but not appended until APPROVED status is set** — Strategist working drafts live in `prompt/052*/DECISIONS_*.md`; this canonical file holds the immutable approved record.

The sealed pre-registration `MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` (SHA-256 `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05`) is the authoritative methodology source. Arbitrations recorded here describe HOW that methodology was sealed, implemented, verified, and what remains.

---

## v11.4 Sprint Decisions

### v11.4-D1 through v11.4-D9 — Pre-registration drafting arbitrations (AUTHORITATIVE via sealed pre-reg)

These arbitrations occurred across four review rounds during the sealed pre-reg drafting phase (2026-05-24). Each arbitration is preserved in its working-drafts file in `prompt/052426/` and is authoritatively embedded in the sealed pre-reg itself:

- `prompt/052426/DECISIONS_2026_05_24_v11_4_arbitration.md` (Round 1 arbitrations)
- `prompt/052426/DECISIONS_2026_05_24_v11_4_arbitration_ROUND_2.md`
- `prompt/052426/DECISIONS_2026_05_24_v11_4_arbitration_ROUND_3.md`
- `prompt/052426/DECISIONS_2026_05_24_v11_4_arbitration_ROUND_4.md`
- Sealed pre-reg: `buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` (SHA-256 `c3c3ec1a…`; tag `v11.4-prereg-sealed`; commit `2a94417`)

These decisions are AUTHORITATIVE as embedded in the sealed pre-reg. Any conflict between the working-drafts files and the sealed pre-reg is resolved in favor of the sealed pre-reg.

---

### v11.4-D10 — v12 path arbitration (APPROVED 2026-05-25)

> **Decision ID**: v11.4-D10 — v12 path arbitration
> **Date**: 2026-05-25
> **Authority chain**: Owner decision → Strategist arbitration → Reviewer inputs (ChatGPT 5.5 Pro + Codex) → Owner approval
> **Status**: APPROVED — actionable artifacts drafted
> **Sealed pre-reg impact**: NONE (sealed at `c3c3ec1a…` remains immutable)
> **Verdict JSON impact**: post-BLK-1 re-run produced canonical verdict `df54264099…`; pre-BLK-1 archived in `outputs/historical/`

#### §1 — Decision context

**Triggering event** — v11.4 sprint produced sealed v2.0 verdict on 2026-05-25:
- Outcome: **FAIL** (1/7 criteria pass)
- evidence_status: MIXED
- Verdict JSON: `outputs/lc_v2_verdict.json`, sidecar SHA `84a457e3…` (pre-BLK-1; CRLF bug fixed in F-BLK1.F)
- Per-criterion: C1-C4 NOT_EVALUABLE_COUNTED_FAIL (data-window-short), C5 FAIL_STATISTICAL (z4 ADF p≈0.7648), C6 PASS (max VIF≈1.70), C7 NOT_EVALUABLE
- Sealed §6.4 trigger: 3-of-3 consecutive pre-reg FAILs (v11.2.0-stat, v11.3.0 LC v1.0, v11.4 LC v2.0)

**Owner's broader question** (paraphrased): "Should we additionally analyze liquidity speed metrics (M2 velocity, M3 YoY change, rate-of-change variables)? Should we discuss with ChatGPT 5.5 Pro and Codex about what we've done, are doing, and will do?"

**Strategist response**: drafted two review request files (`REVIEW_REQUEST_ChatGPT55Pro_v12_design.md`, `REVIEW_REQUEST_Codex_v12_design.md`). Owner submitted both in parallel.

#### §2 — Reviewer findings (summary)

**Codex Round 5 (implementation correctness)**:
- **BLOCKER CR-1**: Verdict-bearing panel did NOT enforce per-origin `load_master(vintage=t)`. Components loaded once from latest master data. Audit was tautological (`max_origin <= max_origin`).
- **MAJOR (4)**: OOS R² fixed-mean instead of Goyal-Welch expanding; `n_bootstrap=50000` policy unenforced; sidecar SHA ≠ file-byte SHA on Windows; broad `except Exception` around skew-t.
- **Empirical findings**: pinned re-run (arch==7.0.0 etc.) produced same verdict → library version delta not material. v12-A z4_rate ADF locally passes (p=0.0227); z1_rate marginal (p=0.0695). **Critical**: under current PIT z-score warmup architecture (n≥120 strict-shift), v12-A z1/z4 rate-of-change START ONE YEAR LATER than current v2.0 — the "longer effective history" claim is FALSE.

**ChatGPT 5.5 Pro (methodology)**:
- Bottom-line: pursue **v12-A′** ONLY as "last confirmatory salvage test." No v12-B/C/D/E. Publish 3-of-3 FAIL writeup BEFORE v12 decision.
- BLOCKERs: PIT warmup contradiction (echoes Codex); pre-registration is NOT absolution against data-snooping; need alpha-spending ledger + White's Reality Check / Hansen SPA; post-2024 OOS too short for 1Y/3Y/5Y; do NOT add M2V or M3.
- v12-A′ structure: same 5 components, z1/z4 rate-of-change, TIGHTER thresholds, alpha-spending ledger, retire ≥24 months if FAIL.

#### §3 — Strategist mistake #10 confessed

In Phase E §7 spec, Strategist specified "Assert feature_vintage_max <= forecast_origin" but did NOT specify HOW `feature_vintage_max` is computed. Claude Code implemented it as the maximum aligned forecast-origin date, making the audit tautological. Codex caught it in Round 5.

**Forward policy**: every audit specification must henceforth include (1) the exact computation of the audit VALUE, (2) a synthetic test case the audit MUST FAIL on (non-tautological proof), (3) if audit can't detect a known violation → BLOCKER, redesign required. Incorporated into `PROMPT_CC_v11_4_phase_F_BLK1_fix.md` §4 and future Phase prompts.

**Total Strategist confessed mistakes across v11.4 sprint arc: 10.** Pattern: each mistake caught architecturally; 0 code damage in any case.

| # | Mistake | Caught by | Resolution |
|---|---|---|---|
| 1 | Recommended skipping Codex round-2 | Owner | Round 2 reinstated |
| 2 | Algebraically redundant two-tier decision rule | ChatGPT Round 2 | Simplified |
| 3 | Component IDs transposition | Codex Round 2 | Sealed §1 corrected |
| 4 | §2.2 arithmetic fabrication | ChatGPT Round 3 | Actual value used |
| 5 | Wrong `b_sb` column reference | Codex Round 3 empirical | "stationary" column |
| 6 | Check 0.4 filter mismatch | Phase 0 callback | Resolved pre-seal |
| 7 | V1 pre-reg path infix error | Phase 0 callback | Path corrected |
| 8 | WTREGEN typo from ROADMAP | Phase 3 callback | IDs cross-checked |
| 9 | Phase B+C prompt 4 wrong technical specs | Phase B callback | RESUME directive |
| 10 | PIT audit tautological spec | Codex Round 5 | BLK-1 fix + forward policy |

#### §4 — Owner decision (received 2026-05-25)

> **"BLK-1, Path A, SSRN"**

| Element | Decision |
|---|---|
| **BLK-1** | Proper fix + re-run: refactor implementation per Codex BLOCKER + 4 MAJOR findings; re-run v2.0 verdict under fix; delta-analyze against original |
| **Path A** | Conservative sequencing: write 3-of-3 FAIL writeup FIRST, then decide v12-A′ vs full retirement |
| **SSRN** | Publication venue: submit writeup to SSRN first (establish priority), polish for journal later |

#### §5 — Strategist arbitration synthesis

**Reviewer convergence**: both reviewers independently identified PIT warmup contradiction, v12-A unworkable in original form, M2V/M3 exclusion, 3-of-3 FAIL writeup INDEPENDENTLY of v12 decision. Convergence increases confidence in diagnoses.

**Sealed pre-reg integrity preserved**: BLK-1 fix does NOT amend the sealed pre-reg. BLK-1 brings IMPLEMENTATION into compliance with sealed methodology already specified (sealed §3.2.2 + §3 + §3.8 + reproducibility). Bug fixes, not methodology changes. Pre-BLK-1 verdict preserved in `outputs/historical/`.

**Path A justification**: writing 3-of-3 FAIL first forces clear articulation; reduces post-hoc selection risk; v12 decision informed by writeup-clarified understanding; ChatGPT 5.5 Pro explicit recommendation; Owner cognitive load reduction.

#### §6 — Pre-commitments

1. Sealed pre-reg `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` IMMUTABLE
2. No retroactive methodology change
3. Pre-BLK-1 verdict preserved in `outputs/historical/lc_v2_verdict_pre_blk1.json` as audit trail
4. Writeup before v12 decision
5. Reviewer attribution permanent
6. Honest disclosure of mistake #10 in writeup
7. Architecture-as-contribution presented alongside empirical null

#### §7 — Calibration (post-arbitration)

| Outcome | Pre-arbitration P | Post-arbitration P |
|---|---|---|
| v2.0 verdict robust under BLK-1 fix | 92% | 90% (Codex pinned re-run confirms) |
| v12-A workable as originally proposed | 35% | **5%** (REJECTED) |
| v12-A′ workable (refined) | n/a | 50% |
| Owner chooses Path A | 55% | confirmed |
| Writeup posted to SSRN | 60% | 70% |
| If v12-A′ pursued: PASSes | 30% | 25% |

#### §8 — Status of D10 commitments (as of 2026-05-26)

| Commitment | Phase / artifact | Status |
|---|---|---|
| BLK-1 fix implementation | Phase F-BLK1 (commits `909f4b3` → `96f87e0`) | **DONE**: 8 commits; outcome UNCHANGED FAIL (1/7); canonical verdict `df54264099…` |
| Sealed pre-reg integrity | continuously verified | **HOLDS**: SHA `c3c3ec1a…` immutable throughout sprint |
| Pre-BLK-1 verdict preserved | `outputs/historical/lc_v2_verdict_pre_blk1.json` (`6671cc9f…`) | **DONE** (Phase F-BLK1.J) |
| Environment pinning | Phase F-DOC (commits `623e09f` → `e87f213`) | **DONE**: 1092-line hashed `requirements.lock`; pinned closeout re-run normalized SHA equal to BLK-1 |
| Display framing | `outputs/lc_v2_display_fail.md` (Phase F-DOC.D) | **DONE**: DIAGNOSTIC ONLY view per sealed §7 |
| Engineering closeout report | `outputs/v11_4_sprint_engineering_closeout.md` (Phase F-DOC.E) | **DONE**; tag `v11.4-engineering-closeout` |
| Reproducibility appendix | Phase F-REPRO | **DONE** (this phase): manifest + reconstruction script + REPLICATION_INSTRUCTIONS + clean-state report; tag `v11.4-ssrn-reproducibility-ready` |
| §6.4 meta-DECISIONS authorship | `prompt/052526/DECISIONS_2026_05_26_meta_3of3_FAIL.md` | **DRAFT** (v11.4-D11 below); pending Owner approval |
| 3-of-3 FAIL SSRN writeup v0 | TBD | PENDING (post-Owner-approval of D11) |
| v12-A′ go/no-go decision | TBD | DEFERRED to after writeup completes (Path A discipline) |

---

### v11.4-D11 — §6.4 meta-DECISIONS on 3-of-3 FAIL (DRAFT pending Owner approval)

> **Decision ID**: v11.4-D11
> **Date**: 2026-05-26
> **Status**: STRATEGIST-AUTHORED DRAFT (pending Owner review per §14 of the entry)
> **Sealed pre-reg impact**: NONE (sealed `c3c3ec1a…` immutable; this entry is *required* by sealed §6.4 but does not modify the sealed methodology)
> **Predecessor**: v11.4-D10 (above)

The draft is at `prompt/052526/DECISIONS_2026_05_26_meta_3of3_FAIL.md`. Upon Owner approval (explicit or by 7-day no-objection default per §14 of the entry), this section will be replaced with the full content via a subsequent commit.

**Summary** (for navigation only — see draft for canonical content):

- Fulfills Strategist's pre-commitment in sealed §6.4
- Documents that 3-of-3 pre-reg FAIL (v11.2.0-stat → v11.3.0 LC v1.0 → v11.4 LC v2.0) is informative, not merely repeated null
- Enumerates falsified claims (F1–F6), unresolved claims (U1–U5), confirmed claims (C1–C5)
- Diagnoses two failure modes (Mode A data-window-vs-gate; Mode B z4 level-family non-stationarity)
- Identifies architectural finding: sealed-pre-reg + multi-round-review + callback-safety-net is feasible at individual/industry scale
- Evaluates three pivots: A (v12-A′ "last confirmatory salvage"), B (formal retirement), C (2029 re-evaluation of sealed v2.0, automatic)
- Strategist recommendation: Hybrid Pivot A + C with Pivot B off-ramp; conditional on Owner appetite
- 10 project-wide pre-commitments (D11 §9)
- Owner review checklist (D11 §14)
- 7 open questions for Owner (D11 §11) — defaults applied if no Owner response

**Current status**: Strategist working draft in `prompt/052526/DECISIONS_2026_05_26_meta_3of3_FAIL.md`. **Not yet canonical.** Promotion to this canonical record awaits explicit Owner approval or 7-day no-objection default.

---

## Future decisions

Reserved for v12-A′ arbitrations (if pursued), post-SSRN feedback decisions, the 2029-Q1 sealed v2.0 re-evaluation, and any later research-program decisions made by Owner + Strategist.

---

## Authority + provenance

| Role | Identity | Authority |
|---|---|---|
| Strategist | Claude AI (Anthropic) | Master spec §0.5.4 |
| Owner | Project owner per project authority | Decision authority |
| Sealed methodology | Sealed pre-reg at `c3c3ec1a…` (tag `v11.4-prereg-sealed`, commit `2a94417`) | Authoritative methodology source |
| Reviewers (Rounds 1–5) | ChatGPT 5.5 Pro (methodology lane) + Codex (empirical execution lane) | Contributory; attributed in writeup acknowledgments |
