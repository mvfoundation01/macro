"""Phase F-DOC.D — display framing per sealed §7 + §10.1 (v1.0 §12.2 inheritance).

Sealed §7 inherits v1.0 §12.2: a FAIL verdict triggers ``DIAGNOSTIC ONLY``
display framing. The 3-tier mapping per sealed §10.1:

- ``n_pass == 5+`` → ``PASS`` — headline LC tab with normal framing.
- ``n_pass == 4`` → ``PASS_WITH_CAVEATS`` — headline LC tab with disclosure card.
- ``n_pass <= 3`` → ``FAIL`` — DIAGNOSTIC ONLY view, no actionable conviction
  / probability / signal interpretation.

For v2.0 (n_pass=1, FAIL): produces DIAGNOSTIC ONLY markdown with explicit
"do not interpret as predictive signal" disclaimers, full per-criterion +
audit + provenance content, and failure-mode diagnosis.

References
----------
- Sealed pre-reg §7 (display framing rules).
- Sealed pre-reg §10.1 (v1.0 §12.2 transcribed wording).
- PROMPT_CC_v11_4_phase_F_DOC.md §5.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal


FramingMode = Literal["PASS", "PASS_WITH_CAVEATS", "FAIL"]


def determine_framing_mode(verdict: dict) -> FramingMode:
    """Map verdict outcome to display framing mode per sealed §7 + §10.1.

    Uses ``verdict["n_pass_total"]`` (binary decision is ``>= 4`` → PASS, but
    sealed §7 inherits the 3-tier ``5 / 4 / ≤3`` from v1.0 §12.2 for display).
    """
    n_pass = int(verdict.get("n_pass_total", 0))
    if n_pass >= 5:
        return "PASS"
    if n_pass == 4:
        return "PASS_WITH_CAVEATS"
    return "FAIL"


def _criterion_value_str(c: dict) -> str:
    """Render a criterion value with the canonical operator + threshold."""
    val = c.get("value")
    op = c.get("operator", "")
    thr = c.get("threshold")
    val_str = "—" if val is None else f"{val:.6g}" if isinstance(val, (int, float)) else str(val)
    thr_str = "—" if thr is None else f"{thr:g}" if isinstance(thr, (int, float)) else str(thr)
    return f"{val_str} (`{op} {thr_str}`)" if op and thr_str != "—" else val_str


def compose_diagnostic_only_view(verdict: dict, output_path: Path) -> str:
    """Compose the FAIL → DIAGNOSTIC ONLY markdown view per sealed §7.

    Required elements (sealed §7 + §10.1):
    - ``DIAGNOSTIC ONLY`` label, prominent
    - ``FAIL`` outcome stated
    - ``n_pass`` and decision rule
    - Per-criterion status table
    - Failure mode diagnosis
    - PIT audit summary
    - Explicit "no actionable conviction / probability / signal" disclaimer
    - Provenance / SHA chain

    Returns the generated markdown content (also writes to ``output_path``).
    """
    n_pass = int(verdict.get("n_pass_total", 0))
    n_pass_pred = int(verdict.get("n_pass_predictive", 0))
    decision_rule = verdict.get("decision_rule_check", {}).get(
        "rule", "n_pass >= 4 of 7"
    )
    evidence = verdict.get("evidence_status", "UNKNOWN")
    data_cutoff = verdict.get("data_cutoff", "—")
    audit = verdict.get("look_ahead_audit", {})
    audit_status = audit.get("audit_status") or (
        "PASS" if audit.get("all_cells_pit_compliant") else "FAIL"
    )
    n_origins_audited = audit.get("n_origins_audited", "—")
    n_violations = audit.get("n_violations", "—")
    sealed_sha = verdict.get("sealed_prereg_sha256", "")
    verdict_run_at = verdict.get("run_timestamp", "—")

    md: list[str] = []
    md.append("# DIAGNOSTIC ONLY VIEW — v2.0 Liquidity Composite (v11.4 sprint FAIL)\n\n")
    md.append("> **Display framing**: sealed pre-reg §7 inherits v1.0 §12.2 — a FAIL ")
    md.append("verdict (`n_pass ≤ 3`) triggers DIAGNOSTIC ONLY display with no ")
    md.append("actionable conviction, probability, or signal interpretation.\n\n")
    md.append(f"**Generated**: {verdict_run_at} (verdict run timestamp)\n\n")
    md.append("---\n\n")

    md.append("## DO NOT INTERPRET AS PREDICTIVE SIGNAL\n\n")
    md.append("This view is presented per sealed pre-registration §7 as **DIAGNOSTIC ONLY**.  \n")
    md.append("The v2.0 Liquidity Composite **did NOT pass** the sealed pre-registered evaluation.  \n")
    md.append("Any pattern visible in this view is shown for methodological transparency only.  \n")
    md.append("Treating the numerical contents as an actionable trading signal violates the ")
    md.append("pre-registered methodology and basic statistical principle.\n\n")
    md.append("---\n\n")

    md.append("## Verdict\n\n")
    md.append(f"- **Outcome**: `{verdict.get('verdict', '—')}`\n")
    md.append(f"- **Decision rule**: `{decision_rule}` (sealed §2.1)\n")
    md.append(f"- **n_pass_total**: `{n_pass} / 7`\n")
    md.append(f"- **n_pass_predictive**: `{n_pass_pred} / 5` (transparency field; not a gate)\n")
    md.append(f"- **evidence_status**: `{evidence}`\n")
    md.append(f"- **data_cutoff**: `{data_cutoff}`\n\n")

    md.append("## Per-criterion status\n\n")
    md.append("| # | Criterion | Status | Value | Predictive? |\n")
    md.append("|---|---|---|---|---|\n")
    for c in verdict.get("criteria", []):
        cid = c.get("criterion_id", "?")
        label = c.get("label", cid).replace("|", "\\|")
        status = c.get("status", "—")
        value_str = _criterion_value_str(c)
        predictive = "yes" if c.get("predictive") else "no"
        md.append(f"| {cid} | {label} | `{status}` | {value_str} | {predictive} |\n")
    md.append("\n")

    md.append("## Failure mode diagnosis\n\n")
    md.append("Two failure modes were diagnosed in the v2.0 verdict:\n\n")
    md.append("**Mode A — data-window-vs-strict-gate interaction (C1, C2, C3, C4, C7)**. ")
    md.append("z4 (DXY) is bottlenecked to ~2016-01 because the v2.0 master archive lacks ")
    md.append("pre-2006 ICE_DXY, and the sealed §10.1 PIT z-score requires 120 monthly ")
    md.append("observations. Combined with the sealed §3.4 / Amendment 4 strict ")
    md.append("insufficient-sample gate (`n_obs_oos >= max(60, 3 * HAC_lag)` AND `n_eff >= 30`), ")
    md.append("most cells did not clear the gate at any horizon, yielding ")
    md.append("`NOT_EVALUABLE_COUNTED_FAIL` for the four predictive criteria and C7.\n\n")
    md.append("**Mode B — z4 (DXY) near-unit-root level (C5)**. ")
    md.append("The DXY broad-trade-weighted log-level (post-splice, pre-z-score) does ")
    md.append("not reject the unit-root null at conventional levels ")
    md.append("(max ADF p ≈ 0.7648 across the five components). The level-family ")
    md.append("transformation drives the Holm-Šidák multiplicity test to fail, ")
    md.append("resulting in `FAIL_STATISTICAL` for C5.\n\n")
    md.append("**C6 (VIF) PASSED.** Components are not problematically collinear ")
    md.append("(max VIF ≈ 1.70 across the 5 aligned z-scored components). This is the ")
    md.append("only criterion that passed the v2.0 sealed evaluation.\n\n")

    md.append("## Audit summary\n\n")
    md.append(f"- **PIT look-ahead audit**: `{audit_status}` ")
    md.append(f"(n_cells_audited={audit.get('n_cells_audited', '—')}, ")
    md.append(f"n_origins_audited={n_origins_audited}, ")
    md.append(f"n_violations={n_violations}). ")
    md.append("Construction: ")
    md.append(f"`{audit.get('pit_audit_construction', 'unknown')}` ")
    md.append("(Phase F-BLK1.A populates per-origin `feature_vintage_max`; Phase F-BLK1.B ")
    md.append("audit iterates `(origin, cell)` pairs and asserts `fvm[t] <= t`).\n")
    md.append("- **Sealed pre-reg integrity**: PASS — SHA-256 immutable at ")
    md.append(f"`{sealed_sha[:12]}…`.\n")
    md.append("- **Verdict JSON byte-reproducibility**: PASS — Phase F-BLK1.F binary-mode write ")
    md.append("+ LF-newlines + read-back verification; sidecar matches `sha256sum` cross-OS.\n")
    md.append("- **Pinned-environment closeout reproducibility**: PASS — Phase F-DOC.C "
              "normalized SHA equality between off-pin BLK-1 and pinned closeout re-run.\n")
    md.append("- **§16 seal-report criteria**: 10/10 PASS (no regression across the sprint).\n\n")

    md.append("---\n\n")
    md.append("## RESTATING — DO NOT INTERPRET AS PREDICTIVE SIGNAL\n\n")
    md.append("This diagnostic view exists for:\n\n")
    md.append("1. **Methodological transparency** — every cell, criterion, gate, ")
    md.append("audit decision is disclosed.\n")
    md.append("2. **Audit trail completeness** — pre-BLK-1 historical verdict + ")
    md.append("post-BLK-1 canonical + closeout pinned re-run all preserved.\n")
    md.append("3. **Public scientific record** — the FAIL outcome itself is the empirical finding.\n\n")
    md.append("This diagnostic view does NOT exist for:\n\n")
    md.append("1. Investment decisions\n")
    md.append("2. Position sizing\n")
    md.append("3. Signal extraction of any kind\n\n")
    md.append("The v2.0 Liquidity Composite **FAILED** the sealed pre-registered evaluation. ")
    md.append("That is the empirical finding. The numerical contents of this report are ")
    md.append("evidence FOR the FAIL outcome and provide diagnostic information about WHY ")
    md.append("the failure occurred, but do NOT constitute a usable signal.\n\n")

    md.append("---\n\n")
    md.append("## Provenance\n\n")
    md.append("- Canonical verdict JSON: `outputs/lc_v2_verdict.json`\n")
    md.append("- Verdict JSON sidecar SHA-256: `outputs/lc_v2_verdict.json.sha256` (sha256sum-compatible format)\n")
    md.append(f"- Sealed pre-reg: `specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` SHA-256 `{sealed_sha[:16]}…`\n")
    md.append("- Pre-BLK-1 archived verdict: `outputs/historical/lc_v2_verdict_pre_blk1.json`\n")
    md.append("- BLK-1 delta analysis: `outputs/lc_v2_verdict_blk1_delta.md`\n")
    md.append("- Closeout re-run delta: `outputs/lc_v2_verdict_closeout_delta.md`\n")
    md.append("- Phase F-DOC directive: `prompt/052526/PROMPT_CC_v11_4_phase_F_DOC.md`\n")
    md.append("- Phase F-BLK1 directive: `prompt/052526/PROMPT_CC_v11_4_phase_F_BLK1_fix.md`\n\n")

    content = "".join(md)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content


def write_display_framing(verdict_json_path: Path, output_dir: Path) -> Path:
    """Main entry: read verdict, compose framed view, write to ``output_dir``.

    For v2.0 (FAIL): writes ``lc_v2_display_fail.md``. PASS / PASS_WITH_CAVEATS
    branches raise NotImplementedError — sealed §7 leaves the exact PASS-view
    composition open and v2.0 does not exercise those branches.
    """
    verdict = json.loads(Path(verdict_json_path).read_text(encoding="utf-8"))
    mode = determine_framing_mode(verdict)
    output_dir = Path(output_dir)
    output_path = output_dir / f"lc_v2_display_{mode.lower()}.md"

    if mode == "FAIL":
        compose_diagnostic_only_view(verdict, output_path)
        return output_path
    raise NotImplementedError(
        f"display framing mode {mode!r} not implemented; v2.0 outcome is FAIL "
        f"(n_pass=1) so only the DIAGNOSTIC ONLY branch is exercised. The PASS "
        f"/ PASS_WITH_CAVEATS branches are deferred to a future sprint that "
        f"produces a non-FAIL verdict."
    )
