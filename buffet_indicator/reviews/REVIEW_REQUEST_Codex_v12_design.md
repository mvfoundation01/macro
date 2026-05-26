# REVIEW_REQUEST_Codex_v12_design.md

> **Audience**: Codex / ChatGPT 5.5 Codex (empirical execution + code review per master spec §0.5)
> **Author**: Strategist (Claude AI) on behalf of the project owner
> **Scope**: (1) Code review of Phase B-E implementations (v11.4 sprint), (2) Empirical execution of v12 candidate component analyses, (3) Library-version sensitivity verification
> **NOT in scope**: methodology debate (parallel request goes to ChatGPT 5.5 Pro — see `REVIEW_REQUEST_ChatGPT55Pro_v12_design.md`)
> **Response format**: severity-tagged comments per §14 below; empirical results in markdown tables with code

---

## §0 — Why we need YOU specifically

ChatGPT 5.5 Pro is being asked methodology questions in a parallel request. Methodology questions can be answered through argument and literature citation.

Your role is different: you can EXECUTE code, RUN actual statistical tests on real FRED data, and VERIFY claims about library behavior. The owner has 6+ years of FRED API access; Strategist has provided manifests; you can pull and analyze.

**What we need from you**:
1. **Code review** of Phase A-E implementations (sanity-check the engineering)
2. **Empirical execution** on candidate v12 components (ADF/KPSS/autocorrelation tests)
3. **Library-version sensitivity** verification (does `arch==7.0.0` vs `arch==8.0.0` produce byte-identical verdict?)
4. **Data quality assessment** for proposed v12 series (M3 OECD reconstruction, M2V quarterly→monthly interpolation)

This is execution-heavy work. Strategist cannot do it from inside its container. You can.

---

## §1 — Context (abbreviated; full methodology context in ChatGPT 5.5 Pro request)

### §1.1 — Sprint arc, in one paragraph

The v11.x sprint arc tested macro/liquidity composites for equity return prediction across 3 increasingly rigorous pre-registered iterations: v11.2.0-stat (MRC) FAIL, v11.3.0 (LC v1.0) FAIL, v11.4 (LC v2.0) FAIL. All three were sealed pre-registrations with multi-round reviewer corroboration. The v2.0 verdict (1/7 criteria pass) is documented in `outputs/lc_v2_verdict.json` (SHA-256 `84a457e3f47f5ad5e11f8fc2f86adf03ea25e30fead4a99c084e99ccfa6d4180`). The verdict is FINAL and sealed.

### §1.2 — Why v2.0 FAILed

Two failure modes:
- **Mode A**: 4 of 7 criteria → `NOT_EVALUABLE_COUNTED_FAIL` because z4 (DXY) data bottleneck pushed composite valid-start to 2016-01, leaving OOS window too short for sealed §3.4 gate (`n_obs_oos < max(60, 3·HAC_lag) OR n_eff < 30`).
- **Mode B**: C5 → `FAIL_STATISTICAL` because z4 has max ADF p ≈ 0.7648 (non-stationary at conventional levels).

Both modes are driven by z4 being a LEVEL transformation (log-DXY) rather than rate-of-change (Δlog-DXY).

### §1.3 — The v12 design question

Owner's intuition: convert level-family components (z1, z4) to rate-of-change family; potentially add velocity variables (M2V, M3 YoY).

Strategist enumerated 7 candidate v12 designs (v12-A through v12-G, see ChatGPT 5.5 Pro request §3). The most likely contender is **v12-A**: same 5 components, all converted to rate-of-change.

YOUR JOB: empirically assess whether this is technically feasible AND whether the candidate transformations actually have the predicted properties (stationarity, longer effective history, sensible cross-correlations).

---

## §2 — Code review request (Phase A-E)

### §2.1 — Modules to review (in priority order)

