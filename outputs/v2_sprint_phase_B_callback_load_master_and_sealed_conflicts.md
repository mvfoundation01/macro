# v2.0 sprint — Phase B callback: `load_master` signature + sealed-spec conflicts

**Filed**: 2026-05-25T12:42:12Z
**Filer**: Claude Code
**Phase**: B+C (per `PROMPT_CC_v11_4_v2_sprint_PHASE_B_C.md`)
**Branch**: `spec/liquidity-composite-v2.0`
**HEAD**: `ac6a245` (Phase A progress report, now pushed to origin)
**Authority requested**: Strategist (Claude AI) per master spec §0.5.4
**Halt reason**: Multiple substantive conflicts between the Phase B+C prompt's expected signatures and (a) the sealed pre-registration's actual mandates, (b) pre-existing implementations in the codebase. Per `PROMPT_CC_v11_4_v2_sprint_PHASE_B_C.md` §9 callback procedure + §10 stop conditions.

The prior session (Phase A) completed cleanly and is fully pushed (push receipt: `outputs/v2_sprint_phase_a_push_receipt.md`). The §1 BACKLOG.0 push of this Phase B+C session is **DONE** and verified. The callback halts work BEFORE §3 (Phase B.1 implementation), so the codebase is unchanged from `ac6a245`.

---

## Summary of conflicts (executive)

| # | Phase | Conflict | Severity | Section below |
|---|---|---|---|---|
| 1 | B.1 | `load_master` already exists in `src/ingest/master_archive.py:396` with a different signature (no `vintage` parameter) | **BLOCKER** | §A |
| 2 | B.1 | Sealed §3.2.2 mandates `load_master(series_id, vintage=t, fill="none")` but the actual master parquet schema (`[value, source, vintage, transform]`) records ONLY the retrieval timestamp — there is no ALFRED-style revision history to support "value as of date t" queries | **BLOCKER (data architecture)** | §B |
| 3 | B.2 | Prompt §4.1 specifies splices as "multiplicative" / "additive" with continuity gates `mean|δ|<0.5%` etc.; sealed §10.1 specifies different methods (YoY-growth-space / log-levels-space / z-score-blend) with different gates (`corr>0.50`, `corr>0.85`, `abs(funding_z.diff().max())<1.5σ`) | **METHOD MISMATCH** | §C |
| 4 | C.1 | Prompt §5.1 expects `min_window=60`; sealed §10.1 mandates `n ≥ 120` before non-NaN z-score | **METHOD MISMATCH** | §D |
| 5 | C.1 | Existing `compute_pit_zscore` in `src/quant_engine/mv_conditional.py:40` already implements PIT z-score (with `shift(1)` and `min_periods=60`) per PROMPT_v11_2 §3.2 | **DUPLICATION** | §D |
| 6 | C.1 | Existing `expanding_zscore` in `src/models/zscore.py:19` is also used by many call-sites (orchestrator_modeling, mrc_compute, mrc_v2, build_macro_risk, build_macro_charts) | **DUPLICATION** | §D |
| 7 | C.2 | Composite construction is genuinely new (no LC_FULL/LC_TIER2/LC_DEEP in current codebase), but the prompt §6.2 algorithm's "if any required component is NaN → composite NaN" rule needs Strategist confirmation against sealed §10.1's effective-start-date scheme | **CLARIFICATION NEEDED** | §E |

---

## §A — `load_master` already exists with a different signature

### Discovered

`buffet_indicator/src/ingest/master_archive.py:396` already has a working `load_master`:

```python
def load_master(
    series_id: str,
    *,
    start: str | None = None,
    end: str | None = None,
    frequency: Literal["D", "W", "M", "Q", "A"] | None = None,
    fill: Literal["none", "ffill", "interpolate"] = "none",
) -> MasterSeries:
```

- Returns a `MasterSeries` dataclass (`series_id`, `data`, `sources_used`, `earliest`, `latest`, `n_observations`).
- Has tests in `buffet_indicator/tests/ingest/test_master_archive.py`.
- Has 3+ in-tree call-sites: `src/models/orchestrator_modeling.py`, `src/transform/crestmont_compute.py`.

### Prompt §3.1 expected signature

