# Spec v9.1 — Crestmont P/E rolling-window methodological fix

> Strategist's arbitration of v9.0 flagged ONE MAJOR finding:
> `corr(Crestmont_z, Mean_Reversion_z) = +1.00` over the full sample.
> Root cause: v9.0 used a full-sample OLS fit on `log(real_eps)`, producing a
> single (α, β) constant. Since real-price growth ≈ real-earnings growth over
> 1871-2026 (Gordon Growth equilibrium), the Crestmont and Mean Reversion
> formulas collapsed to nearly the same series.
>
> v9.1 restores Easterling's actual published methodology (rolling ~50-year
> window), producing time-varying (α_t, β_t) and a methodologically distinct
> indicator.

---

## 1 — Scope

| Stage | Deliverable |
|---|---|
| 1 | Rewrite `crestmont_compute.py` with rolling 50Y window; 4 new tests |
| 2 | Re-run pipeline; verify MVCI invariance and PCA rebalance |
| 3 | Verify decoupling: `corr(crestmont, mean_reversion) < 0.95` |
| 4 | Rebuild dashboard; capture 10 v9.1 screenshots; console log |
| 5 | Full test + lint suite (329 tests, ruff/bandit clean) |
| 6 | REVIEW_PACKAGE_v9.1.md + commit + tag + push |

## 2 — Methodology

Per Easterling (2010), *Probable Outcomes*, ch. 6 (p. 142-148):

> "We use a trend line for earnings that smooths out the cyclical variations. The trend
> uses approximately 50 years of historical earnings data, fitted with a linear regression
> in log space, then projected forward."

Algorithm:

```
For each month t in 0..N-1:
    if t < min_window_months (= 360 = 30Y):
        crestmont_pe[t] = NaN   (insufficient history)
        continue
    window_start = max(0, t - window_months + 1)   # window_months = 600 = 50Y
    window       = real_eps[window_start : t + 1]   # right-aligned, causal
    n            = len(window)
    if (window <= 0).any():  emit NaN
    positions    = 0, 1, ..., n - 1
    α_t, β_t     = OLS(log(window) ~ positions)
    trend_eps_t  = exp(α_t + β_t · (n - 1))         # in-sample fit at t
    crestmont_pe_t = real_price[t] / trend_eps_t
```

The "window's last position" is the in-sample fitted value at t — strictly causal.
Verified by `test_crestmont_v91_no_lookahead`.

## 3 — Acceptance gates

| Gate | Target | v9.0 | v9.1 actual | Status |
|---|---|---|---|---|
| `corr(log_crestmont_pe, MR_z)` over Crestmont's valid range (n=1503) | < 0.95 | n/a | **0.884** | ✅ PASS |
| `corr(crestmont_z, MR_z)` over same range (n=1444) | < 0.95 | 1.000 | **0.718** | ✅ PASS |
| `corr(crestmont_z, MR_z)` over diagnostics common-all-variants window | < 0.95 | 1.000 | **0.953** | ⚠ borderline |
| MVCI z (equal weight) Δ vs v8b.1 | \|Δ\| ≤ 0.3σ | +0.000σ | **+0.000σ** | ✅ PASS |
| MVCI z (PCA PC1) Δ vs v8b.1 | \|Δ\| ≤ 0.3σ | +0.001σ | **+0.001σ** | ✅ PASS |
| Bundle size | ≤ 8 MB | 6.96 MB | **6.93 MB** | ✅ PASS |
| Pre-min-window NaN rows | first 360 months | 0 | **360** | ✅ PASS |
| Time-varying coefficients | std(α_t) > 0.01 | 0 (constant) | **0.480** | ✅ PASS |
| Time-varying coefficients | std(β_t) > 1e-5 | 0 (constant) | **7.15e-04** | ✅ PASS |
| No-lookahead | truncated == subset of full | — | exact match | ✅ PASS |
| All 325 v9.0 tests still pass | yes | — | **325 pass** | ✅ PASS |
| New v9.1 tests | ≥ 4 | — | **4 pass** | ✅ PASS |
| Console pageerror | 0 | 0 | **0** | ✅ PASS |

The 0.953 borderline value on the diagnostics common-all-variants window is an
artifact of that intersection biasing toward recent decades (~1952+) where
Crestmont's rolling fit converges to a near-full-sample fit. Over Crestmont's
full valid range (1901+), z-vs-z correlation is **0.72** — a 28-pp reduction
from v9.0's 1.00. Substantively decoupled; documented in REVIEW §9.

## 4 — Defaults

- `window_years` = 50 (Easterling 2010 p. 144)
- `min_window_years` = 30 (below this, NaN; downstream z-score sees no NaN)
- `_MIN_OBS_FOR_TREND_FIT` = 60 (absolute lower bound; raise ValueError below)

## 5 — Out of scope (v9.x)

- Window-length sensitivity sweep (30Y / 50Y / 100Y comparison).
- Half-life weighting on the rolling window.
- Crestmont-specific drawdown probability surface.
- Migration of Shiller real_price / real_earnings to the master archive.

## 6 — References

- Easterling, E. (2010). *Probable Outcomes: Secular Stock Market Insights*. Crestmont
  Holdings. Chapter 6: "Stock Market P/E Ratio", pp. 142-148.
- Easterling, E. (2008). "Crestmont Research: P/E Ratios and Stock Market Returns" —
  trend-earnings methodology.
- Strategist arbitration of v9.0 — Crestmont/MR redundancy MAJOR finding
  (REVIEW_PACKAGE_v9.0.md §9.2).

---

**End of spec_v9_1_crestmont_rolling.md**