| Priority | Module | Purpose |
|---|---|---|
| **HIGH** | `src/models/v2_panel_builder.py` | Phase E.1 — builds 12-cell panel with PIT vintage discipline |
| **HIGH** | `src/models/predictive_regression_v2.py` | Phase D.3 — composes HAC NW + Stambaugh + skewed-t + bootstrap |
| **HIGH** | `src/models/v2_criteria.py` | Phase D2 — evaluates 7 criteria + binary verdict |
| **MEDIUM** | `src/transform/composite.py` | Phase C.2 — LC_FULL/LC_TIER2/LC_DEEP construction |
| **MEDIUM** | `src/transform/splice.py` | Phase B.2 — 4 splice helpers per sealed §10.1 |
| **MEDIUM** | `src/transform/pit_zscore.py` | Phase C.1 — strict-shift PIT z-score |
| **MEDIUM** | `src/stats/bootstrap.py` | Phase D.1 — stationary block bootstrap (50K immutable) |
| **MEDIUM** | `src/stats/skewt.py` | Phase D.2 — Hansen 1994 conditional skewed-t fit |
| **LOW** | `src/stats/hac.py`, `sample_gate.py`, `stambaugh.py`, etc. | Phase D.1 utilities |

All in `https://github.com/mvfoundation01/macro/tree/spec/liquidity-composite-v2.0/buffet_indicator/src`.

### §2.2 — Specific code review questions

**CR-1**: In `src/models/v2_panel_builder.py`, does the panel construction correctly enforce PIT vintage at each forecast origin? Specifically:
- Is `load_master(vintage=t)` called for every component at every origin?
- Is the strict-shift PIT z-score (n≥120 prior observations excluding current) verified at every cell?
- Are there any code paths where data observation-dated AFTER `t` could leak into the composite at origin `t`?

The audit at §7 of Phase E reported 0 violations. Please cross-check by reading the code, NOT just trusting the audit.

**CR-2**: In `src/models/predictive_regression_v2.py`, does the OOS R² computation match Goyal-Welch (2008)?
- Numerator: `MSE_model` (forecast errors from in-sample-estimated model applied to OOS)
- Denominator: `MSE_benchmark` (forecast errors from prevailing mean on the OOS sample, computed expanding)
- `R²_OOS = 1 - MSE_model / MSE_benchmark`

Specifically, is the prevailing-mean benchmark computed correctly (rolling expanding through OOS) rather than a fixed in-sample mean?

**CR-3**: In `src/stats/bootstrap.py`, verify `n_bootstrap=50000` is hard-coded immutable (not a configurable kwarg). Sealed §3.8 specifies IMMUTABLE; the function should raise if a caller attempts to override.

**CR-4**: In `src/stats/skewt.py`, verify the Gaussian fallback gate is exactly per sealed §3.7:
- `n_resid < 120` OR
- `sigma_hat <= 1e-12` OR
- fewer than 20 unique rounded residuals OR
- any non-finite residual

Strategist mistake #5 was about the SkewStudent loglikelihood API call. Please re-verify the actual API usage matches the empirically-correct signature you confirmed in Round 3.

**CR-5**: In `src/transform/splice.py`, verify the 4 splice helpers match sealed §10.1 verbatim:
- `splice_busloans_totll_yoy` — YoY-growth-space additive constant; gates `corr>0.50 AND abs(c)<0.05`
- `splice_icedxy_dtwexbgs_log` — log-levels-space additive constant; gates `corr>0.85 AND mean|z-divergence|<0.30`
- `concat_ioer_iorb` — level concat 2021-07-29; gate `abs(IOER@2021-07-28 - IORB@2021-07-29) < 0.01pp`
- `splice_ted_sofr_iorb_zblend` — 14-month z-blend Feb 2022 → Apr 2023; gate `abs(funding_z.diff().max())<1.5σ`

Are the implementations exactly as sealed specifies, or are there silent variations?

**CR-6**: In `src/transform/composite.py`, verify the weight normalization:
- LC_FULL: `Σ|w| = 1.00` (z1=+0.25, z2=+0.20, z3=+0.20, z4=+0.20, z5=−0.15)
- LC_TIER2: `Σ|w| ≈ 1.001` (z2=+0.267, z3=+0.267, z4=+0.267, z5=−0.200)
- LC_DEEP: `Σ|w| ≈ 0.999` (z2=+0.333, z3=+0.333, z4=+0.333)

NOT `Σw = 1`. Strategist had to arbitrate this in §E of Phase B+C callback.

**CR-7**: Performance review — is the panel construction performant? Should be O(n_origins × 5 components) without quadratic re-computation. Verify caching / vectorization.

**CR-8**: Test coverage — `pytest --cov=src` should show ≥90% per master spec §1.6.6. Verify and flag uncovered branches in production code.

---

## §3 — Library version sensitivity (THE critical Phase F-preview)

