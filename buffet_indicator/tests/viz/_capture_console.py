"""Helper: load dashboard.html in chromium and capture console messages.

Not a pytest test — invoked directly to populate REVIEW_PACKAGE_v8b.md §5.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    dashboard = Path(__file__).resolve().parents[2] / "outputs" / "dashboard.html"
    url = f"file://{dashboard.as_posix()}"
    messages: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on(
            "console",
            lambda msg: messages.append(f"[{msg.type}] {msg.text}"),
        )
        page.on("pageerror", lambda err: messages.append(f"[pageerror] {err}"))
        page.goto(url)
        page.wait_for_selector("svg", timeout=10_000)
        # Click through every tab to exercise rendering
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
            page.click(f'button[data-tab="{tab}"]')
            page.wait_for_timeout(500)
        browser.close()

    out_path = Path(__file__).resolve().parents[2] / "logs" / "v8b_console.log"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if messages:
        out_path.write_text("\n".join(messages), encoding="utf-8")
    else:
        out_path.write_text(
            "(no console messages — dashboard renders cleanly)\n", encoding="utf-8"
        )
    print(f"Captured {len(messages)} console messages → {out_path}")


if __name__ == "__main__":
    main()
