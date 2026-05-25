# v2.0 sprint Phase D progress

**Timestamp**: 2026-05-25T16:11:42Z
**Session**: Phase D (statistical layer — D1.1 + D1.2 + D1.3 + D2)
**Starting HEAD**: `a052a89` (Phase B+C complete progress report)
**Ending HEAD**: `68ed517`
**Commits this session**: 4
**Pushed**: 4 (all to `origin/spec/liquidity-composite-v2.0`)

---

## Phases completed

| Phase | Status | Commit | Tests | Notes |
|---|---|---|---|---|
| D1.1 — 5 utilities (layer 1) | PASS | `04972dd` | 6 §11.2 + 4 ancillary = 10 | parse_component_id_map, load_bootstrap_policy, compute_hac_lag, should_apply_stambaugh, choose_stationary_block_length (+ stationary_bootstrap_ci co-located ahead of D1.2) |
| D1.2 — 3 statistical primitives (layer 2) | PASS | `6917023` | 4 §11.2 + 2 ancillary = 6 | sample_gate_status, fit_conditional_skew_t, stationary_bootstrap_ci |
| D1.3 — predictive_regression_v2 (layer 3) | PASS | `ca4371b` | 3 §11.2 = 3 | NW HAC + Stambaugh + Campbell-Yogo + OOS R² (Goyal-Welch) + Clark-West composition |
| D2 — 5 composition/orchestration (layer 4-5) | PASS | `68ed517` | 7 §11.2 + 9 ancillary = 16 | compare_threshold, evaluate_v2_criteria (7 criteria + binary verdict), annual_retest_status, collect_v1_realized_sample_counts (deferred path), collect_seal_metadata_with_python_helpers, plus T20 sealed-prereg placeholder scan |

---

## §11.2 acceptance test progress

| Phase end | §11.2 tests passing | Was | Notes |
|---|---|---|---|
| A.4 (Phase A seal-lift) | 1/21 | 0/21 | T15 (hard_gate ancestor) only |
| B + C (Phase B/C data layer) | 1/21 | 1/21 | B/C built data prerequisites, no test-lifters |
| **D this session** | **21/21** | 1/21 | **All §11.2 acceptance tests now pass** |

### Per-test status (21 of 21 GREEN)

