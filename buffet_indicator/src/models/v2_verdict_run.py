"""Phase E.2 / E.3 / E.4 — v2.0 verdict-bearing run composition layer.

Composes Phase D §11.1 functions over the Phase E.1 panel to produce the
per-cell regression / skew-t / bootstrap results and the criteria-input
panel for ``evaluate_v2_criteria``.

References
----------
- Phase E prompt §3 (regression sweep), §4 (C5/C6/C7 diagnostics).
- Phase D §11.1 functions: run_predictive_regression_v2,
  fit_conditional_skew_t, stationary_bootstrap_ci, evaluate_v2_criteria.
- Sealed pre-reg §3-§5 + §10.1 + §11.1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import hashlib
import numpy as np
import pandas as pd

import arch.bootstrap
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant
from statsmodels.tsa.stattools import adfuller

from src.models.predictive_regression_v2 import (
    RegressionResult,
    run_predictive_regression_v2,
)
from src.models.v2_panel_builder import (
    HORIZONS_MONTHS,
    PanelCell,
    V2Panel,
    build_v2_panel,
)
from src.stats.bootstrap import choose_stationary_block_length
from src.stats.bootstrap_policy import VERDICT_N_BOOTSTRAP
from src.stats.hac import compute_hac_lag
from src.stats.sample_gate import sample_gate_status
from src.stats.skewt import SkewTFitResult, fit_conditional_skew_t


C7_HORIZONS_MONTHS: tuple[int, ...] = (12, 36, 60, 120)
"""Sealed §5.3: 5 components × 4 horizons = 20 (component × horizon) cells for C7."""


# ---------------------------------------------------------------------------
# E.2 — regression sweep
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SweepResult:
    """Per-cell regression + skewed-t + bootstrap composite."""

    cell_key: tuple[str, int]  # (scope, horizon_years)
    regression: RegressionResult
    skewt: Optional[SkewTFitResult]
    bootstrap_beta_ci_lower: Optional[float]
    bootstrap_beta_ci_upper: Optional[float]
    bootstrap_block_length: Optional[int]
    bootstrap_seed_hex: Optional[str]
    bootstrap_n_used: Optional[int]


def _seed_hex(seed: int) -> str:
    ss = np.random.SeedSequence(int(seed))
    state = ss.generate_state(4, dtype=np.uint32)
    return hashlib.sha256(state.tobytes()).hexdigest()[:16]


def _bootstrap_regression_beta(
    x: np.ndarray,
    y: np.ndarray,
    *,
    n_bootstrap: int,
    seed: int,
    confidence_level: float = 0.95,
) -> tuple[Optional[float], Optional[float], int, str]:
    """Stationary block bootstrap on OLS β given paired (x, y) in-sample data.

    Returns ``(ci_lower, ci_upper, block_length, seed_hex)``. CIs are NaN /
    None if the bootstrap is not evaluable (n < 30 or block_length > n//2).
    """
    n = x.size
    seed_hex = _seed_hex(seed)
    if n != y.size or n < 30:
        return None, None, 0, seed_hex

    paired = np.column_stack([x, y])
    block_length = choose_stationary_block_length(y)
    if block_length > max(1, n // 2):
        return None, None, int(block_length), seed_hex

    ss = np.random.SeedSequence(int(seed))
    rng = np.random.default_rng(ss)
    bs = arch.bootstrap.StationaryBootstrap(int(block_length), paired, seed=rng)

    betas = np.full(int(n_bootstrap), np.nan, dtype="float64")
    for i, (resampled, _) in enumerate(bs.bootstrap(int(n_bootstrap))):
        block = resampled[0]  # shape (n, 2)
        x_b = block[:, 0]
        y_b = block[:, 1]
        xm = x_b.mean()
        denom = float(np.sum((x_b - xm) ** 2))
        if denom <= 0.0 or not math.isfinite(denom):
            continue
        betas[i] = float(np.sum((x_b - xm) * (y_b - y_b.mean())) / denom)

    finite = betas[np.isfinite(betas)]
    if finite.size == 0:
        return None, None, int(block_length), seed_hex
    alpha = 1.0 - confidence_level
    lo = float(np.percentile(finite, 100.0 * alpha / 2.0))
    hi = float(np.percentile(finite, 100.0 * (1.0 - alpha / 2.0)))
    return lo, hi, int(block_length), seed_hex


def _seed_for_cell(scope: str, horizon_years: int, master_seed: int = 42) -> int:
    """Deterministic per-cell seed derived from a master seed + cell key.

    Per sealed §3.8: deterministic via SeedSequence; child seeds derived
    via SHA-256 of the cell key.
    """
    key = f"{scope}|{horizon_years}|master={master_seed}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, "big") & 0x7FFFFFFFFFFFFFFF  # positive int64


def run_regression_sweep(
    panel: V2Panel,
    *,
    n_bootstrap: int = VERDICT_N_BOOTSTRAP,
    fit_skewt: bool = True,
    bootstrap_beta: bool = True,
    master_seed: int = 42,
) -> dict[tuple[str, int], SweepResult]:
    """Apply run_predictive_regression_v2 + skewed-t + bootstrap per cell.

    Parameters
    ----------
    panel : V2Panel
        Output of :func:`build_v2_panel`.
    n_bootstrap : int, default 50_000
        Bootstrap reps per cell (sealed §3.8 IMMUTABLE for verdict).
    fit_skewt : bool, default True
        If True, fit conditional skewed-t on in-sample residuals per cell.
    bootstrap_beta : bool, default True
        If True, run stationary bootstrap CI on β per cell.
    master_seed : int, default 42
        Master seed; per-cell seeds derived via SHA-256(cell_key).

    Returns
    -------
    dict[(scope, horizon_years) -> SweepResult]
    """
    out: dict[tuple[str, int], SweepResult] = {}
    for key, cell in panel.cells.items():
        scope, horizon_years = key
        # Always run the regression (it handles too-few-rows internally).
        reg = run_predictive_regression_v2(
            cell.composite_series,
            cell.forward_return_series,
            horizon_months=cell.horizon_months,
            forecast_origin=cell.oos_split_date,
        )
        # Skewed-t on in-sample residuals (Phase D function handles fallbacks).
        skewt: Optional[SkewTFitResult] = None
        if fit_skewt and reg.residuals is not None:
            try:
                resid = np.asarray(reg.residuals, dtype="float64").ravel()
                if resid.size > 0:
                    skewt = fit_conditional_skew_t(
                        resid, seed=_seed_for_cell(scope, horizon_years, master_seed)
                    )
            except Exception:
                skewt = None

        # Stationary block bootstrap on β.
        bs_lo: Optional[float] = None
        bs_hi: Optional[float] = None
        bs_bl: Optional[int] = None
        bs_seed_hex: Optional[str] = None
        bs_n_used: Optional[int] = None
        if bootstrap_beta and cell.n_obs_insample >= 30:
            cell_seed = _seed_for_cell(scope, horizon_years, master_seed)
            x_arr = (
                cell.composite_series.loc[cell.composite_series.index <= cell.oos_split_date]
                .to_numpy(dtype="float64")
            )
            y_arr = (
                cell.forward_return_series.loc[
                    cell.forward_return_series.index <= cell.oos_split_date
                ].to_numpy(dtype="float64")
            )
            common_n = min(x_arr.size, y_arr.size)
            x_arr = x_arr[:common_n]
            y_arr = y_arr[:common_n]
            bs_lo, bs_hi, bs_bl, bs_seed_hex = _bootstrap_regression_beta(
                x_arr, y_arr, n_bootstrap=int(n_bootstrap), seed=cell_seed
            )
            bs_n_used = int(n_bootstrap)

        out[key] = SweepResult(
            cell_key=key,
            regression=reg,
            skewt=skewt,
            bootstrap_beta_ci_lower=bs_lo,
            bootstrap_beta_ci_upper=bs_hi,
            bootstrap_block_length=bs_bl,
            bootstrap_seed_hex=bs_seed_hex,
            bootstrap_n_used=bs_n_used,
        )
    return out


# ---------------------------------------------------------------------------
# E.3 — C5/C6/C7 diagnostics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ADFResult:
    component_id: str
    adf_stat: Optional[float]
    p_value: Optional[float]
    n_lags_used: Optional[int]
    n_obs: Optional[int]


def run_adf_per_component(panel: V2Panel) -> dict[str, ADFResult]:
    """ADF test per component on raw post-splice / pre-z-score series (§5 / §5.2).

    Uses ``autolag='AIC'`` and ``regression='c'`` (constant only) per the
    classical Goyal-Welch / Campbell convention; sealed §5.2 specifies
    Holm-Šidák multiplicity correction in :mod:`src.models.v2_criteria`
    but does not pin specific ADF kwargs — defaults are standard.
    """
    out: dict[str, ADFResult] = {}

    # z1 NetFed (level)
    components_to_test: list[tuple[str, str]] = [
        ("z1", "netfed_level"),
        ("z2", "m2_yoy"),
        ("z3", "banklend_yoy"),
        ("z4", "log_dxy"),
        ("z5", "funding_spread_or_blend"),
    ]
    raw_series: dict[str, pd.Series] = {}
    # Reconstruct raw series at the same monthly EOM frequency used in z-scoring.
    from src.models.v2_panel_builder import (
        RRPONTSYD_DENSE_FROM,
        _resample_monthly_eom,
    )
    from src.ingest.master_archive import load_master

    walcl_m = _resample_monthly_eom(load_master("walcl").data.astype("float64").dropna())
    wdtgal_m = _resample_monthly_eom(load_master("wdtgal").data.astype("float64").dropna())
    rrp_m = _resample_monthly_eom(load_master("rrpontsyd").data.astype("float64").dropna())
    union_idx = walcl_m.index.union(wdtgal_m.index).union(rrp_m.index)
    rrp_m = rrp_m.reindex(union_idx)
    pre_2013 = union_idx < RRPONTSYD_DENSE_FROM
    rrp_m.loc[pre_2013] = rrp_m.loc[pre_2013].fillna(0.0)
    idx = walcl_m.index.intersection(wdtgal_m.index).intersection(rrp_m.index)
    raw_series["z1"] = (walcl_m.loc[idx] - wdtgal_m.loc[idx] - rrp_m.loc[idx]).dropna()

    m2_m = _resample_monthly_eom(load_master("m2_sl").data.astype("float64").dropna())
    raw_series["z2"] = m2_m.pct_change(periods=12).dropna()

    from src.transform.splice import _splice_busloans_totll_yoy_impl
    bus_m = _resample_monthly_eom(load_master("busloans").data.astype("float64").dropna())
    tot_m = _resample_monthly_eom(load_master("totll").data.astype("float64").dropna())
    bus_yoy = bus_m.pct_change(periods=12)
    tot_yoy = tot_m.pct_change(periods=12)
    spliced, _ = _splice_busloans_totll_yoy_impl(
        bus_yoy, tot_yoy, pd.Timestamp("1973-01-03"), overlap_months=36
    )
    raw_series["z3"] = spliced.dropna()

    dxy_m = _resample_monthly_eom(load_master("dtwexbgs").data.astype("float64").dropna())
    raw_series["z4"] = np.log(dxy_m).dropna()

    # z5: use the funding-z series from the panel (already PIT-z-blended).
    raw_series["z5"] = panel.components.z5.dropna() if panel.components.z5 is not None else pd.Series(dtype="float64")

    for cid, _label in components_to_test:
        s = raw_series.get(cid, pd.Series(dtype="float64"))
        if s.empty or s.size < 20:
            out[cid] = ADFResult(
                component_id=cid, adf_stat=None, p_value=None,
                n_lags_used=None, n_obs=int(s.size) if s.size else None,
            )
            continue
        try:
            adf_stat, p_value, n_lags, n_obs, _crit, _icb = adfuller(
                s.values, autolag="AIC", regression="c",
            )
            out[cid] = ADFResult(
                component_id=cid,
                adf_stat=float(adf_stat),
                p_value=float(p_value),
                n_lags_used=int(n_lags),
                n_obs=int(n_obs),
            )
        except (ValueError, np.linalg.LinAlgError) as exc:
            out[cid] = ADFResult(
                component_id=cid, adf_stat=None, p_value=None,
                n_lags_used=None, n_obs=int(s.size),
            )
    return out


def run_vif(panel: V2Panel) -> dict[str, Optional[float]]:
    """VIF per component on the LC_FULL aligned 5-component z-score panel (§5).

    Returns ``{"z1": float | None, ..., "z5": float | None, "max_vif": float | None}``.
    Computation uses the common-dates intersection of all 5 z-scored components.
    """
    comp = panel.components
    pieces = {
        "z1": comp.z1, "z2": comp.z2, "z3": comp.z3, "z4": comp.z4, "z5": comp.z5,
    }
    aligned = pd.concat(
        {k: v for k, v in pieces.items() if v is not None}, axis=1, join="inner"
    ).dropna()
    out: dict[str, Optional[float]] = {k: None for k in pieces}
    out["max_vif"] = None
    if aligned.shape[0] < 10 or aligned.shape[1] < 2:
        return out
    X = add_constant(aligned.to_numpy(dtype="float64"))
    vifs: dict[str, float] = {}
    for i, col in enumerate(aligned.columns, start=1):  # +1 for constant
        try:
            vif = float(variance_inflation_factor(X, i))
        except (ValueError, np.linalg.LinAlgError):
            vif = float("nan")
        vifs[col] = vif
        out[col] = vif
    finite = [v for v in vifs.values() if math.isfinite(v)]
    out["max_vif"] = float(max(finite)) if finite else None
    return out


@dataclass(frozen=True)
class BonferroniCell:
    component_id: str
    horizon_months: int
    p_value: Optional[float]
    t_nw: Optional[float]
    beta: Optional[float]
    n_obs_oos: int
    n_eff: float
    hac_lag: int
    gate_status: str
    adequately_sampled: bool


def run_bonferroni_sweep(
    panel: V2Panel,
    oos_split: pd.Timestamp = pd.Timestamp("2021-01-31"),
    n_obs_oos_floor: int = 60,
) -> list[BonferroniCell]:
    """Sealed §5.3: 5 components × 4 horizons = 20 (component × horizon) cells.

    For each cell, run univariate predictive regression of forward returns
    on the component's PIT z-score, with NW HAC SE (Phase D
    :func:`run_predictive_regression_v2`).
    """
    out: list[BonferroniCell] = []
    components = {
        "z1": panel.components.z1,
        "z2": panel.components.z2,
        "z3": panel.components.z3,
        "z4": panel.components.z4,
        "z5": panel.components.z5,
    }
    for cid, comp_series in components.items():
        if comp_series is None:
            for h_m in C7_HORIZONS_MONTHS:
                out.append(
                    BonferroniCell(
                        component_id=cid, horizon_months=h_m,
                        p_value=None, t_nw=None, beta=None,
                        n_obs_oos=0, n_eff=0.0,
                        hac_lag=compute_hac_lag(h_m),
                        gate_status="not_evaluable", adequately_sampled=False,
                    )
                )
            continue
        for h_m in C7_HORIZONS_MONTHS:
            h_y = h_m // 12
            fr = panel.forward_returns.get(h_y)
            if fr is None:
                out.append(
                    BonferroniCell(
                        component_id=cid, horizon_months=h_m,
                        p_value=None, t_nw=None, beta=None,
                        n_obs_oos=0, n_eff=0.0,
                        hac_lag=compute_hac_lag(h_m),
                        gate_status="not_evaluable", adequately_sampled=False,
                    )
                )
                continue
            reg = run_predictive_regression_v2(
                comp_series, fr,
                horizon_months=h_m, forecast_origin=oos_split,
            )
            adequately = reg.n_obs_oos >= n_obs_oos_floor and reg.gate_status == "evaluable"
            out.append(
                BonferroniCell(
                    component_id=cid, horizon_months=h_m,
                    p_value=float(reg.p_nw) if math.isfinite(reg.p_nw) else None,
                    t_nw=float(reg.t_nw) if math.isfinite(reg.t_nw) else None,
                    beta=float(reg.beta) if math.isfinite(reg.beta) else None,
                    n_obs_oos=int(reg.n_obs_oos),
                    n_eff=float(reg.n_eff),
                    hac_lag=int(reg.hac_lag) if reg.hac_lag is not None else compute_hac_lag(h_m),
                    gate_status=str(reg.gate_status) if reg.gate_status else "not_evaluable",
                    adequately_sampled=bool(adequately),
                )
            )
    return out


# ---------------------------------------------------------------------------
# E.4 — compose criteria input panel and run evaluate_v2_criteria
# ---------------------------------------------------------------------------


def compose_criteria_panel(
    sweep: dict[tuple[str, int], SweepResult],
    adf: dict[str, ADFResult],
    vif: dict[str, Optional[float]],
    bonferroni: list[BonferroniCell],
) -> pd.DataFrame:
    """Translate Phase E.2/E.3 outputs into the row-format expected by
    :func:`src.models.v2_criteria.evaluate_v2_criteria`.
    """
    rows: list[dict] = []

    # Regression panel rows: one per (composite × horizon) cell.
    for (scope, h_y), sr in sweep.items():
        reg = sr.regression
        rows.append(
            {
                "composite": scope,
                "horizon_months": HORIZONS_MONTHS[h_y],
                "component_id": "",
                "gate_status": reg.gate_status or "not_evaluable",
                "n_obs_oos": int(reg.n_obs_oos),
                "n_obs_insample": int(reg.n_obs_insample) if reg.n_obs_insample is not None else 0,
                "n_eff": float(reg.n_eff),
                "hac_lag": int(reg.hac_lag) if reg.hac_lag is not None else 0,
                "beta": float(reg.beta) if math.isfinite(reg.beta) else None,
                "t_nw": float(reg.t_nw) if math.isfinite(reg.t_nw) else None,
                "p_nw": float(reg.p_nw) if math.isfinite(reg.p_nw) else None,
                "oos_r2": reg.oos_r2 if (reg.oos_r2 is not None and math.isfinite(reg.oos_r2)) else None,
                "clark_west_stat": reg.clark_west_stat,
                "max_vif": None,
                "adf_pvalue": None,
                "p_value": None,
            }
        )

    # C5 ADF rows: one per component (composite-agnostic).
    for cid, adf_res in adf.items():
        rows.append(
            {
                "composite": "",
                "horizon_months": 0,
                "component_id": cid,
                "gate_status": "evaluable" if (adf_res.p_value is not None) else "not_evaluable",
                "n_obs_oos": adf_res.n_obs or 0,
                "adf_pvalue": adf_res.p_value,
            }
        )

    # C6 VIF: single max_vif row.
    rows.append(
        {
            "composite": "",
            "horizon_months": 0,
            "component_id": "",
            "max_vif": vif.get("max_vif"),
        }
    )

    # C7 Bonferroni rows: 20 (component × horizon).
    for bcell in bonferroni:
        rows.append(
            {
                "composite": "",
                "horizon_months": bcell.horizon_months,
                "component_id": bcell.component_id,
                "gate_status": bcell.gate_status,
                "n_obs_oos": bcell.n_obs_oos,
                "n_eff": bcell.n_eff,
                "hac_lag": bcell.hac_lag,
                "p_value": bcell.p_value,
                "t_nw": bcell.t_nw,
                "beta": bcell.beta,
            }
        )

    return pd.DataFrame(rows)
