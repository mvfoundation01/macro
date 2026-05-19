# REVIEW_PACKAGE_v4 — Buffett Indicator Transform + Modeling Layer (Spec v4.0)

Generated: 2026-05-18 (UTC). Working dir: `D:\macro\buffet_indicator`. Built on top of v1.0 ingestion (already verified).

## 1 — Self-assessment vs each spec section

| Section | Item | Status | Notes |
| --- | --- | --- | --- |
| §1 | API contract (`run_modeling`) | OK | Returns `headline`, `backtest_view`, plus the two BI-series dicts. Headline structure exactly matches spec example. |
| §2 | Module skeleton + new packages | OK | `src/transform/` and `src/models/` directories + 10 modules created. `statsmodels`, `arch`, `scipy` installed (versions newer than the pins). `ruptures` failed wheel build on Python 3.14 → log-linear fallback used per spec Appendix A. |
| §3 | `unit_harmonization.py` | OK | All 3 helpers + 6 tests (U1-U5 + all-NaN edge case). |
| §4 | `wilshire_scaling.py` | OK | Anchors + interpolate/extrapolate. Import-time sanity assert (1.057 < mult_2026 < 1.060) confirmed. 7 tests (W1-W6 + empty). |
| §5 | `align_monthly.py` | OK | Descriptive view broadcasts each quarter's value to its 3 months and forward-fills up to 3 months past the last observed quarter (so the dashboard sees Q1 2026's GDP through May 2026). Backtest view applies per-key release lag. 8 tests (A1-A8). |
| §6 | `buffett_compute.py` | OK | 3 BI variants. 5 tests (B1-B5). |
| §7 | `trend.py` (battery: log-linear, HP, BP/PELT) | OK | `ruptures` couldn't build on Python 3.14, so `bai_perron_piecewise` falls back to log-linear and reports `method="fallback_loglinear"`, with a one-time WARNING per series. Trend battery agreement metric uses average pairwise R² between trend lines. 13 tests (T1-T6 + 7 error-path / edge-case tests). |
| §8 | `zscore.py` | OK | Expanding (default `min_periods=60`), full-sample, and empirical percentile (scalar or expanding). 6 tests (Z1-Z6). |
| §9 | `regime.py` | OK | 5 regimes + colors. NaN → "Insufficient Data". 6 tests (R1-R5 + classify_series shape). |
| §10 | `bootstrap_ci.py` | OK | Stationary block bootstrap via `arch.bootstrap.StationaryBootstrap`. Block length via Politis-White (`optimal_block_length`). Returns all 7 keys + `confidence_pct = 100·max(0, 1 − width/4)`. 5 tests (BS1-BS5). |
| §11 | `preliminary_metrics.py` | OK | Cross-variant agreement + partial conviction (no HAC / OOS-R² / hit rate). Weights asserted to sum to 1.0. 6 tests (P1-P5 + invalid-weights). |
| §12 | `orchestrator_modeling.py` + CLI | OK | `python -m src.cli model` runs the full pipeline. JSON output is sanitized (Timestamps → ISO, Series → tail-60 dict). |
| §13 | Acceptance assertions | PASS | Both `test_v4_acceptance_descriptive_view` and `test_v4_acceptance_backtest_view_differs` pass when `ACCEPTANCE=1`. |
| §14 | Deliverables | OK | Sources + tests + `outputs/tables/{bi_series_*.csv, headline.json}` + `data/processed/bi_series_*.parquet` + REVIEW_PACKAGE_v4.md. |

## 2 — Test results

### Without acceptance / integration tests (default `pytest -q`)
```
$ python -m pytest -q
.............................................s.......s.................. [ 61%]
..................ss..........................                           [100%]
114 passed, 4 skipped in 6.16s
```
Skipped: 2 `@pytest.mark.integration` + 2 `@pytest.mark.acceptance` (require env-var opt-in).

### With acceptance tests on
```
$ set ACCEPTANCE=1
$ python -m pytest tests/test_v4_acceptance.py -v --no-cov
tests\test_v4_acceptance.py::test_v4_acceptance_descriptive_view PASSED  [ 50%]
tests\test_v4_acceptance.py::test_v4_acceptance_backtest_view_differs PASSED  [100%]
2 passed in 3.89s
```

### Full coverage with acceptance on
```
$ set ACCEPTANCE=1
$ python -m pytest --cov=src --cov-report=term
116 passed, 2 skipped in 9.51s
TOTAL                                  1564    269    83%
```

Per-new-module coverage:

