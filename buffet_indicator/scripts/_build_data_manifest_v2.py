"""Phase F-REPRO.A — augment data_manifest.json with v2.0 sprint series.

Reads data/master/*.parquet for the 11 v2.0 LC components, computes SHA-256
of each cached file, and writes the augmented manifest. Preserves pre-v2.0
entries (GDP, Wilshire, Shiller, etc.) for comprehensive coverage.

Authority: PROMPT_CC_v11_4_phase_F_REPRO.md §2.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


SEALED_SHA = "c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05"
VERDICT_SHA = "df542640992d4cf5b6014d6483629266f93399dd01d3d9f7cc9a181ea507ab0c"

V2_SERIES: dict[str, dict] = {
    "walcl":    {"used_by": ["z1"], "fred_id": "WALCL",     "freq": "W",  "units": "Billions of U.S. Dollars",                  "transform": "level_minus_wdtgal_minus_rrpontsyd_netfed",         "splice_partners": []},
    "wdtgal":   {"used_by": ["z1"], "fred_id": "WDTGAL",    "freq": "W",  "units": "Billions of U.S. Dollars",                  "transform": "subtracted_in_netfed",                              "splice_partners": []},
    "rrpontsyd":{"used_by": ["z1"], "fred_id": "RRPONTSYD", "freq": "D",  "units": "Billions of U.S. Dollars",                  "transform": "subtracted_in_netfed_with_zero_fill_lt_2013_09_23", "splice_partners": []},
    "m2_sl":    {"used_by": ["z2"], "fred_id": "M2SL",      "freq": "M",  "units": "Billions of U.S. Dollars",                  "transform": "yoy_pct_change_12mo",                               "splice_partners": []},
    "busloans": {"used_by": ["z3"], "fred_id": "BUSLOANS",  "freq": "M",  "units": "Billions of U.S. Dollars",                  "transform": "yoy_pct_change_12mo_pre_splice",                    "splice_partners": ["totll@1973-01-03 yoy-growth additive c per sealed §10.1"]},
    "totll":    {"used_by": ["z3"], "fred_id": "TOTLL",     "freq": "W",  "units": "Billions of U.S. Dollars",                  "transform": "yoy_pct_change_12mo_post_splice",                   "splice_partners": ["busloans@1973-01-03"]},
    "dtwexbgs": {"used_by": ["z4"], "fred_id": "DTWEXBGS",  "freq": "D",  "units": "Index Jan 2006=100",                         "transform": "log_then_inverted_via_negative_z_score",            "splice_partners": []},
    "tedrate":  {"used_by": ["z5"], "fred_id": "TEDRATE",   "freq": "D",  "units": "Percent",                                    "transform": "pit_z_pre_blend_120mo_warmup",                      "splice_partners": ["sofr-iorb_zblend@2022-02 to 2023-04 (14-month z-score blend)"]},
    "sofr":     {"used_by": ["z5"], "fred_id": "SOFR",      "freq": "D",  "units": "Percent",                                    "transform": "minus_iorb_then_pit_z_post_blend_24mo_warmup",      "splice_partners": ["iorb_extended@2021-07-31", "tedrate_zblend@2022-02 to 2023-04"]},
    "iorb":     {"used_by": ["z5"], "fred_id": "IORB",      "freq": "D",  "units": "Percent",                                    "transform": "iorb_post_2021_07_31",                              "splice_partners": ["ioer@2021-07-31"]},
    "ioer":     {"used_by": ["z5"], "fred_id": "IOER",      "freq": "D",  "units": "Percent",                                    "transform": "extended_to_iorb_pre_2021_07_31",                   "splice_partners": ["iorb@2021-07-31"]},
}


def build_manifest(repo_root: Path) -> dict:
    records: dict[str, dict] = {}

    # 1. v2.0 component series from data/master/*.parquet.
    for series_id, meta in V2_SERIES.items():
        p = repo_root / "data" / "master" / f"{series_id}.parquet"
        if not p.exists():
            print(f"MISSING: {p}")
            continue
        df = pd.read_parquet(p)
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        earliest = str(df.index.min().date()) if hasattr(df.index.min(), "date") else str(df.index.min())
        latest = str(df.index.max().date()) if hasattr(df.index.max(), "date") else str(df.index.max())
        records[f"master.{series_id}"] = {
            "series_id": meta["fred_id"],
            "source": "fred_alfred_observation_date_approximation",
            "source_tier": 2,
            "frequency": meta["freq"],
            "units": meta["units"],
            "n_observations": int(df.shape[0]),
            "earliest_date": earliest,
            "latest_date": latest,
            "sha256": sha,
            "cache_path": f"buffet_indicator/data/master/{series_id}.parquet",
            "vintage_basis": "observation_date_approximation_per_phase_b_c_arbitration_section_B_option_B3",
            "vintage_note": "Sealed §3.2.2 mandates load_master(vintage=t); Phase B+C §B approved observation-date approximation under Option B3. Per-origin feature_vintage_max_at_origin verified non-tautological by Phase F-BLK1.A + B.",
            "used_in_v2_0_components": meta["used_by"],
            "transformations_applied": [meta["transform"]],
            "splice_partners": meta["splice_partners"],
        }
        print(f"OK {series_id}: n={df.shape[0]} {earliest}..{latest} sha={sha[:12]}...")

    # 2. Forward-return source series (read from prior manifest).
    prior_path = repo_root / "data_manifest.json"
    prior_entries = {}
    if prior_path.exists():
        try:
            prior = json.loads(prior_path.read_text(encoding="utf-8"))
            for e in prior.get("entries", []):
                if "key" in e:
                    prior_entries[e["key"]] = e
        except Exception as exc:
            print(f"prior manifest read failed: {exc}")

    spxtr = prior_entries.get("tradingview.spxtr")
    if spxtr:
        records["forward_returns.spxtr_daily"] = {
            "series_id": "SPXTR",
            "symbol": spxtr.get("symbol", "SPXTR"),
            "source": "tradingview_csv",
            "source_tier": 5,
            "frequency": "D",
            "units": "Index points (USD, total return)",
            "n_observations": spxtr.get("n_observations"),
            "earliest_date": spxtr.get("earliest"),
            "latest_date": spxtr.get("latest"),
            "sha256": spxtr.get("sha256"),
            "cache_path": "raw data/SP_SPXTR, 1D.csv",
            "used_in_v2_0_components": ["forward_returns_post_1988"],
            "transformations_applied": ["monthly_eom_level_then_horizon_forward_return"],
            "splice_partners": ["shiller_nominal_total_return@1988-01-01"],
        }
        print(f"OK forward_returns.spxtr_daily preserved from prior manifest")

    shiller = prior_entries.get("shiller.ie_data")
    if shiller:
        records["forward_returns.shiller_ie_data"] = {
            "series_id": "SHILLER_IE_DATA",
            "source": "shiller_ie_data_xls",
            "source_tier": 1,
            "frequency": "M",
            "units": "Index (Shiller monthly composite)",
            "n_observations": shiller.get("n_observations"),
            "earliest_date": shiller.get("earliest"),
            "latest_date": shiller.get("latest"),
            "sha256": shiller.get("sha256"),
            "cache_path": "data/raw/ie_data.xls (or comparable Shiller monthly download)",
            "used_in_v2_0_components": ["forward_returns_pre_1988"],
            "transformations_applied": ["nominal_total_return_then_splice_at_1988_01_with_spxtr"],
            "splice_partners": ["spxtr_daily@1988-01-01"],
        }
        print(f"OK forward_returns.shiller_ie_data preserved from prior manifest")

    # 3. Preserve pre-v2.0 entries for comprehensive coverage.
    preserve_keys = [
        "fred.gdp", "fred.equities_all", "fred.equities_public", "fred.equities_nonfin",
        "tradingview.spx", "tradingview.wilshire_tv", "tradingview.gdp_backup",
        "yahoo.wilshire", "master.wilshire_5000",
    ]
    for k in preserve_keys:
        if k in prior_entries:
            entry = {**prior_entries[k]}
            entry["preserved_from_pre_v2_0_manifest"] = True
            records[k] = entry
            print(f"preserved {k}")

    # 4. Top-level metadata + series block.
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    tier_counts: dict[str, int] = {}
    for r in records.values():
        t = str(r.get("source_tier", "?"))
        tier_counts[t] = tier_counts.get(t, 0) + 1

    return {
        "_meta": {
            "manifest_version": "v2.0-F_REPRO.A",
            "generated_at": now_iso,
            "v11_4_sprint_authority": "PROMPT_CC_v11_4_phase_F_REPRO.md §2",
            "sealed_pre_reg_sha256": SEALED_SHA,
            "canonical_verdict_sha256": VERDICT_SHA,
            "total_series": len(records),
            "tier_distribution": tier_counts,
            "schema_note": (
                "Each series entry pins source, frequency, units, n_observations, "
                "earliest/latest, SHA-256 of cached file, cache_path, vintage_basis, "
                "used_in_v2_0_components, transformations_applied, splice_partners. "
                "Preserved pre-v2.0 entries carry preserved_from_pre_v2_0_manifest=true."
            ),
        },
        "series": records,
    }


def write_byte_exact_json(manifest: dict, path: Path) -> int:
    """Byte-exact LF write for cross-OS reproducibility per BLK-1.F pattern."""
    body = json.dumps(manifest, indent=2, sort_keys=False, default=str)
    body_bytes = body.encode("utf-8").replace(b"\r\n", b"\n")
    path.write_bytes(body_bytes)
    return len(body_bytes)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest = build_manifest(repo_root)
    out_path = repo_root / "data_manifest.json"
    n_bytes = write_byte_exact_json(manifest, out_path)
    print(f"\nwrote {out_path}: {n_bytes} bytes; {len(manifest['series'])} series; tiers={manifest['_meta']['tier_distribution']}")


if __name__ == "__main__":
    main()
