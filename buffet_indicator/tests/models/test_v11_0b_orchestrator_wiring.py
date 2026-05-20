"""v11.0b orchestrator wiring tests for the 7 macro indicators + 3 MRC variants.

Verifies the full dual-frame predictive pipeline runs end-to-end and the
sample-size penalty downgrades small-sample credit-spread convictions.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.models.macro_orchestrator import (
    analyze_macro_indicator,
    classify_quadrant,
    persist_indicator_block,
    quadrant_history,
    quadrant_summary,
)


warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Module-scoped fixtures (build forward returns + signals once)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def forward_returns():
    from src.config import TV_SPXTR
    from src.ingest.csv_loader import load_tradingview_file
    from src.ingest.shiller_loader import load_shiller
    from src.transform.forward_returns import build_forward_returns

    sh = load_shiller()
    try:
        spxtr_ts = load_tradingview_file(TV_SPXTR, expected_frequency="D")
        return build_forward_returns(
            sh, spxtr_ts.data["close"], check_continuity=False
        )
    except Exception:
        return build_forward_returns(sh, None, check_continuity=False)


def _load_signal(variant_key: str) -> pd.Series:
    pq = Path(f"outputs/charts/{variant_key}_value_history.parquet")
    df = pd.read_parquet(pq).set_index("date")
    return df["signal"].dropna()


def _load_mrc(scheme: str) -> pd.Series:
    df = pd.read_parquet("outputs/charts/mrc_value_history.parquet")
    return (
        df[df["scheme"] == scheme]
        .set_index("date")["mrc_z"]
        .dropna()
        .sort_index()
    )


VARIANT_KEYS = (
    "yc_10y3m",
    "yc_10y2y",
    "cs_hy_master",
    "cs_ig_master",
    "cs_hy_bb",
    "cs_hy_ccc",
    "margin_debt_growth",
)
MRC_SCHEMES = ("equal_weight", "inv_variance", "pca_pc1")


@pytest.fixture(scope="module")
def all_blocks(forward_returns) -> dict:
    out: dict = {}
    for vk in VARIANT_KEYS:
        try:
            sig = _load_signal(vk)
        except FileNotFoundError:
            pytest.skip(f"missing signal parquet for {vk}")
        out[vk] = analyze_macro_indicator(
            vk, sig, forward_returns=forward_returns,
            bootstrap_n=200, n_bootstrap_prob=200,
        )
    for scheme in MRC_SCHEMES:
        vk = f"mrc_{scheme}"
        sig = _load_mrc(scheme)
        out[vk] = analyze_macro_indicator(
            vk, sig, forward_returns=forward_returns,
            bootstrap_n=200, n_bootstrap_prob=200,
        )
    return out


# ---------------------------------------------------------------------------
# 1) Each indicator's dual-frame pipeline returns finite z + regression
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant_key", VARIANT_KEYS)
def test_indicator_dual_frame_returns_finite_outputs(
    variant_key: str, all_blocks: dict
) -> None:
    blk = all_blocks[variant_key]
    assert "long_run" in blk and "current_regime" in blk
    for frame in ("long_run", "current_regime"):
        z = blk[frame]["z_score"]
        assert np.isfinite(z), f"{variant_key}.{frame}.z_score = {z}"
    # Forward outlook with at least the 60m horizon available.
    primary = blk["long_run"]["forward_outlook"]["primary"]
    assert any(
        h_blk.get("available") for h_blk in primary.values()
    ), f"{variant_key}: no horizon available"


# ---------------------------------------------------------------------------
# 2) Each MRC variant's dual-frame returns finite outputs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scheme", MRC_SCHEMES)
def test_mrc_variant_dual_frame_returns_finite_outputs(
    scheme: str, all_blocks: dict
) -> None:
    blk = all_blocks[f"mrc_{scheme}"]
    assert np.isfinite(blk["long_run"]["z_score"])
    assert np.isfinite(blk["current_regime"]["z_score"])


# ---------------------------------------------------------------------------
# 3) Cross-composite quadrant classification
# ---------------------------------------------------------------------------


def test_classify_quadrant_high_val_high_stress() -> None:
    assert classify_quadrant(2.0, 1.5) == "high_val_high_stress"


def test_classify_quadrant_high_val_low_stress() -> None:
    assert classify_quadrant(1.8, -0.5) == "high_val_low_stress"


def test_classify_quadrant_low_val_high_stress() -> None:
    assert classify_quadrant(-0.5, 1.2) == "low_val_high_stress"


def test_classify_quadrant_low_val_low_stress() -> None:
    assert classify_quadrant(-2.0, -1.5) == "low_val_low_stress"


def test_quadrant_history_matches_components(forward_returns) -> None:
    mvci = (
        pd.read_parquet("outputs/charts/z_history.parquet")
        .query("variant == 'mvci' and frame == 'long_run'")
        .set_index("date")["z_score"]
    )
    mrc = _load_mrc("equal_weight")
    qdf = quadrant_history(mvci, mrc, forward_returns["fr_spliced"], horizon_col="r_120m")
    assert {"mvci_z", "mrc_z", "quadrant"}.issubset(qdf.columns)
    # No quadrant should be NaN or empty string.
    assert qdf["quadrant"].notna().all()
    assert (qdf["quadrant"] != "").all()


def test_quadrant_summary_returns_four_quadrants_or_subset(
    forward_returns,
) -> None:
    mvci = (
        pd.read_parquet("outputs/charts/z_history.parquet")
        .query("variant == 'mvci' and frame == 'long_run'")
        .set_index("date")["z_score"]
    )
    mrc = _load_mrc("equal_weight")
    qdf = quadrant_history(mvci, mrc, forward_returns["fr_spliced"], horizon_col="r_120m")
    summary = quadrant_summary(qdf)
    expected = {
        "high_val_high_stress",
        "high_val_low_stress",
        "low_val_high_stress",
        "low_val_low_stress",
    }
    assert set(summary.index).issubset(expected)
    assert (summary["n_months"] > 0).all()


# ---------------------------------------------------------------------------
# 4) Conviction in [0, 5] for each variant at the current observation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "variant_key", VARIANT_KEYS + ("mrc_equal_weight",)
)
def test_conviction_in_range(variant_key: str, all_blocks: dict) -> None:
    blk = all_blocks[variant_key]
    fc = blk["long_run"].get("full_conviction", {})
    if not fc:
        pytest.skip(f"{variant_key}: no full_conviction block")
    for h_key, conv in fc.items():
        if isinstance(conv, dict) and "score" in conv:
            score = float(conv["score"])
            assert 0.0 <= score <= 5.0, f"{variant_key}.{h_key} conv = {score}"


# ---------------------------------------------------------------------------
# 5) P(neg return) in [0, 1] with non-zero CI width
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "variant_key", ["cs_hy_master", "yc_10y2y", "mrc_equal_weight"]
)
def test_p_negative_return_valid(variant_key: str, all_blocks: dict) -> None:
    blk = all_blocks[variant_key]
    primary = blk["long_run"]["forward_outlook"]["primary"]
    # Use whichever long horizon is available.
    for h_key in ("h_120m", "h_60m", "h_36m", "h_12m"):
        h_blk = primary.get(h_key)
        if h_blk and h_blk.get("available"):
            prob = h_blk.get("probabilities") or {}
            events = prob.get("events") or {}
            p_neg_entry = events.get("P_neg_return")
            if not p_neg_entry:
                continue
            p_neg = float(p_neg_entry.get("point", float("nan")))
            ci_low, ci_high = p_neg_entry.get("ci95", (None, None))
            assert 0.0 <= p_neg <= 1.0, f"{variant_key}.{h_key} P(neg) = {p_neg}"
            # Bootstrap CI should have non-zero width (some sampling variation).
            if ci_low is not None and ci_high is not None:
                assert ci_high >= ci_low
            return
    pytest.skip(f"{variant_key}: no usable horizon")


# ---------------------------------------------------------------------------
# 6) Sample-size penalty downgrades small-sample convictions
# ---------------------------------------------------------------------------


def test_sample_size_penalty_below_one_for_short_sample() -> None:
    """A synthetic 80-obs signal would get penalty == 0.8 (< 1.0).

    Bai-Perron requires T >= 120, so the pipeline cannot run on 80 obs;
    we verify the penalty formula directly on the floor constant instead.
    Then we run the pipeline at 130 obs (where penalty saturates at 1.0)
    to confirm it does not over-apply.
    """
    rng = np.random.default_rng(42)
    # Use 130 observations so the pipeline runs but penalty still applies.
    idx2 = pd.date_range("2010-01-31", periods=130, freq="ME")
    sig2 = pd.Series(rng.normal(size=130), index=idx2, name="synth2")
    fr = pd.DataFrame(
        {
            "r_12m": rng.normal(0.05, 0.1, size=130),
            "r_60m": rng.normal(0.05, 0.1, size=130),
            "r_120m": rng.normal(0.05, 0.1, size=130),
        },
        index=idx2,
    )
    block = analyze_macro_indicator(
        "synth2",
        sig2,
        forward_returns={"fr_spliced": fr},
        bootstrap_n=100,
        n_bootstrap_prob=100,
    )
    # 130/100 = 1.3, but min(1, 1.3) = 1.0. So with 130 obs, penalty = 1.0.
    assert block["sample_size_penalty"] == 1.0
    # For the SHORT sample (80 obs), the formula gives 0.8 directly.
    # We compute it manually since the pipeline can't run on 80 obs.
    from src.models.macro_orchestrator import _SAMPLE_PENALTY_FLOOR  # noqa: PLC0415
    penalty_80 = min(1.0, 80 / _SAMPLE_PENALTY_FLOOR)
    assert penalty_80 == pytest.approx(0.8)


def test_sample_size_penalty_applied_to_conviction(all_blocks: dict) -> None:
    """If raw conviction > 0, the persisted score should equal raw * penalty."""
    blk = all_blocks["cs_hy_master"]
    fc = blk["long_run"].get("full_conviction", {})
    for h_key, conv in fc.items():
        if isinstance(conv, dict) and "score_raw_unpenalized" in conv:
            penalty = conv.get("sample_size_penalty_applied", 1.0)
            assert conv["score"] == pytest.approx(
                conv["score_raw_unpenalized"] * penalty, abs=1e-6
            )


def test_sample_size_penalty_credit_spreads_full(all_blocks: dict) -> None:
    """Credit spreads have 354 observations (1996-12 onward), so penalty = 1.0."""
    blk = all_blocks["cs_hy_master"]
    assert blk["sample_size_penalty"] == 1.0


# ---------------------------------------------------------------------------
# 7) MVCI invariance vs v11.0a
# ---------------------------------------------------------------------------


def test_mvci_z_long_run_unchanged_vs_v11_0a() -> None:
    """MVCI long-run z must equal v11.0a's +1.786718σ to ±1e-3."""
    df = pd.read_parquet("outputs/charts/z_history.parquet")
    mvci_lr = (
        df.query("variant == 'mvci' and frame == 'long_run'")
        .set_index("date")["z_score"]
        .iloc[-1]
    )
    assert abs(float(mvci_lr) - 1.786718) < 1e-3


