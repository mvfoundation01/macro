# §6 — Stage 3 LC v1.0 Session 8 Final Report

## 1. Status

**complete** — all 4 sub-stages + sprint closeout (§2.0 DECISIONS.md addendum + §2.H diagnostics + §2.I dashboard panel + §2.J verdict/write-up + `v11.3.0`).

## 2. Sub-stages completed

| Sub-stage | Status | Commit | Tag | CI run |
|---|---|---|---|---|
| §2.0 DECISIONS.md addendum (Strategist arbitration on Session 7 findings) | ✅ | [`c89d5e7`](https://github.com/mvfoundation01/macro/commit/c89d5e7) | `v11.3-lc-v1-decisions-2-2026-05-25` | [26304545776](https://github.com/mvfoundation01/macro/actions/runs/26304545776) |
| §2.H Diagnostics (ADF + KPSS + PP + ZA + VIF + Bai-Perron) | ✅ | [`d081085`](https://github.com/mvfoundation01/macro/commit/d081085) | `v11.3-lc-v1-H-2026-05-25` | [26304782659](https://github.com/mvfoundation01/macro/actions/runs/26304782659) |
| §2.I DIAGNOSTIC ONLY dashboard panel | ✅ | [`177554f`](https://github.com/mvfoundation01/macro/commit/177554f) | `v11.3-lc-v1-I-2026-05-25` | [26304954593](https://github.com/mvfoundation01/macro/actions/runs/26304954593) |
| §2.J Verdict locked + research write-up + sprint closeout | ✅ | [`d56174c`](https://github.com/mvfoundation01/macro/commit/d56174c) | `v11.3-lc-v1-J-2026-05-25` + **`v11.3.0`** | [26305214049](https://github.com/mvfoundation01/macro/actions/runs/26305214049) |
| §6 + §4 final reports + PROGRESS | ✅ | (this commit) | — | — |

## 3. Headline outcomes

### 3.1 Final scorecard locked (`outputs/lc_v1_verdict.json`)

| # | Criterion | Threshold | Realized | Pass |
|---|---|---|---|---|
| 1 | OOS R² @ 1Y on LC_TIER2 | > 0.005 | −0.0167 | ❌ |
| 2 | OOS R² @ 3Y on LC_TIER2 | > 0.020 | −0.0028 | ❌ |
| 3 | OOS R² @ 5Y on LC_TIER2 | > 0.040 | −0.0602 | ❌ |
| 4 | LC_FULL NW t > 1.65 (POSITIVE) any horizon | t > 1.65 ∧ β > 0 | best is 3Y: β=−0.034, t=−3.08 (sign FAIL) | ❌ |
| 5 | ADF rejects null for all 5 components | p < 0.05 for all | z₁ p=0.17, z₄ p=0.37, z₅ p=0.08 fail | ❌ |
| 6 | Max VIF across 5 components < 5 | max < 5 | z₅ VIF=7.58, z₁ VIF=6.02 | ❌ |
| 7 | Any Bonferroni-sig cell (p < 0.0025) | any cell | only z₁ NetFed @ 10Y (n=42 insufficient-sample flagged) | ❌ |

**`n_pass = 0 of 7` → FAIL → DIAGNOSTIC ONLY display framing locked.**

### 3.2 Diagnostics — selected highlights

* **Stationarity**: z₂ M2_yoy, z₃ BankLend_yoy, LC_TIER2, LC_DEEP all stationary. z₁ NetFed, z₄ DXY⁻¹, z₅ Funding, LC_FULL conflicting (default to non-stationary per master spec §3.3).
* **VIF**: z₁ NetFed = 6.02 ⚠; z₅ Funding_stress = 7.58 ⚠. z₂/z₃/z₄ all < 2 (fine).
* **Bai-Perron** breaks across composites — economically interpretable:
  * 2020-03 (COVID) — appears in ALL 3 composites.
  * 2023-07 — appears in ALL 3 composites.
  * 2009-09 (post-GFC) — LC_TIER2 and LC_DEEP.

### 3.3 Dashboard panel (`outputs/lc_v1_diagnostic_panel.html`)

* 173 KB standalone HTML page (well under 20 MB bundle ceiling).
* 9 sections per prompt §2.I.2: headline FAIL verdict card, 3 findings narrative, 12-cell regression table (color-coded), 5×4 per-component table, ⚠ calibration disclosure, faded conditional probabilities, collapsible diagnostics, collapsible calibration with embedded reliability + PIT figures, methodology provenance.
* 16 structural tests (T-I1..T-I16), all pass.

### 3.4 Research write-up (`outputs/reports/lc_v1_research_writeup.md`)

* ~2,500 words academic-style draft (passes 1500-3500 word-count gate).
* 8 numbered sections + 2 appendices + references (~30 papers).
* 10 structural tests (T-J7..T-J10 + 6 verdict-content checks).

## 4. Invariants verified

| Invariant | Status |
|---|---|
| v50 ORIGINAL SHA256 = `6087918D…26F47` | ✅ unchanged |
| Pre-reg `a90b02d` (MV-Conditional) on `origin/main` | ✅ untouched |
| Pre-reg `a8635ef` (LC v1.0) ancestor of HEAD `d56174c` | ✅ HARD GATE re-enforced at verdict-write time |
| All sealed pre-reg values | ✅ unchanged |

## 5. Tests / coverage

| Module | New tests | Coverage |
|---|---|---|
| `src/models/lc_v1_diagnostics.py` | 16 | 92% |
| Panel structural tests | 16 | n/a (HTML structural) |
| Verdict JSON tests | 9 | n/a (JSON schema) |
| Research write-up tests | 6 | n/a (markdown structural) |

Total new tests in Session 8: **47**. Session 8 baseline test suite still green (Session 1-7 tests all pass after Session 8 changes).

## 6. Owner action required

**Paste `LC_V1_SPRINT_CLOSEOUT_REPORT.md` to the Strategist for merge-to-main arbitration.**

Three merge-timing options offered by the prompt §2.J.6:

a) Merge with explicit feature flag.
b) Keep on spec branch indefinitely as research record.
c) Merge but tag `main` as 'diagnostic-only-research-content'.

The Strategist's choice should be recorded in a new `DECISIONS.md` entry post-`v11.3.0`.

## 7. Session metrics

* Wall time: ≈ 1.5h of 10h budget (very fast closeout).
* Sub-stages shipped: 4 of 4 + sprint closeout + reports.
* Tests added: 47 new.
* Commits: 5 (4 sub-stages + final reports).
* Tags pushed: 4 sub-stage tags + 1 sprint closeout tag = 5.
* CI iterations: 5 manual triggers.
* Blockers filed: 0.

## 8. Next steps

The v11.3 LC v1.0 sprint is **complete**.

The next sprint (v11.4 LC v2.0) starts fresh from a new pre-registration that incorporates the 4 amendment candidates documented in `outputs/lc_v1_verdict.json`:

1. Pre-reg §4.1 priors with both monetarist + mean-reversion literature streams.
2. Criterion 4 sign-vs-magnitude disambiguation.
3. Conditional probability framework defaulting to skewed-t / empirical kernel.
4. Insufficient-sample gate as explicit pre-reg condition.

The held-out validation window for v11.4 LC v2.0 should be 2025–2027 (not yet used for v11.3 estimation) to preserve pre-registration discipline.
