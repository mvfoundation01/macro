"""v11.0b — Run all 7 macro indicators + 3 MRC variants through the dual-frame
predictive pipeline; persist results.

Usage::

    python -m scripts.run_v11_0b_macro_pipeline
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import pandas as pd
import yaml

warnings.filterwarnings("ignore")


def _load_fred_key() -> str | None:
    cfg = yaml.safe_load(Path("config.yaml").read_text()) or {}
    key = cfg.get("fred_api_key")
    return str(key) if key and key != "PASTE_YOUR_32_CHAR_KEY_HERE" else None


def _load_forward_returns():
    from src.config import TV_SPXTR
    from src.ingest.csv_loader import load_tradingview_file
    from src.ingest.shiller_loader import load_shiller
    from src.transform.forward_returns import build_forward_returns

    sh = load_shiller()
    spxtr_ts = load_tradingview_file(TV_SPXTR, expected_frequency="D")
    return build_forward_returns(
        sh, spxtr_ts.data["close"], check_continuity=False
    )


def _load_signal(variant_key: str) -> pd.Series:
    pq = Path(f"outputs/charts/{variant_key}_value_history.parquet")
    df = pd.read_parquet(pq).set_index("date")
    return df["signal"].dropna()


def _load_mrc_signal(scheme: str) -> pd.Series:
    df = pd.read_parquet("outputs/charts/mrc_value_history.parquet")
    out = (
        df[df["scheme"] == scheme]
        .set_index("date")["mrc_z"]
        .dropna()
        .sort_index()
    )
    return out


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


def main() -> None:
    from src.models.macro_orchestrator import (
        analyze_macro_indicator,
        persist_indicator_block,
        quadrant_history,
        quadrant_summary,
    )

    fr = _load_forward_returns()
    out_root = Path("outputs/indicators")
    out_root.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict] = []
    z_series_by_variant: dict[str, pd.Series] = {}

    for vk in VARIANT_KEYS:
        try:
            sig = _load_signal(vk)
        except Exception as exc:
            print(f"[skip] {vk}: {exc}")
            continue
        print(f"[run] {vk}: n={len(sig)}")
        block = analyze_macro_indicator(
            vk, sig, forward_returns=fr, bootstrap_n=500, n_bootstrap_prob=500
        )
        persist_indicator_block(vk, block, out_dir=out_root)
        z_series_by_variant[vk] = block["long_run"]["z_score_series"].dropna()
        summary_rows.append(
            {
                "variant_key": vk,
                "z_long_run": block["long_run"]["z_score"],
                "regime_long_run": block["long_run"]["regime"],
                "z_current_regime": block["current_regime"]["z_score"],
                "n_obs": block["n_observations"],
                "sample_penalty": block["sample_size_penalty"],
            }
        )

    # MRC variants
    for scheme in MRC_SCHEMES:
        vk = f"mrc_{scheme}"
        try:
            sig = _load_mrc_signal(scheme)
        except Exception as exc:
            print(f"[skip] {vk}: {exc}")
            continue
        print(f"[run] {vk}: n={len(sig)}")
        block = analyze_macro_indicator(
            vk, sig, forward_returns=fr, bootstrap_n=500, n_bootstrap_prob=500
        )
        persist_indicator_block(vk, block, out_dir=out_root)
        z_series_by_variant[vk] = block["long_run"]["z_score_series"].dropna()
        summary_rows.append(
            {
                "variant_key": vk,
                "z_long_run": block["long_run"]["z_score"],
                "regime_long_run": block["long_run"]["regime"],
                "z_current_regime": block["current_regime"]["z_score"],
                "n_obs": block["n_observations"],
                "sample_penalty": block["sample_size_penalty"],
            }
        )

    # Persist summary table.
    summary_df = pd.DataFrame(summary_rows)
    summary_path = out_root / "v11_0b_summary.parquet"
    summary_df.to_parquet(summary_path)
    print(f"wrote {summary_path}")
    print(summary_df.to_string())

    # Cross-composite quadrant analysis
    mvci_lr = (
        pd.read_parquet("outputs/charts/z_history.parquet")
        .query("variant == 'mvci' and frame == 'long_run'")
        .set_index("date")["z_score"]
    )
    mrc_ew = z_series_by_variant.get("mrc_equal_weight")
    if mrc_ew is None:
        # Fallback: use the persisted MRC value history.
        mrc_ew = _load_mrc_signal("equal_weight")
    cross_dir = Path("outputs/cross_composite")
    cross_dir.mkdir(parents=True, exist_ok=True)
    quad_df = quadrant_history(mvci_lr, mrc_ew, fr["fr_spliced"], horizon_col="r_120m")
    quad_df.reset_index().to_parquet(cross_dir / "mvci_mrc_joint.parquet")
    summary = quadrant_summary(quad_df)
    summary.to_parquet(cross_dir / "mvci_mrc_quadrant_summary.parquet")
    print(f"wrote {cross_dir / 'mvci_mrc_joint.parquet'}")
    print(summary.to_string())

    # Current quadrant
    current = quad_df.iloc[-1]
    print()
    print(
        f"Current observation ({current.name.date()}): "
        f"MVCI={current['mvci_z']:+.3f} MRC={current['mrc_z']:+.3f} -> "
        f"quadrant = {current['quadrant']}"
    )

    # Persist current-state JSON for dashboard consumption.
    state = {
        "date": str(current.name.date()),
        "mvci_z": float(current["mvci_z"]),
        "mrc_z": float(current["mrc_z"]),
        "quadrant": str(current["quadrant"]),
        "corr_mvci_mrc": float(quad_df["mvci_z"].corr(quad_df["mrc_z"])),
    }
    (cross_dir / "current_state.json").write_text(json.dumps(state, indent=2))
    print(f"wrote {cross_dir / 'current_state.json'}")


if __name__ == "__main__":
    main()
