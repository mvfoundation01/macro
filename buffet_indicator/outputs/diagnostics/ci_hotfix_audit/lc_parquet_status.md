# LC parquet status — P1-3 (2026-05-23)

## Inventory

**Committed on `spec/liquidity-composite-v1.0` HEAD** (`ec08850`):

```
buffet_indicator/data/master/
├── _catalog.json
├── _scaling_anchors.json
├── _source_policy.json           # new on spec branch
├── icedxy_close.parquet          # new on spec branch (ICE DXY cache, LFS)
├── nber_recessions.meta.json
├── nber_recessions.parquet
└── wilshire_5000.parquet
```

**Committed on `main` HEAD** (`e1eed67`):

```
buffet_indicator/data/master/
├── _catalog.json
├── _scaling_anchors.json
├── nber_recessions.meta.json
├── nber_recessions.parquet
└── wilshire_5000.parquet
```

Delta on spec branch over main: `_source_policy.json`, `icedxy_close.parquet` (LFS).

## The 12 LC parquets (P1-3 subject)

The 12 LC source-data parquets called out in TECH_DEBT P1-3 are:

```
busloans, dtwexbgs, ioer, iorb, m2_sl, rrpontsyd, sofr,
tedrate, totll, walcl, wdtgal
```

(11 distinct — the prior session's list had `sofr` duplicated; corrected here.)

**Status**:

- NOT committed on `main`.
- NOT committed on `spec/liquidity-composite-v1.0` HEAD.
- Present as local working files in `buffet_indicator/data/master/` on the current clone (~0.5 MB total; regeneratable from FRED).
- Referenced as new catalog entries in `stash@{1}` on `spec/liquidity-composite-v1.0` (modifications to `_catalog.json` adding the 12 entries).

## Decision

**SCOPE-GATED per prompt §2.5**: do NOT commit these to main or to the v2.0 branch this session.

Rationale: committing the LC source-data parquets to main is part of the Strategist's merge-to-main arbitration (per `LC_V1_SPRINT_CLOSEOUT_REPORT.md` §8 on the spec branch — three options open: feature-flag merge, indefinite spec-branch retention, or merge-with-disclosure). Each of the three options has a different answer for "where do the LC source parquets live". Pre-empting that decision now would constrain the Strategist's choice.

## TECH_DEBT.md P1-3 update

Change status from "untracked; commit via LFS or document regeneration" to:

> **BLOCKED** — awaiting Strategist merge-to-main arbitration. The 12 parquets are local working files matching the `.gitattributes` LFS pattern but intentionally not committed. The catalog entries that reference them are in `stash@{1}` on `spec/liquidity-composite-v1.0`. When Strategist decides on merge-to-main (3 options per closeout report §8), the parquet placement follows from that decision.

## Regeneration command (for completeness)

The 12 parquets are pulled from FRED by the orchestrator on first run:

```bash
cd buffet_indicator
INTEGRATION_TESTS=1 FRED_API_KEY=<owner-key> python -m src.cli ingest --series busloans dtwexbgs ioer iorb m2_sl rrpontsyd sofr tedrate totll walcl wdtgal
```

(Owner has the key in a private `.env` not committed.)
