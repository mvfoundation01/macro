"""LC v1.0 calibration driver (Session 7 §2.G).

For each (scope × horizon) cell:
* Compute Gaussian-approximation forecasts from the predictive regression
  (mean = α̂ + β̂·LC_t; SD = std of residuals on the in-sample window).
* Evaluate CRPS, log score, and PIT against realized forward returns on the
  validation window per pre-reg §3.8.
* Compute Brier + Murphy decomposition for the binary tail event
  ``p_neg_total_return`` using the regression-implied probability vs realized
  0/1 outcomes.

Writes:
* ``outputs/tables/lc_v1_calibration.csv`` — one row per cell.
* ``outputs/figures/lc_v1_reliability_diagram_<scope>_<horizon>y.png`` — 3
  headline figures (LC_FULL 10Y, LC_TIER2 10Y, LC_DEEP 5Y).
* ``outputs/figures/lc_v1_pit_histogram_<scope>_<horizon>y.png`` — 3 figures.

References
----------
* prompt/052226/PROMPT_v11_3_session_7_DECISIONS_investigation_F_G.md §2.G
* specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §3.8 (backtest split)
"""
from __future__ import annotations

# --- sys.path bootstrap (must precede any src.* imports) ---
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# -----------------------------------------------------------

import argparse
import logging

import numpy as np
import pandas as pd
from scipy.stats import norm

from src.models.lc_v1_calibration import (
    compute_brier_decomposition,
    compute_crps,
    compute_log_score,
    compute_pit,
    render_pit_histogram,
    render_reliability_diagram,
)
from src.models.lc_v1_regression import _forward_log_return, _load_spx_total_return

logger = logging.getLogger(__name__)

#: Per pre-reg §3.8 backtest split.
VALIDATION_SPLITS: dict[str, pd.Timestamp] = {
    "LC_FULL": pd.Timestamp("2019-01-01"),
    "LC_TIER2": pd.Timestamp("2011-01-01"),
    "LC_DEEP": pd.Timestamp("2011-01-01"),
}

ESTIMATION_SPLITS: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {
    "LC_FULL": (pd.Timestamp("2013-01-01"), pd.Timestamp("2018-12-31")),
    "LC_TIER2": (pd.Timestamp("1986-01-01"), pd.Timestamp("2010-12-31")),
    "LC_DEEP": (pd.Timestamp("1986-01-01"), pd.Timestamp("2010-12-31")),
}

#: Headline cells for which we generate reliability + PIT figures.
HEADLINE_CELLS: tuple[tuple[str, int], ...] = (
    ("LC_FULL", 10),
    ("LC_TIER2", 10),
    ("LC_DEEP", 5),
)


def _fit_gaussian_forecast(
    lc: pd.Series,
    spx_tr: pd.Series,
    horizon_years: int,
    *,
    est_start: pd.Timestamp,
    est_end: pd.Timestamp,
) -> tuple[float, float, float] | None:
    """Fit OLS β̂, α̂, σ̂_res on the estimation window."""
    fwd = _forward_log_return(spx_tr, horizon_years)
    aligned = pd.concat([lc.rename("lc"), fwd.rename("y")], axis=1).dropna()
    est_mask = (aligned.index >= est_start) & (aligned.index <= est_end)
    est = aligned.loc[est_mask]
    if len(est) < 5:
        return None
    x = est["lc"].to_numpy()
    y = est["y"].to_numpy()
    A = np.column_stack([np.ones(len(x)), x])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    alpha = float(coef[0])
    beta = float(coef[1])
    resid = y - (alpha + beta * x)
    sigma = float(np.std(resid, ddof=2))
    if not np.isfinite(sigma) or sigma <= 0:
        return None
    return alpha, beta, sigma


