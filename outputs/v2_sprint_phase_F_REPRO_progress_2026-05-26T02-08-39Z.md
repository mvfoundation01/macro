# Phase F-REPRO progress

**Timestamp**: 2026-05-26T02:08Z (UTC)
**Session**: Phase F-REPRO (SSRN reproducibility appendix preparation)
**Starting HEAD**: `269d4e8` (Phase F-DOC progress report ending)
**Ending HEAD**: `79230fb` (Phase F-REPRO.G reviewer archive) + tag `v11.4-ssrn-reproducibility-ready`
**Commits this session**: 7 (all pushed)
**Pushed**: every commit + annotated tag

## Phases completed

| Phase | Status | Commit | Notes |
|---|---|---|---|
| §2 F.REPRO.A — manifest audit + augment | PASS | `b0a2857` | 22 series catalogued (11 v2.0 components + 2 forward-return + 9 preserved pre-v2.0); generator script + companion `.md` |
| §3 F.REPRO.B — reconstruction script | PASS | `0283672` | `src/replication/reconstruct_master.py` + 8/8 unit tests (mocked; missing-manifest, malformed JSON, missing-creds, SHA match, SHA mismatch, loader exception, non-FRED skip, report contract) |
| §4 F.REPRO.C — clean-state end-to-end repro | PASS | `7efd3c2` | Cloned to `$TEMP\macro_v11_4_repro_test\`; pinned env install; verdict pipeline outcome = FAIL (1/7); normalized SHA `0fe5c5053af…` MATCH (0 field diffs at 1e-12); main repo canonical INTACT post-test |
| §5 F.REPRO.D — replication instructions | PASS | `7efd3c2` (bundled with §4) | `outputs/replication/REPLICATION_INSTRUCTIONS.md` — 6-step third-party guide with prerequisites, troubleshooting matrix, FRED revision caveats, citation pointers |
| §6 F.REPRO.E — sprint navigation index | PASS | `291f9bc` | `outputs/SPRINT_v11_4_INDEX.md` — single entry-point for readers; links all artifacts; canonical SHA-256 values for citation; 6 tags inventoried |
| §7 F.REPRO.F — canonical DECISIONS.md | PASS | `f07a6f0` | Repo-root `DECISIONS.md` with v11.4-D1..D9 indexed, full D10 APPROVED content (with status table), D11 DRAFT referenced (Strategist draft remains in prompt/052526/ pending Owner approval) |
| §8 F.REPRO.G — reviewer artifacts | PASS | `79230fb` | 14 reviewer artifacts copied from `prompt/052*/` to `buffet_indicator/reviews/` + README inventory + attribution per DECISIONS v11.4-D10 §10 + D11 §15 |
| §9 Tag `v11.4-ssrn-reproducibility-ready` | DONE | (annotated tag on `79230fb`) | Pushed to `origin/v11.4-ssrn-reproducibility-ready` |

## Reproducibility verification (HEADLINE)

| Item | Result |
|---|---|
| Sealed pre-reg SHA-256 | `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` — IMMUTABLE / UNCHANGED ✓ |
| Canonical verdict file-byte SHA | `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c` — UNCHANGED ✓ |
| Clean-state clone verdict outcome | `FAIL (1/7)` — MATCH vs canonical |
| Clean-state clone normalized SHA | `0fe5c5053af78bac061a7ca89568b484b6583a6d9da0d0ddbf5b0837d7344f02` — EXACT MATCH vs canonical |
| Clean-state clone file-byte SHA | `33649ab75c5f521ad17d8198f85ec7f4d8d0d1230f4d17977369bdcbaf5c891a` (differs in dynamic metadata; expected) |
| Reconstruction script: all 11 v2.0 FRED series mapped | YES (FRED_API_KEY required at run-time for fetch; cached data sufficient if present) |
| Substantive field diffs at tol 1e-12 | **0** |

## §16 seal-report criteria

Still **10/10 PASS**. F-REPRO did not touch any seal-report surface; sealed pre-reg SHA `c3c3ec1a…` unchanged at session end.

## Strategist callbacks

**0 callbacks fired.** Expected `P(callback) = 10–15%` per prompt §12; actual = 0%. Hotspots anticipated by §12:

| Hotspot | P (prompt) | Actual |
|---|---|---|
| Manifest series list canonical source | 5% | resolved by reading sealed §10.1 + components/composite.py |
| Reconstruction script: FRED API rate limits | 8% | n/a (mocked tests; clean-state test used cached data) |
| ChatGPT 5.5 Pro Round 5 review file missing | 8% | RESOLVED — found at `prompt/052526/REVIEW_v12_design_ChatGPT55Pro_methodology.md`; copied to `reviews/` |
| Cached data SHA mismatch (post-revision) | 10% | n/a in this session (no FRED fetch performed) |
| DECISIONS.md target location ambiguity | 3% | resolved per master spec §1.6.12 (repo root) |

Pattern from Phase D, E, F-BLK1, F-DOC continues: 0 callbacks under forward-policy + sealed-spec-verbatim discipline.

## v11.4 sprint final state

| Tag | Status | Marks |
|---|---|---|
| `v11.4-prereg-sealed` | Permanent | Sprint started; pre-reg `c3c3ec1a…` immutable |
| `v11.4-engineering-closeout` | Permanent | Engineering scope completed (Phase F-DOC end) |
| **`v11.4-ssrn-reproducibility-ready`** | **Permanent (NEW)** | **SSRN reproducibility appendix complete (this phase end)** |
| Future `v11.4-ssrn-submitted` | TBD | Pending Owner |
| Future `v12-prereg-sealed` | Conditional | Pending Owner decision on Pivot A |

## What this phase delivered (artifact inventory)

New files (tracked):
- `buffet_indicator/data_manifest.json` — augmented from 11 pre-v2.0 entries to **22 entries** with full v2.0 coverage
- `buffet_indicator/data_manifest.md` — human-readable companion
- `buffet_indicator/scripts/_build_data_manifest_v2.py` — generator
- `buffet_indicator/src/replication/__init__.py` + `reconstruct_master.py`
- `buffet_indicator/tests/replication/__init__.py` + `test_reconstruct_master.py` (8 tests)
- `buffet_indicator/outputs/replication/REPLICATION_INSTRUCTIONS.md`
- `buffet_indicator/outputs/replication/v11_4_clean_state_repro_report.md`
- `buffet_indicator/outputs/SPRINT_v11_4_INDEX.md`
- `DECISIONS.md` (repo root)
- `buffet_indicator/reviews/README_v11_4_reviewer_archive.md`
- `buffet_indicator/reviews/REVIEW_*.md` × 14 (copied from `prompt/052*/`)

New tag: `v11.4-ssrn-reproducibility-ready` (annotated, on commit `79230fb`).

## Next prompt

**No further engineering prompts for v11.4 are anticipated unless:**

| Trigger | Action |
|---|---|
| Owner explicitly approves v11.4-D11 (§6.4 meta-DECISIONS) | Small ad-hoc prompt: append full D11 content to canonical `DECISIONS.md`; commit + push |
| Owner pursues v12-A′ | New sealed pre-reg + multi-round review + implementation sprint (months) |
| SSRN reviewer feedback requires repo polish | Ad-hoc prompts on specific reproducibility / clarification items |
| 2029-Q1 calendar event | Sealed v2.0 re-evaluation (automatic per sealed §6.4 implicit pre-commitment) |

Otherwise: Strategist authors SSRN writeup (multi-session intellectual work, no Claude Code involvement until v12-A′ implementation if pursued).

— Phase F-REPRO progress report, 2026-05-26T02:08Z
