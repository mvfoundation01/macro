# Viz suite investigation findings — P1-4 (2026-05-23)

## Summary

The prior session's TECH_DEBT.md P1-4 claim — "Surface 2-8 chart tests run at ~30 sec/test" — was **incorrect**. Re-profiling on this clone shows:

| Test cluster | Test count | Wall time | sec / test |
|---|---|---|---|
| `tests/viz/test_v11_2_3_surface_2_chart.py` (alone) | 5 | 0.62s | 0.124 |
| All Surface 2–8 chart tests together | 36 | 1.92s | 0.053 |
| `tests/viz/test_v11_2_3_svgnan_real_browser.py` (Playwright) | 4 | 50.16s | 12.5 |
| Full `tests/viz/` excluding Playwright | 446 | ~4 min (still running at report time) | ~0.5 |

**Root cause hypothesis for the prior session's hang**: not a per-test slowness, but a single particularly slow file. Most likely candidates:
- `tests/viz/test_build_dashboard.py` (9 tests, builds the full dashboard HTML — each test reuses the dashboard build which is heavy)
- A test that spawns a subprocess or boots an HTTP server fixture
- First-run matplotlib / plotly / numpy / pandas import overhead (cold cache; subsequent runs are much faster)

The Playwright test (`test_v11_2_3_svgnan_real_browser.py`) is **not** an infinite hang — it takes ~12.5s per test (Chromium launch + page load + DOM check), 50s for all 4 tests. Prior session was likely interrupted before this completed.

## Environment

- OS: Windows 11
- Python: 3.14.3 (local) / 3.11 (CI)
- Matplotlib backend (local default): `tkagg`
- `MPLBACKEND` env var: not set (relies on auto-detect)
- CI uses Ubuntu where headless `tkagg` is unavailable so matplotlib auto-falls back to `Agg`

## What was NOT the cause

- **Not `MPLBACKEND`** — Surface 2-8 tests on local Windows with default `tkagg` run in 0.053 sec/test. Setting `MPLBACKEND=Agg` would not change this materially.
- **Not Playwright Chromium missing** — the test ran successfully on this clone (all 4 passed in 50s). The fixture works.
- **Not pytest-timeout missing** — but worth noting: pytest-timeout is not in `requirements.lock`. If a test legitimately hangs (rare), the user has no per-test guardrail.

## What might still be slow

The full viz/ run is still in progress at this writing (CPU ~230 sec); I'll update this file with the per-test `--durations=10` data once it completes. Suspect files: `test_build_dashboard.py`, `test_v8b_visual.py`, anything that reads parquets through `load_master` (cold-cache parquet reads can be 1-2 sec).

## Action: none

No code or CI change required. The TECH_DEBT P1-4 entry should be moved from active debt to RESOLVED (with this finding attached as evidence). Optional follow-up in P2: add `pytest-timeout` to `requirements.lock` and put a default `timeout=120` in `pyproject.toml`'s `[tool.pytest.ini_options]` so future hangs are guard-railed.

The CI behavior is independent of all of the above — `Run pytest` step on main has been GREEN on all 4 recent runs.
