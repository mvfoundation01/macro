"""v11.2 Stage 12 — pushState routing fix tests.

Verifies the routing JS in src/viz/templates/_header.html uses pushState +
popstate listener so back/forward buttons traverse tab history (per
PROMPT_v11_2 §9 Strategist decision).
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HEADER_HTML = REPO_ROOT / "src" / "viz" / "templates" / "_header.html"


def _read_header() -> str:
    assert HEADER_HTML.exists(), f"missing {HEADER_HTML}"
    return HEADER_HTML.read_text(encoding="utf-8")


def test_dashboard_uses_pushstate_not_replacestate():
    """Tab navigation must use pushState; replaceState only for the initial entry."""
    text = _read_header()
    assert "history.pushState" in text, "no history.pushState in routing JS"
    # replaceState may still be used ONCE (for initial state) — verify exactly that pattern.
    rs_count = text.count("history.replaceState")
    ps_count = text.count("history.pushState")
    assert ps_count >= 1, "history.pushState missing"
    assert rs_count <= 1, (
        f"history.replaceState used {rs_count} times — should be ≤ 1 (initial state only)"
    )


def test_popstate_listener_present():
    """A popstate event listener must be registered to handle back/forward buttons."""
    text = _read_header()
    assert "addEventListener(\"popstate\"" in text or "addEventListener('popstate'" in text, (
        "no popstate listener — back/forward buttons won't restore tabs"
    )


def test_initial_load_reads_hash():
    """DOMContentLoaded handler must read the hash and activate the matching tab."""
    text = _read_header()
    assert "DOMContentLoaded" in text, "no DOMContentLoaded handler in routing JS"
    # The init path should call activateFromHash (or equivalent) so a deep-linked
    # hash like #tab=mvci displays the right tab on first load.
    assert "activateFromHash" in text, "activateFromHash not invoked on init"
    # The state must be seeded so the first popstate has somewhere to land.
    assert "fromInit" in text or "history.replaceState" in text, (
        "initial entry should be seeded via replaceState"
    )