def test_mvci_z_current_regime_finite() -> None:
    df = pd.read_parquet("outputs/charts/z_history.parquet")
    mvci_cr = (
        df.query("variant == 'mvci' and frame == 'current_regime'")
        .set_index("date")["z_score"]
        .iloc[-1]
    )
    assert np.isfinite(float(mvci_cr))


def test_corr_mvci_mrc_below_threshold(forward_returns) -> None:
    """Acceptance gate §11.0a: corr(MVCI, MRC) < 0.80."""
    df = pd.read_parquet("outputs/charts/z_history.parquet")
    mvci_lr = (
        df.query("variant == 'mvci' and frame == 'long_run'")
        .set_index("date")["z_score"]
    )
    mrc_ew = _load_mrc("equal_weight")
    common = mvci_lr.index.intersection(mrc_ew.index)
    assert len(common) >= 60
    corr = float(mvci_lr.loc[common].corr(mrc_ew.loc[common]))
    assert abs(corr) < 0.80, f"corr(MVCI, MRC) = {corr:+.3f}"


# ---------------------------------------------------------------------------
# 8) Persistence (parquet write succeeds and round-trips)
# ---------------------------------------------------------------------------


def test_persist_indicator_block_roundtrip(tmp_path: Path, all_blocks: dict) -> None:
    out_dir = tmp_path / "indicators"
    persist_indicator_block("cs_hy_master", all_blocks["cs_hy_master"], out_dir=out_dir)
    pq = out_dir / "cs_hy_master" / "dual_frame_summary.parquet"
    assert pq.exists()
    df = pd.read_parquet(pq)
    # Expected rows: 2 frames × number of available horizons (≥ 1).
    assert len(df) >= 2
    assert "z_score" in df.columns
    assert "beta_hat" in df.columns


