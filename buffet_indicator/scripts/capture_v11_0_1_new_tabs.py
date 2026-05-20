"""v11.0.1 — capture 6 new derived-spread screenshots."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


DASHBOARD = Path("outputs/dashboard.html").resolve()
OUT_DIR = Path("outputs/screenshots/v11_0_1")
DESKTOP = (1920, 1080)


TARGETS = [
    ("20_tab_spread_hy_ig_desktop", "spread_hy_ig"),
    ("21_tab_spread_ccc_bb_desktop", "spread_ccc_bb"),
    ("22_tab_spread_hy_reach_for_yield_desktop", "spread_hy_reach_for_yield"),
    ("23_tab_spread_hy_treasury_traditional_desktop", "spread_hy_treasury_traditional"),
    ("24_tab_spread_equity_credit_rp_desktop", "spread_equity_credit_rp"),
    ("25_tab_spread_hy_oas_3m_delta_desktop", "spread_hy_oas_3m_delta"),
]


def capture() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {"captures": []}
    width, height = DESKTOP
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, tab in TARGETS:
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
            page.evaluate(
                "(t) => window.localStorage.setItem('mv_active_tab', t)", tab
            )
            page.goto(
                f"file://{DASHBOARD}#tab={tab}&group=macro_risk",
                wait_until="domcontentloaded",
            )
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:
                pass
            page.wait_for_timeout(1800)
            page.evaluate(
                """(t) => {
                    const btn = document.querySelector('.tab-button[data-tab="' + t + '"]');
                    if (btn) btn.click();
                }""",
                tab,
            )
            page.wait_for_timeout(1500)
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
