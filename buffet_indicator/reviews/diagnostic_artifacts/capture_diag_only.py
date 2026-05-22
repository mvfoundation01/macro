"""Probe: errors on diagnostics tab — separate render vs hover."""
import asyncio
import json
import pathlib

from playwright.async_api import async_playwright

DASHBOARD_PATH = pathlib.Path("D:/macro/buffet_indicator/outputs/dashboard.html").resolve()
OUT = pathlib.Path("D:/macro/buffet_indicator/reviews/diagnostic_artifacts")


async def main():
    timeline = []
    t0 = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await context.new_page()

        def stamp():
            import time
            return time.monotonic()

        def on_console(msg):
            if "Expected length" in (msg.text or ""):
                timeline.append({"t": stamp(), "phase": "?", "text": msg.text})

        page.on("console", on_console)
        page.on("pageerror", lambda e: timeline.append({"t": stamp(), "phase": "?", "text": str(e)})
                if "Expected length" in str(e) else None)

        url = f"file:///{DASHBOARD_PATH}".replace("\\", "/")

        # phase 1: load
        load_start = stamp()
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(3000)
        load_end = stamp()
        for e in timeline:
            if e["t"] <= load_end:
                e["phase"] = "load"

        # phase 2: click diagnostics
        click_start = stamp()
        btn = await page.query_selector('[data-tab="diagnostics"]')
        if btn:
            await btn.click()
        await page.wait_for_timeout(3000)
        click_end = stamp()
        for e in timeline:
            if e["phase"] == "?" and e["t"] <= click_end:
                e["phase"] = "tab_click_render"

        # phase 3: hover only
        hover_start = stamp()
        plot_divs = await page.query_selector_all(".js-plotly-plot")
        hovered = 0
        for pd in plot_divs:
            if not await pd.is_visible():
                continue
            box = await pd.bounding_box()
            if not box or box["width"] < 50 or box["height"] < 50:
                continue
            for ox in [0.25, 0.5, 0.75]:
                x = box["x"] + box["width"] * ox
                y = box["y"] + box["height"] * 0.5
                await page.mouse.move(x, y)
                await page.wait_for_timeout(150)
                hovered += 1
        hover_end = stamp()
        for e in timeline:
            if e["phase"] == "?" and e["t"] <= hover_end:
                e["phase"] = "hover"

        await browser.close()

    from collections import Counter
    phases = Counter(e["phase"] for e in timeline)
    print(f"Total Expected-length errors: {len(timeline)}")
    print("By phase:", dict(phases))
    print(f"Hovered: {hovered}")
    if timeline:
        sample = timeline[0]
        print("\nFirst error text:")
        print(sample["text"][:300])

    (OUT / "diag_phase_breakdown.json").write_text(json.dumps({
        "total": len(timeline),
        "by_phase": dict(phases),
        "samples": [e["text"] for e in timeline[:5]],
        "hovered": hovered,
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
