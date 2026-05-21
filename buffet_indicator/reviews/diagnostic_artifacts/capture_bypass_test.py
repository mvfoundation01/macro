"""Test whether bypassing mvRenderWhenReady for the diag corr heatmap fixes it.

Strategy: patch the page to replace mvRenderWhenReady with an immediate-render
shim for only the diagnostics-correlation-heatmap div, then click diagnostics.
"""
import asyncio
import pathlib

from playwright.async_api import async_playwright

DASHBOARD_PATH = pathlib.Path("D:/macro/buffet_indicator/outputs/dashboard.html").resolve()


async def main():
    errs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await ctx.new_page()
        page.on("console", lambda m: errs.append(m.text) if "Expected length" in (m.text or "") else None)
        page.on("pageerror", lambda e: errs.append(str(e)) if "Expected length" in str(e) else None)

        url = f"file:///{DASHBOARD_PATH}".replace("\\", "/")
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(1500)

        # Override mvRenderWhenReady to skip all RAF and Observer logic - immediate render
        await page.evaluate('''() => {
            window.mvRenderWhenReady = function (divId, renderFn) {
                const el = document.getElementById(divId);
                if (!el) return;
                if (typeof Plotly === "undefined") { setTimeout(() => renderFn(), 100); return; }
                try { renderFn(); } catch (err) { console.warn("override failed", divId, err); }
            };
        }''')

        btn = await page.query_selector('[data-tab="diagnostics"]')
        if btn:
            await btn.click()
        await page.wait_for_timeout(2500)

        text_err = sum(1 for e in errs if "<text>" in e)
        image_err = sum(1 for e in errs if "<image>" in e)
        await browser.close()

    print(f"With override (immediate render, no RAF):")
    print(f"  total={len(errs)} text_y={text_err} image_h={image_err}")


if __name__ == "__main__":
    asyncio.run(main())
