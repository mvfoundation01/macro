"""Repo-wide pytest hook: auto-skip tests when required raw-data / config
files are absent (typical in CI).

Many tests depend on files that are gitignored:
- ``raw data/`` directory (Shiller ``ie_data.xls``, FRED BAML CSVs,
  TradingView CSVs).
- ``config.yaml`` at the ``buffet_indicator/`` root (FRED API key, etc.).

On a local dev machine these are present; on GitHub Actions runners they
are not. The loaders / config readers raise ``SourceMissingError`` or
``FileNotFoundError``.

Rather than gating each test individually, this hook converts any of the
data/config missing-file exceptions into a ``skipped`` outcome during
setup OR call phase. Real bugs (other ``FileNotFoundError`` paths,
``AssertionError``, etc.) still fail.

Spec ref: v11.2.3 Stage 0.5 CI hotfix-3+4 (PROMPT_v11_2_3_stage_2 §3.2 #10).
"""
from __future__ import annotations

import pytest

from src.ingest._base import SourceMissingError


def _is_missing_data_or_config(excinfo) -> bool:
    """True iff the exception is due to a known data/config dependency
    that is intentionally absent in CI (gitignored locally too).
    """
    if excinfo.errisinstance(SourceMissingError):
        return True
    if excinfo.errisinstance(FileNotFoundError):
        msg = str(excinfo.value).lower()
        if "config.yaml" in msg:
            return True
        if "raw data" in msg or "raw_data" in msg:
            return True
    return False


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if call.excinfo is None:
        return
    if not _is_missing_data_or_config(call.excinfo):
        return

    report.outcome = "skipped"
    report.longrepr = (
        f"[skip-in-ci] required raw-data/config file missing: {call.excinfo.value}"
    )
