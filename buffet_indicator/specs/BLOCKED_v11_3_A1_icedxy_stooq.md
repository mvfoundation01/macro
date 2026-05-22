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
