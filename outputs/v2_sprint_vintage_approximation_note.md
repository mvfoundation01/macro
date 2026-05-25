# v2.0 sprint — Vintage approximation note

**Decision**: Strategist arbitration §B / Option B3 per
`PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md`.

**Written**: 2026-05-25 (Phase B.1 implementation session)
**Affects**: `buffet_indicator/src/ingest/master_archive.py::load_master`

---

## What the sealed pre-reg mandates

Sealed pre-reg §3.2.2 (commit `2a94417`):

> For every forecast origin `t`, component values are computed from records
> with release/vintage timestamp `≤ t`. For revisable FRED series (`M2SL`,
> `BUSLOANS`, `TOTLL`, `WALCL`, `WDTGAL`, and any other ALFRED-supported
> series), the consumption pattern is:
>
> ```python
> series = load_master(series_id, vintage=t, fill="none")  # MANDATORY
> # load_master(series_id, vintage="latest")  ← FORBIDDEN inside backtest loops
> ```
>
> Latest-vintage consumption is forbidden inside any code path that
> produces verdict-bearing artifacts.

Every verdict JSON cell records `feature_vintage_max` and asserts
`feature_vintage_max ≤ forecast_origin`. Failing this assertion at any
cell raises `LookAheadViolation` and aborts the run.

---

## What the data architecture supports

The master parquet schema records ONE `vintage` value per `(date, series_id)`
tuple — the retrieval timestamp of the ingestion pipeline
(e.g., `2026-05-22 16:26:28.303991`).

```
columns: [value, source, vintage, transform]
index:   date (DatetimeIndex)
```

There is NO ALFRED-style revision history per observation. The data IS the
latest-known value at ingestion time. The `vintage` column is uniform
across all rows in a single ingestion run, so it does not enable
"value-as-of-date-`t`" lookups.

---

## v2.0 approximation (Option B3)

`load_master(series_id, vintage=t)` filters to rows where `date <= t` —
i.e., an **observation-date** filter.

This catches the egregious look-ahead pattern of "consuming data
published after `t`" but does **NOT** catch the subtler "consuming a
post-publication FRED revision."

For verdict JSON cells (Phase E):

```
feature_vintage_max := max(observation_date in cell's data) ≤ forecast_origin
```

The `LookAheadViolation` check is on observation dates.

### What `load_master` does in practice (post Phase B.1)

| Call form | Effect |
|---|---|
| `load_master("walcl")` | No filter; full series returned (back-compat default `vintage="latest"`). |
| `load_master("walcl", vintage="latest")` | Same as above; explicit. |
| `load_master("walcl", vintage=pd.Timestamp("2020-01-01"))` | Filter to `date <= 2020-01-01`. |
| `load_master("walcl", vintage=pd.Timestamp("2099-01-01"))` | `ValueError("...is in the future")`. |
| `load_master("walcl", vintage="bogus")` | `ValueError("...must be 'latest' or a pd.Timestamp")`. |

`vintage` composes with `start`/`end`; the most-restrictive cutoff wins.

---

## Why this is honest at v2.0 sprint scope

- The data used here IS THE SAME DATA v1.0 used (which produced sealed
  verdict `0/7 FAIL` at commit `d56174c`).
- v2.0's amendments are methodological (skewed-t, OOS gate, two-sided C4,
  equipoise priors), NOT data-architectural. Adding ALFRED-aware
  ingestion would be a separate sub-sprint.
- v2.0 verdict can be re-run with true vintages later as robustness check
  without changing the pre-registered methodology.

---

## What this approximation does NOT protect against

| Look-ahead pattern | Caught by observation-date approximation? |
|---|---|
| Consuming observations published after `t` (date > `t`) | YES ✓ |
| Consuming a FRED revision published between `date` and `t` | NO ✗ |
| Consuming a different version of a series than was first published | NO ✗ |

The first pattern is the egregious / unambiguous look-ahead. The second
and third are subtler and require ALFRED-style revision tracking.

For v1.0 components (NetFed = WALCL − RRPONTSYD − WDTGAL; M2SL;
BUSLOANS→TOTLL; DTWEXBGS; TED→SOFR−IORB), revisions exist but are
typically small in magnitude (a few basis points for monetary
aggregates, often zero for monthly figures backfilled cleanly). The
approximation is reasonable, NOT exact.

---

## Future work (out of v2.0 sprint scope)

1. Build ALFRED-aware ingestion (`src/ingest/alfred.py`) recording
   per-(date, series) release timestamps.
2. Migrate master parquet schema from
   `[value, source, vintage, transform]` to
   `[value, source, observation_date, release_timestamp, transform]`.
3. Re-run v2.0 verdict; document any deltas vs. observation-date-approximated
   verdict.
4. If the deltas are material, file a v2.1 amendment.

---

## Cross-references

| Artifact | Role |
|---|---|
| `buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` §3.2.2 | Vintage policy authority |
| `buffet_indicator/src/ingest/master_archive.py::load_master` | Implementation |
| `buffet_indicator/tests/ingest/test_master_archive.py` (5 new `test_load_master_vintage_*` tests) | Acceptance |
| `outputs/v2_sprint_phase_B_callback_load_master_and_sealed_conflicts.md` | The original conflict scoping |
| `PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md` §2 | Strategist arbitration (Option B3) |

— Claude Code, v2.0 sprint Phase B.1 @ 2026-05-25
