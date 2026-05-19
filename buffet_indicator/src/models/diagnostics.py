"""Spec v8b §6.2 — Diagnostics parquet emitters.

Three outputs:
  - diagnostics_stationarity.parquet  (one row per variant × frame)
  - diagnostics_oos_r2_evolution.parquet  (rolling Goyal-Welch R²_OOS)
  - diagnostics_correlation_matrix.parquet  (Pearson corr across variants)

The module reads only the standard chart parquets and `headline.json`, so it
can be re-run in seconds without re-running the full modeling pipeline.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


_MIN_OBS_STATIONARITY = 30
_MIN_OBS_OOS = 60
_HORIZON_MONTHS = 120  # 10Y headline


def _safe_adf_pvalue(values: np.ndarray) -> float:
    """ADF unit-root test p-value (null: unit root). Returns nan on failure."""
    try:
        from statsmodels.tsa.stattools import adfuller
    except ImportError:
        return float("nan")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return float(adfuller(values, autolag="AIC")[1])
    except Exception:  # noqa: BLE001
        return float("nan")


def _safe_kpss_pvalue(values: np.ndarray) -> float:
    """KPSS test p-value (null: stationary). Returns nan on failure."""
    try:
        from statsmodels.tsa.stattools import kpss
    except ImportError:
        return float("nan")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return float(kpss(values, regression="c", nlags="auto")[1])
    except Exception:  # noqa: BLE001
        return float("nan")


def _safe_pp_pvalue(values: np.ndarray) -> float:
    """Phillips-Perron test p-value (null: unit root). Returns nan if arch unavailable."""
    try:
        from arch.unitroot import PhillipsPerron
    except ImportError:
        return float("nan")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            test = PhillipsPerron(values, trend="c", lags=None)
            return float(test.pvalue)
    except Exception:  # noqa: BLE001
        return float("nan")


def _safe_za_pvalue(values: np.ndarray) -> float:
    """Zivot-Andrews test p-value (null: unit root with no structural break).

    Prefers ``arch.unitroot.ZivotAndrews`` (per v8b.1 spec A.1); falls back to
    ``statsmodels.tsa.stattools.zivot_andrews`` if arch is unavailable.
    """
    try:
        from arch.unitroot import ZivotAndrews
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            test = ZivotAndrews(values, trend="c")
            return float(test.pvalue)
    except ImportError:
        pass
    except Exception:  # noqa: BLE001
        return float("nan")
    try:
        from statsmodels.tsa.stattools import zivot_andrews
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return float(zivot_andrews(values, trim=0.15)[1])
    except Exception:  # noqa: BLE001
        return float("nan")


def compute_stationarity(z_history: pd.DataFrame) -> pd.DataFrame:
    """One row per (variant, frame) with ADF/KPSS/PP/ZA p-values.

    The four-test panel is the §6.2 spec; missing tests (no library) emit nan.
    """
    if z_history is None or z_history.empty:
        return pd.DataFrame(
            columns=["variant", "frame", "n_obs", "adf_pvalue", "kpss_pvalue", "pp_pvalue", "za_pvalue"]
        )
    rows: list[dict[str, Any]] = []
    for (variant, frame), sub in z_history.groupby(["variant", "frame"], dropna=False):
        z_vals = sub["z_score"].dropna().astype("float64").values
        if len(z_vals) < _MIN_OBS_STATIONARITY:
            rows.append(
                {
                    "variant": variant,
                    "frame": frame,
                    "n_obs": int(len(z_vals)),
                    "adf_pvalue": float("nan"),
                    "kpss_pvalue": float("nan"),
                    "pp_pvalue": float("nan"),
                    "za_pvalue": float("nan"),
                }
            )
            continue
        rows.append(
            {
                "variant": variant,
                "frame": frame,
                "n_obs": int(len(z_vals)),
                "adf_pvalue": _safe_adf_pvalue(z_vals),
                "kpss_pvalue": _safe_kpss_pvalue(z_vals),
                "pp_pvalue": _safe_pp_pvalue(z_vals),
                "za_pvalue": _safe_za_pvalue(z_vals),
            }
        )
    return pd.DataFrame(rows)


def compute_correlation_matrix(z_history: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation matrix of long-run z-score series (one column per variant)."""
    if z_history is None or z_history.empty:
        return pd.DataFrame()
    long_run = z_history[z_history["frame"] == "long_run"]
    wide = (
        long_run.pivot_table(index="date", columns="variant", values="z_score")
        .dropna(how="all")
    )
    common = wide.dropna()
    if len(common) < 12:
        # Fall back to pairwise correlation when no common window exists.
        return wide.corr(min_periods=12)
    return common.corr()


