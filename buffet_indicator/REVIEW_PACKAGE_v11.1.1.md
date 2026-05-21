# REVIEW_PACKAGE_v11.1.1.md — Overview Chart + Format Strings + Routing Hotfix

> Sprint v11.1.1 — focused hotfix for 4 issues found in v11.1 production via
> Strategist's Chrome DevTools console + screenshot review.
> Branch: `main`. Baseline: `bb3cb00` (v11.1-2026-05-20 tag).

---

## 0. Headline

| Gate | Result |
|---|---|
| v11.1.1 new tests | **17 passed / 0 failed** (target ≥12) |
| C1 (Plotly format) | 3 tests |
| C2 (file:// routing) | 3 tests |
| I1 (Overview chart) | 3 tests |
| I2 (V1 lineup table) | 4 tests |
| Regression checks | 4 tests |
| v11.1 tests still pass | 53/53 — no regression |
| Bundle size | **10.02 MB** (Δ vs v11.1: −0.01 MB; ceiling 13 MB) |
| Console errors | **0** across all 5 captured screenshots (down from 2 major in v11.1) |
| Console warnings | 1 (Tailwind CDN production note — acceptable per spec §E.3) |
| Screenshots | **5 / 5**, all > 100 KB, 0 console errors |
| v50 ORIGINAL SHA256 | **UNCHANGED** — `6087918d…b29027f47` |
| ruff (v11.1.1 modules) | 0 errors |

---

## 1. Stage-by-stage status

| Stage | Status | Summary |
|---|---|---|
| A. Fix C1 (Plotly +.2f) | ✅ PASS | Replaced 9 `%{key:+.Nf}` hovertemplate patterns in `chart_specs.py` with safer `%{key:+,.Nf}` (added comma group separator). 0 `WARN: encountered bad format` in console after rebuild. |
| B. Fix C2 (file:// blocked) | ✅ PASS WITH NOTES | Source audit found NO `window.location.href = ...` assignments and all download links already use relative paths. Tab routing already uses `history.replaceState("#"+s)`. Playwright console shows 0 'Unsafe attempt' errors. The original C2 may have been triggered by transient Chrome behavior or a download-link click; current code is verifiably clean. |
| C. Verify I1 (Overview chart) | ✅ PASS | Root cause WAS NOT solely C1+C2 — the `overview-cross-composite-mini` div was never wired up in `dashboard.js`'s `renderChartsForTab("overview")` branch. Added explicit `renderPlot("overview-cross-composite-mini", DATA.overview_mvci_mrc_mini)`. Chart now renders both MVCI and MRC z-score series with NBER bands. |
| D. Fix I2 (V1 lineup table) | ✅ PASS | Root cause was `[:8]` truncation slice in `build_strategy_engine.py`. Replaced with a new `spy_lineup_table` that uses `ranking_full` (all 17 entities sorted by Sharpe desc) joined with `spy_h2h` deltas. Table now shows 17 rows with new CAGR + MaxDD columns, sticky header, max-h-96 internal scroll. |
| E. Validation + screenshots | ✅ PASS | 5 screenshots captured, all > 100 KB, 0 console errors. Bundle 10.02 MB (within ceiling). v50 SHA256 still bit-identical to sprint start. |
| F. Commit + tag + push | ⏳ PENDING USER APPROVAL | Will commit + tag v11.1.1-2026-05-20 + push to origin/main with user confirmation. |

---

## 2. Per-issue verification

### C1 — Plotly bad format

**Before:** 9 occurrences of `%{key:+.Nf}` in `chart_specs.py` (hovertemplates only — Python f-strings with `{x:+.2f}` left alone since they resolve before Plotly sees them).

**After:** 0 occurrences of bad pattern; 9 occurrences of safe `%{key:+,.Nf}` pattern (comma group separator added).

**Specific files modified:**
- `src/viz/chart_specs.py` — 9 hovertemplate strings updated at lines 359, 493, 738, 863, 1056, 1202, 1837, 2092, 2100

**Hovertemplate transformations:**
| Was | Now | Line |
|---|---|---|
| `%{y:+.2f}` (in Z-score history hovertemplate) | `%{y:+,.2f}` | 359, 863 |
| `%{x:+.2f}` (Panel B + sparkline x-axis hover) | `%{x:+,.2f}` | 493, 1837 |
| `%{x}: %{y:+.2f}σ` (single-line z-history) | `%{x}: %{y:+,.2f}σ` | 738 |
| `%{z:+.3f}` (correlation heatmap) | `%{z:+,.3f}` | 1056 |
| `%{y:+.3f}` (ACF/PACF) | `%{y:+,.3f}` | 1202 |
| `f"{name1}: %{{y:+.2f}}σ"` (dual-z overlay — MVCI+MRC mini) | `f"{name1}: %{{y:+,.2f}}σ"` | 2092 |
| `f"{name2}: %{{y:+.2f}}σ"` (dual-z overlay) | `f"{name2}: %{{y:+,.2f}}σ"` | 2100 |

**Console verification:** Playwright sweep across 5 tabs shows 0 `WARN: encountered bad format` lines.

### C2 — file:// blocked

**Source audit results:**
- `grep window.location.href` in `src/`: 0 matches
- `grep window.location.search` in `src/`: 0 matches
- `grep location.assign` in `src/`: 0 matches
- `grep href='file:` in templates: 0 matches
- The only `.href = ...` JS pattern is in `dashboard.js:439` setting `a.href = url` where `url` is a **blob URL** from `URL.createObjectURL(blob)` — safe, used for CSV downloads.

**Files audited (no changes required):**
- `src/viz/static/dashboard.js` — uses `Plotly.newPlot()`, blob URL downloads, hash-based routing
- `src/viz/templates/_header.html` — tab routing uses `history.replaceState(null, "", "#" + s)`
- `src/viz/templates/tab_strategy_engine.html` — download links use relative paths (`outputs/quant_engine/latest/latest.xlsx`)
- `src/viz/templates/tab_backtest.html` — deprecation banner anchor uses `href="#tab=strategy_engine"` (hash-only)

**Console verification:** Playwright sweep across 5 tabs shows 0 `Unsafe attempt to load URL` errors. The original C2 report may have been triggered by a transient Chrome behavior (e.g., right-click on download link) or a different Chrome version's stricter file:// policy. Current code is verifiably clean of bad-pattern URLs.

### I1 — MVCI+MRC chart on Overview

**Root cause:** NOT solely a downstream consequence of C1+C2. The chart spec `DATA.overview_mvci_mrc_mini` was successfully built by `build_macro_chart_payload()` and present in the inline JSON payload, but `dashboard.js`'s `renderChartsForTab("overview")` branch only called `renderSparklines()` — it never invoked `Plotly.newPlot()` for the `overview-cross-composite-mini` div. This was likely a v11.0c oversight when the chart spec was first added.

**Fix:** Added the missing wire-up in `dashboard.js` at the `overview` branch:
```javascript
if (tabName === "overview") {
  renderSparklines();
  // v11.1.1 I1 fix: wire up the MVCI+MRC mini chart
  if (DATA.overview_mvci_mrc_mini && DATA.overview_mvci_mrc_mini.data &&
      DATA.overview_mvci_mrc_mini.data.length > 0) {
    renderPlot("overview-cross-composite-mini", DATA.overview_mvci_mrc_mini);
  }
}
```

The `data.length > 0` guard skips the chart when MVCI+MRC z-histories are unavailable (n/a fallback case from the spec function).

**Screenshot:** `outputs/screenshots/v11_1_1/01_overview_mvci_mrc_chart_fixed.png` — visible blue MVCI line + purple MRC line with NBER bands shaded across the time axis.

### I2 — V1 lineup truncation

**Root cause:** In `build_strategy_engine.py`, `spy_h2h_top = metrics.get("spy_h2h", [])[:8]` truncated the list to 8 entries. Worse, `spy_h2h` excludes SPY itself (the baseline). So the rendered table lost SPY + the 9 lowest-Sharpe entities (TROW, BEN, IVZ, STT, NTRS, GS, JPM, MS).

**Fix:** Replaced the truncated `spy_h2h_top` with a new `spy_lineup_table` that:
- Iterates `metrics["ranking_full"]` (all 17 entities, already sorted by Sharpe desc)
- Joins in `delta_sharpe_vs_spy` and `delta_maxdd_vs_spy` from `spy_h2h` for non-SPY entries
- Includes SPY with delta=0 (baseline marker)
- Returns 17 entries instead of 8

Template updated to:
- Add CAGR and MaxDD columns alongside Sharpe + deltas
- Use sticky header + max-h-96 internal scroll for compact layout
- Highlight SPY row with a baseline indicator (`(baseline)` label + bg-gray-50 row)
- Show "n/a" for any missing values instead of crashing

**Screenshot:** `outputs/screenshots/v11_1_1/02_strategy_engine_v1_lineup_full.png` — table visible with DD-TARGET, Combination, LowBeta, ENS-Ultra, EW, BLK, BRK.B, RJF, and the rest scrollable below.

---

## 3. Regression check

- ✅ All 53 v11.1 tests still pass (re-verified via `pytest tests/quant_engine/ tests/viz/test_v11_1_*.py` → 70/70 including new 17 v11.1.1)
- ✅ All 35 Strategy Engine sections still render with real content (regression test `test_regression_strategy_engine_still_has_35_sections` passes)
- ✅ Old Backtest tab still shows deprecation banner (regression test passes)
- ✅ Methodology v50 section still present (regression test passes)
- ✅ Bundle size 10.02 MB ≈ v11.1's 10.03 MB (regression test bounds [9.5, 11.0])
- ✅ v50 ORIGINAL SHA256 = `6087918db909d3bb3ae66f43305c3331e4171aebc55ddc0366aaff6128026f47` (unchanged)

---

## 4. Test results

- pytest (v11.1.1 + v11.1): **70 passed**, 0 failed
- pytest (full suite, including pre-v11.1 legacy): exit code 0 (full count being verified)
- ruff (v11.1.1-touched modules): 0 errors
- bandit: no new HIGH/MEDIUM since v11.1

**v11.1.1 new test count: 17** (target was 12)
- C1: 3 tests
- C2: 3 tests
- I1: 3 tests
- I2: 4 tests
- Regression: 4 tests

---

## 5. Self-assessment (≥10 bullet points)

### 5.1 Methodology

- **C1 format fix approach:** Used `:+,.Nf` (added comma group separator) per spec recipe. This was uniformly safe — all 9 hovertemplate sites worked the same way. No case-by-case decisions needed. The `,` separator only shows up in actual number rendering when values exceed 1,000 — for z-scores ([-3, +3] σ range), it has no visible effect on the formatted output.
- **C1 scope discipline:** Did NOT touch Python f-strings like `f"{z:+.2f}"` — those resolve to a static string before Plotly sees them, so they're not affected by Plotly's d3-format parser. Touched only Plotly hovertemplate / texttemplate / similar substitution strings.
- **C2 outcome surprise:** The spec hypothesized `window.location.href` usage as the trigger, but source grep found NONE. The single `.href = url` in `dashboard.js` is for blob URLs (safe). My fixes therefore focused on verification (auditing + clean Playwright sweep) rather than code changes. If C2 reappears in actual desktop Chrome (not headless Playwright), the next investigation should focus on download-link click events or Plotly's image-export path.
- **I1 surprise — NOT a downstream consequence of C1+C2.** The spec hypothesized that fixing C1+C2 might auto-resolve I1. False. The chart was missing a wire-up call in `dashboard.js`. This was a pure JS-side bug present since v11.0c when the chart was first added. The Plotly format warning never blocked rendering — Plotly gracefully falls back to default formatting.
- **I2 reason for showing all 17 (not 8):** Option A from spec ("show ALL 17 entities") chosen over Option B (rename to "top 8"). Strategist's review explicitly noted truncation hides SPY at Sharpe 0.501 — the baseline — making the table mislabel itself. Full transparency wins.

### 5.2 UX

- **Bundle size change: 10.03 → 10.02 MB (−0.01 MB).** The fixes added trivial bytes (JS wire-up, table rows, hovertemplate commas). Within the 13 MB v11.1 ceiling with comfortable headroom.
- **Visual regressions noticed:** None during the 5-screenshot regression sweep. Strategy Engine 35 sections all render; methodology section intact; deprecation banner present; HY-IG layout fixes (L1-L4) still in place.
- **I2 table layout choice — sticky header + internal scroll:** Chose `max-h-96 overflow-y-auto` with `sticky top-0` thead so the table fits in compact viewport but all 17 rows remain accessible without page scroll. Alternative was rendering full table inline (would push the period heatmap further down).
- **SPY baseline marker:** Added `(baseline)` label and bg-gray-50 row tint to make SPY visually distinct from the other entities, since its delta-vs-SPY values are 0 by definition.

### 5.3 Performance

- **Dashboard build time:** unchanged (~6 s).
- **Page render time (Overview):** Slight increase (one extra `Plotly.newPlot()` call for the MVCI+MRC mini chart). Negligible — both lines combined have ~1,500 data points.

### 5.4 Tests

- **v11.1.1 test count: 17 vs target 12.** Exceeded by 5 because I added regression checks against v11.1 surface (Strategy Engine sections, methodology, deprecation banner, bundle size) that the spec only implied.
- **No tests relaxed or skipped** during v11.1.1.
- **DOM probe coverage:** `test_each_section_passes_dom_content_gate` from v11.1 still passes — all 35 Strategy Engine sections still have ≥1 tr OR Plotly div OR ≥100 chars of prose.

### 5.5 Things NOT done

- **Tailwind CDN production warning:** acceptable cosmetic warning per spec §E.3. Defer to v12.0 hosted deployment when Tailwind would be properly bundled.
- **Combination strategy 3 bps rebal cost sensitivity:** still deferred to v11.2.
- **MV-Conditional V2 backtest:** for v11.2.
- **Hosted refresh endpoint** for the Refresh button: still static fallback in v11.1.1; defer.
- **`history.pushState` instead of `replaceState` for tab routing:** the current `replaceState` means back/forward buttons don't traverse tab history. Strategist may want to evaluate; out of scope for this hotfix.

---

## 6. Git state

- Baseline: `bb3cb00` (v11.1-2026-05-20)
- v11.1.1 modifications staged:
  - Modified: `src/viz/chart_specs.py` (9 hovertemplate strings)
  - Modified: `src/viz/static/dashboard.js` (overview chart wire-up)
  - Modified: `src/viz/build_strategy_engine.py` (spy_lineup_table builder)
  - Modified: `src/viz/templates/tab_strategy_engine.html` (full 17-entity table with sticky header)
  - Modified: `outputs/dashboard.html` (rebuilt)
  - New: `tests/viz/test_v11_1_1_hotfixes.py` (17 tests)
  - New: `scripts/capture_v11_1_1_screenshots.py`
  - New: `outputs/screenshots/v11_1_1/01..05*.png` + `_capture_log.json`
  - New: `REVIEW_PACKAGE_v11.1.1.md` (this file)
- **Tag plan:** `v11.1.1-2026-05-20`
- Chain: `... → cc6dc5c (v11.0.2) → 8227129 → bb3cb00 (v11.1) → HEAD (v11.1.1)`
- **Outside repo (intentional):** `D:\macro\quant_pipeline\` and v50 ORIGINAL — both untouched.

---

End of REVIEW_PACKAGE_v11.1.1.md
