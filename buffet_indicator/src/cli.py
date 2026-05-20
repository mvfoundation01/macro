"""CLI entry point.

Usage:
    python -m src.cli              # run the ingestion pipeline (default)
    python -m src.cli model        # run modeling pipeline + build dashboard
    python -m src.cli dashboard    # rebuild dashboard only (Spec v8a)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from src.config import ensure_skeleton


def _load_api_key(cfg_path: Path) -> str | None:
    if not cfg_path.exists():
        return None
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    key = cfg.get("fred_api_key")
    if key and key != "PASTE_YOUR_32_CHAR_KEY_HERE":
        return str(key)
    return None


def _run_modeling(args: argparse.Namespace) -> int:
    from src.models.orchestrator_modeling import run_modeling

    ensure_skeleton()
    api_key = _load_api_key(Path(args.config))
    result = run_modeling(api_key=api_key, bootstrap_n=args.bootstrap_n)

    h = result["headline"]
    print(
        f"\nHeadline ({h['asof']}, view={h['view']}, "
        f"primary_frame={h['interpretation']['primary_frame']}):\n"
    )

    def _outlook_line(payload: dict) -> str:
        if not payload or not payload.get("available"):
            return "  (forward outlook not available)"
        reg = payload["regression"]
        oos = payload["oos"]["goyal_welch"]
        events = payload["probabilities"]["events"]
        p_neg = events.get("P_neg_return", {})
        p_below_5 = events.get("P_below_5pct", {})
        p_above_7 = events.get("P_above_7pct", {})

        def _ci(p: dict) -> str:
            lo, hi = p.get("ci95", (float("nan"), float("nan")))
            return f"[{lo * 100:.0f}%, {hi * 100:.0f}%]"

        return (
            f"      regression: beta={reg['beta']:+.4f}  SE_NW={reg['beta_se_nw']:.4f}  "
            f"t_NW={reg['t_nw']:+.2f}  R^2_in={reg['r_squared']:.2f}  "
            f"R^2_OOS={oos['r2_oos']:.2f}\n"
            f"      P(neg {payload['horizon_months']}M)  : {p_neg.get('point', float('nan'))*100:5.1f}% "
            f"{_ci(p_neg)}  conf={p_neg.get('confidence_pct', float('nan')):.0f}%\n"
            f"      P(<5% CAGR) : {p_below_5.get('point', float('nan'))*100:5.1f}% {_ci(p_below_5)}\n"
            f"      P(>7% CAGR) : {p_above_7.get('point', float('nan'))*100:5.1f}% {_ci(p_above_7)}"
        )

    for vname, v in h["variants"].items():
        lr, cr = v["long_run"], v["current_regime"]
        fi = v["frame_interpretation"]
        label = v.get("headline_label", vname)
        unit = v.get("headline_unit", "")
        value = v.get("headline_value", v.get("bi_value"))
        # Format BI variants with %, CAPE with bare number.
        if unit == "%":
            value_str = f"{value:,.1f}%"
        else:
            value_str = f"{value:,.2f}"
        print(f"  {vname:20s}  ({label}: {value_str})")
        print(
            f"    long_run        z={lr['z_score']:+.2f}  "
            f"pct={lr['empirical_percentile']:5.1f}  "
            f"regime={lr['regime']:22s}  conf={lr['confidence_pct']:.0f}%"
        )
        print(
            f"    current_regime  z={cr['z_score']:+.2f}  "
            f"pct={cr['empirical_percentile']:5.1f}  "
            f"regime={cr['regime']:22s}  conf={cr['confidence_pct']:.0f}%  "
            f"[breaks: {cr.get('n_breaks', 0)}]"
        )
        print(f"    [{fi['narrative_code']}]  z_spread={fi['z_spread']:.2f}")

        outlook = lr.get("forward_outlook", {})
        h120 = outlook.get("primary", {}).get("h_120m")
        if h120:
            print("    Forward outlook (long_run, primary FR=spliced, h=10Y):")
            print(_outlook_line(h120))
        fc = lr.get("full_conviction", {}).get("h_120m")
        if fc:
            print(f"    FULL CONVICTION (section 6.3, 10Y): {fc['score']:.2f}/5.00")

    xv_lr = h["cross_variant_long_run"]
    xv_cr = h["cross_variant_current_regime"]
    pc = h["preliminary_conviction"]
    intr = h["interpretation"]
    print("\nCross-variant:")
    print(
        f"  long_run        mean_z={xv_lr['mean_z']:+.2f}  "
        f"agreement={xv_lr['agreement']:.2f}  regime={xv_lr['combined_regime']}"
    )
    print(
        f"  current_regime  mean_z={xv_cr['mean_z']:+.2f}  "
        f"agreement={xv_cr['agreement']:.2f}  regime={xv_cr['combined_regime']}"
    )
    print(f"\nDual-frame conviction (v4.2 preliminary): {pc['score']:.2f}/5.00")
    print(
        f"\n=== Interpretation ({intr['narrative_code']}, "
        f"primary={intr['primary_frame']}) ==="
    )
    print(intr["narrative"])
    print("\n(Full per-horizon table -> outputs/tables/forward_regressions.csv)")

    # Spec v8a: auto-build the dashboard after the model run.
    try:
        from src.viz.build_dashboard import build_dashboard

        path = build_dashboard()
        print(f"Dashboard rebuilt -> {path}")
    except Exception as exc:  # noqa: BLE001
        print(f"(Dashboard build skipped: {exc})")
    return 0


def _run_dashboard(args: argparse.Namespace) -> int:
    from src.viz.build_dashboard import build_dashboard

    path = build_dashboard()
    print(f"Dashboard written: {path}")
    return 0


def _run_backtest(args: argparse.Namespace) -> int:
    """v10.0: tactical MVCI backtest with bootstrap-CI'd performance metrics."""
    from src.backtest.run import print_summary, run_real_data_backtest

    summary = run_real_data_backtest(
        seed=args.seed,
        bootstrap_reps=args.bootstrap_reps,
    )
    print_summary(summary)
    print("\nOutputs persisted under outputs/backtest/")
    return 0