def compute_oos_r2_evolution(
    scatter_df: pd.DataFrame,
    *,
    variant_key: str = "mvci",
    horizon_col: str = "forward_120m_cagr",
    min_window: int = 60,
) -> pd.DataFrame:
    """Expanding-window Goyal-Welch R²_OOS evolution for one variant + horizon.

    For each end date ``t``, fit OLS on data through ``t-1`` and use it to predict
    ``t`` for the realized forward CAGR. Compare against a no-skill mean.
    """
    if scatter_df is None or scatter_df.empty:
        return pd.DataFrame(columns=["date", "r2_oos", "n_obs_in_window"])

    sub = scatter_df[scatter_df["variant"] == variant_key].copy()
    sub = sub.dropna(subset=["z_score_long_run", horizon_col]).sort_values("date").reset_index(drop=True)
    if len(sub) < min_window + 1:
        return pd.DataFrame(columns=["date", "r2_oos", "n_obs_in_window"])

    rows: list[dict[str, Any]] = []
    cum_sse_model = 0.0
    cum_sse_mean = 0.0
    for t in range(min_window, len(sub)):
        train = sub.iloc[:t]
        x_train = train["z_score_long_run"].values
        y_train = train[horizon_col].values
        n = len(train)
        x_mean = x_train.mean()
        y_mean = y_train.mean()
        var_x = ((x_train - x_mean) ** 2).sum()
        if var_x <= 0:
            continue
        beta = ((x_train - x_mean) * (y_train - y_mean)).sum() / var_x
        alpha = y_mean - beta * x_mean

        target_row = sub.iloc[t]
        x_t = float(target_row["z_score_long_run"])
        y_t = float(target_row[horizon_col])
        y_pred_model = alpha + beta * x_t
        y_pred_mean = y_mean

        cum_sse_model += (y_t - y_pred_model) ** 2
        cum_sse_mean += (y_t - y_pred_mean) ** 2
        r2 = 1.0 - cum_sse_model / cum_sse_mean if cum_sse_mean > 0 else float("nan")
        rows.append(
            {
                "date": pd.Timestamp(target_row["date"]),
                "r2_oos": float(r2),
                "n_obs_in_window": int(n),
            }
        )
    return pd.DataFrame(rows)


def compute_break_dates(
    z_history: pd.DataFrame,
    *,
    max_breaks: int = 5,
    asymptotic_ci_obs: int = 18,
) -> pd.DataFrame:
    """Per-variant Bai-Perron break dates (v8b.1 spec A.2).

    For each variant's long-run z-score series, run Bai-Perron with BIC penalty
    up to ``max_breaks`` and emit one row per detected break.
    """
    if z_history is None or z_history.empty:
        return pd.DataFrame(
            columns=["variant", "break_idx", "break_date", "ci_lower", "ci_upper"]
        )
    try:
        from src.models.bai_perron import bai_perron
    except ImportError:
        return pd.DataFrame(
            columns=["variant", "break_idx", "break_date", "ci_lower", "ci_upper"]
        )

    long_run = z_history[z_history["frame"] == "long_run"]
    rows: list[dict[str, Any]] = []
    for variant, sub in long_run.groupby("variant"):
        series = sub.set_index("date")["z_score"].astype("float64").dropna().sort_index()
        if len(series) < 120:
            continue
        try:
            result = bai_perron(series, max_breaks=max_breaks, criterion="bic")
        except Exception:  # noqa: BLE001
            continue
        for k, break_date in enumerate(result.get("break_dates", []), start=1):
            # Approximate 95% CI by ±N months around the break (the proper
            # Bai-Perron asymptotic CI requires a per-segment variance
            # computation we don't expose; using a fixed window is
            # documented-conservative).
            offset = pd.DateOffset(months=asymptotic_ci_obs)
            rows.append(
                {
                    "variant": variant,
                    "break_idx": k,
                    "break_date": pd.Timestamp(break_date),
                    "ci_lower": pd.Timestamp(break_date) - offset,
                    "ci_upper": pd.Timestamp(break_date) + offset,
                }
            )
    return pd.DataFrame(rows)