Phase D methodology note 7 stated that the API surfaces of `arch.bootstrap.optimal_block_length` and `arch.univariate.SkewStudent.loglikelihood` are unchanged from `arch==7.0.0` to `arch==8.0.0`. But this does NOT guarantee byte-identical numerical output.

### §3.1 — Critical sensitivity test

Please run the following and report:

```bash
# In a fresh virtualenv, install SEALED-PINNED versions
pip install arch==7.0.0 pandas==2.2.3 numpy==1.26.4 scipy==1.13.1 statsmodels==0.14.2

# Re-run the verdict pipeline
cd buffet_indicator
python -m src.models.v2_verdict_run --data-cutoff 2026-03-31 --n-bootstrap 50000 --seed 42 --output /tmp/lc_v2_verdict_pinned.json

# Compare to current (installed-versions) verdict
diff /tmp/lc_v2_verdict_pinned.json buffet_indicator/outputs/lc_v2_verdict.json

# Compute SHA-256
sha256sum /tmp/lc_v2_verdict_pinned.json buffet_indicator/outputs/lc_v2_verdict.json
```

**Report**:
- Byte-identical? Same SHA-256?
- If not: which fields differ? Is the difference numerical (precision) or structural (e.g., one library reports more decimals)?
- Does the FAIL verdict outcome change?
- Do any criterion status codes change (PASS / FAIL / NOT_EVALUABLE)?

This is THE critical Phase F-preview check. If pinned re-run produces different verdict, the v2.0 verdict's claim is weaker.

### §3.2 — Library-specific risk areas

For each, please test under both `arch==7.0.0` and `arch==8.0.0` and report differences:

| Surface | Test |
|---|---|
| `arch.bootstrap.optimal_block_length` | Returns same column names? Same numerical values for synthetic AR(1) ρ=0.5 series? |
| `arch.bootstrap.StationaryBootstrap` with seed=42 | Same draw sequence? Same statistic across 50K reps? |
| `arch.univariate.SkewStudent.loglikelihood(parameters, resids, sigma2, individual=False)` | Same numerical value for synthetic standardized residuals? |
| `statsmodels.OLS(...).fit(cov_type='HAC', cov_kwds={'maxlags': k})` | Same SE for same input? |
| `statsmodels.tsa.stattools.adfuller(autolag='AIC')` | Same p-value? |

Critically: are any of these surfaces tied to `numpy.random` state that may have changed across versions?

---

## §4 — Empirical execution for v12 candidate components

The Strategist proposes converting z1 and z4 from level to rate-of-change for v12-A. We need empirical confirmation that:
1. The rate-of-change versions have longer effective history
2. They actually pass ADF
3. They don't introduce new collinearity issues

Plus: we need to assess the proposed velocity/M3 additions.

### §4.1 — Candidate v12-A components (transform existing 5)

For EACH of the following, please pull data from FRED and compute the statistics in §4.4 below:

| Component | Sealed v2.0 (current) | v12-A candidate (proposed) |
|---|---|---|
| z1 NetFed | LEVEL of `WALCL - WDTGAL - RRPONTSYD` (weekly, USD billions) | **`Δ12 log(WALCL - WDTGAL - RRPONTSYD)`** (12-month log change, weekly→monthly) |
| z2 M2 | `Δ12 log(M2SL)` already | **Δ12 log(M2SL)** unchanged |
| z3 BankLend | `Δ12 log(BUSLOANS→TOTLL spliced)` already | unchanged |
| z4 DXY | log-LEVEL of `DTWEXBGS` (or ICE_DXY if available) | **Δ12 log(DTWEXBGS)** YoY rate of change |
| z5 FundingStress | TED→SOFR-IORB z-blend (already rate-like) | unchanged |

### §4.2 — Candidate v12 ADDITIONS (velocity / M3 family)

Owner's specific intuition. Please also assess:

| Candidate | FRED Series | Frequency | Theoretical role |
|---|---|---|---|
| z6 M2V | `M2V` | Quarterly (interpolate to monthly?) | Money velocity / demand residual |
| z7 M3 YoY | `MABMM301USM189S` (OECD) | Monthly | Broader money aggregate growth (M3 reconstructed) |
| z6b Monetary base velocity | derived: nominal GDP / `BOGMBASE` | Quarterly | Pre-/post-2008 comparison |
| z6c Real money growth | derived: `Δ12 (M2SL / CPIAUCSL)` | Monthly | Inflation-adjusted liquidity |
| z6d Money multiplier | derived: `M2SL / BOGMBASE` | Monthly | Fractional-reserve credit creation |

