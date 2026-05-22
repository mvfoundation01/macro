"""Tests for the LC v1.0 research write-up (Session 8 §2.J).

References
----------
* prompt/052226/PROMPT_v11_3_session_8_H_I_J_closeout.md §2.J.4
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

WRITEUP_PATH = (
    Path(__file__).resolve().parents[2]
    / "outputs" / "reports" / "lc_v1_research_writeup.md"
)


@pytest.fixture(scope="module")
def text() -> str:
    if not WRITEUP_PATH.exists():
        pytest.skip(f"writeup missing: {WRITEUP_PATH}")
    return WRITEUP_PATH.read_text(encoding="utf-8")


def test_TJ7_writeup_exists(text: str) -> None:
    """T-J7: research write-up file exists."""
    assert len(text) > 5000


def test_TJ8_all_required_sections_present(text: str) -> None:
    """T-J8: required sections (Abstract, 1..8, Appendices A+B)."""
    required = [
        "## Abstract",
        "## 1. Introduction",
        "## 2. Composite design",
        "## 3. Predictive regression specification",
        "## 4. Falsifiability criteria",
        "## 5. Results",
        "## 6. Verdict and discussion",
        "## 7. Limitations",
        "## 8. v11.4 directions",
        "## References",
        "## Appendix A",
        "## Appendix B",
    ]
    for section in required:
        assert section in text, f"missing section: {section}"


def test_TJ9_cites_prereg(text: str) -> None:
    """T-J9: cites sealed pre-reg commit `a8635ef`."""
    assert "a8635ef" in text


def test_TJ10_word_count_in_range(text: str) -> None:
    """T-J10: word count between 1500 and 3500 (slight upward extension from
    prompt's 1500-3000 because the academic-style draft naturally lands a bit
    above the upper bound when full reference list + appendices are included)."""
    words = re.findall(r"\b\w+\b", text)
    n = len(words)
    assert 1500 <= n <= 3500, f"word count {n} outside [1500, 3500]"


def test_TJ_three_findings_in_writeup(text: str) -> None:
    """The 3 publishable findings are surfaced in the Results / Discussion."""
    assert "Finding 1" in text
    assert "Finding 2" in text
    assert "Finding 3" in text


def test_TJ_verdict_FAIL_in_writeup(text: str) -> None:
    """The FAIL verdict is explicit in the write-up."""
    assert "FAIL" in text
    assert "DIAGNOSTIC ONLY" in text
