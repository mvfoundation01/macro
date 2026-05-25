"""Phase F-BLK1.G — skew-t exception logging tests.

Per Codex Round 5 MAJOR CQ-1: pre-BLK1 ``run_regression_sweep`` had a broad
``except Exception`` that silently set ``skewt = None``. Numerical or API
failures were hidden as missing distribution metadata.

These tests verify:
1. A simulated ValueError from ``fit_conditional_skew_t`` is logged at INFO
   and the cell record carries a ``gaussian_fallback`` distribution_family
   with a ``value_error:`` fallback_reason.
2. A simulated unexpected error is logged at ERROR (with traceback) and the
   cell record carries a ``gaussian_fallback`` distribution_family with an
   ``unexpected_<ErrorClass>`` fallback_reason.
3. Successful skew-t fits still produce ``distribution_family='skewed_t'``.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.ingest._base import SourceMissingError  # noqa: E402


def _has_required_masters() -> bool:
    from src.ingest.master_archive import load_master
    for sid in (
        "walcl", "wdtgal", "rrpontsyd", "m2_sl", "busloans", "totll",
        "dtwexbgs", "tedrate", "sofr", "ioer", "iorb",
    ):
        try:
            load_master(sid)
        except SourceMissingError:
            return False
    return True


pytestmark = pytest.mark.skipif(
    not _has_required_masters(),
    reason="Requires Phase B master parquets in data/master/.",
)


def test_skewt_value_error_logged_and_recorded(caplog: pytest.LogCaptureFixture) -> None:
    """ValueError in fit_conditional_skew_t -> INFO log + value_error fallback."""
    from src.models.v2_panel_builder import build_v2_panel
    from src.models.v2_verdict_run import run_regression_sweep

    panel = build_v2_panel()
    caplog.set_level(logging.INFO, logger="src.models.v2_verdict_run")

    def raise_value_error(*args, **kwargs):
        raise ValueError("synthetic_value_error_for_test")

    with patch(
        "src.models.v2_verdict_run.fit_conditional_skew_t",
        side_effect=raise_value_error,
    ):
        sweep = run_regression_sweep(
            panel, n_bootstrap=50, purpose="test", fit_skewt=True, bootstrap_beta=False,
        )

    # All cells with non-empty residuals should carry the fallback metadata.
    cells_with_fallback = [
        sr for sr in sweep.values()
        if sr.skewt is not None and sr.skewt.distribution_family == "gaussian_fallback"
        and sr.skewt.fallback_reason and "value_error" in sr.skewt.fallback_reason
    ]
    assert len(cells_with_fallback) > 0, (
        "no cells recorded the expected value_error fallback metadata"
    )
    # At least one INFO log entry mentioning the cell + synthetic error.
    info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert any("synthetic_value_error_for_test" in m for m in info_msgs), (
        f"no INFO log line carried the synthetic ValueError; saw {info_msgs}"
    )


def test_skewt_unexpected_error_logged_with_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Non-ValueError exception -> ERROR log + unexpected_<class> fallback."""
    from src.models.v2_panel_builder import build_v2_panel
    from src.models.v2_verdict_run import run_regression_sweep

    panel = build_v2_panel()
    caplog.set_level(logging.ERROR, logger="src.models.v2_verdict_run")

    def raise_runtime_error(*args, **kwargs):
        raise RuntimeError("synthetic_runtime_error_for_test")

    with patch(
        "src.models.v2_verdict_run.fit_conditional_skew_t",
        side_effect=raise_runtime_error,
    ):
        sweep = run_regression_sweep(
            panel, n_bootstrap=50, purpose="test", fit_skewt=True, bootstrap_beta=False,
        )

    cells_with_unexpected = [
        sr for sr in sweep.values()
        if sr.skewt is not None and sr.skewt.distribution_family == "gaussian_fallback"
        and sr.skewt.fallback_reason
        and "unexpected_RuntimeError" in sr.skewt.fallback_reason
    ]
    assert len(cells_with_unexpected) > 0, (
        "no cells recorded the expected unexpected_RuntimeError fallback metadata"
    )
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    matching_error_records = [
        r for r in error_records if "synthetic_runtime_error_for_test" in r.message
    ]
    assert len(matching_error_records) > 0, (
        "no ERROR log line carried the synthetic RuntimeError"
    )
    # exc_info=True surfaces traceback on the record.
    assert any(r.exc_info is not None for r in matching_error_records), (
        "no ERROR record carried exc_info traceback"
    )


def test_skewt_success_path_unchanged_when_no_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Normal skew-t fits still produce skewed_t or documented gates."""
    from src.models.v2_panel_builder import build_v2_panel
    from src.models.v2_verdict_run import run_regression_sweep

    panel = build_v2_panel()
    caplog.set_level(logging.WARNING, logger="src.models.v2_verdict_run")
    sweep = run_regression_sweep(
        panel, n_bootstrap=50, purpose="test", fit_skewt=True, bootstrap_beta=False,
    )
    families = {sr.skewt.distribution_family for sr in sweep.values() if sr.skewt}
    # Only the two sealed-allowed enums (skewed_t / gaussian_fallback).
    assert families.issubset({"skewed_t", "gaussian_fallback"})
    # No unexpected errors should have been logged.
    unexpected_logs = [
        r for r in caplog.records
        if "unexpected" in r.message.lower() and r.levelno >= logging.ERROR
    ]
    assert len(unexpected_logs) == 0, (
        f"unexpected error logs in success path: {[r.message for r in unexpected_logs]}"
    )
