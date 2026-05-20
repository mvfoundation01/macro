"""Granular per-tab screenshot capture for v9.0 dashboard.

Idempotent — skips any output file already present and ≥ 50 KB.

Usage::

    python scripts/capture_v10_0_screenshots.py               # all tabs
    python scripts/capture_v10_0_screenshots.py v10_0_mvci.png # one tab

Designed to be timeout-resilient: each invocation handles ONE Playwright
session for ONE tab. If an API/network timeout interrupts the harness,
partial progress is preserved.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

_ROOT = Path(__file__).resolve().parents[1]
_DASHBOARD = f"file://{(_ROOT / 'outputs' / 'dashboard.html').as_posix()}"
_OUTDIR = _ROOT / "outputs" / "screenshots"
_OUTDIR.mkdir(parents=True, exist_ok=True)

# (filename, tab_data_attr, (width, height), wait_selector)
# tab_data_attr=None means overview is the default landing tab.
TABS = [
    ("v10_0_overview.png", None, (1440, 900), "svg"),
    ("v10_0_mvci.png", "mvci", (1440, 900), "#hero-chart-mvci svg"),
    ("v10_0_buffett.png", "buffett", (1440, 900), "#hero-chart-buffett svg"),
    ("v10_0_cape.png", "cape", (1440, 900), "#hero-chart-cape svg"),
    ("v10_0_crestmont.png", "crestmont", (1440, 900), "#hero-chart-crestmont svg"),
    ("v10_0_qratio.png", "qratio", (1440, 900), "#hero-chart-qratio svg"),
    ("v10_0_ey_deficit.png", "ey_deficit", (1440, 900), "#hero-chart-ey_deficit svg"),
    (
        "v10_0_mean_reversion.png",
        "mean_reversion",
        (1440, 900),
        "#hero-chart-mean-reversion svg",
    ),
    ("v10_0_diagnostics.png", "diagnostics", (1440, 900), "svg"),
    ("v10_0_backtest.png", "backtest", (1440, 900), "#backtest-equity-curve svg"),
    ("v10_0_mobile.png", None, (360, 800), "svg"),
]


def _already_done(filename: str) -> bool:
    p = _OUTDIR / filename
    return p.exists() and p.stat().st_size > 50_000


def capture_one(
    filename: str,
    tab: str | None,
    viewport: tuple[int, int],
    selector: str,
) -> None:
    out_path = _OUTDIR / filename
    if _already_done(filename):
        print(f"SKIP {filename} (already exists, > 50KB)")
        return
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(
                viewport={"width": viewport[0], "height": viewport[1]}
            )
            page.goto(_DASHBOARD)
            # Wait for the active overview tab to render at least one Plotly
            # container (not just "any svg" — some sparkline SVGs in hidden
            # tabs may match first and confuse Playwright's visibility check).
            page.wait_for_selector(".tab-content.active", timeout=15_000)
            # Wait for the initial JS init + Plotly newPlot to settle.
            page.wait_for_timeout(1500)
            if tab is not None:
                page.click(f'button[data-tab="{tab}"]')
                page.wait_for_selector(
                    f'section[data-tab="{tab}"].active', timeout=10_000
                )
                page.wait_for_timeout(1000)
            try:
                page.wait_for_selector(selector, timeout=10_000)
            except Exception:  # noqa: BLE001
                pass
            page.wait_for_timeout(800)  # allow Plotly final draw
            page.screenshot(path=str(out_path), full_page=True)
        finally:
            browser.close()
    size_kb = out_path.stat().st_size / 1024
    print(f"OK   {filename} ({size_kb:.1f} KB)")


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else None
    for spec in TABS:
        if target and spec[0] != target:
            continue
        capture_one(*spec)
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
