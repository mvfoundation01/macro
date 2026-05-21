# PROGRESS — v11.2.3 + v11.3 combined mega-sprint (Path B4)

> Session log per PROMPT_v11_2_3_plus_v11_3 §0.4 multi-session protocol.
> File location: `buffet_indicator/PROGRESS_v11_2_3_combined.md`
> (`buffet_indicator/logs/` is gitignored — see prior `PROGRESS_v11_2_2_and_v11_3.md` for the same convention).
> Authorization: user 2026-05-22 (per prompt opening).

## Session 1 — 2026-05-21 (Claude Opus 4.7 1M context)

### Done

| Stage | Status | Local commits | Tag | Notes |
|---|---|---|---|---|
| **Stage 0** — deploy.yml + Dockerfile + .dockerignore + README_DEPLOY + 6 tests | ✅ code-complete locally | `def2edb` (initial wrong-location placement), `6e1eeba` (relocate to repo root) | `v11.2.3-deploy-2026-05-21` (on `6e1eeba`) | 6/6 deploy tests pass. Push BLOCKED by Claude Code auto-mode classifier — user must push manually. |
| **Stage 1** — SVG NaN diagnosis + fix + 6 regression tests | ✅ code-complete locally | `1306476` | `v11.2.3-svgnan-2026-05-21` | 131 → 0 errors (100% reduction; target ≥90%). 20/20 v11.2.2 hotfix tests still pass. Push BLOCKED. |

### Invariants verified at session start AND end

| Invariant | Status |
|---|---|
| v50 ORIGINAL at `D:\Quant Pipeline\Momentum pipeline\quant_engine_v50_FINAL.py` SHA256 = `6087918db909d3bb3ae66f43305c3331e4171aebc55ddc0366aaff6128026f47` | ✅ unchanged |
| Pre-reg `a90b02d` (MV-Conditional) on `origin/main` | ✅ untouched |
| Pre-reg `a8635ef` (LC v1.0) on `origin/spec/liquidity-composite-v1.0` | ✅ untouched (sealed since pre-session) |
| v11.2.2 hotfix test suite (20 tests) | ✅ 20/20 pass |
| Bundle size | 10.68 MB (pre) → 10.69 MB (post Stage 0) → 10.71 MB (post Stage 1) — well under Stage 0-2 ceiling 14 MB and Stage 3 ceiling 20 MB |

### Key empirical findings (Stage 1)

- **Per-tab diagnosis**: errors split between page-load render (49) and diagnostics tab activation (82). Hovers add 0.
- **Per-chart isolation**: 100% of the 82 diagnostics errors come from `diagnostics-correlation-heatmap`. Hiding it dropped diagnostics tab to 0 errors.
- **Minimal HTML repro proved chart spec is innocent** (`reviews/diagnostic_artifacts/repro_heatmap.html`, `repro_v2.html` — 0 errors). The cause was `MV_PlotlyConfig.applyUniversalDefaults` forcing `yaxis.type: "linear"` onto heatmap's categorical y-axis — every cell label SVG y becomes NaN, colorbar `<image height>` becomes NaN.
- **Strategist Lesson 1 applied**: hypothesized cause (recent `6fcb2f1` seasonality heatmap or `d91c7a9` mini equity) was wrong; actual cause was a shared layout helper introduced in v11.2.2 B4 fix affecting all heatmaps.

### Files changed this session

```
.github/workflows/deploy.yml            (NEW, repo root)
buffet_indicator/Dockerfile             (NEW)
buffet_indicator/.dockerignore          (NEW)
buffet_indicator/README_DEPLOY.md       (NEW)
buffet_indicator/tests/deploy/test_v11_2_3_deploy_workflow.py  (NEW, 6 tests)
buffet_indicator/src/viz/static/dashboard.js                    (MODIFIED)
buffet_indicator/src/viz/templates/tab_strategy_engine.html     (MODIFIED)
buffet_indicator/src/viz/templates/_ea_surface_9_seasonality.html (MODIFIED)
buffet_indicator/tests/viz/test_v11_2_3_svgnan_regression.py    (NEW, 6 tests)
buffet_indicator/reviews/STAGE_1_svg_nan_diagnosis.md           (NEW)
buffet_indicator/reviews/diagnostic_artifacts/ (NEW captures + repros)
buffet_indicator/outputs/dashboard.html  (REBUILT)
```

### Not done this session

| Stage | Status | Effort remaining |
|---|---|---|
| Stage 2 — Surfaces 2-8 Plotly charts | ⏳ not started | 7-10h, 7 sub-tags |
| Stage 3 — LC v1.0 full implementation | ⏳ not started | 18-22h, sub-stages A1-K |
| Stage 4 — merge LC branch + tag v11.3.0 | ⏳ not started | 1-2h |
| **owner action** — `git push origin main` + `git push origin v11.2.3-deploy-2026-05-21` + `git push origin v11.2.3-svgnan-2026-05-21` + configure HF_TOKEN secret | ⏳ blocked | manual |

### Reconnaissance findings for next session (Stage 2)

- All 7 `_ea_surface_{2..8}_*.html` templates exist; they currently render TABLES only (no Plotly chart). Stage 2 needs to ADD a Plotly chart per surface (per PROMPT §2.5).
- Existing pattern reference: `_ea_surface_1_summary.html` uses Plotly via `MV_PlotlyConfig.renderChart`; `_ea_surface_9_seasonality.html` uses direct `Plotly.newPlot`. Either pattern works.
- Strategy returns data is already wired through the SE renderer (`src/viz/strategy_engine_renderers.py`) — the per-surface builders just need to compute the chart-specific metric (drawdown trajectory, rolling Sharpe, etc.) from the existing strategy returns dict.
- Universal layout defaults already gate on heatmap (per Stage 1 fix) — Surface 8 (SWR heatmap) is the only heatmap in Stage 2 and will inherit that fix.

### Resume protocol for next session

1. `cd D:/macro/buffet_indicator && python -m pytest tests/viz/test_v11_2_3_svgnan_regression.py -v` — confirm 6/6 still pass.
2. Verify §0.2 invariants per the prompt (v50 SHA, pre-reg commits, bundle size).
3. Read this PROGRESS log, then continue from **Stage 2 → Surface 2 (Drawdowns)** per PROMPT §2.5.
4. Before pushing anything: confirm with user that the auto-mode classifier permission has been granted, OR ask user to push the queued commits manually.

### Tag chain on `main` (local, awaiting push)

```
def2edb v11.2.3-deploy: GitHub Actions auto-deploy + Dockerfile per master spec §1.6.8
6e1eeba v11.2.3-deploy: relocate deploy.yml to repo root + working-directory shim   ← tag v11.2.3-deploy-2026-05-21
1306476 v11.2.3-svgnan: fix 131 SVG NaN render errors at root cause                  ← tag v11.2.3-svgnan-2026-05-21
```

`spec/liquidity-composite-v1.0` branch unchanged (pre-reg `a8635ef` still sealed).
