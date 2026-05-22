# LC v1.0 Sprint Closeout Report (v11.3.0)

**Sprint**: v11.3 (LC v1.0 — pre-registered liquidity composite).
**Closeout tag**: `v11.3.0` (commit `d56174c`).
**Verdict**: FAIL per pre-registration §2.1 decision rule (`n_pass = 0 of 7`). Display framing: DIAGNOSTIC ONLY.
**Branch**: `spec/liquidity-composite-v1.0` — NOT merged to main; Strategist arbitrates merge timing.

---

## 1. Sprint summary

9 sessions, 2026-05-21 through 2026-05-25.

| Session | Date | Tag-level scope |
|---|---|---|
| 1 | 2026-05-21 | Stage 0 deploy infrastructure + Stage 1 SVG NaN diagnosis |
| 2 | 2026-05-22 | Stage 0.5 finalize + Stage 2 |
| 3 | 2026-05-22 | Stage 0.5 ship + Stage 2 |
| 4 | 2026-05-22 | SVG NaN regression hotfix |
| 5 | 2026-05-22 | Stage 3 LC v1.0 data layer (A1 FRED ingest + A2 ALFRED vintages) |
| 6 | 2026-05-23 | Stage 3 LC v1.0 modeling (A1-ICEDXY + B splices + C components + D composites + E regression) |
| 6.5 | 2026-05-23 | One-shot bootstrap + build + 12-cell regression |
| 7 | 2026-05-24 | DECISIONS arbitration + investigation + F (50K bootstrap + Campbell-Yogo + conditional probs) + G (calibration) |
| 8 | 2026-05-25 | DECISIONS-2 addendum + H (diagnostics) + I (DIAGNOSTIC panel) + J (verdict + write-up + v11.3.0 closeout) |

Approximate cumulative commit count: ~50+ on the LC v1.0 sprint branch. ~30 tags pushed. ~880+ tests cumulative.

## 2. Verdict

**LC v1.0: FAIL**. `n_pass = 0 of 7` testable criteria. Per pre-registration §2.1 decision rule (`n_pass ≤ 3 → FAIL`) and §12.2 (FAIL → DIAGNOSTIC ONLY display framing). Confidence floor 99% (criterion thresholds sealed in pre-reg `a8635ef`; realized values well outside thresholds).

**Scorecard table** (locked in `outputs/lc_v1_verdict.json`):

| # | Criterion | Threshold | Realized | Pass |
|---|---|---|---|---|
| 1 | OOS R² @ 1Y on LC_TIER2 | > 0.005 | −0.0167 | ❌ |
| 2 | OOS R² @ 3Y on LC_TIER2 | > 0.020 | −0.0028 | ❌ |
| 3 | OOS R² @ 5Y on LC_TIER2 | > 0.040 | −0.0602 | ❌ |
| 4 | LC_FULL NW t > 1.65 (POSITIVE) any horizon | t > 1.65 ∧ β > 0 | best is 3Y: β=−0.034, t=−3.08 (sign FAIL) | ❌ |
| 5 | ADF rejects null for all 5 components | p < 0.05 for all | z₁ p=0.17, z₄ p=0.37, z₅ p=0.08 fail | ❌ |
| 6 | Max VIF across 5 components < 5 | max < 5 | z₅ VIF=7.58, z₁ VIF=6.02 | ❌ |
| 7 | Any Bonferroni-sig (component × horizon) cell at p < 0.0025 | any cell | only z₁ NetFed @ 10Y (n=42, insufficient-sample-flagged per DECISIONS.md 2026-05-25 Q4) | ❌ |

## 3. Three publishable research findings

### 3.1 Robust negative β at 3-year horizon

* **LC_DEEP @ 3Y**: β = −0.053, NW t = −1.89, p_1sided = 0.029, Campbell-Yogo 95% CI [−0.105, −0.002] excludes zero, n = 509 monthly obs (45-year sample).
* **LC_FULL @ 3Y** (post-zero-fill): β = −0.034, NW t = −3.08, p_1sided = 0.0013, CY 95% CI [−0.053, −0.015] excludes zero, n = 126.

### 3.2 5-of-5 component-level negative β anomaly

All five univariate component regressions report NEGATIVE β at all four horizons (z₄ at 10Y essentially zero). Pre-reg §4.1 priors expected POSITIVE β on all five. Four sign-check sensitivity tests rule out composite-construction artifacts; the anomaly is component-level.

### 3.3 Universal Gaussian forecast distribution miscalibration

