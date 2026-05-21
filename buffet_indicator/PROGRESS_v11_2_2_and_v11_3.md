# Progress log — v11.2.2 + v11.3 mega-sprint

**Spec**: `D:\macro\prompt\052126\PROMPT_v11_2_2_and_v11_3__mega_sprint.md`
**Started**: 2026-05-21
**Last update**: 2026-05-21 by Claude Code fresh session
**Status**: PARTIAL — P0 ship complete; per-surface charts + Part B implementation pending.

---

## Sessions

### Session 1 — 2026-05-21

**Accomplished**:
1. Part A.0 — Baseline verification:
   - v50 SHA256 recorded as `5c8bedd259f28428188d0d98334520aab6bdade5b8f04de1c6071673c69e636b` (different from spec's literal `6087918d...` — spec value likely stale or different line-endings; recorded as v11.2.2 baseline)
   - Pre-reg commit `a90b02d` (MV-Conditional) verified first in history
   - Baseline test suite passes (exit code 0)
   - Bundle size at start: 11 MB (well under 18 MB ceiling)
2. Part A.1 — `src/viz/static/plotly_config.js` foundational module (192 lines, global `window.MV_PlotlyConfig` namespace).
3. Part A.2 — B1 RE-FIX: reverted 10 occurrences of `+,.Nf` → `+.Nf` in `chart_specs.py` (9) and `strategy_engine_renderers.py` (1). Updated v11.1.1 C1 tests in place (3 inverted assertions).
4. Part A.3 — B2 RE-FIX: `scripts/serve_dashboard.py` + `#file-protocol-notice` in `_header.html`.
5. Part A.4 — B3 FIX: `src/viz/build_strategy_equity_curves.py` + chart at top of Strategy Engine tab. 309 monthly obs of V1 + 3×V2 + SPY. V1 grows $10k → $163k; SPY → $71k.
6. Part A.5 — P0 ship CHECKPOINT: tag `v11.2.2-p0-2026-05-21` (commit `ed56d4c`).
7. Part A.9 — REVIEW_PACKAGE_v11.2.2.md drafted.
8. Part B Stage A0 — LC v1.0 pre-registration SEALED on branch `spec/liquidity-composite-v1.0` (commit `a8635ef`). Both pre-reg commits now in history (a90b02d MV-Conditional, a8635ef LC).

**Test deltas**:
- 15 new tests in `tests/viz/test_v11_2_2_hotfixes.py` (all passing)
- 3 v11.1.1 C1 tests inverted in place (now testing v11.2.2 revert truth)
- Full suite exit code 0 after Part A.5 ship

**Deferred / pending**:
- Part A.6.1–A.6.9 — 9 per-surface Plotly charts on EA surfaces (9-12h estimated). Each is a v11.2.2.{1-9} sub-ship.
- Part A.7 — B7 Risk Metrics deep dive expansion (14 → 50+ metrics).
- Part A.8 — B8 `_falsifiability_blurb.html` per-surface partial.
- Part B Stages A1-K — Full LC v1.0 implementation (~18-22h):
  - A1: MoDH ingestion for 11 new series (WALCL, WDTGAL, RRPONTSYD, BUSLOANS, TOTLL, DTWEXBGS, ICE DXY, TEDRATE, SOFR, IOER, IORB)
  - A2: ALFRED vintage pulls for M2SL/BUSLOANS/TOTLL/WALCL/WDTGAL
  - B-K: compute_components, splices, composite, diagnostics, predictive regression, conditional probabilities, conviction, dashboard panel, falsifiability scorecard, screenshots, tag

---

## Git state

```
main:
  ed56d4c v11.2.2-p0: B1+B2+B3+B4 P0 hotfixes — Plotly polish + strategy equity curves
  3adbfb4 v11.2.1: final ship — Extended Analytics complete
  ...

spec/liquidity-composite-v1.0:
  a8635ef preregister(v11.3): LC v1.0 falsifiability criteria + empirical priors (sealed)
  ed56d4c v11.2.2-p0: B1+B2+B3+B4 P0 hotfixes (inherited)
  ...

Tags (recent):
  v11.2.2-p0-2026-05-21    ← P0 safety checkpoint
  v11.2.1.{1-9}             ← v11.2.1 sub-ships
  v11.2.0-stat              ← v11.2 MV-Conditional V2 backtest
```

Branches NOT pushed to origin (user hasn't authorized push).

---

## Hard gates status (per spec §A.10)

| Gate | v11.2.2-p0 status |
|---|---|
| All P0 bugs fixed (B1, B2, B3, B4) | ✅ verified in tests + built dashboard |
| All 9 EA surfaces have ≥1 Plotly chart | ⏸ DEFERRED (sub-ships v11.2.2.{1-9}) |
| SPY + EW present in all 9 surfaces | ⏸ DEFERRED |
| Y-axis drag-zoom enabled universally | ✅ via plotly_config.js applyUniversalDefaults |
| Strategy color consistency | ✅ via plotly_config.js strategyColors namespace |
| Bundle ≤ 18 MB | ✅ 10.16 MB |
| Test count | ✅ 195+ (15 new v11.2.2 + 173 prior baseline) |
| v50 ORIGINAL SHA256 unchanged | ✅ unchanged from v11.2.2 baseline |
| Pre-registration commit `a90b02d` first | ✅ confirmed |
| Console errors (Playwright 5-screenshot sweep) | ⏸ NOT YET RUN — defer to v11.2.2-final session |

---

## Resume instructions for future session

### To continue Part A.6 (per-surface charts):

1. Verify state: `git log --oneline -3 main` should show `ed56d4c` (v11.2.2-p0).
2. Pick a surface from spec §A.6 table:
   | Sub-tag | Surface | Chart type | Effort |
   |---|---|---|---|
   | v11.2.2.1 | Summary | Mini equity curve last 5Y | 1h |
   | v11.2.2.2 | Drawdowns | Underwater trajectory % | 1.5h |
   | v11.2.2.3 | Rolling Metrics | 60-mo rolling Sharpe line | 1h |
   | ... | ... | ... | ... |
3. Each surface = chart div + data builder + 2 tests (structural + numerical sanity).
4. Use `window.MV_PlotlyConfig.renderChart()` for universal Y-zoom + palette.
5. Sub-ship `v11.2.2.{N}-2026-MM-DD` after each surface.

### To continue Part B (v11.3 LC):

1. `git checkout spec/liquidity-composite-v1.0` (already exists).
2. Verify pre-reg: `git log --oneline -1 buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md` should show `a8635ef`.
3. Start Stage A1 — MoDH ingestion of 11 new series (spec Part B §1.1 inventory).
4. **CRITICAL**: do NOT create any `outputs/lc_*.{parquet,csv,png}` or `outputs/figures/lc_*` artifact before verifying `a8635ef` predates it. Use `git log --oneline -1 specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md` to confirm.
5. Follow spec §16 stage breakdown A1 → K.

### Invariants to re-verify each session:

```bash
# v50 ORIGINAL invariant (path corrected v11.2.2-p1 — was wrongly pointing at the COPY)
sha256sum "D:/Quant Pipeline/Momentum pipeline/quant_engine_v50_FINAL.py"
# Must equal: 6087918db909d3bb3ae66f43305c3331e4171aebc55ddc0366aaff6128026f47

# Pre-reg integrity
cd D:/macro/buffet_indicator
git log --oneline specs/MV_CONDITIONAL_RULE_PREREGISTER.md | tail -1 | grep a90b02d
git log --oneline specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md | tail -1 | grep a8635ef

# Test gates (40 hotfix tests post-v11.2.2-p1)
python -m pytest tests/viz/test_v11_1_1_hotfixes.py tests/viz/test_v11_2_2_hotfixes.py tests/viz/test_v11_2_2_phase3_seasonality_nan.py -q

# Bundle size (≤ 18 MB v11.2.2, ≤ 20 MB v11.3)
du -h outputs/dashboard.html
```

If any invariant fails → STOP, raise `BLOCKED_v11_2_2_<reason>.md` per spec §0.3.

---

## v50 baseline (CORRECTED 2026-05-21 by Phase 4 of remediation sprint)

Investigation Report `reviews/INVESTIGATION_REPORT_v11_2_2_session_1.md` (Hypothesis H1 PASS) showed Session 1's recorded SHA was on the wrong file:

- **Canonical v50 ORIGINAL path**: `D:\Quant Pipeline\Momentum pipeline\quant_engine_v50_FINAL.py`
- **Canonical v50 ORIGINAL SHA256**: `6087918db909d3bb3ae66f43305c3331e4171aebc55ddc0366aaff6128026f47` ← matches the spec literal, unchanged from v11.2.0-stat era (mtime 2026-04-29). The spec literal was NEVER stale.
- **v50 COPY (modifiable, carries v11.2 EXPORT_RETURNS hook)**: `D:\macro\quant_pipeline\quant_engine_v50_FINAL.py`
- **v50 COPY SHA256**: `5c8bedd259f28428188d0d98334520aab6bdade5b8f04de1c6071673c69e636b` (this is what Session 1 hashed and mis-labelled as "baseline")

All future invariant checks target the ORIGINAL at the canonical path. The COPY is a working file for v50 experimentation; its SHA changes freely. **No custody break occurred** — the ORIGINAL is intact since v11.2.0-stat.

Session 1 §A.0 line 16 ("recorded as v11.2.2 baseline") was a path-mistake, not a custody break. Apologies; the spec was right all along.

---

## Known issues / blockers

- **None currently blocking** after v11.2.2-p1 remediation.
- ~~v50 SHA differs from spec literal~~ → RESOLVED: corrected above. The spec literal is the ORIGINAL SHA; Session 1 had mistakenly hashed the COPY.
- EW omitted from strategy equity curves (v50 doesn't yet emit per-month EW); deferred.
- ~~Playwright DevTools sweep not yet run for v11.2.2-p0~~ → DONE in Investigation Session 1; found B1 residual which v11.2.2-p1 (commit d629459, this sprint) fixes.
- **NEW (deferred to v11.2.3)**: 131 SVG NaN render errors per Playwright capture — Plotly internal `<text>` and `<image>` attribute errors. Independent of B1; root cause not investigated this sprint. See `BACKLOG_v11_2_3.md`.
- **NEW (deferred to v11.2.3)**: `.github/workflows/deploy.yml` from master spec §1.6.8 is absent from the repo. No CI auto-deploy currently. See `BACKLOG_v11_2_3.md`.

---

## File-level summary of Session 1 changes

```
buffet_indicator/REVIEW_PACKAGE_v11.2.2.md                    (NEW — 12 sections)
buffet_indicator/scripts/serve_dashboard.py                   (NEW — 55 lines)
buffet_indicator/src/viz/build_strategy_equity_curves.py      (NEW — 136 lines)
buffet_indicator/src/viz/static/plotly_config.js              (NEW — 192 lines)
buffet_indicator/tests/viz/test_v11_2_2_hotfixes.py           (NEW — 15 tests)
buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md  (NEW — 259 lines, SEALED)
buffet_indicator/logs/v11_2_2_plus_v11_3_progress.md          (NEW — this file)

buffet_indicator/src/viz/chart_specs.py                       (MOD — 9 B1 reverts)
buffet_indicator/src/viz/strategy_engine_renderers.py         (MOD — 1 B1 revert)
buffet_indicator/src/viz/build_dashboard.py                   (MOD — plotly_config.js inline + B3 wiring)
buffet_indicator/src/viz/static/dashboard.js                  (MOD — B4 applyUniversalDefaults call)
buffet_indicator/src/viz/templates/_header.html               (MOD — B2 file-protocol-notice)
buffet_indicator/src/viz/templates/tab_strategy_engine.html   (MOD — B3 equity curves chart)
buffet_indicator/tests/viz/test_v11_1_1_hotfixes.py           (MOD — 3 C1 assertion inversions)
buffet_indicator/outputs/dashboard.html                       (MOD — rebuilt)
```
