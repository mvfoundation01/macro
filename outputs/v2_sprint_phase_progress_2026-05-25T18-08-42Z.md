# v2.0 sprint Phase E progress — VERDICT-BEARING RUN

**Timestamp**: 2026-05-25T18:08:42Z
**Session**: Phase E (verdict JSON writer + verdict-bearing run)
**Starting HEAD**: `6e00ca1` (Phase D progress report committed)
**Ending HEAD**: `9759146` (verdict JSON + sidecar committed)
**Commits this session**: 4
**Pushed**: 4 (all to `origin/spec/liquidity-composite-v2.0`)

---

## Phases completed

| Phase | Status | Commit | Notes |
|---|---|---|---|
| E.1 — Panel construction | **PASS** | `eafaab6` | 12 candidate cells; 5 PIT z-scored components; LC_FULL/LC_TIER2/LC_DEEP composites; SPXTR+Shiller spliced forward returns |
| E.2 — Regression sweep | **PASS** | `f3659a3` | 12 cells regressed via `run_predictive_regression_v2`; conditional skewed-t fits + stationary block bootstrap (n=50,000) on β per evaluable cell |
| E.3 — C5/C6/C7 diagnostics | **PASS** | `f3659a3` | ADF on 5 raw components (autolag=AIC, regression='c'); VIF on aligned z-score panel; Bonferroni sweep over 20 (component × horizon) cells |
| E.4 — Criteria evaluation | **PASS** | `9759146` | 7-criterion composition per sealed §5 + §12; binary verdict per §2.1; evidence_status per §12 |
| E.5 — Verdict JSON write | **PASS** | `9759146` | `outputs/lc_v2_verdict.json` written per sealed §12 schema; SHA-256 sidecar |
| E.6 — PIT audit | **PASS** | `9759146` | 0 violations (strict-shift PIT z-score makes invariant true by construction) |
| E.7 — Summary + progress | **PASS** | (this commit) | `outputs/lc_v2_verdict_summary.md` + this report |

---

## **HEADLINE OUTCOME**

| Field | Value |
|---|---|
| **Verdict** | **FAIL** |
| **n_pass_total** | **1 / 7** |
| **n_pass_predictive** | **0 / 5** |
| **evidence_status** | **MIXED** |
| **Decision rule** | `n_pass >= 4 of 7` (sealed §2.1) |
| **Verdict JSON SHA-256** | `84a457e3f47f5ad5e11f8fc2f86adf03ea25e30fead4a99c084e99ccfa6d4180` |

### Per-criterion outcomes

| # | Criterion | Status | Value | Threshold |
|---|---|---|---|---|
| C1 | OOS R² @ 1Y LC_TIER2 > 0.005 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.005 |
| C2 | OOS R² @ 3Y LC_TIER2 > 0.020 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.020 |
| C3 | OOS R² @ 5Y LC_TIER2 > 0.040 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.040 |
| C4 | LC_FULL \|t_NW\| > 1.65 (Amendment 2) | NOT_EVALUABLE_COUNTED_FAIL | — | 1.65 |
| C5 | ADF rejects all 5 (Holm-Šidák α=0.05) | FAIL_STATISTICAL | max p ≈ 0.7648 | 0.05 |
| C6 | max VIF < 5.0 | **PASS** | ≈ 1.70 | 5.0 |
| C7 | any Bonferroni p < 0.0025 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.0025 |

---

## Verdict JSON provenance

- **Path**: `buffet_indicator/outputs/lc_v2_verdict.json`
- **SHA-256**: `84a457e3f47f5ad5e11f8fc2f86adf03ea25e30fead4a99c084e99ccfa6d4180`
- **Sidecar**: `buffet_indicator/outputs/lc_v2_verdict.json.sha256`
- **Schema validation**: PASS (top-level keys + per-criterion cells counts match sealed §12)
- **PIT audit**: PASS (0 violations)
- **Round-trip**: JSON parses back to structurally equivalent dict

---

## §11.2 tests + broader regression suite

- **§11.2 acceptance tests**: **21/21 PASS** (unchanged from Phase D)
- **New Phase E tests**: **20 PASS** (panel builder × 7, verdict-run × 5, verdict-writer × 8)
- **Broader regression** (`pytest tests/ --ignore=viz --ignore=deploy --ignore=quant_engine --ignore=backtest`): not re-run this session; expected to be 538 pass + 20 new = 558+ (matched on E.5 writer tests).

---

## §16 seal-report criteria
Still **10/10 PASS** (no regression).

---

## Strategist callbacks
**None this session.** All sealed §3 / §10.1 / §12 surfaces interpreted without ambiguity. Two documented Phase E methodology decisions surfaced in verdict JSON `_meta`:

1. **OOS split = 2021-01-31 for all 3 scopes** (data-driven; sealed v1.0 dates 2011-01/2013-01 pre-date v2.0 composite valid start of 2016-01 per sealed §3.2.1 *"estimation expands from longest jointly-available date"*).
2. **z5 SOFR-IORB warm-up relaxed to 24 months** (SOFR-IORB monthly history insufficient for sealed 120-month PIT floor; pre-blend z_TED honors sealed floor).

These are documented in `panel_meta` of the verdict JSON for full transparency.

---

## Library version delta

- **Installed**: `arch=8.0.0`, `pandas=3.0.2`, `numpy=2.4.4`, `scipy=1.17.1`, `statsmodels=0.14.6`
- **Sealed pinned (§3.7.2 / §3.8)**: `arch=7.0.0`, `pandas=2.2.3`, `numpy=1.26.4`, `scipy=1.13.1`, `statsmodels=0.14.2`
- **Phase D methodology note 7** verified API compatibility for the two surfaces exercised (`SkewStudent.loglikelihood`, `optimal_block_length`).
- **Phase F closeout** will pin and re-run for reproducibility.

---

## Sealed §6.4 implications

Per sealed §6.4: a v2.0 FAIL is the **3rd consecutive pre-reg FAIL** on this project (v11.2.0-stat, v11.3.0 LC v1.0, v11.4 LC v2.0). The Strategist will:
- Author a meta-DECISIONS entry documenting that 3-of-3 FAIL is itself informative.
- Enumerate remaining-falsified vs unresolved claims.
- Recommend pivots.

This is a Phase F deliverable, not Phase E.

---

## Next prompt

Issue **Phase F** kickoff: display framing rules (sealed §7) + `requirements.lock` pin + re-run + sprint closeout report + §6.4 meta-DECISIONS entry.
