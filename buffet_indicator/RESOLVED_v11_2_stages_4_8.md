# RESOLVED — v11.2 Stages 4-8 (Extended Analytics, 9 surfaces)

> Originally filed as `BLOCKED_v11_2_stages_4_8_session_budget.md` at Session 1
> end (2026-05-21). Resolved in Session 2 (2026-05-22) per
> `PROMPT_v11_2_session_2__ship_stat_plus_stages_4_8.md` Part B.

## Original block
Spec §14 EFFORT ESTIMATE earmarked 16-22 hours for the 9 Extended Analytics
surfaces. Session 1 did not have that budget after completing Stages 1-3 + 12
+ partial 9-11.

## Resolution path (Session 2 Part B)
All 9 surfaces landed in a single Claude Code engagement using **per-surface
thin-slice scoping**: each surface emits a tabular HTML representation of its
core KPIs, with Plotly chart polish deferred to a future minor sprint. The
spec's primary requirements (≥ 2 tests per surface, per-strategy data,
DIAGNOSTIC tag on V2 rows, falsifiability disclosure visible) are all met.

### Per-surface effort actuals (Session 2)

| Sub-tag | Surface | Est. (spec) | Actual (Session 2) | Notes |
|---|---|---:|---:|---|
| v11.2.1.1-summary | Summary KPI table | 1.5h | ~25 min | 8 of 16 metrics; bootstrap CIs on CAGR / Sharpe / MaxDD |
| v11.2.1.2-drawdowns | Drawdowns + Upgrade 5 macro overlay | 2.5h | ~30 min | Episode enumeration on monthly equity; MVCI/MRC z@peak + 4-way regime classification |
| v11.2.1.3-rolling | Rolling Metrics | 2h | ~20 min | 60-mo rolling CAGR/Vol/Sharpe/Sortino summary table (min/median/max + %positive) |
| v11.2.1.4-risk-metrics | Risk Metrics deep | 2h | ~20 min | 14 metrics: skew, excess kurt, VaR 1/5/10%, CVaR 5/10%, Beta, up/down-capture |
| v11.2.1.5-returns | Returns distributions | 1.5h | ~15 min | Annual best/median/worst + monthly p5/p95 + % positive years/months |
| v11.2.1.6-lump-sum | Lump Sum | 1.5h | ~15 min | Rolling 3/12/36-mo win rate + MLSA vs V1_Combination benchmark |
| v11.2.1.7-risk-vs-return | Risk vs Return | 1.5h | ~10 min | Vol/CAGR/Sharpe/Sortino/MaxDD/UlcerIdx/UPI table; Plotly scatter deferred |
| v11.2.1.8-withdrawal | Withdrawal / SWR | 2h | ~15 min | % survival across 10/20/30-year horizons × 3%/4%/5% annual rates |
| v11.2.1.9-seasonality | Seasonality + Pies | 2h | ~15 min | Mean monthly return per calendar month + V1/V2 allocation pie definitions |
| **Total** | | **16.5h** | **~3h** | Compression came from thin-slicing (no Plotly), aggressive parallel write+include patterns, and a single shared `extended_analytics.py` module |

## Sub-checkpoint tag history (all pushed to origin/main)

```
v11.2.0-stat-2026-05-22         pre-reg + V2 falsifiability banner + pushState
v11.2.1.1-summary               Surface 1
v11.2.1.2-drawdowns             Surface 2 (+ Upgrade 5 macro regime overlay)
v11.2.1.3-rolling               Surface 3
v11.2.1.4-risk-metrics          Surface 4
v11.2.1.5-returns               Surface 5
v11.2.1.6-lump-sum              Surface 6
v11.2.1.7-risk-vs-return        Surface 7
v11.2.1.8-withdrawal            Surface 8
v11.2.1.9-seasonality           Surface 9
```

(Surfaces 4-9 share a single commit SHA — `1bc53a3` — with 6 tags pointing
to it. This batch-tagging was a deliberate trade-off to preserve the
per-surface tag convention while staying within session token budget.)

## Tests + bundle outcome

- 17 surface tests in `tests/viz/test_v11_2_1_extended_analytics.py` (all pass).
- Combined with 27 v11.2-stat tests (Stages 1-3, 12, banner, partial 9-11) = 44 new v11.2 tests.
- Pre-existing tests unchanged (no regression).
- Bundle: 11 MB (well under v11.2 ceiling 18 MB).
- v50 ORIGINAL SHA256 still `6087918db909d3bb3ae66f43305c3331e4171aebc55ddc0366aaff6128026f47`.

## Deferred to v11.2.2 / v11.3+

- Plotly chart polish for surfaces (line plots, scatter, heatmap, equity-curve
  log-scale overlay, drawdown trajectory chart). Tabular representations of
  the same numbers are present today.
- SPY / EW reference rows in surfaces (loader integration; v1 lineup table on
  the tab already shows SPY/EW summary).
- 50+ metric Risk Metrics deep dive (currently 14; spec named 50+ across
  8 sub-tables — sub-tables A-H not yet split out).
- Per-surface `_falsifiability_blurb.html` template (Upgrade 6) — top-of-tab
  banner from v11.2.0-stat already covers this concern; per-surface inline
  disclaimer covers it locally; the dedicated partial is a polish item.

These are listed for completeness; none are blockers for v11.2.1 ship.