```python
def load_master(
    series_id: str,
    start: pd.Timestamp | str | None = None,
    end: pd.Timestamp | str | None = None,
    vintage: pd.Timestamp | str = "latest",
    frequency: str | None = None,
    fill: str = "none",
) -> pd.Series:
```

Differences:
- **Target module**: prompt says `src/ingest/master.py`; existing is in `src/ingest/master_archive.py`.
- **Return type**: prompt says `pd.Series`; existing returns `MasterSeries` (dataclass).
- **`vintage` kwarg**: prompt has it (`"latest"` default); existing does NOT (would require backward-compatible addition).
- **Default schema validation**: prompt §3.2 expects `['date', 'value', 'source', 'vintage', 'frequency', 'transform']`; actual parquet schema is `[value, source, vintage, transform]` with `date` as index.

### Implementation plan (`outputs/v2_sprint_implementation_plan.json`)

The plan I wrote in Phase A says:

```json
"load_master": {
  "module_path": "buffet_indicator/src/ingest/master.py",
  "import_path": "src.ingest.master",
  "note": "load_master is from master spec, not in §11.1 explicitly; required for downstream functions"
}
```

I wrote this without realizing the existing implementation. The plan is therefore wrong on the module path — that is on me.

### Options for Strategist arbitration

**Option A1 — Extend existing in place** (recommended, minimal churn)
Add `vintage: pd.Timestamp | str = "latest"` as an optional kwarg to existing `master_archive.load_master`. Keep return type `MasterSeries`. Update plan to reflect `src/ingest/master_archive.py` as the canonical path. Existing call-sites continue to work (default `vintage="latest"` preserves current behavior).

**Option A2 — Create thin wrapper in `master.py`**
Add `src/ingest/master.py` re-exporting `load_master` from `master_archive`, plus a `load_master_series() -> pd.Series` adapter for callers that want a plain Series. The original `load_master` is untouched.

**Option A3 — New parallel implementation in `master.py`**
Add a new `load_master` in `src/ingest/master.py` with the `pd.Series`-returning, `vintage`-aware signature. Mark `master_archive.load_master` as deprecated. Migrate the 3 internal call-sites. (Largest blast radius — touches working code.)

**Option A4 — Use a different name**
Add new function `load_master_v2()` or similar in `src/ingest/master.py` while keeping existing function untouched. v2.0 code uses the new name; v1.x code is undisturbed.

**My recommendation**: A1. It is minimal-churn, backward-compatible, and the kwarg is purely additive. Existing call-sites that use `vintage="latest"` default get exactly the current behavior. v2.0 code can call with explicit `vintage=t` (subject to §B blocker below). However A1 still returns `MasterSeries`, not `pd.Series` — callers that need a Series do `.data` attribute access.

---

## §B — Vintage-data architecture gap (BLOCKER)

This is the larger of the two §A/§B blockers.

### What the sealed spec mandates

Sealed pre-reg §3.2.2 (lines 162-175):

> For every forecast origin `t`, component values are computed from records with release/vintage timestamp `≤ t`. For revisable FRED series (`M2SL`, `BUSLOANS`, `TOTLL`, `WALCL`, `WDTGAL`, and any other ALFRED-supported series), the consumption pattern is:
>
> ```python
> series = load_master(series_id, vintage=t, fill="none")  # MANDATORY
> # load_master(series_id, vintage="latest")  ← FORBIDDEN inside backtest loops
> ```
>
> Latest-vintage consumption is forbidden inside any code path that produces verdict-bearing artifacts.

And: "Every verdict JSON cell records `feature_vintage_max` and asserts `feature_vintage_max ≤ forecast_origin`. Failing this assertion at any cell raises `LookAheadViolation` and aborts the run."

### What the actual data supports

Current parquet schema (verified by `pd.read_parquet` of `walcl.parquet` etc.):

```
columns: [value, source, vintage, transform]
index:   date (DatetimeIndex)
```

For each (date, series), there is **one row with one vintage timestamp**. Example from `walcl.parquet`:

```
date         value     source       vintage
2002-12-18   719542.0  fred:WALCL   2026-05-22 16:26:28.303991
2002-12-25   732059.0  fred:WALCL   2026-05-22 16:26:28.303991
...
```