For each: data history depth, gaps, units, frequency.

### §4.3 — Specific data quality questions

**EE-1**: M3 (`MABMM301USM189S`):
- What's the earliest available date?
- Are there gaps in the series?
- US Fed discontinued official M3 reporting in 2006. Does OECD's reconstruction span 2006 cleanly, or is there a methodology break?
- Is the OECD series revised retroactively (vintage concerns)?

**EE-2**: M2V (`M2V`):
- What's the underlying construction? (Should be `GDP / M2SL`.)
- Frequency: quarterly. What's the legitimate way to use this in a MONTHLY composite?
  - Option A: forward-fill (step function) — preserves vintage but creates artificial discontinuities
  - Option B: linear interpolation — smoother but introduces look-ahead UNLESS we shift by 1 quarter
  - Option C: use as quarterly variable in a quarterly-frequency v12 composite — most defensible but changes pipeline frequency

**EE-3**: ICE_DXY availability:
- Is the historical ICE_DXY series available from FRED or any free source? (If yes, this would resolve the z4 bottleneck even WITHOUT switching to rate-of-change.)
- TradingView Premium "TVC:DXY" has deep history but is manual export.

### §4.4 — Statistics to compute per candidate

For each candidate (transformed v2.0 components + v12 additions), please compute:

```python
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.regression.linear_model import OLS

# Pull series from FRED
series = fetch_fred_series(symbol)  # whatever your wrapper is

# 1. Basic stats
start_date = series.first_valid_index()
end_date = series.last_valid_index()
n_obs = series.dropna().shape[0]
freq = pd.infer_freq(series.index)
n_gaps = series.isna().sum()

# 2. Stationarity
adf_stat, adf_p, *_ = adfuller(series.dropna(), autolag='AIC', regression='c')
kpss_stat, kpss_p, *_ = kpss(series.dropna(), regression='c', nlags='auto')

# 3. Autocorrelation
acf_lag1 = series.autocorr(lag=1)
acf_lag12 = series.autocorr(lag=12)

# 4. AR(1) coefficient (proxy for ρ̂ for Stambaugh trigger)
y = series.dropna().iloc[1:].values
x = series.dropna().iloc[:-1].values
rho_hat = OLS(y, x).fit().params[0]

# 5. Correlation with realized SPXTR forward returns (12M, 36M, 60M)
spxtr = fetch_fred_series('SP500TR')  # or your total-return source
for h_years in [1, 3, 5]:
    spxtr_forward = spxtr.pct_change(h_years * 12).shift(-h_years * 12)
    aligned = pd.concat([series, spxtr_forward], axis=1).dropna()
    corr = aligned.corr().iloc[0, 1]
    # report

# 6. Cross-correlation with v2.0 components (z1, z2, z3, z4, z5)
# For each existing component, compute correlation. Flag if abs > 0.7.
```

### §4.5 — Output format (per candidate)

Please report results as a markdown table:

```markdown
## Candidate: z4_rate = Δ12 log(DTWEXBGS)

| Statistic | Value | Pass criterion? |
|---|---|---|
| start_date | YYYY-MM-DD | (vs v2.0 z4 2006-01-01) |
| end_date | YYYY-MM-DD | |
| n_obs | int | (vs v2.0 z4 ~245) |
| ADF p-value | float | <0.05 (PASS/FAIL) |
| KPSS p-value | float | >0.10 (PASS/FAIL stationarity null) |
| acf_lag1 | float | |
| AR(1) ρ̂ | float | <0.85 (Stambaugh trigger threshold) |
| corr w/ SPXTR 12M forward | float | |
| corr w/ SPXTR 36M forward | float | |
| corr w/ SPXTR 60M forward | float | |
| corr w/ v2.0 z1 | float | |
| corr w/ v2.0 z2 | float | |
| corr w/ v2.0 z3 | float | |
| corr w/ v2.0 z5 | float | |

**Interpretation** (1-2 sentences): is this candidate better/worse than v2.0 z4 for our purposes?
```

Repeat for all 9 candidates (5 transformed + 4 velocity/M3 additions).

### §4.6 — Joint-history matrix (CRITICAL for v12 panel-construction feasibility)

For all 9 candidates AS A SET, compute:

