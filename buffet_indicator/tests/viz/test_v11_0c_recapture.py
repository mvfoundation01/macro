"""v11.0c — verify the previously-duplicate screenshots are now distinct."""
from __future__ import annotations

import hashlib
from pathlib import Path


SHOTS = Path("outputs/screenshots/v11_0b")
TARGETS = (
    "01_overview_desktop.png",
    "02_overview_macro_snapshot_closeup.png",
    "03_tab_mrc_desktop.png",
    "18_nav_macro_risk_expanded_desktop.png",
    "19_cross_composite_quadrant_closeup.png",
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_target_files_exist() -> None:
    for name in TARGETS:
        p = SHOTS / name
        assert p.exists(), f"missing {name}"


def test_pairwise_distinct() -> None:
    hashes = {name: _hash(SHOTS / name) for name in TARGETS}
    # All 5 hashes must be unique.
    assert len(set(hashes.values())) == 5, (
        f"duplicates among targets: {hashes}"
    )


def test_each_file_above_50kb() -> None:
    for name in TARGETS:
        size = (SHOTS / name).stat().st_size
        assert size > 50_000, f"{name}: {size}B < 50KB"


def test_each_file_is_valid_png() -> None:
    from PIL import Image
    for name in TARGETS:
        with Image.open(SHOTS / name) as im:
            assert im.format == "PNG"
            assert im.size[0] > 100 and im.size[1] > 100