PIT Kolmogorov-Smirnov p-values < 0.0001 across all 12 (scope × horizon) cells. CRPS skill mostly negative (prevailing-mean benchmark beats model). The Gaussian conditional forecast distribution — mean from regression, SD from residuals — is rejected universally vs fat-tailed empirical equity returns.

## 4. Methodological lessons

1. **Prior calibration matters**. Pre-reg §4.1 priors based on 1970s–90s monetarist intuition systematically miss the modern (post-2008) mean-reversion regime. Future composites should explicitly cover both literature streams with separate prior probabilities for each component sign.

2. **Distributional assumption matters**. Conditional-Gaussian forecast distributions fail universally for equity returns. Future probabilistic frameworks should default to skewed-t (Hansen 1994), mixture, or empirical-kernel distributions.

3. **Insufficient-sample handling matters**. Cells where n_obs_insample < 5 × HAC_lag (e.g., LC_FULL @ 10Y with n=42, HAC lag=119) produce statistical artifacts. The threshold should be an explicit pre-registered gate, not a post-hoc filter.

4. **Pre-registration discipline works**. The FAIL verdict is the system functioning correctly. Without pre-registration, the negative-β finding could easily have been mis-presented as a contrarian signal; with pre-registration, it is recorded as a research finding while the conviction headline correctly defaults to DIAGNOSTIC ONLY.

## 5. Artifacts produced

### 5.1 Code modules (under `src/`)

| Path | Purpose |
|---|---|
| `src/ingest/lc_v1_loader.py` | FRED + Norgate ICE DXY ingest |
| `src/ingest/fred_alfred_loader.py` | ALFRED vintage shim |
| `src/transform/lc_v1_splices.py` | 4 splice functions (BUSLOANS→TOTLL, ICEDXY→DTWEXBGS, IOER→IORB, TED→SOFR-IORB) |
| `src/models/lc_v1_components.py` | 5 component z-scores + PIT expanding-window helper |
| `src/models/lc_v1_composite.py` | 3 composite scopes (LC_FULL/TIER2/DEEP) + parquet writer with HARD GATE |
| `src/models/lc_v1_regression.py` | 12-cell predictive regression + Newey-West + Stambaugh + 50K bootstrap + Campbell-Yogo + conditional probabilities |
| `src/models/lc_v1_calibration.py` | Brier + Murphy + CRPS + log score + PIT + reliability diagrams |
| `src/models/lc_v1_diagnostics.py` | ADF + KPSS + PP + Zivot-Andrews + VIF + Bai-Perron |

### 5.2 Build scripts (under `scripts/`)

| Path | Purpose |
|---|---|
| `scripts/bootstrap_icedxy_from_norgate.py` | One-shot Norgate ICE DXY cache write |
| `scripts/build_lc_v1_artifacts.py` | Canonical driver (composites + regression) |
| `scripts/build_lc_v1_artifacts_robustness.py` | Truncate-mode robustness companion |
| `scripts/lc_v1_per_component_regressions.py` | Univariate per-component regressions |
| `scripts/investigate_rrpontsyd.py` | RRPONTSYD pre-2013 empirical investigation |
| `scripts/lc_v1_calibration_run.py` | Calibration driver |
| `scripts/build_lc_v1_diagnostics.py` | Diagnostics driver |
| `scripts/build_lc_v1_dashboard_panel.py` | DIAGNOSTIC ONLY panel builder |

### 5.3 Data + outputs (under `data/` and `outputs/`)

| Path | Purpose |
|---|---|
| `data/master/icedxy_close.parquet` | ICE DXY daily cache (Norgate `$USDX`, 1971-01-04 → 2026-05-21, n=14,129) |
| `data/master/_source_policy.json` | ICE DXY 3-tier priority record |
| `outputs/lc_v1_composites.parquet` | Monthly composite scopes (zero-fill canonical) |
| `outputs/lc_v1_composites_truncate.parquet` | Robustness companion (truncate mode) |
| `outputs/tables/lc_v1_predictive_regression.csv` | 12-cell composite regression (50K boot + CY) |
| `outputs/tables/lc_v1_predictive_regression_truncate.csv` | Robustness |
| `outputs/tables/lc_v1_per_component_regressions.csv` | 5 components × 4 horizons |
| `outputs/tables/lc_v1_conditional_probabilities.csv` | 12 cells × 7 tail events |
| `outputs/tables/lc_v1_calibration.csv` | 12 cells × Brier+CRPS+PIT+log metrics |
| `outputs/tables/lc_v1_stationarity.csv` | ADF/KPSS/PP/ZA on 5 components + 3 composites |
| `outputs/tables/lc_v1_diagnostics.csv` | VIF + multicollinearity flag |
| `outputs/tables/lc_v1_component_correlation_matrix.csv` | 5×5 |
| `outputs/tables/lc_v1_component_eigenvalues.csv` | 5 rows |
| `outputs/tables/lc_v1_bai_perron_breaks.csv` | Bai-Perron breaks per composite |
| `outputs/figures/lc_v1_reliability_diagram_LC_TIER2_10y.png` | + LC_DEEP_5y |
| `outputs/figures/lc_v1_pit_histogram_LC_TIER2_10y.png` | + LC_DEEP_5y |
| `outputs/lc_v1_diagnostic_panel.html` | Standalone DIAGNOSTIC panel |
| `outputs/lc_v1_verdict.json` | **LOCKED verdict** |
| `outputs/reports/lc_v1_research_writeup.md` | Academic-style research draft |