```python
# Stack into a DataFrame
df = pd.concat([z1_rate, z2_rate, z3_rate, z4_rate, z5, m2v, m3_yoy, base_v, real_money], axis=1)

# Joint-history start date (the latest first_valid_index across all)
joint_start = df.dropna(how='any').index[0]

# Without z6 M2V (if quarterly is problematic)
df_no_m2v = df.drop(columns=['m2v'])
joint_start_no_m2v = df_no_m2v.dropna(how='any').index[0]

# Variance Inflation Factor on the joint panel
from statsmodels.stats.outliers_influence import variance_inflation_factor
vif = pd.Series({
    col: variance_inflation_factor(df.values, i)
    for i, col in enumerate(df.columns)
})

# Max VIF (sealed §5.6 threshold = 5.0)
max_vif = vif.max()
```

**Report**:
- Joint history start date (with and without M2V)
- Max VIF
- Which pairs have correlation > 0.7? (flag potential redundancy)

This determines v12 panel feasibility. If joint history starts post-2010 with all 9 candidates included, we have the same data-window problem as v2.0.

### §4.7 — Simulation: v12-A reconstruction with rate-of-change

If time permits, please run a quick simulation of v12-A:
- Replicate v2.0 panel-builder but substitute z1, z4 with their rate-of-change versions
- Build LC_FULL/LC_TIER2/LC_DEEP composites
- Compute joint-history start dates per scope
- Compute ADF on each component (would C5 still fail?)
- Compute valid OOS window length per scope × horizon (would C1-C4 still NOT_EVALUABLE?)

This is EXPLORATORY only — NOT a verdict-bearing run for v12. We're just asking: does v12-A obviously fix the failure modes, or are there other constraints?

**Caveat**: this exploration must NOT inform v12 pre-registration AT ALL. The owner is committed to pre-registering v12 BEFORE seeing v12 candidate data. So this is purely a feasibility check — "is v12 worth pursuing at all" — not a hypothesis-development tool.

---

## §5 — Specific empirical questions

### §5.1 — Bootstrap determinism

**EQ-1**: With `random_state=42` and `n_bootstrap=50000`, does `arch.bootstrap.StationaryBootstrap` produce identical draw sequences across:
- (a) `arch==7.0.0` vs `arch==8.0.0`?
- (b) `numpy==1.26.4` vs `numpy==2.4.4`?
- (c) Different OS / architecture?

If (a) or (b) flip, the verdict JSON byte-identity claim is violated.

### §5.2 — SkewStudent fitting robustness

**EQ-2**: For the v2.0 verdict, which cells used `family="skewed_t"` vs `family="gaussian_fallback"`? Report counts per scope.

If most cells fell back to Gaussian, the Amendment 3 (Hansen 1994 skewed-t) addition didn't meaningfully change v2.0 from v1.0's distributional assumption. Worth understanding for v12 design.

### §5.3 — ADF lag selection sensitivity

**EQ-3**: C5 (ADF) used `autolag='AIC'`. If we use `autolag='BIC'` or `autolag='t-stat'` or fixed `maxlag=12`, do the per-component p-values change materially? Especially for z4 (max p ≈ 0.7648) — is the result robust to lag selection?

### §5.4 — Cell-level inspection of NOT_EVALUABLE failures

**EQ-4**: For each of the 4 NOT_EVALUABLE cells (C1-C3 LC_TIER2 × {1Y, 3Y, 5Y}; C4 LC_FULL × any), please report:
- Actual `n_obs_oos`
- Actual `n_eff` (HAC-adjusted)
- Sealed §3.4 gate thresholds applied
- Which gate triggered: `n_obs_oos < max(60, 3·HAC_lag)` or `n_eff < 30`?

If most cells were narrowly NOT_EVALUABLE (e.g., n_obs_oos = 58 when threshold is 60), that's different from being deeply NOT_EVALUABLE (n_obs_oos = 8). Worth understanding for whether extension wait (v12-F) might fix v2.0 without redesign.

### §5.5 — VIF deeper check

**EQ-5**: C6 reported max VIF ≈ 1.70 (PASS). Please report VIF per component (not just max). If z1 VIF is 1.05 and z3 VIF is 1.65, that tells a different story than uniform 1.4 across all components.

Also: VIF was computed on which date range? LC_FULL-aligned (2016-01 onward) or full available panel? This determines what VIF the v12 candidates need to beat.

### §5.6 — Forward return sanity check

