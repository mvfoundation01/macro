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

    statsmodels exposes a one-step ZA test as ``zivot_andrews``. We fall back
    to nan if the version doesn't include it or the test fails to converge.
    """
    try:
        from statsmodels.tsa.stattools import zivot_andrews
    except ImportError:
        return float("nan")
    try:
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


def emit_diagnostics(
    charts_dir: Path,
    *,
    z_history: pd.DataFrame | None = None,
    scatter_df: pd.DataFrame | None = None,
) -> dict[str, Path]:
    """Compute and persist all 3 diagnostics parquets.

    Args:
        charts_dir: directory where parquets are written (created if missing).
        z_history: optional pre-loaded z_history DataFrame; if None, loaded from charts_dir.
        scatter_df: optional pre-loaded scatter DataFrame; if None, loaded from charts_dir.

    Returns:
        dict mapping output name to written path.
    """
    charts_dir = Path(charts_dir)
    charts_dir.mkdir(parents=True, exist_ok=True)

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

    stat_df = compute_stationarity(z_history)
    stat_path = charts_dir / "diagnostics_stationarity.parquet"
    stat_df.to_parquet(stat_path, index=False)
    out["stationarity"] = stat_path

    corr_df = compute_correlation_matrix(z_history)
    corr_path = charts_dir / "diagnostics_correlation_matrix.parquet"
    if corr_df.empty:
        # write empty placeholder (consumers should check)
        pd.DataFrame().to_parquet(corr_path)
    else:
        corr_df.to_parquet(corr_path)
    out["correlation"] = corr_path

    oos_df = compute_oos_r2_evolution(scatter_df)
    oos_path = charts_dir / "diagnostics_oos_r2_evolution.parquet"
    oos_df.to_parquet(oos_path, index=False)
    out["oos_r2_evolution"] = oos_path

    return out


__all__ = [
    "compute_stationarity",
    "compute_correlation_matrix",
    "compute_oos_r2_evolution",
    "emit_diagnostics",
]
