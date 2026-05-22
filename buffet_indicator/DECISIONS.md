# DECISIONS.md — Strategist arbitration log

This file records Strategist (Claude AI) arbitration decisions on the LC v1.0
sprint. Each entry is dated and traceable to the session that surfaced the
question. Per master spec §0.5.4, the Strategist has final merge decision
authority; this file records the reasoning so reviewers can audit.

---

## 2026-05-24 — Session 6.5 results arbitration (post-regression)

### Context

Session 6.5 delivered the 12-cell predictive regression table in
`outputs/tables/lc_v1_predictive_regression.csv`. Three open questions
surfaced for Strategist arbitration before Session 7 sub-stages F-J proceed.
Full session report: `SESSION_6_5_FINAL_REPORT.md` (committed `6c0ad3d`).

### Headline finding

Falsifiability scorecard (per pre-reg `a8635ef` §2.1, testable criteria 1-4):

- Criterion 1 (OOS R² @ 1Y > 0.005 on LC_TIER2): realized -0.0167. **FAIL**.
- Criterion 2 (OOS R² @ 3Y > 0.020 on LC_TIER2): realized -0.0028. **FAIL**.
- Criterion 3 (OOS R² @ 5Y > 0.040 on LC_TIER2): realized -0.0602. **FAIL**.
- Criterion 4 (NW t > 1.65 on LC_FULL, any horizon): LC_FULL truncated to
  n=31 due to RRPONTSYD post-2013 start; not evaluable as specified. **FAIL**.

`n_pass = 0` of 4 testable criteria. Per pre-reg §2.1 decision rule
(`n_pass ≤ 3 → FAIL → DIAGNOSTIC ONLY view`) and §12.2, **the LC v1.0 verdict
is FAIL** with confidence floor 95% (the criterion thresholds are sealed in
the pre-reg and the realized values are well below threshold).

Per pre-reg §0.3, this verdict is binding. The model still runs end-to-end;
the dashboard panel will frame LC v1.0 as DIAGNOSTIC ONLY (no actionable
conviction/probability headline). Two findings remain publishable in the
research write-up:

1. **LC_DEEP β NEGATIVE robust at 3Y (NW t=-1.89, p=0.029, bootstrap CI
   excludes zero) and 5Y (NW t=-1.60, p=0.055, bootstrap CI excludes zero)
   on 45-year sample**. Interpretable via credit-cycle / dollar-cycle
   reversal literature (Fama-French 1988; Schularick-Taylor 2012;
   Bruno-Shin 2015; Bollerslev-Tauchen-Zhou 2009). NOT consistent with
   pre-reg §4.1 priors which expected positive signs based on simple
   "loose money → returns" intuition.
2. **Sign anomaly across 4 of 5 components (z₂, z₃, z₄, z₁; z₅ inconclusive)**.
   This is NOT a model bug — it reflects pre-reg priors calibrated to the
   wrong literature stream (1970s-90s monetarist vs modern mean-reversion).

### Question 1 — RRPONTSYD treatment

**Question**: LC_FULL realized active-from 2023-09 instead of pre-reg's
sealed 2003-01, because RRPONTSYD data is sparse pre-2013-09-23 (>50%
missing per Session 6.5 §A) and propagates through the 120-mo PIT z warm-up.
Should we (a) accept truncation, (b) zero-fill pre-2013-09-23, or (c) amend
pre-reg z₁?

**Strategist decision**: **(b) zero-fill pre-2013-09-23**.

