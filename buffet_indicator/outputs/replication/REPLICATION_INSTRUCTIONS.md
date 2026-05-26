# Replication Instructions — v11.4 Liquidity Composite v2.0 Verdict

This document enables a third party to reproduce the v11.4 sprint's v2.0 verdict at substantive byte equivalence.

## Overview

- **Verdict outcome**: `FAIL` (1 of 7 pre-registered criteria pass)
- **Canonical verdict JSON SHA-256 (file-byte)**: `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c`
- **Canonical verdict normalized SHA-256 (substantive content)**: `0fe5c5053af78bac061a7ca89568b484b6583a6d9da0d0ddbf5b0837d7344f02`
- **Sealed pre-registration SHA-256**: `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` (IMMUTABLE)
- **Sealed pre-reg commit**: `2a94417` (tag `v11.4-prereg-sealed`)
- **Engineering closeout tag**: `v11.4-engineering-closeout`
- **SSRN reproducibility tag**: `v11.4-ssrn-reproducibility-ready` (this phase)

## Prerequisites

| Item | Requirement | How to obtain |
|---|---|---|
| Python | 3.12.x recommended (3.11+ acceptable) | https://python.org |
| FRED API key | Free, instant | https://fredaccount.stlouisfed.org/apikeys |
| Disk space | ~500 MB (env + cached data + outputs) | Local |
| Network | Required (FRED API) | Internet |
| Wall clock | ~15–30 minutes end-to-end | One-time |
| Optional | `uv` (faster pip-replacement) | https://docs.astral.sh/uv/ |

## Steps

### Step 1 — Clone the repository

```bash
git clone https://github.com/mvfoundation01/macro.git
cd macro
git checkout v11.4-ssrn-reproducibility-ready  # or v11.4-engineering-closeout
```

### Step 2 — Set up a pinned environment

The pinned `requirements.lock` (Phase F-DOC.A) cryptographically pins every dependency. Install with hash verification:

```bash
# Recommended (uv): fast, reproducible
uv venv --python 3.12 .venv
source .venv/bin/activate                 # macOS/Linux
# .venv\Scripts\activate                  # Windows PowerShell
uv pip install --require-hashes -r buffet_indicator/requirements.lock

# Or with stock pip
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install --require-hashes -r buffet_indicator/requirements.lock
```

Sanity-check sealed pins:

```bash
python -c "import arch, pandas, numpy, scipy, statsmodels
assert arch.__version__ == '7.0.0'
assert pandas.__version__ == '2.2.3'
assert numpy.__version__ == '1.26.4'
assert scipy.__version__ == '1.13.1'
assert statsmodels.__version__ == '0.14.2'
print('All 5 sealed §3.7.2/§3.8 pins verified')
"
```

### Step 3 — Configure FRED API access

```bash
export FRED_API_KEY=<your_key>            # macOS/Linux
# $env:FRED_API_KEY = "<your_key>"        # Windows PowerShell
# set FRED_API_KEY=<your_key>             # Windows cmd
```

### Step 4 — Reconstruct master data archive (optional)

If the cached `data/master/*.parquet` files are already in the cloned repo, you can skip this step and proceed to Step 5. To verify the cached data SHA-256 matches `data_manifest.json`:

```bash
cd buffet_indicator
python -m src.replication.reconstruct_master \
    --manifest data_manifest.json \
    --output-dir data/raw/ \
    --verify-sha \
    --report-path outputs/replication/reconstruction_report.json
```

Expected: all 11 v2.0 FRED-source series fetched; the script writes `outputs/replication/reconstruction_report.json` summarising successes, SHA matches, and any mismatches. **SHA mismatches are not failures** — FRED occasionally issues revisions for `M2SL`, `BUSLOANS`, etc., which can legitimately change the cached file's SHA without changing the substantive verdict.

### Step 5 — Run the verdict pipeline

