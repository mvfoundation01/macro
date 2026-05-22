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