**EQ-6**: Please verify the SPXTR forward return computation:
- For origin 2010-01-31 with h=5Y, what's the realized total return?
- Compare to a known source (Yahoo Finance SPXTR or similar) — does the v2.0 pipeline match?

If forward returns are wrong, ALL regression cells are corrupted regardless of methodology.

---

## §6 — Specific code-quality flags (please look for these)

Strategist suspects the following may exist but cannot verify from inside container:

**CQ-1**: Any silent `try/except` blocks that catch numerical errors and substitute NaN? (Would mask real bugs.)

**CQ-2**: Any uses of `pd.DataFrame.iloc[-1]` that assume the last index is the latest? (PIT discipline violation if data is unsorted.)

**CQ-3**: Any global mutable state (module-level dicts, caches) that could leak across cells?

**CQ-4**: Any use of `numpy.random` (the legacy API) instead of `numpy.random.default_rng(seed)` (the modern API)? Master spec §8.3 requires the modern API.

**CQ-5**: Any tests that pass-by-tautology (e.g., assertEqual(x, x))? Always flag.

**CQ-6**: Test isolation — do tests share global state? Run with `pytest --randomly-seed` if installed; report flakiness.

---

## §7 — What to do if you find a BLOCKER

A BLOCKER would be: a discovered bug in Phase A-E that materially affects the v2.0 verdict.

**If found**:
- DO NOT modify the v2.0 verdict (sealed and final).
- DO file the finding with reproduction steps.
- Strategist will decide whether to:
  - (a) Issue a v2.0 amendment with explanation (sealed pre-reg permits amendments before verdict; this would be retrospective)
  - (b) Document as "known limitation; affects v12 design" in §6.4 meta-DECISIONS
  - (c) Accept the bug as part of the v2.0 record (rigor: even bugs in sealed code are sealed)

This is for Strategist + Owner to decide, not for you. But your discovery is essential.

---

## §8 — Pre-commitments

Whatever your review finds:

1. **No retroactive amendment of v2.0 verdict** unless a true BLOCKER is found (then handled per §7).
2. **No silent updates to sealed artifacts.** All amendments through DECISIONS log.
3. **Your authorship is documented** in v12 pre-reg (if pursued) or in meta-DECISIONS (if not).
4. **Empirical findings will inform v12 design** but are NOT v12-binding (pre-registration discipline preserved).

---

## §9 — Time budget guidance

Please prioritize:

| Task | Estimated effort | Priority |
|---|---|---|
| §3 Library-version sensitivity (pinned re-run + SHA compare) | 30-60 min | **CRITICAL** |
| §4 v12-A candidate component statistics (5 transformed) | 60-90 min | HIGH |
| §4 v12 velocity additions (4 candidates) | 60-90 min | HIGH |
| §4.6 Joint-history feasibility matrix | 30 min | HIGH |
| §5 Specific empirical questions (EQ-1 through EQ-6) | 60-90 min | MEDIUM |
| §2 Code review (Phase A-E modules) | 90-180 min | MEDIUM |
| §4.7 v12-A reconstruction simulation | 60-90 min | LOW (only if §3-§5 are completed) |

Total: **~6-12 hours** of empirical work. Take what time you need. Quality > speed.

---

## §10 — Parallel review

A separate methodology request goes to ChatGPT 5.5 Pro (`REVIEW_REQUEST_ChatGPT55Pro_v12_design.md`) asking:
- Post-hoc selection critique of v12 designs
- Multiple-testing correction across iterations
- Literature on rate-of-change vs level for equity prediction
- Whether 3-of-3 FAIL is enough to retire the research program
- Publication strategy for null findings

Your empirical execution + their methodology guidance together will inform §6.4 meta-DECISIONS authorship.

---

## §11 — Artifacts available for your reference

All in `https://github.com/mvfoundation01/macro/tree/spec/liquidity-composite-v2.0/buffet_indicator/`:

| Artifact | Path | SHA-256 |
|---|---|---|
| Sealed v2.0 pre-reg | `specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` | `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` |
| v2.0 verdict JSON | `outputs/lc_v2_verdict.json` | `84a457e3f47f5ad5e11f8fc2f86adf03ea25e30fead4a99c084e99ccfa6d4180` |
| Vintage approximation note | `../outputs/v2_sprint_vintage_approximation_note.md` | (no hash; informational) |
| Source modules | `src/models/`, `src/transform/`, `src/stats/`, `src/ingest/` | reviewable |
| Tests | `tests/` | 21/21 §11.2 + 538 broader |