def _evaluate_cell(
    scope_name: str,
    horizon_years: int,
    lc: pd.Series,
    spx_tr: pd.Series,
) -> dict[str, object]:
    """Compute calibration metrics for one (scope × horizon) cell."""
    est_start, est_end = ESTIMATION_SPLITS[scope_name]
    val_start = VALIDATION_SPLITS[scope_name]

    fit = _fit_gaussian_forecast(
        lc, spx_tr, horizon_years, est_start=est_start, est_end=est_end,
    )
    fwd = _forward_log_return(spx_tr, horizon_years)
    aligned = pd.concat([lc.rename("lc"), fwd.rename("y")], axis=1).dropna()
    val_mask = aligned.index >= val_start
    val = aligned.loc[val_mask]

    row: dict[str, object] = {
        "scope": scope_name,
        "horizon_years": horizon_years,
        "est_start": str(est_start.date()),
        "est_end": str(est_end.date()),
        "val_start": str(val_start.date()),
        "n_validation": int(len(val)),
    }

    if fit is None or val.empty:
        for k in (
            "brier_score", "reliability", "resolution", "uncertainty",
            "crps_model", "crps_benchmark", "crps_skill",
            "log_score_model", "log_score_benchmark",
            "pit_ks_pvalue", "pit_ks_statistic",
        ):
            row[k] = float("nan")
        return row

    alpha, beta, sigma = fit
    mu_val = alpha + beta * val["lc"].to_numpy()
    sd_val = np.full(len(val), sigma)
    y_val = val["y"].to_numpy()

    row["alpha"] = alpha
    row["beta"] = beta
    row["sigma_resid"] = sigma

    # CRPS — model vs prevailing-mean benchmark.
    crps_model = compute_crps(mu_val, sd_val, y_val)
    # Benchmark: prevailing mean μ̂ from estimation window + σ̂.
    est = aligned.loc[(aligned.index >= est_start) & (aligned.index <= est_end)]
    mu_bench = float(est["y"].mean())
    sd_bench = float(est["y"].std(ddof=2))
    if sd_bench <= 0 or not np.isfinite(sd_bench):
        sd_bench = sigma
    crps_benchmark = compute_crps(
        np.full(len(val), mu_bench), np.full(len(val), sd_bench), y_val,
    )
    crps_skill = (
        1.0 - crps_model / crps_benchmark
        if crps_benchmark > 0 and np.isfinite(crps_benchmark) else float("nan")
    )
    row["crps_model"] = crps_model
    row["crps_benchmark"] = crps_benchmark
    row["crps_skill"] = crps_skill

    # Log score — model vs benchmark.
    log_model = compute_log_score(mu_val, sd_val, y_val)
    log_benchmark = compute_log_score(
        np.full(len(val), mu_bench), np.full(len(val), sd_bench), y_val,
    )
    row["log_score_model"] = log_model
    row["log_score_benchmark"] = log_benchmark

    # PIT — under Gaussian forecast.
    pit_result = compute_pit(mu_val, sd_val, y_val, n_bins=10)
    row["pit_ks_pvalue"] = pit_result.ks_pvalue
    row["pit_ks_statistic"] = pit_result.ks_statistic

    # Brier + Murphy for binary tail event: forward CAGR < 0 (negative total return).
    # Forecast probability: P(y < 0 | mean, sd) = Φ((0 − mu)/sd).
    forecast_probs = norm.cdf(-mu_val / sd_val)
    realized_outcomes = (y_val < 0.0).astype(float)
    brier = compute_brier_decomposition(forecast_probs, realized_outcomes, n_bins=10)
    row["brier_score"] = brier.brier_score
    row["reliability"] = brier.reliability
    row["resolution"] = brier.resolution
    row["uncertainty"] = brier.uncertainty

    # Generate figures for headline cells.
    if (scope_name, horizon_years) in HEADLINE_CELLS:
        fig_dir = _PROJECT_ROOT / "outputs" / "figures"
        fig_dir.mkdir(parents=True, exist_ok=True)

        rel_fig = render_reliability_diagram(
            brier,
            title=f"{scope_name} {horizon_years}Y — P(neg total return) calibration",
        )
        rel_path = fig_dir / f"lc_v1_reliability_diagram_{scope_name}_{horizon_years}y.png"
        rel_fig.savefig(rel_path, dpi=120, bbox_inches="tight")
        import matplotlib.pyplot as plt

        plt.close(rel_fig)
        logger.info("Wrote %s", rel_path)

        pit_fig = render_pit_histogram(
            pit_result,
            title=f"{scope_name} {horizon_years}Y forward-return PIT",
        )
        pit_path = fig_dir / f"lc_v1_pit_histogram_{scope_name}_{horizon_years}y.png"
        pit_fig.savefig(pit_path, dpi=120, bbox_inches="tight")
        plt.close(pit_fig)
        logger.info("Wrote %s", pit_path)

    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    composites_path = _PROJECT_ROOT / "outputs" / "lc_v1_composites.parquet"
    if not composites_path.exists():
        logger.error("Missing composites parquet: %s", composites_path)
        return 1
    composites = pd.read_parquet(composites_path)

    logger.info("Loading SPX total-return monthly...")
    spx_tr = _load_spx_total_return()

    horizons = (1, 3, 5, 10)
    rows: list[dict[str, object]] = []
    for scope in ("LC_FULL", "LC_TIER2", "LC_DEEP"):
        lc = composites[scope].dropna()
        for h in horizons:
            row = _evaluate_cell(scope, h, lc, spx_tr)
            rows.append(row)

    df = pd.DataFrame(rows)
    out_csv = _PROJECT_ROOT / "outputs" / "tables" / "lc_v1_calibration.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

    print("\n" + "=" * 80)
    print("LC v1.0 CALIBRATION  -  12 CELLS")
    print("=" * 80)
    with pd.option_context("display.float_format", lambda x: f"{x:.4f}",
                           "display.max_columns", 30):
        cols_to_show = [
            "scope", "horizon_years", "n_validation",
            "brier_score", "reliability", "resolution", "uncertainty",
            "crps_skill", "pit_ks_pvalue",
        ]
        print(df[cols_to_show].to_string(index=False))
    print("=" * 80)
    print(f"Wrote {out_csv}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
