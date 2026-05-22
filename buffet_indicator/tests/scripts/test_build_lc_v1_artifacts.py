"""Smoke test for the LC v1.0 build driver.

Verifies the script imports cleanly, exposes the expected entry points,
and survives ``py_compile`` (catches import-time and parse errors before
the full driver run is attempted).

References
----------
* prompt/052226/PROMPT_v11_3_session_6_5_oneshot_bootstrap_and_regression.md §2.2
"""
from __future__ import annotations

import importlib.util
import py_compile
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "build_lc_v1_artifacts.py"
)


def test_driver_script_exists() -> None:
    """Script file must exist on disk."""
    assert SCRIPT.exists(), f"Missing: {SCRIPT}"


def test_driver_compiles() -> None:
    """The driver must pass ``py_compile`` (catches parse/import-time errors)."""
    py_compile.compile(str(SCRIPT), doraise=True)


def test_driver_exposes_entry_points() -> None:
    """The driver must expose ``main`` and ``verify_prereg_ancestor`` symbols."""
    spec = importlib.util.spec_from_file_location("build_lc_v1_artifacts", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "main"), "missing main()"
    assert hasattr(module, "verify_prereg_ancestor"), "missing verify_prereg_ancestor()"
    assert callable(module.main)
    assert callable(module.verify_prereg_ancestor)