```bash
cd buffet_indicator
python -m src.models.v2_run_verdict \
    --output outputs/lc_v2_verdict_my_reproduction.json
```

Expected runtime: 3–8 minutes (50 000 stationary bootstrap replications per cell × 12 cells, deterministic seeded). Output: verdict JSON + sidecar `.sha256` (sha256sum-compatible format).

The pipeline always uses the sealed-IMMUTABLE `n_bootstrap = 50_000` (Phase F-BLK1.E removed the `--n-bootstrap` CLI override). Diagnostic or test callers can invoke `src.models.v2_run_verdict.run_verdict(..., purpose="test")` programmatically with a smaller `n_bootstrap`.

### Step 6 — Verify substantive equivalence

```bash
python -c "
from pathlib import Path
import sys
sys.path.insert(0, '.')
from src.models.v2_verdict_normalize import normalized_sha256, field_level_diff

canonical = normalized_sha256(Path('outputs/lc_v2_verdict.json'))
yours = normalized_sha256(Path('outputs/lc_v2_verdict_my_reproduction.json'))
print(f'Canonical normalized SHA: {canonical}')
print(f'Your normalized SHA:      {yours}')
print(f'Match: {canonical == yours}')
if canonical != yours:
    diffs = field_level_diff(Path('outputs/lc_v2_verdict.json'), Path('outputs/lc_v2_verdict_my_reproduction.json'))
    print(f'Field differences: {len(diffs)}')
    for path, (c, r) in sorted(diffs.items())[:20]:
        print(f'  {path}: {c} -> {r}')
assert canonical == yours, 'Reproduction failed substantive equivalence test'
print('REPRODUCTION SUCCESSFUL — verdict substantively byte-equivalent.')
"
```

Expected output: `Match: True`. Both normalized SHA-256 values equal `0fe5c5053af…`. The file-byte SHA will differ from the canonical because of legitimate dynamic-metadata fields (timestamp, git_head, host) — see `src/models/v2_verdict_normalize.py` `DYNAMIC_FIELD_PATHS` for the stripped list.

## What you should see

Verdict outcome (per `outputs/lc_v2_verdict.json` top-level):

```json
{
  "verdict": "FAIL",
  "evidence_status": "MIXED",
  "n_pass_total": 1,
  "n_pass_predictive": 0,
  ...
}
```

Per-criterion:

| # | Criterion | Status | Value | Threshold | Operator |
|---|---|---|---|---|---|
| C1 | OOS R² @ 1Y on LC_TIER2 | `NOT_EVALUABLE_COUNTED_FAIL` | — | 0.005 | `>` |
| C2 | OOS R² @ 3Y on LC_TIER2 | `NOT_EVALUABLE_COUNTED_FAIL` | — | 0.020 | `>` |
| C3 | OOS R² @ 5Y on LC_TIER2 | `NOT_EVALUABLE_COUNTED_FAIL` | — | 0.040 | `>` |
| C4 | LC_FULL \|t_NW\| > 1.65 (Amendment 2) | `NOT_EVALUABLE_COUNTED_FAIL` | — | 1.65 | `>` |
| C5 | ADF rejects all 5 (Holm-Šidák α=0.05) | `FAIL_STATISTICAL` | max p ≈ 0.7648 | 0.05 | `<` |
| C6 | max VIF across 5 components | **PASS** | ≈ 1.6951 | 5.0 | `<` |
| C7 | Bonferroni any p < 0.0025 | `NOT_EVALUABLE_COUNTED_FAIL` | — | 0.0025 | `<` |

PIT look-ahead audit:
```json
{
  "audit_status": "PASS",
  "n_cells_audited": 12,
  "n_origins_audited": 756,
  "n_violations": 0,
  "pit_audit_construction": "per_origin_non_tautological_F_BLK1_A"
}
```

## Troubleshooting

