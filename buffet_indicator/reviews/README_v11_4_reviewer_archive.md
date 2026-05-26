# v11.4 Sprint Reviewer Archive

This directory holds the canonical tracked archive of all reviewer artifacts (REQUESTS + RESPONSES) for the v11.4 Liquidity Composite v2.0 sprint, copied here from Strategist's working area `prompt/052*/` per Phase F-REPRO.G.

## Inventory (v11.4-specific)

### Pre-registration drafting reviews

| Round | Reviewer | Request | Response |
|---|---|---|---|
| 1 (seal package) | ChatGPT 5.5 Pro | `REVIEW_REQUEST_ChatGPT55Pro_v11_4_ROUND_1_seal_package.md` | `REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_1.md` |
| 1 (seal package) | Codex | `REVIEW_REQUEST_Codex_v11_4_ROUND_1_seal_package.md` | (text response embedded in DECISIONS Round-1 arbitration) |
| 2 | ChatGPT 5.5 Pro | `REVIEW_REQUEST_ChatGPT55Pro_v11_4_ROUND_2.md` | `REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_2.md` |
| 3 | ChatGPT 5.5 Pro | `REVIEW_REQUEST_ChatGPT55Pro_v11_4_ROUND_3.md` | `REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_3.md` |
| 3 | Codex | `REVIEW_REQUEST_Codex_v11_4_ROUND_3.md` | (text response embedded in DECISIONS Round-3 arbitration) |
| 4 | ChatGPT 5.5 Pro | `REVIEW_REQUEST_ChatGPT55Pro_v11_4_ROUND_4.md` | `REVIEW_v11_4_ChatGPT55Pro_methodology_ROUND_4.md` |
| 4 | Codex | `REVIEW_REQUEST_Codex_v11_4_ROUND_4.md` | (text response embedded in DECISIONS Round-4 arbitration) |

### v12 design review (Round 5)

| Round | Reviewer | Request | Response |
|---|---|---|---|
| 5 (methodology) | ChatGPT 5.5 Pro | `REVIEW_REQUEST_ChatGPT55Pro_v12_design.md` | `REVIEW_v12_design_ChatGPT55Pro_methodology.md` |
| 5 (implementation correctness) | Codex | `REVIEW_REQUEST_Codex_v12_design.md` | `REVIEW_Codex_v12_design_round5_implementation_correctness.md` (committed as part of Codex repository PR at `3abf22f`) |

## Pre-v11.4 review artifacts in this directory

The following files are NOT part of the v11.4 sprint but were preserved in this directory from earlier work:

- `PHASE_2_diagnosis_notes.md` (v11.0/v11.1 era)
- `PHASE_3_svg_nan_findings.md` (v11.0/v11.1 era)
- `REVIEW_PACKAGE_v11.2.2_remediation.md` (v11.2 era)
- `STAGE_1_svg_nan_diagnosis.md` (v11.0/v11.1 era)
- `diagnostic_artifacts/` (subdirectory; pre-v11.4)

## Reviewer attribution

Per DECISIONS.md v11.4-D10 §10 and v11.4-D11 §15, the following reviewers contributed substantively to v11.4:

**ChatGPT 5.5 Pro** (methodology lane):
- 4 rounds of pre-registration drafting review
- Round 5 v12 design + methodology review
- Caught Strategist mistakes #2, #4
- Identified PIT warmup contradiction methodologically

**Codex (ChatGPT Codex)** (empirical execution lane):
- 3+ rounds of pre-registration drafting review (request files preserved; responses embedded in DECISIONS arbitrations)
- Round 5 v12 design + implementation correctness review
- Caught Strategist mistakes #3, #5, #10
- Identified BLOCKER CR-1 (PIT vintage discipline) + 4 MAJOR issues
- Empirically confirmed PIT warmup contradiction + pinned re-run verdict equivalence

Both reviewers will be credited in:
1. SSRN writeup acknowledgments (per Path A discipline)
2. `DECISIONS.md` (canonical record)
3. Public repository documentation

## Working area (untracked) vs tracked archive

The working files in `prompt/052*/` remain as Strategist's working area (untracked in git by convention). This `buffet_indicator/reviews/` directory is the **tracked canonical archive** ensuring reviewer artifacts survive in the public repository for SSRN reproducibility / replication purposes.
