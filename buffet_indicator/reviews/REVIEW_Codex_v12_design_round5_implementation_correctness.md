# Codex Review - v12 Design Round 5 Implementation Correctness

Date: 2026-05-25
Reviewer: Codex
Scope request: `prompt/052526/REVIEW_REQUEST_Codex_v12_design.md`

## Bottom Line

Recommendation: **do not treat the current v11.4 implementation as a correctness-clean baseline for v12 design without fixes.**

The pinned-library rerun did **not** change the verdict or any criterion-critical numeric fields, so I do not see a library-version verdict flip. However, the implementation still has one PIT/vintage blocker, several major reproducibility/methodology issues, and one important v12-A empirical caveat: converting z4 to 12-month log change passes ADF locally, but it does **not** improve effective valid-start if the composite still applies a 120-month strict PIT z-score.

## Severity Findings

### BLOCKER - CR-1: Verdict-bearing panel does not enforce per-origin `load_master(..., vintage=t)`

Sealed DRAFT_v4 requires every forecast-origin loop to consume `load_master(series_id, vintage=t)` and forbids latest-vintage consumption in verdict-bearing paths (`prompt/052426/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER_DRAFT_v4.md:147-158`). Current code builds each component once from latest master data:

- `src/models/v2_panel_builder.py:165-170`
- `src/models/v2_panel_builder.py:197-198`
- `src/models/v2_panel_builder.py:214-217`
- `src/models/v2_panel_builder.py:241-242`
- `src/models/v2_panel_builder.py:269-276`

The output metadata labels this as `observation_date_approximation` (`src/models/v2_panel_builder.py:482-489`), but that is not the same as enforcing the sealed invariant. The audit is also effectively tautological: it sets `feature_vintage_max` to the latest aligned forecast-origin date (`src/models/v2_panel_builder.py:461-468`) and then performs no actual inequality check (`src/models/v2_verdict_writer.py:480-510`).

Impact: v2/v12 verdict-bearing PIT discipline cannot be certified from the current implementation. This may not flip the current verdict, but it invalidates the strongest "implementation-correct" claim around CR-1.

Required fix: build each forecast-origin cell from a data loader that filters by `vintage=t` or explicitly downgrade the prereg/audit language to "latest-revision observation-date approximation, non-ALFRED."

### MAJOR - CR-2: OOS R2 uses a fixed in-sample mean, not an expanding prevailing mean through OOS

`src/models/predictive_regression_v2.py:177-189` defines the benchmark as one constant `y_bar_train`. The OOS path computes `y_bar_train = mean(y_train)` once and applies it to all OOS rows (`src/models/predictive_regression_v2.py:363-373`).

The round-5 request specifically asks whether the benchmark is rolling/expanding through OOS rather than fixed. It is fixed. This diverges from the requested Goyal-Welch prevailing-mean implementation and can change C1-C3 when those criteria become evaluable.

Impact: current C1-C3 are mostly not evaluable, so this does not explain the current FAIL, but it is unsafe for v12.

### MAJOR - CR-3: `n_bootstrap=50000` policy exists but is not enforced

The policy dataclass correctly says `VERDICT_N_BOOTSTRAP = 50_000`, but callers can still override it:

- CLI exposes `--n-bootstrap` (`src/models/v2_run_verdict.py:93-105`)
- sweep accepts arbitrary `n_bootstrap` (`src/models/v2_verdict_run.py:134-149`)
- beta bootstrap passes caller value through (`src/models/v2_verdict_run.py:203-206`)
- generic bootstrap API requires caller-provided `n_bootstrap` (`src/stats/bootstrap.py:117-125`, `src/stats/bootstrap.py:207-208`)

Impact: sealed outputs can be regenerated with non-sealed bootstrap counts without an error. The tests also rely on small bootstrap counts for speed, so there is no failure-mode coverage for a verdict-bearing override attempt.

Required fix: add a verdict-bearing wrapper that rejects any value other than 50,000, or require an explicit `purpose="diagnostic"` escape hatch outside verdict paths.

### MAJOR - Reproducibility: sidecar SHA is not the JSON file-byte SHA on Windows

`write_verdict_json` hashes the in-memory JSON string, then writes via `Path.write_text()` (`src/models/v2_verdict_writer.py:570-580`). On Windows this produced CRLF translation in the file, so:

- existing `outputs/lc_v2_verdict.json` file-byte SHA: `6671cc9ff7b9e9f97a0c7447528bf0bcdc12b18a9406b29a8f0e632550200416`
- existing sidecar / UTF-8-string SHA: `84a457e3f47f5ad5e11f8fc2f86adf03ea25e30fead4a99c084e99ccfa6d4180`
- pinned rerun file-byte SHA: `5919dcf7787df7661456b53d1250217e32442d9b662708a0d1123a5ed6754fb4`
- pinned rerun sidecar / UTF-8-string SHA: `6299c15ca0c42c1ae69acbc112f7fb11e9e3c5dbbbebfe073c8e61d981c8b222`

