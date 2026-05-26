# Data Manifest — v11.4 Sprint Reproducibility

**Total series catalogued**: 22
**Generated**: `2026-05-26T01:51:46Z`
**Sealed pre-reg SHA-256**: `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` (IMMUTABLE)
**Canonical verdict SHA-256**: `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c`
**Manifest version**: `v2.0-F_REPRO.A`
**Tier distribution**: `{'2': 15, '5': 4, '1': 1, '4': 1, 'spliced': 1}`

This document is the human-readable companion to `data_manifest.json`. Both files are byte-exact (LF-only, UTF-8) per Phase F-BLK1.F + F-REPRO.A convention.

---

## v2.0 component series (used in BLK-1 canonical verdict)

| Key | series_id | Tier | Freq | n_obs | Earliest | Latest | Used by | SHA-256 (cache) |
|---|---|---|---|---|---|---|---|---|
| `master.busloans` | `BUSLOANS` | 2 | M | 952 | 1947-01-31 | 2026-04-30 | z3 | `ce9a8f4551d7…` |
| `master.dtwexbgs` | `DTWEXBGS` | 2 | D | 5313 | 2006-01-04 | 2026-05-15 | z4 | `0032ba72c97d…` |
| `master.ioer` | `IOER` | 2 | D | 4676 | 2008-10-09 | 2021-07-28 | z5 | `ddc557e48df2…` |
| `master.iorb` | `IORB` | 2 | D | 1759 | 2021-07-29 | 2026-05-22 | z5 | `157634394f6d…` |
| `master.m2_sl` | `M2SL` | 2 | M | 807 | 1959-01-31 | 2026-03-31 | z2 | `f44465d26667…` |
| `master.rrpontsyd` | `RRPONTSYD` | 2 | D | 3304 | 2013-09-23 | 2026-05-21 | z1 | `f164d5fdd0e4…` |
| `master.sofr` | `SOFR` | 2 | D | 2123 | 2018-04-03 | 2026-05-21 | z5 | `a19f5fdb8000…` |
| `master.tedrate` | `TEDRATE` | 2 | D | 9407 | 1986-01-02 | 2022-01-21 | z5 | `c0ea379039d6…` |
| `master.totll` | `TOTLL` | 2 | W | 2784 | 1973-01-03 | 2026-05-06 | z3 | `e9e22eae87e0…` |
| `master.walcl` | `WALCL` | 2 | W | 1223 | 2002-12-18 | 2026-05-20 | z1 | `37664fc8857c…` |
| `master.wdtgal` | `WDTGAL` | 2 | W | 1223 | 2002-12-18 | 2026-05-20 | z1 | `20969a5f30f8…` |

## Forward-return source series

| Key | series_id | Tier | Freq | n_obs | Earliest | Latest | Used by | SHA-256 (cache) |
|---|---|---|---|---|---|---|---|---|
| `forward_returns.shiller_ie_data` | `SHILLER_IE_DATA` | 1 | M | 1864 | 1871-01-31 | 2026-04-30 | forward_returns_pre_1988 | `0da8a5df5b64…` |
| `forward_returns.spxtr_daily` | `SPXTR` | 5 | D | 9670 | 1988-01-04 | 2026-05-18 | forward_returns_post_1988 | `54a942084c8e…` |

## Splice points (per sealed §10.1)

| Splice | Date / Window | Method | Sealed §10.1 validation |
|---|---|---|---|
| `BUSLOANS` → `TOTLL` | 1973-01-03 | YoY-growth additive constant `c` | `corr > 0.50` AND `|c| < 0.05` per sealed §10.1 + Phase B+C arbitration |
| `IOER` → `IORB` | 2021-07-29 (transitioned at 2021-07-31 monthly EOM) | Level concatenation | `|diff at splice| < 0.01pp` per Phase B+C |
| z_TED → z_(SOFR-IORB) | 2022-02-01 → 2023-04-01 (14-month z-blend) | Linear z-score blend on monthly EOM grid | `|funding_z.diff().max()| < 1.5σ` per Phase B+C; relaxed 24-mo PIT warmup for z_(SOFR-IORB) per Phase E note |
| `Shiller IE_DATA` → `SPXTR` | 1988-01-01 | Nominal total-return splice on monthly EOM | Continuity check; sealed §3.1 |
| `ICE_DXY` → `DTWEXBGS` | (deferred; ICE_DXY parquet absent in v2.0) | Log-levels additive `c` (would-be) | sealed §10.1; v2.0 uses DTWEXBGS only (first non-NaN ~2006) → z4 valid ~2016 |

## Preserved pre-v2.0 entries (other sprints' provenance)

Series catalogued from earlier v11.0 / v11.1 / v11.2 sprints are preserved with `preserved_from_pre_v2_0_manifest: true` for cross-sprint continuity but are NOT used in v2.0 verdict:

- `fred.equities_all`: BOGZ1LM883164105Q (Tier 2; Q; n=321)
- `fred.equities_nonfin`: NCBEILQ027S (Tier 2; Q; n=321)
- `fred.equities_public`: BOGZ1LM883164115Q (Tier 2; Q; n=321)
- `fred.gdp`: GDP (Tier 2; Q; n=321)
- `master.wilshire_5000`: wilshire_5000 (Tier spliced; ?; n=11810)
- `tradingview.gdp_backup`: FRED:GDP (Tier 5; Q; n=316)
- `tradingview.spx`: SPX (Tier 5; D; n=25232)
- `tradingview.wilshire_tv`: FRED:WILL5000PRFC (Tier 5; D; n=11073)
- `yahoo.wilshire`: ^W5000 (Tier 4; D; n=9400)

## Vintage discipline

Per sealed §3.2.2 the verdict-bearing run is required to call `load_master(series_id, vintage=t, fill='none')` for each forecast origin `t`. Phase B+C arbitration §B approved the **observation-date approximation** (Option B3) as the v2.0 implementation: the master archive stores the FRED observation-dated time series; the strict-shift PIT z-score in `src/transform/pit_zscore.py` plus the per-origin `feature_vintage_max_at_origin` mapping populated by `src/models/v2_panel_builder.py` (Phase F-BLK1.A) enforce the discipline. Phase F-BLK1.B's `run_pit_audit_non_tautological` walks every (origin, cell) pair and asserts `fvm[t] <= t` — 756 pairs checked, 0 violations in the canonical verdict.

FRED series listed above are subject to retroactive revision (ALFRED vintages). Any reproducer who fetches these series AFTER the `latest_date` shown may receive revised values — the SHA-256 in this manifest pins the AS-OF-FETCH content used to produce the canonical verdict. The `cache_path` files in the public repo are the authoritative snapshot.

## Reproducibility entry points

- Reconstruction script: `src/replication/reconstruct_master.py` (Phase F-REPRO.B)
- Replication guide: `outputs/replication/REPLICATION_INSTRUCTIONS.md` (Phase F-REPRO.D)
- Sprint navigation index: `outputs/SPRINT_v11_4_INDEX.md` (Phase F-REPRO.E)
- Pinned environment: `requirements.lock` (Phase F-DOC.A)
