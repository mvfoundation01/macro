"""v11.1.1 — capture 5 screenshots verifying the 4 hotfixes.

Plus full console-error sweep across all tabs to verify C1 + C2 fixes."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


DASHBOARD = Path("outputs/dashboard.html").resolve()
OUT_DIR = Path("outputs/screenshots/v11_1_1")
DESKTOP = (1920, 1080)


def capture() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {"captures": [], "all_console_errors": []}
    width, height = DESKTOP

    targets = [
        ("01_overview_mvci_mrc_chart_fixed", "overview", None, 2500),
        ("02_strategy_engine_v1_lineup_full", "strategy_engine", None, 2500),
        ("03_hy_ig_conditional_dist_bayesian", "spread_hy_ig", None, 2500),
        ("04_overview_full_page", "overview", None, 2500),
        ("05_strategy_engine_full_page", "strategy_engine", None, 2500),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, tab, action, settle in targets:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors: list[str] = []
            warns: list[str] = []
            page.on("pageerror", lambda e, errs=errors: errs.append(str(e)))

            def on_console(msg, errs=errors, wns=warns):
                t = msg.type
                if t == "error":
                    errs.append(f"console.error: {msg.text}")
                elif t == "warning":
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
        browser.close()
    (OUT_DIR / "_capture_log.json").write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    r = capture()
    for c in r["captures"]:
        flag = "OK " if c["size_bytes"] > 100_000 and c["n_errors"] == 0 else "WARN"
        print(f"  [{flag}] {c['name']}: {c['size_bytes']:>8d}B err={c['n_errors']} warn={c['n_warns']}")
        if c["errors"]:
            for e in c["errors"]:
                print(f"        ERROR: {e[:120]}")
        if c["warns"]:
            for w in c["warns"]:
                print(f"        WARN:  {w[:120]}")
    print()
    print(f"Total unique console errors across all tabs: {len(set(r['all_console_errors']))}")
