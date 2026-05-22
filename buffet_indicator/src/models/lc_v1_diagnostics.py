"""LC v1.0 diagnostics layer (Session 8 §2.H).

Implements per master spec §3.3 (stationarity) + §3.6 (multicollinearity) +
§3.1 (structural breaks):

* **Stationarity tests**: ADF + KPSS + Phillips-Perron + Zivot-Andrews on each
  of the 5 components (z₁..z₅) + 3 composites (LC_FULL/TIER2/DEEP).
* **Multicollinearity**: VIF + 5×5 cross-correlation matrix + eigenvalue
  spectrum on the contemporaneous component panel.
* **Structural breaks**: Bai-Perron (1998, 2003) on each composite as a
  univariate series, max 5 breaks, BIC selection.

Reference list
--------------
* Dickey, D.A. & Fuller, W.A. (1979), JASA 74(366) — ADF.
* Kwiatkowski, D., Phillips, P.C.B., Schmidt, P., & Shin, Y. (1992),
  J. Econometrics 54 — KPSS.
* Phillips, P.C.B. & Perron, P. (1988), Biometrika 75(2) — PP.
* Zivot, E. & Andrews, D.W.K. (1992), JBES 10(3) — ZA (endogenous break).
* Bai, J. & Perron, P. (1998, 2003), Econometrica + J. Applied Econometrics.
* specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §3.3-§3.7.
* prompt/052226/PROMPT_v11_3_session_8_H_I_J_closeout.md §2.H.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.stats.outliers_influence import (  # type: ignore[import-untyped]
    variance_inflation_factor,
)
from statsmodels.tsa.stattools import adfuller, kpss  # type: ignore[import-untyped]


#: VIF threshold per master spec §3.6 — values above this flag multicollinearity.
VIF_THRESHOLD = 5.0


@dataclass
class StationarityResult:
    """Per-series stationarity test results."""
    series_name: str
    n_obs: int
    adf_stat: float
    adf_pvalue: float
    adf_lags: int
    kpss_stat: float
    kpss_pvalue: float
    kpss_lags: int
    pp_stat: float
    pp_pvalue: float
    za_stat: float
    za_pvalue: float
    za_break_date: str
    conclusion: str  # 'stationary', 'non_stationary', 'conflicting'


def _safe_adf(series: pd.Series) -> tuple[float, float, int]:
    """ADF test with conservative settings (AIC lag selection, constant only)."""
    s = series.dropna().astype("float64")
    if len(s) < 12:
        return float("nan"), float("nan"), 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = adfuller(s.values, autolag="AIC", regression="c")
    return float(result[0]), float(result[1]), int(result[2])


def _safe_kpss(series: pd.Series) -> tuple[float, float, int]:
    """KPSS test (regression='c', lags='auto')."""
    s = series.dropna().astype("float64")
    if len(s) < 12:
        return float("nan"), float("nan"), 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = kpss(s.values, regression="c", nlags="auto")
    return float(result[0]), float(result[1]), int(result[2])


def _safe_pp(series: pd.Series) -> tuple[float, float]:
    """Phillips-Perron via arch.unitroot."""
    from arch.unitroot import PhillipsPerron
    s = series.dropna().astype("float64")
    if len(s) < 12:
        return float("nan"), float("nan")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pp = PhillipsPerron(np.asarray(s.values, dtype=float), trend="c")
            return float(pp.stat), float(pp.pvalue)
    except Exception:
        return float("nan"), float("nan")


def _safe_za(series: pd.Series) -> tuple[float, float, str]:
    """Zivot-Andrews via arch.unitroot. Returns (stat, pvalue, break_date).

    Note: ``arch.unitroot.ZivotAndrews`` (as of v8.x) does NOT expose the
    estimated break period as a public attribute. The break date is therefore
    returned as an empty string in this implementation; consumers should
    treat ``za_break_date`` as informational-only. Stat + p-value remain the
    canonical decision inputs.
    """
    from arch.unitroot import ZivotAndrews
    s = series.dropna().astype("float64")
    if len(s) < 30:
        return float("nan"), float("nan"), ""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            za = ZivotAndrews(np.asarray(s.values, dtype=float), trend="c")
            return float(za.stat), float(za.pvalue), ""
    except Exception:
        return float("nan"), float("nan"), ""


def run_stationarity_tests(
    series: pd.Series,
    series_name: str,
) -> StationarityResult:
    """Run ADF + KPSS + PP + ZA on ``series`` and return the combined result.

    Conclusion mapping (master spec §3.3):

    * ``stationary``      — ADF rejects null AND KPSS does not reject null.
    * ``non_stationary``  — ADF does not reject AND KPSS rejects.
    * ``conflicting``     — any other combination; default to the more
      conservative interpretation (non-stationary) per master spec §3.3.
    """
    adf_stat, adf_p, adf_lags = _safe_adf(series)
    kpss_stat, kpss_p, kpss_lags = _safe_kpss(series)
    pp_stat, pp_p = _safe_pp(series)
    za_stat, za_p, za_break = _safe_za(series)

    # Conclusion logic.
    if np.isnan(adf_p) or np.isnan(kpss_p):
        conclusion = "conflicting"
    else:
        adf_rejects = adf_p < 0.05  # rejects unit-root null → stationary
        kpss_rejects = kpss_p < 0.05  # rejects stationarity null → non-stationary
        if adf_rejects and not kpss_rejects:
            conclusion = "stationary"
        elif not adf_rejects and kpss_rejects:
            conclusion = "non_stationary"
        else:
            conclusion = "conflicting"

    return StationarityResult(
        series_name=series_name,
        n_obs=int(series.dropna().shape[0]),
        adf_stat=adf_stat, adf_pvalue=adf_p, adf_lags=adf_lags,
        kpss_stat=kpss_stat, kpss_pvalue=kpss_p, kpss_lags=kpss_lags,
        pp_stat=pp_stat, pp_pvalue=pp_p,
        za_stat=za_stat, za_pvalue=za_p, za_break_date=za_break,
        conclusion=conclusion,
    )


# ---------------------------------------------------------------------------
# Multicollinearity: VIF + correlation matrix + eigenvalue spectrum
# ---------------------------------------------------------------------------


@dataclass
class MulticollinearityResult:
    """5-component multicollinearity diagnostics."""
    component_names: list[str]
    vif: dict[str, float]
    correlation_matrix: pd.DataFrame
    eigenvalues: np.ndarray
    eigenvalue_proportions: np.ndarray
    eigenvalue_cumulative: np.ndarray
    multicollinearity_flags: dict[str, bool]
    n_obs_aligned: int


def compute_vif_matrix(
    components: dict[str, pd.Series],
    *,
    vif_threshold: float = VIF_THRESHOLD,
) -> MulticollinearityResult:
    """Compute VIF + correlation matrix + eigenvalue spectrum on the
    contemporaneous component panel.

    Inputs are aligned on the intersection of monthly indices (dropna across
    all 5 columns simultaneously).
    """
    df = pd.concat(
        [s.rename(name) for name, s in components.items()],
        axis=1, join="outer",
    ).dropna()
    names = list(components.keys())
    if df.empty or len(df) < 10:
        empty_vif = {n: float("nan") for n in names}
        return MulticollinearityResult(
            component_names=names,
            vif=empty_vif,
            correlation_matrix=pd.DataFrame(
                np.full((len(names), len(names)), np.nan),
                index=names, columns=names,
            ),
            eigenvalues=np.full(len(names), np.nan),
            eigenvalue_proportions=np.full(len(names), np.nan),
            eigenvalue_cumulative=np.full(len(names), np.nan),
            multicollinearity_flags={n: False for n in names},
            n_obs_aligned=int(len(df)),
        )

    X = df[names].to_numpy(dtype="float64")
    vif: dict[str, float] = {}
    for i, name in enumerate(names):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                vif[name] = float(variance_inflation_factor(X, i))
        except Exception:
            vif[name] = float("nan")

    corr = df[names].corr()

    cov_centered = np.cov(X, rowvar=False, ddof=1)
    eigvals = np.linalg.eigvalsh(cov_centered)
    eigvals = np.sort(eigvals)[::-1]
    total_var = float(eigvals.sum())
    if total_var > 0 and np.isfinite(total_var):
        props = eigvals / total_var
    else:
        props = np.full_like(eigvals, np.nan)
    cum = np.cumsum(props)

    flags = {
        n: (np.isfinite(vif[n]) and vif[n] > vif_threshold) for n in names
    }
    return MulticollinearityResult(
        component_names=names,
        vif=vif,
        correlation_matrix=corr,
        eigenvalues=eigvals,
        eigenvalue_proportions=props,
        eigenvalue_cumulative=cum,
        multicollinearity_flags=flags,
        n_obs_aligned=int(len(df)),
    )


# ---------------------------------------------------------------------------
# Bai-Perron structural breaks
# ---------------------------------------------------------------------------


@dataclass
class BaiPerronCellResult:
    series_name: str
    n_breaks_detected: int
    breaks: list[dict[str, Any]]  # one dict per break with index, date, ci, regime means


def run_bai_perron_breaks(
    series: pd.Series,
    series_name: str,
    *,
    max_breaks: int = 5,
    min_segment_size: int = 30,
) -> BaiPerronCellResult:
    """Bai-Perron (1998, 2003) multiple-break test on a univariate series.

    Wraps :func:`src.models.bai_perron.bai_perron` (Session 5 pure-NumPy impl).
    """
    from src.models.bai_perron import bai_perron

    s = series.dropna().astype("float64")
    if len(s) < max(60, 2 * min_segment_size):
        return BaiPerronCellResult(
            series_name=series_name, n_breaks_detected=0, breaks=[],
        )

    result = bai_perron(
        s, max_breaks=max_breaks, min_segment_size=min_segment_size,
        criterion="bic",
    )
    breaks_out: list[dict[str, Any]] = []
    break_indices = result.get("break_indices", []) or []
    segment_means = result.get("segment_means", []) or []
    for k, idx in enumerate(break_indices):
        if 0 <= idx < len(s):
            break_date = str(pd.Timestamp(s.index[idx]).date())
        else:
            break_date = ""
        regime_pre = (
            float(segment_means[k]) if k < len(segment_means) else float("nan")
        )
        regime_post = (
            float(segment_means[k + 1])
            if k + 1 < len(segment_means) else float("nan")
        )
        breaks_out.append({
            "break_index": int(idx),
            "break_date": break_date,
            "regime_pre_mean": regime_pre,
            "regime_post_mean": regime_post,
        })
    return BaiPerronCellResult(
        series_name=series_name,
        n_breaks_detected=len(breaks_out),
        breaks=breaks_out,
    )


__all__ = [
    "VIF_THRESHOLD",
    "StationarityResult",
    "MulticollinearityResult",
    "BaiPerronCellResult",
    "run_stationarity_tests",
    "compute_vif_matrix",
    "run_bai_perron_breaks",
]
