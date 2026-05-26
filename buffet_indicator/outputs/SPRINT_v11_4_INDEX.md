# v11.4 Sprint Navigation Index

This index lists all canonical artifacts produced during the v11.4 Liquidity Composite v2.0 sprint. It is the single entry-point for readers (reviewers, replicators, the Strategist's future self).

---

## Sealed pre-registration (IMMUTABLE)

- **File**: `buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md`
- **SHA-256**: `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05`
- **Sealed at commit**: `2a94417`
- **Tag**: `v11.4-prereg-sealed`

## Canonical verdict

- **File**: `buffet_indicator/outputs/lc_v2_verdict.json`
- **File-byte SHA-256**: `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c` (BLK-1 canonical; matches `sha256sum` cross-OS via `.gitattributes` `-text` rule)
- **Normalized SHA-256 (substantive)**: `0fe5c5053af78bac061a7ca89568b484b6583a6d9da0d0ddbf5b0837d7344f02` (matches pinned closeout re-run + clean-state clone re-run, 0 field diffs at 1e-12)
- **Outcome**: **FAIL (1 of 7)**; `evidence_status = MIXED`
- **Human-readable summary**: `buffet_indicator/outputs/lc_v2_verdict_summary.md`
- **Display framing per sealed §7**: `buffet_indicator/outputs/lc_v2_display_fail.md` (DIAGNOSTIC ONLY view; explicit "do not interpret as predictive signal" disclaimers)

## Historical (pre-BLK-1) verdict

- **File**: `buffet_indicator/outputs/historical/lc_v2_verdict_pre_blk1.json`
- **Status**: Archived audit-trail artifact (the buggy implementation pre-mistake-#10 fix)
- **File-byte SHA-256**: `6671cc9ff7b9e9f97a0c7447528bf0bcdc12b18a9406b29a8f0e632550200416`
- **Original sidecar SHA-256 (in-memory string)**: `84a457e3f4…` (the sidecar/file-byte mismatch was the bug fixed in Phase F-BLK1.F)
- **Companion summary**: `buffet_indicator/outputs/historical/lc_v2_verdict_summary_pre_blk1.md`

## Reproducibility appendix (Phase F-REPRO)

- `buffet_indicator/data_manifest.json` — master archive provenance (22 series; SHA-256 per cached file)
- `buffet_indicator/data_manifest.md` — human-readable companion (splice points, vintage narrative)
- `buffet_indicator/scripts/_build_data_manifest_v2.py` — generator (rebuild from `data/master/*.parquet`)
- `buffet_indicator/src/replication/reconstruct_master.py` — FRED re-fetch + SHA verification
- `buffet_indicator/tests/replication/test_reconstruct_master.py` — 8 unit tests (mocked)
- `buffet_indicator/outputs/replication/REPLICATION_INSTRUCTIONS.md` — third-party replication guide
- `buffet_indicator/outputs/replication/v11_4_clean_state_repro_report.md` — clean-state cross-check (normalized SHA match)
- `buffet_indicator/requirements.lock` — pinned + hash-verified dependencies (1092 lines)
- `buffet_indicator/requirements.in` — direct-deps manifest (sealed pins + project deps)

## Phase prompts (Strategist authority; untracked working area in `prompt/`)

| Prompt | Date | Purpose |
|---|---|---|
| `PROMPT_CC_v11_4_seal_and_kickoff.md` | 052426 | Pre-reg seal + Phase A kickoff |
| `PROMPT_CC_v11_4_v2_sprint_kickoff.md` | 052426 | Phase A (foundation; scaffolds + tests) |
| `PROMPT_CC_v11_4_v2_sprint_PHASE_B_C.md` | 052526 | Phase B+C (data / transform layer) |
| `PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md` | 052526 | Phase B+C callback arbitration (Option B3) |
| `PROMPT_CC_v11_4_v2_sprint_PHASE_D.md` | 052526 | Phase D (statistical layer) |
| `PROMPT_CC_v11_4_v2_sprint_PHASE_E.md` | 052526 | Phase E (verdict-bearing run) |
| `PROMPT_CC_v11_4_phase_F_BLK1_fix.md` | 052526 | Phase F-BLK1 (PIT discipline + 4 MAJOR fixes) |
| `PROMPT_CC_v11_4_phase_F_DOC.md` | 052526 | Phase F-DOC (environment pin + closeout) |
| `PROMPT_CC_v11_4_phase_F_REPRO.md` | 052526 | Phase F-REPRO (this prompt — SSRN reproducibility) |

## DECISIONS records

| Decision ID | Title | Status | Location |
|---|---|---|---|
| v11.4-D1 through v11.4-D9 | Pre-reg drafting arbitrations | AUTHORITATIVE (embedded in sealed pre-reg) | `prompt/052426/DECISIONS_2026_05_24_v11_4_arbitration*.md` (4 rounds) + sealed pre-reg itself |
| v11.4-D10 | v12 decision triple (BLK-1, Path A, SSRN) | APPROVED 2026-05-25 | `prompt/052526/DECISIONS_2026_05_25_v12_arbitration.md` (promoted to repo-root `DECISIONS.md` per Phase F-REPRO.F) |
| v11.4-D11 | §6.4 meta-DECISIONS on 3-of-3 FAIL | DRAFT (pending Owner approval) | `prompt/052526/DECISIONS_2026_05_26_meta_3of3_FAIL.md` |

## Reviewer artifacts

| Round | Reviewer | Phase | Path |
|---|---|---|---|
| seal package | ChatGPT 5.5 Pro | Sealing | `prompt/052326/REVIEW_REQUEST_ChatGPT55Pro_v11_4_seal_package.md` |
| 2 | ChatGPT 5.5 Pro | Pre-reg drafting | request: `prompt/052426/REVIEW_REQUEST_ChatGPT55Pro_v11_4_ROUND_2.md` + response: `prompt/052426/REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_2.md` |
| 3 | ChatGPT 5.5 Pro | Pre-reg drafting | request: `prompt/052426/REVIEW_REQUEST_ChatGPT55Pro_v11_4_ROUND_3.md` + response: `prompt/052426/REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_3.md` |
| 4 | ChatGPT 5.5 Pro | Pre-reg drafting | request: `prompt/052426/REVIEW_REQUEST_ChatGPT55Pro_v11_4_ROUND_4.md` + response: `prompt/052426/REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_4.md` |
| seal package | Codex | Sealing | `prompt/052326/REVIEW_REQUEST_Codex_v11_4_seal_package.md` |
| 3 | Codex | Pre-reg drafting | request: `prompt/052426/REVIEW_REQUEST_Codex_v11_4_ROUND_3.md` |
| 4 | Codex | Pre-reg drafting | request: `prompt/052426/REVIEW_REQUEST_Codex_v11_4_ROUND_4.md` |
| 5 (methodology) | ChatGPT 5.5 Pro | v12 design | request: `prompt/052526/REVIEW_REQUEST_ChatGPT55Pro_v12_design.md` + response: `prompt/052526/REVIEW_v12_design_ChatGPT55Pro_methodology.md` (also archived under `buffet_indicator/reviews/` per F-REPRO.G) |
| 5 (implementation) | Codex | v12 design + post-verdict implementation review | request: `prompt/052526/REVIEW_REQUEST_Codex_v12_design.md` + response: `buffet_indicator/reviews/REVIEW_Codex_v12_design_round5_implementation_correctness.md` (Codex commit `3abf22f`) |

## Progress reports (per phase)

| Phase | Path |
|---|---|
| Phase D | `outputs/v2_sprint_phase_progress_2026-05-25T16-11-42Z.md` |
| Phase E | `outputs/v2_sprint_phase_progress_2026-05-25T18-08-42Z.md` |
| Phase F-BLK1 | `outputs/v2_sprint_phase_F_BLK1_progress_2026-05-25T21-18-46Z.md` |
| Phase F-DOC | `outputs/v2_sprint_phase_F_DOC_progress_2026-05-25T23-50-49Z.md` |
| Phase F-REPRO | `outputs/v2_sprint_phase_F_REPRO_progress_<ts>.md` (this phase) |
| Earlier Phase B+C / A | Older `outputs/v2_sprint_phase_progress_20260525T*.md` |

## Engineering closeout artifacts

- `buffet_indicator/outputs/v11_4_sprint_engineering_closeout.md` — engineering scope completion report (Phase F-DOC.E)
- `buffet_indicator/outputs/lc_v2_verdict_blk1_delta.md` — Phase F-BLK1 delta (pre-BLK-1 → BLK-1 canonical)
- `buffet_indicator/outputs/lc_v2_verdict_closeout_delta.md` — Phase F-DOC closeout delta (BLK-1 → pinned closeout)
- `buffet_indicator/outputs/pinned_test_verification.md` — Phase F-DOC.B verification summary

## Repository

- **Public**: `https://github.com/mvfoundation01/macro`
- **Working branch for v11.4**: `spec/liquidity-composite-v2.0`
- **Default branch**: `main` (NOT merged; v2.0 verdict is FAIL per sealed §7 spec branch only)

## Tags

| Tag | Marks | Status |
|---|---|---|
| `pre-v11.4-baseline` | Pre-sprint state | Historical |
| `v11.4-prereg-sealed` | Pre-registration sealing (sealed pre-reg at `c3c3ec1a…`) | Permanent |
| `v11.4-engineering-closeout` | Engineering scope completion (Phase F-DOC) | Permanent |
| `v11.4-ssrn-reproducibility-ready` | SSRN reproducibility appendix complete (Phase F-REPRO; this phase) | **THIS PHASE** |
| Future `v11.4-ssrn-submitted` | SSRN submission | Pending |
| Future `v12-prereg-sealed` | v12-A′ pre-reg seal (if pursued) | Conditional |

## Key SHA-256 values (for citation / verification)

| Artifact | SHA-256 |
|---|---|
| Sealed pre-reg | `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` |
| Canonical verdict (file-byte) | `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c` |
| Canonical verdict (normalized substantive) | `0fe5c5053af78bac061a7ca89568b484b6583a6d9da0d0ddbf5b0837d7344f02` |
| Pre-BLK-1 verdict (file-byte; preserved audit-trail) | `6671cc9ff7b9e9f97a0c7447528bf0bcdc12b18a9406b29a8f0e632550200416` |
| Pre-BLK-1 verdict (original sidecar; in-memory; legacy bug) | `84a457e3f4…` |
| Pinned closeout verdict (file-byte; F-DOC.C) | `1925e658ef9c88aabecae03c445396f4ed6ffe7a290f07cd0ecb5122a5c31899` |
| Clean-state clone verdict (file-byte; F-REPRO.C) | `33649ab75c5f521ad17d8198f85ec7f4d8d0d1230f4d17977369bdcbaf5c891a` |

All 3 post-BLK-1 verdicts (canonical, pinned closeout, clean-state clone) share the same **normalized substantive SHA-256** `0fe5c5053af78bac061a7ca89568b484b6583a6d9da0d0ddbf5b0837d7344f02`.

## Final sprint state (Phase F-REPRO closing)

- Verdict outcome: **FAIL (1/7)** — robust to library versions, implementation iteration, OS platform, clean state from public repo
- Sealed pre-reg: IMMUTABLE
- Canonical verdict: byte-reproducible across `sha256sum` cross-OS, normalized substantively byte-equal across all four reproducibility axes
- Strategist mistakes confessed: 10 (all caught architecturally; 0 code damage)
- Reviewer rounds: 5 across pre-reg drafting + v12 design
- Engineering scope: COMPLETE (tag `v11.4-engineering-closeout`)
- Reproducibility scope: COMPLETE (tag `v11.4-ssrn-reproducibility-ready`)
- Remaining: §6.4 meta-DECISIONS (DRAFT pending Owner approval) + SSRN writeup (Strategist multi-session intellectual work)
