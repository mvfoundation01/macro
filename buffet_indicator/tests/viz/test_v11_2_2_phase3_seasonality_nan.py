"""Regression test for v11.2.2-p1 B1 residual fix.

Investigation Report `INVESTIGATION_REPORT_v11_2_2_session_1.md` flagged that
v11.2.2-p0's source-grep verification missed Plotly format-string warnings.
Phase 2 diagnosis (`reviews/PHASE_2_diagnosis_notes.md`) showed Plotly 2.35.2
emits ``WARN: encountered bad format`` for ``:+.Nf`` placeholders in
``hovertemplate``. The 'fix' was to strip ``+`` sign-modifiers from all Plotly
hovertemplate format placeholders source-side (chart_specs.py + the seasonality
template).

These tests act as a tripwire — if a future commit reintroduces a Plotly
hovertemplate with ``+.Nf``, the dashboard build + this test will fail.
"""
from __future__ import annotations

import json
import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DASHBOARD_HTML = REPO_ROOT / "outputs" / "dashboard.html"


def _read_dashboard() -> str:
    if not DASHBOARD_HTML.exists():
        return ""
    return DASHBOARD_HTML.read_text(encoding="utf-8")


def test_no_plotly_hovertemplate_with_signed_format():
    """No Plotly hovertemplate placeholder may use ``:+.Nf`` style format.

    Plotly 2.35.2 emits ``encountered bad format`` warnings for these; they are
    cosmetic (Plotly still renders) but produce console noise that obscures real
    bugs. Use plain ``:.Nf`` or pre-format via the ``text`` field instead.
    """
    html = _read_dashboard()
    if not html:
        # Dashboard not built; nothing to check. Don't gate CI on this.
        return
    pattern = re.compile(r'%\{[a-z]:\+\.[0-9]+[fge]')
    matches = pattern.findall(html)
    assert not matches, (
        f"Found {len(matches)} Plotly +.Nf format placeholders in dashboard.html: "
        f"{matches[:5]}. These trigger Plotly d3-format warnings — switch to :.Nf."
    )


def test_seasonality_heatmap_uses_pretext_in_hovertemplate():
    """Seasonality heatmap (Surface 9) hovertemplate must use ``%{text}``.

    The pre-formatted ``mean_fmt`` strings (e.g. ``"+0.83%"``) live in the
    ``text`` field; using ``%{text}`` avoids any Plotly format parsing.
    """
    html = _read_dashboard()
    if not html:
        return
    # Locate the seasonality heatmap script block
    m = re.search(
        r'ea-surface-9-seasonality-heatmap.*?hovertemplate:\s*"([^"]+)"',
        html, re.DOTALL,
    )
    if not m:
        # Surface not present in this build — skip
        return
    hovertemplate = m.group(1)
    assert "%{text}" in hovertemplate, (
        f"Surface 9 seasonality hovertemplate should use %{{text}} (pre-formatted). "
        f"Got: {hovertemplate!r}"
    )
    assert ":+.2f" not in hovertemplate, (
        f"Surface 9 hovertemplate still uses :+.2f — regression. Got: {hovertemplate!r}"
    )


def test_phase3_playwright_capture_zero_bad_format():
    """If a Phase 3 Playwright capture log exists, it must show 0 bad-format warnings.

    Skipped when the capture file is absent (e.g., CI without browser).
    """
    log_path = REPO_ROOT / "reviews" / "diagnostic_artifacts" / "console_file_protocol_v3.json"
    if not log_path.exists():
        return  # capture not run — skip silently
    data = json.loads(log_path.read_text(encoding="utf-8"))
    messages = data.get("messages", [])
    bad_format = [m for m in messages if "encountered bad format" in m.get("text", "")]
    assert not bad_format, (
        f"Playwright capture shows {len(bad_format)} bad-format warnings. "
        f"First: {bad_format[0] if bad_format else None}. "
        f"Re-run reviews/diagnostic_artifacts/capture_console_file_v3.py after the fix."
    )