**Rationale**:
- The ON RRP facility existed pre-2013 but had near-zero balances most days
  (Fed wasn't running RRPs aggressively). Zero is the closest approximation
  to economic truth, not synthetic data injection.
- Pre-reg §1.2 sealed LC_FULL active-from at 2003-01. Accepting truncation
  contradicts the sealed scope.
- Pre-reg §1.1 lists RRPONTSYD as a z₁ component with no caveat about
  handling its sparse history. Per master spec §C.1, ambiguity in
  implementation parameters can be clarified by Strategist without amending
  sealed values.
- (c) requires formal amendment per master spec §6.1 — unnecessary given
  (b) is consistent with pre-reg's sealed active-from.

**Note about Claude Code Session 6.5 claim**: the Session 6.5 report
references "pre-reg row z1 NOTE: 'zero-fill pre-2013-09-23'". The Strategist
has not located this string in the SEALED pre-reg file (`a8635ef`'s
`specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md`). Session 7 sub-stage §2.1
includes an explicit verification step. If the string does NOT appear in
the sealed file, the decision above is the Strategist's interpretive call,
not a literal pre-reg clause. Either way, the decision stands per the
rationale above.

**Implementation directive**: extend `compute_z1_netfed` to zero-fill
RRPONTSYD pre-2013-09-23 with the choice documented inline in the
component's docstring. Maintain the un-filled variant under a kwarg
`rrpontsyd_pre2013_treatment: Literal["zero_fill", "truncate"] = "zero_fill"`
for robustness checks. The canonical artifact uses `"zero_fill"`. Session 7
also produces a robustness companion CSV with `"truncate"` outputs.

### Question 2 — 4-of-5 negative-sign anomaly

**Question**: investigate sign anomaly before proceeding, or proceed with
bootstrap CIs / diagnostics?

**Strategist decision**: **proceed with bootstrap CIs / diagnostics, AND
add a focused investigation sub-stage in Session 7 §2.1 to verify the
finding is methodologically clean (not a sign-flip bug in component
computation, splice direction, or composite weighting).**

**Rationale**:
- LC_DEEP at 3Y/5Y has bootstrap CIs that EXCLUDE ZERO on 45-year sample.
  This is statistically robust — unlikely to vanish under full 50K bootstrap.
- The interpretation via credit-cycle / dollar-cycle reversal literature is
  ECONOMICALLY coherent. Not a "garbage in / garbage out" result.
- Investigation must rule out: (i) sign error in z₄ DXY⁻¹ negation; (ii)
  sign error in z₅ funding-stress weight (-0.15 vs +0.15); (iii) sign error
  in BankLend YoY splice c-term; (iv) SPX TR splice direction at 1988-01-04.
- If all four checks PASS, the negative sign is a genuine finding. If any
  FAIL, the result must be recomputed.

### Question 3 — 3 methodology adjustments from Session 6.5

Claude Code shipped three adjustments during Session 6.5; all preserve
sealed pre-reg values and adjust only implementation parameters that
pre-reg does not constrain.

**Adjustment A**: RRPONTSYD `observation_start = 2013-09-23` in MoDH master.
**Strategist decision**: **ACCEPT**. Data engineering choice. Pre-reg
silent on observation_start. The zero-fill (Q1 decision) operates downstream
in `compute_z1_netfed` and does not require changing the master.

**Adjustment B**: BUSLOANS → TOTLL overlap window 12mo → 36mo for c-term
estimation.
**Strategist decision**: **ACCEPT**. Pre-reg §1.3 row 1 seals date (1973-01-03),
space (YoY), method (additive c), gates (corr > 0.50, |c| < 0.05). It does
NOT specify the overlap window. ±12mo is empirically impossible because
TOTLL_yoy is first defined at 1974-01-31, strictly outside that window.
±36mo gives 24 obs spanning 1974-1976 → corr=0.965, c=+0.025 (both within
sealed gates). The window expansion is forced by data availability, not
chosen to manipulate gate outcomes.

**Adjustment C**: TED → SOFR-IORB max|Δz| gate scope: full series → blend
window (2022-02 minus 1mo, 2023-04 plus 1mo).
**Strategist decision**: **ACCEPT** (already pre-approved live during
Session 6.5 §2.3). Pre-reg §1.3 row 4 specifies the gate threshold (1.5σ)
but is silent on scope. Master spec §2.4.5 Step 4 defines splice gates as
detecting splice-induced discontinuities. The 2008 Lehman shock |Δz|=4.88 is
a genuine funding-stress signal, NOT a splice artifact (splice happens 14
years later in 2022-02). Restricting scope preserves the gate's semantic
purpose without violating the sealed threshold.

### Authorization for Session 7

The Strategist authorizes Claude Code to proceed with Session 7 sub-stages:
- §2.0 (commit this DECISIONS.md verbatim).
- §2.1 (investigation: verify pre-reg claims, implement zero-fill,
  regenerate canonical artifacts, run per-component regressions, run 4
  sign-check sensitivity tests).
- §2.F (full bootstrap CIs at 50K reps for all 12 regression cells +
  conditional probability tail outputs per master spec §5.3 + full
  Campbell-Yogo (2006) implementation replacing the Session 6 stub).
- §2.G (calibration: Brier + Murphy 1973 decomposition + reliability
  diagram + PIT histogram + CRPS).

Session 8 will cover §2.H (diagnostics: ADF/KPSS/PP/ZA stationarity tests
+ VIF + Bai-Perron breaks), §2.I (DIAGNOSTIC ONLY dashboard panel), §2.J
(falsifiability scorecard locked + research write-up draft).

### Verdict status flag (for downstream consumers)

`outputs/lc_v1_verdict.json` should contain:

    {
      "verdict": "FAIL",
      "n_pass_testable_criteria": 0,
      "n_total_testable_criteria": 4,
      "decision_rule_applied": "pre_reg_a8635ef_section_2_1",
      "display_framing": "DIAGNOSTIC_ONLY",
      "research_findings_publishable": [
        "lc_deep_negative_beta_3y_5y_robust",
        "sign_anomaly_consistent_with_mean_reversion_literature"
      ],
      "locked_after_session": 8,
      "interim_locked_after_session": 7
    }

Session 7 §2.J ships this file. Until then, the verdict is preliminary
but the decision rule is locked.

---

## End of 2026-05-24 entry

Future Strategist arbitration entries append below this line.

---

## 2026-05-25 — Session 7 results arbitration (post-zero-fill / post-calibration)

### Context

Session 7 (commit `dab754b`) delivered:
- Zero-fill RRPONTSYD restoration of LC_FULL (n=31 → n=160).
- 4-of-4 sign-check sensitivity tests PASS — composite construction methodologically clean.
- Per-component univariate regressions: **5 of 5 components NEGATIVE β at all horizons** (z₄ at 10Y ≈ 0). Sign anomaly is COMPONENT-LEVEL, not composite-construction artifact.
- Full Campbell-Yogo (2006) implementation replacing Session 6 stub. CY CIs populated for LC_FULL and LC_DEEP cells where ρ_X > 0.95.
- 50K stationary bootstrap reps + conditional probability tail outputs (12 cells × 7 probabilities).
- Calibration layer (Brier + Murphy + reliability + PIT + CRPS).

Three new findings surfaced that require Strategist arbitration before Session 8 proceeds.

### Question 4 — LC_FULL @ 10Y insufficient sample

**Finding**: LC_FULL @ 10Y has `n_obs_insample = 42` (per Session 7 build log). Newey-West HAC with lag = 119 cannot stabilize SE when sample size ≈ HAC lag. The reported t_NW = −17.62 and R²_OOS = +0.704 are statistical artifacts of the small-sample / overlapping-returns / horizon-equal-to-sample-length problem (Hansen-Hodrick 1980; Britten-Jones-Neuberger-Nolte 2011 "Improved inference in regression with overlapping observations").

**Strategist decision**: **flag as "insufficient sample" in the scorecard**. The cell remains in `outputs/tables/lc_v1_predictive_regression.csv` for transparency but:
- Dashboard panel displays a warning badge on the cell.
- Research write-up explicitly excludes the cell from headline conclusions.
- Falsifiability criterion 4 evaluation: LC_FULL @ 3Y (n=126, t=-3.08, p=0.001) is the credible cell satisfying t > 1.65. The 10Y cell is REPORTED but NOT counted.

**Threshold for "insufficient sample"**: any cell with `n_obs_insample < 5 × HAC_lag` is flagged. For 10Y: lag=119 → threshold n<595, so 10Y cells with n=42 (LC_FULL), n=425 (LC_DEEP) are flagged; n=245 (LC_TIER2) is below threshold but the cell sits at n_obs/HAC_lag = 2.1× which is borderline — flag with softer warning.

### Question 5 — Universal calibration failure

**Finding**: PIT Kolmogorov-Smirnov p-values < 0.0001 across all 12 cells. PIT histograms show right-skew (clustering at 0.8–1.0) — Gaussian forecast distribution chronically UNDER-PREDICTS realized values. Reliability diagrams show observed event frequencies far below diagonal — model probabilities of "high prob of negative return" are NOT matched by realized event frequencies. CRPS skill mostly NEGATIVE (prevailing-mean benchmark beats model).

**Strategist decision**: **probability outputs are MISCALIBRATED and must be flagged as such in the dashboard**. Specifically:
- Dashboard panel includes a prominent **"⚠ Probability outputs are MISCALIBRATED — do not use for decisions"** disclosure card directly above any conditional probability display.
- The conditional probability table is shown for transparency, but with a faded / lower-contrast styling indicating it is research material, not actionable.
- Research write-up frames calibration failure as a methodological finding (see Q6).

**Underlying interpretation**: the Gaussian assumption used in the conditional probability framework (forecast mean from regression + forecast SD from regression residuals) fails against fat-tailed empirical equity returns. This is a well-documented limitation of conditional-Gaussian forecast distributions for equity returns (Mandelbrot 1963; Fama 1965; Cont 2001 "Empirical properties of asset returns: stylized facts and statistical issues"). Session 8 does NOT attempt to fix this — the fat-tailed alternative (skewed-t, mixture model, kernel density) was specified per master spec §5.1b but is out of scope for this v11.3 sprint. v11.4 or v12.0 would address.

### Question 6 — Add calibration failure as publishable finding

**Strategist decision**: **YES**. The research write-up §2.J now includes three publishable findings:

1. **LC_DEEP β NEGATIVE robust** at 3Y (t=-1.89, p=0.029, CY CI [-0.105, -0.002] excludes zero) on 45-year sample. LC_FULL @ 3Y also negative (t=-3.08, CY CI [-0.053, -0.015]). Interpretable via credit-cycle / dollar-cycle reversal literature (Fama-French 1988; Schularick-Taylor 2012; Bruno-Shin 2015; Adrian-Boyarchenko 2012).
2. **5-of-5 component-level negative β anomaly** at all horizons. Pre-reg priors expected POSITIVE on all components based on simple "loose money → returns" intuition. Realized signs uniformly NEGATIVE. Interpretable via the same mean-reversion / over-extension literature. This is a methodological lesson about prior calibration for macro-financial composites.
3. **Universal calibration failure of Gaussian conditional forecast distribution** vs fat-tailed empirical returns (PIT K-S p<0.0001, CRPS skill mostly negative). Even methodologically-clean predictive composites built on multiple-decade samples fail distributional calibration when the assumed conditional distribution is misspecified. This is a methodological lesson about probability framework choice.

### Re-evaluation of falsifiability criteria 1-4 (with Session 7 zero-fill artifacts)

| # | Criterion | Threshold | Realized | Pass? |
|---|---|---|---|---|
| 1 | OOS R² @ 1Y > 0.005 on LC_TIER2 | 0.005 | −0.0167 | ❌ FAIL |
| 2 | OOS R² @ 3Y > 0.020 on LC_TIER2 | 0.020 | −0.0028 | ❌ FAIL |
| 3 | OOS R² @ 5Y > 0.040 on LC_TIER2 | 0.040 | −0.0602 | ❌ FAIL |
| 4 | NW t > 1.65 on LC_FULL, any horizon | 1.65 | 3Y: t=-3.08 ✅; 5Y: 0.39 ❌; 10Y: -17.62 ⚠ (flagged insufficient sample). **Net**: PASS on 3Y strict reading. | ✅ PASS (strict) |

**Strict-reading n_pass = 1 of 4** (criterion 4 passes on |t| magnitude; criteria 1-3 fail).
**Spirit-reading n_pass = 0 of 4** (criterion 4 sign violates pre-reg §4.1 priors).

**Strategist arbitration**: per master spec §0.3 ("pre-reg discipline is binding") and the criterion text in `a8635ef` §2.1 which specifies "**Positive with Newey-West HAC t > 1.65**", the SIGN requirement is in the criterion text itself. Realized sign is NEGATIVE → criterion 4 **FAILS** on textual reading as well.

**Final n_pass = 0 of 4 testable criteria** → per pre-reg §2.1 decision rule (`n_pass ≤ 3 → FAIL`), **the LC v1.0 verdict is FAIL** with confidence floor 99%. Per pre-reg §12.2, display framing is DIAGNOSTIC ONLY.

This locks at Session 8 §2.J via `outputs/lc_v1_verdict.json`.

### Authorization for Session 8

The Strategist authorizes Claude Code to proceed with Session 8 sub-stages:
- §2.0 (commit this DECISIONS.md addendum verbatim).
- §2.H (diagnostics: ADF + KPSS + PP + Zivot-Andrews on 5 components + 3 composites; VIF on cross-correlation matrix; Bai-Perron breaks on each composite).
- §2.I (DIAGNOSTIC ONLY dashboard panel: integrated LC v1.0 tab in `outputs/dashboard.html`, with calibration-failure disclosure card, falsifiability scorecard table, 12-cell regression display, per-component regression display, three publishable findings narrative).
- §2.J (final falsifiability scorecard locked; `outputs/lc_v1_verdict.json` written; `outputs/reports/lc_v1_research_writeup.md` academic-style draft; sprint closeout tag `v11.3.0`).

### Future-version pre-reg amendments to consider (NOT for v11.3)

For the eventual LC v2.0 spec, the following modifications should be considered (DO NOT apply to v11.3):
- Pre-reg §4.1 priors need re-anchoring. Both literature streams (1970s-90s monetarist vs 2008+ mean-reversion) should be represented with separate prior probabilities.
- Criterion 4 wording needs disambiguation: "positive t" or "any |t|" must be explicit.
- The conditional probability framework should default to non-Gaussian distributions (skewed-t per Hansen 1994 or empirical kernel) given the calibration failure documented here.
- Insufficient-sample threshold (`n < 5 × HAC_lag`) should be an explicit pre-reg gate, not a post-hoc filter.

These notes are for the v11.4+ Strategist — not actionable in v11.3.

---

## End of 2026-05-25 entry
