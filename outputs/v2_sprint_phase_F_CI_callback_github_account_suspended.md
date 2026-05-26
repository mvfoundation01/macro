# Phase F-CI callback — GitHub account suspension blocks CI

**Timestamp**: 2026-05-26T08:39Z (local) / approx 2026-05-26T12:39Z (UTC)
**Branch**: spec/liquidity-composite-v2.0
**HEAD at callback**: 7ba8579 (Phase F-CI.A: disable LFS in v11.4 verify workflow)
**Severity**: Hard blocker for §7 tag (cannot certify "CI green" until resolved). Soft on remaining F.CI.B–F.CI.E work (all local; pushes still succeed).

## The finding

The `v11.4 sprint verification` workflow added in F.CI.A pushed cleanly to
GitHub, but every GitHub Actions run fails at the very first step
(`actions/checkout@v4`) with:

```
remote: Your account is suspended. Please visit https://support.github.com for more information.
fatal: unable to access 'https://github.com/mvfoundation01/macro/': The requested URL returned error: 403
The process '/usr/bin/git' failed with exit code 128
```

The runner retries three times (20 s between attempts) before exiting 128.

## What I confirmed

- The workflow YAML is syntactically valid; GitHub parses it and creates a run.
- I am still able to **push** from the local clone (commit `7ba8579` pushed
  successfully at 12:37 UTC). So write-side credentials are intact.
- The Actions runner's `GITHUB_TOKEN` fetch is what 403s.
- The test scope CI runs (`tests/models/ tests/stats/ tests/replication/`)
  passes locally in the pinned venv: **247 passed in 39.4 s** under Python
  3.12.10 + sealed pins (arch 7.0.0, pandas 2.2.3, numpy 1.26.4, scipy
  1.13.1, statsmodels 0.14.2).
- The first push attempted `lfs: true` + `fetch-depth: 0` and failed; the
  second attempt switched to `lfs: false` + `fetch-tags: true`. Both failed
  for the same reason — the message is not LFS-quota-related, it is the
  account-level suspension banner.

## Possible causes

1. The user GitHub account `mvfoundation01` has been actually suspended by
   GitHub Trust & Safety. The "remote: Your account is suspended" banner
   matches the exact message GitHub serves in that case.
2. Billing / Actions-minutes / payment failure has flipped the account into
   restricted mode where new Action runs are denied but pushes still work.
3. A workflow-permissions edge case (very unlikely given the message text).

## What I am doing

- **Continuing** F.CI.B (pre-commit hooks), F.CI.C (README polish), F.CI.D
  (SHA consistency audit), F.CI.E (test count snapshot). All four are local
  authoring + commit work; pushes succeed even with the Actions runner
  blocked.
- **Withholding** the §7 annotated tag `v11.4-defensive-infrastructure-ready`
  per §9 stop conditions: "CI must be green before tag." The progress report
  will document the tag as DEFERRED pending account resolution.
- Filing this callback document so the Owner can act on the GitHub-side
  blocker.

## What the Owner needs to do

1. Visit https://support.github.com (per the suspension message) and resolve
   the suspension / billing block.
2. After the account is restored, re-trigger the latest workflow run via
   `gh workflow run v11_4_verify.yml --ref spec/liquidity-composite-v2.0`
   (or push any commit on the branch). The workflow should then pass — local
   validation matches the CI test scope exactly.
3. Once CI is green, run §7 from the original prompt to apply the
   `v11.4-defensive-infrastructure-ready` tag.

If the Owner determines the suspension cannot be resolved soon (e.g., a
multi-day GitHub Support ticket), the progress report's "tag deferred" path
is acceptable — the v11.4 sprint's reproducibility-ready state (tagged
`v11.4-ssrn-reproducibility-ready`) is unaffected.

## Cross-references

- §9 stop conditions: "CI workflow fails first push → Debug + fix; CI must be
  green before tag" — debugging confirms the failure is external (account
  level), not workflow-content.
- §10 callbacks: "CI workflow first-run failure | P=3%" hotspot identified
  in advance; this realization is in scope of the documented prior.
- Master spec §1.6.8: GitHub Actions defensive infrastructure — workflow
  exists at `.github/workflows/v11_4_verify.yml`, locally validated, awaiting
  account restoration to certify green.
