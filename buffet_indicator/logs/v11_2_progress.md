# v11.2 progress log — multi-session resume protocol (§16.4)

> Session 1: 2026-05-21 (Claude Opus 4.7).
> Pre-registration SHA: `a90b02d` (committed BEFORE V2 backtest run, per §1.4).

## Completed stages

### Stage 1 — Pre-registration ✓
- `specs/MV_CONDITIONAL_RULE_PREREGISTER.md` written exactly per §2.1.
- Committed at `a90b02d` BEFORE any V2 backtest code or run.
- SHA recorded at `logs/v11_2_prereg_sha.txt`.
- 3/3 tests pass (`tests/quant_engine/test_v11_2_stage_1_prereg.py`).

### Stage 2 — V2 backtest implementation ✓
- `src/quant_engine/mv_conditional.py` — PIT z-score, 3 rules (R-PRIMARY, R-ALT1, R-ALT2),
  apply_mv_conditional (paired month-shift + 3bps transition cost), data loaders.
- `src/quant_engine/v2_metrics.py` — CAGR/Sharpe/Sortino/MaxDD/Calmar + 120-row
  emitter (`outputs/quant_engine/latest/v2_latest.csv`).
- v50 COPY (`D:\macro\quant_pipeline\quant_engine_v50_FINAL.py`) surgically
  patched to emit per-period × per-cost combo monthly returns CSVs when env
  `V11_2_EXPORT_RETURNS=1`. V11_1_DROP_STRATEGIES gate preserved.
- 8/8 tests pass (`tests/quant_engine/test_v11_2_stage_2_v2_backtest.py`).

### Stage 3 — V1-vs-V2 statistical tests ✓
- `src/quant_engine/stats_v1_v2.py` — Jobson-Korkie + Memmel, White's Reality
  Check (stationary bootstrap), Holm-Šidák step-down, Bootstrap CI for Sharpe
  diff. Builder emits `outputs/quant_engine/latest/v2_statistical_tests.csv`.
- 4/4 tests pass (`tests/quant_engine/test_v11_2_stage_3_stats.py`).
- **Empirical finding** (REJECTS R-PRIMARY per pre-reg §3.3 falsifiability):
  R-PRIMARY's `+1.5σ` MVCI threshold never fires in 2000-2026 (MVCI max in
  this window is 1.43; +1.5σ only reached in 2026-05-31 outside combo window).
  R-ALT1 (+2.0σ MVCI) also never fires. R-ALT2 (continuous gradient) is the
  only rule that produces V2 ≠ V1 (Sharpe diff = -0.013, worse than V1).
  Per pre-reg: V2 ships as DIAGNOSTIC view with disclosure.

### Stage 12 — pushState routing ✓
- `src/viz/templates/_header.html`: switched `history.replaceState` →
  `history.pushState` with state={tab,group}, added `popstate` listener that
  restores tab from state object (or falls back to hash). Initial entry seeded
  via `replaceState` so the first `popstate` has somewhere to land.
- 3/3 tests pass (`tests/viz/test_v11_2_stage_12_routing.py`).

### Stages 9-11 — Institutional upgrades (4 of 6 done) ⚡
- `src/quant_engine/analytics_core.py` — shared StrategyReturns container,
  `compute_bootstrap_ci`, `compute_conviction_triple`, `load_all_strategy_returns`.
- Upgrade 1 (PIT compliance audit) — done; test grep-audits v11.2 code.
- Upgrade 2 (Bootstrap CI infrastructure) — done; reproducible-with-seed test passes.
- Upgrade 3 (Conviction triple) — done; sanity-check test passes.
- Upgrade 4 (V1-vs-V2 stat tests) — done (= Stage 3 above).
- Upgrade 5 (Macro regime overlay) — DEFERRED (depends on Surface 2 / Drawdowns).
- Upgrade 6 (Falsifiability docs HTML) — DEFERRED (depends on Surfaces being built).
- 6/8 tests pass + 2 skipped placeholders.

## Test totals (session 1)
- 24 v11.2 tests passing, 2 skipped (placeholders for Surfaces 2/9).
- All 35 pre-existing quant_engine tests still pass (no regression there).

## Outstanding work — pick up here in Session 2

