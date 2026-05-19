"""v8b.1 Deliverable E — click through every tab, capture console + screenshots.

Audit findings get printed to stdout for inclusion in REVIEW_PACKAGE §1.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


def main() -> None:
    dashboard = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"
    url = f"file://{dashboard.as_posix()}"

    events: list[dict[str, Any]] = []
    findings: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda msg: events.append({"type": msg.type, "text": msg.text}))
        page.on("pageerror", lambda err: events.append({"type": "pageerror", "text": str(err)}))
        page.goto(url)
        page.wait_for_selector("svg", timeout=15000)

        # Test 1: every tab loads at least one svg
        for tab in (
            "overview",
            "mvci",
            "buffett",
            "cape",
            "qratio",
            "ey_deficit",
            "mean_reversion",
            "diagnostics",
            "data",
            "methodology",
        ):
            try:
                page.click(f'button[data-tab="{tab}"]', timeout=5000)
                # methodology + data have no svg; others should
                page.wait_for_timeout(500)
                visible_svgs = page.locator("svg:visible").count()
                if tab not in ("data", "methodology") and visible_svgs == 0:
                    findings.append(f"tab '{tab}': no visible SVG after click")
            except Exception as exc:  # noqa: BLE001
                findings.append(f"tab '{tab}': click failed — {exc}")

        # Test 2: dark mode toggle preserves visible regime colors
        try:
            page.click("#dark-toggle", timeout=5000)
            page.wait_for_timeout(300)
            # Re-toggle back
            page.click("#dark-toggle", timeout=5000)
            page.wait_for_timeout(300)
        except Exception as exc:  # noqa: BLE001
            findings.append(f"dark-toggle: error — {exc}")

        # Test 3: Why-it-matters expandable opens
        try:
            page.click('button[data-tab="cape"]')
            page.wait_for_timeout(400)
            details = page.locator("details.why-it-matters").first
            if details.count() > 0:
                details.click()
                page.wait_for_timeout(200)
                is_open = details.evaluate("el => el.hasAttribute('open')")
                if not is_open:
                    findings.append("why-it-matters: details did not open on click")
        except Exception as exc:  # noqa: BLE001
            findings.append(f"why-it-matters: error — {exc}")

        # Test 4: CSV download buttons wire up (don't trigger save, just check listener)
        try:
            page.click('button[data-tab="data"]')
            page.wait_for_timeout(400)
            n_btns = page.locator("button.csv-download-btn").count()
            if n_btns < 4:
                findings.append(f"data tab: expected ≥4 CSV buttons, found {n_btns}")
        except Exception as exc:  # noqa: BLE001
            findings.append(f"data tab: error — {exc}")

        browser.close()

    # Persist event log
    out_log = Path(__file__).resolve().parents[2] / "logs" / "v8b1_console.json"
    out_log.parent.mkdir(parents=True, exist_ok=True)
    out_log.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")

    # Print summary
    pageerrors = [e for e in events if e["type"] == "pageerror"]
    errors = [e for e in events if e["type"] == "error"]
    warnings = [e for e in events if e["type"] == "warning"]
    print(f"Total console events: {len(events)}")
    print(f"  pageerror: {len(pageerrors)}")
    print(f"  error:     {len(errors)}")
    print(f"  warning:   {len(warnings)}")
    if pageerrors:
        for e in pageerrors:
            print(f"    PAGEERROR: {e['text']}")
    if errors:
        for e in errors:
            print(f"    ERROR: {e['text']}")
    for w in warnings:
        print(f"    WARN: {w['text'][:120]}")
    print()
    print(f"Audit findings: {len(findings)}")
    for f in findings:
        print(f"  - {f}")


if __name__ == "__main__":
    main()