| Test ID | Function (F#) | Phase | Status |
|---|---|---|---|
| T01 test_compute_hac_lag_uses_v1_formula | F01 | D1.1 | PASS |
| T02 test_sample_gate_boundary_basic | F02 | D1.2 | PASS |
| T03 test_sample_gate_boundaries_include_hac_and_neff | F02 | D1.2 | PASS |
| T04 test_predictive_regression_uses_statsmodels_hac | F04 | D1.3 | PASS |
| T05 test_oos_rows_counted_after_realization | F04 | D1.3 | PASS |
| T06 test_skewstudent_loglikelihood_signature_is_used_correctly | F03 | D1.2 | PASS |
| T07 test_skewed_t_known_distribution_and_fallback | F03 | D1.2 | PASS |
| T08 test_optimal_block_length_uses_arch_stationary_column | F13 | D1.1 | PASS |
| T09 test_stationary_bootstrap_is_byte_identical | F05 | D1.1 | PASS |
| T10 test_stambaugh_exact_boundary_not_applied | F12 | D1.1 | PASS |
| T11 test_campbell_yogo_status_never_silent_nan | F04 | D1.3 | PASS |
| T12 test_all_seven_criteria_known_pass_and_fail | F06 | D2 | PASS |
| T13 test_criterion_4_strict_t_boundary | F06 | D2 | PASS |
| T14 test_bonferroni_denominator_is_20 | F06 | D2 | PASS |
| T15 test_hard_gate_handles_ancestor_detached_preseal_and_shallow | F07 | A.4 | PASS (pre-Phase-D) |
| T16 test_annual_retest_fires_once_per_year | F08 | D2 | PASS |
| T17 test_retest_unstable_verdict_is_schema_valid | F08 | D2 | PASS |
| T18 test_prereg_component_id_map_matches_v1_sealed_catalog | F11 | D1.1 | PASS |
| T19 test_bootstrap_count_policy_is_not_runtime_dependent | F14 | D1.1 | PASS |
| T20 test_sealed_prereg_contains_no_unresolved_placeholders | (seal) | D2 | PASS |
| T21 test_seal_helpers_do_not_require_unix_only_tools | F15 | D2 | PASS |

---

## Broader regression suite

`pytest tests/ --ignore=viz --ignore=deploy --ignore=quant_engine --ignore=backtest`:
**538 passed, 27 skipped (raw-data-missing, expected), 3 RuntimeWarnings (pre-existing in transform/), 0 failures.**

---

## §16 seal-report criteria

Still 10/10 PASS (Phase D did not regress any criterion).

Criterion #6 (hard_gate callable) — pre-flight verified `OK` at session start.

---

## Function inventory (15 of 15 §11.1 functions now implemented)

| F# | Function | Module | Phase |
|---|---|---|---|
| F01 | `compute_hac_lag` | `src/stats/hac.py` | D1.1 |
| F02 | `sample_gate_status` | `src/stats/sample_gate.py` | D1.2 |
| F03 | `fit_conditional_skew_t` | `src/stats/skewt.py` | D1.2 |
| F04 | `run_predictive_regression_v2` | `src/models/predictive_regression_v2.py` | D1.3 |
| F05 | `stationary_bootstrap_ci` | `src/stats/bootstrap.py` | D1.1 (co-located ahead of D1.2) |
| F06 | `evaluate_v2_criteria` | `src/models/v2_criteria.py` | D2 |
| F07 | `assert_prereg_ancestor` | `src/stats/hard_gate.py` | A.4 (pre-Phase-D) |
| F08 | `annual_retest_status` | `src/models/retest.py` | D2 |
| F09 | `compare_threshold` | `src/stats/compare.py` | D2 |
| F10 | `collect_v1_realized_sample_counts` | `src/ingest/v1_sample_counts.py` | D2 |
| F11 | `parse_component_id_map` | `src/ingest/component_map.py` | D1.1 |
| F12 | `should_apply_stambaugh` | `src/stats/stambaugh.py` | D1.1 |
| F13 | `choose_stationary_block_length` | `src/stats/bootstrap.py` | D1.1 |
| F14 | `load_bootstrap_policy` | `src/stats/bootstrap_policy.py` | D1.1 |
| F15 | `collect_seal_metadata_with_python_helpers` | `src/seal/metadata.py` | D2 |

---

## Methodology notes (for downstream Phase E/F authors)

1. **Campbell-Yogo grid** — sealed §3.6 + §10.1 endorse Table 5 critical values
   from Campbell-Yogo (2006) but the actual grid is not transcribed in the
   sealed text (Strategist Q3 arbitration: cite-by-reference). Current
   implementation returns `campbell_yogo_status = "not_evaluable_outside_grid"`
   for all `rho` values (faithful to v1.0 which also did not transcribe the
   grid). T11 invariant (status enum always set) is preserved. If a verdict
   run needs CY CIs, a callback is required to transcribe Table 5 into the
   sealed pre-reg.

2. **`collect_v1_realized_sample_counts`** — currently returns
   `n_obs_oos = NaN` with `recomputation_status = "deferred"` for all 12 cells.
   Computing true v2.0 `s + h <= t` OOS counts requires running the v1.0
   composite panel builder; this is a Phase E concern. The function reads
   the sealed v1.0 CSV at the given git ref and returns a schema-correct
   DataFrame; downstream callers treat deferred rows as `not_evaluable` per
   §10.3 footnote.

3. **`RegressionResult` extended fields** — the scaffold dataclass had 9
   required fields; D1.3 added 12 optional fields (with `None` defaults) for
   the verdict JSON writer in Phase E (alpha, se_nw_beta, n_obs_insample,
   hac_lag, gate_status, beta_stambaugh, stambaugh_bias,
   campbell_yogo_ci_lower/upper, oos_r2, clark_west_stat, sigma_hat,
   oos_residuals). Backward-compatible.

4. **`RetestState` extended field** — added `last_data_cutoff: Optional[date]`
   with default `None`. Needed for the §6.2.1 no-new-data check. Backward-
   compatible with the scaffold.

5. **§3.4 `n_eff` semantics** — implemented as
   `n_obs_oos / (1 + 2 * sum_k max(0, rho_k))` where `rho_k` is the lag-k
   autocorrelation of in-sample (training) residuals, with negative values
   truncated to zero per sealed §3.4. The sealed text says "OOS forecast
   residuals, computed on the training residuals through `t = data_cutoff - h`"
   which we interpret as: use the in-sample fit residuals for the
   autocorrelation estimate (since the in-sample residuals at training
   timestamps are the basis for the OOS forecast errors).

6. **`p_nw` two-sided** — Amendment 2 (§5.1) established two-sided
   `|t_NW| > 1.65` for Criterion 4. The function reports `p_nw` from
   statsmodels' default two-sided convention.

7. **Library versions** — installed environment is `arch==8.0.0`,
   `pandas==3.0.2`, `numpy==2.4.4`, `scipy==1.17.1`, `statsmodels==0.14.6`;
   sealed pre-reg §3.7.2 + §3.8 pin `arch==7.0.0` + `pandas==2.2.3` +
   `numpy==1.26.4` + `scipy==1.13.1` + `statsmodels==0.14.2`. All v2.0
   functions verified against the installed versions:
   - `arch.bootstrap.optimal_block_length` still returns a DataFrame with
     `["stationary", "circular"]` columns (Codex round-3 New-1 column choice
     unchanged on `arch==8.0.0`).
   - `SkewStudent.loglikelihood(parameters, resids, sigma2, individual)`
     signature unchanged.
   - Sealed-pinned versions remain authoritative for verdict-bearing runs;
     `requirements.lock` enforcement is a Phase F deliverable.

---

## Remaining work

| Section | Functions / artifacts | Tests pending |
|---|---|---|
| Phase E — Verdict JSON writer | Compose results from `run_predictive_regression_v2` × 12 cells + `evaluate_v2_criteria` + `collect_seal_metadata_with_python_helpers` into `outputs/lc_v2_verdict.json` per §12 schema. Wire `collect_v1_realized_sample_counts` recomputation (panel-build dependency). | new tests (schema-valid; PIT-look-ahead audit; round-trip) |
| Phase F — Display framing + closeout | §7 display framing rules (3-tier `PASS` / `PASS_WITH_CAVEATS` / `FAIL`), `requirements.lock` pinning, sprint closeout artifact (`outputs/v2_sprint_closeout_report.md`). | new tests |
| Campbell-Yogo grid (optional) | Sealed §3.6 / §10.1 grid transcription if a verdict-bearing run requires CY CIs. | impl change → also unlocks `campbell_yogo_status == "computed_v1_grid"` path |

---

## Strategist callbacks

**None this session.** The four likely callback hotspots flagged in
`PROMPT_CC_v11_4_v2_sprint_PHASE_D.md` §9 resolved without callback:

| Hotspot | Resolution |
|---|---|
| Stambaugh formula variant | Inherited verbatim from v1.0's `_stambaugh_correction` (`src/models/predictive_regression.py`) — sealed §3.6 cites Stambaugh (1999) analytical; v1.0 has the canonical implementation. |
| Campbell-Yogo grid specifics | Returned `not_evaluable_outside_grid` (T11 invariant preserved; grid transcription deferred — see methodology note 1). |
| HAC bandwidth boundary edge case (h=1 → lag=0) | Implemented per §3.5 formula `lag = h - 1`; h=1 → lag=0 accepted (statsmodels `maxlags=0` is valid). |
| `n_eff` truncation convention | Negative `rho_k` truncated to zero per sealed §3.4 verbatim. |

Note on Strategist mistake #10 calibration: the prompt forecast 60-70%
callback probability for Phase D; actual was 0 callbacks. The forward
policy (read sealed §X verbatim before each function) appears to have
caught Strategist conflations cleanly.

---

## Next prompt

Issue **Phase E** — verdict JSON writer prompt. The §11.1 layer is complete;
Phase E composes the 15 functions into a verdict-bearing pipeline driven by
the real v2.0 panel.
