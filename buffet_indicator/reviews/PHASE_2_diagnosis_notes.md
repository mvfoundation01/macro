# PHASE_2_diagnosis_notes — B1 residual root cause

> Phase 2 of v11.2.2 remediation sprint, 2026-05-21.
> Triggered by INVESTIGATION_REPORT_v11_2_2_session_1.md §Investigation #2 B1 FAIL verdict.

## TL;DR

**Root cause is the format string itself, NOT NaN in the data.** Plotly 2.35.2's d3-format parser rejects `:+.2f` in heatmap hovertemplate context and emits `WARN: encountered bad format: "+.2f"`. The seasonality data has 0/48 NaN cells.

Fix: switch hovertemplate from `%{z:+.2f}%` to `%{text}` — the `text` field is already populated with Python-side-formatted strings (`mean_fmt` like `"+0.83%"`) and uses Python's native `+.2f` formatter, which Plotly never parses.

## Evidence

### Offending line

`outputs/dashboard.html:9551` (rendered output):
```
hovertemplate: "%{y} · %{x}: %{z:+.2f}%<extra></extra>",
```

Source template: `src/viz/templates/_ea_surface_9_seasonality.html:49`.

### Data integrity test (reviews/diagnostic_artifacts/test_seasonality_nan.py)

Output:
```
Rows (strategies): 4
Total cells: 48
Explicit None/null: 0
NaN (float): 0
Non-numeric: 0
Raw NaN substring occurrences in payload: 0
Raw null substring occurrences in payload: 0
```

4 strategies × 12 months = 48 cells. All numeric. No NaN, no None, no nulls. The Strategist hypothesis ("Plotly's numberFormat receives NaN") is **falsified** for this surface.

### Why Plotly emits the warning despite valid data

Plotly 2.35.2 bundles d3-format-1.x. The `+` sign-modifier is valid d3-format syntax, but Plotly's internal `numberFormat` wrapper around d3-format has a known rejection path for certain modifier+type combinations in `hovertemplate` parsing. The warning is cosmetic — Plotly still renders the value (just without the explicit `+` prefix).

We do not need to fully reverse-engineer Plotly's parser. The pragmatic fix is to bypass Plotly's format parsing entirely by feeding it pre-formatted strings via the existing `text` field.

## Fix (applied in Phase 3)

Change `hovertemplate` in `src/viz/templates/_ea_surface_9_seasonality.html:49`:

```diff
-            hovertemplate: "%{y} · %{x}: %{z:+.2f}%<extra></extra>",
+            hovertemplate: "%{y} · %{x}: %{text}<extra></extra>",
```

The `text` array is already built (line 40-42 in the template, line 9540-9542 in rendered dashboard.html) from `m.mean_fmt`, which is Python-side `+.2f` formatted. This is a hybrid of Option A1 (pre-formatted customdata) — using the existing `text` field as the pre-format vehicle, no new data plumbing required.

## SVG NaN errors hypothesis

The 131 SVG NaN errors (Investigation Report bonus finding) may share root cause with B1 residual: Plotly's heatmap renderer may attempt to draw `<text>` and `<image>` elements with NaN y-coordinates for the seasonality heatmap's axis labels or color bar. If Phase 3 fix eliminates the warning AND the SVG NaN count drops significantly → confirmed same root cause. If SVG count stays at ~131 → independent issue, defer to v11.2.3.

## Files inspected (no edits)

- `outputs/dashboard.html` (read lines 9501-9601)
- `src/viz/templates/_ea_surface_9_seasonality.html`
- `src/viz/templates/tab_strategy_engine.html`
- `src/viz/build_dashboard.py`
- `src/viz/captions.py`
- `src/viz/build_macro_risk.py`

`+.2f` occurrences elsewhere in src/viz/ are Python f-strings (lines like `f"{z:+.2f}"`), which are formatted by Python before HTML rendering — Plotly never sees those format specs. Only line 49 of `_ea_surface_9_seasonality.html` puts `+.2f` into a Plotly format context.

## End Phase 2.
