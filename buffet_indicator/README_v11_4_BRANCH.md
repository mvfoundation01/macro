# README — `spec/liquidity-composite-v2.0` branch

> **Branch purpose**: house the v11.4 LC v2.0 sprint, addressing the 4 amendment
> candidates identified during the v11.3.0 LC v1.0 closeout.
>
> **Branch status (2026-05-23)**: EMPTY SCAFFOLD. v2.0 pre-registration NOT yet sealed.
> v11.4 implementation must NOT begin until the sealed v2.0 pre-reg commit exists.
>
> **Branch base**: `main` at commit `3d0dc0f` (tag `pre-v11.4-baseline`, created
> by the post-v11.3.0 stabilization session 2026-05-23).

---

## What this branch contains today

| File | Purpose |
|---|---|
| `specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md.TEMPLATE` | Placeholder pre-reg structure. Strategist replaces with sealed content; rename drops `.TEMPLATE`. |
| `specs/v11_4_amendment_candidates_FROM_v11_3_0.md` | Reference material — 4 amendment candidates from v11.3.0 verdict.json, with v1.0-context narrative for each. |
| `README_v11_4_BRANCH.md` | This file. |

Everything else on this branch is identical to `main @ pre-v11.4-baseline`.

---

## How the v2.0 sealing works (analog to v1.0's `a8635ef`)

1. Strategist drafts the sealed pre-reg content via a separate prompt.
2. Claude Code commits the sealed content **verbatim**, replacing the
   `.TEMPLATE` file (rename to drop `.TEMPLATE`, content overwritten).
3. The resulting commit becomes the v2.0 pre-reg invariant; record its
   short hash + date in `TECH_DEBT.md` and any session PROGRESS log.
4. v11.4 implementation (sub-stages A1, B, C, …) starts AFTER this sealing
   commit. Pre-reg content is read-only thereafter for the sprint duration.

---

## Cross-link to prior pre-registrations and artifacts

- **MV-Conditional rule pre-reg**: `a90b02d` on `main` (sealed 2026-05-21,
  `specs/MV_CONDITIONAL_RULE_PREREGISTER.md`).
- **LC v1.0 pre-reg**: `a8635ef` on `spec/liquidity-composite-v1.0` (sealed
  2026-05-21, `specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md`). FAILED v11.3.0
  falsifiability test; see `LC_V1_SPRINT_CLOSEOUT_REPORT.md` on that branch.
- **v50 ORIGINAL invariant**:
  SHA256 `6087918DB909D3BB3AE66F43305C3331E4171AEBC55DDC0366AAFF6128026F47`
  at `D:\Quant Pipeline\Momentum pipeline\quant_engine_v50_FINAL.py`.

---

## What MUST happen before v11.4 implementation

1. Strategist drafts and Claude Code commits the sealed v2.0 pre-reg (replaces `.TEMPLATE`).
2. Tag the sealing commit (suggested: `v11.4-lc-v2-preregister-YYYY-MM-DD`).
3. Re-verify all invariants on this branch (the prompt's §1 opening checklist).
4. Drive CI deploy.yml back to green on `main` (per `TECH_DEBT.md` §1 P1 item 2).
5. Optionally clear the viz-suite slowdown blocker (`TECH_DEBT.md` §1 P1 item 4) so the full pytest suite can complete.

Only then does v11.4 sub-stage A1 begin.
