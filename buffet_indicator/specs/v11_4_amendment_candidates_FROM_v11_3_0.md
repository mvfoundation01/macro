<!--
AMENDMENTS FILE PROVENANCE
==========================
created_at_seal_time_utc: 2026-05-24T13:03:39Z
branch_chosen: A
themes_detected_in_candidate: 4 of 4
candidate_source_path: buffet_indicator\_amendments.md
candidate_source_sha256: e7e6f10934ea308339b2fdb69e60652324640856f13ab29751025b2850f8ebcb
strategist_fallback_used_for_missing_themes: False
seal_resume_directive: PROMPT_CC_v11_4_seal_RESUME_FULL.md
-->

# v11.4 Amendment Candidates â€” extracted from v11.3.0 verdict.json

> **Source**: `outputs/lc_v1_verdict.json` on branch `spec/liquidity-composite-v1.0`
> (commit `d56174c`, tag `v11.3.0`, verdict_locked_at 2026-05-25T00:00:00Z).
>
> **Purpose**: Strategist reference material for drafting the v2.0 pre-registration.
> This file is RECORD-ONLY â€” it copies the four amendment candidates from v1.0's
> verdict.json into a standalone markdown document, with context on why each
> was identified during the v11.3.0 LC v1.0 sprint.
>
> **Does NOT constitute a sealed v2.0 pre-reg.** The actual sealed pre-reg lives
> in `MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` (currently `.TEMPLATE`, awaiting
> Strategist).

---

## Amendment 1 â€” Pre-reg Â§4.1 priors: both monetarist and mean-reversion streams

> *Verbatim from verdict.json `v11_4_amendment_candidates[0]`*:
>
> > Pre-reg Â§4.1 priors to incorporate both monetarist and mean-reversion literature streams with separate prior probabilities for each component sign

**v11.3.0 context**:

LC v1.0's pre-registration Â§4.1 priors were calibrated on simple 1970sâ€“90s
monetarist intuition ("loose money â†’ returns"), assigning positive prior
probability to all 5 component betas.

The realized 45-year multi-horizon regression showed the opposite:

- 5-of-5 components have NEGATIVE Î² at 3Y and 5Y horizons (`zâ‚„ DXY-inv near
  zero at 10Y but still negative; zâ‚, zâ‚‚, zâ‚ƒ, zâ‚… all clearly negative`)
- LC_DEEP Î² is robust-negative at 3Y (NW t = âˆ’1.89, p = 0.029; 50K-bootstrap
  CI excludes zero) and 5Y (NW t = âˆ’1.60, p = 0.055; CI excludes zero)

This is consistent with credit-cycle / dollar-cycle reversal literature
(Fama-French 1988; Schularick-Taylor 2012; Bruno-Shin 2015; Bollerslev-
Tauchen-Zhou 2009; Adrian-Boyarchenko 2012). Modern macro-liquidity proxies
historically PRECEDE lower forward equity returns at end-of-cycle â€”
mean-reversion-on-prior-overextension, not loose-money-spurs-returns.

**v2.0 design implication**: v2.0 priors must give meaningful probability to
*both* sign hypotheses per component (or per composite scope), and the
pre-reg should state which literature stream is which. A symmetric
0.5 / 0.5 prior per component is the minimum defensible default; better is
component-by-component calibration based on which sample window the
component spans (post-1970 monetarist sub-sample vs. post-2000 modern-
liquidity sub-sample).

---

## Amendment 2 â€” Criterion 4 sign-vs-magnitude disambiguation

> *Verbatim from verdict.json `v11_4_amendment_candidates[1]`*:
>
> > Criterion 4 wording to disambiguate sign vs magnitude requirement explicitly

**v11.3.0 context**:

LC v1.0 Â§2.1 Criterion 4 read: "LC_FULL NW t > 1.65 (POSITIVE) any horizon".
The empirical result was: best LC_FULL 3Y horizon shows Î² = âˆ’0.034, t = âˆ’3.08
(|t| = 3.08, well above the 1.65 magnitude threshold) â€” but the sign is
NEGATIVE, opposite to the pre-registered positive direction.

