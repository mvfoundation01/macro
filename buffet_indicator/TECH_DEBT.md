# TECH_DEBT.md — Macro Project Technical Debt Registry

> Living document. Updated at each sprint closeout. Strategist arbitrates priority.
>
> Last updated: 2026-05-23 (post-v11.3.0 stabilization)

## 0. Baseline state (this update)

- HEAD (main): `27d3a7b` (`v11.2.3-s2-svgnan-hotfix: fix Surface 9 NaN + harden via HTTP Playwright tests`)
- Latest sprint closeout: `v11.3.0` on `spec/liquidity-composite-v1.0` (commit `d56174c`, 2026-05-25), NOT merged to main
- Tests collected: **1000** (`pytest --collect-only` on tests/)
  - Fast subset run (excludes tests/viz, tests/deploy, --no-cov): **544 collected, ~515 passed, ~29 skipped, 0 failed** (exit 0)
  - Skips are `INTEGRATION_TESTS=1`-guarded loaders in tests/ingest (shiller, yahoo)
  - Full-suite run hangs on slow chart-rendering tests in tests/viz/ after ~51% completion (one prior run reached 99% but never emitted final summary line); see P1 item 4 below
- Coverage: **not captured this session** (the addopts `--cov=src --cov-report=term-missing` requires the full suite to complete; deferred until viz slowness fixed). Most recent successful coverage on record was from v11.2.3-s2 closeout — refer to that commit's PROGRESS entry.
- Ruff: **8 errors** (7 `E402` module-import-not-at-top-of-file in `scripts/`, 1 `F841` unused-variable in `scripts/smoke_test.py`). Per `pyproject.toml`, tests/ already has E402 suppressed; `scripts/` does not.
- MyPy strict on `src/`: **134 errors in 33 files** (72 source files checked). Breakdown by error code:
  - 23 `arg-type`
  - 19 `import-untyped`
  - 14 `union-attr`, 14 `type-arg`, 14 `no-any-return`
  - 13 `attr-defined`
  - 9 `operator`, 8 `index`, 8 `assignment`
  - 4 `str`, 4 `return-value`, 4 `call-overload`
  - 2 `valid-type`
  - 1 `untyped-decorator` (tolerable per prompt §2.1 precedent)
  - 1 `misc`, 1 `bytes`
- Bandit security scan on `src/`: **17 Low, 0 Medium, 0 High** (16130 LoC scanned). Dominant pattern: `try/except/pass` (`B110`).
- Bundle size:
  - `outputs/dashboard.html`: **10.36 MB** (ceiling 20 MB — OK)
  - `outputs/` total: **61.7 MB** (75% is `outputs/screenshots/` at 46.4 MB)
  - `data/master/`: **0.6 MB** (16 files, mostly small parquets)
- v11.3.0 verdict.json parses cleanly: **yes** (verdict=FAIL, n_pass=0/7, sprint=v11.3.0, pre_reg=a8635ef)
- Git LFS: 6 tracked files, `git lfs fsck` reports OK
- Pre-reg invariants intact: `a90b02d` (MV-Conditional, ancestor of main), `a8635ef` (LC v1.0, ancestor of spec branch), v50 ORIGINAL SHA `6087918DB909D3BB3AE66F43305C3331E4171AEBC55DDC0366AAFF6128026F47`

## 1. Active technical debt items

### P0 (must fix before next sprint)

None at this baseline. All invariants intact; no test regressions observed in the fast subset; v11.3.0 artifacts on spec branch verified.

### P1 (should fix during next sprint)

1. **Root-level `.gitignore` is absent.** Repository root is `D:\macro` (parent of `buffet_indicator/`); only `buffet_indicator/.gitignore` exists. As a result, `git status` from the repo root surfaces many untracked directories at the parent level (`.claude/`, `API/`, `prompt/`, `quant_pipeline/`, `raw data/`, `template/`) on every command. Add a minimal root `.gitignore` covering these.

