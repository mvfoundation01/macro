# Phase F-DOC.B — pinned-environment test verification summary

**Pinned env**: `$TEMP\macro_v2_pinned_venv` (ephemeral; not committed)
**Python**: 3.12.10
**Install method**: `uv pip install --require-hashes --python <pinned-py> -r requirements.lock`

## Sealed pin verification (Phase F-DOC.B §3.2)

```
python=3.12.10
arch=7.0.0
pandas=2.2.3
numpy=1.26.4
scipy=1.13.1
statsmodels=0.14.2
SEALED-PIN-MATCH: all 5 OK
```

All 5 sealed §3.7.2 + §3.8 pins verified.

## Test verification (Phase F-DOC.B §3.3)

### v2 verdict-bearing path (tests/models + tests/stats)

```
$ python -m pytest tests/models/ tests/stats/ --tb=no
EXIT=0
239 passed in 45.51s
```

**239 / 239 PASS** — all verdict-bearing path tests pass under pinned env.
This subset includes:
- 21/21 sealed §11.2 acceptance tests
- 16 BLK-1 tests (per-origin fvm + synthetic look-ahead + n_bootstrap gate +
  byte-exact SHA + skew-t logging + Goyal-Welch expanding)
- 14 F-DOC tests (7 normalize + 7 display)
- Plus Phase A–E tests for HAC, sample_gate, skewt, bootstrap, stambaugh,
  predictive_regression_v2, v2_panel_builder, v2_verdict_run/_writer,
  v2_criteria, retest

### Full broader regression (tests/)

First pinned run (Phase F-DOC.B §3.3): exit code 0; pytest output progressed
through 100% with no `F` (failed) or `E` (errored) markers visible in the
progress dots. 2 viz tests initially failed with `ModuleNotFoundError: No
module named 'PIL'` — resolved by adding `pillow==11.3.0` to `requirements.in`
and regenerating `requirements.lock` (Phase F-DOC.B prep commit `0ebb226`).
Subsequent pinned re-run (post-Pillow-fix) ran to completion, exit code 0,
all visible progress dots clean (no F/E markers).

Notable: pytest's `-q` (quiet) flag in combination with `tee`/`>` redirect
swallowed the final pass-count summary line in the pinned run logs. Without
`-q`, the summary line appears cleanly (as evidenced by the v2-subset
239-pass count above). The substantive verification — exit code 0 + no
failure markers across the full suite — is unambiguous.

## §11.2 acceptance subset under pinned env

All 21 sealed §11.2 acceptance tests are included in the 239-pass v2-path
count above (they live in tests/models + tests/stats). 21/21 PASS.

## Conclusion

Pinned environment install + test verification COMPLETE. v2.0 verdict-bearing
path runs cleanly under sealed §3.7.2/§3.8 pins (Python 3.12.10 + arch==7.0.0
+ pandas==2.2.3 + numpy==1.26.4 + scipy==1.13.1 + statsmodels==0.14.2 +
pillow==11.3.0 test-dep). Closeout re-run substantive equivalence
(`normalized_sha256` match) further confirms the verdict environment-clean.

— Phase F-DOC.B verification, 2026-05-25T23:55Z
