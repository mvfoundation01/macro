# v11.4 LC v2.0 — Sprint Implementation Plan

**Generated**: 2026-05-24
**Authority**: Strategist (Claude AI) per `PROMPT_CC_v11_4_v2_sprint_kickoff.md` §2
**Source of truth**: `buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` (SHA-256 `c3c3ec1a…`, seal commit `2a94417…`)
**Project layout**: `buffet_indicator/` is the package root; `src/` and `tests/` live inside it; imports via `from src.<pkg>.<mod>` after `sys.path.insert(0, _ROOT)`.

---

## §A — Phase A.1 plan summary

- **15 public functions** from sealed §11.1 to scaffold + implement
- **21 acceptance tests** from sealed §11.2 to scaffold (TDD-first; failing stubs)
- **Priority module**: `src/stats/hard_gate.py` (`assert_prereg_ancestor`) — lifts seal report §16 #6 from DEFERRED to PASS
- **Module package count**: 7 (`stats`, `models`, `ingest`, `seal`, `transform`, plus existing `backtest`, `viz`, `quant_engine`)

## §B — 15 §11.1 functions → modules (Phase A.2 scaffolding targets)

| ID | Function | Module path | Tests |
|---|---|---|---|
| F01 | `compute_hac_lag` | `src/stats/hac.py` | T01 |
| F02 | `sample_gate_status` | `src/stats/sample_gate.py` | T02, T03 |
| F03 | `fit_conditional_skew_t` | `src/stats/skewt.py` | T06, T07 |
| F04 | `run_predictive_regression_v2` | `src/models/predictive_regression_v2.py` | T04, T05, T11 |
| F05 | `stationary_bootstrap_ci` | `src/stats/bootstrap.py` | T09, T19 |
| F06 | `evaluate_v2_criteria` | `src/models/v2_criteria.py` | T12, T13, T14 |
| **F07** | **`assert_prereg_ancestor`** ← **FIRST** | **`src/stats/hard_gate.py`** | **T15** |
| F08 | `annual_retest_status` | `src/models/retest.py` | T16, T17 |
| F09 | `compare_threshold` | `src/stats/compare.py` | (used by F06) |
| F10 | `collect_v1_realized_sample_counts` | `src/ingest/v1_sample_counts.py` | (deferred §10.3 recompute) |
| F11 | `parse_component_id_map` | `src/ingest/component_map.py` | T18 |
| F12 | `should_apply_stambaugh` | `src/stats/stambaugh.py` | T10 |
| F13 | `choose_stationary_block_length` | `src/stats/bootstrap.py` *(co-located w/ F05)* | T08 |
| F14 | `load_bootstrap_policy` | `src/stats/bootstrap_policy.py` | T19 |
| F15 | `collect_seal_metadata_with_python_helpers` | `src/seal/metadata.py` | T21 |

## §C — 21 §11.2 tests → test files (Phase A.3 scaffolding targets)

| ID | Test | Test file |
|---|---|---|
| T01 | `test_compute_hac_lag_uses_v1_formula` | `tests/stats/test_hac.py` |
| T02 | `test_sample_gate_boundary_basic` | `tests/stats/test_sample_gate.py` |
| T03 | `test_sample_gate_boundaries_include_hac_and_neff` | `tests/stats/test_sample_gate.py` |
| T04 | `test_predictive_regression_uses_statsmodels_hac` | `tests/models/test_predictive_regression_v2.py` |
| T05 | `test_oos_rows_counted_after_realization` | `tests/models/test_predictive_regression_v2.py` |
| T06 | `test_skewstudent_loglikelihood_signature_is_used_correctly` | `tests/stats/test_skewt.py` |
| T07 | `test_skewed_t_known_distribution_and_fallback` | `tests/stats/test_skewt.py` |
| T08 | `test_optimal_block_length_uses_arch_stationary_column` | `tests/stats/test_bootstrap.py` |
| T09 | `test_stationary_bootstrap_is_byte_identical` | `tests/stats/test_bootstrap.py` |
| T10 | `test_stambaugh_exact_boundary_not_applied` | `tests/stats/test_stambaugh.py` |
| T11 | `test_campbell_yogo_status_never_silent_nan` | `tests/models/test_predictive_regression_v2.py` |
| T12 | `test_all_seven_criteria_known_pass_and_fail` | `tests/models/test_v2_criteria.py` |
| T13 | `test_criterion_4_strict_t_boundary` | `tests/models/test_v2_criteria.py` |
| T14 | `test_bonferroni_denominator_is_20` | `tests/models/test_v2_criteria.py` |
| **T15** | **`test_hard_gate_handles_ancestor_detached_preseal_and_shallow`** | **`tests/stats/test_hard_gate.py`** ← **FIRST** |
| T16 | `test_annual_retest_fires_once_per_year` | `tests/models/test_retest.py` |
| T17 | `test_retest_unstable_verdict_is_schema_valid` | `tests/models/test_retest.py` |
| T18 | `test_prereg_component_id_map_matches_v1_sealed_catalog` | `tests/ingest/test_component_map.py` |
| T19 | `test_bootstrap_count_policy_is_not_runtime_dependent` | `tests/stats/test_bootstrap_policy.py` |
| T20 | `test_sealed_prereg_contains_no_unresolved_placeholders` | `tests/seal/test_sealed_prereg.py` |
| T21 | `test_seal_helpers_do_not_require_unix_only_tools` | `tests/seal/test_metadata_cross_platform.py` |

## §D — Phase B/C deferred items (NOT in §11.1 explicitly but needed downstream)

- `load_master()` → `src/ingest/master.py` (per master spec §2.4.10 and kickoff §6.1)
- 3 splice helpers → `src/transform/splices_v2.py` (BUSLOANS→TOTLL 1973-01-03; TED→SOFR-IORB 2022-01-22; ICE DXY→DTWEXBGS 2006-01-04)
- PIT z-score → `src/transform/pit_zscore.py`
- LC composite construction (LC_FULL/LC_TIER2/LC_DEEP) → `src/models/lc_composite_v2.py`

These are deferred to a later session/prompt unless context budget allows mid-prompt continuation.

## §E — This-session execution order

1. ✅ §1 Remote verification (PASS)
2. ✅ §2.1+§2.2 Plan extraction (this file)
3. → §2.3 Commit plan + remote verification report
4. → §3 (A.2) Scaffold 15 modules (NotImplementedError bodies)
5. → §4 (A.3) Scaffold 21 tests (failing stubs)
6. → §5 (A.4) Implement `src/stats/hard_gate.py` first (§16 #6 lift)
7. → §9.3 Progress report at session end

Phases B/C/D execution depends on context budget after §5.

## §F — Spec-referenced ambiguities to watch for (per §10 callback procedure)

None identified yet during plan extraction. If signature interpretation or test boundary surfaces an ambiguity during implementation, follow §10 callback procedure.

— Claude Code, v2.0 sprint Phase A.1 plan @ 2026-05-24
