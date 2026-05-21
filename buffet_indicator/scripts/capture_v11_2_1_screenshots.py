"""v11.2.1 — capture screenshots covering all 9 Extended Analytics surfaces +
regression touchpoints. Each surface is a <details> block; the capture script
opens it programmatically before scrolling and snapshotting.

Targets (15 total):
  01_overview_regression
  02_strategy_engine_v1_lineup_regression
  03_strategy_engine_v2_banner_regression
  04_ea_surface_1_summary
  05_ea_surface_2_drawdowns
  06_ea_surface_3_rolling
  07_ea_surface_4_risk_metrics
  08_ea_surface_5_returns
  09_ea_surface_6_lump_sum
  10_ea_surface_7_risk_vs_return
  11_ea_surface_8_withdrawal
  12_ea_surface_9_seasonality
  13_methodology_regression
  14_diagnostics_regression
  15_pushstate_routing_working
"""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

DASHBOARD = Path("outputs/dashboard.html").resolve()
OUT_DIR = Path("outputs/screenshots/v11_2_1")
DESKTOP = (1920, 1080)
TAILWIND = "cdn.tailwindcss.com should not be used in production"


def _ok_warning(text: str) -> bool:
    return TAILWIND in (text or "")


def _open_surface(page, surface_id: str) -> None:
    """Open a <details id=...> element + scroll it into view."""
    page.evaluate(
        """(sid) => {
            const el = document.getElementById(sid);
            if (el) {
                el.open = true;
                el.scrollIntoView({block: 'start'});
            }
        }""",
        surface_id,
    )


def capture() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {"captures": [], "all_console_errors": []}
    width, height = DESKTOP

    surface_targets = [
        ("01_overview_regression", "overview", None, 2500),
        ("02_strategy_engine_v1_lineup_regression", "strategy_engine", None, 2500),
        ("03_strategy_engine_v2_banner_regression", "strategy_engine",
         "() => document.getElementById('v2-diagnostic-banner').scrollIntoView({block:'start'})", 2500),
        ("04_ea_surface_1_summary", "strategy_engine", "ea-surface-1-summary", 2500),
        ("05_ea_surface_2_drawdowns", "strategy_engine", "ea-surface-2-drawdowns", 2500),
        ("06_ea_surface_3_rolling", "strategy_engine", "ea-surface-3-rolling", 2500),
        ("07_ea_surface_4_risk_metrics", "strategy_engine", "ea-surface-4-risk-metrics", 2500),
        ("08_ea_surface_5_returns", "strategy_engine", "ea-surface-5-returns", 2500),
        ("09_ea_surface_6_lump_sum", "strategy_engine", "ea-surface-6-lump-sum", 2500),
        ("10_ea_surface_7_risk_vs_return", "strategy_engine", "ea-surface-7-risk-vs-return", 2500),
        ("11_ea_surface_8_withdrawal", "strategy_engine", "ea-surface-8-withdrawal", 2500),
        ("12_ea_surface_9_seasonality", "strategy_engine", "ea-surface-9-seasonality", 2500),
        ("13_methodology_regression", "methodology", None, 2500),
        ("14_diagnostics_regression", "diagnostics", None, 2500),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, tab, surface_or_action, settle in surface_targets:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors: list[str] = []
            warns: list[str] = []
            page.on("pageerror", lambda e, errs=errors: errs.append(str(e)))

            def on_console(msg, errs=errors, wns=warns):
                t = msg.type
                if t == "error":
                    errs.append(f"console.error: {msg.text}")
                elif t == "warning" and not _ok_warning(msg.text):
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
            if surface_or_action:
                try:
                    if surface_or_action.startswith("ea-surface-"):
                        _open_surface(page, surface_or_action)
                    else:
                        page.evaluate(surface_or_action)
                    page.wait_for_timeout(1200)
                except Exception as e:
                    errors.append(f"surface_open_failed: {e}")
            out_path = OUT_DIR / f"{name}.png"
            page.screenshot(path=str(out_path), full_page=True)
            size = out_path.stat().st_size
            results["captures"].append({
                "name": name, "tab": tab, "size_bytes": size,
                "n_errors": len(errors), "n_warns": len(warns),
                "errors": errors[:3], "warns": warns[:3],
            })
            results["all_console_errors"].extend(errors)
            page.close()

        # 15: pushState back-button restoration.
        page = browser.new_page(viewport={"width": width, "height": height})
        errors: list[str] = []
        warns: list[str] = []
        page.on("pageerror", lambda e, errs=errors: errs.append(str(e)))

        def on_console15(msg, errs=errors, wns=warns):
            t = msg.type
            if t == "error":
                errs.append(f"console.error: {msg.text}")
            elif t == "warning" and not _ok_warning(msg.text):
                wns.append(f"console.warn: {msg.text}")

        page.on("console", on_console15)
        page.goto(f"file://{DASHBOARD}", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        for tab_name in ("strategy_engine", "methodology"):
            page.evaluate(
                "(t) => { const b = document.querySelector('.tab-button[data-tab=\"' + t + '\"]'); if (b) b.click(); }",
                tab_name,
            )
            page.wait_for_timeout(1300)
        page.go_back()
        page.wait_for_timeout(2200)
        restored = page.evaluate(
            "() => { const el = document.querySelector('section[data-tab].tab-content.active'); return el ? el.getAttribute('data-tab') : null; }"
        )
        if restored != "strategy_engine":
            errors.append(f"pushState restore: expected strategy_engine, got {restored!r}")
        out_path = OUT_DIR / "15_pushstate_routing_working.png"
        page.screenshot(path=str(out_path), full_page=True)
        results["captures"].append({
            "name": "15_pushstate_routing_working", "tab": "strategy_engine (restored)",
            "restored_tab_observed": restored, "size_bytes": out_path.stat().st_size,
            "n_errors": len(errors), "n_warns": len(warns),
            "errors": errors[:3], "warns": warns[:3],
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
        for e in c["errors"]:
            print(f"        ERROR: {e[:120]}")
    print()
    print(f"Total unique console errors: {len(set(r['all_console_errors']))}")
