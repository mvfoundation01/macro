# MV_CONDITIONAL_RULE_PREREGISTER.md

> Pre-registration for MV-Conditional V2 backtest, per master spec §0.5
> ("Pre-registration policy for all tactical rules"). This file is committed
> via git BEFORE any V2 backtest is executed. Git commit timestamp is the
> formal pre-registration timestamp.

## 1. Hypothesis

H₀: Combining V1 Combination strategy with a regime-based de-risking rule
based on MVCI z-score and MRC z-score does NOT improve risk-adjusted
returns over plain V1 Combination on the OOS holdout sample.

H₁ (alternative): The MV-Conditional rule R-PRIMARY (defined below) DOES
improve risk-adjusted returns by either:
  (a) Sharpe ratio improvement of ≥ +0.05 (V2 vs V1), OR
  (b) MaxDD improvement of ≥ 3pp (less negative drawdown)
on the OOS holdout sample (FULL period minus Dotcom cycle, since Dotcom is
the period most likely to drive any benefit via the high-CAPE peak).

## 2. Empirical motivation (from V1 results)

Per V1 backtest @ 15bps (FULL 2000-01-03 → 2026-04-30):

| Cycle | V1 Combo Sharpe (proxy) | CAPE z_PIT @ start |
|---|---:|---:|
| Dotcom (2000-2003) | 0.357 | +2.92 |
| Bear22 (2022) | 0.336 | +2.14 |
| AIBull (2023-2026) | 0.986 | +1.39 |
| COVID (2020) | 1.331 | +1.65 |
| LongBull (2009-2020) | 1.218 | −0.17 |
| Bull03-07 | 1.543 | +0.93 |
| GFC (2007-2009) | −1.144 | +1.44 |

Spearman rank correlation ρ(CAPE_z, Combo_Sharpe) = −0.50 (p=0.253, n=7).

The direction is consistent with the MV-Conditional thesis (higher
valuation → lower forward Sharpe) but does NOT reach statistical
significance in this small sample. The pre-registered rule below must
account for this WEAK prior support — the hypothesis must be falsifiable
on OOS data.

## 3. Rule R-PRIMARY (the pre-registered rule)

### 3.1 Formal definition

Let z_MVCI(t-1) and z_MRC(t-1) be the PIT expanding-window z-scores of MVCI
and MRC, observed at end-of-month t-1.

Define the indicator:
    fire(t-1) = 1 if (z_MVCI(t-1) > +1.5σ) AND (z_MRC(t-1) > +0.5σ)
              = 0 otherwise

Allocation for month t:
    w_combination(t) = 0.50 if fire(t-1) = 1
                     = 1.00 otherwise
    w_tbills(t) = 1.00 - w_combination(t)

Rebalance cost: 3 bps applied at each transition between buckets (consistent
with V1 Combination's 3 bps internal rebal cost assumption — Strategist
deems this the appropriate baseline).

### 3.2 Why this rule?

- **MVCI z > +1.5σ filter**: captures extreme valuation periods (Dotcom 2.92,
  Bear22 2.14, COVID 1.65, GFC 1.44 historically). The +1.5σ threshold is
  chosen to fire ~30-40% of months in the historical sample (avoiding both
  excessive trading and signal famine).
- **MRC z > +0.5σ co-filter**: requires credit stress to confirm regime
  (avoids false positives in healthy-credit high-valuation periods like
  Bull03-07 where CAPE was already elevated but credit was fine).
- **Joint AND condition**: classic "late-cycle = high val + worsening credit"
  signal. Eliminates single-signal false positives.
- **50/50 risk-off**: not 100% T-bills. Half-out gives signal value without
  excessive sequence risk if the signal is wrong.
- **Monthly evaluation**: matches V1's monthly rebalance frequency. No
  intra-month switching to avoid transaction costs and over-trading.

### 3.3 Falsifiability statement

Rule R-PRIMARY is REJECTED if BOTH of the following hold on the OOS holdout
(FULL period excluding Dotcom):
  - Sharpe(V2) - Sharpe(V1) < +0.05, AND
  - MaxDD(V2) - MaxDD(V1) > -3pp (V2 NOT less-negative by 3pp)

Holm-Šidák-corrected p-value for Sharpe difference (Jobson-Korkie + Memmel
1003) must be < 0.0167 (= 0.05 / 3 rules) for R-PRIMARY to be considered
significant.

If rule is rejected, V2 ships as a DIAGNOSTIC view with explicit "rule did
not pass pre-registered improvement test" disclosure on the dashboard.

## 4. Alternative rules tested (for Holm-Šidák correction)

### R-ALT1: MVCI alone, conservative threshold
    fire(t-1) = 1 if z_MVCI(t-1) > +2.0σ else 0
    w_combination = 0.50 when fire, else 1.00
    (Simpler rule; uses only MVCI; higher threshold)

### R-ALT2: Continuous gradient, joint regime
    w_combination(t) = clamp(1.0 - 0.25 × max(0, z_MVCI(t-1) + z_MRC(t-1) - 1.0), 0.50, 1.00)
    (Smooth de-leveraging based on joint regime stress; no binary threshold)

Both alternatives are computed on the same data, with the same PIT
discipline. Performance reported alongside R-PRIMARY. Holm-Šidák correction
applied across all 3 rules.

## 5. Walk-forward validation

- **Training set**: 2000-01-03 to 2010-12-31 (10.97 years, includes Dotcom + Bull03-07 + GFC)
- **Holdout set**: 2011-01-01 to 2026-04-30 (15.33 years, includes LongBull + COVID + Bear22 + AIBull)
- Thresholds (+1.5σ, +0.5σ, +2.0σ) chosen BEFORE seeing holdout data
- No re-tuning of thresholds based on holdout performance
- Both training and holdout metrics reported separately

## 6. Multiple-testing correction

- **Holm-Šidák correction**: family-wise α = 0.05 across 3 rules → individual
  p-value threshold = 1 - (1 - 0.05)^(1/3) ≈ 0.0170 for first rejection,
  then 1 - (1 - 0.05)^(1/2) for second, etc.
- **White's (2000) Reality Check**: applied to the BEST-performing rule.
  Reference distribution via stationary bootstrap (Politis-Romano 1994),
  10,000 replications, block length per Politis-White (2004) automatic.

## 7. Statistical tests reported

- **Jobson-Korkie (1981) Sharpe difference test** with Memmel (2003) small-sample correction
- **Diebold-Mariano (1995)** for cumulative returns difference
- **Bootstrap CIs** on V1 Sharpe, V2 Sharpe, V1-V2 Sharpe difference (95% CI, 10K stationary bootstrap reps)
- **MaxDD difference**: bootstrap CI (10K stationary reps), no formal hypothesis test

## 8. Pre-registration commitment

This file is committed to git via:
    git add specs/MV_CONDITIONAL_RULE_PREREGISTER.md
    git commit -m "preregister(v11.2): MV-Conditional rule R-PRIMARY + 2 alternatives"

The git commit timestamp serves as the formal pre-registration timestamp.
ANY change to rule definitions after this commit requires:
  1. An explicit `specs/MV_CONDITIONAL_RULE_PREREGISTER_AMENDMENT_v2.md` file
  2. Strategist (Claude AI) approval documented in `DECISIONS.md`
  3. Re-running BOTH old and new rules with full disclosure

End of MV_CONDITIONAL_RULE_PREREGISTER.md
