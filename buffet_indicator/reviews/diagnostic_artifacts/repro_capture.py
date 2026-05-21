"""Capture errors when minimal heatmap is rendered."""
import asyncio
import pathlib

from playwright.async_api import async_playwright

import sys
fname = sys.argv[1] if len(sys.argv) > 1 else "repro_heatmap.html"
PATH = pathlib.Path(f"D:/macro/buffet_indicator/reviews/diagnostic_artifacts/{fname}").resolve()


async def main():
    errs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await ctx.new_page()
        page.on("console", lambda m: errs.append(m.text) if "Expected length" in (m.text or "") else None)
        page.on("pageerror", lambda e: errs.append(str(e)) if "Expected length" in str(e) else None)
        url = f"file:///{PATH}".replace("\\", "/")
        await page.goto(url, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(3000)
        await browser.close()
    print(f"Errors: {len(errs)}")
    for e in errs[:3]:
        print(" -", e[:200])


if __name__ == "__main__":
    asyncio.run(main())
