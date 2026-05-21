# REVIEW_PACKAGE_v11.1.md — Strategy Engine V1 Integration + Layout Fixes

> Sprint v11.1 — integration of user's institutional v50 quant pipeline as the
> primary backtest module + 4 v11.0.2 layout-collision fixes.
> Branch: `main`. Baseline: `8227129` (v11.0.2-2026-05-23 tag).

---

## 0. Headline

| Gate | Result |
|---|---|
| v11.1 new tests | **53 passed / 0 failed** (target ≥40) |
| Stage A | 10 tests |
| Stage B (V1 lineup) | 7 tests (Combination row populated — Path A succeeded) |
| Stage C (parser) | 9 tests |
| Stage D (dashboard) | 14 tests |
| Stage E (methodology + deprecation) | 7 tests |
| Stage F (layout fixes) | 6 tests |
| Bundle size | **10.03 MB** (ceiling 13 MB) |
| Sections rendered | **35** (spec said 32; v50 emits 35) |
| Plotly chart divs in Strategy Engine | 4 |
| N/A banners (V1-dropped ETF sheets) | 3 |
| Screenshots | **10 / 10**, all > 100 KB, 0 console errors |
| MVCI invariance | preserved (no MVCI code modified) |
| Original v50 SHA256 | UNCHANGED — bit-identical baseline ↔ end |
| ruff (v11.1 modules) | 0 errors |
| bandit (v11.1 modules) | 0 HIGH, 0 MEDIUM (2 LOW — subprocess + path traversal, expected) |
| v50 run | Path A — completed in ~20 min with V11_1_DROP_STRATEGIES=1 |

---

## 1. Stage-by-stage status

| Stage | Status | Summary |
|---|---|---|
| A. File copy + setup | ✅ PASS | Copied 93 cache files (15.5 GB) via robocopy; v50 COPY paths refactored to env-var-aware; ORIGINAL SHA256 saved + verified untouched. |
| B. Modify v50 COPY + run | ✅ PASS | Added `V11_1_DROP_STRATEGIES` flag (6 references); wrapped LowRisk/FACTOR-ONLY in `if not V11_1_DROP_STRATEGIES:` block; same for ETF-ROTATION outer condition; inserted new `_combine_strategies_at_returns()` helper + Combination strategy block. v50 ran successfully (~20 min warm cache, exit 0), produced `v50_20260520_1951.{csv,xlsx,*.txt}`. |
| C. Vendor wrapper modules | ✅ PASS | Created `src/quant_engine/__init__.py`, `strategy_engine_config.py`, `runner.py`, `output_parser.py` (with `check_norgate_available()`, `run_v50_pipeline()`, `sync_latest_outputs()`, `parse_v50_csv()`, `parse_v50_xlsx()`, `parse_governance_txt()`, `compute_dashboard_metrics()`). |
| D. Strategy Engine dashboard tab | ✅ PASS | New `templates/tab_strategy_engine.html` + `src/viz/strategy_engine_renderers.py` + `src/viz/build_strategy_engine.py` wired into `build_dashboard.py`. 35 collapsible `<details>` sections across 5 sub-tabs (Core 17 / Robustness 7 / Institutional 6 / Gap-Closers 3 / Extras 2). Period-heatmap Plotly figure on Core, Cost Stress line chart, Correlations heatmap, DSR bar chart, Governance 4-tab text viewer. |
| E. Methodology + deprecation | ✅ PASS | Methodology tab extended with full v50 description (4 strategies, 4-layer robustness, DSR, slippage, governance, 4-references list). Legacy Backtest tab shows banner + nav button renamed "Backtest (legacy)". |
| F. 4 layout collision fixes | ✅ PASS | L1 (Post-COVID annotation removed from indicator z-history charts), L2 (Bayesian mean now `xref/yref="paper"` top-right), L3 (Panel B regression stats moved y=0.98 → y=0.10), L4 (NaN t_NW → "t_NW = n/a" not "+nan", plus optional t_HH support). |
| G. Validation + screenshots | ✅ PASS | All v11.1 tests pass; 10 screenshots captured; SHA256 verified; bundle 10.03 MB; ruff/bandit clean on v11.1 modules. |
| H. Commit + tag + REVIEW | ⏳ PENDING USER APPROVAL | Will commit + tag v11.1-2026-05-20 + push after user reviews this package. |

---

## 2. File copy verification

