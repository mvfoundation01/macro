# Pre-Registration — Liquidity Composite v1.0

**Status**: SEALED — modifications require amendment file + DECISIONS.md entry per master spec §6.1.
**Spec parent**: `D:\macro\prompt\052126\PROMPT_v11_2_2_and_v11_3__mega_sprint.md` Part B (sections B.0 through B.21).
**Sprint**: v11.3 Liquidity Composite v1.0 institutional research module.
**Strategist sign-off**: Claude AI Session N, 2026-05-22 (per spec §20.1).
**Branch**: `spec/liquidity-composite-v1.0`.
**Pre-registration discipline**: per Munafò et al. 2017 + AEA Pre-Analysis Plans norms.

This document is the **first git action** in Part B. **Per spec §0.1, no LC backtest
artifact (`outputs/lc_*.parquet`, `outputs/figures/lc_*.png`, `outputs/tables/lc_*.csv`)
may be created with a git timestamp earlier than this file's commit.** If `git log
specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md` shows a commit timestamp AFTER any LC
artifact, the entire sprint is **REJECTED** per spec §0.1's HARD REJECTION CRITERION.

---

## 1. Locked composition (per spec §0.2)

### 1.1 Five components and weights (LC_FULL)

| # | Component | Weight | Sign on equity returns |
|---|---|---|---|
| z₁ | NetFed = WALCL − WDTGAL − RRPONTSYD (monthly aggregate) | +0.25 | + |
| z₂ | M2_growth_yoy = (M2SL_t / M2SL_{t−12}) − 1 | +0.20 | + |
| z₃ | BankLend_growth_yoy = (BankLend_t / BankLend_{t−12}) − 1, spliced BUSLOANS↔TOTLL @1973-01 | +0.20 | + |
| z₄ | DXY⁻¹ = −z(log DXY), spliced ICE DXY↔DTWEXBGS @2006-01 | +0.20 | + |
| z₅ | Funding_stress, spliced TED↔SOFR−IORB @2022-01 with blended transition | −0.15 | + on liquidity (since stress enters with negative weight) |

Sum of absolute weights = 1.00 (= 0.25 + 0.20·3 + 0.15).

### 1.2 Nested scopes (per spec §1.3)

| Scope | Components active | Effective monthly start | Reason |
|---|---|---|---|
| **LC_FULL** | All 5 (z₁ + z₂ + z₃ + z₄ + z₅) | 2003-01 | NetFed (WALCL) starts 2002-12 → 12-mo warm-up → 2003-12 valid first composite; pragmatically anchored at 2003-01 with NetFed partially warming up |
| **LC_TIER2** | Drops z₁; renormalized {z₂ z₃ z₄ z₅} weights | 1987-01 | Funding (TED) starts 1986-01 → 12-mo warm-up → 1987-01 first valid |
| **LC_DEEP** | Drops z₁ AND z₅; renormalized {z₂ z₃ z₄} | 1973-01 | BankLend (TOTLL) starts 1973-01 (BUSLOANS earlier); 12-mo warm-up → 1974-01 first valid; pragmatically 1973-01 |

LC_TIER2 renormalized weights: 0.267, 0.267, 0.267, −0.200.
LC_DEEP renormalized weights: 0.333, 0.333, 0.333.

### 1.3 Splice methodologies (per spec §3)

| Splice | Space | Date | Validation gates |
|---|---|---|---|
| BUSLOANS → TOTLL | YoY growth-rate (additive c) | 1973-01-03 | corr > 0.50, abs(c) < 0.05 |
| ICE DXY → DTWEXBGS | log levels (additive c) | 2006-01-04 | corr > 0.85, mean abs z-divergence < 0.30 |
| IOER → IORB | level concat (no splice) | 2021-07-29 | abs(IOER@2021-07-28 − IORB@2021-07-29) < 0.01pp |
| TED → SOFR−IORB | z-score linear-blend transition 2022-02 → 2023-04 | 2022-01-22 | abs(funding_z.diff().max()) < 1.5σ |

### 1.4 Standard PIT z-score computation (per spec §2.1)

- Expanding window, mean + sample SD (Bessel n−1), strict PIT excluding current observation.
- Minimum sample threshold: n ≥ 120 observations before non-NaN z.
- All components brought to month-end-of-month frequency before z-scoring.
- Real-time vintages (ALFRED) for revisable series: M2SL, BUSLOANS, TOTLL, WALCL, WDTGAL.

---

## 2. Locked falsifiability criteria (per spec §12.1 — 7 criteria)

**Decision rule** (per spec §12.2):
- `n_pass ≥ 5` → **PASS** — headline LC tab promoted prominently.
- `n_pass == 4` → **PASS_WITH_CAVEATS** — headline LC tab with disclosure card.
- `n_pass ≤ 3` → **FAIL** — DIAGNOSTIC ONLY view, no actionable conviction/probability.

In all cases, the pipeline still runs; the verdict affects dashboard framing only.

### 2.1 The 7 criteria (SEALED)

| # | Criterion | Threshold | Scope applied |
|---|---|---|---|
| 1 | OOS R² (Goyal-Welch 2008) on 1Y SPX TR | > 0.005 | LC_TIER2 (longest reliable sample for 1Y) |
| 2 | OOS R² on 3Y SPX TR | > 0.020 | LC_TIER2 |
| 3 | OOS R² on 5Y SPX TR | > 0.040 | LC_TIER2 |
| 4 | Predictive β sign | Positive with Newey-West HAC t > 1.65 (1-sided p<0.05) | LC_FULL (headline scope) |
| 5 | ADF rejects unit root (p < 0.10) on each of 5 component z-scores | Reject for all 5 | Per-component (z₁ through z₅) |
| 6 | Maximum cross-component VIF | < 5 | Per-component panel |
| 7 | Bonferroni-corrected p-value (5 components × 4 horizons = 20 tests, FW α = 0.05) | At least 1 (horizon × component) significant at Bonferroni α/20 = 0.0025 | LC_FULL or LC_TIER2 |

### 2.2 What does NOT get pre-registered (allowed post-hoc adjustment per spec §0.3)

- Visual dashboard styling (colors, font sizes, layout polish).
- Test coverage above the 90% floor.
- Documentation prose.
- Sensitivity analyses BEYOND the 7 locked criteria (labeled exploratory in REVIEW_PACKAGE).

### 2.3 Component-empirically-impossible carveout (per spec §18)

If a pre-registered criterion is empirically impossible (e.g., insufficient SOFR-IORB
observations for ADF in LC_FULL), Claude Code documents the finding in REVIEW_PACKAGE
under "Falsifiability scorecard" with rationale, and the criterion counts as **FAIL**
for that scope. Strategist arbitrates whether to re-weight criteria or proceed with
a CAVEATS verdict.

---

## 3. Locked methodological choices (per spec §0.2 + §5)

### 3.1 Predictive regression specification

```
r_{t, t+h} = α + β · LC_t + ε_{t, t+h}
```

- `r_{t, t+h}` = forward h-year total return of S&P 500 (annualized log return).
- Total return source: `SP_SPXTR_1D.csv` (post-1988) spliced with Shiller dividend-reinvested
  column (pre-1988) at 1988-01-04 with multiplicative scale anchor.
- Horizons: **1Y, 3Y, 5Y, 10Y** (4 horizons).

### 3.2 Standard errors

- **Newey-West HAC** with lag `L = h · 12 − 1` (monthly frequency). E.g., L=119 for 10Y.
- Implementation: `statsmodels.regression.linear_model.OLS(...).fit(cov_type='HAC',
  cov_kwds={'maxlags': L, 'use_correction': True})`.
- Robustness: also report **Hansen-Hodrick** estimates.

### 3.3 Bias correction

- **Stambaugh (1999)** analytical correction for persistent regressor.
- Also report bootstrap-corrected β via 10K stationary bootstrap as cross-check.

### 3.4 Out-of-sample R²

- **Goyal-Welch (2008)** prevailing-historical-mean benchmark.
- **Clark-West (2007)** MSPE-adjusted statistic for nested model comparison.
- **Campbell-Yogo (2006)** CIs when regressor is near-unit-root (ρ > 0.95).

### 3.5 Bootstrap

- **Stationary block bootstrap** (Politis-Romano 1994).
- Block length: Politis-White (2004) optimal, defaulted to `b_opt = ceil(2·N^(1/3))`.
- Replications: **10,000** for standard CIs; **50,000** for tail probabilities (P < 1%).
- Seed: `np.random.default_rng(42)`.

### 3.6 Stationarity & multicollinearity diagnostics (per spec §4)

- ADF, KPSS, Phillips-Perron, Zivot-Andrews on each component z-score and on each composite.
- Acceptance: ADF rejects AND KPSS does not reject → stationary; disagreement → conservative.
- VIF, Pearson correlation, Spearman rank, condition number, eigenvalue spectrum on
  the 5-component cross-correlation matrix.

### 3.7 Bai-Perron breaks (per spec §7)

- Multiple-breakpoint test on composites and on rolling 10-year β.
- Max breaks: 5; min regime length: 30 months; selection: BIC; trimming: 15%.

### 3.8 Calibration (per spec §8)

- Brier score + Murphy 1973 decomposition.
- Reliability diagram + isotonic regression overlay.
- Logarithmic (Ignorance) score, CRPS, PIT histogram.
- Backtest split: 1986-01 → 2010-12 estimation, 2011-01 → present validation
  (for LC_TIER2/LC_DEEP); 2013-01 → present validation for LC_FULL.

---

## 4. Empirical priors (per spec §14 — DO NOT modify post-hoc)

### 4.1 Per-component sign + correctness priors

| Component | Expected sign on SPX TR (5Y) | Prior P(correct sign in regression) |
|---|---|---|
| z₁ NetFed | + | 75% |
| z₂ M2_yoy | + | 65% (M2 surge can precede inflation, ambiguous) |
| z₃ BankLend_yoy | + | 70% |
| z₄ DXY⁻¹ (already inverted) | + | 72% |
| z₅ Funding (−0.15 weight) | − on funding stress (correct sign already baked into composite weight) | 80% |

### 4.2 Falsifiability outcome priors

| Verdict | Prior P | 95% CI |
|---|---|---|
| PASS (≥ 5/7 criteria) | 58% | [42%, 72%] |
| PASS_WITH_CAVEATS (4/7) | 25% | [12%, 40%] |
| FAIL (≤ 3/7) | 17% | [7%, 30%] |

### 4.3 Predictive R² priors (LC_TIER2, longest scope with all 4 non-NetFed components)

| Horizon | Prior median R²_OOS | Prior 95% CI |
|---|---|---|
| 1Y | 0.01 | [−0.01, +0.04] |
| 3Y | 0.04 | [+0.01, +0.10] |
| 5Y | 0.08 | [+0.03, +0.18] |
| 10Y | 0.12 | [+0.05, +0.25] |

### 4.4 Comparison-to-other-composites priors

| Comparison | Prior P(LC adds incremental info) |
|---|---|
| LC vs CAPE alone, 5Y | 70% |
| LC vs AMVI alone, 5Y | 68% |
| LC vs (CAPE + AMVI), 5Y | 52% |
| LC at 1Y horizon adds info vs no model | 50% (short horizon hard) |

---

## 5. Pre-registration verification chain

Per spec §C.1 step 5 and master spec §6.1:

```
Required git log order:
  ... → a90b02d  (preregister: MV-Conditional rule R-PRIMARY, sealed 2026-05-21)
      → <this commit>  (preregister: LC v1.0 falsifiability + priors, sealed 2026-05-21)
      → <future LC backtest artifacts>
