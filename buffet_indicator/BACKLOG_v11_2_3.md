# BACKLOG for v11.2.3 minor sprint

> Filed 2026-05-21 by v11.2.2-p1 remediation sprint (Phase 4.3).
> Items deferred from v11.2.2 remediation. Strategist will sequence and authorize.

## P0 — Critical (auto-deploy broken without it)

- **`.github/workflows/deploy.yml` missing per master spec §1.6.8.**
  - Current state: neither `D:\macro\.github\workflows\` nor `D:\macro\buffet_indicator\.github\workflows\` exists. There is no `.github/` directory anywhere in the repo.
  - Effect: pushes to `origin/main` do NOT trigger any GitHub Actions; `mvfoundation01/macro` Pages / release / artifact builds remain manual.
  - Path forward: create `.github/workflows/deploy.yml` matching master spec §1.6.8 schema. Likely needs:
    - GitHub Pages publish from `outputs/dashboard.html` (or its served equivalent), or
    - Release-asset upload on tag push, or
    - Both.
  - Tokens / secrets needed: depends on target (Pages doesn't need any extra; GHCR/Release does).
  - Estimated effort: 1–2 h once the deployment target is decided.

## P1 — Medium (visible to any DevTools user, cosmetic risk)

- **131 SVG NaN render errors per Playwright capture.**
  - Confirmed independent of B1 `+.Nf` fix (count unchanged at 131 before and after the v11.2.2-p1 fix; see `reviews/PHASE_3_svg_nan_findings.md`).
  - Pattern: 129x `<text> attribute y: Expected length, "NaN"` and 2x `<image> attribute height: Expected length, "NaN"`. All originate inside `plotly-2.35.2.min.js` line 7.
  - Hypothesis (untested): Plotly's internal SVG renderer is computing a y-coordinate or height from a numeric expression that evaluates to NaN — possibly from a zero-range axis on the MVCI/MRC overlay, a colorbar height computed from a uniform z-array, or an annotation position referencing a missing value.
  - Reproduction: `python reviews/diagnostic_artifacts/capture_console_file_v3.py` after `python -m src.cli dashboard`. Counts ≥ 1 ⇒ regression.
  - Estimated effort: 1–3 h to isolate which chart contributes which slice of the 131 errors and patch the offending trace builder.

## P1 — Medium (UX completeness)

- **Per-surface Plotly charts for Surfaces 2–8.**
  - Master spec §A.6.{2..8}. Only Surface 1 (Summary mini equity curve, v11.2.2.1) and Surface 9 (Seasonality heatmap, v11.2.2.9) shipped in mega-sprint Session 1.
  - Surfaces still missing: Drawdowns (2), Rolling Metrics (3), Risk-vs-Return (4), Returns (5), Lump-Sum (6), Risk-vs-Return Scatter (7), Withdrawal (8). Each ≈ 1–1.5 h.
  - Estimated effort: 7–10 h total for full §A.6 sweep.

## P2 — Low (defer freely)

- **B7 Risk Metrics expansion (14 → 50+ metrics).** Master spec §A.7. Stretch goal.
- **B8 per-surface `_falsifiability_blurb.html` partial.** Master spec §A.8. Never shipped, demoted from P0.
- **EW (equal-weight) strategy in equity curves.** Currently omitted because v50 doesn't yet emit per-month EW. Requires v50 COPY (`D:\macro\quant_pipeline\quant_engine_v50_FINAL.py`) modification or a separate EW computation path.

---

## Items NOT in this backlog (intentionally)

- v50 ORIGINAL custody: confirmed clean (`6087918d…26f47` at `D:\Quant Pipeline\Momentum pipeline\`). No action needed; covered by the Phase 4 PROGRESS-log correction (commit `e2058f5`).
- B1 / B2 fixes: completed in v11.2.2-p1 (commit `d629459`). 0 bad-format warnings, 0 unsafe-URL errors verified under both file:// and http://.

## Next-sprint sequencing recommendation (for Strategist arbitration)

1. **P0 first**: ship `deploy.yml` so subsequent work auto-deploys.
2. **Then choose**: SVG NaN root-cause OR Surfaces 2–8 build-out, depending on whether UX completeness or console-cleanliness is more pressing.
3. **Stretch**: B7 / B8 if cycles remain.

End of backlog.
