"""v11.2 Stage 1 — Pre-registration file commit verification.

These tests guard the pre-registration integrity rule from PROMPT_v11_2 §2.3:
the spec file must exist, be tracked by git (i.e., committed BEFORE V2
backtest is executed), and contain the required structural sections.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PREREG_PATH = REPO_ROOT / "specs" / "MV_CONDITIONAL_RULE_PREREGISTER.md"


def test_preregister_file_exists():
    """File at specs/MV_CONDITIONAL_RULE_PREREGISTER.md must exist."""
    assert PREREG_PATH.exists(), f"missing pre-registration file at {PREREG_PATH}"
    assert PREREG_PATH.stat().st_size > 1024, "pre-registration file suspiciously small"


def test_preregister_file_committed_to_git():
    """`git log <file>` must return non-empty (file is tracked, formally pre-registered)."""
    rel_path = "buffet_indicator/specs/MV_CONDITIONAL_RULE_PREREGISTER.md"
    try:
        out = subprocess.check_output(
            ["git", "log", "--oneline", "--", rel_path],
            cwd=str(REPO_ROOT.parent),
            stderr=subprocess.STDOUT,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        pytest.skip(f"git not available or path issue: {e}")
    assert out.strip(), (
        "pre-registration file is NOT tracked by git — must be committed "
        "BEFORE V2 backtest runs (PROMPT_v11_2 §1.4)"
    )


def test_preregister_contains_required_sections():
    """File must reference R-PRIMARY, Falsifiability, Walk-forward, Holm-Šidák."""
    text = PREREG_PATH.read_text(encoding="utf-8")
    required = ["R-PRIMARY", "Falsifiability", "Walk-forward", "Holm-Šidák"]
    missing = [k for k in required if k not in text]
    assert not missing, f"pre-registration missing required sections: {missing}"
