"""Lock in the sys.path bootstrap pattern for every script under ``scripts/``
that imports from ``src.*``.

Background
----------
Python's import system finds modules by walking ``sys.path``. When a script
under ``scripts/`` is invoked via ``python scripts/foo.py``, ``sys.path[0]``
becomes ``scripts/`` — and ``src/`` is no longer reachable as a top-level
package. The standard fix is to insert the project root into ``sys.path``
before any ``from src.* import`` statement.

This test parametrizes over every ``scripts/*.py`` and asserts the
bootstrap pattern is present whenever the script imports from ``src.*``.
Future scripts inherit the rule for free.

References
----------
* prompt/052226/PROMPT_v11_3_session_6_5_oneshot_bootstrap_and_regression.md §2.0
* Session 6 bug: ``ModuleNotFoundError: No module named 'src'`` when
  ``scripts/bootstrap_icedxy_from_norgate.py`` was invoked directly.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
PATTERN = re.compile(r"sys\.path\.insert\(0,\s*str\(_PROJECT_ROOT\)\)", re.MULTILINE)


@pytest.mark.parametrize("script", sorted(SCRIPTS_DIR.glob("*.py")))
def test_script_has_sys_path_bootstrap(script: Path) -> None:
    """Any script that imports from ``src.*`` must have the bootstrap pattern."""
    text = script.read_text(encoding="utf-8")
    if "from src." not in text and "import src" not in text:
        pytest.skip(f"{script.name} does not import from src.* — bootstrap not required")
    assert PATTERN.search(text), (
        f"{script.name} imports from src.* but lacks the sys.path bootstrap. "
        f"Add the standard pattern (see scripts/bootstrap_icedxy_from_norgate.py)."
    )