Every row's `vintage` is the timestamp when the ingestion pipeline fetched the data (2026-05-22), NOT the FRED release timestamp / ALFRED revision date. The schema does NOT support "what was the value of WALCL_2002-12-18 *as known on date t*" — there is no revision history per observation.

### Why this matters

Sealed §3.2.2 wants `vintage=t` to mean "the value as known to a forecaster who ran the model at time `t`" — i.e., ALFRED-style revision-aware lookups. The current data has no such information; the parquet records when the *current run* fetched the data.

A naive implementation would interpret `vintage=t` as "filter to rows with `df["vintage"] <= t`" — but `df["vintage"]` is the retrieval timestamp (uniform across all rows in a single run), so this filter would either return everything (if `t >= retrieval_time`) or nothing (if `t < retrieval_time`). It would not deliver the intended "as-of date `t`" semantics.

### Options for Strategist arbitration

**Option B1 — Redefine `vintage=t` semantics for v2.0**
Strategist amends "vintage" to mean "observation date `<= t`" (effectively `series.loc[:t]`). This is approximate (doesn't reflect post-release FRED revisions) but matches what the data supports. Codify the approximation in `load_master`'s docstring and in the verdict JSON's `feature_vintage_max` field documentation. The `LookAheadViolation` check then becomes `last_observation_date <= forecast_origin`, which the existing parquet schema supports.

**Option B2 — Build ALFRED-aware ingestion (new sub-sprint)**
Add a new ingestion path that records FRED release timestamps for each (date, series) tuple. Rebuild the master parquets with revision history. Implementation cost: significant. Schema impact: `[value, source, release_timestamp, observation_timestamp, transform]`. Re-running v1.0 verdict for parity comparison would require this.

**Option B3 — Document `vintage=t` as "best-effort approximation" + ship Option B1 now**
Same as B1 in code, but flag in `outputs/seal_report_v11_4.md` Appendix that v2.0's `vintage=t` is "release-vintage approximation = observation date" not true ALFRED revision-aware. Note the limitation in §13 (security/integrity) of the verdict JSON.

**Option B4 — Halt v2.0 sprint pending ALFRED-aware ingestion**
Block all verdict-bearing work until B2 lands. Most conservative; longest delay.

**My recommendation**: B1 (or B3 for full transparency). The data we have IS what was used for v1.0 (which produced a sealed verdict per §0.1). v2.0's deltas are methodological, not data-ingestion-level. Recording the approximation transparently (B3) is honest about the limitation without re-doing the data layer. If/when ALFRED-aware ingestion is built later, the v2.0 numbers can be re-run as a robustness check.

---

## §C — Splice-helper method mismatch

### What the prompt says (§4.1)

| ID | Source series | Splice date | Type |
|---|---|---|---|
| z3 BankLend | BUSLOANS → TOTLL | 1973-01-03 | level (multiplicative) |
| z5 FundingStress | TED → (SOFR − IORB) | 2022-01-22 | rate (additive) |
| z4 DXY_inv | ICE_DXY → DTWEXBGS | 2006-01-04 | level (multiplicative) |

Prompt §4.2 algorithm: compute median(s_new / s_old) (multiplicative) or median(s_new - s_old) (additive) over ±30-day overlap; validate `mean|δ| < 0.5%, max|δ| < 2%` for level series; `mean|Δ| < 0.05pp, max|Δ| < 0.20pp` for rates.

### What the sealed spec says (§10.1)

| ID | Splice | Space | Method | Validation gates |
|---|---|---|---|---|
| z3 | BUSLOANS↔TOTLL @ 1973-01-03 | YoY growth-rate space | additive constant `c` | `corr > 0.50` AND `abs(c) < 0.05` |
| z4 | ICE DXY ↔ DTWEXBGS @ 2006-01-04 | log-levels space | additive constant `c` | `corr > 0.85` AND `mean abs z-divergence < 0.30` |
| z5 | TED ↔ SOFR−IORB @ 2022-01-22 | z-score linear-blend (Feb 2022 → Apr 2023, 14-month transition) | n/a | `abs(funding_z.diff().max()) < 1.5σ` |
| z5 (pre-step) | IOER → IORB level concat @ 2021-07-29 | level (no splice) | n/a | `abs(IOER@2021-07-28 − IORB@2021-07-29) < 0.01pp` |

The dates match the prompt; the methods do NOT.

- **z3**: sealed says YoY-growth-space additive constant, NOT level multiplicative.
- **z4**: sealed says log-levels-space additive constant, NOT raw-level multiplicative.
- **z5**: sealed says 14-month z-score blend, NOT a point-additive splice; plus a pre-step IOER→IORB level concat that the prompt doesn't mention.

### Options for Strategist arbitration

**Option C1 — Implement per sealed §10.1** (recommended)
Follow the sealed spec verbatim. The prompt's "multiplicative/additive" framing is a working summary that doesn't match the actual methods. Each splice gets its own implementation reflecting its space (growth-rate / log-levels / z-blend) and validation gates.

**Option C2 — Implement per prompt §4.2 and document the deviation**
Risk: the resulting series would not match v1.0's spliced series; v2.0 verdict would be on inputs that aren't what was pre-registered. **Not recommended** — would violate the sealed pre-registration.

**My recommendation**: C1. The sealed spec is authoritative.

---

## §D — PIT z-score conflicts

### What the prompt says (§5.1)

```python
def pit_zscore(
    series: pd.Series,
    min_window: int = 60,
    method: Literal["expanding", "rolling"] = "expanding",
    rolling_window: int | None = None,
) -> pd.Series:
```

Prompt §5.2 algorithm: "Window: `series.loc[:t]` (all observations through `t`, inclusive)".

### What the sealed spec says (§10.1)

> **Z-score definition** (expanding-window, PIT-compliant) — verbatim from v1.0 §1.4: expanding window, mean + sample SD (Bessel n−1), strict PIT excluding current observation; minimum sample threshold **n ≥ 120** observations before non-NaN z; all components brought to month-end-of-month frequency before z-scoring; real-time vintages (ALFRED) for revisable series M2SL, BUSLOANS, TOTLL, WALCL, WDTGAL.

Conflicts:
- `min_window`: prompt 60 vs sealed 120.
- Inclusive `:t` vs `strict PIT excluding current observation` (i.e., `shift(1)` so window at `t` is `data[:t-1]`).
- Prompt allows `method="rolling"`; sealed says expanding only.

### What existing code does

`src/quant_engine/mv_conditional.py:40` already has:

```python
def compute_pit_zscore(series: pd.Series, min_periods: int = 60) -> pd.Series:
    """Expanding-window z-score with ``.shift(1)`` PIT discipline."""
    shifted = series.shift(1)
    mu = shifted.expanding(min_periods=min_periods).mean()
    sd = shifted.expanding(min_periods=min_periods).std()
    return (shifted - mu) / sd
```

This matches the sealed spec EXCEPT min_periods default (60 vs sealed 120).

`src/models/zscore.py:19` has `expanding_zscore` (used by ~6 sites: orchestrator_modeling, mrc_compute, mrc_v2, build_macro_risk, build_macro_charts).

### Options for Strategist arbitration

**Option D1 — Add v2.0-specific helper with sealed defaults** (recommended)
Add `pit_zscore` in `src/transform/pit_zscore.py` per the sealed spec:
- `min_window: int = 120` (sealed default)
- expanding only (no rolling option)
- `shift(1)` strict PIT semantics

Keep existing `compute_pit_zscore` and `expanding_zscore` untouched (they have their own callers). v2.0 code imports the new `pit_zscore`.

**Option D2 — Reuse existing `compute_pit_zscore` with explicit `min_periods=120`**
Add a thin v2.0 wrapper that calls `compute_pit_zscore(series, min_periods=120)`. Minimal new code.

**Option D3 — Migrate everything to a unified `pit_zscore`**
Change all 7+ call-sites. Big blast radius.

**My recommendation**: D1. New module under `src/transform/` (or `src/stats/`) with v2.0-canonical defaults. Leaves existing code untouched.

---

## §E — Composite construction (clarification needed)

The sealed spec at §10.1 gives canonical scope weights:

| Scope | Effective monthly start | Components and weights |
|---|---|---|
| LC_FULL | 2003-01 | z1=+0.25, z2=+0.20, z3=+0.20, z4=+0.20, z5=−0.15 (sum abs = 1.00) |
| LC_TIER2 | 1987-01 | z2=+0.267, z3=+0.267, z4=+0.267, z5=−0.200 |
| LC_DEEP | 1973-01 | z2=+0.333, z3=+0.333, z4=+0.333 |

The prompt §6.2 says: "If any required component is NaN → composite at `t` is NaN (do NOT fall back to fewer components; preserves scope semantics)."

This is reasonable per the scope-fixed weight scheme. But the sealed spec's "effective monthly start" dates suggest that BEFORE the scope start date, the composite is undefined — that is, LC_FULL is NaN before 2003-01 even if all components are non-NaN earlier (which they typically aren't at the LC_FULL combination, but LC_DEEP starts in 1973-01 because BankLend(z3) starts then).

