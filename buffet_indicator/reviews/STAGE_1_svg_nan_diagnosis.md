# Stage 1 — SVG NaN diagnosis (v11.2.3-svgnan)

> Empirical investigation per PROMPT_v11_2_3 §1.1. Hypothesis-driven binary search.
> Final diagnosis 2026-05-21 by Claude Code (Opus 4.7 1M context).

## Baseline (per-tab, before fix)

Captured via `reviews/diagnostic_artifacts/capture_svg_nan_per_tab.py` — fresh Playwright browser context per tab to attribute SVG NaN render errors unambiguously.

| Tab | Total errors | `<text> y` | `<image> height` |
|---|---:|---:|---:|
| no-click baseline (overview default) | 49 | 48 | 1 |
| overview (after hover) | 49 | 48 | 1 |
| cape | 49 | 48 | 1 |
| buffett | 49 | 48 | 1 |
| mvci | 49 | 48 | 1 |
| strategy_engine | 49 | 48 | 1 |
| **diagnostics** | **131** | **129** | **2** |
| data | 49 | 48 | 1 |
| methodology | 49 | 48 | 1 |
| backtest | 49 | 48 | 1 |

**Pattern**: 49 errors on bare page load (overview is the default tab). Clicking diagnostics adds 82 more (49 → 131). All other tabs add 0. Hover adds 0 errors (verified by phase-stamped capture in `capture_diag_only.py`).

## Root cause #1 — 49 baseline errors

**Two independent unconditional renders on `DOMContentLoaded`** rendering Plotly into a hidden (`display: none`) strategy_engine tab:

1. `src/viz/templates/tab_strategy_engine.html:300-319` — `details[open] .se-plotly-chart` renders + `#se-period-heatmap-bonus` render.
2. `src/viz/templates/_ea_surface_9_seasonality.html:66-69` — seasonality heatmap IIFE with `setTimeout(tryRender, 100)`.

Both fire regardless of which tab is active. `Plotly.newPlot` into a `display:none` div computes layout from `clientWidth/Height = 0`, producing NaN coordinates for every `<text>` and `<image>` element.

The seasonality heatmap accounts for the `<image height="NaN">` (colorbar pixmap) + ~48 cell-label `<text y="NaN">` errors. Multiple `.se-plotly-chart` divs in the open `<details>` block contribute additional text errors.

## Root cause #2 — 82 errors when diagnostics tab activates

Per-chart isolation in `capture_per_diag_chart.py` (hide each chart, re-measure):

| Hidden | Total | `text_y` | `image_h` |
|---|---:|---:|---:|
| `<none>` | 82 | 81 | 1 |
| `diagnostics-correlation-heatmap` | **0** | **0** | **0** |
| `diagnostics-oos-r2-chart` | 82 | 81 | 1 |
| `diagnostics-acf-pacf-chart` | 82 | 81 | 1 |
| `diagnostics-calibration-chart` | 82 | 81 | 1 |

**Single culprit: the 9×9 correlation heatmap.** 81 cell-label text errors + 1 colorbar image error.

Minimal HTML reproductions (`repro_heatmap.html`, `repro_v2.html`) emitted **0 errors** with the same chart spec — so the spec itself is fine. The difference: the real dashboard passes layout through `MV_PlotlyConfig.applyUniversalDefaults()` in `dashboard.js:renderPlot`, which merges:

```js
yaxis: {
  fixedrange: false,
  autorange: true,
  type: "linear",        // ← KILLER
  showspikes: true,
  ...
}
```

…onto the heatmap's `yaxis: {autorange: "reversed", tickfont: ...}`. Heatmaps have **categorical** axes (variant names as labels). Forcing `type: "linear"` on a categorical axis breaks Plotly's coordinate computation — every cell label SVG y-coordinate becomes NaN, and the colorbar's `<image>` height becomes NaN. Hence exactly 81 + 1 = 82 errors per render.

## Fix (Category B + Category D mixed — bug in shared layout helper)

Three minimal patches:

### A. `src/viz/static/dashboard.js` — gate `applyUniversalDefaults` on non-heatmap

```js
const hasHeatmap = Array.isArray(data) && data.some(t =>
  t && (t.type === "heatmap" || t.type === "heatmapgl")
);
if (window.MV_PlotlyConfig?.applyUniversalDefaults && !hasHeatmap) {
  layout = window.MV_PlotlyConfig.applyUniversalDefaults(layout);
}
```

Eliminates **82 diagnostics-tab errors**. This is the load-bearing fix.

### B. `src/viz/static/dashboard.js` — `window.mvRenderWhenReady` helper

Public helper that defers `Plotly.newPlot` calls until the host div has non-zero dimensions AND Plotly is loaded. Uses `requestAnimationFrame` polling (up to ~500 ms) then falls back to `IntersectionObserver` for tabs that may activate much later. Used by `renderPlot` for all dashboard.js renders.

### C. Template-side use of `mvRenderWhenReady`

- `src/viz/templates/tab_strategy_engine.html` — gate the `details[open]` + `se-period-heatmap-bonus` renders.
- `src/viz/templates/_ea_surface_9_seasonality.html` — gate the seasonality heatmap IIFE.

Together with B, this eliminates the **49 baseline errors**.

## Post-fix capture

```
Summary:
  no-click baseline: 0
  overview          : total= 0  text_y= 0  image_height= 0
  cape              : total= 0  text_y= 0  image_height= 0
  buffett           : total= 0  text_y= 0  image_height= 0
  mvci              : total= 0  text_y= 0  image_height= 0
  strategy_engine   : total= 0  text_y= 0  image_height= 0
  diagnostics       : total= 0  text_y= 0  image_height= 0
  data              : total= 0  text_y= 0  image_height= 0
  methodology       : total= 0  text_y= 0  image_height= 0
  backtest          : total= 0  text_y= 0  image_height= 0
```

**131 → 0 errors (100% elimination, target was ≥90%).**

20/20 existing `tests/viz/test_v11_2_2_hotfixes.py` still pass.

## Strategist lessons confirmed (from PROMPT §0.5)

- **Lesson 1** (don't bet wrong on root cause): The Strategist's initial hypothesis space included "v11.2.2 regression introduced by `6fcb2f1` heatmap or `d91c7a9` mini equity curve". Empirical per-tab + per-chart isolation showed the actual cause was a *shared* layout helper (`applyUniversalDefaults`) introduced in v11.2.2 B4 fix — affecting every heatmap, not just the recent ones. Empirical isolation BEFORE patching was essential.
- **Lesson 6** (Reviewer audit perspective): Playwright per-tab captures are the source of truth, not source grep. The `+.Nf` and `applyUniversalDefaults` bugs both required actual browser captures to surface.

## Artifacts

- `reviews/diagnostic_artifacts/svg_nan_per_tab.json` — per-tab error breakdown (post-fix, all zero)
- `reviews/diagnostic_artifacts/diag_phase_breakdown.json` — phase-stamped capture (render vs hover)
- `reviews/diagnostic_artifacts/capture_svg_nan_per_tab.py` — per-tab capture (kept for future audits)
- `reviews/diagnostic_artifacts/capture_per_diag_chart.py` — per-chart isolation harness
- `reviews/diagnostic_artifacts/repro_heatmap.html`, `repro_v2.html` — minimal reproductions that proved the spec is innocent
