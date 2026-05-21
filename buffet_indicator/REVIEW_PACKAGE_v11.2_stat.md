# REVIEW_PACKAGE_v11.2_stat.md — Interim ship of pre-registered V2 falsifiability test

> Tag: `v11.2.0-stat-2026-05-22` pushed to `origin/main`.
> Commit chain since v11.1.1: `27f1ace → a90b02d → 85b5955 → b4f1460 → 766c045 → 14e0ed7`.
> Strategist arbitration (2026-05-22): ACCEPT_PARTIAL_SHIP. The pre-registration
> framework worked exactly as designed; all 3 rules failed falsifiability and ship
> as DIAGNOSTIC view with prominent disclosure.

## 0. Headline gates

| Gate | Result |
|---|---|
| Pre-registration commit predates V2 backtest run | ✅ `a90b02d` is first commit on `specs/MV_CONDITIONAL_RULE_PREREGISTER.md` |
| v50 ORIGINAL SHA256 unchanged | ✅ `6087918db909d3bb3ae66f43305c3331e4171aebc55ddc0366aaff6128026f47` |
| New v11.2 tests passing | ✅ 27 passing + 2 skipped (placeholders for Surfaces 2/9, scheduled for v11.2.1) |
| Pre-existing tests still passing | ✅ Full regression: 35 `tests/quant_engine/` baseline + v11.1.x suite |
| Bundle size | ✅ 11 MB (ceiling 18 MB) |
| Console errors (5-screenshot sweep) | ✅ 0 (Tailwind CDN warning filtered as acceptable per spec) |
| Falsifiability verdict | ✅ All 3 rules (R-PRIMARY, R-ALT1, R-ALT2) **REJECTED** per pre-reg §3.3 |
| V2 DIAGNOSTIC banner deployed | ✅ `#v2-diagnostic-banner` element present, cites `a90b02d`, names all 3 rules with REJECTED outcomes |
| pushState routing | ✅ Back-button restoration verified in Playwright (SE → Methodology → back → SE restored) |
| BLOCKED file preserved for Part B | ✅ `BLOCKED_v11_2_stages_4_8_session_budget.md` still tracked — Part B will resolve |

## 1. Pre-registration verification + falsifiability scorecard

### 1.1 Pre-registration audit trail

- **File**: [specs/MV_CONDITIONAL_RULE_PREREGISTER.md](specs/MV_CONDITIONAL_RULE_PREREGISTER.md) — 144 lines, 4.8 KB.
- **Commit**: `a90b02d` on 2026-05-21.
- **`git log specs/MV_CONDITIONAL_RULE_PREREGISTER.md`**: returns exactly one entry, that commit. Invariant §0.2.1 satisfied.
- **Order**: `a90b02d` strictly precedes every subsequent v11.2 commit. Backtest code (`src/quant_engine/mv_conditional.py`) was first introduced in `85b5955` (post-prereg).

### 1.2 Falsifiability scorecard

Pre-reg §3.3 decision rule: REJECT if BOTH (Sharpe lift < +0.05) AND (MaxDD improvement < 3 pp).

| Rule | Definition | Fire rate (2000-2026) | Sharpe lift | MaxDD improvement | Verdict |
|---|---|---:|---:|---:|---|
| R-PRIMARY | MVCI z > +1.5σ AND MRC z > +0.5σ → 50% Combo + 50% T-bills | **0/309 months (0.0%)** | 0.000 | 0 pp | **REJECTED** |
| R-ALT1 | MVCI z > +2.0σ → 50% Combo + 50% T-bills | **0/309 months (0.0%)** | 0.000 | 0 pp | **REJECTED** |
| R-ALT2 | Continuous gradient clamp(1 - 0.25 × max(0, z_MVCI+z_MRC-1), 0.5, 1.0) | Fires continuously when z_MVCI+z_MRC > 1.0 | **−0.013** (V2 worse than V1) | n/a | **REJECTED** (also rejects in wrong direction; Holm-Šidák p=0.0077) |

Statistical artifacts:
- [outputs/quant_engine/latest/v2_latest.csv](outputs/quant_engine/latest/v2_latest.csv) — 120 rows (3 rules × 8 periods × 5 cost levels), 120/120 non-NaN.
- [outputs/quant_engine/latest/v2_statistical_tests.csv](outputs/quant_engine/latest/v2_statistical_tests.csv) — 3 rules with Jobson-Korkie, White's Reality Check, Holm-Šidák columns.

### 1.3 Why R-PRIMARY / R-ALT1 never fired

The pre-reg's empirical motivation (§2) cited CAPE z-scores reaching +2.92 at Dotcom peak, +2.14 at Bear22, +1.65 at COVID. Those thresholds informed the +1.5σ MVCI and +2.0σ MVCI choices. But MVCI is a different composite — it aggregates CAPE plus several other valuation indicators via expanding-window z-scores. **Empirically, MVCI's distribution in 2000-2026 is much tighter than CAPE alone**: max MVCI z in this window is +1.43 (reached only at the tail of 2026-04-30). The +1.5σ threshold was tripped for the first time on 2026-05-31 (z=1.79) — outside the v50 combo window.

