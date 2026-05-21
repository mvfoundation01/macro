# BLOCKED — v11.2 Stages 4-8 (Extended Analytics, 9 surfaces)

## What's blocked
Stages 4-8 of `PROMPT_v11_2__combined_mega_spec.md`: implement 9 Extended
Analytics surfaces (Summary, Drawdowns, Rolling Metrics, Risk Metrics deep,
Returns, Lump Sum, Risk-vs-Return, Withdrawal, Seasonality + Allocation Pies)
× 6 strategies (V1_Combination, V2_R-PRIMARY, V2_R-ALT1, V2_R-ALT2, SPY, EW).

## Why
The spec itself (§14 EFFORT ESTIMATE) earmarks 16-22 hours for Stages 4-8.
That is by an order of magnitude larger than any other single stage in this
sprint and exceeds the realistic budget of a single Claude Code session even
with parallel tool calls and aggressive prioritization.

Per spec §1.1 ("NO scope cuts ... If any stage harder than expected, write
`BLOCKED_v11_2__stage_X_<reason>.md` and STOP. Do not silently skip work."),
this file documents the gap explicitly rather than burying it.

## What WAS completed adjacent to Stages 4-8
- `src/quant_engine/analytics_core.py`: the shared compute primitives module
  envisioned in spec §6.2 (`StrategyReturns` dataclass,
  `load_all_strategy_returns`, `stationary_bootstrap_indices`,
  `compute_bootstrap_ci`, `compute_conviction_triple`).
- All 6 strategy returns are derivable today via `load_all_strategy_returns()`
  once v50's full set of cost-level combo CSVs is in place.
- Statistical tests (Stage 3, Upgrade 4) are wired and operating; the
  framework that Stages 4-8 build atop is intact.

## Resume protocol (Session 2+)
1. Read `logs/v11_2_progress.md` for full context.
2. Decide per-surface implementation order. Spec's recommended order is
   Summary → Drawdowns → Rolling → Risk Metrics → Returns → Lump Sum →
   Risk-vs-Return → Withdrawal → Seasonality+Pies.
3. For each surface, gate the work behind a sub-checkpoint so partial
   sessions can still commit a tested, rendering surface.
4. Spec §6.3-§6.11 describes each surface's KPIs, tests, and chart contracts.
5. CHECKPOINT 2 (§7) is the final gate — verify all 9 surfaces render, ≥ 18
   per-surface tests pass, bundle ≤ 18 MB.

## Strategist contact protocol (per §16.1)
If the Strategist's original intent is unclear when resuming a particular
surface, file a `BLOCKED_v11_2_stage_<X>_<reason>.md` before guessing.
Pre-registration integrity (§1.4) is independent of Stages 4-8 and remains
preserved by `a90b02d`.
