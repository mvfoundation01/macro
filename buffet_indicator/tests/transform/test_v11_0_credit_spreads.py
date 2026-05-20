"""v11.0 acceptance tests for credit spread compute (4 BAML variants)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ingest._base import SourceMissingError
from src.transform.credit_spread_compute import (
    REQUIRED_COLUMNS,
    VARIANT_REGISTRY,
    compute_all_credit_spreads,
    compute_credit_spread,
    latest_summary,
)


VARIANT_KEYS = tuple(VARIANT_REGISTRY.keys())


@pytest.fixture(scope="module")
def all_spreads() -> dict[str, pd.DataFrame]:
    return compute_all_credit_spreads()


# ---------------------------------------------------------------------------
# 1. Per-variant schema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant_key", VARIANT_KEYS)
def test_credit_spread_returns_required_columns(variant_key: str) -> None:
    df = compute_credit_spread(variant_key)
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"{variant_key} missing column {col!r}"
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.attrs.get("variant_key") == variant_key
    assert df.attrs.get("direction") == "standard"


def test_cs_hy_master_loads_and_returns_required_columns(
    all_spreads: dict[str, pd.DataFrame],
) -> None:
    assert "cs_hy_master" in all_spreads
    df = all_spreads["cs_hy_master"]
    assert (df["spread_raw"] > 0).all()
    assert df["log_spread"].notna().all()


def test_cs_ig_master_returns_required_columns(
    all_spreads: dict[str, pd.DataFrame],
) -> None:
    assert "cs_ig_master" in all_spreads
    df = all_spreads["cs_ig_master"]
    # IG OAS should always be < HY OAS in the same month.
    hy = all_spreads["cs_hy_master"]
    common = df.index.intersection(hy.index)
    assert (df.loc[common, "spread_raw"] < hy.loc[common, "spread_raw"]).all()


def test_cs_hy_bb_returns_required_columns(
    all_spreads: dict[str, pd.DataFrame],
) -> None:
    assert "cs_hy_bb" in all_spreads
    df = all_spreads["cs_hy_bb"]
    # BB OAS should always be < CCC OAS in the same month (better quality).
    ccc = all_spreads["cs_hy_ccc"]
    common = df.index.intersection(ccc.index)
    assert (df.loc[common, "spread_raw"] < ccc.loc[common, "spread_raw"]).all()


def test_cs_hy_ccc_returns_required_columns(
    all_spreads: dict[str, pd.DataFrame],
) -> None:
    assert "cs_hy_ccc" in all_spreads
    df = all_spreads["cs_hy_ccc"]
    # CCC is the lowest credit quality, so OAS should max out highest.
    assert df["spread_raw"].max() > 20  # peaks around 36-44 pp in 2008/2020


# ---------------------------------------------------------------------------
# 2. Signal direction (standard, no inversion)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant_key", VARIANT_KEYS)
def test_credit_spread_signal_equals_log_no_negation(variant_key: str) -> None:
    df = compute_credit_spread(variant_key)
    err = (df["signal"] - df["log_spread"]).abs().max()
    assert err < 1e-12, (
        f"{variant_key}: signal must equal log_spread (no negation); err={err}"
    )
    # Sanity: log_spread monotonic in spread_raw.
    assert np.allclose(np.log(df["spread_raw"]), df["log_spread"])


# ---------------------------------------------------------------------------
# 3. 2008 crisis stress signature
# ---------------------------------------------------------------------------


def test_credit_spread_2008_crisis_visible_in_data(
    all_spreads: dict[str, pd.DataFrame],
) -> None:
    """HY OAS must spike above 15 pp in Oct 2008 (per spec text)."""
    hy = all_spreads["cs_hy_master"]
    oct_2008 = hy.loc["2008-10-31"]
    assert oct_2008["spread_raw"] > 15, (
        f"HY OAS in Oct 2008 = {oct_2008['spread_raw']:.2f}pp; expected > 15."
    )
    # And the peak month should be Oct-Dec 2008.
    crisis_window = hy.loc["2008-09-01":"2009-01-31"]
    peak_date = crisis_window["spread_raw"].idxmax()
    assert 2008 <= peak_date.year <= 2009


# ---------------------------------------------------------------------------
# 4. Unknown variant key raises KeyError
# ---------------------------------------------------------------------------


def test_unknown_variant_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        compute_credit_spread("cs_does_not_exist")


# ---------------------------------------------------------------------------
# 5. latest_summary returns expected keys
# ---------------------------------------------------------------------------


def test_latest_summary_keys(all_spreads: dict[str, pd.DataFrame]) -> None:
    df = all_spreads["cs_hy_master"]
    s = latest_summary(df)
    assert set(s.keys()) == {"date", "spread_pp", "log_spread", "signal"}
    assert s["spread_pp"] > 0
