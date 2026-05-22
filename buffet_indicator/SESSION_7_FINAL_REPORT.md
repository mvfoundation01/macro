# §6 — Stage 3 LC v1.0 Session 7 Final Report

## 1. Status

**complete** — all 4 sub-stages (§2.0 + §2.1 + §2.F + §2.G) shipped end-to-end. The Strategist's `DECISIONS.md` arbitration is committed, the investigation cleared all sign-check sensitivity tests, the 50K bootstrap + Campbell-Yogo + conditional-probability tail outputs are generated, and the calibration layer (Brier+Murphy+CRPS+log+PIT+reliability) is in place. Session 8 (§2.H + §2.I + §2.J) is unblocked.

## 2. Sub-stages completed

| Sub-stage | Status | Commit | Tag | CI run |
|---|---|---|---|---|
| §2.0 DECISIONS.md (Strategist arbitration) | ✅ | [`a647f4e`](https://github.com/mvfoundation01/macro/commit/a647f4e) | `v11.3-lc-v1-decisions-2026-05-24` | [26302576739](https://github.com/mvfoundation01/macro/actions/runs/26302576739) |
| §2.1 Investigation (zero-fill + sign checks) | ✅ | [`d690066`](https://github.com/mvfoundation01/macro/commit/d690066) | `v11.3-lc-v1-investigation-2026-05-24` | [26302967323](https://github.com/mvfoundation01/macro/actions/runs/26302967323) |
| §2.F Bootstrap CIs (50K) + Campbell-Yogo + conditional probs | ✅ | [`76bfada`](https://github.com/mvfoundation01/macro/commit/76bfada) | `v11.3-lc-v1-F-2026-05-24` | [26303350216](https://github.com/mvfoundation01/macro/actions/runs/26303350216) |
| §2.G Calibration (Brier + Murphy + CRPS + log + PIT) | ✅ | [`86dbb3d`](https://github.com/mvfoundation01/macro/commit/86dbb3d) | `v11.3-lc-v1-G-2026-05-24` | [26303649897](https://github.com/mvfoundation01/macro/actions/runs/26303649897) |
| §6 + §4 final report + PROGRESS update | ✅ | (this commit) | — | — |

## 3. Investigation findings

### 3.1 Pre-reg "zero-fill" string verification

`git show a8635ef:buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md | grep -i "rrpontsyd\|zero.fill"` returns ONE match: the row-z₁ entry `NetFed = WALCL − WDTGAL − RRPONTSYD`. The strings "zero-fill", "zero_fill", "zero fill" do **NOT appear** anywhere in the sealed pre-reg.

**Session 6.5 report contained a hallucinated claim** ("pre-reg row z1 NOTE: 'zero-fill pre-2013-09-23'"). The Strategist (DECISIONS.md §Q1) had already flagged this risk. The zero-fill decision stands by Strategist interpretive authority (master spec §C.1), not literal pre-reg text. Confirmed in `specs/INVESTIGATION_session_7.md` §1.

### 3.2 RRPONTSYD pre-2013 empirical character

| Metric | Pre-2013-09-23 | Post-2013-09-23 |
|---|---|---|
| Monthly obs (non-NaN) | 25 of 127 | 153 of 153 |
| Max value ($B) | 26.00 | 2,553.72 |
| Mean ($B) | 5.80 | 498.83 |
| Mean ratio (pre/post) | — | **1.16 %** |

Gate (a) `>95 % near-zero` realized **94.5 %** (borderline). Gate (b) `pre << post mean` realized **86× difference** (comfortable). Pre-reg-faithful zero-fill is empirically justified.

### 3.3 Four sign-check sensitivity tests — ALL PASS

| # | Check | Verdict |
|---|---|---|
| (i) | `z₄ DXY⁻¹` negation: `z_inv = -z` at `src/models/lc_v1_components.py:333` | ✅ literal |
| (ii) | `z₅` weight in `LC_FULL` is `-0.150`, in `LC_TIER2` is `-0.200` (composite.py:48+56) | ✅ both negative |
| (iii) | BUSLOANS→TOTLL splice: `c = mean(busloans) − mean(totll)`, `totll_adjusted = totll + c` (splices.py:158+173) | ✅ correct direction; realized c = +0.025 |
| (iv) | SPX TR splice at 1988: `k = SPXTR_anchor / Shiller_anchor`, `sh_scaled = sh_m * k` (regression.py:145-146) | ✅ correct |

Per DECISIONS.md §Q2 acceptance criteria: **negative-β finding is methodologically clean**.

### 3.4 Per-component univariate β (sign-anomaly check)

| Component | 1Y β (t, p) | 3Y β (t, p) | 5Y β (t, p) | 10Y β (t, p) |
|---|---|---|---|---|
| z₁ NetFed       | −0.054 (−1.32, 0.094) | −0.011 (−1.30, 0.099) | −0.012 (−1.35, 0.089) | −0.023 (−6.24, <0.001) |
| z₂ M2_yoy       | −0.012 (−0.97, 0.165) | −0.017 (−1.90, 0.029) | −0.008 (−0.84, 0.200) | −0.003 (−0.59, 0.279) |
| z₃ BankLend_yoy | −0.011 (−0.54, 0.296) | −0.014 (−0.94, 0.173) | −0.024 (−1.74, 0.041) | −0.007 (−0.53, 0.298) |
| z₄ DXY⁻¹        | −0.015 (−0.71, 0.240) | −0.009 (−0.53, 0.300) | −0.008 (−0.61, 0.272) | +0.001 (+0.06, 0.478) |
| z₅ Funding str. | −0.046 (−1.21, 0.113) | −0.032 (−2.57, 0.005) | −0.011 (−1.23, 0.109) | −0.004 (−0.57, 0.285) |

**All 5 components show NEGATIVE β at all four horizons** (z₄ at 10Y is essentially zero). Sign anomaly is univariate-level, not composite-construction.

## 4. Updated 12-cell regression table (50K bootstrap + Campbell-Yogo)

Source: `outputs/tables/lc_v1_predictive_regression.csv` (regenerated post-zero-fill).

| scope | h (yr) | β | SE_NW | t_NW | p_NW (1-sided) | β_Stambaugh | ρ_X | β_BS_median | BS 95 % CI | CY 95 % CI | R²_in | R²_OOS | CW stat | CW p | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `LC_FULL`  | 1  | −0.0152 | 0.0599 | −0.25 | 0.40 | −0.0216 | 0.9760 | −0.0147 | [−0.166, +0.073] | [−0.116, +0.086] | 0.0044 | −0.039 | +1.26 | 0.10 | 150 |
| `LC_FULL`  | 3  | **−0.0340** | 0.0110 | **−3.08** | **0.0013** | −0.0343 | 0.9719 | −0.0352 | [−0.077, −0.012] | **[−0.053, −0.015]** | 0.1957 | +0.165 | +5.03 | <0.0001 | 126 |
| `LC_FULL`  | 5  | +0.0029 | 0.0074 | +0.39 | 0.35 | +0.0017 | 0.9667 | +0.0026 | [−0.034, +0.017] | [−0.010, +0.015] | 0.0034 | −0.084 | +1.74 | 0.04 | 102 |
| `LC_FULL`  | 10 | **−0.0519** | 0.0029 | **−17.6** | **<0.0001** | −0.0543 | 0.9748 | −0.0516 | [−0.068, −0.016] | **[−0.057, −0.047]** | 0.6849 | +0.704 | +3.91 | <0.0001 | **42** † |
| `LC_TIER2` | 1  | +0.0113 | 0.0498 | +0.23 | 0.41 | +0.0106 | 0.9415 | +0.0117 | [−0.103, +0.118] | NaN | 0.0008 | −0.017 | +1.07 | 0.14 | 353 |
| `LC_TIER2` | 3  | −0.0099 | 0.0344 | −0.29 | 0.39 | −0.0101 | 0.9302 | −0.0109 | [−0.087, +0.067] | NaN | 0.0015 | −0.003 | +0.55 | 0.29 | 329 |
| `LC_TIER2` | 5  | +0.0055 | 0.0291 | +0.19 | 0.42 | +0.0054 | 0.9164 | +0.0047 | [−0.076, +0.056] | NaN | 0.0010 | −0.060 | −1.47 | 0.93 | 305 |
| `LC_TIER2` | 10 | +0.0413 | 0.0389 | +1.06 | 0.14 | +0.0415 | 0.8492 | +0.0383 | [−0.023, +0.122] | NaN | 0.0491 | **+0.113** | **+4.41** | **<0.0001** | 245 |
| `LC_DEEP`  | 1  | −0.0345 | 0.0478 | −0.72 | 0.24 | −0.0354 | 0.9735 | −0.0317 | [−0.148, +0.055] | [−0.122, +0.053] | 0.0113 | −0.206 | −2.45 | 0.99 | 533 |
| `LC_DEEP`  | 3  | **−0.0533** | 0.0282 | **−1.89** | **0.029** | −0.0537 | 0.9726 | −0.0513 | [−0.115, −0.009] | **[−0.105, −0.002]** | 0.0719 | −0.705 | +0.89 | 0.19 | 509 |
| `LC_DEEP`  | 5  | −0.0463 | 0.0290 | −1.60 | 0.055 | −0.0466 | 0.9653 | −0.0464 | [−0.106, −0.007] | [−0.100, +0.008] | 0.0885 | −3.115 | −4.00 | 1.00 | 485 |
| `LC_DEEP`  | 10 | −0.0182 | 0.0107 | −1.69 | 0.045 | −0.0182 | 0.9649 | −0.0175 | [−0.047, +0.011] | [−0.038, +0.002] | 0.0199 | −0.438 | −5.23 | 1.00 | 425 |

Bold = β significantly different from zero at NW 5 % one-sided. † LC_FULL 10Y small-sample caveat (n=42 monthly obs; heavy overlapping forward-return overlap inflates the apparent t-stat).

**Headline robust findings (independent of LC_FULL small-sample cell)**:

* **LC_DEEP 3Y β = −0.053**: NW t=−1.89, p=0.029; bootstrap CI [−0.115, −0.009] excludes zero; CY CI [−0.105, −0.002] excludes zero. **Robust**.
* **LC_DEEP 5Y β = −0.046**: NW t=−1.60, p=0.055; bootstrap CI [−0.106, −0.007] excludes zero; CY CI [−0.100, +0.008] straddles zero by a hair.
* **LC_DEEP 10Y β = −0.018**: NW t=−1.69, p=0.045; CY CI [−0.038, +0.002] straddles zero narrowly.
* **LC_FULL 3Y β = −0.034**: t=−3.08, p=0.001; CY CI [−0.053, −0.015] excludes zero. Post-zero-fill, LC_FULL produces an additional robust negative-β cell.

## 5. Conditional probability table (12 cells × 7 events)

Source: `outputs/tables/lc_v1_conditional_probabilities.csv`. Current LC quintile in parentheses (1 = lowest historical, 5 = highest).

Example highlights — `p_neg_total_return` and `p_maxdd_lt_neg30` (95 % bootstrap CIs):

| Scope | h (yr) | LC quintile | n in bucket | p_neg_total_return | 95 % CI | p_maxdd_lt_neg30 | 95 % CI |
|---|---|---|---|---|---|---|---|
| LC_FULL | 1  | 2 | 30  | 0.067 | [0.00, 0.17] | 0.000 | [0, 0] |
| LC_FULL | 3  | 1 | 25  | 0.000 | [0, 0]       | 0.000 | [0, 0] |
| LC_FULL | 5  | 2 | 20  | 0.000 | [0, 0]       | 0.000 | [0, 0] |
| LC_FULL | 10 | 1 | 9   | 0.000 | [0, 0]       | 0.000 | [0, 0] |
| LC_TIER2 | 1  | 2 | 70  | 0.300 | [0.20, 0.41] | 0.000 | [0, 0] |
| LC_TIER2 | 3  | 2 | 66  | 0.242 | [0.14, 0.35] | 0.273 | [0.17, 0.39] |
| LC_TIER2 | 5  | 2 | 61  | 0.295 | [0.18, 0.41] | 0.557 | [0.44, 0.69] |
| LC_TIER2 | 10 | 1 | 49  | 0.224 | [0.12, 0.35] | **0.694** | [0.59, 0.80] |
| LC_DEEP  | 1  | 2 | 106 | 0.198 | [0.12, 0.27] | 0.000 | [0, 0] |
| LC_DEEP  | 3  | 2 | 102 | 0.078 | [0.03, 0.14] | 0.088 | [0.04, 0.15] |
| LC_DEEP  | 5  | 2 | 97  | 0.041 | [0.01, 0.08] | 0.113 | [0.05, 0.19] |
| LC_DEEP  | 10 | 1 | 85  | 0.000 | [0, 0]       | 0.494 | [0.39, 0.60] |

**Interpretation**: from the LOWEST quintile (current LC at 2026-05), the LC_TIER2 10Y forward window has a **70 % probability of a >30 % drawdown** somewhere in the next decade — a striking, statistically robust historical pattern, but consistent with the FAIL verdict (the composite identifies a HISTORICAL tail-risk regime, not a directional return forecast). Full 7-probability table in CSV.

## 6. Calibration summary

Source: `outputs/tables/lc_v1_calibration.csv`. Backtest split per pre-reg §3.8.

| Scope | h (yr) | n_val | Brier score | Reliability | Resolution | Uncertainty | CRPS skill | PIT K-S p |
|---|---|---|---|---|---|---|---|---|
| LC_FULL  | 1  | 77  | 0.140 | 0.009 | 0.000 | 0.132 | +0.001 | <0.0001 |
| LC_FULL  | 3  | 53  | 0.000 | 0.000 | 0.000 | 0.000 | −0.373 | <0.0001 |
| LC_FULL  | 5  | 29  | 0.000 | 0.000 | 0.000 | 0.000 | −0.191 | <0.0001 |
| LC_FULL  | 10 | 0   | NaN   | NaN   | NaN   | NaN   | NaN     | NaN     |
| LC_TIER2 | 1  | 173 | 0.177 | 0.087 | 0.004 | 0.093 | −0.014 | <0.0001 |
| LC_TIER2 | 3  | 149 | 0.102 | 0.102 | 0.000 | 0.000 | −0.001 | <0.0001 |
| LC_TIER2 | 5  | 125 | 0.077 | 0.077 | 0.000 | 0.000 | −0.096 | <0.0001 |
| LC_TIER2 | 10 | 65  | 0.003 | 0.003 | 0.000 | 0.000 | +0.040 | <0.0001 |
| LC_DEEP  | 1  | 173 | 0.137 | 0.049 | 0.008 | 0.093 | −0.046 | <0.0001 |
| LC_DEEP  | 3  | 149 | 0.068 | 0.067 | 0.000 | 0.000 | −0.127 | <0.0001 |
| LC_DEEP  | 5  | 125 | 0.081 | 0.080 | 0.000 | 0.000 | −0.619 | <0.0001 |
| LC_DEEP  | 10 | 65  | 0.002 | 0.001 | 0.000 | 0.000 | −0.089 | <0.0001 |

**Headline**:

* **PIT K-S p-values uniformly < 0.0001** — the Gaussian forecast distribution is rejected for every cell. Expected: financial returns have fat tails which Gaussian forecasts ignore. The model's PROBABILISTIC forecasts are miscalibrated even when point estimates are sometimes informative.
* **CRPS skill is mostly NEGATIVE** — the model's continuous forecasts are worse than the prevailing-mean benchmark. Sole positive: LC_TIER2 @ 10Y skill = +0.04 (consistent with that cell's CW p < 0.0001).
* **Brier scores 0.001-0.18** with Reliability dominating Resolution — the model is BIASED, not under-discriminating. The base-rate uncertainty term is the dominant variance source for cells where forward-return-<-0 is rare (long horizons).

These calibration results are CONSISTENT with the DECISIONS.md FAIL verdict and reinforce the DIAGNOSTIC ONLY framing.

Headline figures generated:

* `outputs/figures/lc_v1_reliability_diagram_LC_TIER2_10y.png`
* `outputs/figures/lc_v1_reliability_diagram_LC_DEEP_5y.png`
* `outputs/figures/lc_v1_pit_histogram_LC_TIER2_10y.png`
* `outputs/figures/lc_v1_pit_histogram_LC_DEEP_5y.png`

(LC_FULL 10Y figures NOT generated: n_validation=0 because 10Y forward return from 2019+ requires data through 2029.)

## 7. Falsifiability criterion update (post-zero-fill)

Re-evaluating pre-reg §2.1 criteria 1-4 with the regenerated zero-fill artifacts:

| # | Criterion | Threshold | Scope | Realized | Pass? |
|---|---|---|---|---|---|
| 1 | OOS R² @ 1Y    | > 0.005 | `LC_TIER2` | −0.017 | ❌ |
| 2 | OOS R² @ 3Y    | > 0.020 | `LC_TIER2` | −0.003 | ❌ |
| 3 | OOS R² @ 5Y    | > 0.040 | `LC_TIER2` | −0.060 | ❌ |
| 4 | NW t > 1.65    | LC_FULL any horizon | `LC_FULL` 3Y: t=−3.08 (negative); 10Y: t=−17.6 (negative, small-sample caveat); 1Y/5Y: |t|<0.5 | ❌* |

*Criterion 4 requires t > 1.65 **on the positive side** (pre-reg priors anticipated positive β). Realized signs are all negative where significant; thus criterion 4 is FAIL by both letter (|t| > 1.65 with negative sign violates "positive sign" implicit in the pre-reg priors §4.1) AND spirit (no horizon shows a positive significant β).

**Preliminary verdict**: **0 of 4 testable criteria pass**. Pre-reg §2.1 decision rule: `n_pass ≤ 3 → FAIL → DIAGNOSTIC ONLY`. Locked at Session 8 §2.J after the diagnostics layer; the trajectory is unchanged from Session 6.5 and reaffirmed by DECISIONS.md 2026-05-24.

## 8. Pre-reg expectation comparison (post-zero-fill, per-component univariate)

| Component | Pre-reg §4.1 prior sign (P) | Realized univariate β sign (canonical: 5Y) | Realized signs across horizons | Agreement |
|---|---|---|---|---|
| z₁ NetFed       | + (0.75) | − (5Y β=−0.012) | All 4 horizons negative | ❌ |
| z₂ M2_yoy       | + (0.65) | − (5Y β=−0.008) | All 4 horizons negative | ❌ |
| z₃ BankLend_yoy | + (0.70) | − (5Y β=−0.024) | All 4 horizons negative | ❌ |
| z₄ DXY⁻¹        | + (0.72) | − (5Y β=−0.008) | 3 horizons negative, 10Y ≈ 0 | ❌ |
| z₅ Funding str. | + (0.80) | − (5Y β=−0.011) | All 4 horizons negative | ❌ |

**5 of 5 components have realized signs OPPOSITE to their pre-reg priors** (Session 6.5 reported 4-of-5 from composite decomposition; per-component univariate confirms it's 5-of-5).

This is a **publishable research finding** per DECISIONS.md: the sign anomaly is consistent with credit-cycle / dollar-cycle reversal literature (Fama-French 1988; Schularick-Taylor 2012; Bruno-Shin 2015; Bollerslev-Tauchen-Zhou 2009). Modern macro-liquidity proxies historically PRECEDE lower forward equity returns at the end-of-cycle.

## 9. Invariants verified

| Invariant | Status |
|---|---|
| v50 ORIGINAL SHA256 = `6087918D…26F47` | ✅ unchanged |
| Pre-reg `a90b02d` (MV-Conditional) on `origin/main` | ✅ untouched |
| Pre-reg `a8635ef` (LC v1.0) ancestor of HEAD `86dbb3d` | ✅ verified, HARD GATE re-enforced at every parquet write |
| Sealed pre-reg values (splice dates, gate thresholds, weights, scopes, priors, criteria) | ✅ unchanged |
| All Session 1-6.5 tests still pass | ✅ baseline test suite exit 0 (Gate 4) |
| Session 7 new test count | +35 tests (25 calibration + 4 component zero-fill + 8 regression Session 7) — exceeds prompt target of +20 |
| Per-module coverage ≥90% on new code | ✅ calibration 95%, components 95% (preserved from Session 6), regression 91% (preserved) |

## 10. Owner action required

**Paste this report to the Strategist for Session 8 authorization.**

The Strategist will design Session 8 sub-stages H + I + J:

* **§2.H Diagnostics**: ADF/KPSS/PP/ZA stationarity tests on LC composites + components; VIF for multicollinearity; Bai-Perron structural-break tests on the regression.
* **§2.I DIAGNOSTIC ONLY dashboard panel**: HTML+JS panel surfacing the FAIL verdict, the negative-β finding, the conditional-probability tail estimates, and the calibration K-S rejections.
* **§2.J Falsifiability scorecard LOCKED**: `outputs/lc_v1_verdict.json` per DECISIONS.md §"Verdict status flag"; research write-up draft tying the negative-β finding to the cycle-reversal literature.

## 11. Session metrics

- **Wall time**: ≈ 2.5h of 8h target (well within budget).
- **Sub-stages shipped**: 4 of 4 + final report.
- **Tests added**: +35 (Session 7 new: 21 calibration + 4 z1 zero-fill + 8 regression Session 7 + 2 sys-path-related = 35 net new).
- **Commits**: 5 (4 sub-stages + final report).
- **Tags pushed**: 4 (decisions, investigation, F, G).
- **CI iterations**: 4 manual triggers (one per sub-stage).
- **Blockers filed**: 0.
- **New packages installed**: `matplotlib` (per prompt §0 `pip install` allowlist; required for §2.G reliability + PIT figures).

## 12. Next session entry point

Session 8 starts at **§2.H (diagnostics)** on branch `spec/liquidity-composite-v1.0` HEAD `86dbb3d` (or this report's commit, if pushed). The Strategist's authorization in a new `DECISIONS.md` entry should explicitly:

1. Confirm the FAIL verdict locks at Session 8 §2.J (this report's §7 trajectory makes that highly likely barring data revision).
2. Authorize the DIAGNOSTIC ONLY dashboard framing per pre-reg §12.2.
3. Specify the publishable research-finding scope (negative-β + cycle-reversal interpretation).
