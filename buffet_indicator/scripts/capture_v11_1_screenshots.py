"""v11.1 — capture 10 screenshots covering Strategy Engine + Methodology + L1-L4 fix verification."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


DASHBOARD = Path("outputs/dashboard.html").resolve()
OUT_DIR = Path("outputs/screenshots/v11_1")
DESKTOP = (1920, 1080)


def capture() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {"captures": []}
    width, height = DESKTOP

    targets = [
        # (filename, tab, group, post_action, settle_ms)
        ("01_overview_with_strategy_engine_link", "overview", "overview", None, 1500),
        ("02_strategy_engine_header_with_kpis", "strategy_engine", "analysis", None, 2500),
        ("03_strategy_engine_core_analytics_subtab", "strategy_engine", "analysis", "showSeGroup('core')", 2500),
        ("04_strategy_engine_robustness_subtab", "strategy_engine", "analysis", "showSeGroup('robustness')", 2500),
        ("05_strategy_engine_institutional_subtab", "strategy_engine", "analysis", "showSeGroup('institutional')", 2500),
        ("06_strategy_engine_gap_closers_subtab", "strategy_engine", "analysis", "showSeGroup('gap_closers')", 2500),
        ("07_strategy_engine_governance_modal", "strategy_engine", "analysis",
         "showSeGroup('gap_closers'); document.querySelector('details[data-sheet=\"Governance\"]').open = true",
         2500),
        ("08_methodology_with_v50_section", "methodology", "reference",
         "document.querySelector('h2.text-xl.font-bold.mb-2')?.scrollIntoView()", 1500),
        ("09_deprecated_backtest_banner", "backtest", "analysis", None, 1500),
        ("10_layout_fix_verification_hy_ig", "spread_hy_ig", "macro_risk", None, 2500),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, tab, group, action, settle in targets:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors: list[str] = []
            page.on("pageerror", lambda e, errs=errors: errs.append(str(e)))
            page.on(
                "console",
                lambda msg, errs=errors: errs.append(f"console.{msg.type}: {msg.text}")
                if msg.type == "error"
                else None,
            )
            page.goto(f"file://{DASHBOARD}", wait_until="domcontentloaded")
            # Click the right nav button
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
                    page.wait_for_timeout(1500)
                except Exception as e:
                    errors.append(f"post_action_failed: {e}")
            out_path = OUT_DIR / f"{name}.png"
            page.screenshot(path=str(out_path), full_page=True)
            size = out_path.stat().st_size
            results["captures"].append(
                {"name": name, "tab": tab, "size_bytes": size, "errors": errors}
            )
            page.close()
        browser.close()
    (OUT_DIR / "_capture_log.json").write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    r = capture()
    for c in r["captures"]:
        flag = "OK " if c["size_bytes"] > 100_000 and not c["errors"] else "FAIL"
        print(f"  [{flag}] {c['name']}: {c['size_bytes']:>8d}B errors={len(c['errors'])}")
