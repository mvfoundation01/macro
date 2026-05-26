# Test Count Snapshot — v11.4 Sprint Endpoint

**Snapshot timestamp**: 2026-05-26T12:50Z (UTC)
**Repository state**: HEAD `f17b37f` on `spec/liquidity-composite-v2.0`
**Pinned environment**: Python 3.12.10 + sealed pins per `requirements.lock`
  (arch 7.0.0, pandas 2.2.3, numpy 1.26.4, scipy 1.13.1, statsmodels 0.14.2)

---

## Headline (citation-ready)

### Verdict-bearing scope (SSRN appendix citation)

> "The v11.4 sprint's verdict-bearing implementation comprises **247 passing
> automated tests** under the sealed-pinned library environment (Python
> 3.12.10; arch 7.0.0; pandas 2.2.3; numpy 1.26.4; scipy 1.13.1;
> statsmodels 0.14.2). The verdict-bearing path is
> `tests/models/` + `tests/stats/` + `tests/replication/` and exercises
> the v2 panel builder, regression, verdict writer, criteria evaluators,
> HAC + bootstrap + skew-t + Stambaugh statistical machinery, and master
> data reconstruction. All 247 tests passed at sprint endpoint
> (HEAD `f17b37f` on `spec/liquidity-composite-v2.0`)."

### Full local-runnable scope

| Metric | Count |
|---|---|
| **Total tests collected** | 1,135 |
| Total tests collected (excluding viz) | 695 |
| Tests passed (excluding viz) | **665** |
| Tests skipped (excluding viz) | 30 |
| Tests failed | 0 |
| Tests errored | 0 |
| Warnings (deprecation / runtime) | 8 |
| Wall time (excluding viz) | ~56s |
| Wall time (verdict-bearing scope) | ~42s |

Notes on the 30 skipped tests (excluding viz):
- 24 of 30 are acceptance-gate tests (`ACCEPTANCE!=1` env-gated; on-demand only)
- 2 are integration tests (`INTEGRATION_TESTS!=1` env-gated)
- 1 needs the `xlwt` module (legacy XLS, not pinned)
- 3 are forward-work surface tests (Surface 2 Drawdowns + Extended Analytics
  surfaces — not yet built in this session; intentional skips)

## Per-module breakdown (collected counts)

| Test directory | Collected | Notes |
|---|---|---|
| `tests/models/` | 210 | v2 panel builder, regression, verdict writer, criteria |
| `tests/stats/` | 29 | HAC, bootstrap, skewt, Stambaugh, sample gate, hard_gate |
| `tests/replication/` | 8 | reconstruction script (mocked I/O) |
| `tests/ingest/` | 64 | FRED loader, master archive, splicing |
| `tests/transform/` | 291 | PIT z-score, splice helpers, composite + per-component computes |
| `tests/viz/` | 440 | Dashboard charts; Playwright-dependent (run in CI deploy.yml, not pinned env) |
| `tests/backtest/` | 10 | Backtest engine |
| `tests/deploy/` | 6 | Deploy workflow checks |
| `tests/quant_engine/` | 49 | Strategy Engine v11.1/v11.2 stages |
| `tests/seal/` | 2 | Sealed pre-reg metadata cross-platform |
| `tests/test_v*_acceptance.py` (top-level) | 26 | Acceptance gates (skipped without `ACCEPTANCE=1`) |
| **TOTAL** | **1,135** | |

## Verdict-bearing scope (the SSRN claim)

`tests/models/` + `tests/stats/` + `tests/replication/` collectively cover:

- Panel builder (per-origin `load_master(vintage=t)`, no look-ahead leakage)
- OOS regression at each origin (HAC inference, walk-forward)
- Six of seven criterion evaluators (C1–C4 + C6 + C7); C5 is the
  stationarity gate evaluated in `tests/stats/`
- Verdict JSON writer (byte-exact, LF-only via `.gitattributes`)
- Sample gate (n_obs ≥ floor)
- Hard gate (PASS/FAIL/NOT_EVALUABLE assignment)
- Bootstrap CI (block-bootstrap, n_bootstrap floor)
- HAC variance estimator (NW kernel, optimal bandwidth)
- Stambaugh small-sample bias correction
- Skew-t parametric loglik
- Master reconstruction script (FRED-equivalent + splicing)

Run anytime under pinned env:

```powershell
$pinnedPython = "$env:TEMP\macro_v2_pinned_venv\Scripts\python.exe"
cd D:\macro\buffet_indicator
& $pinnedPython -m pytest tests/models/ tests/stats/ tests/replication/ -q --tb=short
# Expected: 247 passed in ~42s
```

## v11.4 sprint-specific test additions (approximate, by phase)

| Phase | Tests added | Purpose |
|---|---|---|
| Phase D (statistical layer) | ~20 | Econometric machinery TDD: HAC, bootstrap, Stambaugh, skew-t |
| Phase E (verdict writer) | ~15 | Verdict JSON construction, criterion audit, sample/hard gates |
| Phase F-BLK1 | 16 | Per-origin fvm + synthetic look-ahead + expanding R² + n_bootstrap gate + byte-exact SHA + skew-t logging |
| Phase F-DOC | 14 | Display framing per §7 + normalize comparison + pinned-env test verification |
| Phase F-REPRO | 8 | Reconstruction script (mocked I/O, ~all subtests for `reconstruct_master.py`) |
| **Total v11.4-added** | **~73** | (out of 247 verdict-bearing) |

Pre-v11.4 tests (older sprints, pre-existing): ~174 / 247 verdict-bearing.

## Reproducibility note

This snapshot was taken locally on Windows 11 (Python 3.12.10 pinned venv).
Identical counts are expected on Linux/macOS under the same pinned env,
since:

1. `tests/viz/` is the only Playwright-dependent suite; it is gated by the
   deploy.yml workflow (Linux runner with `playwright install`) and not
   exercised here.
2. The remaining 695 tests are pure-Python computational tests with no
   browser, networking, or OS-specific dependencies (gated `ACCEPTANCE=1`
   and `INTEGRATION_TESTS=1` tests aside).

For full citation-ready reproducibility, see
`buffet_indicator/outputs/replication/REPLICATION_INSTRUCTIONS.md` (§4 Verify
verdict).

## Log artifacts

- `outputs/final_test_count_snapshot.log` — full pytest output, 61 lines,
  documenting 665 passed / 30 skipped / 0 failed / 0 errored in 55.83s for
  the `tests/ --ignore=tests/viz` scope.