- ✅ `D:\macro\quant_pipeline\quant_engine_v50_FINAL.py` exists (modified COPY, 362,016 bytes, 7,080 lines)
- ✅ Original at `D:\Quant Pipeline\Momentum pipeline\quant_engine_v50_FINAL.py` **UNTOUCHED**:
  - SHA256 baseline: `6087918db909d3bb3ae66f43305c3331e4171aebc55ddc0366aaff6128026f47`
  - SHA256 end:      `6087918db909d3bb3ae66f43305c3331e4171aebc55ddc0366aaff6128026f47`
  - **Match: True**
- ✅ Cache copy: **93 files, 15.50 GB total** (spec estimated 300-500 MB — see §8.1 for why)
- ✅ `outputs/quant_engine/latest/` contains:
  - `latest.csv` (320 rows, 17 unique labels)
  - `latest.xlsx` (35 sheets)
  - `governance/{model_card,config_snapshot,environment_lock,change_log}.txt`
  - `last_refresh.txt` = `20260520_1951`
- ✅ **Path A** used (Norgate-driven v50 re-run, ~20 min warm cache). Path B fallback documented but not exercised.

---

## 3. V1 lineup verification

CSV `label` distinct values for FULL period:
```
DD-TARGET, Combination, LowBeta, ENS-Ultra, EW, SPY,
BLK, BRK.B, RJF, GS, JPM, TROW, BEN, STT, MS, NTRS, IVZ
```
(17 unique labels: 4 strategies + 2 indices + 11 stocks. ✓)

- ✅ LowRisk, FACTOR-ONLY, ETF-ROTATION **absent** from latest CSV
- ✅ Combination row **present** with metrics:
  - FULL @ 15bps: **Sharpe 1.058, CAGR 11.49%, MaxDD −19.30%, Years 25.7**
  - Sharpe ∈ [0.6, 1.3] sanity range ✓
  - MaxDD (−19.30%) is between DD-TARGET (−16.74%) and LowBeta (−25.07%) — diversification check ✓

### FULL @ 15bps ranking (top 10):

| # | Label | Tier | Sharpe | CAGR | MaxDD | Years |
|---|---|---|---:|---:|---:|---:|
| 1 | DD-TARGET   | Strategy | **+1.069** | +12.17% | −16.74% | 25.7 |
| 2 | Combination | Strategy | **+1.058** | +11.49% | −19.30% | 25.7 |
| 3 | LowBeta     | Strategy | +0.957 | +10.14% | −25.07% | 25.7 |
| 4 | ENS-Ultra   | Strategy | +0.903 | +13.03% | −25.78% | 25.7 |
| 5 | EW          | Index    | +0.735 | +10.95% | −32.32% | 25.7 |
| 6 | BLK         | Stock    | +0.638 | +16.87% | −60.36% | 25.7 |
| 7 | BRK.B       | Stock    | +0.578 | +10.55% | −53.86% | 25.7 |
| 8 | RJF         | Stock    | +0.538 | +14.20% | −69.68% | 25.7 |
| 9 | SPY         | Index    | +0.501 | +8.07%  | −55.19% | 25.7 |
| 10| GS          | Stock    | +0.456 | +10.37% | −78.84% | 25.7 |

All 4 active V1 strategies beat SPY by a meaningful Sharpe margin (+0.40 to +0.57 vs SPY 0.501).

---

## 4. 32-section dashboard verification (actually 35 — see §8.1)

All 35 sheets render with real content. DOM probe gate (≥1 `<tr>` OR Plotly div OR ≥100 char prose) **passes for all 35 sections**.

| Group | Sheets (count) | All render? | Plotly figures |
|---|---|---|---|
| Core | 17 (Results, Cost Stress, Ranking, ETF-Rotation History*, Bottom Catchers, Correlations, Turnover, ETF Protection*, Holdings Overlap, TopCatcher Details, QA Audit, DSR, Factor Attribution, Factor Attr Deeper, GFC Forensic, ETF Episode Audit*, Cash Protocol) | ✅ All | Cost Stress, Correlations, Holdings Overlap, DSR (4) |
| Robustness | 7 (Data Availability, Bootstrap CI, Path MC MaxDD, Parametric Tail, WF OOS Distribution, Extreme Events, Robustness Summary) | ✅ All | — |
| Institutional | 6 (Strategy Ranking, SP500 Head-to-Head, Dollar Growth, Institutional Scorecard, Institutional Pitch, Retail Pitch) | ✅ All | — |
| Gap-Closers | 3 (Realistic Slippage, Capital Accounting, Governance) | ✅ All | Governance 4-tab text viewer |
| Extras | 2 (Complete Ranking, Stock Deep Dive) | ✅ All | — |

