"""v11.2-stat — capture 5 screenshots per Part A §A.4.

Targets:
  01_overview_with_mvci_mrc           — Overview (regression: v11.1.1 I1 fix)
  02_strategy_engine_with_v2_banner   — Strategy Engine tab w/ V2 DIAGNOSTIC banner
  03_strategy_engine_v1_17_lineup     — Strategy Engine V1 lineup (regression: I2)
  04_methodology_intact               — Methodology tab (regression)
  05_pushstate_routing_working        — restored tab after back-button (pushState fix)

Gates: each PNG > 100 KB, total console errors == 0 (Tailwind CDN warning ok).
"""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

DASHBOARD = Path("outputs/dashboard.html").resolve()
OUT_DIR = Path("outputs/screenshots/v11_2_stat")
DESKTOP = (1920, 1080)
TAILWIND_CDN_WARNING_FRAGMENT = "cdn.tailwindcss.com should not be used in production"


def _is_acceptable_warning(text: str) -> bool:
    return TAILWIND_CDN_WARNING_FRAGMENT in (text or "")


def capture() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {"captures": [], "all_console_errors": []}
    width, height = DESKTOP

    # Per Part A spec: each capture has (name, target-tab, optional-pre-action, settle-ms).
    static_targets = [
        ("01_overview_with_mvci_mrc", "overview", None, 2500),
        # Full strategy_engine page — banner is at the bottom of the tab content.
        ("02_strategy_engine_with_v2_banner", "strategy_engine",
         "document.getElementById('v2-diagnostic-banner').scrollIntoView({block:'start'})", 2500),
        ("03_strategy_engine_v1_17_lineup", "strategy_engine", None, 2500),
        ("04_methodology_intact", "methodology", None, 2500),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, tab, action, settle in static_targets:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors: list[str] = []
            warns: list[str] = []
            page.on("pageerror", lambda e, errs=errors: errs.append(str(e)))

            def on_console(msg, errs=errors, wns=warns):
                t = msg.type
                if t == "error":
                    errs.append(f"console.error: {msg.text}")
                elif t == "warning":
                    if _is_acceptable_warning(msg.text):
                        return
                    wns.append(f"console.warn: {msg.text}")

            page.on("console", on_console)
            page.goto(f"file://{DASHBOARD}", wait_until="domcontentloaded")
            page.evaluate(
                """(t) => {
                    const btn = document.querySelector('.tab-button[data-tab="' + t + '"]');
                    if (btn) btn.click();
                }""",
                tab,
            )
            page.wait_for_timeout(settle)
            if action:
                try:
                    page.evaluate(action)
                    page.wait_for_timeout(1000)
                except Exception as e:
                    errors.append(f"post_action_failed: {e}")
            out_path = OUT_DIR / f"{name}.png"
            page.screenshot(path=str(out_path), full_page=True)
            size = out_path.stat().st_size
            results["captures"].append({
                "name": name, "tab": tab, "size_bytes": size,
                "n_errors": len(errors), "n_warns": len(warns),
                "errors": errors[:5], "warns": warns[:5],
            })
            results["all_console_errors"].extend(errors)
            page.close()

        # ── 05: pushState routing — back button restores prior tab ──
        page = browser.new_page(viewport={"width": width, "height": height})
        errors: list[str] = []
        warns: list[str] = []
        page.on("pageerror", lambda e, errs=errors: errs.append(str(e)))

        def on_console5(msg, errs=errors, wns=warns):
            t = msg.type
            if t == "error":
                errs.append(f"console.error: {msg.text}")
            elif t == "warning" and not _is_acceptable_warning(msg.text):
                wns.append(f"console.warn: {msg.text}")

        page.on("console", on_console5)
        page.goto(f"file://{DASHBOARD}", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        # 1) click strategy_engine → pushState adds entry
        page.evaluate("""() => {
            const btn = document.querySelector('.tab-button[data-tab="strategy_engine"]');
            if (btn) btn.click();
        }""")
        page.wait_for_timeout(1500)

        # 2) click methodology → pushState adds another entry
        page.evaluate("""() => {
            const btn = document.querySelector('.tab-button[data-tab="methodology"]');
            if (btn) btn.click();
        }""")
        page.wait_for_timeout(1500)

        # 3) press browser back → popstate listener should restore strategy_engine
        page.go_back()
        page.wait_for_timeout(2500)

        # Verify the restored tab is strategy_engine.
        # Tabs use ".tab-content.active" CSS class (per dashboard.js showTab).
        restored_tab = page.evaluate(
            "() => { const el = document.querySelector('section[data-tab].tab-content.active'); return el ? el.getAttribute('data-tab') : null; }"
        )
        if restored_tab != "strategy_engine":
            errors.append(f"pushState restore failed: expected 'strategy_engine', got {restored_tab!r}")

        out_path = OUT_DIR / "05_pushstate_routing_working.png"
        page.screenshot(path=str(out_path), full_page=True)
        size = out_path.stat().st_size
        results["captures"].append({
            "name": "05_pushstate_routing_working",
            "tab": "strategy_engine (restored from methodology via back-button)",
            "restored_tab_observed": restored_tab,
            "size_bytes": size,
            "n_errors": len(errors), "n_warns": len(warns),
            "errors": errors[:5], "warns": warns[:5],
        })
        results["all_console_errors"].extend(errors)
        page.close()
        browser.close()

    (OUT_DIR / "_capture_log.json").write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    r = capture()
    print()
    for c in r["captures"]:
        flag = "OK  " if c["size_bytes"] > 100_000 and c["n_errors"] == 0 else "WARN"
        print(f"  [{flag}] {c['name']}: {c['size_bytes']:>8d}B err={c['n_errors']} warn={c['n_warns']}")
        if c["errors"]:
            for e in c["errors"]:
                print(f"        ERROR: {e[:120]}")
        if c["warns"]:
            for w in c["warns"]:
                print(f"        WARN:  {w[:120]}")
    print()
    print(f"Total unique console errors across 5-tab sweep: {len(set(r['all_console_errors']))}")
