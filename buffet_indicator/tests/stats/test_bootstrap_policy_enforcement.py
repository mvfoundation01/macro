"""Phase F-BLK1.E — verdict-bearing n_bootstrap immutability enforcement.

Per Codex Round 5 MAJOR CR-3: ``VERDICT_N_BOOTSTRAP = 50_000`` was declared
but unenforced; CLI accepted arbitrary ``--n-bootstrap`` overrides and
downstream sweeps propagated them into verdict cells.

This test suite verifies:
1. ``ensure_verdict_n_bootstrap`` rejects ``purpose='verdict'`` + non-50K.
2. ``ensure_verdict_n_bootstrap`` accepts ``purpose='diagnostic'``/``'test'``
   with any positive integer.
3. ``ensure_verdict_n_bootstrap`` rejects unknown purposes.
4. ``run_regression_sweep`` enforces the gate end-to-end.
5. ``run_verdict`` enforces the gate end-to-end.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.bootstrap_policy import (  # noqa: E402
    VALID_BOOTSTRAP_PURPOSES,
    VERDICT_N_BOOTSTRAP,
    ensure_verdict_n_bootstrap,
)


def test_ensure_verdict_n_bootstrap_accepts_sealed_50k_for_verdict() -> None:
    """Default verdict path with n=50_000 is permitted."""
    assert ensure_verdict_n_bootstrap(VERDICT_N_BOOTSTRAP, "verdict") is None


def test_ensure_verdict_n_bootstrap_rejects_override_in_verdict_path() -> None:
    """Phase F-BLK1.E: verdict purpose + non-50K MUST raise ValueError."""
    with pytest.raises(ValueError, match="IMMUTABLE"):
        ensure_verdict_n_bootstrap(200, "verdict")
    with pytest.raises(ValueError, match="IMMUTABLE"):
        ensure_verdict_n_bootstrap(50_001, "verdict")
    with pytest.raises(ValueError, match="IMMUTABLE"):
        ensure_verdict_n_bootstrap(49_999, "verdict")


def test_ensure_verdict_n_bootstrap_allows_any_count_for_diagnostic_and_test() -> None:
    """Diagnostic / test purposes accept any positive int."""
    for purpose in ("diagnostic", "test"):
        assert ensure_verdict_n_bootstrap(200, purpose) is None
        assert ensure_verdict_n_bootstrap(1_000, purpose) is None
        assert ensure_verdict_n_bootstrap(50_000, purpose) is None
        assert ensure_verdict_n_bootstrap(100_000, purpose) is None


def test_ensure_verdict_n_bootstrap_rejects_unknown_purpose() -> None:
    """Unknown purposes raise ValueError listing valid options."""
    with pytest.raises(ValueError, match="purpose must be one of"):
        ensure_verdict_n_bootstrap(50_000, "production")
    with pytest.raises(ValueError, match="purpose must be one of"):
        ensure_verdict_n_bootstrap(50_000, "")


def test_valid_purposes_enum_has_expected_values() -> None:
    assert VALID_BOOTSTRAP_PURPOSES == frozenset({"verdict", "diagnostic", "test"})


# End-to-end gate tests (require master data; skip if absent).


def _has_required_masters() -> bool:
    try:
        from src.ingest._base import SourceMissingError
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
    except Exception:
        return False


@pytest.mark.skipif(
    not _has_required_masters(),
    reason="Requires Phase B master parquets in data/master/.",
)
def test_run_regression_sweep_rejects_override_in_verdict_path() -> None:
    """End-to-end: run_regression_sweep raises if verdict + non-50K."""
    from src.models.v2_panel_builder import build_v2_panel
    from src.models.v2_verdict_run import run_regression_sweep

    panel = build_v2_panel()
    with pytest.raises(ValueError, match="IMMUTABLE"):
        run_regression_sweep(panel, n_bootstrap=500, purpose="verdict")


@pytest.mark.skipif(
    not _has_required_masters(),
    reason="Requires Phase B master parquets in data/master/.",
)
def test_run_verdict_rejects_override_in_verdict_path(tmp_path: Path) -> None:
    """End-to-end: run_verdict raises if verdict + non-50K."""
    from src.models.v2_run_verdict import run_verdict

    out = tmp_path / "lc_v2_verdict.json"
    with pytest.raises(ValueError, match="IMMUTABLE"):
        run_verdict(n_bootstrap=200, purpose="verdict", output_path=out)


@pytest.mark.skipif(
    not _has_required_masters(),
    reason="Requires Phase B master parquets in data/master/.",
)
def test_run_verdict_allows_test_purpose(tmp_path: Path) -> None:
    """Tests can pass small n_bootstrap via purpose='test' (used by writer tests)."""
    from src.models.v2_run_verdict import run_verdict

    out = tmp_path / "lc_v2_verdict.json"
    _, doc, _ = run_verdict(n_bootstrap=200, purpose="test", output_path=out)
    assert doc["verdict"] in {"PASS", "FAIL"}