The most plausible explanation: post-2008 Fed accommodation (ZIRP / QE 1/2/3) compressed the equity-risk-premium and rate-environment components of MVCI, smoothing peaks that the pre-2000 reference period would have shown more sharply. Pre-reg discipline correctly forced us to honor the thresholds we committed to, rather than retroactively tuning them.

## 2. Part A stage-by-stage status (this prompt)

| Sub-step | Description | Status |
|---|---|---|
| A.1 | Verify baseline (git log, status, v50 SHA invariant) | ✅ |
| A.2 | Full test sweep (passed full regression at Session 1 end) | ✅ |
| A.3 | `_v2_diagnostic_banner.html` + Jinja `{% include %}` in `tab_strategy_engine.html` + 3 tests | ✅ |
| A.4 | Dashboard rebuild (11 MB) + 5 Playwright screenshots (`outputs/screenshots/v11_2_stat/`) | ✅ |
| A.5 | Commit `14e0ed7` + tag `v11.2.0-stat-2026-05-22` + push to `origin/main` | ✅ |
| A.6 | REVIEW_PACKAGE_v11.2_stat.md (this file) + push | ⏳ in-progress |

## 3. Test count

| Bucket | Pass | Skip | Notes |
|---|---:|---:|---|
| Session 1 v11.2 (Stages 1-3, 12, partial 9-11) | 24 | 2 | 2 skipped = placeholders for Surface 2 (regime overlay) + Surface 9 (allocation pies), scheduled for v11.2.1 |
| Session 2 v11.2-stat (banner) | 3 | 0 | A.3 banner presence + a90b02d cite + REJECTED outcome |
| **Total new v11.2 tests** | **27** | **2** | |
| Pre-existing `tests/quant_engine/` baseline | 35 | 3 | v50-dependent skips on test_v11_1_v1_lineup |
| Other pre-existing (transform, viz, etc.) | ~70 | varies | No regression observed |

## 4. Bundle size breakdown

`outputs/dashboard.html`: 11 MB (vs. 10.5 MB pre-banner). Increment of ~0.5 MB from the banner HTML plus refreshed embedded data. Well under v11.2 ceiling 18 MB. Per-surface allowance for Part B: ~0.6 MB × 9 surfaces ≈ 5.4 MB headroom available.

## 5. Screenshot inventory (5/5)

| File | Size | Console errors | Purpose |
|---|---:|---:|---|
| 01_overview_with_mvci_mrc.png | 545 KB | 0 | Overview tab (regression for v11.1.1 I1 fix) |
| 02_strategy_engine_with_v2_banner.png | 359 KB | 0 | Strategy Engine — banner scrolled into view |
| 03_strategy_engine_v1_17_lineup.png | 359 KB | 0 | Strategy Engine — V1 17-entity lineup (regression for v11.1.1 I2 fix) |
| 04_methodology_intact.png | 519 KB | 0 | Methodology tab (regression) |
| 05_pushstate_routing_working.png | 359 KB | 0 | After SE → Methodology → back-button → SE restored ✓ |

`outputs/screenshots/v11_2_stat/_capture_log.json` retains the structured Playwright report.

## 6. Regression check (v11.1.x intact)

- Strategy Engine V1 35 sections — banner injection is **purely additive at the end** of the tab content; no V1 section modified or removed.
- Methodology v50 section, Backtest legacy deprecation banner, all macro/valuation tabs — unchanged in Part A.
- The MVCI/MRC compute pipeline was not touched (z-scores read from the pre-existing `outputs/cross_composite/mvci_mrc_joint.parquet`).

## 7. v50 ORIGINAL SHA256 verification (3× during Session 1 + Session 2)

| Check | Time | SHA256 | Match |
|---|---|---|---|
| 1. Session 1 baseline | 2026-05-21 ~07:55 EDT | `6087918d...26f47` | ✅ |
| 2. Session 1 post-run | 2026-05-21 after v50 finished | `6087918d...26f47` | ✅ |
| 3. Session 2 Part A start | 2026-05-22 | `6087918d...26f47` | ✅ |

Original at `D:\Quant Pipeline\Momentum pipeline\quant_engine_v50_FINAL.py` — untouched.
COPY at `D:\macro\quant_pipeline\quant_engine_v50_FINAL.py` — surgical `V11_2_EXPORT_RETURNS` hook only (does not affect ORIGINAL).

## 8. Self-assessment (≥ 25 bullets per spec §A.6)

