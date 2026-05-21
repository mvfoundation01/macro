"""v11.1 Stage A — File copy + setup acceptance tests."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


QUANT_PIPELINE_ROOT = Path(r"D:\macro\quant_pipeline")
V50_COPY = QUANT_PIPELINE_ROOT / "quant_engine_v50_FINAL.py"
CACHE_DIR = QUANT_PIPELINE_ROOT / "data_cache"
RESULTS_DIR = QUANT_PIPELINE_ROOT / "results"
ORIGINAL_V50 = Path(r"D:\Quant Pipeline\Momentum pipeline\quant_engine_v50_FINAL.py")
ORIGINAL_SHA_FILE = Path(__file__).resolve().parents[2] / "logs" / "v11_1_original_sha256_start.txt"


def _sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.mark.skipif(not V50_COPY.exists(), reason="v50 copy not present (run Stage A first)")
def test_v50_copy_exists():
    """Stage A.3: v50 COPY exists at expected location."""
    assert V50_COPY.exists(), f"v50 copy missing at {V50_COPY}"
    assert V50_COPY.stat().st_size > 100_000, "v50 copy suspiciously small"


@pytest.mark.skipif(not V50_COPY.exists(), reason="v50 copy not present")
def test_v50_copy_uses_env_var_paths():
    """Stage A.7: COPY's SAVE/CACHE paths are env-var-aware, not hardcoded."""
    src = V50_COPY.read_text(encoding="utf-8")
    assert "QUANT_PIPELINE_RESULTS" in src, "Missing env-var override for SAVE"
    assert "QUANT_PIPELINE_CACHE" in src, "Missing env-var override for CACHE"
    # Hardcoded source path must NOT appear in the COPY
    assert r"D:\Quant Pipeline\Momentum pipeline\results" not in src, \
        "Hardcoded original path leaked into COPY"
    assert r"D:\Quant Pipeline\Momentum pipeline\data_cache" not in src, \
        "Hardcoded original cache path leaked into COPY"


@pytest.mark.skipif(not V50_COPY.exists(), reason="v50 copy not present")
def test_v50_copy_has_v11_1_drop_strategies_flag():
    """Stage B.1: V11_1_DROP_STRATEGIES feature flag added to v50 COPY."""
    src = V50_COPY.read_text(encoding="utf-8")
    assert "V11_1_DROP_STRATEGIES" in src
    # At least: definition + 2 wrap sites + 1 ETF guard = 4 occurrences minimum
    assert src.count("V11_1_DROP_STRATEGIES") >= 4


@pytest.mark.skipif(not V50_COPY.exists(), reason="v50 copy not present")
def test_v50_copy_has_combination_block():
    """Stage B.3: Combination strategy block inserted in v50 COPY."""
    src = V50_COPY.read_text(encoding="utf-8")
    assert "_combine_strategies_at_returns" in src, "Combination helper missing"
    assert "Combination" in src
    assert "DD-TARGET" in src and "ENS-Ultra" in src and "LowBeta" in src


@pytest.mark.skipif(not CACHE_DIR.exists(), reason="cache dir not present")
def test_cache_has_at_least_10_files():
    """Stage A.4: data_cache contains ≥10 files."""
    files = [f for f in CACHE_DIR.iterdir() if f.is_file()]
    assert len(files) >= 10, f"Only {len(files)} cache files (expected ≥10)"


@pytest.mark.skipif(not CACHE_DIR.exists(), reason="cache dir not present")
def test_cache_has_large_panels():
    """Stage A.4: at least 2 cache files >10 MB (the parquet/pkl panels)."""
    big = [f for f in CACHE_DIR.iterdir()
           if f.is_file() and f.stat().st_size > 10 * 1024 * 1024]
    assert len(big) >= 2, f"Expected ≥2 large cache files, got {len(big)}"


@pytest.mark.skipif(not CACHE_DIR.exists(), reason="cache dir not present")
def test_cache_total_size_at_least_200mb():
    """Stage A.4: total cache size ≥200 MB."""
    total = sum(f.stat().st_size for f in CACHE_DIR.iterdir() if f.is_file())
    assert total >= 200 * 1024 * 1024, \
        f"Cache too small: {total / 1024**2:.0f} MB"


@pytest.mark.skipif(not RESULTS_DIR.exists(), reason="results dir not present")
def test_results_dir_has_v50_csv():
    """Stage A.5: at least one v50_*.csv exists in results/."""
    csvs = list(RESULTS_DIR.glob("v50_*.csv"))
    assert len(csvs) >= 1, "No v50_*.csv in results/"


@pytest.mark.skipif(not ORIGINAL_V50.exists(), reason="original v50 not on this machine")
def test_original_v50_still_has_hardcoded_path():
    """Stage A.8 (hard gate): ORIGINAL v50 untouched — still has the hardcoded path."""
    orig = ORIGINAL_V50.read_text(encoding="utf-8")
    assert r"D:\Quant Pipeline\Momentum pipeline\results" in orig, \
        "ORIGINAL v50 appears to have been modified — hardcoded path missing"
    assert r"D:\Quant Pipeline\Momentum pipeline\data_cache" in orig, \
        "ORIGINAL v50 cache path missing — modification detected"


@pytest.mark.skipif(
    not (ORIGINAL_V50.exists() and ORIGINAL_SHA_FILE.exists()),
    reason="original v50 or baseline SHA file not present",
)
def test_original_v50_sha256_matches_baseline():
    """Stage A.8 + G.7 (hard gate): ORIGINAL v50 SHA256 unchanged from sprint start."""
    baseline = ORIGINAL_SHA_FILE.read_text(encoding="utf-8").strip()
    current = _sha256_of(ORIGINAL_V50)
    assert baseline == current, (
        f"ORIGINAL v50 modified during sprint!\n"
        f"  baseline: {baseline}\n"
        f"  current:  {current}"
    )
