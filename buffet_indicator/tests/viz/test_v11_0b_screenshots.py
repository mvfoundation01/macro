"""v11.0b screenshot-gate tests.

Validates that scripts/capture_v11_0b_screenshots.py produced 19 PNG files,
each > 100 KB, with 0 console errors logged during capture.

Does NOT re-run the capture (Playwright launch is slow + flaky in CI);
instead it inspects the artefacts and the log JSON produced by the capture.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


SCREENSHOTS_DIR = Path("outputs/screenshots/v11_0b")
LOG_PATH = SCREENSHOTS_DIR / "_capture_log.json"

EXPECTED = (
    "01_overview_desktop",
    "02_overview_macro_snapshot_closeup",
    "03_tab_mrc_desktop",
    "04_tab_mrc_mobile",
    "05_tab_yc_10y3m_desktop",
    "06_tab_yc_10y2y_desktop",
    "07_tab_cs_hy_master_desktop",
    "08_tab_cs_ig_master_desktop",
    "09_tab_cs_hy_bb_desktop",
    "10_tab_cs_hy_ccc_desktop",
    "11_tab_margin_debt_desktop",
    "12_tab_buffett_recession_overlay_check",
    "13_tab_cape_recession_overlay_check",
    "14_tab_mean_reversion_recession_overlay_check",
    "15_tab_diagnostics_desktop",
    "16_tab_backtest_desktop",
    "17_tab_methodology_desktop",
    "18_nav_macro_risk_expanded_desktop",
    "19_cross_composite_quadrant_closeup",
)


def _require_artefacts() -> None:
    if not SCREENSHOTS_DIR.exists() or not LOG_PATH.exists():
        pytest.skip(
            "Screenshot artefacts not present; run "
            "`python -m scripts.capture_v11_0b_screenshots` first."
        )


def test_all_19_screenshots_exist() -> None:
    _require_artefacts()
    for name in EXPECTED:
        f = SCREENSHOTS_DIR / f"{name}.png"
        assert f.exists(), f"missing screenshot {name}.png"


def test_each_screenshot_above_threshold() -> None:
    """Most shots are full-page captures > 100 KB; v11.0c §F intentionally
    produces 3 cropped/element screenshots (02 closeup, 18 nav crop, 19
    cross-composite element) which can legitimately be smaller. Per
    v11.0c spec the threshold for those is > 50 KB."""
    _require_artefacts()
    cropped = {
        "02_overview_macro_snapshot_closeup",
        "18_nav_macro_risk_expanded_desktop",
        "19_cross_composite_quadrant_closeup",
    }
    for name in EXPECTED:
        f = SCREENSHOTS_DIR / f"{name}.png"
        size = f.stat().st_size
        threshold = 50_000 if name in cropped else 100_000
        assert size > threshold, (
            f"{name}.png is only {size} bytes (<{threshold//1000}KB)"
        )


def test_each_screenshot_is_valid_png() -> None:
    _require_artefacts()
    from PIL import Image

    for name in EXPECTED:
        f = SCREENSHOTS_DIR / f"{name}.png"
        with Image.open(f) as im:
            assert im.format == "PNG", f"{name} is not a PNG (format={im.format})"
            assert im.size[0] > 100 and im.size[1] > 100, (
                f"{name} dimensions look broken: {im.size}"
            )


def test_no_console_errors_during_capture() -> None:
    _require_artefacts()
    log = json.loads(LOG_PATH.read_text())
    bad: list[str] = []
    for cap in log.get("captures", []):
        if cap.get("errors"):
            bad.append(f"{cap['name']}: {cap['errors']}")
    assert not bad, "console errors logged: " + "; ".join(bad)
