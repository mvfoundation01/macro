# Seal Report §16 Criterion #6 — Lift Demonstration

**Date**: 2026-05-25T12:22:55Z
**Branch**: spec/liquidity-composite-v2.0
**Implementing commit**: e3480f9e61cbaf10bbfc2a326ffeea8e349822d3
**Module**: `buffet_indicator/src/stats/hard_gate.py`
**Function**: `assert_prereg_ancestor`
**Authority**: PROMPT_CC_v11_4_v2_sprint_RESUME_after_disconnect.md §5

---

## §16 Criterion #6 (from `outputs/seal_report_v11_4.md`)

> `assert_prereg_ancestor(seal_commit, sealed=True)` returns success.

| Status | Detail |
|---|---|
| Previous | ⏳ DEFERRED (`src/stats/hard_gate.py` was a v2.0 sprint deliverable) |
| New      | ✅ PASS |

---

## Demonstration

```python
import sys
from pathlib import Path
sys.path.insert(0, "buffet_indicator")

from src.stats.hard_gate import assert_prereg_ancestor

# Call against the canonical seal commit
result = assert_prereg_ancestor(
    "2a94417524e67c7b88cb05ad1ac61fafd6b5711a",
    sealed=True,
)
# Returns None (no exception raised) — gate PASSED.
print(result)  # -> None
```

The HARD GATE invariant from §0.3 + §8.2 of the sealed pre-registration
is now demonstrable via Python import + function call.

---

## Test pass evidence

```
$ python -m pytest tests/stats/test_hard_gate.py -v --no-cov
================ test session starts ================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: D:\macro\buffet_indicator
configfile: pytest.ini
plugins: cov-7.1.0, mock-3.15.1
collected 1 item

tests/stats/test_hard_gate.py::test_hard_gate_handles_ancestor_detached_preseal_and_shallow PASSED  [100%]

================ 1 passed in 1.49s ==================
```

The single sealed §11.2 test name
`test_hard_gate_handles_ancestor_detached_preseal_and_shallow`
covers all four sub-scenarios in one function:

| Sub-case | Setup | Expectation | Result |
|---|---|---|---|
| **ancestor** | Real `D:\macro` repo + real seal commit `2a94417…` | `assert_prereg_ancestor(...)` returns `None` | ✅ PASS |
| **detached** | Synthetic two-branch repo: HEAD on sibling of "seal" | `HardGateViolation` raised | ✅ PASS |
| **preseal (default)** | Synthetic A→B repo, HEAD at A, pre_reg = B | `HardGateViolation` raised | ✅ PASS |
| **preseal (`allow_preseal=True`)** | Same as above, override on | Returns `None` | ✅ PASS |
| **shallow** | Synthetic depth-1 shallow clone | `HardGateIndeterminate` raised | ✅ PASS |
| **dev-mode** | `sealed=False` with bogus SHA | Returns `None` (no-op) | ✅ PASS |

---

## Implementation details (for traceability)

- Single Python module: `buffet_indicator/src/stats/hard_gate.py`.
- Exposes: `assert_prereg_ancestor`, `HardGateViolation`, `HardGateIndeterminate`.
- Git plumbing only: `git rev-parse`, `git cat-file`, `git merge-base --is-ancestor`.
- No `subprocess.run(..., shell=True)`; argv passed as list (per §13.3 subprocess safety).
- Defensive shallow-clone handling: shallow + `sealed=True` → `HardGateIndeterminate` regardless of whether ancestry could otherwise be determined (per §8.2 "refuse to certify rather than guess").
- Distinguishes between definitive policy breach (`HardGateViolation`) and conclusively-unknowable cases (`HardGateIndeterminate`).

---

## Updated §16 success-criteria tally

| # | Criterion (short) | Prior status | Current status |
|---|---|---|---|
| 1 | Sealed pre-reg present at canonical path | ✅ PASS | ✅ PASS |
| 2 | SHA-256 of sealed file recorded | ✅ PASS | ✅ PASS |
| 3 | Seal commit recorded and reachable | ✅ PASS | ✅ PASS |
| 4 | Manifest sidecar present | ✅ PASS | ✅ PASS |
| 5 | Seal report written | ✅ PASS | ✅ PASS |
| **6** | **`assert_prereg_ancestor` callable + tested** | **⏳ DEFERRED** | **✅ PASS** |
| 7 | All open Q's documented | ✅ PASS | ✅ PASS |
| 8 | Audit-trail files in `outputs/seal_*` | ✅ PASS | ✅ PASS |
| 9 | Branch & remote in clean state | ✅ PASS | ✅ PASS |
| 10 | Pre-registration locks the methodology | ✅ PASS | ✅ PASS |

**Tally**: **10 of 10 PASS** (was 9 of 10 PASS + 1 DEFERRED).

The v11.4 pre-registration phase is now **fully complete** with all
success criteria PASS.

---

## Source artefacts

| Path | Role |
|---|---|
| `buffet_indicator/src/stats/hard_gate.py` | Implementation |
| `buffet_indicator/tests/stats/test_hard_gate.py` | T15 acceptance test |
| `buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` (SHA-256 `c3c3ec1a…`, seal commit `2a94417…`) | Sealed pre-registration (source of §11.1 signature) |
| `outputs/seal_report_v11_4.md` | Seal report containing the §16 criteria |
| `outputs/v2_sprint_implementation_plan.{json,md}` | Implementation plan (§11.1 + §11.2 extraction) |
| Commit `e3480f9` on `spec/liquidity-composite-v2.0` | Phase A.4 implementing commit |

— Claude Code, v2.0 sprint Phase A.4 @ 2026-05-25T12:22:55Z