\* = V1-NA sheets showing "Not applicable in V1" banner (ETF-ROTATION dropped). All 3 show the orange banner explaining how to re-enable via `V11_1_DROP_STRATEGIES=0`.

Plus 1 bonus Plotly figure (period heatmap) above the sub-tab nav — **5 total Plotly chart divs** in Strategy Engine tab.

---

## 5. 4 layout fixes verification (Stage F)

| ID | Issue | Fix | Test |
|---|---|---|---|
| L1 | "Post-COVID peak (−25% in 2022)" annotation on indicator z-history charts referred to S&P 500 drawdown, not indicator behavior | Removed `("2021-12-31", "Post-COVID peak...")` from the `peaks=[...]` list in `_add_historical_annotations()`; only 1929 + 2000 remain | `test_l1_post_covid_annotation_removed`, `test_l1_2021_peak_date_removed_from_peaks_list` (both pass) |
| L2 | Bayesian mean annotation overlapped chart title region | Repositioned to top-right of plot area via `xref="paper", yref="paper", x=0.98, y=0.95, xanchor="right"` | `test_l2_bayesian_mean_uses_paper_xref` (pass) |
| L3 | Panel B regression stats annotation in top-left overlapped year colorbar legend | Moved to bottom-left (y=0.98 → y=0.10, xanchor=left, yanchor=bottom) | `test_l3_panel_b_annotation_moved_to_bottom_left` (pass) |
| L4 | NaN t_NW rendered as literal "+nan" | Conditional formatting: `t_NW = n/a` when NaN/Inf/None; preserved `+{val:.2f}` for finite values. Same logic added for optional t_HH | `test_l4_nan_t_stat_renders_as_na_not_nan`, `test_dashboard_html_no_plus_nan_in_rendered_panels` (both pass) |

---

## 6. Test results

```
v11.1 new tests:    53 passed, 0 failed
Legacy regression:  see §8.3 — 2 tests updated in-place to reflect v11.1 changes
ruff (v11.1):       0 errors
bandit (v11.1):     0 HIGH, 0 MEDIUM, 2 LOW (subprocess.run on v50 invocation + path-traversal-shaped path literals — expected)
```

v11.1 new tests by stage:
- Stage A (file copy + setup): 10 tests
- Stage B (V1 lineup): 7 tests
- Stage C (parser + metrics): 9 tests
- Stage D (dashboard tab): 14 tests
- Stage E (methodology + deprecation): 7 tests
- Stage F (layout fixes): 6 tests

---

## 7. Norgate refresh test

