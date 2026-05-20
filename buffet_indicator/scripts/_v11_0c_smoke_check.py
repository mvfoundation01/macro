"""v11.0c — quick smoke check: per-tab header pills + chart render counts."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

DASHBOARD = Path("outputs/dashboard.html").resolve()


def check() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for tab in [
            "overview", "mrc", "yc_10y3m", "yc_10y2y",
            "cs_hy_master", "cs_ig_master", "cs_hy_bb", "cs_hy_ccc",
            "margin_debt_growth",
        ]:
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(f"file://{DASHBOARD}", wait_until="domcontentloaded")
            page.evaluate(
                "(t) => localStorage.setItem('mv_active_tab', t)", tab
            )
            page.goto(
                f"file://{DASHBOARD}#tab={tab}", wait_until="domcontentloaded"
            )
            page.wait_for_timeout(2000)
            page.evaluate(
                """(t) => {
                    const b = document.querySelector('.tab-button[data-tab="' + t + '"]');
                    if (b) b.click();
                }""",
                tab,
            )
            page.wait_for_timeout(1200)
            data = page.evaluate(
                """() => {
                    const pills = {
                        z: document.querySelector('[data-pill="z"]').textContent.trim(),
                        p: document.querySelector('[data-pill="p_neg"]').textContent.trim(),
                        c: document.querySelector('[data-pill="confidence"]').textContent.trim(),
                        v: document.querySelector('[data-pill="conviction"]').textContent.trim(),
                    };
                    const active = document.querySelector('.tab-content.active');
                    const tabName = active ? active.dataset.tab : 'none';
                    return {pills, tabName};
                }"""
            )
            pills = data["pills"]
            # ASCII-only for Windows cp1252 print safety
            def safe(s: str) -> str:
                return (s or "").replace("σ", "s").replace("×", "x")
            print(
                f"[{tab:22s}] active={data['tabName']:22s} "
                f"z={safe(pills['z']):10s} p={safe(pills['p']):10s} "
                f"conf={safe(pills['c']):8s} conv={safe(pills['v']):10s}"
            )
            page.close()
        browser.close()


if __name__ == "__main__":
    check()