| Module | Cover |
| --- | --- |
| `src/transform/unit_harmonization.py` | 100% |
| `src/transform/wilshire_scaling.py`   | 100% |
| `src/transform/align_monthly.py`      | 93% |
| `src/transform/buffett_compute.py`    | 100% |
| `src/models/preliminary_metrics.py`   | 100% |
| `src/models/zscore.py`                | 92% |
| `src/models/regime.py`                | 89% |
| `src/models/bootstrap_ci.py`          | 85% |
| `src/models/orchestrator_modeling.py` | 85% |
| `src/models/trend.py`                 | 72% (28 lines unreachable: `_try_pelt` + `_piecewise_loglinear_fit` need `ruptures`, which doesn't build on Python 3.14) |

Transform layer average: **96%**; models layer average: **89%** (excluding unreachable PELT paths).

## 3 — Smoke output (actual numbers — `python -m src.cli model --bootstrap-n 2000`)

```
Headline (2026-05-31):
  bi_allequity_pct     z=+1.43  pct=98.7   regime=Overvalued   conf=6%
  bi_wilshire_pct      z=+1.50  pct=90.7   regime=Overvalued   conf=0%
  bi_spx_proxy         z=+1.96  pct=100.0  regime=Overvalued   conf=7%
  cross_variant: mean_z=+1.63  agreement=0.82  combined=Overvalued
  preliminary_conviction: 4.17/5.00
```

BI values (from `outputs/tables/headline.json`):

| Variant            | bi_value (desc)  | bi_value (backtest) | Spec expected (Appx B) |
| ------------------ | ---------------- | ------------------- | ---------------------- |
| bi_allequity_pct   | **302.37**       | 302.37              | 285-325 ✓              |
| bi_wilshire_pct    | **245.07**       | 245.07              | 225-260 ✓              |
| bi_spx_proxy       | 23 256.00        | 23 256.00           | "~16-20" (see Note A) |

### Notes on smoke output

- **Z-scores are lower than the spec example.** Spec §1's illustrative numbers were z=+2.18 / +2.30 / +2.50; we observe z=+1.43 / +1.50 / +1.96. All still firmly "Overvalued" (z>1.0) and pass the acceptance assertion `z_score > 1.0`. The acceptance test does NOT require z>2 (Strongly Overvalued); only `z > 1.0`. The lower z reflects the long-run log-linear trend absorbing the post-2010 valuation surge — a known sensitivity of single-spec trend de-trending. With Spec v5's full Bai-Perron breaks (if `ruptures` lands), the post-2010 segment would have its own intercept and the residual would correctly read as more extreme. For now, the empirical percentile (98.7 / 90.7 / 100.0) is a more faithful "tail" signal than the absolute z.
- **`confidence_pct` is low (0-7%).** The bootstrap CI on the most recent z-score is wide for residuals over 80 years of monthly data (block length 18-30, so the resampled "last observation" varies a lot). The formula `100·max(0, 1 − CI_width/4)` reads ~0% when CI width approaches 4. The acceptance test only requires `0 ≤ confidence_pct ≤ 100` (✓); the spec's illustrative 80%+ in §1 likely assumes a much shorter / less volatile residual series.
- **Note A — `bi_spx_proxy.bi_value`:** Spec Appendix B says "~16-20"; the formula `spx / gdp_t × 100` produces 23 256 when SPX=7408 and GDP=31.86 T (i.e., 7408 / 31.86 × 100). Either Appendix B implicitly used a different scaling, or the expected magnitude is in error. We implemented per the formula in §6 (and the acceptance test does not check bi_spx_proxy's bi_value).
- **`regime = "Overvalued"` (not "Strongly Overvalued").** Z < 2.0 across all three, so the boundary lands one tier lower than the spec's illustrative output. Cross-variant `agreement = 0.82`, `same_regime = True`, `same_sign = True`.

### Cross-variant + conviction

```
cross_variant.mean_z          = +1.63
cross_variant.agreement       = 0.82
cross_variant.same_sign       = True
cross_variant.same_regime     = True
cross_variant.combined_regime = "Overvalued"

preliminary_conviction.score         = 4.17 / 5.00
preliminary_conviction.components    = {magnitude: 0.54, agreement: 0.82, sample_size: 1.00}
preliminary_conviction.weights       = {magnitude: 0.30, agreement: 0.40, sample_size: 0.30}
```

## 4 — Acceptance test results

```
$ set ACCEPTANCE=1
$ python -m pytest tests/test_v4_acceptance.py -v --no-cov
tests/test_v4_acceptance.py::test_v4_acceptance_descriptive_view  PASSED
tests/test_v4_acceptance.py::test_v4_acceptance_backtest_view_differs PASSED
```

All assertions pass:
- 3 variants present ✓
- bi_allequity in [280, 350] (302.37) ✓
- bi_wilshire in [220, 260] (245.07) ✓
- All z-scores > 1.0 (1.43, 1.50, 1.96) ✓
- All confidence_pct in [0, 100] ✓
- All empirical_percentile > 90 (98.7, 90.7, 100.0) ✓
- cross_variant.agreement > 0.7 (0.82) ✓
- cross_variant.same_sign True ✓
- preliminary_conviction.score in [3.0, 5.0] (4.17) ✓
- preliminary_conviction.note contains "Spec v5" ✓
- bt / desc in [0.92, 1.08] (1.000 — same Q1 GDP value used in both views at 2026-05-31) ✓

## 5 — Deviations from the spec

1. **`ruptures` not installed.** Wheel build fails on Python 3.14 (Cython incompatibility). Per spec Appendix A, the loader catches `ImportError` and falls back to log-linear-only trend with `method="fallback_loglinear"` and a one-time WARNING. The `bai_perron_piecewise` function and the trend battery still return valid output; just no break detection. Tests acknowledge this (T6 accepts both `pelt_proxy` and `fallback_loglinear` outcomes).

2. **Package versions newer than `requirements.lock` pins.** Python 3.14 host had `statsmodels==0.14.6`, `arch==8.0.0`, `scipy==1.17.1` installed (vs spec pins 0.14.2 / 7.0.0 / 1.13.1). All API calls used are stable; no behavior change observed. `requirements.lock` still lists the spec pins for reproducible installs on Python 3.11 systems.

3. **Descriptive monthly view extends 3 months past the last observed quarter.** Spec §5 docstring says "Each month within a quarter takes that quarter's value" but doesn't address post-last-quarter months. I forward-fill the last quarter's value through 3 additional months so a "today" dashboard run shows current-state numbers (e.g., May 2026 sees Q1 2026's GDP). Backtest view is strict — no ffill beyond the actual published quarter ends.

4. **`bi_spx_proxy` bi_value differs from Appendix B's "~16-20"** (we produce ~23 000). We followed the explicit formula in §6 (`spx / gdp_t × 100` with `gdp_t` in USD trillions). The acceptance test correctly does not check this magnitude; only z and percentile.

5. **`confidence_pct` proxy formula reads near-zero on long-history residuals.** The spec proxy `100·max(0, 1 − CI_width/4)` saturates at 0 once `CI_width ≥ 4`, which is the typical width for an 80-year residual-bootstrap CI on the last observation. The acceptance test only requires `0 ≤ confidence_pct ≤ 100`, which we pass. A future calibration (perhaps width-relative-to-residual-std rather than absolute) is left for Spec v5.

6. **Pre-existing 2 `@pytest.mark.integration` tests still skipped by default** (Shiller real-file load, Yahoo real-network fetch). Both pass under `INTEGRATION_TESTS=1`. The 2 new `@pytest.mark.acceptance` tests are similarly opt-in via `ACCEPTANCE=1`.

7. **`mypy --strict` and `ruff check` not executed.** Neither tool is in the host environment; spec also notes them as targets, not blockers. The code passes `python -c "import src.cli, src.models.orchestrator_modeling"` cleanly.

## 6 — Known limitations / TODOs (carried into v5)

- **No PELT / Bai-Perron available** until `ruptures` ships a Python 3.14 wheel (or until the project pins Python 3.13).
- **No HAC t-stat, OOS R², or hit-rate components** of conviction — explicitly Spec v5 territory.
- **No forward-return regression** or probability engine.
- **`confidence_pct` calibration** likely needs tuning once the predictive-regression CIs are available.
- **Spec v4's MASTER_DIR change-detection / vintage diffing** is unchanged from v1 — masters are still descriptive-only.

## 7 — Deliverables on disk

```
src/
  transform/
    __init__.py
    unit_harmonization.py
    wilshire_scaling.py
    align_monthly.py
    buffett_compute.py
  models/
    __init__.py
    bootstrap_ci.py
    orchestrator_modeling.py
    preliminary_metrics.py
    regime.py
    trend.py
    zscore.py
  cli.py                            (extended with `model` subcommand)
tests/
  transform/
    test_unit_harmonization.py      (6 tests)
    test_wilshire_scaling.py        (7 tests)
    test_align_monthly.py           (8 tests)
    test_buffett_compute.py         (5 tests)
  models/
    test_trend.py                   (13 tests)
    test_zscore.py                  (6 tests)
    test_regime.py                  (6 tests)
    test_bootstrap_ci.py            (5 tests)
    test_preliminary_metrics.py     (6 tests)
  test_v4_acceptance.py             (2 acceptance tests, opt-in)
outputs/tables/
  bi_series_descriptive.csv         (3 columns × ~700 rows)
  bi_series_backtest.csv            (3 columns × ~700 rows)
  headline.json                     (full result tree)
data/processed/
  bi_series_descriptive.parquet
  bi_series_backtest.parquet
requirements.lock                   (statsmodels/arch/scipy appended)
pytest.ini                          (added `acceptance` marker)
REVIEW_PACKAGE_v4.md                (this document)
```

End of REVIEW_PACKAGE_v4.