```

Verification command (master spec §6.1 + spec §C.1):

```bash
# Both pre-registration commits must precede their respective backtests:
git log --oneline --reverse --pretty=format:"%h %ci %s" specs/MV_CONDITIONAL_RULE_PREREGISTER.md
git log --oneline --reverse --pretty=format:"%h %ci %s" specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md
```

If either pre-registration timestamp is AFTER its corresponding backtest artifact's
git timestamp, the entire sprint is **REJECTED** per spec §0.1 + §D.1.

---

## 6. Sign-off

| Role | Identity | Date |
|---|---|---|
| Strategist | Claude AI Session N | 2026-05-22 (per spec §20.1) |
| Implementer | Claude Code, fresh session | 2026-05-21 (commit timestamp) |
| Reviewer | Strategist arbitration upon REVIEW_PACKAGE_v11.3.md | TBD |

---

## 7. Items explicitly OUT OF SCOPE for v11.3 (per spec §20.2)

- LC_LEGACY 2-component variant (M2 + BankLend only, 1961+) — exploratory only.
- Pre-2002 NetFed reconstruction via H.4.1 archive — Tier 4+ effort.
- Tobin's Q decomposition of NetFed (QE vs QT separation).
- International liquidity (ECB, BoJ, PBoC) — v11.5+ international extension.
- Cross-asset liquidity (FX swaps, credit beyond TED/SOFR-IORB) — v11.4 funding/credit composite.
- Live signal feed (daily JSON) — v12.0 hosted dashboard scope.

Adding any of these in v11.3 requires amendment spec (this file does NOT cover them).

---

## 8. Cross-link to prior pre-registration

This commit extends the pre-registration discipline started in:

- `specs/MV_CONDITIONAL_RULE_PREREGISTER.md` (commit `a90b02d`, sealed 2026-05-21) —
  the v11.2 MV-Conditional rule R-PRIMARY + 2 alternatives, whose falsifiability
  test verdict was REJECT_ALL_3 per v11.2.0-stat REVIEW.

Both pre-registration files together establish a methodological track record. Each
must independently predate its respective backtest artifacts.

---

End of `MV_LIQUIDITY_COMPOSITE_PREREGISTER.md` — SEALED.