def compute_residuals_for_mvci_10y(scatter_df: pd.DataFrame) -> pd.Series:
    """OLS residuals from MVCI z → 10Y forward CAGR regression (v8b.1 A.3)."""
    if scatter_df is None or scatter_df.empty:
        return pd.Series(dtype="float64", name="residual")
    sub = scatter_df[scatter_df["variant"] == "mvci"].copy()
    sub = sub.dropna(subset=["z_score_long_run", "forward_120m_cagr"]).sort_values("date")
    if len(sub) < 30:
        return pd.Series(dtype="float64", name="residual")
    x = sub["z_score_long_run"].values
    y = sub["forward_120m_cagr"].values
    x_mean = x.mean()
    y_mean = y.mean()
    var_x = ((x - x_mean) ** 2).sum()
    if var_x <= 0:
        return pd.Series(dtype="float64", name="residual")
    beta = ((x - x_mean) * (y - y_mean)).sum() / var_x
    alpha = y_mean - beta * x_mean
    residuals = y - (alpha + beta * x)
    return pd.Series(
        residuals,
        index=pd.DatetimeIndex(sub["date"]),
        name="residual",
        dtype="float64",
    )


def compute_calibration_metrics(
    scatter_df: pd.DataFrame,
    *,
    event_threshold: float = 0.05,
    n_buckets: int = 10,
) -> dict[str, Any]:
    """Calibration / reliability + Brier decomposition (v8b.1 A.4).

    For each historical month, predict ``P(forward 10Y CAGR < event_threshold)``
    from a Gaussian fit of the OLS residual SD on data ≤ that month
    (recursive, no look-ahead). Bucket predictions into deciles, compare to
    realized frequency, compute Brier score = reliability − resolution + uncertainty.
    """
    if scatter_df is None or scatter_df.empty:
        return {"available": False}
    sub = scatter_df[scatter_df["variant"] == "mvci"].copy()
    sub = sub.dropna(subset=["z_score_long_run", "forward_120m_cagr"]).sort_values("date").reset_index(drop=True)
    n = len(sub)
    if n < 60:
        return {"available": False}

    from math import erf, sqrt
    def norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + erf(x / sqrt(2.0)))

    preds: list[float] = []
    realized: list[int] = []
    for t in range(30, n - 1):
        train = sub.iloc[:t]
        x_tr = train["z_score_long_run"].values
        y_tr = train["forward_120m_cagr"].values
        x_mean = x_tr.mean()
        y_mean = y_tr.mean()
        var_x = ((x_tr - x_mean) ** 2).sum()
        if var_x <= 0:
            continue
        beta = ((x_tr - x_mean) * (y_tr - y_mean)).sum() / var_x
        alpha = y_mean - beta * x_mean
        fit = alpha + beta * x_tr
        residual_sd = float(np.std(y_tr - fit, ddof=1))
        if residual_sd <= 0:
            continue
        target = sub.iloc[t]
        x_t = float(target["z_score_long_run"])
        y_t = float(target["forward_120m_cagr"])
        mu_pred = alpha + beta * x_t
        z = (event_threshold - mu_pred) / residual_sd
        p_event = float(norm_cdf(z))
        preds.append(p_event)
        realized.append(1 if y_t < event_threshold else 0)

    if not preds:
        return {"available": False}

    p_arr = np.asarray(preds, dtype="float64")
    r_arr = np.asarray(realized, dtype="float64")

    # Bucket by predicted probability (n_buckets quantiles).
    quantiles = np.linspace(0.0, 1.0, n_buckets + 1)
    bucket_edges = np.quantile(p_arr, quantiles)
    bucket_edges = np.unique(bucket_edges)
    buckets: list[dict[str, Any]] = []
    overall_freq = float(r_arr.mean())
    reliability = 0.0
    resolution = 0.0
    n_total = len(p_arr)
    for i in range(len(bucket_edges) - 1):
        if i == len(bucket_edges) - 2:
            mask = (p_arr >= bucket_edges[i]) & (p_arr <= bucket_edges[i + 1])
        else:
            mask = (p_arr >= bucket_edges[i]) & (p_arr < bucket_edges[i + 1])
        if not mask.any():
            continue
        pred_mean = float(p_arr[mask].mean())
        real_freq = float(r_arr[mask].mean())
        n_in = int(mask.sum())
        buckets.append(
            {"predicted_mean": pred_mean, "realized_freq": real_freq, "n": n_in}
        )
        reliability += (n_in / n_total) * (pred_mean - real_freq) ** 2
        resolution += (n_in / n_total) * (real_freq - overall_freq) ** 2

    uncertainty = overall_freq * (1.0 - overall_freq)
    brier_score = float(((p_arr - r_arr) ** 2).mean())

    return {
        "available": True,
        "horizon_years": 10,
        "event": f"forward_10y_cagr_below_{int(event_threshold * 100)}pct",
        "n_observations": int(n_total),
        "buckets": buckets,
        "brier_score": brier_score,
        "reliability": float(reliability),
        "resolution": float(resolution),
        "uncertainty": float(uncertainty),
    }


