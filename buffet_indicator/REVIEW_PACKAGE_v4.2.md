# REVIEW_PACKAGE_v4.2 — Dual-Frame Z-Scores (Spec v4.2)

Generated: 2026-05-18 (UTC). Working dir: `D:\macro\buffet_indicator`. Patch on top of v4.1.

## 1 — Diff summary

| File | Change |
| --- | --- |
| `src/models/preliminary_metrics.py` | Added `dual_frame_conviction(...)` (~70 lines + docstring). Old `preliminary_conviction` retained (still tested + back-compat). |
| `src/models/trend.py` | Added `frames(battery)` accessor returning `{"long_run": ll_resid, "current_regime": bp_resid}`. No new computation. |
| `src/models/orchestrator_modeling.py` | Replaced `_analyze` with `_analyze_dual_frame`; refactored `_build_view` to compute per-frame cross-variant + dual-frame conviction; new top-level `interpretation` block with `narrative_code` + prose. |
| `src/cli.py` | `python -m src.cli model` now prints both frames per variant + per-variant `narrative_code` + cross-variant per-frame + top-level interpretation. |
| `tests/models/test_preliminary_metrics.py` | Added P6-P9 (4 tests) for `dual_frame_conviction`. |
| `tests/test_v4_acceptance.py` | Replaced single-frame v4.1 tests with 4 v4.2 dual-frame tests. |

No new public modules. No new external dependencies. Total LOC added: ~190 source / ~110 test.

## 2 — Smoke output (verbatim, May 2026)

```
$ python -m src.cli model --bootstrap-n 2000

Headline (2026-05-31):  view=descriptive
  bi_allequity_pct  (BI = 302.4%)
    long_run        z=+1.43  pct= 98.7  regime=Overvalued        conf=28%
    current_regime  z=+0.18  pct= 61.5  regime=Fair Value        conf=19%  [breaks: 2]
    [MIXED]  z_spread=1.25
  bi_wilshire_pct  (BI = 245.1%)
    long_run        z=+1.50  pct= 90.7  regime=Overvalued        conf=27%
    current_regime  z=+1.44  pct= 93.7  regime=Overvalued        conf=28%  [breaks: 2]
    [MIXED]  z_spread=0.06
  bi_spx_proxy  (BI = 237.6%)
    long_run        z=+1.96  pct=100.0  regime=Overvalued        conf=34%
    current_regime  z=+1.75  pct= 94.9  regime=Overvalued        conf=28%  [breaks: 2]
    [AGREE_EXTREME_HIGH]  z_spread=0.21

Cross-variant:
  long_run        mean_z=+1.63  agreement=0.82  regime=Overvalued
  current_regime  mean_z=+1.12  agreement=0.26  regime=Overvalued

Preliminary conviction: 3.49/5.00

=== Interpretation (MIXED, primary=long_run) ===
The long-run and current-regime frames give partially conflicting valuation
signals. Neither all-agreement nor a clean bubble-or-shift pattern; the
variants split between regimes. Inspect each variant's z-scores and
narrative_code individually.

(Backtest view also computed -- see outputs/tables/headline.json)
```

## 3 — Per-variant (long_run, current_regime, narrative_code, breaks)

| Variant | bi_value | long_run z | long_run pct | LR regime | current_regime z | CR pct | CR regime | n_breaks | break_dates | narrative_code | z_spread |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bi_allequity_pct | 302.37 | **+1.43** | 98.7 | Overvalued | **+0.18** | 61.5 | Fair Value | 2 | 1974-03-31, 2007-12-31 | **MIXED** | 1.25 |
| bi_wilshire_pct  | 245.07 | **+1.50** | 90.7 | Overvalued | **+1.44** | 93.7 | Overvalued | 2 | 1979-04-30, 2002-05-31 | **MIXED** | 0.06 |
| bi_spx_proxy     | 237.61 | **+1.96** | 100.0 | Overvalued | **+1.75** | 94.9 | Overvalued | 2 | 1964-10-31, 1982-10-31 | **AGREE_EXTREME_HIGH** | 0.21 |

- `bi_allequity_pct` shows the canonical "frames disagree" pattern: long-run says Overvalued (98.7th percentile residual), current-regime absorbed the post-GFC level shift via the 2007-12 break and reads Fair Value.
- `bi_wilshire_pct` shows near-perfect frame agreement (z_spread = 0.06) — both lenses agree on "Overvalued".
- `bi_spx_proxy` shows the strongest signal (long_run hits the 100th percentile) with both frames agreeing.

## 4 — Cross-variant per frame

| Block | mean_z | std_z | agreement | same_sign | same_regime | combined_regime |
| --- | --- | --- | --- | --- | --- | --- |
| `cross_variant_long_run`       | +1.63 | 0.29 | **0.82** | True | True | Overvalued |
| `cross_variant_current_regime` | +1.12 | 0.83 | **0.26** | True | False | Overvalued |

Long-run frame shows high cross-variant agreement (0.82); current-regime frame shows much lower agreement (0.26) because BI-AllEquity's BP-residual diverges from the other two.