2. **CI deploy.yml is failing 10/10 most-recent runs** (all `workflow_dispatch` on `spec/liquidity-composite-v1.0`; no runs on main since 27d3a7b). Two compounding failures:
   - `pip install -r requirements.lock --require-hashes` fails because `buffet_indicator/requirements.lock` (22 lines) lists `package==version` pinning but no hashes. The `|| pip install -r requirements.lock` fallback in `.github/workflows/deploy.yml:37` is supposed to recover, but the job still exits non-zero — investigate fallback behavior under pip's exit-code semantics.
   - MyPy strict on `src/` produces 134 errors (see baseline §0); the CI mypy step exits non-zero, blocking deploy.
   - **Net effect**: no successful main-branch CI run since the v11.3.0 sprint began. Next sprint should not begin v2.0 implementation work before CI is green.

3. **12 data parquet files untracked in `buffet_indicator/data/master/`** even though `.gitattributes` LFS filter (`data/master/*.parquet filter=lfs ...`) matches them. Files: `busloans, dtwexbgs, ioer, iorb, m2_sl, rrpontsyd, sofr, tedrate, totll, walcl, wdtgal, sofr` (LC v1.0 source data). The `_catalog.json` modifications stashed on spec branch (stash@{0}) reference them. Either commit via LFS or document the regeneration command in master spec.

4. **Pytest viz suite slowdown.** Tests in `tests/viz/test_v11_2_3_surface_*_chart.py` (Surfaces 2-8 chart rendering tests) run at ~30 sec/test in the local environment, causing the full suite to take 15+ minutes on main HEAD without finishing the summary line. A separate test, `tests/viz/test_v11_2_3_svgnan_real_browser.py`, hangs entirely on Playwright fixture setup. Root cause likely fixture or matplotlib backend setup. Profile and fix before v2.0 work — these tests must remain runnable as gates.

### P2 (defer, but track)

5. **MyPy strict 134-error backlog.** Cleanup is a sprint-sized effort; deferring is acceptable as long as no new errors are added. Top files by error count: `src/quant_engine/runner.py`, `src/models/probability_engine.py`, `src/models/lc_v1_calibration.py`, `src/cli.py`. Reasonable to land incremental fixes in v11.4 sub-stages without explicit dedicated stage.

6. **Ruff 8 errors in `scripts/`** (7 `E402`, 1 `F841`). Either expand the `pyproject.toml` per-file ignore list to include `scripts/**/*.py` (parallel to the `tests/` precedent for E402) or fix the imports.

7. **24 `REVIEW_PACKAGE_v*.md` files at `buffet_indicator/` root** (v4 through v11.2.2). Heavy accumulation. Move pre-v11 entries into `archive/REVIEW_PACKAGE/` and leave only the 5 most recent at root.

8. **49 PNGs + 8 versioned subdirs under `outputs/screenshots/`** (v8b through v11.2_stat), 46.4 MB total. Archive pre-v11.2 versions; keep the 2-3 most recent.

9. **10 `capture_v*_screenshots.py` scripts under `scripts/`** (v9.0 through v11.2_stat). Consolidate into a single parametrized capture script or archive pre-v11.2 entries.

10. **76 log files under `logs/`** accumulated since v10. The `.gitignore` already excludes `logs/*` except `.gitkeep` and a few whitelisted PROGRESS files, but the committed entries (per `git ls-files`) include many v10 / v11.0 / v11.1 / v11.2 build logs. Archive pre-v11.3 logs.

11. **15 files in `reviews/diagnostic_artifacts/`** (capture scripts + JSON / log / HTML outputs from the v11.2.3 SVG NaN investigation). Move under `archive/` once the investigation is fully closed.

12. **Bandit 17 Low issues.** Mostly `B110:try_except_pass`. Replace `except: pass` with logged-and-continue where intent is to swallow, or add `# nosec B110` with rationale.

13. **`stash@{1}: pre-session-6 leftover state`** is still on the stash from before v11.3.0. Owner reviews — most likely safe to drop, but flagged for explicit decision.

14. **`stash@{0}: pre-stabilization-2026-05-23-spec-branch-local-mods`** created this session to clear the spec-branch working tree before the gate sweep. Contents: `_catalog.json` (catalog entries for 12 LC parquets), `nber_recessions.meta.json` (vintage bump 2026-05-20 → 2026-05-22), 10 `outputs/screenshots/v9_0_*.png` regenerations. All regeneratable. Owner decides whether to drop or unstash for inclusion in v2.0 data layer.

