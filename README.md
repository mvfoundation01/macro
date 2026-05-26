# macro

Pre-registered empirical-finance research repository. Maintained by the Owner
(`mvfoundation01`).

**Public-repository status as of 2026-05-26**: v11.4 sprint complete.

---

## Latest sprint — v11.4 Liquidity Composite v2.0

| | |
|---|---|
| **Outcome** | **FAIL** (1 of 7 sealed criteria pass) |
| **Sealed pre-registration SHA-256** | `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` |
| **Canonical verdict SHA-256 (file-byte)** | `df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c` |
| **Canonical verdict SHA-256 (normalized substantive)** | `0fe5c5053af78bac061a7ca89568b484b6583a6d9da0d0ddbf5b0837d7344f02` |
| **Branch** | `spec/liquidity-composite-v2.0` |
| **Permanent tags** | `v11.4-prereg-sealed` → `v11.4-engineering-closeout` → `v11.4-ssrn-reproducibility-ready` (→ `v11.4-defensive-infrastructure-ready` once CI is green) |

### Reproducibility

To reproduce the v2.0 verdict from clean state:

- [`buffet_indicator/outputs/replication/REPLICATION_INSTRUCTIONS.md`](buffet_indicator/outputs/replication/REPLICATION_INSTRUCTIONS.md) — step-by-step third-party guide
- [`buffet_indicator/outputs/SPRINT_v11_4_INDEX.md`](buffet_indicator/outputs/SPRINT_v11_4_INDEX.md) — single entry-point for all sprint artifacts
- [`buffet_indicator/requirements.lock`](buffet_indicator/requirements.lock) — pinned dependencies (Python 3.12.10 + sealed pins, `--require-hashes`)
- [`buffet_indicator/outputs/replication/v11_4_clean_state_repro_report.md`](buffet_indicator/outputs/replication/v11_4_clean_state_repro_report.md) — clean-state-clone reproducibility verification

The v2.0 verdict is reproducible across four reproducibility axes:

1. **Library versions** — pinned closeout re-run produces normalized SHA `0fe5c5053af…` identical to canonical
2. **Implementation iteration** — BLK-1 fixes produced same substantive verdict (normalized SHA preserved across implementation deltas)
3. **Operating system** — byte-exact SHA cross-OS via Git LFS + `.gitattributes` `-text` rule
4. **Clean state** — isolated clone from public repo produces normalized SHA `0fe5c5053af…` identical to canonical (0 field diffs at 1e-12 tolerance)

### What this sprint pre-registered

The v11.4 sprint pre-registered a 5-component Liquidity Composite (LC) hypothesis: that aggregate USD liquidity conditions (Fed net liquidity, M2, bank lending, broad-dollar index, funding stress) predict forward equity returns under sealed methodology. The seven sealed criteria are:

| Criterion | Description |
|---|---|
| C1 | OOS R² vs. AR(1) benchmark |
| C2 | OOS Spearman ρ (forecast vs. realized) |
| C3 | OOS direction-accuracy vs. coin-flip |
| C4 | OOS Sharpe vs. buy-and-hold |
| C5 | Stationarity (ADF p < 0.10 for each component) |
| C6 | Multicollinearity (max VIF < 5.0) |
| C7 | Stambaugh small-sample bias bound |

### Failure modes (diagnosed)

| Mode | Diagnosis |
|---|---|
| Mode A — short OOS window | 4 of 7 criteria NOT_EVALUABLE due to short OOS window post-z4 anchoring (data-window vs. strict-gate interaction) |
| Mode B — z4 non-stationary | z4 (DXY log-level) does not pass ADF stationarity (max p ≈ 0.7648 across components) |
| One PASS | C6 max VIF ≈ 1.70 < 5.0 confirms components are not problematically collinear |

See [`buffet_indicator/outputs/lc_v2_verdict_summary.md`](buffet_indicator/outputs/lc_v2_verdict_summary.md) for the full criterion-by-criterion verdict and [`buffet_indicator/outputs/lc_v2_display_fail.md`](buffet_indicator/outputs/lc_v2_display_fail.md) for the sealed §7 display framing (diagnostic-only; explicit no-signal disclaimers).

### What this sprint contributes (methodologically)

The architecture itself is a contribution independent of the empirical null:

- **Sealed pre-registration** via git annotated tag + SHA-256 immutability — falsification-class evidence
- **Multi-round reviewer corroboration** — 4 pre-reg drafting rounds (ChatGPT 5.5 Pro + Codex) + 1 v12 design round
- **Callback safety net** — 10 Strategist mistakes caught architecturally during implementation; 0 code damage
- **Library pinning** + reproducibility verification across four axes
- **Non-tautological audit construction** — per-origin vintage loading + synthetic violation detection tests

See the SSRN writeup (forthcoming) for the full methodological treatment.

---

## Repository structure (top level)

```
macro/
├── DECISIONS.md                  Strategist arbitration log (canonical)
├── README.md                     this file
├── .github/workflows/            CI workflows
│   ├── deploy.yml                main-branch dashboard build + deploy
│   └── v11_4_verify.yml          v11.4 sprint invariant verification
├── .pre-commit-config.yaml       pre-commit hooks (sealed pre-reg guard + lint + type + security)
├── tools/                        defensive infrastructure scripts
├── buffet_indicator/             v11.4 sprint codebase (see internal README)
├── API/                          API stubs (forthcoming)
├── outputs/                      repo-level audit + callback logs
├── prompt/                       per-session prompt templates
├── quant_pipeline/               forward-work staging area
├── raw data/                     uncommitted raw downloads (gitignored)
└── template/                     scaffolding
```

See [`buffet_indicator/`](buffet_indicator/) for the v11.4 sprint codebase entry-point and its internal documentation.

## License

Owner-specified. (Code is under an OSI-compatible license; data attribution follows source-provider licenses — see component-level metadata sidecars in `buffet_indicator/data/master/`.)

## Contact

Maintainer: `mvfoundation01`. For SSRN reviewer questions, please use repository Issues.

## Citation

To be filled in upon SSRN submission.