### 5.4 Specs + governance

| Path | Purpose |
|---|---|
| `specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md` | Sealed pre-registration (commit `a8635ef`) |
| `specs/RECON_lc_v1_2026-05-22.md` | Reconnaissance / planning |
| `specs/BLOCKED_v11_3_A1_icedxy_stooq.md` | Stooq blocker + Session 6 §2.0 resolution |
| `specs/INVESTIGATION_session_7.md` | Pre-reg verification + sign checks |
| `DECISIONS.md` | Strategist arbitration log (2026-05-24 + 2026-05-25) |

## 6. Invariants verified

| Invariant | Status |
|---|---|
| v50 ORIGINAL SHA256 = `6087918DB909D3BB3AE66F43305C3331E4171AEBC55DDC0366AAFF6128026F47` | ✅ unchanged across all 9 sessions |
| Pre-reg `a90b02d` (MV-Conditional, on `main`) | ✅ untouched |
| Pre-reg `a8635ef` (LC v1.0, ancestor of HEAD on spec branch) | ✅ HARD GATE enforced at every artifact write |
| No force-push / history rewrite on `spec/liquidity-composite-v1.0` | ✅ |
| All sealed pre-reg values (splice dates, gate thresholds, weights, scopes, priors, falsifiability criteria) | ✅ unchanged |
| Bundle ≤ 20 MB | ✅ standalone DIAGNOSTIC panel: 173 KB |

## 7. v11.4+ amendment candidates

These are NOT actionable in v11.3 (sealed); they are notes for the next-version Strategist:

1. **Pre-reg §4.1 priors**: re-anchor with both monetarist and mean-reversion literature streams; separate prior probabilities per component sign.
2. **Criterion 4 wording**: disambiguate "positive sign AND |t| > 1.65" vs "any |t| > 1.65" explicitly.
3. **Conditional probability framework**: default to non-Gaussian (skewed-t Hansen 1994 / empirical kernel) given universal Gaussian failure documented in v11.3.
4. **Insufficient-sample gate**: `n_obs_insample < 5 × HAC_lag` as an explicit pre-reg condition rather than a post-hoc filter.

A v11.4 LC v2.0 pre-registration based on these amendments should be tested on a held-out 2025–2027 window (not yet used for LC v1.0 estimation) to preserve pre-registration discipline.

## 8. Owner action required

**Paste this report to the Strategist for merge-to-main arbitration.**

The Strategist arbitrates merge timing. Three options per Session 8 prompt §2.J.6:

a) **Merge with explicit feature flag**: bring the LC v1.0 code + DIAGNOSTIC panel into `main` but gate visibility behind a feature flag so the production dashboard does not surface the FAIL-verdict content by default.

b) **Keep on spec branch indefinitely as a research record**: do not merge; `spec/liquidity-composite-v1.0` remains the canonical reference for the LC v1.0 work.

c) **Merge but tag main as 'diagnostic-only-research-content'**: integrate fully into `main` with a clear top-of-README disclosure that the LC v1.0 panel is research output, not production signal.

The Strategist's recommendation should be recorded in a new `DECISIONS.md` entry post-`v11.3.0`.

---

## Session-by-session links

* Session 1 final report: `PROGRESS_v11_2_3_combined.md` §"Session 1"
* Session 2 final report: `PROGRESS_v11_2_3_combined.md` §"Session 2"
* Session 3, 4, 5: `PROGRESS_v11_2_3_combined.md`
* Session 6 final report: `SESSION_6_FINAL_REPORT.md`
* Session 6.5 final report: `SESSION_6_5_FINAL_REPORT.md`
* Session 7 final report: `SESSION_7_FINAL_REPORT.md`
* Session 8 final report: `SESSION_8_FINAL_REPORT.md`
