# BLOCKED — Sub-stage A1 — ICE DXY (Stooq access)

**Filed by**: Claude Code Session 5 (autonomous)
**Date**: 2026-05-22
**Sub-stage**: A1 (data ingestion)
**Affects**: z₄ DXY⁻¹ component pre-2006 → blocks LC_FULL, LC_TIER2, LC_DEEP pre-2006 history
**Spec reference**: spec §1.1 row s4b, spec §17 (known risk row "ICE DXY source (Stooq) intermittent | 40% probability | Stage A1 blocker")

## Symptom

Stooq's free CSV endpoint for the ICE DXY narrow-basket symbol returns empty/gated content:

```
$ curl -s 'https://stooq.com/q/d/l/?s=dx.f&i=d'
# (empty)

$ curl -s 'https://stooq.com/q/d/l/?s=^dxy&i=d'
Get your apikey:
1. Open https://stooq.com/q/d/?s=^dxy&get_apikey
```

Both the older `dx.f` (futures continuous) and `^dxy` (index) routes are unavailable without an API key as of 2026-05-22. This is exactly the risk row the spec anticipated.

## Impact

- `src/ingest/lc_v1_loader.build_lc_icedxy_master()` works correctly against injected/mocked CSV bytes — all 8 unit tests pass (S1-S6, O2, A1-audit), plus the integration test confirms FRED-side fetches work.
- Live Stooq fetch (`test_I2_real_stooq_icedxy_happy_path`) fails. This is gated behind `INTEGRATION_TESTS=1` and does NOT block CI.
- DTWEXBGS (FRED) covers 2006+. Without ICE DXY:
  - LC_FULL effective start shifts from 2003-01 → 2007-01 (need DXY+12mo warmup).
  - LC_TIER2 effective start shifts from 1987-01 → 2007-01.
  - LC_DEEP effective start shifts from 1973-01 → 2007-01.
  - All three composites collapse to a much shorter sample, which is likely insufficient for falsifiability criteria 1-3 (OOS R² thresholds at 1Y/3Y/5Y).

## Per spec §17 mitigation, recommended fallbacks (Strategist decision needed)

| Option | Pros | Cons |
|---|---|---|
| **A. Norgate Diamond** (paid subscription) | Authoritative, full 1971+ ICE DXY history | Requires paid subscription on owner's machine |
| **B. yfinance ticker `DX-Y.NYB`** | Free, daily, no key | History only back to 1985 → still missing 1971-1984 for LC_DEEP |
| **C. Static archive parquet** | Reproducible, version-controlled | One-time manual fetch; requires owner provenance documentation |
| **D. Defer to v11.4** | Unblocks Stage 3 modeling on FRED-only path | Reduces LC scope; violates spec §1.2 (LC_DEEP, LC_TIER2 not deliverable per spec) |

## Per spec §18

> If Claude Code wants to add ANY of these in v11.3, file an amendment spec.

Switching from Stooq to a different ICE DXY source is **not an amendment** of the sealed pre-reg `a8635ef` (which lists ICE DXY as the abstract series, not a specific vendor) — it is a within-scope vendor swap permitted by spec §17. So options B or C can proceed without amendment, contingent on owner approval of the vendor.

## Resolution path

**Recommended (this session): defer the live ICE DXY fetch.** The loader is fully tested against synthetic bytes; once a fresh ICE DXY CSV is staged (either via Norgate, yfinance, or owner-provided archive), `build_lc_icedxy_master(stooq_body=<bytes>)` can ingest it. The 11 FRED series are unaffected by this blocker.

**Next session**: owner provides ICE DXY source decision; resolve in early sub-stage A2 or B.

## Status flag

Surface in §7 final report under "Owner actions required".

---

## Resolution (2026-05-23, Session 6 §2.0)

**Decision**: Option A (Norgate Diamond) + Option B (yfinance) hybrid.

- **Norgate Diamond** serves as the deep-history primary (1971+). Owner runs
  `scripts/bootstrap_icedxy_from_norgate.py` ONCE while subscription is active.
  Result cached to `data/master/icedxy_close.parquet` and committed via Git LFS.
- **yfinance `DX-Y.NYB`** (1985+) serves as Tier-4 runtime fallback for tail updates.
- **Local MoDH parquet** (`data/master/icedxy_close.parquet`) is the default
  runtime source — survives Norgate subscription cancellation per spec §2.4.8.

**Implementation landing**:
- `src/ingest/lc_v1_loader.build_lc_icedxy_master()` rewritten with 3-tier source
  priority (`norgate_data` / `yfinance_data` / `cache_parquet_path`), monthly EOM
  resample, log transform, and DTWEXBGS log-level-additive splice at 2006-01-04
  with sealed gates (`corr > 0.85`, `mean |z-divergence| < 0.30`) per pre-reg
  a8635ef §1.3.
- `src/ingest/lc_v1_loader.build_lc_icedxy_stooq_master_legacy()` retains the
  Stooq master-write path behind a `DeprecationWarning` for audit replay only.
- `scripts/bootstrap_icedxy_from_norgate.py` is the one-shot Norgate cache builder.
- `data/master/_source_policy.json` records the priority chain formally
  per master spec §2.4.5 Step 1 override mechanism.
- 12 new unit tests in `tests/ingest/test_lc_v1_loader_icedxy.py` cover the
  priority chain, splice algorithm, gates, look-ahead audit, and the cached-parquet
  default path.

**Stooq fallback deprecated**: its empty-response state is documented as a
historical artifact, not a current path. Code retained behind
`build_lc_icedxy_stooq_master_legacy()` (and orchestrator flag
`use_stooq_legacy=False`, default off) for future audit, with a deprecation
warning.

**Pre-reg posture**: this resolution is a within-scope vendor swap permitted by
spec §17 — NOT an amendment of sealed pre-reg `a8635ef` (which lists ICE DXY
abstractly, not a specific vendor). Both pre-reg invariants (`a90b02d` on `main`,
`a8635ef` ancestor of `spec/liquidity-composite-v1.0` HEAD) remain intact.

**Owner action remaining**: run
`python scripts/bootstrap_icedxy_from_norgate.py` ONCE while Norgate Diamond is
active to populate the cache. Until then, `build_lc_icedxy_master()` raises
`RuntimeError` with an actionable error message. Components downstream of z4
(LC composites) will naturally be NaN where ICE DXY is missing, allowing the
rest of the modeling layer to ship and be validated independently.
