"""v11.2.3 Session 4 — SVG NaN regression tests over HTTP (real-browser sim).

These tests replicate the owner's actual Chrome workflow:
- Dashboard served via HTTP (NOT `file://`).
- Each top-level tab clicked.
- Inside Strategy Engine: every `<details>` opened, every `<select>`
  cycled through all options.

Any SVG NaN error (Plotly emitting `<text y="NaN">` / `<image height="NaN">`)
will fail the test. The Stage 2 regression caught by the owner was missed
by `capture_svg_nan_per_tab.py` because it only loaded via `file://` and
never opened the Surface 9 details on the Strategy Engine tab. These
tests close that gap permanently.

Spec ref: PROMPT_v11_2_3_svgnan_hotfix §4.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


DASHBOARD_HTML = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"
TOP_TABS = [
    "overview", "cape", "buffett", "mvci", "strategy_engine",
    "diagnostics", "data", "methodology", "backtest",
]


def _is_nan_error(text: str) -> bool:
    return "Expected length" in text and "NaN" in text


def _playwright_available() -> bool:
    try:
        from playwright.async_api import async_playwright  # noqa: F401
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not DASHBOARD_HTML.exists(),
    reason="outputs/dashboard.html required",
)


@pytest.fixture(scope="module")
def http_url(http_server_fixture: str) -> str:
    """Module-scoped URL to the served dashboard.html."""
    return f"{http_server_fixture}/dashboard.html"


async def _open_page(url: str):
    """Returns (browser, page, errors_list). Caller must close browser."""
    from playwright.async_api import async_playwright

    pw_cm = async_playwright()
    p = await pw_cm.__aenter__()
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 1600, "height": 1000})
    page = await context.new_page()

    errors: list[str] = []

    def on_console(msg):
        t = msg.text or ""
        if _is_nan_error(t):
            errors.append(t)

    def on_page_error(err):
        t = str(err)
        if _is_nan_error(t):
            errors.append(t)

    page.on("console", on_console)
    page.on("pageerror", on_page_error)

    await page.goto(url, wait_until="networkidle", timeout=45000)
    await page.wait_for_timeout(2000)
    return pw_cm, p, browser, page, errors


async def _close_page(pw_cm, browser) -> None:
    await browser.close()
    await pw_cm.__aexit__(None, None, None)


@pytest.mark.skipif(not _playwright_available(), reason="playwright not installed")
def test_no_nan_errors_on_initial_load(http_url: str) -> None:
    async def run() -> int:
        pw_cm, _p, browser, _page, errors = await _open_page(http_url)
        await _close_page(pw_cm, browser)
        return len(errors)

    n = asyncio.run(run())
    assert n == 0, f"{n} SVG NaN error(s) on initial load over HTTP"


@pytest.mark.skipif(not _playwright_available(), reason="playwright not installed")
def test_no_nan_errors_on_each_top_tab(http_url: str) -> None:
    async def run() -> tuple[int, dict[str, int]]:
        pw_cm, _p, browser, page, errors = await _open_page(http_url)
        per_tab: dict[str, int] = {}
        for tab in TOP_TABS:
            before = len(errors)
            btn = await page.query_selector(f'[data-tab="{tab}"]')
            if not btn:
                per_tab[tab] = -1
                continue
            await btn.click()
            await page.wait_for_timeout(1500)
            per_tab[tab] = len(errors) - before
        await _close_page(pw_cm, browser)
        return len(errors), per_tab

    total, per_tab = asyncio.run(run())
    assert total == 0, f"{total} total SVG NaN error(s) cycling top tabs: per-tab={per_tab}"


@pytest.mark.skipif(not _playwright_available(), reason="playwright not installed")
def test_no_nan_errors_on_strategy_engine_subactions(http_url: str) -> None:
    """Open every Strategy Engine `<details>` (Surfaces 1–9). This is the
    interaction class that triggered the Session 4 regression on Surface 9.
    """
    async def run() -> tuple[int, list[str]]:
        pw_cm, _p, browser, page, errors = await _open_page(http_url)
        # Navigate to Strategy Engine.
        se_btn = await page.query_selector('[data-tab="strategy_engine"]')
        if se_btn:
            await se_btn.click()
            await page.wait_for_timeout(1000)
        opened: list[str] = []
        details_elems = await page.query_selector_all("details")
        for det in details_elems:
            if not await det.is_visible():
                continue
            det_id = await det.get_attribute("id") or "<no-id>"
            if not det_id.startswith("ea-surface-"):
                # Restrict to Strategy Engine surfaces for this test.
                continue
            summary = await det.query_selector("summary")
            if not summary:
                continue
            is_open = await det.get_attribute("open")
            if is_open is None:
                await summary.click()
                await page.wait_for_timeout(800)
                opened.append(det_id)
        await _close_page(pw_cm, browser)
        return len(errors), opened

    total, opened = asyncio.run(run())
    assert total == 0, (
        f"{total} SVG NaN error(s) after opening Strategy Engine details: opened={opened}"
    )


@pytest.mark.skipif(not _playwright_available(), reason="playwright not installed")
def test_no_nan_errors_on_strategy_dropdown_changes(http_url: str) -> None:
    """Cycle every visible `<select>` (e.g. Surface 8 SWR strategy dropdown)
    through all its options.
    """
    async def run() -> tuple[int, list[str]]:
        pw_cm, _p, browser, page, errors = await _open_page(http_url)
        se_btn = await page.query_selector('[data-tab="strategy_engine"]')
        if se_btn:
            await se_btn.click()
            await page.wait_for_timeout(1000)
        # Open all surface details so selects become visible.
        for det in await page.query_selector_all("details"):
            if not await det.is_visible():
                continue
            det_id = await det.get_attribute("id") or ""
            if not det_id.startswith("ea-surface-"):
                continue
            is_open = await det.get_attribute("open")
            if is_open is None:
                s = await det.query_selector("summary")
                if s:
                    await s.click()
                    await page.wait_for_timeout(400)
        cycled: list[str] = []
        selects = await page.query_selector_all("select")
        for sel in selects:
            if not await sel.is_visible():
                continue
            sel_id = await sel.get_attribute("id") or "<no-id>"
            opts = await sel.query_selector_all("option")
            for o in opts:
                v = await o.get_attribute("value")
                if v is None:
                    continue
                try:
                    await sel.select_option(value=v)
                except Exception:
                    continue
                await page.wait_for_timeout(600)
                cycled.append(f"{sel_id}={v}")
        await _close_page(pw_cm, browser)
        return len(errors), cycled

    total, cycled = asyncio.run(run())
    assert total == 0, (
        f"{total} SVG NaN error(s) after dropdown changes: cycled={cycled}"
    )