If you cannot pull from GitHub, request specific files in your reply and Strategist will paste.

---

## §12 — Recommended workflow for your session

1. Read this prompt entirely first. Identify your time budget.
2. Start with §3 (library-version sensitivity) — this is the most consequential single check.
3. If §3 passes (byte-identical verdict under pinned versions), proceed to §4 empirical execution.
4. If §3 fails (verdict differs under pinned versions), STOP and report — this changes everything.
5. §2 code review can be interleaved with §4 (alternating focus).
6. §5 empirical questions can fill remaining time.
7. Output: a single response containing all findings, organized per §14 format.

---

## §13 — On asymmetry of effort

Strategist acknowledges this is a heavy ask. Two mitigations:

1. **Parallel structure**: most §4 candidate-component analyses are independent and can be run via a single batched script. Don't run 9 separate Jupyter sessions.

2. **Acceptable partial responses**: if time-constrained, prioritize §3 (library sensitivity) > §4.6 (joint-history feasibility) > §4 individual candidates > §2 (code review). Anything beyond §3 + §4.6 is valuable but not strictly required for v12 go/no-go decision.

If §3 alone shows pinned re-run mismatch, that's enough — STOP and report.

---

## §14 — Response format

Per master spec §0.5.3 with empirical extensions:

| Tag | Meaning | When to use |
|---|---|---|
| `BLOCKER` | Bug or finding that invalidates v2.0 verdict | If found in code review or pinned re-run |
| `MAJOR` | Significant finding affecting v12 design | E.g., M3 OECD methodology break detected |
| `MINOR` | Nice-to-fix, doesn't change conclusions | Style, performance, edge case |
| `NIT` | Cosmetic | |
| `EMPIRICAL` | A data result (table, p-value, correlation) | All §4 outputs |
| `RECOMMEND` | Suggested action for v12 design or meta-DECISIONS | E.g., "M2V quarterly interpolation should be option C" |
| `LITERATURE` | Reference to a paper/source | (if relevant; ChatGPT 5.5 Pro will cover most of this) |

Format: number your comments. Cite `[§X.QY TAG]` for each (e.g., `[§4.EE-1 EMPIRICAL]`, `[§2.CR-3 MAJOR]`).

End with a **SUMMARY** section:
- Pinned re-run result (byte-identical / differs in X fields / fails)
- Top 5 empirical findings most relevant to v12 design
- Top 3 code quality issues (if any)
- Recommended next steps (your opinion)

---

## §15 — Specific provocations (please push back if wrong)

Strategist intentionally states three claims that may be wrong; please verify or refute:

1. **CLAIM**: "Re-running the v2.0 pipeline under sealed-pinned library versions (`arch==7.0.0`, etc.) will produce a byte-identical `outputs/lc_v2_verdict.json`."
   - **Test**: §3 above.

2. **CLAIM**: "Converting z4 from log-DXY-level to Δ12-log-DXY-YoY will pass ADF (p < 0.05) with the same sample period."
   - **Test**: §4 EE for z4_rate.

3. **CLAIM**: "Adding M2V to the composite adds little marginal information because Δlog(M2V) = Δlog(GDP) − Δlog(M2), and M2 YoY is already z2 of the existing composite."
   - **Test**: §4 correlation matrix; compute `corr(Δlog(M2V), Δlog(M2))` and `corr(Δlog(M2V), GDP_growth)`. If first is high, the claim holds. If low, M2V adds information.

---

## §16 — On reproducibility

Please report your environment:
- Python version
- OS / architecture (Linux x86_64, macOS arm64, etc.)
- Library versions used for §3 (the pinned ones) and §4-§5 (whatever you use for empirical execution)
- Random seed used (for any §4.6 / §4.7 stochastic analyses)

Strategist will replicate your environment if §3 finds a mismatch.

---

## §17 — Closing

You contributed substantively across the v11.4 sprint (Codex Round 3 caught Strategist mistake #5: the `b_sb` column reference was wrong; the correct column is `stationary`). Your empirical execution discipline has been critical.

This request is heavier than prior rounds because v12 design is a higher-stakes decision. The owner trusts your work and the parallel methodology review with ChatGPT 5.5 Pro.

Whatever you find, the owner will accept and act on. Authorship credit will be documented.

— Strategist (Claude AI)
2026-05-25

End of REVIEW REQUEST. Standing by for your response.
