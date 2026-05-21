"""Capture SVG NaN errors per tab - identifies which chart contributes which slice.

Reloads dashboard fresh per-tab to attribute SVG NaN render errors unambiguously.
"""
import asyncio
import json
import pathlib

from playwright.async_api import async_playwright

DASHBOARD_PATH = pathlib.Path("D:/macro/buffet_indicator/outputs/dashboard.html").resolve()
OUT = pathlib.Path("D:/macro/buffet_indicator/reviews/diagnostic_artifacts")
OUT.mkdir(parents=True, exist_ok=True)

TABS = [
    "overview", "cape", "buffett", "mvci", "strategy_engine",
    "diagnostics", "data", "methodology", "backtest",
]


async def hover_visible_plots(page):
    plot_divs = await page.query_selector_all(".js-plotly-plot")
    hovered = 0
    for plot_div in plot_divs:
        try:
            if not await plot_div.is_visible():
                continue
            box = await plot_div.bounding_box()
            if not box or box["width"] < 50 or box["height"] < 50:
                continue
            for ox in [0.25, 0.5, 0.75]:
                x = box["x"] + box["width"] * ox
                y = box["y"] + box["height"] * 0.5
                await page.mouse.move(x, y)
                await page.wait_for_timeout(80)
                hovered += 1
        except Exception:
            pass
    return hovered


async def capture_for_tab(p, tab):
    """Fresh page per tab to isolate error attribution."""
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 1600, "height": 1000})
    page = await context.new_page()

    errors = []

    def on_console(msg):
        text = msg.text or ""
        if "Expected length" in text:
            errors.append({"type": msg.type, "text": text})

    def on_page_error(err):
        text = str(err)
        if "Expected length" in text:
            errors.append({"type": "pageerror", "text": text})

    page.on("console", on_console)
    page.on("pageerror", on_page_error)

    url = f"file:///{DASHBOARD_PATH}".replace("\\", "/")
    try:
        await page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception as e:
        print(f"[{tab}] goto exception: {e}")

    await page.wait_for_timeout(2000)

    # Always hover the default (overview) plots first; then optionally click target tab
    hovered_default = await hover_visible_plots(page)

    hovered_tab = 0
    if tab != "overview":
        btn = await page.query_selector(f'[data-tab="{tab}"]')
        if btn:
            await btn.click()
            await page.wait_for_timeout(1500)
            hovered_tab = await hover_visible_plots(page)

    text_err = sum(1 for e in errors if "<text>" in e["text"])
    image_err = sum(1 for e in errors if "<image>" in e["text"])
    other_err = len(errors) - text_err - image_err

    await browser.close()
    return {
        "tab": tab,
        "total": len(errors),
        "text_y": text_err,
        "image_height": image_err,
        "other": other_err,
        "hovered_default": hovered_default,
        "hovered_tab": hovered_tab,
    }


async def main():
    results = []
    async with async_playwright() as p:
        for tab in TABS:
            print(f"Capturing tab: {tab}...")
            r = await capture_for_tab(p, tab)
            results.append(r)
            print(f"  total={r['total']}  text_y={r['text_y']}  image_height={r['image_height']}  "
                  f"hov_default={r['hovered_default']}  hov_tab={r['hovered_tab']}")

    # Also capture "no clicks" baseline (just default load)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await context.new_page()
        no_click_errors = []

        def on_console(msg):
            if "Expected length" in (msg.text or ""):
                no_click_errors.append({"type": msg.type, "text": msg.text})

        page.on("console", on_console)
        page.on("pageerror", lambda e: no_click_errors.append({"type": "pe", "text": str(e)})
                if "Expected length" in str(e) else None)

        url = f"file:///{DASHBOARD_PATH}".replace("\\", "/")
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(3000)
        await browser.close()
        no_click_baseline = {
            "tab": "<no-clicks-no-hover>",
            "total": len(no_click_errors),
            "text_y": sum(1 for e in no_click_errors if "<text>" in e["text"]),
            "image_height": sum(1 for e in no_click_errors if "<image>" in e["text"]),
        }

    out = OUT / "svg_nan_per_tab.json"
    payload = {
        "no_click_baseline": no_click_baseline,
        "per_tab": results,
    }
    out.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")
    print(f"\nSummary:")
    print(f"  no-click baseline: {no_click_baseline['total']}")
    for r in results:
        print(f"  {r['tab']:18s}: total={r['total']:4d}  text_y={r['text_y']:4d}  image_height={r['image_height']:3d}")


if __name__ == "__main__":
    asyncio.run(main())
