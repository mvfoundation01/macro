"""Isolate which of the 4 diagnostics charts produces the SVG NaN errors.

Strategy: temporarily set display:none on each diagnostics chart one at a time,
then click the diagnostics tab and count errors. The chart whose suppression
drops errors to 0 is the culprit.
"""
import asyncio
import pathlib

from playwright.async_api import async_playwright

DASHBOARD_PATH = pathlib.Path("D:/macro/buffet_indicator/outputs/dashboard.html").resolve()

CHART_IDS = [
    "diagnostics-correlation-heatmap",
    "diagnostics-oos-r2-chart",
    "diagnostics-acf-pacf-chart",
    "diagnostics-calibration-chart",
]


async def capture_with_hidden(p, hide_id):
    errs = []
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(viewport={"width": 1600, "height": 1000})
    page = await ctx.new_page()
    page.on("console", lambda m: errs.append(m.text) if "Expected length" in (m.text or "") else None)
    page.on("pageerror", lambda e: errs.append(str(e)) if "Expected length" in str(e) else None)

    url = f"file:///{DASHBOARD_PATH}".replace("\\", "/")
    await page.goto(url, wait_until="networkidle", timeout=45000)
    await page.wait_for_timeout(1500)

    if hide_id:
        # Hide the chart div BEFORE diagnostics tab is shown
        await page.evaluate(f'''() => {{
            const d = document.getElementById("{hide_id}");
            if (d) d.style.display = "none";
        }}''')

    btn = await page.query_selector('[data-tab="diagnostics"]')
    if btn:
        await btn.click()
    await page.wait_for_timeout(2500)

    text_err = sum(1 for e in errs if "<text>" in e)
    image_err = sum(1 for e in errs if "<image>" in e)
    await browser.close()
    return {"hide": hide_id, "total": len(errs), "text_y": text_err, "image_h": image_err}


async def main():
    results = []
    async with async_playwright() as p:
        results.append(await capture_with_hidden(p, None))
        for cid in CHART_IDS:
            results.append(await capture_with_hidden(p, cid))

    print(f"{'hide':40s} {'total':>6} {'text_y':>7} {'image_h':>8}")
    for r in results:
        print(f"{(r['hide'] or '<none>'):40s} {r['total']:6d} {r['text_y']:7d} {r['image_h']:8d}")


if __name__ == "__main__":
    asyncio.run(main())