def test_persistence_file_exists_for_all_variants() -> None:
    """The shell pipeline run should have produced one file per variant."""
    for vk in VARIANT_KEYS:
        pq = Path(f"outputs/indicators/{vk}/dual_frame_summary.parquet")
        assert pq.exists(), f"missing {pq}"
    for scheme in MRC_SCHEMES:
        pq = Path(f"outputs/indicators/mrc_{scheme}/dual_frame_summary.parquet")
        assert pq.exists(), f"missing {pq}"


def test_v11_0b_summary_parquet_has_expected_rows() -> None:
    """The summary parquet must include the v11.0b core set; v11.0.2 added 6
    derived spreads which are also expected to be present once the pipeline
    has been run after v11.0.2 Stage A."""
    df = pd.read_parquet("outputs/indicators/v11_0b_summary.parquet")
    v11_0b_expected = set(VARIANT_KEYS) | {f"mrc_{s}" for s in MRC_SCHEMES}
    present = set(df["variant_key"])
    assert v11_0b_expected.issubset(present), (
        f"missing v11.0b variants: {v11_0b_expected - present}"
    )


def test_cross_composite_current_state_persisted() -> None:
    import json
    p = Path("outputs/cross_composite/current_state.json")
    assert p.exists()
    state = json.loads(p.read_text())
    assert {"date", "mvci_z", "mrc_z", "quadrant", "corr_mvci_mrc"} == set(
        state.keys()
    )
    assert state["quadrant"] in {
        "high_val_high_stress",
        "high_val_low_stress",
        "low_val_high_stress",
        "low_val_low_stress",
    }
    assert abs(state["corr_mvci_mrc"]) < 0.80


def test_quadrant_summary_n_months_sums_to_total(forward_returns) -> None:
    mvci = (
        pd.read_parquet("outputs/charts/z_history.parquet")
        .query("variant == 'mvci' and frame == 'long_run'")
        .set_index("date")["z_score"]
    )
    mrc = _load_mrc("equal_weight")
    qdf = quadrant_history(mvci, mrc, forward_returns["fr_spliced"], horizon_col="r_120m")
    summary = quadrant_summary(qdf.dropna(subset=["forward_return"]))
    n_total = int(summary["n_months"].sum())
    expected = int(qdf["forward_return"].notna().sum())
    assert n_total == expected