| Problem | Likely cause | Resolution |
|---|---|---|
| `FRED_API_KEY not set` | env var missing | Set per Step 3 |
| `ModuleNotFoundError: No module named 'PIL'` | Pillow missing | `pip install --require-hashes -r buffet_indicator/requirements.lock` (Pillow pinned in Phase F-DOC.B prep) |
| SHA mismatch on a single FRED series | FRED revised that series since the sprint | EXPECTED for revisable series; check `reconstruction_report.json` `sha_mismatches` |
| Verdict outcome differs (PASS instead of FAIL) | Library version drift | Verify pinned versions; sealed §3.7.2/§3.8 require exact `arch==7.0.0`, `pandas==2.2.3`, `numpy==1.26.4`, `scipy==1.13.1`, `statsmodels==0.14.2` |
| Normalized SHA differs at < 1e-9 magnitude | Library numerical drift | Acceptable; substantive equivalence holds |
| Normalized SHA differs at ≥ 1e-9 | Library / data drift | Investigate — check `field_level_diff` for the divergent fields |
| `pip install --require-hashes` fails | Network or pip version | Upgrade pip ≥ 23.0; retry; or use `uv pip install` |
| Verdict pipeline takes > 30 minutes | Slow CPU or 50K bootstrap on heavy panel | Normal expected wall-clock is 3–8 min on modern hardware |

## Notes on data vintages

FRED series (`M2SL`, `BUSLOANS`, `WALCL`, …) are subject to retroactive revision (ALFRED). The v11.4 sprint uses an **observation-date approximation** per `data_manifest.json` → `vintage_basis: observation_date_approximation_per_phase_b_c_arbitration_section_B_option_B3`. If FRED has revised a series since the sprint's `retrieval_timestamp`, your reproduction may differ in numerical detail without flipping the verdict outcome.

To reproduce the EXACT sprint-vintage data (pre-revision), use the cached `data/master/*.parquet` files preserved in the public repository (Step 4 verifies their SHA-256 against `data_manifest.json`).

## How to cite this work

If you reproduce, extend, or critique this work, please cite the SSRN entry (TBD upon submission per `WRITEUP_OUTLINE_3of3_FAIL_SSRN.md`) and reference:

- Repository: `https://github.com/mvfoundation01/macro` at tag `v11.4-ssrn-reproducibility-ready`
- Sealed pre-registration: SHA-256 `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05`
- Canonical verdict JSON: SHA-256 `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c` (normalized substantive: `0fe5c5053af…`)

## Contact

[Owner to fill in upon SSRN submission]

## Provenance + further reading

| Document | Purpose |
|---|---|
| `buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` | Sealed pre-registration (IMMUTABLE) |
| `buffet_indicator/outputs/lc_v2_verdict.json` | Canonical verdict JSON |
| `buffet_indicator/outputs/lc_v2_verdict_summary.md` | Human-readable verdict summary |
| `buffet_indicator/outputs/lc_v2_display_fail.md` | Sealed §7 DIAGNOSTIC ONLY view |
| `buffet_indicator/outputs/lc_v2_verdict_blk1_delta.md` | Phase F-BLK1 delta (pre-BLK-1 → BLK-1 canonical) |
| `buffet_indicator/outputs/lc_v2_verdict_closeout_delta.md` | Phase F-DOC closeout delta (BLK-1 → pinned closeout) |
| `buffet_indicator/outputs/v11_4_sprint_engineering_closeout.md` | Engineering closeout report |
| `buffet_indicator/data_manifest.json` + `.md` | Data manifest (provenance, SHA-256, splice points) |
| `buffet_indicator/outputs/SPRINT_v11_4_INDEX.md` | Sprint navigation index (this phase) |
| `buffet_indicator/outputs/historical/lc_v2_verdict_pre_blk1.json` | Pre-BLK-1 verdict (preserved audit-trail) |
| `buffet_indicator/reviews/` | Reviewer reports (ChatGPT 5.5 Pro + Codex, Rounds 1–5) |