### Blocking on v50 background completion
- v50 with `V11_1_DROP_STRATEGIES=1 V11_2_EXPORT_RETURNS=1` was started but
  took longer than expected (>25 min). At session end, 8 of 40 combo CSVs
  had been emitted (FULL @ 15bps + 7 cycles @ 15bps + FULL @ 30bps).
- The current `v2_latest.csv` has 48 of 120 non-NaN rows (just the 15bps + partial 30bps).
- **Action for resume**: confirm v50 finished (or re-launch), then re-run
  `python scripts/v11_2_build_v2_outputs.py` to refresh both CSVs with all
  120 valid rows. All 24 currently-passing tests will continue to pass.

### Stages 4-8 — Extended Analytics (NOT STARTED) ⛔
- 9 surfaces × 6 strategies × ~2h each = 16-22 hours, well beyond single-session
  budget. Architecture stub exists (`src/quant_engine/analytics_core.py` with
  `StrategyReturns` + `load_all_strategy_returns`) but per-surface HTML
  templates, Plotly charts, KPI tables, drawdown enumeration, etc. are NOT
  built.
- Per spec §1.1 (NO scope cuts), a `BLOCKED_v11_2_stages_4_8_session_budget.md`
  is filed alongside this log so the gap is explicit.

### Stages 9-11 — remaining institutional upgrades
- Upgrade 5 (Macro regime overlay) — implement after Surface 2 lands.
  `tag_episodes_with_macro_regime()` skeleton would consume the drawdown
  episode DataFrame and join `mvci_z_at_peak` / `mrc_z_at_peak`.
- Upgrade 6 (Falsifiability HTML template) — create
  `src/viz/templates/_falsifiability_blurb.html` per spec §8.6 once surfaces
  exist to attach it to.

### Stage 13 — Validation + screenshots (NOT STARTED) ⛔
- Requires dashboard rebuild + 20 v11.2 screenshots. Cannot capture
  screenshots of Extended Analytics surfaces that don't exist yet.
- Console error sweep + v50 SHA256 verification CAN run today.

### Stage 14 — Final commit + tag + push + REVIEW_PACKAGE
- Defer until Stages 4-8 complete (or until user decides to ship partial).
- §8 self-assessment will need ≥ 50 bullets per spec §1.9.

## Files modified / created in Session 1

### Committed (a90b02d)
- `buffet_indicator/specs/MV_CONDITIONAL_RULE_PREREGISTER.md`

### Working tree, NOT yet committed (Session 1 WIP)
New source:
- `src/quant_engine/mv_conditional.py`
- `src/quant_engine/v2_metrics.py`
- `src/quant_engine/stats_v1_v2.py`
- `src/quant_engine/analytics_core.py`
- `scripts/v11_2_build_v2_outputs.py`

New tests:
- `tests/quant_engine/test_v11_2_stage_1_prereg.py`
- `tests/quant_engine/test_v11_2_stage_2_v2_backtest.py`
- `tests/quant_engine/test_v11_2_stage_3_stats.py`
- `tests/quant_engine/test_v11_2_stage_9_11_upgrades.py`
- `tests/viz/test_v11_2_stage_12_routing.py`

Modified template:
- `src/viz/templates/_header.html` — pushState + popstate listener.

Generated outputs (regenerable from v50):
- `outputs/quant_engine/latest/v2_latest.csv` (120 rows; 48 currently non-NaN)
- `outputs/quant_engine/latest/v2_statistical_tests.csv` (3 rows)
- `logs/v11_2_prereg_sha.txt`
- `logs/v11_2_v50_run.log`

### Outside buffet_indicator/ (untracked, will stay so unless user opts in)
- `D:\macro\quant_pipeline\quant_engine_v50_FINAL.py` — surgical EXPORT_RETURNS
  hook added (V11_1_DROP_STRATEGIES gate preserved verbatim).
- `D:\macro\quant_pipeline\results\v50_v11_2_combo_monthly_returns_*.csv` (8 files
  at session end, expected 40 when v50 completes).

## Pre-reg integrity reminder
The MV-Conditional rule definitions (R-PRIMARY, R-ALT1, R-ALT2) were committed
at `a90b02d` BEFORE any V2 backtest code executed. ANY change to those
definitions in Session 2 requires writing
`specs/MV_CONDITIONAL_RULE_PREREGISTER_AMENDMENT_v2.md` + a `DECISIONS.md`
entry per §1.4 of the prompt and §8 of the pre-reg file itself.