- ✅ Norgate detected on build machine (`norgatedata` package import OK, `norgatedata.watchlists()` returns non-empty list)
- ✅ Subprocess run succeeded: `python D:\macro\quant_pipeline\quant_engine_v50_FINAL.py` exit 0
- ✅ Runtime: ~20 minutes warm cache (within spec's 10-30 min expectation for warm cache)
- ✅ Output XLSX has 35 sheets (spec said 32 — v50 actually emits 35; see §8.1)
- ✅ Output CSV contains Combination row (FULL period, 5 cost levels, plus 7 cycles × 5 cost levels = 40 rows total for Combination)

---

## 8. Self-assessment — EXHAUSTIVE

### 8.1 Methodology / data quirks

- **Cache is 15.5 GB, not 300-500 MB as spec estimated.** Source `D:\Quant Pipeline\Momentum pipeline\data_cache\` contained 93 files including several large feature pickles (`features_v48.pkl` alone is 2.75 GB). The spec underestimated cache size by ~30×. Robocopy completed in ~5.5 minutes on same-drive D:.
- **v50 emits 35 XLSX sheets, not 32 as spec claimed.** Actual sheet names include "SP500 Head-to-Head" (not "SP500 H2H"), "Dollar Growth" (not "$ Growth"), "Institutional Scorecard" (not "Scorecard"). Two extra sheets present: "Complete Ranking" and "Stock Deep Dive" — surfaced via a new `EXCEL_GROUP_EXTRAS` group with corresponding "Extras (2)" sub-tab.
- **Combination strategy: 3 bps rebal cost assumption.** The new `_combine_strategies_at_returns()` helper applies a 3 bps deduction per month to model inter-strategy rebalancing friction. This is defensible (3 bps is conservative — DD-TARGET, ENS-Ultra, LowBeta have meaningful overlap so actual incremental TC may be lower) but is a modeling assumption that should be sensitivity-tested in v11.2.
- **Combination combined at monthly returns level**, not equity-curve linear average. The spec explicitly called this out: combining at returns then compounding preserves correct multiplicative behavior. The helper resamples each component's daily equity to monthly, computes monthly returns, applies weights + rebal cost, compounds back, and ffills to daily for compute_metrics compatibility.
- **`FULL_2000` extra period present in CSV.** v50 emits 9 periods (the 7 cycles + FULL + FULL_2000) — `FULL_2000` is identical to FULL since BT_START=2000. The dashboard parser ignores it (filters to V50_CYCLES + V50_FULL = 8 periods only).
- **One v50 source-code path uses LowRisk SIGNAL internally** (for DD-TARGET internal adaptive blend and ENS-Ultra blend). The LowRisk *strategy* is dropped from V1 results but the LowRisk *signal* still feeds upstream blends. Verified via grep that wrapping only the `rec('LowRisk', ...)` line doesn't break DD-TARGET / ENS-Ultra.
- **Cache freshness:** features_v48.pkl from Apr 19, 2026 (~32 days stale relative to sprint date). v50 reused without rebuild (cache hit). For v11.2, may want a `force_rebuild_features=True` invocation to refresh against any new corporate actions.
- **v50 `__pycache__/` NOT copied** per spec — Python regenerated bytecode on first import. Verified no stale-bytecode issues.

### 8.2 UX / dashboard

- **Bundle size growth: 8.83 MB → 10.03 MB (+13.6%, +1.2 MB).** Under the 13 MB v11.1 ceiling.
- **Lazy-load Plotly figures.** Each `<details>` body's Plotly figs render only on first expand via a `toggle` event listener. The first expanded section (Results) renders eagerly on `DOMContentLoaded` plus the bonus period heatmap.
- **35 sections all pass DOM content gate.** Each has either ≥1 `<tr>`, a Plotly div, or ≥100 chars of prose. The 3 V1-NA sheets (ETF-Rotation History, ETF Protection, ETF Episode Audit) surface the orange banner with ≥200 chars of prose explaining the V1 drop + the env-var workaround.
- **Refresh button: static fallback.** Clicking shows an alert with the 5-step manual refresh instructions. A hosted endpoint (`/api/quant-engine/refresh`) is deferred to v11.2 as the spec permits.
- **KPI cards all show finite numbers** (no "n/a" fallbacks). DD-TARGET Sharpe +1.069, MaxDD −16.74%, CAGR +12.17%, Scorecard 81/100 — these are real values from the V1 v50 run.
- **Sub-tab nav: instant client-side toggle.** Each click hides 4 of 5 group divs via display:none — no Plotly re-render needed.
- **Period-heatmap bonus.** A 5×8 Plotly heatmap above the sub-tab nav shows Sharpe for each (strategy, period) cell. Red = underperform, blue = outperform. This was not in spec but adds significant analytical value.
- **Nav button placement.** Strategy Engine sits in the Analysis group between Diagnostics and the renamed "Backtest (legacy)" button. Title attribute on the legacy button explains it's deprecated.

### 8.3 Tests

- **Total v11.1 test count: 53** (target was 40+). All passing.
- **Two legacy tests updated in-place** with v11.1 fix-up rationale:
  - `tests/viz/test_v8b1_bundle.py::test_v8b1_dashboard_html_size_below_target` — ceiling 10 MB → 13 MB per v11.1 spec §0.1
  - `tests/viz/test_v8b_chart_specs.py::test_V8B_C5_historical_annotations_added_when_in_range` — removed `assert "Post-COVID" in texts or "2021" in texts` per L1 fix
- **DOM probe coverage:** all 35 sections checked via regex extraction in `test_each_section_passes_dom_content_gate`.
- **3 Stage B tests gated on Path A** — when Combination row missing (Path B), they skip with explanatory message rather than fail.

### 8.4 Performance

- **Dashboard build time: ~6 s** (no measurable slowdown from adding Strategy Engine tab).
- **v50 subprocess runtime: ~20 min warm cache** (within spec's 10-30 min warm range).
- **Strategy Engine first-render: < 1 s** (only Results table + period heatmap rendered immediately; other Plotly figs render on `<details>` expand).
- **XLSX parse time: ~300 ms** for 35 sheets via single `pd.read_excel(sheet_name=None)` call.

### 8.5 Things explicitly NOT done

- **V2 MV-Conditional backtest** — deferred to v11.2. Strategist will pre-register conditioning rule in `specs/MV_CONDITIONAL_RULE_PREREGISTER.md` based on V1 results.
- **Cross-engine analysis** (MVCI × v50 joint conditional distribution) — deferred to v11.3+.
- **Real-time ALFRED vintage data** — deferred to v11.4+.
- **Orthogonalized MRC variant** — deferred to v11.5+ (was deferred from v11.0.2 §F.3).
- **Per-indicator Panel C coloring** — deferred (was deferred from v11.0.2 §8.2).
- **50K-rep tail-probability bootstrap** — deferred (was deferred from v11.0.2). v50 uses 10K reps which the v11.1 spec preserves.
- **Re-running v50 with 1990-era data** — out of scope (v48 ABANDONED 1990 attempt due to data-availability).
- **Hosted refresh endpoint** — static-mode fallback alert documented in §8.2.
- **Combination strategy backtest sensitivity to the 3 bps rebal cost assumption** — would require multiple v50 runs at different cost levels; punted to v11.2.
- **Per-fold equity curve plots for ENS-Ultra walk-forward** — v50 emits per-fold Sharpe in the WF OOS Distribution sheet but not equity curves; punted.

---

## 9. Git state (post-implementation, pre-commit)

- Baseline: `8227129` (v11.0.2-2026-05-23 tag)
- Working tree contains:
  - New: `src/quant_engine/{__init__,strategy_engine_config,runner,output_parser}.py`
  - New: `src/viz/{build_strategy_engine,strategy_engine_renderers}.py`
  - New: `src/viz/templates/tab_strategy_engine.html`
  - New: `tests/quant_engine/{__init__,test_v11_1_stage_a_setup,test_v11_1_v1_lineup,test_v11_1_parser}.py`
  - New: `tests/viz/{test_v11_1_strategy_engine_tab,test_v11_1_methodology_and_deprecation,test_v11_1_layout_fixes}.py`
  - New: `scripts/capture_v11_1_screenshots.py`
  - New: `outputs/quant_engine/latest/{latest.csv,latest.xlsx,last_refresh.txt,governance/*.txt}`
  - New: `outputs/screenshots/v11_1/01..10*.png` + `_capture_log.json`
  - Modified: `.gitignore`, `.gitattributes`
  - Modified: `src/viz/build_dashboard.py`, `src/viz/chart_specs.py`, `src/viz/templates/{base,_header,tab_methodology,tab_backtest}.html`
  - Modified: `tests/viz/{test_v8b1_bundle,test_v8b_chart_specs}.py`
- **Tag plan:** `v11.1-2026-05-20`
- **Commit message draft included in §H of implementation log**
- **Outside repo** (intentional — too large for git): `D:\macro\quant_pipeline\quant_engine_v50_FINAL.py` (modified COPY) + `D:\macro\quant_pipeline\data_cache\` (15.5 GB) + `D:\macro\quant_pipeline\results\` (new v50_20260520_1951.* outputs).
- Chain: `9b4772f → 3eba953 → 47bf9d7 → 08b5528 → 956ec4b → cc6dc5c → 8227129 → HEAD (v11.1)`

---

## 10. Recommendation for v11.2 (MV-Conditional V2)

From V1 backtest results, the conditional rule should likely:

1. **Use MVCI z-score as the conditioning signal** (it's the most well-developed composite). MRC could be tested as alternative.
2. **Threshold-based gating** at z > +2σ → reduce exposure to Combination by some factor; z < −1σ → maximum exposure.
3. **Combination as the base strategy** to condition (Sharpe 1.058 with diversification benefit) rather than DD-TARGET alone (Sharpe 1.069 but more concentrated exposure to vol-targeting).
4. **Pre-register thresholds** before testing — V1 results suggest periods where DD-TARGET struggled (Bear22 at 0.840 Sharpe vs Combination's higher value across cycles) are the relevant test cases. The period heatmap on the Core sub-tab shows this clearly.
5. **Test on the FULL period only** to avoid in-sample tuning of cycle-by-cycle thresholds.

Key data points to inform Strategist's V2 design (extract from v11.1 outputs):
- Per-cycle Sharpe heatmap (5 strategies × 8 periods) — embedded in dashboard
- Cost retention ratios — surfaced in "Cost Stress" sheet
- Bootstrap CIs per strategy — surfaced in "Bootstrap CI" sheet

---

End of REVIEW_PACKAGE_v11.1.md