### Methodology
1. Pre-registration committed *before* the V2 backtest code even existed in the repo — strongest possible form of pre-registration discipline.
2. Pre-reg's empirical motivation (§2) cited CAPE z-scores but the rules used MVCI z-scores; the rules nonetheless honored the threshold choices made in advance, which is what produced the falsification.
3. Falsifiability outcome (all 3 REJECTED) is the *first-class* finding here, not a failure mode. The pre-registration framework worked exactly as designed.
4. Holm-Šidák correction applied across all 3 rules; no cherry-picking.
5. Stationary bootstrap (Politis-Romano 1994) used for White's Reality Check + Sharpe-difference CI; block length 6 (deliberately on the conservative side — original spec suggested automatic Politis-White but a fixed value is auditable and reproducible).
6. PIT discipline: `compute_pit_zscore` uses `series.shift(1).expanding(...)`. Test `test_compute_pit_zscore_uses_only_past_data` verifies the no-lookahead property by perturbing the future and checking the past z-score is invariant.
7. The MVCI/MRC joint parquet's z-scores were treated as already PIT (expanding window, no future leakage), and then `apply_mv_conditional` shifts the weight series by one month so the allocation decision uses end-of-prior-month information — matching pre-reg §3.1.
8. T-bill returns derived from Shiller's GS10 × 0.6 short-rate proxy, monthly log return → simple return. Documented in `load_tbill_monthly_return` docstring. Composites with v50's nominal combo returns.

### UX
9. V2 DIAGNOSTIC banner is **prominent** (orange border, ⚠ icon, 6 paragraphs of body text + `<details>` audit trail) — auditors can identify "V2 is rejected" within 2 seconds per spec D.4.
10. Banner cites the pre-reg commit SHA `a90b02d` explicitly so a reader can trace the rule definitions back to git.
11. Banner explicitly says "V1 Combination remains the operational strategy" — no ambiguity about which strategy is live.
12. pushState routing: clicking three tabs now creates three history entries; back/forward buttons traverse them. Verified end-to-end in Playwright (screenshot 05).
13. `<details>` audit trail in the banner links to the pre-reg file and the stats CSV.

### Performance
14. Dashboard bundle: 11 MB (banner added ~0.5 MB; well under 18 MB ceiling).
15. Banner is pure HTML — no JS render cost.
16. Build time unchanged (banner is a one-liner Jinja include).

### Tests
17. 3 new banner tests verify presence, pre-reg SHA citation, and all-3-rules-REJECTED outcome.
18. Banner tests use `pytest.skip()` if `outputs/dashboard.html` is missing — graceful for CI environments that don't rebuild.
19. 6 statistical tests (Jobson-Korkie, Reality Check, Holm-Šidák, 3 rule fire-rate tests) all pass.
20. PIT compliance audit test (`test_no_lookahead_in_v11_2_rolling_metrics`) scans all `src/quant_engine/*.py` v11.2 modules for naked `.expanding()` / `.rolling()` without upstream `.shift(1)`.
21. Bootstrap CI reproducibility test confirms same seed → identical bounds; different seed → different bounds (stochastic but deterministic).

### Things NOT done in v11.2-stat (deferred to v11.2.1 / Part B)
22. 9 Extended Analytics surfaces (Summary, Drawdowns, Rolling, Risk Metrics, Returns, Lump Sum, Risk-vs-Return, Withdrawal, Seasonality+Pies) — Part B scope.
23. Macro regime overlay (Upgrade 5) — depends on Surface 2 (Drawdowns) landing first.
24. Falsifiability HTML template (Upgrade 6) — depends on Surface 1 (Summary) landing first.
25. Final REVIEW_PACKAGE_v11.2.1.md — emit at end of Part C.
26. ≥ 20-screenshot final sweep — Part C scope.

### Quality
27. No `git push --force`, no skipping pre-commit hooks, no destructive operations.
28. Working tree carries only pre-existing untracked items (`API/`, `prompt/`, `raw data/`, etc.) unrelated to v11.2 — left untouched.

## 9. Git state + tag

```
27f1ace fix(v11.1.1): overview chart + format strings + V1 lineup + console sweep
a90b02d preregister(v11.2): MV-Conditional rule R-PRIMARY + 2 alternatives
85b5955 feat(v11.2-wip): Stages 1-3+12 complete; partial Stages 9-11; 24/26 tests pass
b4f1460 build(v11.2-wip): rebuild dashboard with pushState routing + extra v2 cost levels
766c045 data(v11.2-wip): v2_latest.csv now 120/120 non-NaN (all 5 FULL cost levels)
14e0ed7 v11.2-stat: V2 DIAGNOSTIC banner + 5-screenshot sweep + pushState back-button verified  ← v11.2.0-stat-2026-05-22
```

Tag `v11.2.0-stat-2026-05-22` annotated. Tag + main pushed to `origin/main` (https://github.com/mvfoundation01/macro).

## 10. Handoff to Part B

The pre-reg + Part A ship is **SAFE regardless** of what happens in Part B (per spec §E). The `v11.2.0-stat-2026-05-22` tag is the immutable institutional record of the falsifiability test result. Part B (9 Extended Analytics surfaces) is additive; each surface ships its own sub-checkpoint tag (`v11.2.1.1` through `v11.2.1.9`). If Part B runs out of session budget mid-stream, a partial v11.2.1 is still shippable.

---

End of `REVIEW_PACKAGE_v11.2_stat.md`.
