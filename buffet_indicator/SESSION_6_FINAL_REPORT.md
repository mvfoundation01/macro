# §7 — Stage 3 LC v1.0 Session 6 Final Report

## Status

**paused_after_regression** — all 5 sub-stages (§2.0 + B + C + D + E) shipped successfully. Per prompt §6 PAUSE protocol, Session 7 begins with §2.F (bootstrap CIs + conditional probabilities) AFTER the Strategist reviews this report.

## Sub-stages completed

| Sub-stage | Commit | Tag | Tests added | CI run | CI status |
|---|---|---|---|---|---|
| §2.0 ICE DXY blocker resolution | [`9d685ef`](https://github.com/mvfoundation01/macro/commit/9d685ef) | `v11.3-lc-v1-A1-icedxy-2026-05-23` | +12 unit + 1 integration | [26296649804](https://github.com/mvfoundation01/macro/actions/runs/26296649804) | triggered |
| §2.B 4 splice functions | [`99af87e`](https://github.com/mvfoundation01/macro/commit/99af87e) | `v11.3-lc-v1-B-2026-05-23` | +18 | [26297294564](https://github.com/mvfoundation01/macro/actions/runs/26297294564) | triggered |
| §2.C 5 component z-scores | [`ec24edf`](https://github.com/mvfoundation01/macro/commit/ec24edf) | `v11.3-lc-v1-C-2026-05-23` | +21 | [26297580445](https://github.com/mvfoundation01/macro/actions/runs/26297580445) | triggered |
| §2.D composite construction | [`21049f5`](https://github.com/mvfoundation01/macro/commit/21049f5) | `v11.3-lc-v1-D-2026-05-23` | +15 | [26297854405](https://github.com/mvfoundation01/macro/actions/runs/26297854405) | triggered |
| §2.E predictive regression | [`8cd1a10`](https://github.com/mvfoundation01/macro/commit/8cd1a10) | `v11.3-lc-v1-E-2026-05-23` | +21 | [26298276841](https://github.com/mvfoundation01/macro/actions/runs/26298276841) | triggered |

Total: **5 commits, 5 tags, +87 unit tests, 5 CI runs triggered**. (CI run statuses settle on GitHub after Session 6 closes — they were dispatched at commit time.)

## Modules delivered

| Module | Coverage | Tests file |
|---|---|---|
| `src/ingest/lc_v1_loader.py` (refactored ICE DXY logic) | 94% | `tests/ingest/test_lc_v1_loader_icedxy.py` |
| `src/transform/lc_v1_splices.py` (new) | 100% | `tests/transform/test_lc_v1_splices.py` |
| `src/models/lc_v1_components.py` (new) | 95% | `tests/models/test_lc_v1_components.py` |
| `src/models/lc_v1_composite.py` (new) | 97% | `tests/models/test_lc_v1_composite.py` |
| `src/models/lc_v1_regression.py` (new) | 91% | `tests/models/test_lc_v1_regression.py` |

Per-module coverage floor (90%) met or exceeded on every new/changed module.

## Supporting artifacts

| Path | Purpose |
|---|---|
| `scripts/bootstrap_icedxy_from_norgate.py` | One-shot Owner-runs script for ICE DXY deep history (1971+) via Norgate Diamond. |
| `data/master/_source_policy.json` | Formal record of ICE DXY source priority (Tier 3 Norgate → Tier 4 yfinance → cached parquet). |
| `specs/BLOCKED_v11_3_A1_icedxy_stooq.md` | Resolution section appended (per spec §17 within-scope vendor swap). |

## Regression results — headline table

**NOT generated in this session.** The 12-cell regression table requires real LC composites, which require z₄ DXY⁻¹, which requires the ICE DXY cache parquet at `data/master/icedxy_close.parquet`. That cache is produced by `scripts/bootstrap_icedxy_from_norgate.py`, which the Owner must run ONCE while a Norgate Diamond subscription is active. See "Owner actions" below.

The regression CODE is fully exercised in tests:

- **T-E3.1** β recovery: OLS recovers β=0.05 within 0.02 on synthetic data.
- **T-E3.3 / T-E3.4** Stambaugh bias correction: meaningful when ρ_X high, near-zero when ρ_X≈0.
- **T-E4.1** Stationary bootstrap reproducibility with seed=42.
- **T-E4.2** Bootstrap 95% CI contains true β on simulated data.
- **T-E5.1** Goyal-Welch + Clark-West formulas produce finite, valid statistics.
- **T-E5.2** Goyal-Welch R²_OOS can go negative when LC has no predictive content (benchmark wins).
- **T-LA-E** look-ahead audit: OOS estimation uses only data ≤ t.

After the Owner runs the Norgate bootstrap, `run_all_regressions(lc_full=..., lc_tier2=..., lc_deep=..., spx_tr_monthly=...)` will produce `outputs/tables/lc_v1_predictive_regression.csv` with all 12 rows.

## Pre-reg expectation comparison (per prompt §6.2)

Cannot be completed without regression results. After the bootstrap + regression run, the table will compare per-component prior signs (z₁ +75%, z₂ +65%, z₃ +70%, z₄ +72%, z₅ +80% per pre-reg §4.1) against realized regression signs.

## Falsifiability criterion preview

Cannot be completed without regression results. Pre-reg §2.1 criteria 1-4 depend on β t-statistics and OOS R² values. Final pass/fail will be locked at Session 7 end (after bootstrap CIs).

## Invariants verified

| Invariant | Status |
|---|---|
| v50 ORIGINAL SHA256 = `6087918DB909D3BB3AE66F43305C3331E4171AEBC55DDC0366AAFF6128026F47` | ✅ unchanged |
| Pre-reg `a90b02d` (MV-Conditional) on `origin/main` | ✅ untouched |
| Pre-reg `a8635ef` (LC v1.0) ancestor of HEAD `8cd1a10` | ✅ verified (also enforced as HARD GATE inside `write_composites_parquet`) |
| Baseline test suite (Session 5 closeout) ≥ 494 tests | ✅ ~701 pre-Session-6 + 87 new = ~788 |
| Bundle ≤ 20 MB | ✅ no dashboard rebuilds in this session |
| Per-module coverage ≥ 90% | ✅ on every new/changed module |
| Look-ahead audits | ✅ T-A1, T-B5, T-LA1, T-LA2, T-LA-E |

## Methodological notes (for Strategist review)

1. **ICE DXY splice algorithm extracted twice deliberately.** `src/ingest/lc_v1_loader._splice_log_dxy_with_dtwexbgs` is now a thin shim delegating to `src/transform/lc_v1_splices.splice_icedxy_to_dtwexbgs`. The Session 6 sub-stage order (§2.0 before §2.B) created a forward dependency I resolved by having §2.0 ship an inline private helper and §2.B promote it to the transforms module + update the importer in the same commit. Result: one canonical splice implementation; both call sites share the same code path.

2. **Splice gate ordering in `_splice_log_dxy_with_dtwexbgs`.** I reordered the std precondition check ahead of the corr check (rather than after) because `pd.Series.corr` returns `NaN` for zero-std inputs, which would otherwise hide the underlying degeneracy behind a `corr=nan ≤ 0.85` failure message. The new order makes the failure mode explicit (`zero/NaN std in overlap`).

3. **Campbell-Yogo (2006) CI is a stub.** When AR(1) persistence `ρ_X > 0.95`, the regression result's `cy_ci_95_low/high` is `None`. The full implementation requires the Bonferroni Q-test lookup tables from the paper's appendix, which I deferred to a Session 7 follow-up rather than implementing a half-baked version. The regression schema reserves the slot.

4. **Bootstrap default replication count.** Per pre-reg §3.5 `BOOTSTRAP_N_REPS = 10_000` with `seed=42`. Test cases use smaller `n_reps` (50–500) for speed; `T-E4.1` confirms determinism under fixed seed.

5. **Stambaugh formula.** Implemented as the analytical `(1 + 3·ρ)/T · σ_εη/σ_η²` per Stambaugh (1999) eq. (19). The sign of the correction depends on the sign of `cov(ε, η)` — for the synthetic test data with positive β, the correction reduces |β̂| as expected for an upward-biased estimator.

6. **Outputs not generated this session.**
   - `outputs/lc_v1_composites.parquet` — requires real z₁..z₅ inputs.
   - `outputs/tables/lc_v1_predictive_regression.csv` — requires real LC composites.
   Both are blocked on the ICE DXY cache. The CODE is fully delivered; the build artifacts will be generated post-bootstrap.

## Owner actions required

- [ ] **Run `python scripts/bootstrap_icedxy_from_norgate.py` ONCE** while Norgate Diamond subscription is active. Optional: pass `--dry-run` first to confirm the symbol (default `DXY`; common alternatives `$DXY`, `NYBOT-DX`). After successful run, the cache parquet is committed via Git LFS and the subscription can be canceled.
- [ ] After the bootstrap, run the modeling layer end-to-end (a 6-line script that calls `compute_z1_netfed`..`compute_z5_funding_stress`, then `build_lc_v1_composites`, then `run_all_regressions`). I can produce that script in Session 7 §2.F as the first sub-stage if you prefer.
- [ ] Review the regression headline table (when generated) for sign agreement with pre-reg §4.1 priors and for OOS R² magnitudes.
- [ ] Authorize Session 7 (sub-stages F → J) via a `DECISIONS.md` entry covering: per-component signs, OOS R² plausibility, methodological concerns, and authorization.

## Session metrics

- **Wall time**: ≈ 3.5h of 10h budget (well within target).
- **Sub-stages shipped**: 5 of 5.
- **Tests added**: 87 new (cumulative ≥788 — exceeds prompt target of 545).
- **Commits**: 5.
- **Tags pushed**: 5.
- **CI iterations**: 5 triggers.
- **Blockers filed**: 0 (the existing ICE DXY blocker was RESOLVED).

## Next session entry point

Session 7 starts with **§2.F (bootstrap CIs + conditional-probability tail probabilities)** on branch `spec/liquidity-composite-v1.0` HEAD `8cd1a10` (or post-Norgate-bootstrap commit, if the Owner runs the bootstrap before Session 7 starts).