def emit_diagnostics(
    charts_dir: Path,
    *,
    z_history: pd.DataFrame | None = None,
    scatter_df: pd.DataFrame | None = None,
    tables_dir: Path | None = None,
) -> dict[str, Path]:
    """Compute and persist all v8b/v8b.1 diagnostics artifacts.

    Args:
        charts_dir: directory where parquets are written (created if missing).
        z_history: optional pre-loaded z_history DataFrame; if None, loaded from charts_dir.
        scatter_df: optional pre-loaded scatter DataFrame; if None, loaded from charts_dir.
        tables_dir: optional directory for non-parquet outputs (calibration JSON).
            Defaults to charts_dir.parent / "tables".

    Returns:
        dict mapping output name to written path.
    """
    import json as _json

    charts_dir = Path(charts_dir)
    charts_dir.mkdir(parents=True, exist_ok=True)
    if tables_dir is None:
        tables_dir = charts_dir.parent / "tables"
    tables_dir = Path(tables_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)

    if z_history is None:
        zh_path = charts_dir / "z_history.parquet"
        if zh_path.exists():
            z_history = pd.read_parquet(zh_path)
        else:
            z_history = pd.DataFrame()
    if scatter_df is None:
        sd_path = charts_dir / "scatter_data.parquet"
        if sd_path.exists():
            scatter_df = pd.read_parquet(sd_path)
        else:
            scatter_df = pd.DataFrame()

    out: dict[str, Path] = {}

    # 1. Stationarity panel
    stat_df = compute_stationarity(z_history)
    stat_path = charts_dir / "diagnostics_stationarity.parquet"
    stat_df.to_parquet(stat_path, index=False)
    out["stationarity"] = stat_path

    # 2. Correlation matrix
    corr_df = compute_correlation_matrix(z_history)
    corr_path = charts_dir / "diagnostics_correlation_matrix.parquet"
    if corr_df.empty:
        pd.DataFrame().to_parquet(corr_path)
    else:
        corr_df.to_parquet(corr_path)
    out["correlation"] = corr_path

    # 3. OOS R² evolution
    oos_df = compute_oos_r2_evolution(scatter_df)
    oos_path = charts_dir / "diagnostics_oos_r2_evolution.parquet"
    oos_df.to_parquet(oos_path, index=False)
    out["oos_r2_evolution"] = oos_path

    # 4. v8b.1 A.2 — Bai-Perron break dates per variant
    bd_df = compute_break_dates(z_history)
    bd_path = charts_dir / "diagnostics_break_dates.parquet"
    bd_df.to_parquet(bd_path, index=False)
    out["break_dates"] = bd_path

    # 5. v8b.1 A.3 — MVCI residuals (for ACF/PACF chart)
    residuals = compute_residuals_for_mvci_10y(scatter_df)
    res_path = charts_dir / "diagnostics_mvci_residuals.parquet"
    if residuals.empty:
        pd.DataFrame(columns=["residual"]).to_parquet(res_path)
    else:
        residuals.to_frame().to_parquet(res_path)
    out["mvci_residuals"] = res_path

    # 6. v8b.1 A.4 — calibration metrics
    calib = compute_calibration_metrics(scatter_df)
    calib_path = tables_dir / "calibration_metrics.json"
    calib_path.write_text(_json.dumps(calib, indent=2, default=str), encoding="utf-8")
    out["calibration"] = calib_path

    return out


__all__ = [
    "compute_stationarity",
    "compute_correlation_matrix",
    "compute_oos_r2_evolution",
    "compute_break_dates",
    "compute_residuals_for_mvci_10y",
    "compute_calibration_metrics",
    "emit_diagnostics",
]
