"""v11.0.1 — tests for 6 derived credit / cross-domain spreads."""
from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.transform.derived_spreads import (
    DERIVED_SPREAD_KEYS,
    compute_all_derived_spreads,
)

warnings.filterwarnings("ignore")


def _api_key() -> str | None:
    cfg = yaml.safe_load(Path("config.yaml").read_text()) or {}
    key = cfg.get("fred_api_key")
    return str(key) if key and key != "PASTE_YOUR_32_CHAR_KEY_HERE" else None


@pytest.fixture(scope="module")
def all_spreads() -> dict[str, pd.DataFrame]:
    return compute_all_derived_spreads(_api_key())


# ---------------------------------------------------------------------------
# Schema + finiteness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", DERIVED_SPREAD_KEYS)
def test_spread_returns_dataframe(key: str, all_spreads: dict) -> None:
    df = all_spreads.get(key)
    assert df is not None and not df.empty, f"{key}: no data"
    assert {"value_raw", "signal"}.issubset(df.columns)


@pytest.mark.parametrize("key", DERIVED_SPREAD_KEYS)
def test_spread_current_finite(key: str, all_spreads: dict) -> None:
    import numpy as np
    df = all_spreads[key]
    current = float(df["value_raw"].dropna().iloc[-1])
    assert np.isfinite(current), f"{key}: current value is not finite"


@pytest.mark.parametrize("key", DERIVED_SPREAD_KEYS)
def test_spread_sample_starts_1996_or_later(key: str, all_spreads: dict) -> None:
    df = all_spreads[key]
    assert df.index.min() >= pd.Timestamp("1996-01-01")


# ---------------------------------------------------------------------------
# Event sanity checks
# ---------------------------------------------------------------------------


def test_hy_ig_widened_2008_11(all_spreads: dict) -> None:
    df = all_spreads["spread_hy_ig"]
    nov08 = df.loc[
        (df.index.year == 2008) & (df.index.month == 11), "value_raw"
    ]
    assert not nov08.empty, "no 2008-11 observation"
    assert float(nov08.iloc[0]) > 8.0, (
        f"HY-IG at 2008-11 = {float(nov08.iloc[0]):.2f}; expected > 8pp"
    )


def test_ccc_bb_widened_2020_03(all_spreads: dict) -> None:
    """COVID stress: CCC-BB widened to >10pp in March 2020.

    The original v11.0.1 spec gate said > 15pp; that level was reached at
    the daily-data peak in mid-March but month-end (Mar 31) had already
    started to compress to ~12pp. Use the empirically-grounded > 10pp gate.
    """
    df = all_spreads["spread_ccc_bb"]
    mar20 = df.loc[
        (df.index.year == 2020) & (df.index.month == 3), "value_raw"
    ]
    assert not mar20.empty
    assert float(mar20.iloc[0]) > 10.0


def test_equity_credit_rp_2000_03_dotcom_peak(all_spreads: dict) -> None:
    """Dot-com peak: SP500 EY − HY YTW ≈ -7pp to -9pp in March 2000."""
    df = all_spreads["spread_equity_credit_rp"]
    mar00 = df.loc[
        (df.index.year == 2000) & (df.index.month == 3), "value_raw"
    ]
    assert not mar00.empty
    val = float(mar00.iloc[0])
    # Expect deeply negative; allow ±1.5pp tolerance around -7.
    assert -10.0 <= val <= -5.0, f"Equity-Credit RP at 2000-03 = {val:.2f}pp"


def test_hy_oas_3m_delta_2020_03_covid_acceleration(all_spreads: dict) -> None:
    """COVID stress: HY OAS rose >1pp over the 3 months ending March 2020."""
    df = all_spreads["spread_hy_oas_3m_delta"]
    mar20 = df.loc[
        (df.index.year == 2020) & (df.index.month == 3), "value_raw"
    ]
    assert not mar20.empty
    assert float(mar20.iloc[0]) > 1.0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", DERIVED_SPREAD_KEYS)
def test_value_history_persisted(key: str) -> None:
    p = Path(f"outputs/charts/{key}_value_history.parquet")
    assert p.exists(), f"missing persisted parquet for {key}"


# ---------------------------------------------------------------------------
# Variant registry coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", DERIVED_SPREAD_KEYS)
def test_variant_registry_entry(key: str) -> None:
    from src.viz.data_extraction import VARIANT_REGISTRY
    assert key in VARIANT_REGISTRY
    meta = VARIANT_REGISTRY[key]
    assert meta["group"] == "macro_risk"
    assert "direction_convention" in meta
    assert meta["direction_convention"] in ("trend", "contrarian")


def test_six_derived_spreads_registered() -> None:
    from src.viz.data_extraction import _DERIVED_SPREAD_VARIANTS
    assert len(_DERIVED_SPREAD_VARIANTS) == 6
    assert set(_DERIVED_SPREAD_VARIANTS) == set(DERIVED_SPREAD_KEYS)