Impact: shell-level `sha256sum outputs/lc_v2_verdict.json` will not match the sidecar on Windows. This makes the "artifact SHA" ambiguous.

Required fix: write bytes explicitly with a chosen newline convention and hash exactly those bytes.

### MAJOR - CQ-1: Skew-t fit exceptions are silently swallowed

`src/models/v2_verdict_run.py:174-181` catches broad `Exception` around `fit_conditional_skew_t()` and sets `skewt = None`.

Impact: numerical/API failures in `arch.univariate.SkewStudent` can be hidden as missing distribution metadata. The lower-level skew-t function already has explicit fallback gates; broad catch at orchestration level should record the exception in the verdict or fail loudly.

### MAJOR - CR-1: z5 still violates strict 120-month PIT for SOFR-IORB spread

The panel builder explicitly relaxes z5 post-splice spread warmup to 24 months (`src/models/v2_panel_builder.py:259-260`, `src/models/v2_panel_builder.py:295-296`, `src/models/v2_panel_builder.py:493-494`).

Impact: this is disclosed, but it means the answer to "strict-shift PIT z-score n>=120 verified at every cell?" is no. This may be acceptable as a documented data-availability exception, but it must not be reported as strict compliance.

### MINOR - v12 request assumes log-growth for z2/z3, implementation uses simple percent change

The round-5 design request describes z2/z3 as `Delta12 log(...)`, but implementation uses `pct_change(12)` for M2 and bank-lending growth (`src/models/v2_panel_builder.py:200`, `src/models/v2_panel_builder.py:220-221`; helper in `src/transform/splice.py:55`).

Impact: for small monthly growth this is close, but not identical. Before v12 preregistration, choose one convention and make code/spec/tests agree.

## Library Sensitivity Result

I installed `requirements.lock` into an isolated target and reran:

```text
python -m src.models.v2_run_verdict --n-bootstrap 50000 --output outputs/diagnostics/v12_review/lc_v2_verdict_pinned.json
```

Pinned versions in the rerun included Python 3.12.13, `arch==7.0.0`, `numpy==1.26.4`, `pandas==2.2.3`, `scipy==1.13.1`, and `statsmodels==0.14.2`.

Result:

- pinned rerun: `verdict=FAIL`, `n_pass_total=1/7`, `evidence_status=MIXED`
- existing artifact: same verdict, same `n_pass_total`, same evidence status
- recursive JSON diff showed only metadata/version/timestamp/git-head paths differed
- no criterion status or criterion numeric path differed

Interpretation: no library-version verdict flip found for the actual artifact. The byte-identity claim is still too strong because dynamic metadata and OS newline hashing prevent byte-identical output.

## Bootstrap / Skew-t Empirical Questions

For the pinned verdict JSON, distribution-family records were:

| family | count |
|---|---:|
| `gaussian_fallback` | 4 |
| `None` | 3 |
| `skewed_t` | 0 |

All Gaussian fallbacks used `fallback_reason="n_resid_lt_120"`.

Interpretation: Amendment 3 did not materially exercise a fitted Hansen skewed-t in the current verdict run. This matters for v12: if the panel remains short, the distribution-family amendment may continue to be mostly nominal.

## Tests Run

Targeted v2/stats/transform suite under pinned dependencies:

```text
pytest tests/models/test_v2_panel_builder.py tests/models/test_predictive_regression_v2.py tests/models/test_v2_criteria.py tests/models/test_v2_verdict_run.py tests/models/test_v2_verdict_writer.py tests/stats/test_bootstrap.py tests/stats/test_bootstrap_policy.py tests/stats/test_skewt.py tests/transform/test_composite.py tests/transform/test_pit_zscore.py tests/transform/test_splice.py -q
```

Result: all selected tests passed after setting pytest temp/cache inside `outputs/diagnostics/v12_review/pytest_tmp`.

Coverage for the same selected suite:

- total repo coverage: 20% because the selected suite does not cover the whole repo
- relevant module coverage: `v2_panel_builder` 97%, `predictive_regression_v2` 91%, `v2_criteria` 87%, `v2_verdict_run` 91%, `stats/bootstrap` 94%, `stats/skewt` 93%, `pit_zscore` 100%
- no repo-level `fail-under` coverage threshold is enforced; `pytest.ini` only sets `addopts = -q`, while `pyproject.toml` has `--cov=src --cov-report=term-missing` but no minimum threshold

## v12-A Local Empirical Check

Data source: local master parquets only. Shell download from FRED CSV timed out; FRED metadata was checked via FRED pages/data tables for M2V, M3, BOGMBASE, CPIAUCSL, and GDP.

Local transformed candidates:

| candidate | start | end | n | ADF p | KPSS p | AR(1) rho | corr 1Y fwd | corr 3Y fwd | corr 5Y fwd |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| z1_rate_log_yoy | 2003-12-31 | 2026-05-31 | 270 | 0.0695 | 0.1000 | 0.9645 | 0.1329 | 0.1199 | 0.3175 |
| z2_rate_log_yoy | 1960-01-31 | 2026-03-31 | 795 | 0.000003 | 0.0723 | 0.9969 | -0.1088 | -0.2345 | -0.1170 |
| z3_rate_log_yoy | 1948-01-31 | 2026-05-31 | 929 | 0.00000009 | 0.1000 | 0.9891 | -0.1841 | -0.1092 | -0.1394 |
| z4_rate_log_yoy_raw | 2007-01-31 | 2026-05-31 | 233 | 0.0227 | 0.1000 | 0.9180 | 0.3897 | 0.4247 | 0.4354 |
| z5_funding_stress | 1996-01-31 | 2026-05-31 | 350 | 0.0826 | 0.1000 | 0.8503 | -0.1397 | -0.2338 | -0.1209 |

Local 5-candidate joint history:

- raw transformed joint start: 2007-01-31
- raw transformed joint end: 2026-03-31
- n: 216
- max VIF: 2.11
- pairs with absolute correlation > 0.7: none

PIT-z effective starts if v12-A still applies `min_window=120`:

| component | v2 current first valid | v12-A PIT first valid |
|---|---:|---:|
| z1 | 2012-12-31 | 2013-12-31 |
| z2 | 1970-01-31 | 1970-01-31 |
| z3 | 1958-01-31 | 1958-01-31 |
| z4 | 2016-01-31 | 2017-01-31 |
| z5 | 1996-01-31 | 1996-01-31 |

Interpretation:

- z4 12-month log change supports the stationarity intuition: ADF p=0.0227 locally.
- z1 12-month log change does **not** pass ADF at 5% locally: p=0.0695, with high persistence.
- If the composite still uses strict PIT z-score with 120 prior monthly observations, z1_rate and z4_rate start **one year later**, not earlier. The "longer effective history" claim is false under the current PIT architecture.
- Local collinearity is not the problem: max VIF is 2.11 and no pair exceeds absolute correlation 0.7.

## v12 Additions - Data Quality Notes From FRED Metadata

Sources checked:

- M2V FRED table: https://fred.stlouisfed.org/data/M2V
- M3/OECD FRED table: https://fred.stlouisfed.org/data/MABMM301USM189S
- BOGMBASE FRED table: https://fred.stlouisfed.org/data/BOGMBASE
- CPIAUCSL FRED table: https://fred.stlouisfed.org/data/CPIAUCSL
- GDP FRED table: https://fred.stlouisfed.org/data/GDP

M2V:

- Date range: 1959-01-01 to 2026-01-01
- Frequency: quarterly
- Construction: ratio of quarterly nominal GDP to quarterly average M2 money stock
- Recommendation: do not linearly interpolate into a monthly composite unless shifted/lagged to avoid quarter look-ahead. The clean choices are quarterly v12 or release-lagged forward-fill.

M3 (`MABMM301USM189S`):

- Date range: 1960-01-01 to 2023-11-01
- Frequency: monthly
- Source: OECD Main Economic Indicators
- Last updated: 2024-01-12; next release not available on the FRED series page
- Recommendation: not suitable as a live v12 component unless the owner accepts stale OECD history or identifies a refreshed primary source.

BOGMBASE / monetary base:

- Date range: 1959-01-01 to 2026-03-01
- Frequency: monthly
- Units: billions of dollars, not seasonally adjusted
- Notes: H.3 was discontinued and the series is now consolidated onto H.6; this should be documented if used for pre/post-2008 comparisons.

CPIAUCSL and GDP:

- CPIAUCSL: monthly, 1947-01-01 to 2026-04-01
- GDP: quarterly, 1947-01-01 to 2026-01-01
- Derived real-money growth can be monthly using M2SL/CPIAUCSL.
- Derived base velocity using GDP/BOGMBASE inherits GDP's quarterly frequency and should be modeled quarterly or explicitly lagged/forward-filled.

## Final Recommendation For v12

1. Fix or explicitly downgrade PIT vintage semantics before using this code as a v12 scaffold.
2. Correct OOS R2 to use an expanding prevailing-mean benchmark before v12 criteria are tested.
3. Enforce immutable `n_bootstrap=50000` in verdict-bearing paths.
4. Make verdict JSON hashing byte-exact across OSes.
5. For v12-A, treat z4_rate as promising for stationarity but **not** as a history-window fix under 120-month PIT.
6. Avoid M3/OECD as a live component unless a current, maintained source is found.
7. If velocity variables are included, prefer a quarterly v12 variant or a rigorously lagged monthly representation.

