<!--
SEAL_PROVENANCE_BLOCK (machine-readable; do not modify)
====================================================
v1_seal_commit: a8635ef
v1_seal_timestamp: 2026-05-21T11:46:05-04:00
v1_verdict_commit: d56174c
v1_verdict_timestamp: 2026-05-22T14:30:59-04:00
v1_verdict_descends_from_v1_seal: true
amendments_file_path: buffet_indicator/specs/v11_4_amendment_candidates_FROM_v11_3_0.md
amendments_sha256: e19d63b562fa730728352525b6a74faed689cbee2f17259aa686944fce1c45f0
amendments_commit: 1ca4da2d590b64f40c674e6d5722679feca9248f
seal_metadata_collected_utc: 2026-05-24T17:10:59.757219+00:00
invariants_B11_B12_B13_B15: PASS
seal_commit: see outputs/seal_manifest.json (resolved post-commit)
SEAL_PROVENANCE_BLOCK_END
-->

# MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER — DRAFT_v4

> **Status**: DRAFT v4 — NOT yet sealed. NARROW round-4 verification pending (both ChatGPT 5.5 Pro and Codex; ~30 min each).
> **Predecessor**: DRAFT v3 (round-3 verdict: ChatGPT `SEAL_WITH_MINOR_EDITS` with 1 VERIFY-FAIL upgraded to MAJOR + 1 NEW MINOR; Codex `RE-DRAFT_REQUIRED` with 1 NEW BLOCKER + 2 NEW MINORs).
> **Round-3 arbitration**: `DECISIONS_2026_05_24_v11_4_arbitration_ROUND_3.md` (accepts 1 BLOCKER + 1 MAJOR + 3 MINORs + 1 NIT = 6 of 6 findings).
> **Surgical change scope**: ~10 text edits from DRAFT_v3 (§2.1 transparency wording, §2.2 arithmetic correction, §3.8 column name revert, §8.1 invariant rename, §9 item #11 cross-reference, §10.2 row deletion, §11.2 heading count + test name + tolerance addition, §12 enum rename).
> **Sealing workflow**: narrow round-4 verification → if clean → seal. Round-5 unlikely (predicted 8%).

---

## PREAMBLE

This pre-registration governs the v11.4 sprint constructing the Liquidity Composite v2.0. It supersedes v1.0 (sealed commit `a8635ef`, verdict FAIL at commit `d56174c`) by adopting the four amendment candidates extracted from v11.3.0's `verdict.json` (preserved verbatim in `specs/v11_4_amendment_candidates_FROM_v11_3_0.md` on `spec/liquidity-composite-v2.0`, SHA-256 `e19d63b562fa730728352525b6a74faed689cbee2f17259aa686944fce1c45f0`).

All other elements of v1.0's design are retained unchanged. Specifically: the seven testable criteria's *targets* are preserved (with Criterion 4 wording disambiguated per amendment 2), the binary decision rule `n_pass ≥ 4 of 7` is preserved verbatim from v1.0, and inference machinery (HAC, Stambaugh, Campbell-Yogo) is inherited verbatim per §3.5–§3.6. This conservatism is deliberate: changing criterion *targets* or *decision rule* after observing v1.0's results would constitute data-snooping and invalidate pre-registration discipline.

The v2.0 sprint's purpose is to test whether the four methodological amendments (priors, criterion wording, distribution family, insufficient-sample gate) materially change the verdict for a model that is otherwise identical to v1.0.

**Self-containment commitment** (per Codex MAJOR #3): every inherited-from-v1.0 value executable by code is transcribed verbatim in §10 below. No clause depends on reading another document at implementation time.

---

## §0 — Pre-registration metadata and provenance invariants

### §0.1 Identifiers

- **Sealing commit**: see `outputs/seal_manifest.json` (resolved post-commit per §9 sidecar approach)
- **Sealing date (ISO 8601 UTC)**: see `outputs/seal_manifest.json`
- **Predecessor v1.0 sealing commit**: `a8635ef`
- **Predecessor v1.0 sealing timestamp (ISO 8601 UTC)**: `2026-05-21T11:46:05-04:00`
- **Predecessor v1.0 verdict commit**: `d56174c`
- **Predecessor v1.0 verdict timestamp (ISO 8601 UTC)**: `2026-05-22T14:30:59-04:00`
- **Amendments file**: `specs/v11_4_amendment_candidates_FROM_v11_3_0.md`
- **Amendments file SHA-256**: `e19d63b562fa730728352525b6a74faed689cbee2f17259aa686944fce1c45f0`
- **Branch**: `spec/liquidity-composite-v2.0`
- **Verdict authority**: Strategist (Claude AI).
- **Implementation authority**: Claude Code.

### §0.2 Chronology and provenance invariants (5 invariants — ACCEPT ChatGPT BLOCKER #1 + round-2 New-2)

The seal commit fails validation if ANY invariant below is false:

- **B-1.1** `v1_seal_timestamp ≤ v1_verdict_timestamp`
- **B-1.2** `v1_verdict_timestamp ≤ v2_seal_timestamp` (v1.0 must close before v2.0 seals)
- **B-1.3** `amendments_file_commit` is an ancestor of `v2_seal_commit`
- **B-1.4** `v2_seal_timestamp ≤ now_at_seal_invocation` (no future sealing)
- **B-1.5** `git merge-base --is-ancestor a8635ef d56174c` returns exit code 0 (v1.0 verdict commit descends from v1.0 sealed pre-reg commit — defends against rewrite-history attacks)

Claude Code MUST verify all five invariants programmatically before writing the seal commit. Failure aborts the seal with an unrecoverable error logged to `setup_and_run.log`. Provenance block at seal time logs `v1_verdict_descends_from_v1_seal = true`.

### §0.3 HARD GATE invariant (extended per Codex MAJOR #6)

Every artifact written by v11.4 implementation must verify the v2.0 pre-reg commit is an ancestor of the writing commit's HEAD. The check is implemented in a shared function specified in §8.2.

---

## §1 — Hypothesis

Aggregate macro-liquidity conditions, summarized as a multi-component composite z-score over five components — NetFed liquidity, M2 growth, total bank credit (bank lending), dollar-strength-inverse via ICE DXY, and funding stress (TED-spread or post-2018 equivalent) — predict forward US-equity total returns at horizons {1Y, 3Y, 5Y, 10Y}.

**Canonical component IDs (FIX per Codex BLOCKER #2 — match v1.0 sealed catalog verbatim)**:

| ID | Component name | FRED series |
|---|---|---|
| `z1` | NetFed liquidity | derived = WALCL − RRPONTSYD − WDTGAL |
| `z2` | M2 growth y/y | `M2SL` |
| `z3` | Bank lending growth y/y | `BUSLOANS` → `TOTLL` (post-2010 splice) |
| `z4` | Dollar-strength-inverse | `DTWEXBGS` (broad) / `DTWEXBFM` (major) |
| `z5` | Funding stress | `TED` (pre-2018) → SOFR-IORB (post-2018) |

The *direction* of prediction is not pre-specified: per amendment 1, both monetarist (positive β) and mean-reversion (negative β) literature streams receive non-zero prior probability per component.

Three composite scopes (`LC_FULL`, `LC_TIER2`, `LC_DEEP`) follow v1.0's construction unchanged, transcribed in §10.

---

## §2 — Decision rule (REVISED per ChatGPT round-2 #6 VERIFY-FAIL — Option A preserving v1.0 target comparability)

### §2.1 Binary verdict — inherited verbatim from v1.0

```
PASS  ⟺  n_pass ≥ 4 of 7
FAIL  ⟺  n_pass ≤ 3 of 7
```

This is the v1.0 sealed decision rule, preserved verbatim in v2.0 to maintain target comparability across pre-registrations.

**DRAFT v2's "two-tier rule" is WITHDRAWN.** DRAFT v2 proposed `PASS ⇔ (n_pass ≥ 4) AND (n_pass_predictive ≥ 2)`. ChatGPT round-2 (#6 VERIFY-FAIL) correctly observed this is algebraically redundant: with only 2 non-predictive criteria (C5, C6), `n_pass ≥ 4` mechanically implies `n_pass_predictive ≥ 4 − 2 = 2`. The two-tier wording added no protective gating and falsely claimed to be "stricter." It is removed.

**Predictive subset reporting**: the verdict JSON (§12) reports `n_pass_predictive` (count of passing criteria in `{C1, C2, C3, C4, C7}`) as a *transparency field*, not a gate. Downstream display can highlight cases where `n_pass = 4` depends on C5–C6 admissibility criteria and only two predictive criteria pass, but this never alters the binary verdict.

Cells failing the insufficient-sample gate (§3.4) are recorded as `not_evaluable` and count as FAIL for the relevant criterion. See §12 for verdict JSON schema.

Verdict is published in `outputs/lc_v2_verdict.json` with all 7 criteria, realized values, pass/fail status, evidence_status, and the locked `pre_reg_commit` field.

### §2.2 Null calibration of the binary rule (CORRECTED arithmetic per ChatGPT round-3 New-1)

Under the null hypothesis that LC components have no predictive content, with stated independent marginal pass probabilities per criterion:

| Criterion | Marginal P(pass) under null | Rationale |
|---|---|---|
| C1 OOS R² @ 1Y > 0.005 | 0.10 | Goyal-Welch (2008) typical OOS R² noise floor |
| C2 OOS R² @ 3Y > 0.020 | 0.10 | Same noise-floor logic, multi-year horizon |
| C3 OOS R² @ 5Y > 0.040 | 0.05 | Tighter threshold; lower null-pass rate |
| C4 LC_FULL \|t_NW\| > 1.65 (two-sided 10% screen) | 0.10 | Nominal 10% two-sided alpha (see §5.1) |
| C5 ADF rejects null for all 5 components, Holm-Šidák α=0.05 | 0.60 | Macro liquidity series typically near-but-not-unit-root |
| C6 max VIF across 5 components < 5 | 0.80 | Components orthogonal-by-design |
| C7 Bonferroni-significant cell at α/20 = 0.0025 | 0.05 | Bonferroni-corrected across 20 (5×4) cells |

Under the assumed-independence approximation with marginal vector `p = [0.10, 0.10, 0.05, 0.10, 0.60, 0.80, 0.05]`:

```
P(n_pass ≥ 4 | null, independent marginals)
  = Σ_{k=4}^{7} P(exactly k pass | independent marginals above)
  = 0.0254580 + 0.0020277 + 0.0000791 + 0.0000012
  = 0.0275660
  = 2.7566%
  ≈ 2.8%
```

(Computed as the tail of the Poisson-binomial distribution. Term-by-term verification: `P(N=4)=0.0254580`, `P(N=5)=0.0020277`, `P(N=6)=0.0000791`, `P(N=7)=0.0000012`. Verified independently in round-3 review.)

**Interpretation**: under the stated independent-marginal approximation, the plain `n_pass ≥ 4` rule has an approximately 2.8% null-pass probability. This is **descriptive, not a sealed invariant** and not a formal familywise-error guarantee, because the criteria are not independent and empirical dependence could move the realized null tail probability. Specifically:

1. The independence assumption is approximate — criteria 5, 6 are likely positively correlated (well-behaved data tends to be both stationary and not multicollinear). Positive correlation between admissibility criteria moves the null tail probability higher.
2. Predictive criteria (C1, C2, C3) may exhibit positive correlation under the null if model misspecification affects multiple horizons jointly.
3. The PASS/FAIL determination remains exclusively the binary rule in §2.1, independent of this calibration.

The 2.8% rate compares favorably to a conventional 5% familywise alpha (more conservative), but should not be interpreted as a formal Type I error rate.

---

## §3 — Methodology

### §3.1 Forward returns

Monthly grid, SPXTR total return (Yahoo `^SP500TR` 1988+ spliced with Shiller dividend-reinvested column for pre-1988), horizons in months `h ∈ {12, 36, 60, 120}`. Identical to v1.0.

### §3.2 Estimation window and data availability

#### §3.2.1 Expanding window

Estimation expands from the longest jointly-available date for the five components per scope (§10).

#### §3.2.2 Vintage policy (ACCEPT Codex BLOCKER #2 from round-1)

For every forecast origin `t`, component values are computed from records with release/vintage timestamp `≤ t`. For revisable FRED series (`M2SL`, `BUSLOANS`, `TOTLL`, `WALCL`, `WDTGAL`, and any other ALFRED-supported series), the consumption pattern is:

```python
series = load_master(series_id, vintage=t, fill="none")  # MANDATORY
# load_master(series_id, vintage="latest")  ← FORBIDDEN inside backtest loops
```

Latest-vintage consumption is forbidden inside any code path that produces verdict-bearing artifacts. The only exceptions are:
- Static reporting tables explicitly labeled "as-revised" / "latest-vintage" in their caption.
- Diagnostic-only outputs in `outputs/diagnostics/<session_tag>/` with `purpose: descriptive_only` metadata.

Every verdict JSON cell records `feature_vintage_max` and asserts `feature_vintage_max ≤ forecast_origin`. Failing this assertion at any cell raises `LookAheadViolation` and aborts the run.

#### §3.2.3 RRPONTSYD zero-fill boundary (ACCEPT Codex MINOR #10 from round-1)

For RRPONTSYD, rows with observation date **strictly `< 2013-09-23`** are set to `0.0` in the NetFed transform layer. 2013-09-23 and later use source values. The raw source parquet is not overwritten. Output series include `rrpontsyd_pre2013_treatment = "zero_fill_strict_lt_2013_09_23"` in metadata and retain a `source_value_missing_pre_fill` diagnostic count.

### §3.3 OOS evaluation (ACCEPT ChatGPT MAJOR #3 + round-2 New-4 wording fix)

For a forecast origin `t` and horizon `h` (in months), the model predicts `r_{t, t+h}`. The training set at `t` is:

```
training_set(t, h) = { (x_s, r_{s, s+h}) : s + h ≤ t }
```

The condition `s + h ≤ t` ensures the realized return `r_{s, s+h}` was observable at time `t`. Feature values `x_t` may be used only for the forecast being scored, not as a training observation until `r_{t, t+h}` is realized.

OOS R² uses the prevailing historical mean as benchmark (Goyal-Welch 2008), estimated under the same `s + h ≤ t` realized-return cutoff.

Verdict JSON adds per-cell:
- `train_cutoff_inclusive = t - h` — **inclusive: last allowed training forecast-origin `s` under `s+h ≤ t`**.
- `score_date = t + h`
- `feature_origin = t`

(DRAFT_v2 mislabeled `train_cutoff` as "exclusive"; corrected to "inclusive" per ChatGPT round-2 New-4.)

### §3.4 Insufficient-sample gate

A `(composite × horizon × criterion)` cell is recorded as `not_evaluable` if **either** of the following holds:

```
n_obs_oos < max(60, 3 × HAC_lag)
                OR
n_eff < 30
```

where:

- `n_obs_oos` = number of forecast-origin rows `t` satisfying `score_date ≤ data_cutoff` AND `feature_vintage_max ≤ t` AND `(x_t, r_{t, t+h})` both non-NaN, evaluated per `(composite, horizon, criterion)`.

- `HAC_lag` = inherited from v1.0 (see §3.5).

- `n_eff` = HAC-adjusted effective sample size:
  ```
  n_eff = n_obs_oos / (1 + 2 × Σ_{k=1..HAC_lag} max(0, ρ̂_k))
  ```
  where `ρ̂_k` is the sample autocorrelation at lag `k` of the OOS forecast residuals, computed on the training residuals through `t = data_cutoff - h`. Negative `ρ̂_k` are truncated at zero for conservatism.

Cells violating the gate are tagged `NOT_EVALUABLE_COUNTED_FAIL` in the verdict JSON (distinguished from `FAIL_STATISTICAL`, see §12) and count as FAIL for the relevant criterion.

**Disclosure**: With LC_FULL data availability from 2003-02 (NetFed earliest), the 10Y horizon has at most ~160 monthly OOS observations vs `3 × HAC_lag = 3 × 119 = 357` minimum, so Criterion 4 at 10Y is **expected to be `not_evaluable` by construction**. This is documented honest pre-reg disclosure, not gate-rigging. Criterion 4 still passes if ANY of {1Y, 3Y, 5Y} satisfies `|t_NW| > 1.65` at evaluable status.

### §3.5 HAC standard errors (verbatim inheritance from v1.0)

Newey-West with lag `L = horizon_months − 1`:

| Horizon | `horizon_months` | `HAC_lag = L` |
|---|---|---|
| 1Y | 12 | 11 |
| 3Y | 36 | 35 |
| 5Y | 60 | 59 |
| 10Y | 120 | 119 |

Implementation:
```python
from statsmodels.regression.linear_model import OLS
model = OLS(y, X).fit(
    cov_type="HAC",
    cov_kwds={"maxlags": HAC_lag, "use_correction": True},
)
```

### §3.6 Stambaugh bias and Campbell-Yogo intervals (verbatim inheritance from v1.0)

**v2.0 inherits v1.0's inference rules verbatim, without methodological change.** Specifically:

- **Stambaugh (1999) bias correction** applied when AR(1) of the regressor `ρ̂ > 0.85` (strict greater-than — see §3.9 comparator semantics). `ρ̂` is estimated on the same expanding training rows used for the predictive regression at forecast origin `t`, after dropping non-finite values.
- **Campbell-Yogo (2006)** confidence intervals computed using v1.0's simplified critical-value grid (transcribed in §10.1) when `ρ̂_X > 0.95`. Outside the grid, CY status is `not_evaluable_outside_grid`.
- If `ρ̂ ≥ 0.995` or `n < max(120, 3 × HAC_lag)` for the AR(1) estimation, Stambaugh correction is flagged `not_evaluable_rho_boundary` and is not applied.

Changes to inference rules are deferred to a future v2.1 pre-reg.

### §3.7 Conditional forecast distribution (AMENDMENT 3 — REWRITTEN per Codex round-2 BLOCKER #1)

Replaces v1.0's Gaussian conditional distribution with a standardized Hansen (1994) skewed-t.

#### §3.7.1 Parameterization (corrected to match `arch` library naming)

Use `arch.univariate.SkewStudent` (pinned `arch==7.0.0`). The library's parameter naming convention:

- **`eta_tail` ∈ (2, ∞)** — degrees-of-freedom (tail heaviness). `arch` names this `eta`.
- **`lambda_skew` ∈ (−1, 1)** — skewness (asymmetry). `arch` names this `lambda`.

DRAFT_v2 had these inverted; DRAFT_v3 onwards corrects to match `arch` conventions. Verdict JSON fields are `skewt_eta_tail` and `skewt_lambda_skew` to avoid label ambiguity.

Implementation bounds enforced via L-BFGS-B:
- `eta_tail ∈ [2.05, 200.0]` (strict-interior, avoid `ν → 2` singularity)
- `lambda_skew ∈ [−0.95, 0.95]` (strict-interior, avoid boundary likelihood singularity)

#### §3.7.2 Fitting procedure (corrected `loglikelihood` signature per Codex BLOCKER #1)

At each forecast origin `t`:

1. Compute training residuals from §3.5 regression: `e_s = r_{s, s+h} − ŷ_{s, s+h}` for `s + h ≤ t`.
2. Standardize: `ẽ_s = e_s / σ̂_t` where `σ̂_t = std(e_s, ddof=1)` over the training set.
3. **Fallback gate** — if ANY of the following holds, set `distribution_family = "gaussian_fallback"` and skip skewed-t fit:
   - `n_resid < 120`
   - `σ̂_t ≤ 1e-12` (numerically degenerate)
   - fewer than 20 unique rounded residuals (insufficient empirical heterogeneity)
   - any non-finite residual in training set
4. Otherwise, fit `(eta_tail, lambda_skew)` via ML using `arch.univariate.SkewStudent` with the CORRECT loglikelihood signature:
   ```python
   from arch.univariate import SkewStudent
   import scipy.optimize
   import numpy as np

   dist = SkewStudent(seed=child_seed_for_cell(composite, horizon, forecast_origin))
   std_resid = np.asarray(standardized_residuals, dtype="float64")
   sigma2 = np.ones_like(std_resid, dtype="float64")  # standardized → unit variance

   # arch parameter order: [eta_tail, lambda_skew]
   start = np.array([8.0, 0.0])                       # ν=8 (moderate tails), λ=0 (no skew)
   bounds = [(2.05, 200.0), (-0.95, 0.95)]

   result = scipy.optimize.minimize(
       fun=lambda params: -float(dist.loglikelihood(params, std_resid, sigma2, individual=False)),
       x0=start,
       method="L-BFGS-B",
       bounds=bounds,
   )
   if not result.success or not np.isfinite(result.fun):
       distribution_family = "gaussian_fallback"
       fallback_reason = "ml_convergence_failure"
   else:
       distribution_family = "skewed_t"
       eta_tail_hat, lambda_skew_hat = result.x
   ```
5. Always log `distribution_family`, `fallback_reason` (if any), `eta_tail_hat`, `lambda_skew_hat`, and `loglikelihood_at_optimum` to the verdict cell.

**Library version pin**: `requirements.lock` must pin `arch==7.0.0`. If a future bump changes the `SkewStudent.loglikelihood` signature or parameter naming, the change becomes a v2.1 pre-reg event.

#### §3.7.3 Conditional forecast

Let `regression_mean(t)` denote the predicted mean from §3.5. Then:

```
r_{t, t+h} = regression_mean(t) + σ̂_t · z
```

where:
- If `distribution_family = "skewed_t"`: `z ~ SkewStudent(eta_tail_hat, lambda_skew_hat)` standardized to `E[z]=0, Var[z]=1`.
- If `distribution_family = "gaussian_fallback"`: `z ~ Normal(0, 1)`.

No location parameter is estimated separately — the residual mean is exactly the regression mean by OLS first-order conditions, and the skewed-t is standardized to zero mean in `z`-space.

### §3.8 Stationary bootstrap (REVERTED per Codex round-3 New-1 — `stationary` column verified against `arch==7.0.0` actual API)

Stationary bootstrap (Politis-Romano 1994) via `arch.bootstrap.StationaryBootstrap`. Specification:

- **`n_bootstrap = 50,000`** — **TRULY IMMUTABLE** for all verdict-bearing quantities. No downsample option (ChatGPT round-2 New-1 + Codex round-2 New-4 — see §11.3).
- **Block length** (Codex round-3 EMPIRICALLY VERIFIED column name on installed `arch==7.0.0`):
   ```python
   import arch.bootstrap
   import numpy as np

   obl = arch.bootstrap.optimal_block_length(x)
   # arch==7.0.0 returns DataFrame with columns ["stationary", "circular"]
   raw = float(obl["stationary"].iloc[0])
   if np.isfinite(raw) and raw > 0:
       block_length = int(np.ceil(raw))
   else:
       block_length = int(np.ceil(2 * len(x) ** (1/3)))
   block_length = min(max(1, block_length), max(1, len(x) // 2))
   ```
   **Note on round-history**: DRAFT_v2 used `["stationary"]` (correct). Codex round-1 + round-2 advice changed it to `["b_sb"]` (based on docs, not execution). Codex round-3 actually executed against installed `arch==7.0.0` and confirmed `["stationary", "circular"]` are the real column names; DRAFT_v4 reverts to `["stationary"]`. The acceptance test §11.2 `test_optimal_block_length_uses_arch_stationary_column` verifies this against the real library.
- **Determinism**: derived seeds from a master `numpy.random.SeedSequence(42)`:
   ```python
   import hashlib
   import numpy as np

   master_ss = np.random.SeedSequence(42)
   cell_key = f"{composite}|{horizon}|{forecast_origin.isoformat()}"
   cell_seed = int.from_bytes(hashlib.sha256(cell_key.encode()).digest()[:8], "big")
   rng = np.random.default_rng(np.uint64(cell_seed))
   bs = arch.bootstrap.StationaryBootstrap(block_length, x, seed=rng)
   ```
- **Storage**: only summary statistics (CIs, Brier scores, point estimates) persist by default. Raw draws are optional under `outputs/diagnostics/<session_tag>/` and size-budgeted.
- **Reproducibility test**: two runs with same seed, same data must produce byte-identical bootstrap summaries (enforced by §11 test `test_stationary_bootstrap_is_byte_identical`).

If `n < 30` or `block_length > n // 2`, the bootstrap is marked `not_evaluable` and CIs are NaN.

**Library version pin**: `requirements.lock` must pin the full lock (`arch==7.0.0` + `pandas==2.2.3` + `numpy==1.26.4` + `scipy==1.13.1` + `statsmodels==0.14.2`). Codex round-3 confirmed naive `pip install arch==7.0.0` alone pulls incompatible `pandas==3.0.3` and fails import.

### §3.9 Comparator semantics (REVISED per Codex round-2 New-5 — Stambaugh boundary fix)

To eliminate boundary ambiguity:

| Clause | Operator | Boundary case | Interpretation |
|---|---|---|---|
| §3.4 sample gate `n_obs_oos < max(60, 3 × HAC_lag)` | `<` | `n_obs_oos = 60` | `evaluable` |
| §3.4 `n_eff < 30` | `<` | `n_eff = 30.0` | `evaluable` |
| §3.2.3 RRPONTSYD `< 2013-09-23` | `<` | obs on 2013-09-23 | source value (NOT zero-filled) |
| §5 C1 OOS R² > 0.005 | `>` | OOS R² = 0.005 | FAIL |
| §5 C2 OOS R² > 0.020 | `>` | exact | FAIL |
| §5 C3 OOS R² > 0.040 | `>` | exact | FAIL |
| §5 C4 \|t_NW\| > 1.65 | `>` | `\|t\| = 1.65` | FAIL |
| §5 C5 ADF `p < 0.05` (Holm-Šidák-adjusted) | `<` | exact | FAIL |
| §5 C6 max VIF `< 5` | `<` | VIF = 5.0 | FAIL |
| §5 C7 Bonferroni `p < 0.0025` | `<` | exact | FAIL |
| **§3.6 Stambaugh `ρ̂ > 0.85`** | **`>`** | **`ρ̂ = 0.85` exactly** | **Stambaugh NOT applied** (strict `>` enforced — FIX per Codex round-2 New-5) |
| §3.6 Stambaugh `ρ̂ ≥ 0.995` | `≥` | exact | `not_evaluable_rho_boundary` |

All comparators implemented through a single helper `compare_threshold(value, op, threshold, *, on_nan="fail")`.

(DRAFT_v2 had a self-contradicting row that listed operator `>` but said boundary "Stambaugh applied"; corrected.)

---

## §4 — Priors (AMENDMENT 1)

### §4.1 Component-level sign priors

The empirical literature contains two ex ante plausible mechanisms:

- *Liquidity-beta / asset-inflation stream*: loose monetary and credit conditions → higher asset prices → positive β at short horizons. References: Friedman-Schwartz (1963); modern Treasury-flow analyses; intermediary-asset-pricing literature.
- *Credit-cycle / mean-reversion stream*: tight credit conditions precede higher forward returns at multi-year horizons; loose conditions precede lower forward returns. References: Schularick-Taylor (2012); Adrian-Boyarchenko (2012); Fama-French (1988).

Both have well-cited empirical support. v2.0 takes the **Bayesian-model-averaging (BMA) equipoise** position: 0.5/0.5 sign prior on every component.

| Component ID | Component name | P(β > 0) | P(β < 0) |
|---|---|---|---|
| `z1` | NetFed liquidity | 0.5 | 0.5 |
| `z2` | M2 growth y/y | 0.5 | 0.5 |
| `z3` | Bank lending growth y/y (BUSLOANS→TOTLL) | 0.5 | 0.5 |
| `z4` | Dollar-strength-inverse | 0.5 | 0.5 |
| `z5` | Funding stress (TED→SOFR-IORB) | 0.5 | 0.5 |

**Role of priors in v2.0**: priors are *interpretive only*. They do NOT alter Criteria 1–7 or the PASS/FAIL threshold. Their function is to:

1. Justify the sign-agnostic Criterion 4 (§5).
2. Prevent sign-based cherry-picking in narrative interpretation of v2.0 verdict.
3. Allow downstream Bayesian model averaging across BMA-symmetric and literature-tilt-sensitivity views (§4.3).

### §4.2 Composite-level prior

Because the five component priors are symmetric by design, the composite sign prior is also symmetric under the maintained no-directional-tilt assumption. **Independence between components is NOT required**: a symmetric joint distribution over component-β signs implies a symmetric aggregate-β sign regardless of component-component correlations. Correlations affect uncertainty and magnitude of the aggregate, not its symmetric sign-prior.

### §4.3 Literature-tilt sensitivity (descriptive, not verdict-affecting — FIX per ChatGPT round-2 §4.3 wording)

For interpretive completeness (not affecting verdict), §15 (appendix) reports criteria evaluated under asymmetric priors per the following literature tilts:

| Component ID | Component name | Horizon-conditional asymmetry | Source |
|---|---|---|---|
| `z3` | Bank lending growth y/y | 60/40 toward negative β at 3Y–10Y | Schularick-Taylor (2012) |
| `z5` | Funding stress | 60/40 toward negative β at 3Y–10Y | Adrian-Boyarchenko (2012) |
| `z2` | M2 growth y/y | 60/40 toward positive β at 1Y | monetarist liquidity stream |
| `z1`, `z4` | NetFed, DXY inverse | 50/50 (no strong pre-v1.0 evidence) | — |

These tilts are sensitivity analysis ONLY and do not enter the deterministic verdict. The label "descriptive, not verdict-affecting" replaces DRAFT_v2's "descriptive, not pre-registered" (this sensitivity IS pre-specified by the pre-reg, just not verdict-affecting).

---

## §5 — Seven testable criteria

Criteria 1, 2, 3, 5, 6, 7 are **unchanged from v1.0**. Criterion 4 is amended per amendment 2.

| # | Criterion | Threshold | Operator | Predictive subset? |
|---|---|---|---|---|
| 1 | OOS R² @ 1Y on `LC_TIER2` | 0.005 | `>` | Yes |
| 2 | OOS R² @ 3Y on `LC_TIER2` | 0.020 | `>` | Yes |
| 3 | OOS R² @ 5Y on `LC_TIER2` | 0.040 | `>` | Yes |
| 4 | `LC_FULL` two-sided 10% screen, `\|t_NW\| > 1.65` at any evaluable horizon | 1.65 | `>` | Yes |
| 5 | ADF rejects null for all 5 components at Holm-Šidák-adjusted α=0.05 | 0.05 (post-adjust) | `<` | No (admissibility) |
| 6 | Max VIF across 5 components | 5 | `<` | No (admissibility) |
| 7 | Any Bonferroni-significant (component × horizon) cell at α/20 = 0.0025 | 0.0025 | `<` | Yes |

### §5.1 Criterion 4 explicit semantics (AMENDMENT 2)

At any evaluable horizon (subject to §3.4 gate), Criterion 4 passes if `|t_NW| > 1.65` for `LC_FULL`'s regression coefficient. The sign of β does not factor in.

**Effective nominal alpha**: 10% two-sided (since `P(|Z| > 1.65) ≈ 0.099`). This is a **weak-evidence screen**, intentionally so — its weakness is balanced by Criterion 7's Bonferroni-adjusted 5% across 20 cells.

Threshold target unchanged from v1.0; what changed is the *sign convention* (one-sided → two-sided), not the *evidence strength* at the boundary. Treating the criterion as one-sided 5% (1.65 with sign restriction) vs two-sided 10% (1.65 without sign) preserves target difficulty per the preamble's "targets unchanged" commitment.

Horizons failing the §3.4 sample gate are excluded from the search. If all four horizons fail the gate, Criterion 4 is recorded as `NOT_EVALUABLE_COUNTED_FAIL`.

### §5.2 Criterion 5 ADF multiplicity

ADF tests are run per component (5 tests). Holm-Šidák step-down correction is applied: sort raw p-values ascending, compare `p_(k)` against `1 − (1 − α)^(1 / (n − k + 1))` with `α = 0.05` and `n = 5`. The criterion passes only if ALL 5 components reject at the adjusted threshold.

### §5.3 Criterion 7 multiplicity denominator — 20 cells enumerated (CORRECTED component IDs)

The Bonferroni denominator is 20, derived as `5 components × 4 horizons = 20 cells`:

| Component ID | Component name | 1Y | 3Y | 5Y | 10Y |
|---|---|---|---|---|---|
| `z1` | NetFed liquidity | C7-cell-1 | C7-cell-2 | C7-cell-3 | C7-cell-4 |
| `z2` | M2 growth y/y | C7-cell-5 | C7-cell-6 | C7-cell-7 | C7-cell-8 |
| `z3` | Bank lending growth y/y | C7-cell-9 | C7-cell-10 | C7-cell-11 | C7-cell-12 |
| `z4` | Dollar-strength-inverse | C7-cell-13 | C7-cell-14 | C7-cell-15 | C7-cell-16 |
| `z5` | Funding stress | C7-cell-17 | C7-cell-18 | C7-cell-19 | C7-cell-20 |

Cells failing the §3.4 sample gate count as FAIL toward Criterion 7 (do NOT reduce the denominator). This preserves the pre-registered familywise alpha at 5%.

---

## §6 — Falsification window and re-test cadence

### §6.1 Sealing-to-verdict design

The v11.4 sprint runs the v2.0 analysis on the same data as v1.0 (no new data acquired). **The verdict is a sealed re-analysis of existing data plus prospective stability monitoring, not a fresh-OOS confirmation.**

OOS evaluation per §3.3 uses expanding-window logic; no separate held-out test set is reserved. A strict pre-registration purist would reserve a held-out window (e.g., 2027+ data only). v2.0 does not because: (i) the four amendments primarily revise methodology, not criterion targets; (ii) waiting 10 years for fresh 10Y-horizon data is prohibitive; (iii) v2.0 undergoes annual re-test per §6.2.

### §6.2 Annual re-test cadence

Starting **one calendar year after sealing**, the Strategist re-runs the v2.0 analysis with all newly-realized forward returns. If any criterion-level conclusion *reverses* at the 1Y or 3Y horizon, the verdict is downgraded to `UNSTABLE` and re-arbitrated.

#### §6.2.1 Idempotency and no-new-data handling

Re-test state keyed by `(retest_year, scheduled_date, data_cutoff, git_commit)` stored in `outputs/lc_v2_retest_state.json`. Re-test fires once when local date `≥ scheduled_date` AND no record for that `retest_year` exists. If no new realized 1Y/3Y returns exist or data fetch fails, write:
- `RETEST_SKIPPED_NO_NEW_DATA` — explicit, NOT `UNSTABLE`.
- `RETEST_BLOCKED_DATA_UNAVAILABLE` — explicit, NOT `UNSTABLE`.

### §6.3 Definitive falsification criterion

The v2.0 verdict is **DEFINITIVELY FALSIFIED** if any of the following holds at any annual re-test:

1. A 1Y- or 3Y-horizon criterion (C1, C2, C4, or C7) reverses pass/fail status.
2. The composite β sign reverses on `LC_FULL` at 1Y or 3Y horizon with `|t_NW| > 2.0`.
3. The Brier score of the skewed-t conditional forecast (§3.7) is worse than the Gaussian fallback at the 1Y horizon, measured over paired post-seal observations:
   - Define `event_1Y := r_{t, t+12} < 0`.
   - Compute `ΔBrier = E[Brier_skewed_t − Brier_Gaussian]` over paired post-seal forecasts.
   - Estimate `95% CI(ΔBrier)` via paired stationary block bootstrap with `block_length ≥ 12 months`.
   - Falsification triggers when `LB(95% CI ΔBrier) > 0 AND n_eff = floor(n_obs / 12) ≥ 10`.
   - If `n_eff < 10`, status is `PROVISIONAL` (no trigger).

### §6.4 Meta-finding on 3-of-3 pre-reg FAIL

If v2.0 closes FAIL, that is the third consecutive pre-reg FAIL on this project (v11.2.0-stat, v11.3.0 LC v1.0, v11.4 LC v2.0). The Strategist commits to writing a meta-DECISIONS entry documenting that 3-of-3 FAIL is itself informative, enumerating remaining-falsified vs unresolved claims, and recommending pivots.

---

## §7 — Display framing rules

Inherits v1.0 §12.2 (transcribed in §10.1): a FAIL verdict triggers `DIAGNOSTIC ONLY` display framing.

Per merge-to-main arbitration (option b′ with structured `RESEARCH_RECORD.md` at `buffet_indicator/docs/`):
- v2.0 PASS → eligible for merge to `main` with normal display framing.
- v2.0 FAIL → spec branch only; entry appended to `buffet_indicator/docs/RESEARCH_RECORD.md`.
- v2.0 UNSTABLE (at annual re-test) → reverted to spec branch with `unstable` tag.

---

## §8 — Pre-registration invariants (HARD GATE)

### §8.1 Immutable post-seal

The following are immutable post-seal:

1. The sealing commit hash (becomes ancestor-test target for every artifact write).
2. All numerical thresholds in §5 (Criteria 1–7), including `1.65` and `0.0025`.
3. **The binary decision rule `n_pass ≥ 4 of 7` in §2.1** (CORRECTED from DRAFT_v2's redundant two-tier).
4. The Hansen (1994) skewed-t family specification in §3.7 (specifically: standardized 2-parameter `eta_tail, lambda_skew`; L-BFGS-B with stated bounds; Gaussian fallback policy; correct `arch.SkewStudent.loglikelihood(params, resids, sigma2, individual=False)` signature).
5. The insufficient-sample gate `max(60, 3 × HAC_lag) OR n_eff < 30` in §3.4.
6. The HAC convention `lag = horizon_months − 1` in §3.5.
7. The 0.5/0.5 per-component priors in §4.1 (interpretive only).
8. The expanding-window OOS evaluation in §3.3 (no held-out window).
9. The annual re-test cadence and downgrade criteria in §6.
10. **`n_bootstrap = 50,000` TRULY IMMUTABLE for ALL verdict-bearing quantities** (no runtime-conditional downsampling — FIX per ChatGPT round-2 New-1 + Codex round-2 New-4).
11. The Brier comparison protocol in §6.3 bullet 3.
12. The canonical component IDs (`z1..z5`) per §1 and §4.1.
13. The `arch.bootstrap.optimal_block_length` column `"stationary"` per §3.8 (empirically verified against installed `arch==7.0.0`).

Any change requires a v2.1 pre-registration with new seal commit and a NEW sprint.

### §8.2 HARD GATE algorithm

Function `assert_prereg_ancestor(pre_reg_commit, *, sealed: bool, allow_preseal: bool = False, head: str = "HEAD") → None`:

```python
import subprocess
import logging

logger = logging.getLogger(__name__)

class HardGateViolation(RuntimeError): pass
class HardGateIndeterminate(RuntimeError): pass
class HardGateDisabled(RuntimeError): pass

def assert_prereg_ancestor(
    pre_reg_commit: str,
    *,
    sealed: bool,
    allow_preseal: bool = False,
    head: str = "HEAD",
) -> None:
    if not sealed:
        if not allow_preseal:
            raise HardGateDisabled(
                "Pre-seal artifact writes are disabled. "
                "Set allow_preseal=True only for the seal commit itself."
            )
        return

    # Check shallow-clone status
    shallow_check = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        capture_output=True, text=True, check=False,
    )
    if shallow_check.stdout.strip() == "true":
        unshallow = subprocess.run(
            ["git", "fetch", "--unshallow", "--tags"],
            capture_output=True, text=True, check=False,
        )
        if unshallow.returncode != 0:
            raise HardGateIndeterminate(
                f"Shallow clone cannot verify ancestor. "
                f"Run `git fetch --unshallow --tags` and retry. "
                f"pre_reg_commit={pre_reg_commit}"
            )

    # Ancestor check
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", pre_reg_commit, head],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 0:
        logger.info("HARD_GATE_PASS", extra={
            "pre_reg_commit": pre_reg_commit, "head": head,
        })
        return
    elif result.returncode == 1:
        raise HardGateViolation(
            f"pre_reg_commit {pre_reg_commit} is NOT an ancestor of {head}. "
            f"Artifact write refused."
        )
    else:
        raise HardGateIndeterminate(
            f"git merge-base returned exit code {result.returncode}: "
            f"{result.stderr.strip()}"
        )
```

Every artifact writer to `outputs/lc_v2_*`, `outputs/tables/lc_v2_*`, `outputs/figures/lc_v2_*`, `outputs/reports/lc_v2_*` MUST call `assert_prereg_ancestor(V2_SEAL_COMMIT, sealed=True)` immediately before the write. Per-write, not per-session.

---

## §9 — Open Strategist verification items — must resolve BEFORE seal (11 items, expanded from DRAFT_v2's 10)

Claude Code resolves all items as part of the seal sequence (see `DECISIONS_2026_05_24_v11_4_arbitration_ROUND_2.md` §3 for sub-tasks).

1. **v1.0 §12.2 display framing exact wording** — transcribe verbatim into §10.1.
2. **Composite scope construction (`LC_FULL`, `LC_TIER2`, `LC_DEEP`)** — transcribe definitions into §10.1.
3. **HAC_lag convention** — verify v1.0 used `lag = horizon_months − 1`. Transcribe v1.0 clause into §10.1.
4. **Component definition unchanged from v1.0** — transcribe component definitions and weights into §10.1 (component IDs `z1..z5` per §1 above).
5. **Realized v1.0 `n_obs_oos` by composite × horizon** — extract via `git show spec/liquidity-composite-v1.0:buffet_indicator/outputs/lc_v1_verdict.json` (or recompute from `outputs/model_scores.parquet`). Document in §10.3.
6. **Amendment source file hash and four-row amendment mapping table** — verify SHA-256 and ancestor-of-seal-commit. Transcribe four amendments into §10.1.
7. **Exact v1.0 OOS training-set timing** — transcribe v1.0's training-set timing clause into §10.1.
8. **§8.1 invariants completeness** — verify 13-item list above is complete.
9. **Criterion 7 multiplicity 20-cell enumeration** — verify §5.3 corresponds to cells actually tested in v1.0 implementation.
10. **Criterion 5 ADF multiplicity rule** — verify §5.2 Holm-Šidák consistent with v1.0; document as v1.0→v2.0 delta in §10.2 if changed.
11. **Cross-platform seal-helper compatibility** (per Codex round-2 New-9) — verify seal-time commands work on both Unix and Windows (`Get-FileHash`/`sha256sum`, `ConvertFrom-Json`/`jq`); see DECISIONS round-2 §4 for canonical commands.

---

## §10 — v2.0 deltas from v1.0 (UPDATED — decision rule revert)

### §10.1 Inherited from v1.0 verbatim (Claude Code transcribes at seal time)

- **Composite scope definitions** (`LC_FULL`, `LC_TIER2`, `LC_DEEP`) — verbatim from v1.0 §1.2 (commit `a8635ef`):

| Scope | Components active | Effective monthly start | Reason |
|---|---|---|---|
| **LC_FULL** | All 5 (z₁ + z₂ + z₃ + z₄ + z₅) | 2003-01 | NetFed (WALCL) starts 2002-12 → 12-mo warm-up → 2003-12 valid first composite; pragmatically anchored at 2003-01 with NetFed partially warming up |
| **LC_TIER2** | Drops z₁; renormalized {z₂ z₃ z₄ z₅} weights | 1987-01 | Funding (TED) starts 1986-01 → 12-mo warm-up → 1987-01 first valid |
| **LC_DEEP** | Drops z₁ AND z₅; renormalized {z₂ z₃ z₄} | 1973-01 | BankLend (TOTLL) starts 1973-01 (BUSLOANS earlier); 12-mo warm-up → 1974-01 first valid; pragmatically 1973-01 |

LC_TIER2 renormalized weights: 0.267, 0.267, 0.267, −0.200.
LC_DEEP renormalized weights: 0.333, 0.333, 0.333.
- **Component construction (canonical IDs match v1.0)**:
  - `z1` NetFed — verbatim from v1.0 §1.1 z₁: `NetFed = WALCL − WDTGAL − RRPONTSYD` (monthly aggregate); weight +0.25 in LC_FULL; expected sign on equity returns: +.
  - `z2` M2 growth y/y — verbatim from v1.0 §1.1 z₂: `M2_growth_yoy = (M2SL_t / M2SL_{t−12}) − 1`; weight +0.20 in LC_FULL; expected sign: +.
  - `z3` Bank lending growth y/y (BUSLOANS→TOTLL) — verbatim from v1.0 §1.1 z₃ + §1.3: `BankLend_growth_yoy = (BankLend_t / BankLend_{t−12}) − 1`, spliced BUSLOANS↔TOTLL @ 1973-01-03 in YoY growth-rate space (additive constant `c`, validation gates `corr > 0.50` and `abs(c) < 0.05`); weight +0.20 in LC_FULL; expected sign: +.
  - `z4` DXY inverse — verbatim from v1.0 §1.1 z₄ + §1.3: `DXY⁻¹ = −z(log DXY)`, spliced ICE DXY ↔ DTWEXBGS @ 2006-01-04 in log-levels space (additive constant `c`, validation gates `corr > 0.85` and `mean abs z-divergence < 0.30`); weight +0.20 in LC_FULL; expected sign: +.
  - `z5` Funding stress (TED→SOFR-IORB) — verbatim from v1.0 §1.1 z₅ + §1.3: `Funding_stress`, spliced TED ↔ SOFR−IORB @ 2022-01-22 via z-score linear-blend transition (2022-02 → 2023-04, validation gate `abs(funding_z.diff().max()) < 1.5σ`); pre-step IOER→IORB level concat @ 2021-07-29 (no splice; gate `abs(IOER@2021-07-28 − IORB@2021-07-29) < 0.01pp`); weight −0.15 in LC_FULL; expected sign: + on liquidity (since stress enters with negative weight).
- **Z-score definition** (expanding-window, PIT-compliant) — verbatim from v1.0 §1.4: expanding window, mean + sample SD (Bessel n−1), strict PIT excluding current observation; minimum sample threshold `n ≥ 120` observations before non-NaN z; all components brought to month-end-of-month frequency before z-scoring; real-time vintages (ALFRED) for revisable series M2SL, BUSLOANS, TOTLL, WALCL, WDTGAL.
- **Composite weighting scheme** (equal-weight by default + robustness) — verbatim from v1.0 §1.1 + §1.2: LC_FULL weights z₁ +0.25, z₂ +0.20, z₃ +0.20, z₄ +0.20, z₅ −0.15 (sum of absolute weights = 1.00 = 0.25 + 0.20·3 + 0.15); LC_TIER2 renormalized {0.267, 0.267, 0.267, −0.200}; LC_DEEP renormalized {0.333, 0.333, 0.333}. Robustness alternatives per v1.0 §3.7 (Bai-Perron breaks on rolling β) and v1.0 §3.4 (Goyal-Welch OOS R² cross-validation).
- **Forward-return definition** (SPXTR monthly) — verbatim from v1.0 §3.1: `r_{t, t+h} = α + β · LC_t + ε_{t, t+h}` where `r_{t, t+h}` = forward h-year total return of S&P 500 (annualized log return); total-return source `SP_SPXTR_1D.csv` (post-1988) spliced with Shiller dividend-reinvested column (pre-1988) at 1988-01-04 with multiplicative scale anchor; horizons {1Y, 3Y, 5Y, 10Y} (4 horizons).
- **Stambaugh (1999) implementation formula** — verbatim from v1.0 §3.3 (per Strategist Q2 arbitration: v1.0 references method by citation; analytical formula is canonical Stambaugh 1999):
  - **Stambaugh (1999)** analytical correction for persistent regressor.
  - Also report bootstrap-corrected β via 10K stationary bootstrap as cross-check.
- **Campbell-Yogo simplified critical-value grid** — verbatim from v1.0 §3.4 (per Strategist Q3 arbitration: v1.0 references method by citation; Table 5 critical values are published in Campbell-Yogo 2006): **Campbell-Yogo (2006)** CIs when regressor is near-unit-root (ρ > 0.95).
- **v1.0 §12.2 display framing wording** — verbatim from v1.0 §2 (per Strategist Q4 arbitration):

  > **Decision rule** (per spec §12.2):
  > - `n_pass ≥ 5` → **PASS** — headline LC tab promoted prominently.
  > - `n_pass == 4` → **PASS_WITH_CAVEATS** — headline LC tab with disclosure card.
  > - `n_pass ≤ 3` → **FAIL** — DIAGNOSTIC ONLY view, no actionable conviction/probability.
  >
  > In all cases, the pipeline still runs; the verdict affects dashboard framing only.

  **§10.1 transcription note** (Strategist-authorized per `PROMPT_CC_v11_4_seal_PHASE3_RESUME.md` §4): DRAFT_v4 §2.1 binary verdict (PASS ⇔ `n_pass ≥ 4`) is the collapse of v1.0's 3-tier display framing above into Not-FAIL vs FAIL. DRAFT_v4 §7 ("Display framing rules") inherits the 3-tier wording verbatim for dashboard display; the verdict JSON's binary `verdict: "PASS" | "FAIL"` field corresponds to v1.0's `n_pass ≥ 4` (i.e., PASS OR PASS_WITH_CAVEATS) vs `n_pass ≤ 3` (FAIL). The two representations are consistent.

### §10.2 Explicit deltas (v1.0 → v2.0)

| Clause | v1.0 value | v2.0 value | Source authority |
|---|---|---|---|
| Conditional forecast distribution | Gaussian | Hansen (1994) standardized skewed-t (`arch.SkewStudent`) with Gaussian fallback | Amendment 3 |
| Criterion 4 wording | `t_NW > 1.65 AND β > 0` (one-sided 5%) | `\|t_NW\| > 1.65` (two-sided 10% screen) | Amendment 2 |
| Component sign priors | (implicit, asymmetric per literature) | 0.5/0.5 BMA equipoise on all 5 | Amendment 1 |
| Insufficient-sample gate | `n_obs_insample < 5 × HAC_lag` (per amendments file) | `n_obs_oos < max(60, 3 × HAC_lag) OR n_eff < 30` | Amendment 4 + round-1 ChatGPT BLOCKER #2 |
| HAC lag formula (cosmetic restatement) | `lag = h * 12 − 1` (h years) | `lag = horizon_months − 1` (equivalent) | Codex round-1 MAJOR #3 (restate, not change) |
| n_bootstrap | (v1.0: variable) | 50,000 fixed | Master spec §3.6 |
| Verdict JSON state representation | ad-hoc flags | 5-state enum + UNSTABLE retest status (§12) | Codex round-1 MINOR #9 + round-2 New-6 |

**Note**: DRAFT_v2 proposed a "decision rule" delta (two-tier `n_pass ≥ 4 AND n_pass_predictive ≥ 2`) which was withdrawn in DRAFT_v3 per ChatGPT round-2 #6. v2.0 inherits v1.0's plain `n_pass ≥ 4 of 7` rule unchanged per §2.1 — no decision-rule delta exists in v2.0.

### §10.3 Realized v1.0 sample-count audit

Claude Code fills at seal time via `git show spec/liquidity-composite-v1.0:...`:

| Composite | Horizon | v1.0 `n_obs_oos` (or recomputed) | v2.0 gate min | v2.0 gate status | v1.0 verdict status |
|---|---|---|---|---|---|
| LC_FULL | 1Y | `150_insample (oos_split: 2013-01-01; n_obs_oos recomp deferred to §11.1)` | 60 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `C4.realized_1y: t=-0.254, p_1sided=0.3999, sign=negative` |
| LC_FULL | 3Y | `126_insample (oos_split: 2013-01-01; n_obs_oos recomp deferred to §11.1)` | 105 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `C4.realized_3y: t=-3.076, p_1sided=0.0013, sign=negative` |
| LC_FULL | 5Y | `102_insample (oos_split: 2013-01-01; n_obs_oos recomp deferred to §11.1)` | 177 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `C4.realized_5y: t=0.388, p_1sided=0.3493, sign=positive_but_t_below_threshold` |
| LC_FULL | 10Y | `42_insample (oos_split: 2013-01-01; n_obs_oos recomp deferred to §11.1)` | 357 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` (likely `not_evaluable`) | `C4.realized_10y: t=-17.622, n_obs_insample=42, flag=insufficient_sample` |
| LC_TIER2 | 1Y | `353_insample (oos_split: 2011-01-01; n_obs_oos recomp deferred to §11.1)` | 60 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `C1: realized=-0.0167, threshold=0.005, pass=false` |
| LC_TIER2 | 3Y | `329_insample (oos_split: 2011-01-01; n_obs_oos recomp deferred to §11.1)` | 105 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `C2: realized=-0.0028, threshold=0.020, pass=false` |
| LC_TIER2 | 5Y | `305_insample (oos_split: 2011-01-01; n_obs_oos recomp deferred to §11.1)` | 177 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `C3: realized=-0.0602, threshold=0.040, pass=false` |
| LC_TIER2 | 10Y | `245_insample (oos_split: 2011-01-01; n_obs_oos recomp deferred to §11.1)` | 357 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `<no v1.0 criterion>` |
| LC_DEEP | 1Y | `533_insample (oos_split: 2011-01-01; n_obs_oos recomp deferred to §11.1)` | 60 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `<no v1.0 criterion>` |
| LC_DEEP | 3Y | `509_insample (oos_split: 2011-01-01; n_obs_oos recomp deferred to §11.1)` | 105 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `<no v1.0 criterion>` |
| LC_DEEP | 5Y | `485_insample (oos_split: 2011-01-01; n_obs_oos recomp deferred to §11.1)` | 177 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `<no v1.0 criterion>` |
| LC_DEEP | 10Y | `425_insample (oos_split: 2011-01-01; n_obs_oos recomp deferred to §11.1)` | 357 | `<NOT_EVALUABLE_WITHOUT_OOS_N>` | `<no v1.0 criterion>` |

**§10.3 transcription note** (Strategist-authorized per `PROMPT_CC_v11_4_seal_PHASE4_RESUME.md` §1.4 — Path D refined):

The §10.3 audit table is descriptive (not verdict-binding) and documents the v1.0 → v2.0 metric-basis change. Three documented limitations:

1. **`n_obs_oos` vs `n_obs_insample`**: v1.0 sealed pre-reg and verdict.json reported sample counts on an in-sample basis (`n_obs_insample` from `outputs/tables/lc_v1_predictive_regression.csv`); v2.0 §3.4 gate uses an OOS basis (`n_obs_oos`). The column 3 values are v1.0's in-sample counts with the `_insample` suffix and `oos_split_date` annotation. True per-cell `n_obs_oos` recomputation is deferred to v2.0 sprint's `collect_v1_realized_sample_counts(ref="spec/liquidity-composite-v1.0")` per §11.1. Because `n_obs_insample` is always ≥ `n_obs_oos` for the same cell, applying the v2.0 gate to the proxy would systematically overstate evaluability; column 5 therefore reads `<NOT_EVALUABLE_WITHOUT_OOS_N>` rather than a computed-on-proxy flag.

2. **Criterion-vs-cell schema mismatch**: v1.0's scorecard is organized by criterion (7 entries), not by (composite × horizon) (12 cells). Only 3 cells (LC_TIER2 × {1Y, 3Y, 5Y}) have a direct criterion-level pass/fail mapping (C1, C2, C3). The 4 LC_FULL cells map to C4 sub-objects with per-horizon t/p/sign info. The remaining 5 cells (LC_TIER2 × 10Y + LC_DEEP × all 4 horizons) have no v1.0 criterion entry and column 6 reads `<no v1.0 criterion>`.

3. **Amendment 4 structural consequence (observation only — not a §10.3 deliverable)**: under v2.0's stricter OOS gate `n_obs_oos < max(60, 3 × HAC_lag)`, cells with `oos_split_date` close to end-of-sample at long horizons (especially 5Y and 10Y) likely render `not_evaluable` even if v1.0 reported them as in-sample-evaluable. This is the documented consequence of Amendment 4's metric-basis switch. The v2.0 sprint's actual verdict will reflect this; §10.3 deliberately does not pre-compute it to avoid binding the v2.0 verdict at seal time.


---

## §11 — Acceptance test matrix and performance budget (EXPANDED per Codex round-2)

### §11.1 Required public functions

```python
def compute_hac_lag(horizon_months: int) -> int: ...
def sample_gate_status(n_obs_oos: int, hac_lag: int, n_eff: float) -> Literal["evaluable", "not_evaluable"]: ...
def fit_conditional_skew_t(residuals: np.ndarray, *, seed: int) -> SkewTFitResult: ...
def run_predictive_regression_v2(x, y, *, horizon_months: int, forecast_origin: pd.Timestamp) -> RegressionResult: ...
def stationary_bootstrap_ci(data, *, n_bootstrap: int, seed: int) -> BootstrapResult: ...
def evaluate_v2_criteria(panel: pd.DataFrame) -> VerdictResult: ...
def assert_prereg_ancestor(pre_reg_commit: str, *, sealed: bool, allow_preseal: bool = False, head: str = "HEAD") -> None: ...
def annual_retest_status(today: date, state: RetestState, data: pd.DataFrame) -> RetestResult: ...
def compare_threshold(value: float, op: str, threshold: float, *, on_nan: str = "fail") -> bool: ...
def collect_v1_realized_sample_counts(ref: str = "spec/liquidity-composite-v1.0") -> pd.DataFrame: ...
def parse_component_id_map(spec_path: str) -> dict: ...
def should_apply_stambaugh(rho: float) -> bool: ...
def choose_stationary_block_length(x: np.ndarray) -> int: ...
def load_bootstrap_policy() -> BootstrapPolicy: ...
def collect_seal_metadata_with_python_helpers() -> dict: ...
```

### §11.2 Required acceptance tests (21 test IDs — EXPANDED through round-2 and round-3)

| Test ID | Purpose | Boundary checked |
|---|---|---|
| `test_compute_hac_lag_uses_v1_formula` | HAC lag = horizon_months − 1 | h=12→11, h=120→119 |
| `test_sample_gate_boundary_basic` | Strict `<` in §3.4 | n_obs_oos=60, hac_lag=11 → evaluable; n_obs_oos=59 → not_evaluable |
| `test_sample_gate_boundaries_include_hac_and_neff` (NEW per Codex round-2 New-8) | High-HAC + n_eff boundaries | n_obs_oos=105, hac_lag=35, n_eff=30.0 → evaluable; 104 → not; n_eff=29.999 → not |
| `test_predictive_regression_uses_statsmodels_hac` | NW with use_correction=True | HAC_kwds set correctly |
| `test_oos_rows_counted_after_realization` | s + h ≤ t rule | Synthetic panel, expected count |
| `test_skewstudent_loglikelihood_signature_is_used_correctly` (NEW per Codex round-2 New-1) | Correct arch API: `loglikelihood(parameters, resids, sigma2)` | No `TypeError`; finite likelihood |
| `test_skewed_t_known_distribution_and_fallback` (with explicit tolerance per Codex round-3 New-3) | Hansen 1994 fit + fallback | `seed=42`, `size=500` standard_t df=5 standardized → `3.0 ≤ eta_tail_hat ≤ 8.0` AND `\|lambda_skew_hat\| ≤ 0.15` (interval calibrated to Codex's empirical run: `eta_tail≈4.2542`, `lambda≈-0.0427`); degenerate residuals → `gaussian_fallback` |
| `test_optimal_block_length_uses_arch_stationary_column` (CORRECTED per Codex round-3 New-1) | Correct column `"stationary"` against installed `arch==7.0.0` | Real arch import + `obl = arch.bootstrap.optimal_block_length(np.arange(100.0))`; assert `"stationary" in obl.columns AND "circular" in obl.columns`; `choose_stationary_block_length(np.arange(100.0)) == int(np.ceil(obl["stationary"].iloc[0]))` |
| `test_stationary_bootstrap_is_byte_identical` | Determinism with SeedSequence | Two runs same seed → identical |
| `test_stambaugh_exact_boundary_not_applied` (NEW per Codex round-2 New-5) | Strict `>` at ρ̂=0.85 | `should_apply_stambaugh(0.85) is False`; `nextafter(0.85, 1.0) is True` |
| `test_campbell_yogo_status_never_silent_nan` | Status enum always set | rho=0.99 → computed_v1_grid or not_evaluable_outside_grid |
| `test_all_seven_criteria_known_pass_and_fail` | Verdict logic | Synthetic all-pass / all-fail fixtures |
| `test_criterion_4_strict_t_boundary` | t=1.65 → FAIL; t=1.6501 → PASS | Strict `>` |
| `test_bonferroni_denominator_is_20` | α/20 = 0.0025 | 5 components × 4 horizons |
| `test_hard_gate_handles_ancestor_detached_preseal_and_shallow` | HardGateViolation, HardGateIndeterminate raised | Synthetic git fixture (preseal, shallow, detached) |
| `test_annual_retest_fires_once_per_year` | Idempotency | Date trigger, no-new-data handling |
| `test_retest_unstable_verdict_is_schema_valid` (NEW per Codex round-2 New-6) | `UNSTABLE` schema-valid | Reversal fixture → schema validates |
| `test_prereg_component_id_map_matches_v1_sealed_catalog` (NEW per Codex round-2 New-2) | z1..z5 == v1.0 catalog | Parse spec, assert match `{z1:netfed, z2:m2_growth_yoy, z3:banklend_growth_yoy, z4:dxy_inverse, z5:funding_stress}` |
| `test_bootstrap_count_policy_is_not_runtime_dependent` (NEW per Codex round-2 New-4) | 50K immutable | `policy.verdict_count == 50_000`; no "runtime_exceeded" reason permitted |
| `test_sealed_prereg_contains_no_unresolved_placeholders` (NEW per Codex round-2 New-7) | Seal-blocking | No `<VERIFIED_BY_CLAUDE_CODE>`, `<TRANSCRIBE_FROM_V1>`, `<TRANSCRIBE>`, `<COMPUTE>`, `<TO_BE_FILLED_BY_CLAUDE_CODE_AT_SEAL_TIME>` remain in sealed text |
| `test_seal_helpers_do_not_require_unix_only_tools` (NEW per Codex round-2 New-9) | Cross-platform seal | No `jq`/`sha256sum` dependency; Python helpers work |

### §11.3 Performance budget (REVISED — no downsample exception per ChatGPT round-2 New-1)

| Operation | Wall-clock ceiling | RAM ceiling |
|---|---|---|
| Canonical full-sample v2.0 run (12 cells × all criteria + 50K bootstrap) | ≤ 120 minutes on 2020-class laptop | ≤ 4 GB peak |
| Annual re-test (incremental, post-seal) | ≤ 20 minutes | ≤ 2 GB peak |
| Skewed-t ML fits (up to 5,760 if per-test-date) | Cached or fit once per training-endpoint actually used; raw 5,760-fit run forbidden absent explicit `--allow-uncached-skewt` flag | — |
| Bootstrap (50K reps × 12 canonical cells) | ≤ 60 minutes (parallelizable via `joblib`) | — |

**Critical: `n_bootstrap = 50,000` is IMMUTABLE for ALL verdict-bearing quantities (§8.1 invariant #10).** DRAFT_v2 allowed 10K downsample under runtime pressure; DRAFT_v3 removes this option entirely. If runtime budget exceeded:
- Claude Code MUST cache, parallelize, or invoke `--allow-uncached-skewt` flag.
- If still exceeded, the run produces `BLOCKED_PERFORMANCE_BUDGET` status — NOT a downsampled CI.
- Diagnostic-only non-verdict outputs (separate label, separate path) may use lower bootstrap counts but MUST NOT be cited in any criterion-bearing or CI-bearing artifact.

---

## §12 — Verdict JSON schema (EXTENDED per Codex round-2 New-6 — UNSTABLE state)

```json
{
  "schema_version": "v2.0",
  "verdict": "PASS" | "FAIL" | "UNSTABLE",
  "evidence_status": "NORMAL" | "NO_EVALUABLE_CRITERIA" | "MIXED",
  "retest_status": "NOT_APPLICABLE" | "STABLE" | "UNSTABLE" | "RETEST_SKIPPED_NO_NEW_DATA" | "RETEST_BLOCKED_DATA_UNAVAILABLE",
  "pre_reg_commit": "<SEAL_COMMIT_HASH>",
  "data_cutoff": "<ISO_DATE>",
  "run_timestamp": "<ISO_DATETIME_UTC>",
  "git_head": "<COMMIT_HASH>",
  "n_pass_total": <int 0..7>,
  "n_pass_predictive": <int 0..5>,
  "component_id_map": {
    "z1": "netfed_liquidity",
    "z2": "m2_growth_yoy",
    "z3": "banklend_growth_yoy",
    "z4": "dxy_inverse",
    "z5": "funding_stress"
  },
  "criteria": [
    {
      "criterion_id": "C1",
      "label": "OOS R² @ 1Y on LC_TIER2 > 0.005",
      "predictive": true,
      "status": "PASS" | "FAIL_STATISTICAL" | "NOT_EVALUABLE_COUNTED_FAIL" | "UNDEFINED_ALL_NOT_EVALUABLE",
      "counted_as": "PASS" | "FAIL",
      "value": <float or null>,
      "threshold": 0.005,
      "operator": ">",
      "cells": [
        {
          "composite": "LC_TIER2",
          "horizon_months": 12,
          "n_obs_oos": <int>,
          "hac_lag": 11,
          "min_required_n_obs": 60,
          "n_eff": <float>,
          "evaluable": <bool>,
          "feature_vintage_max": "<ISO_DATE>",
          "train_cutoff_inclusive": "<ISO_DATE>",
          "score_date": "<ISO_DATE>",
          "distribution_family": "skewed_t" | "gaussian_fallback",
          "fallback_reason": <string or null>,
          "skewt_eta_tail": <float or null>,
          "skewt_lambda_skew": <float or null>,
          "loglikelihood_at_optimum": <float or null>,
          "regression": {
            "beta": <float>,
            "t_nw": <float>,
            "p_nw": <float>,
            "stambaugh_status": "computed" | "not_evaluable_rho_boundary" | "not_applied",
            "campbell_yogo_status": "computed_v1_grid" | "not_evaluable_outside_grid",
            "rho_ar1": <float>
          },
          "bootstrap": {
            "ci_lower": <float>,
            "ci_upper": <float>,
            "n_bootstrap_used": 50000,
            "block_length": <int>,
            "block_length_source": "stationary_optimal" | "fallback_2_n_third_root",
            "seed_hex": "<HEX_FROM_SEEDSEQUENCE>"
          }
        }
      ]
    }
  ],
  "decision_rule_check": {
    "rule": "n_pass >= 4 of 7",
    "total_passed": true | false,
    "verdict_logic_chain": "<HUMAN_READABLE>"
  },
  "look_ahead_audit": {
    "all_cells_pit_compliant": true,
    "violations": []
  }
}
```

`evidence_status`:
- `NORMAL` — at least one criterion is `PASS` or `FAIL_STATISTICAL`.
- `NO_EVALUABLE_CRITERIA` — all 7 criteria are `NOT_EVALUABLE_COUNTED_FAIL`.
- `MIXED` — some criteria `PASS`/`FAIL_STATISTICAL`, others `NOT_EVALUABLE_COUNTED_FAIL`.

`verdict = UNSTABLE` arises only from annual re-test reversal (§6.2); initial sprint produces only `PASS` or `FAIL`. The same `outputs/lc_v2_verdict.json` schema is reused for re-test outputs with the addition of `retest_status` populated.

---

## §13 — Security and artifact redaction

### §13.1 Secret-handling invariants

- FRED, ALFRED, GitHub, Norgate, Hugging Face, and dashboard deployment tokens MUST NEVER be serialized into pre-reg, verdict, research, or diagnostic artifacts.
- `buffet_indicator/config.yaml` and `.env` remain in `.gitignore` per master spec §1.6.4.
- Data-fetch code reads secrets only from environment variables or git-ignored config.

### §13.2 Artifact redaction policy

Before any auto-commit/push, artifact writers MUST scan output for patterns matching:

```regex
api[_-]?key[\s=:]+[A-Za-z0-9_\-]{16,}
token[\s=:]+[A-Za-z0-9_\-]{16,}
ghp_[A-Za-z0-9]{20,}
://[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+@
[\?&]token=[A-Za-z0-9_\-]+
```

Matches abort the commit with `SecretLeakPrevented` error. Fixtures use `FRED_API_KEY_EXAMPLE_REDACTED` placeholder.

### §13.3 Subprocess and deserialization safety

- All subprocess invocations use argument lists, never `shell=True` with user-controlled paths.
- Parquet, JSON, YAML deserialization uses structured parsers (`pyarrow`, `json`, `yaml.safe_load`) — never `pickle.load` on untrusted bytes.
- `eval`/`exec` on dynamic content forbidden.

### §13.4 Out-of-scope

The existing `.github/workflows/deploy.yml` uses `git push --force` to Hugging Face Space — inherited from prior sprints, NOT changed by v11.4. v11.4 implementation MUST NOT copy this force-push pattern to spec-branch seal automation.

---

## §14 — References

- Adrian, T., & Boyarchenko, N. (2012/2015). FRBNY Staff Report No. 567.
- Andrews, D. W. K. (1991). *Econometrica*.
- Campbell, J. Y., & Yogo, M. (2006). *JFE*.
- Fama, E. F., & French, K. R. (1988). *JFE*.
- Goyal, A., & Welch, I. (2008). *RFS*.
- Hansen, B. E. (1994). *IER*.
- Hansen, L. P., & Hodrick, R. J. (1980). *JPE*.
- Munafò, M. R., et al. (2017). *Nature Human Behaviour*.
- Newey, W. K., & West, K. D. (1987). *Econometrica*.
- Politis, D. N., & Romano, J. P. (1994). *JASA*.
- Politis, D. N., & White, H. (2004); Patton-Politis-White (2009).
- Schularick, M., & Taylor, A. M. (2012). *AER*.
- Stambaugh, R. F. (1999). *JFE*.

---

## §15 — Appendix: literature-tilt sensitivity (descriptive, not verdict-affecting)

(Filled at run time per §4.3. Reports criteria evaluated under asymmetric priors per literature tilts. Does NOT affect deterministic verdict.)

---

**End of DRAFT_v4. Narrow round-4 verification per `REVIEW_REQUEST_ChatGPT55Pro_v11_4_ROUND_4.md` and `REVIEW_REQUEST_Codex_v11_4_ROUND_4.md`.**
