"""Capture SVG NaN errors via HTTP (mimics the owner's real Chrome session).

Differences from `capture_svg_nan_per_tab.py`:
- Loads `http://127.0.0.1:<port>/dashboard.html` (NOT `file://`).
- Does NOT launch Chromium with `--allow-file-access-from-files`.
- For Strategy Engine: expands every `<details>` element, clicks every
  visible sub-rail link, and changes every `<select>` through all options.
  Captures per-action error deltas so we can attribute errors to a
  specific user action.

Spec ref: PROMPT_v11_2_3_svgnan_hotfix §1.2.

Usage (assumes `python -m http.server 8000 --directory outputs` is running):
    python reviews/diagnostic_artifacts/capture_svg_nan_real_browser.py
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys

from playwright.async_api import async_playwright

OUT = pathlib.Path("D:/macro/buffet_indicator/reviews/diagnostic_artifacts")
OUT.mkdir(parents=True, exist_ok=True)

DEFAULT_URL = "http://127.0.0.1:8000/dashboard.html"

TABS = [
    "overview", "cape", "buffett", "mvci", "strategy_engine",
    "diagnostics", "data", "methodology", "backtest",
]


def is_nan_error(text: str) -> bool:
    return "Expected length" in text and "NaN" in text


async def capture(url: str = DEFAULT_URL, headless: bool = True):
    actions_log: list[dict] = []
    all_errors: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await context.new_page()

        def on_console(msg):
            t = msg.text or ""
            if is_nan_error(t):
                all_errors.append(t)

        def on_page_error(err):
            t = str(err)
            if is_nan_error(t):
                all_errors.append(t)

        page.on("console", on_console)
        page.on("pageerror", on_page_error)

        # Phase 0 — initial load.
        print(f"Loading {url} ...")
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(2000)
        actions_log.append({"action": "initial-load", "errors_after": len(all_errors)})
        print(f"  initial-load: {len(all_errors)} errors")

        # Phase 1 — click each top-level tab.
        for tab in TABS:
            before = len(all_errors)
            btn = await page.query_selector(f'[data-tab="{tab}"]')
            if not btn:
                actions_log.append({"action": f"tab:{tab}", "delta": 0, "skipped": "no-button"})
                continue
            await btn.click()
            await page.wait_for_timeout(1500)
            delta = len(all_errors) - before
            actions_log.append({"action": f"tab:{tab}", "delta": delta, "total": len(all_errors)})
            print(f"  tab:{tab}: +{delta} (total {len(all_errors)})")

        # Phase 2 — Strategy Engine sub-actions.
        # Re-click strategy_engine tab to make sure we're on it.
        se_btn = await page.query_selector('[data-tab="strategy_engine"]')
        if se_btn:
            await se_btn.click()
            await page.wait_for_timeout(1000)

        # 2a — expand every <details> on the page (Surface 1–9).
        details_elems = await page.query_selector_all("details")
        for i, det in enumerate(details_elems):
            try:
                if not await det.is_visible():
                    continue
                # If already open, close + reopen to force a render cycle.
                is_open = await det.get_attribute("open")
                summary = await det.query_selector("summary")
                if not summary:
                    continue
                before = len(all_errors)
                det_id = await det.get_attribute("id") or f"details[{i}]"
                if is_open is None:
                    await summary.click()
                    await page.wait_for_timeout(800)
                    delta = len(all_errors) - before
                    actions_log.append({"action": f"open-details:{det_id}", "delta": delta, "total": len(all_errors)})
                    print(f"  open-details:{det_id}: +{delta} (total {len(all_errors)})")
            except Exception as e:
                actions_log.append({"action": f"open-details[{i}]", "error": str(e)})

        # 2b — change every <select> through all options.
        selects = await page.query_selector_all("select")
        for i, sel in enumerate(selects):
            try:
                if not await sel.is_visible():
                    continue
                opts = await sel.query_selector_all("option")
                values = []
                for o in opts:
                    v = await o.get_attribute("value")
                    if v is not None:
                        values.append(v)
                sel_id = await sel.get_attribute("id") or f"select[{i}]"
                for v in values:
                    before = len(all_errors)
                    try:
                        await sel.select_option(value=v)
                    except Exception:
                        continue
                    await page.wait_for_timeout(800)
                    delta = len(all_errors) - before
                    actions_log.append({
                        "action": f"select:{sel_id}=>{v}",
                        "delta": delta, "total": len(all_errors),
                    })
                    print(f"  select:{sel_id}={v}: +{delta} (total {len(all_errors)})")
            except Exception as e:
                actions_log.append({"action": f"select[{i}]", "error": str(e)})

        # 2c — hover all visible plotly plots once.
        plot_divs = await page.query_selector_all(".js-plotly-plot")
        for j, pd in enumerate(plot_divs):
            try:
                if not await pd.is_visible():
                    continue
                before = len(all_errors)
                box = await pd.bounding_box()
                if not box or box["width"] < 50 or box["height"] < 50:
                    continue
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                await page.mouse.move(cx, cy)
                await page.wait_for_timeout(200)
                delta = len(all_errors) - before
                pd_id = await pd.get_attribute("id") or f"plot[{j}]"
                if delta != 0:
                    actions_log.append({"action": f"hover:{pd_id}", "delta": delta, "total": len(all_errors)})
                    print(f"  hover:{pd_id}: +{delta} (total {len(all_errors)})")
            except Exception:
                pass

        await browser.close()

    payload = {
        "url": url,
        "total_errors": len(all_errors),
        "actions": actions_log,
        "errors_sample": [e[:200] for e in all_errors[:200]],
    }
    out = OUT / "svg_nan_real_browser.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")
    print(f"\nFinal total errors: {len(all_errors)}")

    # Print a per-action breakdown showing only actions that added errors.
    spikes = [a for a in actions_log if a.get("delta", 0) > 0]
    if spikes:
        print("\nActions that introduced errors:")
        for a in spikes:
            print(f"  {a['action']}: +{a['delta']}")
    else:
        print(f"\nNo per-action spikes recorded; baseline was {actions_log[0].get('errors_after', '?')}.")

    return len(all_errors)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    rc = asyncio.run(capture(url=url, headless=True))
    sys.exit(0 if rc == 0 else 1)