**Clarification request**:
1. Confirm that composite NaN propagation per the prompt §6.2 is correct (any missing input → NaN out).
2. Confirm that the effective-start dates are policy, not inherent — i.e., LC_FULL @ 2002-12 returns NaN by policy even if z1..z5 were available.
3. Confirm that LC_TIER2 weights `{z2, z3, z4, z5}` actually sum to `0.601` (= 0.267×3 − 0.200) — is this intentional (z5's negative weight does not get its absolute value into the sum-1 normalization), or did v1.0 actually use sum-of-absolute-values = 1.00 normalization? The sealed text says "renormalized {0.267, 0.267, 0.267, −0.200}" without explaining the renormalization basis.

(Same kind of arithmetic question for LC_DEEP: weights sum to 1.0 cleanly, no issue.)

---

## What I've already done this session (and what I have NOT done)

### Done

1. §1.1–§1.3 push of prior 6 commits: ✅ DONE and verified.
   - Remote at `ac6a245`.
   - Seal tag `v11.4-prereg-sealed` still resolves to `2a94417` (unchanged).
2. Push receipt written to `outputs/v2_sprint_phase_a_push_receipt.md` (not yet committed; will be bundled in the next commit).
3. §2 sealed pre-reg SHA-256 re-verified: `c3c3ec1a…` unchanged ✅.
4. Diagnostic reads of the existing codebase: `master_archive.load_master`, `mv_conditional.compute_pit_zscore`, `models/zscore.expanding_zscore` — all identified as pre-existing.
5. Inspection of actual master parquet schema (e.g., `walcl.parquet`) — confirmed `[value, source, vintage, transform]` with date as index and vintage = retrieval timestamp (not ALFRED revision).
6. Read of sealed pre-reg §1, §3.2, §4, §5, §10.1 to scope all Phase B/C conflicts.

### NOT done

- §3 Phase B.1 `load_master` implementation: **HALTED before any code change** pending arbitration.
- §4 Phase B.2 splice helpers: HALTED.
- §5 Phase C.1 PIT z-score: HALTED.
- §6 Phase C.2 composites: HALTED.

The working tree has NO modifications to tracked code from this session. Only two new files are untracked at this point: this callback file and the push receipt.

---

## Requested resume directive

Please issue a resume prompt addressing the seven conflicts above. Suggested structure:

```
RESOLVED:
  §A load_master module path: <A1|A2|A3|A4>
  §B vintage semantics:       <B1|B2|B3|B4>
  §C splice methods:          <C1|C2>
  §D PIT z-score:             <D1|D2|D3>
  §E composite arithmetic:    <CONFIRM E.1 / E.2 / E.3 per §E above>

Continue from §3 of PROMPT_CC_v11_4_v2_sprint_PHASE_B_C.md using the above
resolutions. The implementation plan should be updated to reflect:
  - load_master canonical module path:  <PATH>
  - PIT z-score canonical module path:  <PATH>
  - splice helpers canonical module path: <PATH>
  - composite construction canonical module path: <PATH>
```

---

## Operational notes

- This callback is being committed in the same change as `outputs/v2_sprint_phase_a_push_receipt.md` (which §3.6 of the Phase B+C prompt instructed to bundle with the next commit; since §3 was halted, it bundles with this callback instead — owner can re-bundle in the resume commit if preferred).
- The push of this callback commit follows the `auto_push: true` default per master spec §1.6.3.
- TDD discipline is preserved: NO scaffolded tests have been touched. The 1/21 passing (T15 hard_gate) and 20/21 failing baseline is unchanged.
- Per §10 stop conditions, halting here on a methodology question is the correct action.

— Claude Code, v2.0 sprint Phase B+C callback @ 2026-05-25T12:42:12Z
