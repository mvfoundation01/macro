"""Repo-wide pytest hook: auto-skip tests when required raw-data files
are absent (typical in CI).

Many tests depend on files in the gitignored ``raw data/`` directory
(``ie_data.xls`` from Shiller, FRED BAML CSVs, TradingView CSVs, etc.).
On a local dev machine these are present; on GitHub Actions runners they
are not, and the loaders raise ``SourceMissingError``.

Rather than gating each test individually, this hook converts any
``SourceMissingError`` raised during setup OR call phase into a
``skipped`` outcome. This keeps the CI signal meaningful (real failures
still fail) without requiring raw-data secrets in the runner.

Spec ref: v11.2.3 Stage 0.5 CI hotfix-3 (PROMPT_v11_2_3_stage_2 §3.2 #10).
"""
from __future__ import annotations

import pytest

from src.ingest._base import SourceMissingError


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if call.excinfo is None:
        return
    if not call.excinfo.errisinstance(SourceMissingError):
        return

    report.outcome = "skipped"
    report.longrepr = (
        f"[skip-in-ci] required raw-data file missing: {call.excinfo.value}"
    )
