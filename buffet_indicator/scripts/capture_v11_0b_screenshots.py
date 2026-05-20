"""v11.0b — Capture 19 Playwright headless screenshots of the dashboard.

Acceptance per PROMPT_v11_0_b §H.3:
- Each PNG > 100 KB
- 0 page errors during capture
- Macro-risk tabs show coloured regime callout, at least one chart, no
  "[object Object]" strings
"""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


DASHBOARD = Path("outputs/dashboard.html").resolve()
OUT_DIR = Path("outputs/screenshots/v11_0b")
DESKTOP = (1920, 1080)
MOBILE = (390, 844)


TARGETS = [
    ("01_overview_desktop", "#tab=overview", DESKTOP),
    ("02_overview_macro_snapshot_closeup", "#tab=overview", DESKTOP),
    ("03_tab_mrc_desktop", "#tab=mrc&group=macro_risk", DESKTOP),
    ("04_tab_mrc_mobile", "#tab=mrc&group=macro_risk", MOBILE),
    ("05_tab_yc_10y3m_desktop", "#tab=yc_10y3m&group=macro_risk", DESKTOP),
    ("06_tab_yc_10y2y_desktop", "#tab=yc_10y2y&group=macro_risk", DESKTOP),
    ("07_tab_cs_hy_master_desktop", "#tab=cs_hy_master&group=macro_risk", DESKTOP),
    ("08_tab_cs_ig_master_desktop", "#tab=cs_ig_master&group=macro_risk", DESKTOP),
    ("09_tab_cs_hy_bb_desktop", "#tab=cs_hy_bb&group=macro_risk", DESKTOP),
    ("10_tab_cs_hy_ccc_desktop", "#tab=cs_hy_ccc&group=macro_risk", DESKTOP),
    ("11_tab_margin_debt_desktop", "#tab=margin_debt_growth&group=macro_risk", DESKTOP),
    ("12_tab_buffett_recession_overlay_check", "#tab=buffett&group=valuation", DESKTOP),
    ("13_tab_cape_recession_overlay_check", "#tab=cape&group=valuation", DESKTOP),
    ("14_tab_mean_reversion_recession_overlay_check", "#tab=mean_reversion&group=valuation", DESKTOP),
    ("15_tab_diagnostics_desktop", "#tab=diagnostics&group=analysis", DESKTOP),
    ("16_tab_backtest_desktop", "#tab=backtest&group=analysis", DESKTOP),
    ("17_tab_methodology_desktop", "#tab=methodology&group=reference", DESKTOP),
    ("18_nav_macro_risk_expanded_desktop", "#tab=mrc&group=macro_risk", DESKTOP),
    ("19_cross_composite_quadrant_closeup", "#tab=mrc&group=macro_risk", DESKTOP),
]


def _hash_to_tab(hash_url: str) -> str | None:
    h = hash_url.lstrip("#")
    for kv in h.split("&"):
        if kv.startswith("tab="):
            return kv.split("=", 1)[1]
    return None


def main() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {"captures": [], "errors_global": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, hash_url, (width, height) in TARGETS:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors: list[str] = []
            page.on("pageerror", lambda e, errs=errors: errs.append(str(e)))
            page.on(
                "console",
                lambda msg, errs=errors: errs.append(f"console.{msg.type}: {msg.text}")
                if msg.type == "error"
                else None,
            )
            # Pre-seed localStorage with the target tab so the dashboard.js
            # initTabs() activates it directly (this is the storage key the
            # existing JS reads).
            tab = _hash_to_tab(hash_url) or "overview"
            page.goto(f"file://{DASHBOARD}", wait_until="domcontentloaded")
            page.evaluate(
                "(t) => { window.localStorage.setItem('mv_active_tab', t); }", tab
            )
            page.goto(
                f"file://{DASHBOARD}{hash_url}", wait_until="domcontentloaded"
            )
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(2000)
            # Force-click the target tab as a belt-and-braces measure (covers
            # the case where pre-seed localStorage didn't survive navigation).
            page.evaluate(
                """(t) => {
                    const btn = document.querySelector('.tab-button[data-tab="' + t + '"]');
                    if (btn) btn.click();
                }""",
                tab,
            )
            page.wait_for_timeout(1200)
            out_path = OUT_DIR / f"{name}.png"
            # Always full_page so the tall macro tabs (header + hero + 3-panel
            # + regression table + probability table + interpretation +
            # about) are captured in their entirety. Mobile renders the
            # tabs as a vertical stack so full_page is essential there.
            page.screenshot(path=str(out_path), full_page=True)
            size = out_path.stat().st_size if out_path.exists() else 0
            results["captures"].append(
                {
                    "name": name,
                    "hash": hash_url,
                    "viewport": (width, height),
                    "size_bytes": size,
                    "errors": errors,
                }
            )
            page.close()
        browser.close()
    log_path = OUT_DIR / "_capture_log.json"
    log_path.write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    r = main()
    n_ok = sum(
        1 for c in r["captures"] if c["size_bytes"] > 100_000 and not c["errors"]
    )
    n_total = len(r["captures"])
    print(f"captured {n_total}; PASS-quality (>100KB, 0 console errors) = {n_ok}")
    for c in r["captures"]:
        flag = "OK " if c["size_bytes"] > 100_000 and not c["errors"] else "FAIL"
        print(
            f"  [{flag}] {c['name']}: {c['size_bytes']:>8d}B errors={len(c['errors'])}"
        )
