# DIAGNOSTIC ONLY VIEW — v2.0 Liquidity Composite (v11.4 sprint FAIL)

> **Display framing**: sealed pre-reg §7 inherits v1.0 §12.2 — a FAIL verdict (`n_pass ≤ 3`) triggers DIAGNOSTIC ONLY display with no actionable conviction, probability, or signal interpretation.

**Generated**: 2026-05-25T20:58:09Z (verdict run timestamp)

---

## DO NOT INTERPRET AS PREDICTIVE SIGNAL

This view is presented per sealed pre-registration §7 as **DIAGNOSTIC ONLY**.  
The v2.0 Liquidity Composite **did NOT pass** the sealed pre-registered evaluation.  
Any pattern visible in this view is shown for methodological transparency only.  
Treating the numerical contents as an actionable trading signal violates the pre-registered methodology and basic statistical principle.

---

## Verdict

- **Outcome**: `FAIL`
- **Decision rule**: `n_pass >= 4 of 7` (sealed §2.1)
- **n_pass_total**: `1 / 7`
- **n_pass_predictive**: `0 / 5` (transparency field; not a gate)
- **evidence_status**: `MIXED`
- **data_cutoff**: `2026-03-31`

## Per-criterion status

| # | Criterion | Status | Value | Predictive? |
|---|---|---|---|---|
| C1 | OOS R² @ 1Y on LC_TIER2 > 0.005 | `NOT_EVALUABLE_COUNTED_FAIL` | — (`> 0.005`) | yes |
| C2 | OOS R² @ 3Y on LC_TIER2 > 0.020 | `NOT_EVALUABLE_COUNTED_FAIL` | — (`> 0.02`) | yes |
| C3 | OOS R² @ 5Y on LC_TIER2 > 0.040 | `NOT_EVALUABLE_COUNTED_FAIL` | — (`> 0.04`) | yes |
| C4 | LC_FULL \|t_NW\| > 1.65 at any evaluable horizon (Amendment 2 two-sided) | `NOT_EVALUABLE_COUNTED_FAIL` | — (`> 1.65`) | yes |
| C5 | ADF rejects null for all 5 components at Holm-Šidák α=0.05 | `FAIL_STATISTICAL` | 0.764779 (`< 0.05`) | no |
| C6 | max VIF across 5 components < 5.0 | `PASS` | 1.69506 (`< 5`) | no |
| C7 | any (component x horizon) cell has Bonferroni p < α/20 = 0.0025 (denominator=20) | `NOT_EVALUABLE_COUNTED_FAIL` | — (`< 0.0025`) | yes |

## Failure mode diagnosis

Two failure modes were diagnosed in the v2.0 verdict:

**Mode A — data-window-vs-strict-gate interaction (C1, C2, C3, C4, C7)**. z4 (DXY) is bottlenecked to ~2016-01 because the v2.0 master archive lacks pre-2006 ICE_DXY, and the sealed §10.1 PIT z-score requires 120 monthly observations. Combined with the sealed §3.4 / Amendment 4 strict insufficient-sample gate (`n_obs_oos >= max(60, 3 * HAC_lag)` AND `n_eff >= 30`), most cells did not clear the gate at any horizon, yielding `NOT_EVALUABLE_COUNTED_FAIL` for the four predictive criteria and C7.

**Mode B — z4 (DXY) near-unit-root level (C5)**. The DXY broad-trade-weighted log-level (post-splice, pre-z-score) does not reject the unit-root null at conventional levels (max ADF p ≈ 0.7648 across the five components). The level-family transformation drives the Holm-Šidák multiplicity test to fail, resulting in `FAIL_STATISTICAL` for C5.

**C6 (VIF) PASSED.** Components are not problematically collinear (max VIF ≈ 1.70 across the 5 aligned z-scored components). This is the only criterion that passed the v2.0 sealed evaluation.

## Audit summary

- **PIT look-ahead audit**: `PASS` (n_cells_audited=12, n_origins_audited=756, n_violations=0). Construction: `per_origin_non_tautological_F_BLK1_A` (Phase F-BLK1.A populates per-origin `feature_vintage_max`; Phase F-BLK1.B audit iterates `(origin, cell)` pairs and asserts `fvm[t] <= t`).
- **Sealed pre-reg integrity**: PASS — SHA-256 immutable at `c3c3ec1a83e4…`.
- **Verdict JSON byte-reproducibility**: PASS — Phase F-BLK1.F binary-mode write + LF-newlines + read-back verification; sidecar matches `sha256sum` cross-OS.
- **Pinned-environment closeout reproducibility**: PASS — Phase F-DOC.C normalized SHA equality between off-pin BLK-1 and pinned closeout re-run.
- **§16 seal-report criteria**: 10/10 PASS (no regression across the sprint).

---

## RESTATING — DO NOT INTERPRET AS PREDICTIVE SIGNAL

This diagnostic view exists for:

1. **Methodological transparency** — every cell, criterion, gate, audit decision is disclosed.
2. **Audit trail completeness** — pre-BLK-1 historical verdict + post-BLK-1 canonical + closeout pinned re-run all preserved.
3. **Public scientific record** — the FAIL outcome itself is the empirical finding.

This diagnostic view does NOT exist for:

1. Investment decisions
2. Position sizing
3. Signal extraction of any kind

The v2.0 Liquidity Composite **FAILED** the sealed pre-registered evaluation. That is the empirical finding. The numerical contents of this report are evidence FOR the FAIL outcome and provide diagnostic information about WHY the failure occurred, but do NOT constitute a usable signal.

---

## Provenance

- Canonical verdict JSON: `outputs/lc_v2_verdict.json`
- Verdict JSON sidecar SHA-256: `outputs/lc_v2_verdict.json.sha256` (sha256sum-compatible format)
- Sealed pre-reg: `specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` SHA-256 `c3c3ec1a83e4cb9c…`
- Pre-BLK-1 archived verdict: `outputs/historical/lc_v2_verdict_pre_blk1.json`
- BLK-1 delta analysis: `outputs/lc_v2_verdict_blk1_delta.md`
- Closeout re-run delta: `outputs/lc_v2_verdict_closeout_delta.md`
- Phase F-DOC directive: `prompt/052526/PROMPT_CC_v11_4_phase_F_DOC.md`
- Phase F-BLK1 directive: `prompt/052526/PROMPT_CC_v11_4_phase_F_BLK1_fix.md`