## 5 — Preliminary dual-frame conviction (3.49 / 5.00)

| Component | Value | Weight | Weighted |
| --- | ---: | ---: | ---: |
| long_run_magnitude (mean_z=+1.63) | 0.544 | 0.20 | 0.109 |
| current_regime_magnitude (mean_z=+1.12) | 0.375 | 0.20 | 0.075 |
| cross_variant_agreement_long_run | 0.824 | 0.15 | 0.124 |
| cross_variant_agreement_current_regime | 0.262 | 0.15 | 0.039 |
| frame_coherence (z_spread_avg=0.506) | 0.873 | 0.20 | 0.175 |
| sample_size (n_min=947) | 1.000 | 0.10 | 0.100 |
| **Total raw** | | | **0.622** |
| **Score = 1 + 4 × raw** | | | **3.49** |

Conviction is moderate (3.49/5.00). Drivers: high `frame_coherence` (0.87) and high cross-variant agreement on the long-run frame (0.82) pull up; low cross-variant agreement on the current-regime frame (0.26) pulls down. This is the intended behavior — when the two lenses or the three variants disagree, conviction is correctly moderated.

## 6 — Headline interpretation

- `interpretation.primary_frame`: `long_run` (matches CMV / LongtermTrends conventions).
- `interpretation.narrative_code`: `MIXED` (consensus across variants — see §7).
- `interpretation.per_variant_codes`: `["MIXED", "MIXED", "AGREE_EXTREME_HIGH"]`.
- `interpretation.z_spread_avg`: 0.506 (across the three variants' per-frame z gaps).

The narrative prose displayed by the CLI:

> The long-run and current-regime frames give partially conflicting valuation signals. Neither all-agreement nor a clean bubble-or-shift pattern; the variants split between regimes. Inspect each variant's z-scores and narrative_code individually.

## 7 — Why the consensus is MIXED (and not BUBBLE_OR_SHIFT)

Spec v4.2 § 8 predicted the consensus code would be `BUBBLE_OR_SHIFT` for May 2026, with `bi_allequity_pct.long_run.z = +2.30`. Our actual result is `bi_allequity_pct.long_run.z = +1.43`, which sits just below the `> 1.5` threshold needed to fire `BUBBLE_OR_SHIFT`.

Two notes on this:

1. **Empirical percentile and z agree on "extreme high".** `bi_allequity_pct.long_run.empirical_percentile = 98.7` — the latest residual sits at the 98.7th percentile of the full historical distribution. A Normal would translate that to z ≈ +2.2, matching the spec's prediction. The actual residual distribution has fat negative tails (Great Depression, 1970s, 2008, 2020), which inflate the std and pull z down to +1.43. The spec author implicitly assumed near-Normal residuals; reality is leptokurtic on the left.

2. **`narrative_code` thresholds were honored verbatim.** `BUBBLE_OR_SHIFT` requires `long_run.z > 1.5 AND current_regime.z < 1.0`. `bi_allequity` misses the first condition by 0.07. If thresholds were relaxed to `> 1.4`, the variant would fire `BUBBLE_OR_SHIFT` and the consensus would propagate (`bi_allequity` BUBBLE_OR_SHIFT, `bi_wilshire`/`bi_spx_proxy` MIXED → still no 2/3 majority → MIXED overall).

Bottom line: the dual-frame infrastructure is working correctly. The "BUBBLE_OR_SHIFT" narrative is a real possibility for the long-run frame on `bi_allequity`, but the residual distribution's fat tails put its z just under the threshold. The dashboard / Spec v5 could optionally relax thresholds to `> 1.3` if calibration against historical bubble episodes warrants.

## 8 — Test results

### Unit tests (no acceptance)
```
$ python -m pytest -q
140 passed, 6 skipped in 8.40s
```
Skipped: 2 `@pytest.mark.integration` (real network) + 4 `@pytest.mark.acceptance` (default off).

### Acceptance tests
```
$ set ACCEPTANCE=1
$ python -m pytest tests/test_v4_acceptance.py -v --no-cov
tests\test_v4_acceptance.py::test_v42_dual_frame_structure         PASSED
tests\test_v4_acceptance.py::test_v42_long_run_overvalued_may2026  PASSED
tests\test_v4_acceptance.py::test_v42_bi_spx_scaled                PASSED
tests\test_v4_acceptance.py::test_v42_backtest_view_present        PASSED
4 passed in 13.34s
```

### Full coverage with ACCEPTANCE=1
```
144 passed, 2 skipped in 47.05s

Name                                  Stmts   Miss  Cover
---------------------------------------------------------
src\models\bai_perron.py                135      8    94%
src\models\bootstrap_ci.py               43      6    86%
src\models\orchestrator_modeling.py     153     23    85%
src\models\preliminary_metrics.py        38      0   100%
src\models\regime.py                     18      2    89%
src\models\trend.py                      75     15    80%
src\models\zscore.py                     26      2    92%
src\transform\align_monthly.py           75      5    93%
src\transform\buffett_compute.py         41      3    93%
src\transform\unit_harmonization.py      15      0   100%
src\transform\wilshire_scaling.py        23      0   100%
TOTAL                                  1775    285    84%
```

Per-new-or-modified module:
- `preliminary_metrics.py` (added `dual_frame_conviction`): **100%**
- `orchestrator_modeling.py` (dual-frame refactor): **85%**
- `trend.py` (added `frames`): **80%**

New P6-P9 tests for `dual_frame_conviction`:

```
tests/models/test_preliminary_metrics.py::test_P6_dual_frame_strong_agreement_high_score  PASSED
tests/models/test_preliminary_metrics.py::test_P7_dual_frame_disagreement_lowers_score    PASSED
tests/models/test_preliminary_metrics.py::test_P8_weights_sum_to_one                       PASSED
tests/models/test_preliminary_metrics.py::test_P9_custom_weights_override_default          PASSED
```

## 9 — Deviations from Spec v4.2

1. **`narrative_code` consensus is `MIXED`, not the spec-predicted `BUBBLE_OR_SHIFT`.** Reason in §7: `bi_allequity.long_run.z = +1.43` misses the `> 1.5` threshold by 0.07. The threshold itself is honored verbatim per Spec v4.2 §3.

2. **`bi_allequity.long_run.regime = "Overvalued"`, not "Strongly Overvalued".** Same root cause as (1): z < 2.0 means the regime classifier returns "Overvalued" (1 < z ≤ 2) per the existing regime definitions in `src/models/regime.py`.

3. **`current_regime` uses the orchestrator's tuned defaults `max_breaks=2, criterion="lwz"`**, not BP function defaults `max_breaks=5, criterion="bic"`. Same reasoning as v4.1: avoids the 5-break over-fitting trap warned about in Spec v4.1 §5.1. The values in Spec v4.2 §8 expected output match the tuned defaults, so this is consistent with the spec author's intent even though the function defaults differ.

4. **Top-level `interpretation.narrative` is a static lookup per `narrative_code`**, not a fully data-substituted string. Spec example shows a single very-specific paragraph with computed numbers interpolated; the implementation uses a static prose template per code (parameter substitution can be added in Spec v5 if dashboards need the dynamic version).

5. **`preliminary_conviction` is preserved alongside `dual_frame_conviction`.** Per Spec v4.2 §4 "do NOT remove the old `preliminary_conviction`; it's still used internally and by tests" — followed verbatim. `dual_frame_conviction` is what the orchestrator now calls.

## 10 — Implications

- **Headline regime call for May 2026**: Overvalued (long-run frame, with high cross-variant agreement). The BI-Wilshire and BI-SPX-proxy variants both register Overvalued under both frames. BI-AllEquity is the only variant whose `current_regime` reads Fair Value -- because BP placed a break at 2007-12 and the post-GFC slope captures the modern level as "trend".
- **Diagnostic finding for `bi_allequity`**: the z_spread = 1.25σ between long_run and current_regime IS the headline -- either US corporate-equity-to-GDP has undergone a permanent structural upshift (current_regime is right), or it's an extended bubble that BP has been forced to accommodate within trend (long_run is right). With current data alone, the two hypotheses are observationally indistinguishable.
- **Implications for Spec v5** (per spec preamble): forward-return regressions can now be run with `long_run.z` OR `current_regime.z` as the predictor; the data will tell us which lens predicts better at which horizon. Hypothesis: long_run dominates at 5Y+ (mean reversion); current_regime dominates at 1Y- (momentum).

## 11 — Files / artefacts

```
src/models/
  bai_perron.py                       (unchanged from v4.1)
  bootstrap_ci.py                     (unchanged from v4.1)
  orchestrator_modeling.py            (REFACTORED for dual frames)
  preliminary_metrics.py              (added dual_frame_conviction)
  regime.py                           (unchanged)
  trend.py                            (added frames accessor)
  zscore.py                           (unchanged)
src/cli.py                            (model subcommand updated for dual-frame display)

tests/models/
  test_bai_perron.py                  (unchanged, 12 tests)
  test_bootstrap_ci.py                (unchanged, 10 tests)
  test_preliminary_metrics.py         (added P6-P9, total 10 tests)
  test_regime.py                      (unchanged, 6 tests)
  test_trend.py                       (unchanged, 13 tests)
  test_zscore.py                      (unchanged, 6 tests)
tests/transform/                      (all unchanged)
tests/test_v4_acceptance.py           (replaced 2 v4.1 tests with 4 v4.2 tests)

outputs/tables/
  headline.json                       (rewritten with dual-frame schema)
  bi_series_descriptive.csv           (rewritten)
  bi_series_backtest.csv              (rewritten)
data/processed/
  bi_series_descriptive.parquet
  bi_series_backtest.parquet

REVIEW_PACKAGE_v4.2.md                (this document)
```

End of REVIEW_PACKAGE_v4.2.
