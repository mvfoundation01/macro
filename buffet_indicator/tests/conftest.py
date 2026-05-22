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

Also exposes ``http_server_fixture`` (session-scoped) — a SimpleHTTPServer
on a random port serving the rendered ``outputs/`` directory. Used by
``tests/viz/test_v11_2_3_svgnan_real_browser.py`` to drive Playwright
against the real-browser HTTP URL.

Spec ref: v11.2.3 Stage 0.5 CI hotfix-3+4 (PROMPT_v11_2_3_stage_2 §3.2 #10).
        + v11.2.3 Session 4 SVG NaN hotfix (PROMPT_v11_2_3_svgnan_hotfix §4).
"""
from __future__ import annotations

import http.server
import os
import socketserver
import threading
import time
from pathlib import Path

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


# ---------------------------------------------------------------------------
# v11.2.3 Session 4 — HTTP-served dashboard fixture for Playwright tests.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def http_server_fixture():
    """Serve ``outputs/`` over HTTP on a random local port for the session.

    Yields the base URL (e.g. ``http://127.0.0.1:54321``). Playwright tests
    use this so the dashboard is loaded the same way a real browser would
    (HTTP, no ``--allow-file-access-from-files``), catching the class of
    bugs that ``file://`` loads silently mask.
    """
    outputs = Path(__file__).resolve().parents[1] / "outputs"
    if not outputs.exists():
        pytest.skip(f"outputs/ directory missing at {outputs}")

    prev_cwd = os.getcwd()
    os.chdir(outputs)

    # Bind to port 0 so the OS picks a free one — supports parallel test runs.
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    # Allow the server thread to fully come up before any test hits it.
    time.sleep(0.3)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        os.chdir(prev_cwd)