## 2. Closed technical debt items (this session resolved)

- None directly closed; this session is the registry's first issuance. Future stabilization sessions will append "closed" entries when items in §1 are resolved.

## 3. Known limitations (NOT debt — intentional design choices)

- v11.3.0 LC v1.0 panel lives on `spec/liquidity-composite-v1.0` (not merged to main). This is by Strategist arbitration (per `LC_V1_SPRINT_CLOSEOUT_REPORT.md` §8 — three options open: feature-flag merge, indefinite spec-branch retention, or merge-with-disclosure); not debt.
- RRPONTSYD zero-fill pre-2013-09-23 per `DECISIONS.md` 2026-05-24 Q1. Documented, intentional, not debt.
- ICE DXY cache requires Norgate Diamond subscription for re-bootstrap. Cache committed via Git LFS; survives subscription cancellation. Not debt.
- Campbell-Yogo table coverage limited to `c ∈ {-50, -20, -10, -5, -2, 0}` (per Session 7 §2.F.1). Cells with `c` outside this range return NaN. Documented in `src/models/lc_v1_regression.py` docstring. Acceptable per master spec §3.5.

## 4. Stale branches (candidates for cleanup)

`git branch -a --no-merged main` lists only `spec/liquidity-composite-v1.0` (and its origin counterpart), which is intentional pending Strategist's merge-to-main decision. **No stale branches require action.**

`spec/liquidity-composite-v2.0` is newly created by this session as an empty scaffold (no pre-reg sealed yet); see `POST_V11_3_0_STABILIZATION_REPORT.md` §2.4.

## 5. Multiple PROGRESS files (consolidation candidate)

Three competing PROGRESS files on main:

| File | Lines (main) | Latest entry | Status |
|---|---|---|---|
| `PROGRESS_v11_2_3_combined.md` | 274 | v11.2.3-s2 SVG NaN hotfix (Session 4) | **canonical** |
| `PROGRESS_v11_2_2_and_v11_3.md` | 176 | v11.2.2 baseline + P0 ship | older / partial |
| `logs/v11_2_progress.md` | 135 | v11.2 work pre-Session 1 | oldest |

Note: on `spec/liquidity-composite-v1.0`, `PROGRESS_v11_2_3_combined.md` extends to 502 lines with Sessions 5–8 (LC v1.0 sprint). The main-branch version stops at Session 4 because the LC sprint never merged.

This stabilization session appends to `PROGRESS_v11_2_3_combined.md` on main (canonical). Strategist arbitrates whether to archive the two older files in a follow-up.

## 6. CI health

- Recent 10 runs of `deploy.yml`: **0/10 green** (all failures, all `workflow_dispatch` on `spec/liquidity-composite-v1.0` branch over 2026-05-22 16:22Z to 18:31Z). See §1 P1 item 2 for root cause.
- No CI runs on main since v11.2.3-s2 hotfix (commit `27d3a7b`).
- Workflow file: `.github/workflows/deploy.yml` (last modified during v11.2.3-s2).

## 7. Test coverage gaps

Not measured this session (full-suite coverage report blocked by viz tests slowdown — see §1 P1 item 4). Once the viz slowdown is fixed, re-run with `pytest tests/ --cov=src --cov-report=term-missing` and document modules below 90%.

## 8. Bundle / disk health

| Path | Size | Ceiling | Status |
|---|---|---|---|
| `outputs/dashboard.html` | 10.36 MB | 20 MB | OK (52% headroom) |
| `outputs/` total | 61.7 MB | — | dominated by `screenshots/` |
| `outputs/screenshots/` | 46.4 MB | — | P2 candidate (§1 item 8) |
| `outputs/tables/` | 3.1 MB | — | OK |
| `data/master/` | 0.6 MB | LFS quota | OK; 16 files |

Git LFS quota: not checked this session; verify in GitHub Settings → Billing if storage approaches free tier limit. No LFS issues reported by `git lfs fsck`.

## Append-only — future updates

(Each future stabilization session appends a new dated section here.)