def _run_emit_diagnostics(args: argparse.Namespace) -> int:
    """v8b.1 A.5: regenerate the diagnostics parquets without re-running modeling."""
    from src.config import OUTPUTS_DIR
    from src.models.diagnostics import emit_diagnostics

    charts_dir = OUTPUTS_DIR / "charts"
    paths = emit_diagnostics(charts_dir)
    for name, p in paths.items():
        print(f"  {name}: {p} ({p.stat().st_size} bytes)")
    if getattr(args, "rebuild_dashboard", False):
        from src.viz.build_dashboard import build_dashboard
        out = build_dashboard()
        print(f"Dashboard rebuilt: {out}")
    return 0


def _run_ingestion(args: argparse.Namespace) -> int:
    from src.ingest.orchestrator import run_ingestion

    ensure_skeleton()
    api_key = _load_api_key(Path(args.config))
    run_ingestion(
        api_key=api_key,
        force_refresh=args.force_refresh,
        skip_fred=args.skip_fred,
        skip_yahoo=args.skip_yahoo,
        skip_masters=args.skip_masters,
    )
    print("\nIngestion complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Buffett Indicator CLI (ingestion + modeling)"
    )
    parser.add_argument("--config", default="config.yaml")

    sub = parser.add_subparsers(dest="cmd")

    p_ingest = sub.add_parser("ingest", help="Run ingestion pipeline (default).")
    p_ingest.add_argument("--force-refresh", action="store_true")
    p_ingest.add_argument("--skip-fred", action="store_true")
    p_ingest.add_argument("--skip-yahoo", action="store_true")
    p_ingest.add_argument("--skip-masters", action="store_true")

    p_model = sub.add_parser("model", help="Run transform + modeling pipeline (v4).")
    p_model.add_argument("--bootstrap-n", type=int, default=10_000)

    sub.add_parser("dashboard", help="Rebuild outputs/dashboard.html (Spec v8a).")

    p_bt = sub.add_parser(
        "backtest",
        help="Run tactical MVCI backtest with bootstrap-CI'd Sharpe (Spec v10.0).",
    )
    p_bt.add_argument("--seed", type=int, default=42)
    p_bt.add_argument("--bootstrap-reps", type=int, default=10_000)

    p_diag = sub.add_parser(
        "emit-diagnostics",
        help="Regenerate diagnostics parquets + calibration JSON (Spec v8b.1).",
    )
    p_diag.add_argument(
        "--rebuild-dashboard",
        action="store_true",
        help="Also rebuild dashboard.html after emitting diagnostics.",
    )
    p_diag.add_argument(
        "--full",
        action="store_true",
        help="(Reserved) — full diagnostics pass; currently same as default.",
    )

    # Ingestion flags also accessible at top level for backwards compatibility.
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--skip-fred", action="store_true")
    parser.add_argument("--skip-yahoo", action="store_true")
    parser.add_argument("--skip-masters", action="store_true")

    args = parser.parse_args()

    if args.cmd == "model":
        if not hasattr(args, "bootstrap_n"):
            args.bootstrap_n = 10_000
        return _run_modeling(args)
    if args.cmd == "dashboard":
        return _run_dashboard(args)
    if args.cmd == "emit-diagnostics":
        return _run_emit_diagnostics(args)
    if args.cmd == "backtest":
        return _run_backtest(args)
    # Default: ingestion (handles both `python -m src.cli` and `... ingest`).
    return _run_ingestion(args)


if __name__ == "__main__":
    sys.exit(main())
