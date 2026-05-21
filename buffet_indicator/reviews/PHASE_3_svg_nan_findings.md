# PHASE_3_svg_nan_findings — SVG NaN errors are independent

> Phase 3 of v11.2.2 remediation, 2026-05-21.
> Triggered by Investigation Report bonus finding: 131 SVG NaN render errors per Playwright capture.

## TL;DR

The 131 SVG NaN errors per capture are **independent** of the B1 `+.Nf` format-string fix. They persist unchanged after the Phase 3 fix landed. Root cause not investigated in this remediation sprint per prompt scope; deferred to v11.2.3 backlog.

## Evidence

| Capture | text-y-NaN errors | image-height-NaN errors | Total |
|---------|-------------------|--------------------------|-------|
| file:// pre-fix (Investigation Session 1) | 129 | 2 | 131 |
| http:// pre-fix (Investigation Session 1) | 129 | 2 | 131 |
| file:// post-fix (Phase 3 capture) | 129 | 2 | 131 |
| http:// post-fix (Phase 3 capture) | 129 | 2 | 131 |

Counts identical — B1 fix did not affect SVG render errors.

## Sample error text (5)

All 131 errors share two unique signatures, originating from `https://cdn.plot.ly/plotly-2.35.2.min.js` line 7:

```
Error: <text> attribute y: Expected length, "NaN".
Error: <text> attribute y: Expected length, "NaN".
Error: <text> attribute y: Expected length, "NaN".
Error: <text> attribute y: Expected length, "NaN".
Error: <image> attribute height: Expected length, "NaN".
```

## Hypothesis (NOT tested in this sprint)

Plotly's internal SVG renderer is computing y-coordinates or height values that evaluate to NaN — likely:
- a layout calculation where two data points coincide (`y2 - y1 == 0` then `/0` → NaN), or
- a colorbar height being computed from an empty/uniform z-array, or
- an annotation position being computed from a missing reference value.

The most likely candidate is the **MVCI/MRC mini overlay** on the Overview tab or one of the diagnostics charts where dual-trace y-coords are computed at render time from runtime-resolved layout. But this is **speculation** and was not tested.

## Action

- **Phase 3 commit**: includes this findings doc as evidence that SVG NaN was investigated and confirmed independent.
- **v11.2.3 backlog**: add `[P1] Root-cause 131 SVG NaN render errors per Playwright capture` (created in Phase 4).
- **No fix applied here**: out of scope; prompt §3.4 directs to defer.

## End Phase 3 SVG NaN investigation.