The decision rule treated this as FAIL (since the criterion required Î² > 0),
but the wording could be read either way and consumed Strategist arbitration
cycles in Sessions 6.5 and 7.

**v2.0 design implication**: each criterion should explicitly state whether
it's a sign criterion (Î² > 0 or Î² < 0 specifically) OR a magnitude criterion
(|Î²| > X regardless of sign) OR a joint criterion (Î² > 0 AND |t| > 1.65). No
implicit conjunctions.

---

## Amendment 3 â€” Non-Gaussian conditional forecast distribution

> *Verbatim from verdict.json `v11_4_amendment_candidates[2]`*:
>
> > Conditional probability framework to default to skewed-t (Hansen 1994) or empirical kernel distributions (non-Gaussian) given universal calibration failure documented here

**v11.3.0 context**:

LC v1.0's pre-reg Â§3 specified Gaussian conditional forecast distributions
(per simple regression mean + RMSE). Session 7 calibration testing (Brier,
Murphy decomposition, CRPS, log-score, PIT, reliability diagrams) showed:

- PIT K-S test rejects null of Uniform(0,1) at p < 0.0001 in **all 12 cells**
  (3 composites Ã— 4 horizons)
- CRPS skill score is mostly negative (i.e. the prevailing-mean benchmark
  beats the conditional-Gaussian forecast)

This is the well-documented failure of conditional-Gaussian assumption for
equity returns (Mandelbrot 1963; Fama 1965; Cont 2001 â€” fat tails, skew,
volatility clustering).

**v2.0 design implication**: default to skewed-t (Hansen 1994, 4-parameter:
location, scale, skewness Î·, df Î½) OR empirical-kernel distribution. Either
choice should be made in the pre-reg; the chosen family's parameters become
part of the pre-reg invariant.

---

## Amendment 4 â€” Insufficient-sample gate as explicit pre-reg condition

> *Verbatim from verdict.json `v11_4_amendment_candidates[3]`*:
>
> > Insufficient-sample gate (n_obs_insample < 5 * HAC_lag) to be an explicit pre-reg condition rather than a post-hoc filter

**v11.3.0 context**:

LC v1.0 Criterion 4 evaluated LC_FULL at all 4 horizons. The LC_FULL OOS
sample for 10Y horizon had `n_obs = 31` after RRPONTSYD truncation to
post-2013-09-23 (per DECISIONS.md 2026-05-24 Q1). HAC lag for 10Y forward
returns is conventionally floor(1.5 Ã— 120) = 180 months â€” far exceeding the
`5 Ã— HAC_lag = 900-month minimum n_obs` rule of thumb. Session 7's
arbitration noted "n_obs < 5 Ã— HAC_lag â†’ criterion not evaluable as
specified", and the cell was marked FAIL by convention (no positive
evidence) â€” but this filter was applied **post-hoc**, not pre-registered.

**v2.0 design implication**: list the insufficient-sample gate `n_obs <
5 Ã— HAC_lag` (or analogous bias-correction adequacy rule) in the pre-reg's
Â§3 methodological-choices section, so future low-n cells are decided
ex-ante rather than re-litigated each sprint.

---

## Cross-reference â€” full v11.3.0 closeout context

- `LC_V1_SPRINT_CLOSEOUT_REPORT.md` (on `spec/liquidity-composite-v1.0`) â€” Â§7 amendment summary
- `outputs/lc_v1_verdict.json` (on `spec/liquidity-composite-v1.0`) â€” locked scorecard + amendments array (canonical source for this file)
- `DECISIONS.md` (on `spec/liquidity-composite-v1.0`) â€” 2026-05-24 + 2026-05-25 arbitration entries
- `outputs/reports/lc_v1_research_writeup.md` (on `spec/liquidity-composite-v1.0`) â€” full research narrative behind the 3 publishable findings

The Strategist's v2.0 pre-reg should also incorporate any additional
methodological lessons from `SESSION_6_5_FINAL_REPORT.md` and Sessions 7/8
investigation entries on the spec branch.
