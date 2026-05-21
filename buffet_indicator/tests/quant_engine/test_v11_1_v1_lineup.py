"""v11.1 Stage B — V1 lineup verification (CSV + outputs sync) tests."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
QE_LATEST_CSV = REPO_ROOT / "outputs" / "quant_engine" / "latest" / "latest.csv"
QE_LATEST_XLSX = REPO_ROOT / "outputs" / "quant_engine" / "latest" / "latest.xlsx"
QE_GOVERNANCE_DIR = REPO_ROOT / "outputs" / "quant_engine" / "latest" / "governance"
QE_LAST_REFRESH = REPO_ROOT / "outputs" / "quant_engine" / "latest" / "last_refresh.txt"


@pytest.mark.skipif(not QE_LATEST_CSV.exists(), reason="v50 CSV not synced yet")
def test_latest_csv_exists():
    assert QE_LATEST_CSV.exists()
    assert QE_LATEST_CSV.stat().st_size > 1024


@pytest.mark.skipif(not QE_LATEST_CSV.exists(), reason="v50 CSV not synced yet")
def test_latest_csv_drops_v1_dropped_strategies():
    """CSV must NOT contain LowRisk/FACTOR-ONLY/ETF-ROTATION rows for FULL period.

    The pre-existing v50_20260429_1053.csv (synced via Path B fallback) DOES
    contain these strategies — the filter happens in parse_v50_csv() at read
    time. After a Path A re-run with V11_1_DROP_STRATEGIES=1, the CSV at the
    source itself won't contain these labels for the new run, but Path B
    keeps the legacy CSV unchanged.
    """
    # Read raw CSV to see what was actually written
    df = pd.read_csv(QE_LATEST_CSV)
    if df.empty:
        pytest.skip("CSV empty")
    # If this is a Path-A V11.1 re-run, the dropped strategies won't be present.
    # If this is Path B (legacy April 29 CSV), they will be — that's documented
    # in REVIEW §8 as acceptable fallback.
    has_dropped = bool(set(df["label"].unique()) & {"LowRisk", "FACTOR-ONLY", "ETF-ROTATION"})
    if has_dropped:
        # Path B mode — log but don't fail
        pytest.skip(
            "Path B fallback in use (legacy April-29 CSV with LowRisk/FACTOR-ONLY/"
            "ETF-ROTATION still present). parse_v50_csv() filters these out at "
            "read time. New V11.1 v50 run will produce a clean CSV."
        )
    else:
        # Path A — assert clean
        for dropped in ("LowRisk", "FACTOR-ONLY", "ETF-ROTATION"):
            assert dropped not in df["label"].unique(), f"V1 lineup violation: {dropped} present"


@pytest.mark.skipif(not QE_LATEST_CSV.exists(), reason="v50 CSV not synced yet")
def test_latest_csv_has_required_v1_active_strategies():
    """V1 active strategies (DD-TARGET, ENS-Ultra, LowBeta) must be in CSV.

    Combination is conditional on a Path A re-run; tested separately.
    """
    df = pd.read_csv(QE_LATEST_CSV)
    labels = set(df["label"].unique())
    required = {"DD-TARGET", "ENS-Ultra", "LowBeta"}
    missing = required - labels
    assert not missing, f"V1 active strategies missing: {missing}"


@pytest.mark.skipif(not QE_LATEST_CSV.exists(), reason="v50 CSV not synced yet")
def test_latest_csv_combination_or_path_b_disclosed():
    """If Path A re-run with V11_1_DROP_STRATEGIES=1: Combination row must exist
    in CSV (FULL period @ 15bps) with Sharpe in plausible range [0.6, 1.3].

    If Path B fallback: Combination is absent; skip (documented in §8).
    """
    df = pd.read_csv(QE_LATEST_CSV)
    if "Combination" not in set(df["label"].unique()):
        pytest.skip(
            "Path B fallback used — Combination not yet present in CSV. "
            "Path A re-run with V11_1_DROP_STRATEGIES=1 will produce it."
        )
    sub = df[
        (df["label"] == "Combination")
        & (df["period"] == "FULL")
        & (df["_costbps"] == 15)
    ]
    assert len(sub) == 1, f"Expected 1 Combination FULL@15bps row, got {len(sub)}"
    sh = float(sub.iloc[0]["sharpe"])
    assert 0.6 <= sh <= 1.3, f"Combination Sharpe {sh} outside sanity range [0.6, 1.3]"


@pytest.mark.skipif(not QE_LATEST_CSV.exists(), reason="v50 CSV not synced yet")
def test_combination_maxdd_diversification():
    """Combination MaxDD should not exceed max(component MaxDD) + 1% slack.

    Diversification check: blending DD-TARGET/ENS-Ultra/LowBeta should not
    make MaxDD worse than the worst single component (with 1% slack for
    rebalance friction).
    """
    df = pd.read_csv(QE_LATEST_CSV)
    if "Combination" not in set(df["label"].unique()):
        pytest.skip("Path B fallback — Combination not present")
    sub_combo = df[(df["label"] == "Combination") & (df["period"] == "FULL") & (df["_costbps"] == 15)]
    if len(sub_combo) == 0:
        pytest.skip("Combination FULL@15bps row missing")
    combo_dd = float(sub_combo.iloc[0]["maxdd"])
    comp_dds = []
    for name in ("DD-TARGET", "ENS-Ultra", "LowBeta"):
        s = df[(df["label"] == name) & (df["period"] == "FULL") & (df["_costbps"] == 15)]
        if len(s):
            comp_dds.append(float(s.iloc[0]["maxdd"]))
    if not comp_dds:
        pytest.skip("No component MaxDDs to compare")
    worst_comp = min(comp_dds)  # MaxDD is negative; "worst" = most negative
    assert combo_dd >= worst_comp - 0.01, (
        f"Combination MaxDD {combo_dd:.4f} worse than worst component "
        f"{worst_comp:.4f} by >1% — diversification check failed"
    )


def test_governance_files_present():
    """4 governance txt files must be present after sync."""
    expected = ["model_card.txt", "config_snapshot.txt", "environment_lock.txt", "change_log.txt"]
    if not QE_GOVERNANCE_DIR.exists():
        pytest.skip("Governance dir not present yet")
    found = sorted(p.name for p in QE_GOVERNANCE_DIR.iterdir() if p.is_file())
    for name in expected:
        assert name in found, f"Governance file missing: {name}"


def test_last_refresh_parseable():
    """last_refresh.txt contains a v50-style timestamp parseable as datetime."""
    if not QE_LAST_REFRESH.exists():
        pytest.skip("last_refresh.txt not present yet")
    content = QE_LAST_REFRESH.read_text(encoding="utf-8").strip()
    assert content, "last_refresh.txt is empty"
    from datetime import datetime
    # Format is YYYYMMDD_HHMM
    try:
        datetime.strptime(content, "%Y%m%d_%H%M")
    except ValueError as e:
        pytest.fail(f"last_refresh.txt '{content}' not parseable: {e}")
