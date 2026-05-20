"""Top-level modeling orchestrator (Spec v5 dual-frame + forward outlook).

For each (variant, frame) the pipeline now also produces, per horizon, a
``forward_outlook`` block containing:
    regression       -- OLS + Newey-West HAC + Hansen-Hodrick + Stambaugh
    oos              -- Goyal-Welch R^2_OOS + Clark-West MSPE-adj
    conditional_dist -- empirical bucket of forward returns at current z
    probabilities    -- bootstrap-CI P(neg/below-rf/below-5pct/above-7pct)
    bayesian         -- Normal-Normal posterior with Gordon-Growth prior
    full_conviction  -- Master Spec section 6.3 score
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.config import DATA_DIR, OUTPUTS_DIR, PROJECT_ROOT, ensure_skeleton
from src.ingest._base import get_logger

logger = get_logger("buffett.models.orchestrator")


# Bai-Perron defaults used for the ``current_regime`` frame.
_BP_DEFAULTS: dict[str, Any] = {"max_breaks": 2, "criterion": "lwz"}

# Headline horizon for full_conviction and CLI display.
_HEADLINE_HORIZON_MONTHS = 120

# Per-horizon analysis schedule.
_PRIMARY_HORIZONS_MONTHS = (12, 36, 60, 120)
_ROBUSTNESS_HORIZONS_MONTHS = (60, 120)


# Spec v6: human-readable labels + units for each variant (used by the
# headline JSON + CLI + future dashboard). Variants not listed default to
# (variant_key, "").
HEADLINE_LABELS: dict[str, tuple[str, str]] = {
    "bi_allequity_pct": ("Buffett (All Equity)", "%"),
    "bi_wilshire_pct": ("Buffett (Wilshire)", "%"),
    "bi_spx_proxy": ("Buffett (SPX proxy)", "%"),
    "cape": ("CAPE / Shiller P/E10", ""),
    # Spec v7 additions:
    "qratio": ("Tobin's Q-Ratio", ""),
    "ey_deficit": ("Equity Yield Deficit", "%"),
    "mvci": ("MV Composite Index", "sigma"),
    # Spec v8a.1 addition:
    "mean_reversion": ("Mean Reversion (Real S&P)", ""),
    # Spec v9.0 addition: Crestmont P/E (Easterling 2010) — trend-earnings normalization.
    "crestmont": ("Crestmont P/E", ""),
    # Spec v11.0b additions: Macro Risk Module.
    "yc_10y3m": ("Yield Curve 10Y-3M", "pp"),
    "yc_10y2y": ("Yield Curve 10Y-2Y", "pp"),
    "cs_hy_master": ("HY OAS (master)", "pp"),
    "cs_ig_master": ("IG OAS (master)", "pp"),
    "cs_hy_bb": ("HY BB OAS", "pp"),
    "cs_hy_ccc": ("HY CCC OAS", "pp"),
    "margin_debt_growth": ("Margin Debt 12M Growth", "log"),
    "mrc": ("MV Macro Risk Composite", "sigma"),
    "mrc_equal_weight": ("MRC (equal weight)", "sigma"),
    "mrc_inv_variance": ("MRC (inverse variance)", "sigma"),
    "mrc_pca_pc1": ("MRC (PCA PC1)", "sigma"),
}

# All variants currently use the convention HIGH = OVERVALUED. EY-Deficit is
# already negated at source so it follows the same rule.
HEADLINE_DIRECTION: dict[str, int] = {
    "bi_allequity_pct": +1,
    "bi_wilshire_pct": +1,
    "bi_spx_proxy": +1,
    "cape": +1,
    "qratio": +1,
    "ey_deficit": +1,
    "mvci": +1,
    "mean_reversion": +1,
    "crestmont": +1,
    # v11.0b macro additions (all already direction-encoded via signal column).
    "yc_10y3m": +1,
    "yc_10y2y": +1,
    "cs_hy_master": +1,
    "cs_ig_master": +1,
    "cs_hy_bb": +1,
    "cs_hy_ccc": +1,
    "margin_debt_growth": +1,
    "mrc": +1,
    "mrc_equal_weight": +1,
    "mrc_inv_variance": +1,
    "mrc_pca_pc1": +1,
}


# Spec v6: CAPE has a small publication lag (~15 days) for the backtest view.
CAPE_RELEASE_LAG = pd.Timedelta(days=15)


def _apply_release_lag_to_cape(
    cape_variants: dict[str, pd.Series],
    *,
    lag: pd.Timedelta = CAPE_RELEASE_LAG,
    today: pd.Timestamp | None = None,
) -> dict[str, pd.Series]:
    """Drop CAPE observations whose publication date (idx + lag) is after ``today``.

    Practical effect: latest 1 monthly observation is excluded from the
    backtest view (since Shiller typically publishes mid-month).
    """
    today = today or pd.Timestamp.utcnow().tz_localize(None).normalize()
    out: dict[str, pd.Series] = {}
    for k, s in cape_variants.items():
        s = s.copy()
        publication_dates = s.index + lag
        out[k] = s[publication_dates <= today]
    return out


# ---------------------------------------------------------------------------
# Helpers (shared with v4.2)
# ---------------------------------------------------------------------------


def _battery_agreement(*fitted_series: pd.Series) -> float:
    fits = pd.DataFrame({f"t{i}": s for i, s in enumerate(fitted_series)}).dropna()
    if len(fits) < 5 or fits.shape[1] < 2:
        return 0.0
    corr = fits.corr().abs().values
    n = corr.shape[0]
    mask = ~np.eye(n, dtype=bool)
    return float(corr[mask].mean()) if mask.any() else 1.0


def _load_api_key(api_key: str | None) -> str:
    if api_key:
        return api_key
    cfg_path = PROJECT_ROOT / "config.yaml"
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
        key = cfg.get("fred_api_key")
        if key and key != "PASTE_YOUR_32_CHAR_KEY_HERE":
            return str(key)
    import os

    env = os.environ.get("FRED_API_KEY")
    if env:
        return env
    raise RuntimeError(
        "No FRED API key available; pass api_key=, set FRED_API_KEY, "
        "or fill in config.yaml.",
    )


# Series fields that are too large for the headline JSON dump (kept in-memory
# for downstream consumers like MVCI but stripped from outputs/tables/headline.json).
_HEAVY_SERIES_KEYS = {"z_score_series", "weights_history"}


def _to_jsonable(obj: Any, *, _key: str | None = None) -> Any:
    if _key in _HEAVY_SERIES_KEYS:
        return "<series stripped for JSON>"
    if isinstance(obj, dict):
        return {k: _to_jsonable(v, _key=k) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.DataFrame):
        return "<dataframe stripped for JSON>"
    if isinstance(obj, pd.Series):
        return _to_jsonable(obj.dropna().tail(60).to_dict())
    if isinstance(obj, pd.Timedelta):
        return str(obj)
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    return obj


def _narrative_code(z_lr: float, z_cr: float) -> str:
    if z_lr > 1.5 and z_cr > 1.5:
        return "AGREE_EXTREME_HIGH"
    if z_lr < -1.5 and z_cr < -1.5:
        return "AGREE_EXTREME_LOW"
    if abs(z_lr) <= 1.0 and abs(z_cr) <= 1.0:
        return "AGREE_FAIR"
    if z_lr > 1.5 and z_cr < 1.0:
        return "BUBBLE_OR_SHIFT"
    if z_lr < -1.5 and z_cr > -1.0:
        return "CRASH_OR_SHIFT"
    return "MIXED"


def _cross_variant_for_frame(
    variants: dict[str, dict[str, Any]], frame_name: str
) -> dict[str, Any]:
    from src.models.preliminary_metrics import cross_variant_agreement

    zs = {k: variants[k][frame_name]["z_score"] for k in variants}
    out = cross_variant_agreement(zs)
    out["n_variants"] = int(len(zs))
    return out


_NARRATIVES: dict[str, str] = {
    "AGREE_EXTREME_HIGH": (
        "Both lenses agree the US equity market is statistically extreme on the "
        "high side. Long-run trend (1947+ log-linear OLS, Huber sigma) and "
        "current-regime trend (Bai-Perron piecewise) both register z-scores "
        "above +1.5 across variants. High conviction in 'overvalued' "
        "designation; the data does not support a structural-shift hypothesis."
    ),
    "AGREE_EXTREME_LOW": (
        "Both lenses agree the US equity market is statistically extreme on the "
        "low side. Long-run trend and current-regime trend both register "
        "z-scores below -1.5. High conviction in 'undervalued' designation."
    ),
    "AGREE_FAIR": (
        "Both lenses agree the US equity market is statistically near long-run "
        "fair value. Z-scores within +/- 1.0 across frames; no actionable "
        "valuation extreme."
    ),
    "BUBBLE_OR_SHIFT": (
        "Long-run trend flags US equities as extreme high. Current-regime "
        "trend absorbs the post-GFC rally as a new equilibrium and reads near-"
        "fair. The two lenses diverge -- this divergence is itself the "
        "diagnostic finding. Either US equity valuations have undergone a "
        "permanent structural upshift, OR the post-2010 rally is an extended "
        "bubble that Bai-Perron has been forced to accommodate within a "
        "within-regime trend. The two hypotheses are observationally "
        "indistinguishable from current data."
    ),
    "CRASH_OR_SHIFT": (
        "Long-run trend flags US equities as extreme low; current-regime trend "
        "reads near-fair. Symmetric to BUBBLE_OR_SHIFT: either the current low "
        "is the new normal, or the long-run mean reverter is about to do its "
        "job. Observationally indistinguishable with current data."
    ),
    "MIXED": (
        "The long-run and current-regime frames give partially conflicting "
        "valuation signals. Neither all-agreement nor a clean bubble-or-shift "
        "pattern; the variants split between regimes. Inspect each variant's "
        "z-scores and narrative_code individually."
    ),
}


def _consensus_code(per_variant_codes: list[str]) -> str:
    if not per_variant_codes:
        return "MIXED"
    counts = Counter(per_variant_codes)
    most_common, n = counts.most_common(1)[0]
    if n >= 2:
        return most_common
    return "MIXED"


# ---------------------------------------------------------------------------
# Forward-outlook helpers
# ---------------------------------------------------------------------------


def _horizon_col(horizon_months: int) -> str:
    return f"r_{horizon_months}m"


def _per_horizon_outlook(
    z: pd.Series,
    fr_table: pd.DataFrame,
    horizon_months: int,
    *,
    risk_free_rate_decimal: float,
    n_bootstrap_prob: int,
) -> dict[str, Any]:
    """Compute (regression, oos, cond_dist, probabilities, bayesian) at one horizon."""
    from src.models.bayesian_posterior import bayesian_forward_return
    from src.models.conditional_distribution import conditional_distribution
    from src.models.oos_validation import clark_west, goyal_welch_oos_r2
    from src.models.predictive_regression import (
        InsufficientSampleError,
        predictive_regression,
    )
    from src.models.probability_engine import compute_probabilities

    col = _horizon_col(horizon_months)
    if col not in fr_table.columns:
        return {"available": False, "reason": f"horizon {horizon_months}m not in FR table"}

    r_fwd = fr_table[col].dropna()
    z_aligned = z.reindex(r_fwd.index).dropna()
    common = z_aligned.index.intersection(r_fwd.index)
    z_a = z_aligned.loc[common]
    r_a = r_fwd.loc[common]

    out: dict[str, Any] = {"available": True, "horizon_months": int(horizon_months)}
    try:
        reg = predictive_regression(z_a, r_a, horizon_months=horizon_months)
        out["regression"] = reg
    except InsufficientSampleError as exc:
        out["available"] = False
        out["reason"] = str(exc)
        return out

    out["oos"] = {
        "goyal_welch": goyal_welch_oos_r2(z_a, r_a),
        "clark_west": clark_west(z_a, r_a),
    }
    cd = conditional_distribution(z_a, r_a, n_buckets=5, risk_free_rate=risk_free_rate_decimal)
    out["conditional_dist"] = cd
    out["probabilities"] = compute_probabilities(
        cd,
        risk_free_rate_decimal=risk_free_rate_decimal,
        n_bootstrap=n_bootstrap_prob,
    )

    latest_z = float(z_a.iloc[-1])
    out["bayesian"] = bayesian_forward_return(latest_z, reg)

    return out


def _forward_outlook_for_frame(
    z: pd.Series,
    forward_returns: dict[str, pd.DataFrame],
    *,
    risk_free_rate_decimal: float,
    n_bootstrap_prob: int,
) -> dict[str, Any]:
    """Build the per-FR-source, per-horizon forward outlook block for one frame."""
    out: dict[str, Any] = {}
    primary_table = forward_returns.get("fr_spliced")
    if primary_table is not None:
        primary_block: dict[str, Any] = {}
        for h in _PRIMARY_HORIZONS_MONTHS:
            primary_block[f"h_{h}m"] = _per_horizon_outlook(
                z,
                primary_table,
                horizon_months=h,
                risk_free_rate_decimal=risk_free_rate_decimal,
                n_bootstrap_prob=n_bootstrap_prob,
            )
        out["primary"] = primary_block

    for robust_key, name in (
        ("fr_spxtr_only", "robustness_spxtr_only"),
        ("fr_shiller_only", "robustness_shiller_only"),
    ):
        table = forward_returns.get(robust_key)
        if table is None:
            continue
        block: dict[str, Any] = {}
        for h in _ROBUSTNESS_HORIZONS_MONTHS:
            block[f"h_{h}m"] = _per_horizon_outlook(
                z,
                table,
                horizon_months=h,
                risk_free_rate_decimal=risk_free_rate_decimal,
                n_bootstrap_prob=n_bootstrap_prob,
            )
        out[name] = block
    return out


def _full_conviction_block(
    abs_z: float,
    cross_variant_agreement: float,
    outlook_primary: dict[str, Any],
    z_series: pd.Series,
    fr_primary: pd.DataFrame,
    *,
    frame_disagreement_penalty: float = 0.0,
) -> dict[str, Any]:
    """Compute full_conviction per horizon using the primary FR source."""
    from src.models.full_conviction import full_conviction, historical_hit_rate

    out: dict[str, Any] = {}
    current_z = float(z_series.dropna().iloc[-1]) if not z_series.dropna().empty else float("nan")
    for h in _PRIMARY_HORIZONS_MONTHS:
        outlook = outlook_primary.get(f"h_{h}m")
        if not outlook or not outlook.get("available"):
            continue
        reg = outlook["regression"]
        r_fwd = fr_primary[_horizon_col(h)].dropna()
        hr = historical_hit_rate(
            z_series, r_fwd, current_z=current_z, horizon_months=h
        )
        oos_r2 = outlook["oos"]["goyal_welch"]["r2_oos"]
        fc = full_conviction(
            abs_z=abs_z,
            cross_variant_agreement=cross_variant_agreement,
            t_hac=reg["t_hh"] if np.isfinite(reg["t_hh"]) else reg["t_nw"],
            r2_oos=float(oos_r2) if oos_r2 is not None else float("nan"),
            hit_rate=hr["hit_rate"],
            frame_disagreement_penalty=frame_disagreement_penalty,
        )
        fc["historical_hit_rate"] = hr
        out[f"h_{h}m"] = fc
    return out


# ---------------------------------------------------------------------------
# Per-variant analysis (dual frame + forward outlook)
# ---------------------------------------------------------------------------


def _analyze_dual_frame(
    bi_series: pd.Series,
    *,
    forward_returns: dict[str, pd.DataFrame] | None,
    bootstrap_n: int,
    risk_free_rate_decimal: float,
    n_bootstrap_prob: int,
    include_forward_outlook: bool = True,
    xv_agreement_long_run: float = 0.0,
    xv_agreement_current_regime: float = 0.0,
    variant_key: str = "",
) -> dict[str, Any]:
    from src.models.bootstrap_ci import bootstrap_zscore_ci
    from src.models.regime import classify
    from src.models.trend import bai_perron_trend, hp_filter_trend, log_linear_trend
    from src.models.zscore import empirical_percentile, expanding_zscore

    if bi_series.empty:
        raise ValueError("BI series is empty")

    # Trend functions need strictly positive input (log transform). Variants
    # like EY-Deficit can be negative; shift up so the minimum is well above 0.
    # The log-trend's intercept absorbs the shift; residuals' z-scores are
    # invariant to the additive offset (Taylor: log(c+x) ~ log(c) + x/c).
    series_min = float(bi_series.min())
    if series_min <= 0:
        shift = float(abs(series_min) + 10.0)
        positive_series = bi_series + shift
    else:
        positive_series = bi_series

    ll = log_linear_trend(positive_series)
    hp = hp_filter_trend(positive_series)
    bp = bai_perron_trend(positive_series, **_BP_DEFAULTS)
    tb_agreement = _battery_agreement(ll["fitted"], hp["fitted"], bp["fitted"])

    headline_label, headline_unit = HEADLINE_LABELS.get(variant_key, (variant_key, ""))
    headline_value = float(bi_series.iloc[-1])
    out: dict[str, Any] = {
        "headline_value": headline_value,
        "bi_value": headline_value,  # back-compat alias for the v8 dashboard
        "headline_label": headline_label,
        "headline_unit": headline_unit,
        "valuation_direction": HEADLINE_DIRECTION.get(variant_key, +1),
        "asof": bi_series.index[-1],
        "trend_battery_agreement": tb_agreement,
        "loglinear_r2": float(ll["r_squared"]),
    }

    frames_spec: list[tuple[str, pd.Series, str, dict[str, Any]]] = [
        ("long_run", ll["residuals"], "log_linear", {}),
        (
            "current_regime",
            bp["residuals"],
            "bai_perron",
            {
                "n_breaks": int(bp["n_breaks"]),
                "break_dates": [str(d.date()) for d in bp["break_dates"]],
                "bai_perron_method": bp["method"],
            },
        ),
    ]

    z_series_per_frame: dict[str, pd.Series] = {}
    for frame_name, residuals, method, extras in frames_spec:
        z = expanding_zscore(residuals, scale_method="huber")
        z_series_per_frame[frame_name] = z
        clean_z = z.dropna()
        if clean_z.empty:
            raise ValueError(
                f"frame '{frame_name}' has <60 monthly obs; expanding z undefined"
            )
        latest_z = float(clean_z.iloc[-1])
        ci = bootstrap_zscore_ci(residuals, n_replications=bootstrap_n)
        pct = empirical_percentile(residuals, value=float(residuals.iloc[-1]))
        regime, color = classify(latest_z)
        out[frame_name] = {
            "z_score": latest_z,
            "z_score_ci95": (ci["ci_lower"], ci["ci_upper"]),
            "ci_width": ci["ci_width"],
            "empirical_percentile": float(pct),
            "regime": regime,
            "regime_color": color,
            "confidence_pct": ci["confidence_pct"],
            "trend_method": method,
            "n_observations": int(residuals.dropna().shape[0]),
            "scale_method": "huber",
            # Spec v7: expose the full z-score series for MVCI consumption.
            "z_score_series": z,
            **extras,
        }

    z_lr = out["long_run"]["z_score"]
    z_cr = out["current_regime"]["z_score"]
    same_regime = out["long_run"]["regime"] == out["current_regime"]["regime"]
    out["frame_interpretation"] = {
        "agreement": bool(same_regime),
        "consensus_regime": out["long_run"]["regime"] if same_regime else None,
        "max_z": float(max(z_lr, z_cr)),
        "min_z": float(min(z_lr, z_cr)),
        "z_spread": float(abs(z_lr - z_cr)),
        "narrative_code": _narrative_code(z_lr, z_cr),
    }

    # Forward outlook + full conviction per frame.
    if include_forward_outlook and forward_returns is not None:
        for frame_name, _resid, _method, _extras in frames_spec:
            z = z_series_per_frame[frame_name]
            out_frame = out[frame_name]
            outlook = _forward_outlook_for_frame(
                z,
                forward_returns,
                risk_free_rate_decimal=risk_free_rate_decimal,
                n_bootstrap_prob=n_bootstrap_prob,
            )
            out_frame["forward_outlook"] = outlook

            xv = (
                xv_agreement_long_run
                if frame_name == "long_run"
                else xv_agreement_current_regime
            )
            penalty = 0.0
            if not same_regime:
                penalty = 0.3  # mild penalty when frames disagree
            fr_primary = forward_returns.get("fr_spliced")
            if fr_primary is not None and "primary" in outlook:
                out_frame["full_conviction"] = _full_conviction_block(
                    abs_z=abs(out_frame["z_score"]),
                    cross_variant_agreement=xv,
                    outlook_primary=outlook["primary"],
                    z_series=z,
                    fr_primary=fr_primary,
                    frame_disagreement_penalty=penalty,
                )

    return out


# ---------------------------------------------------------------------------
# View builder
# ---------------------------------------------------------------------------


def _build_view(
    bi_dict: dict[str, pd.Series],
    view_name: str,
    *,
    forward_returns: dict[str, pd.DataFrame] | None,
    bootstrap_n: int,
    risk_free_rate_decimal: float,
    n_bootstrap_prob: int,
    include_forward_outlook: bool,
) -> dict[str, Any]:
    if not bi_dict:
        return {
            "view": view_name,
            "variants": {},
            "cross_variant_long_run": {},
            "cross_variant_current_regime": {},
            "preliminary_conviction": {},
            "interpretation": {},
            "asof": None,
        }

    # First pass: per-variant without xv_agreement (so we have z_scores to compute xv).
    pre = {
        k: _analyze_dual_frame(
            v,
            forward_returns=None,
            bootstrap_n=bootstrap_n,
            risk_free_rate_decimal=risk_free_rate_decimal,
            n_bootstrap_prob=n_bootstrap_prob,
            include_forward_outlook=False,
            variant_key=k,
        )
        for k, v in bi_dict.items()
    }
    xv_lr_pre = _cross_variant_for_frame(pre, "long_run")
    xv_cr_pre = _cross_variant_for_frame(pre, "current_regime")

    # Second pass: full analysis with xv_agreement available for conviction.
    variants = {
        k: _analyze_dual_frame(
            v,
            forward_returns=forward_returns if include_forward_outlook else None,
            bootstrap_n=bootstrap_n,
            risk_free_rate_decimal=risk_free_rate_decimal,
            n_bootstrap_prob=n_bootstrap_prob,
            include_forward_outlook=include_forward_outlook,
            xv_agreement_long_run=xv_lr_pre["agreement"],
            xv_agreement_current_regime=xv_cr_pre["agreement"],
            variant_key=k,
        )
        for k, v in bi_dict.items()
    }

    xv_lr = _cross_variant_for_frame(variants, "long_run")
    xv_cr = _cross_variant_for_frame(variants, "current_regime")
    z_spread_avg = float(
        np.mean([v["frame_interpretation"]["z_spread"] for v in variants.values()])
    )
    n_obs_min = min(v["long_run"]["n_observations"] for v in variants.values())

    from src.models.preliminary_metrics import dual_frame_conviction

    conviction = dual_frame_conviction(
        long_run_mean_z=xv_lr["mean_z"],
        current_regime_mean_z=xv_cr["mean_z"],
        cross_variant_agreement_long_run=xv_lr["agreement"],
        cross_variant_agreement_current_regime=xv_cr["agreement"],
        z_spread_avg=z_spread_avg,
        n_observations=n_obs_min,
    )

    per_variant_codes = [
        v["frame_interpretation"]["narrative_code"] for v in variants.values()
    ]
    headline_code = _consensus_code(per_variant_codes)
    narrative = _NARRATIVES.get(headline_code, _NARRATIVES["MIXED"])

    return {
        "asof": max(v["asof"] for v in variants.values()),
        "view": view_name,
        "variants": variants,
        "cross_variant_long_run": xv_lr,
        "cross_variant_current_regime": xv_cr,
        "preliminary_conviction": conviction,
        "interpretation": {
            "primary_frame": "long_run",
            "narrative_code": headline_code,
            "narrative": narrative,
            "per_variant_codes": per_variant_codes,
            "z_spread_avg": z_spread_avg,
        },
    }


# ---------------------------------------------------------------------------
# Spec v7: MVCI integration
# ---------------------------------------------------------------------------


_CONSTITUENT_KEYS = (
    "bi_allequity_pct",
    "bi_wilshire_pct",
    "bi_spx_proxy",
    "cape",
    "qratio",
    "ey_deficit",
    # Spec v8a.1: Mean Reversion added as a 7th MVCI constituent.
    "mean_reversion",
    # Spec v9.0: Crestmont P/E added as an 8th MVCI constituent.
    "crestmont",
)


def _build_z_panel(
    variants: dict[str, dict[str, Any]], frame_name: str
) -> pd.DataFrame:
    """Stack constituent z-score series into one aligned panel."""
    cols: dict[str, pd.Series] = {}
    for k in _CONSTITUENT_KEYS:
        if k not in variants:
            continue
        frame = variants[k].get(frame_name, {})
        z_series = frame.get("z_score_series")
        if isinstance(z_series, pd.Series):
            cols[k] = z_series.astype("float64")
    if not cols:
        return pd.DataFrame()
    panel = pd.DataFrame(cols)
    return panel


def _mvci_forward_outlook_block(
    z_series: pd.Series,
    forward_returns: dict[str, pd.DataFrame] | None,
    *,
    risk_free_rate_decimal: float,
    n_bootstrap_prob: int,
) -> dict[str, Any]:
    if forward_returns is None:
        return {}
    return _forward_outlook_for_frame(
        z_series,
        forward_returns,
        risk_free_rate_decimal=risk_free_rate_decimal,
        n_bootstrap_prob=n_bootstrap_prob,
    )


def _mvci_full_conviction_block(
    abs_z: float,
    cross_variant_agreement: float,
    outlook_primary: dict[str, Any],
    z_series: pd.Series,
    fr_primary: pd.DataFrame,
    *,
    frame_disagreement_penalty: float = 0.0,
) -> dict[str, Any]:
    return _full_conviction_block(
        abs_z=abs_z,
        cross_variant_agreement=cross_variant_agreement,
        outlook_primary=outlook_primary,
        z_series=z_series,
        fr_primary=fr_primary,
        frame_disagreement_penalty=frame_disagreement_penalty,
    )


def _build_mvci_for_frame(
    z_panel: pd.DataFrame,
    *,
    frame_name: str,
    bootstrap_n: int,
    forward_returns: dict[str, pd.DataFrame] | None,
    risk_free_rate_decimal: float,
    n_bootstrap_prob: int,
    xv_agreement: float,
    frame_disagreement_penalty: float = 0.0,
) -> dict[str, Any]:
    """Build the MVCI block for one frame: 3 schemes + default forward outlook."""
    from src.models.bootstrap_ci import bootstrap_zscore_ci
    from src.models.regime import classify
    from src.models.zscore import empirical_percentile
    from src.transform.mvci_compute import compute_mvci_schemes

    schemes = compute_mvci_schemes(z_panel)
    default = schemes["equal_weight"]
    default_series = default["z_score_series"].dropna()
    if default_series.empty:
        return {}

    latest_z = float(default_series.iloc[-1])
    regime, color = classify(latest_z)
    # Bootstrap CI uses the equal-weight series itself as "residuals" (already
    # standardized, so the conditional-SD interpretation is direct).
    ci = bootstrap_zscore_ci(default_series, n_replications=bootstrap_n)
    pct = empirical_percentile(default_series, value=latest_z)

    frame_out: dict[str, Any] = {
        "z_score": latest_z,
        "z_score_ci95": (ci["ci_lower"], ci["ci_upper"]),
        "ci_width": ci["ci_width"],
        "empirical_percentile": float(pct),
        "regime": regime,
        "regime_color": color,
        "confidence_pct": ci["confidence_pct"],
        "trend_method": "mvci_aggregate",
        "n_observations": int(len(default_series)),
        "scale_method": "huber_constituents",
        "z_score_series": default["z_score_series"],
        "weights_current": default["weights_current"],
        "schemes": {
            name: {
                "scheme": s["scheme"],
                "z_score": s["z_score"],
                "weights_current": s["weights_current"],
                # v8b.1: loadings_full carries the unscaled PCA PC1 eigenvector
                # so the dashboard can display every variant's contribution.
                "loadings_full": s.get("loadings_full"),
                "explained_variance": s.get("explained_variance"),
                "n_constituents": s["n_constituents"],
                "z_score_series": s["z_score_series"],
            }
            for name, s in schemes.items()
        },
    }

    if forward_returns is not None:
        outlook = _forward_outlook_for_frame(
            default["z_score_series"],
            forward_returns,
            risk_free_rate_decimal=risk_free_rate_decimal,
            n_bootstrap_prob=n_bootstrap_prob,
        )
        frame_out["forward_outlook"] = outlook
        fr_primary = forward_returns.get("fr_spliced")
        if fr_primary is not None and "primary" in outlook:
            frame_out["full_conviction"] = _full_conviction_block(
                abs_z=abs(latest_z),
                cross_variant_agreement=xv_agreement,
                outlook_primary=outlook["primary"],
                z_series=default["z_score_series"],
                fr_primary=fr_primary,
                frame_disagreement_penalty=frame_disagreement_penalty,
            )

    return frame_out


def _augment_view_with_mvci(
    view: dict[str, Any],
    *,
    forward_returns: dict[str, pd.DataFrame] | None,
    bootstrap_n: int,
    risk_free_rate_decimal: float,
    n_bootstrap_prob: int,
) -> dict[str, Any]:
    """Append an ``mvci`` variant to a built view, plus update interpretation."""
    variants = view["variants"]
    xv_lr = view.get("cross_variant_long_run", {})
    xv_cr = view.get("cross_variant_current_regime", {})

    # Build z-panels per frame from the existing variants (excluding mvci).
    panel_lr = _build_z_panel(variants, "long_run")
    panel_cr = _build_z_panel(variants, "current_regime")
    if panel_lr.empty and panel_cr.empty:
        return view

    label, unit = HEADLINE_LABELS["mvci"]
    mvci_entry: dict[str, Any] = {
        "headline_label": label,
        "headline_unit": unit,
        "valuation_direction": HEADLINE_DIRECTION["mvci"],
        "asof": view["asof"],
    }
    # headline_value for MVCI = latest equal-weight z (in sigma units).
    if not panel_lr.empty:
        mvci_lr = _build_mvci_for_frame(
            panel_lr,
            frame_name="long_run",
            bootstrap_n=bootstrap_n,
            forward_returns=forward_returns,
            risk_free_rate_decimal=risk_free_rate_decimal,
            n_bootstrap_prob=n_bootstrap_prob,
            xv_agreement=float(xv_lr.get("agreement", 0.0)),
        )
        mvci_entry["long_run"] = mvci_lr
    if not panel_cr.empty:
        mvci_cr = _build_mvci_for_frame(
            panel_cr,
            frame_name="current_regime",
            bootstrap_n=bootstrap_n,
            forward_returns=forward_returns,
            risk_free_rate_decimal=risk_free_rate_decimal,
            n_bootstrap_prob=n_bootstrap_prob,
            xv_agreement=float(xv_cr.get("agreement", 0.0)),
        )
        mvci_entry["current_regime"] = mvci_cr

    # Headline value: equal-weight long_run z (or current_regime if LR missing).
    lr_entry = mvci_entry.get("long_run") or {}
    cr_entry = mvci_entry.get("current_regime") or {}
    headline_val = lr_entry.get("z_score", cr_entry.get("z_score", float("nan")))
    mvci_entry["headline_value"] = float(headline_val)
    mvci_entry["bi_value"] = mvci_entry["headline_value"]

    z_lr = float(lr_entry.get("z_score", float("nan")))
    z_cr = float(cr_entry.get("z_score", float("nan")))
    same_regime = (
        lr_entry.get("regime") == cr_entry.get("regime")
        if lr_entry and cr_entry
        else False
    )
    mvci_entry["frame_interpretation"] = {
        "agreement": bool(same_regime),
        "consensus_regime": lr_entry.get("regime") if same_regime else None,
        "max_z": float(max(z_lr, z_cr)) if all(map(np.isfinite, (z_lr, z_cr))) else float("nan"),
        "min_z": float(min(z_lr, z_cr)) if all(map(np.isfinite, (z_lr, z_cr))) else float("nan"),
        "z_spread": float(abs(z_lr - z_cr)) if all(map(np.isfinite, (z_lr, z_cr))) else float("nan"),
        "narrative_code": _narrative_code(z_lr, z_cr)
        if all(map(np.isfinite, (z_lr, z_cr)))
        else "MIXED",
    }
    new_variants = dict(variants)
    new_variants["mvci"] = mvci_entry
    new_view = dict(view)
    new_view["variants"] = new_variants
    return new_view


# ---------------------------------------------------------------------------
# Flat-table flattening (forward_regressions.csv)
# ---------------------------------------------------------------------------


def _flatten_forward_regressions(headline: dict[str, Any]) -> pd.DataFrame:
    """Flatten the forward_outlook block into one row per (variant, frame, FR-source, horizon)."""
    rows: list[dict[str, Any]] = []
    for vname, v in headline.get("variants", {}).items():
        for frame_name in ("long_run", "current_regime"):
            frame = v.get(frame_name, {})
            outlook = frame.get("forward_outlook", {})
            for fr_source, horizons in outlook.items():
                for h_key, payload in horizons.items():
                    if not payload.get("available"):
                        continue
                    reg = payload["regression"]
                    oos = payload["oos"]["goyal_welch"]
                    cw = payload["oos"]["clark_west"]
                    p_neg = payload["probabilities"]["events"].get("P_neg_return", {})
                    p_below_5 = payload["probabilities"]["events"].get("P_below_5pct", {})
                    rows.append(
                        {
                            "variant": vname,
                            "frame": frame_name,
                            "fr_source": fr_source,
                            "horizon": h_key,
                            "n_obs": reg["n_obs"],
                            "alpha": reg["alpha"],
                            "beta": reg["beta"],
                            "beta_se_nw": reg["beta_se_nw"],
                            "t_nw": reg["t_nw"],
                            "t_hh": reg["t_hh"],
                            "pvalue_nw": reg["pvalue_nw"],
                            "r2_in": reg["r_squared"],
                            "r2_oos": oos["r2_oos"],
                            "cw_stat": cw["cw_stat"],
                            "cw_pvalue": cw["p_value"],
                            "p_neg": p_neg.get("point"),
                            "p_neg_ci_lo": (p_neg.get("ci95") or (None, None))[0],
                            "p_neg_ci_hi": (p_neg.get("ci95") or (None, None))[1],
                            "p_below_5pct": p_below_5.get("point"),
                            "rho_ar1": reg["rho_ar1"],
                            "beta_stambaugh": reg["beta_stambaugh"],
                        }
                    )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_modeling(
    api_key: str | None = None,
    *,
    save_outputs: bool = True,
    bootstrap_n: int = 10_000,
    n_bootstrap_prob: int = 2_000,
    risk_free_rate_decimal: float = 0.043,
    include_forward_outlook: bool = True,
) -> dict[str, Any]:
    """Run the full transform + dual-frame + forward-outlook pipeline."""
    ensure_skeleton()
    api_key = _load_api_key(api_key)

    # 1. Load ingestion outputs.
    from src.ingest.csv_loader import load_tradingview_inputs
    from src.ingest.fred_loader import load_buffett_fred
    from src.ingest.master_archive import load_master
    from src.ingest.shiller_loader import load_shiller

    fred = load_buffett_fred(api_key=api_key)
    tv = load_tradingview_inputs(require_all=False)
    wil = load_master("wilshire_5000")
    sh = load_shiller()

    # 2. Unit harmonization.
    from src.transform.unit_harmonization import (
        rate_to_decimal,
        to_trillions_from_billions,
        to_trillions_from_millions,
    )
    from src.transform.wilshire_scaling import points_to_trillions

    raw: dict[str, pd.Series | None] = {
        "gdp_t": to_trillions_from_billions(fred["gdp"].data),
        "equities_all_t": to_trillions_from_millions(fred["equities_all"].data),
        "equities_public_t": to_trillions_from_millions(fred["equities_public"].data),
        "equities_nonfin_t": to_trillions_from_millions(fred["equities_nonfin"].data),
        "wilshire_usd_t": points_to_trillions(wil.data),
        "spx": tv["spx"].data["close"] if "spx" in tv else None,
        "spxtr": tv["spxtr"].data["close"] if "spxtr" in tv else None,
        "cape": sh.data["cape"].dropna() if sh is not None else None,
        "gs10": rate_to_decimal(sh.data["long_rate_gs10"].dropna())
        if sh is not None
        else None,
    }
    raw_clean = {k: v for k, v in raw.items() if v is not None and not v.empty}

    # 3. Build forward-return tables (Spec v5 section 3).
    from src.transform.forward_returns import build_forward_returns

    spxtr_daily = tv["spxtr"].data["close"] if "spxtr" in tv else None
    try:
        forward_returns_tables = build_forward_returns(
            sh, spxtr_daily, check_continuity=False
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Forward returns build failed: %s", exc)
        forward_returns_tables = {}

    # 4. Align to monthly + compute BI variants.
    from src.transform.align_monthly import align_to_monthly_grid
    from src.transform.buffett_compute import compute_bi_variants

    aligned_desc = align_to_monthly_grid(raw_clean, view="descriptive")
    aligned_bt = align_to_monthly_grid(raw_clean, view="backtest")
    bi_desc = compute_bi_variants(aligned_desc)
    bi_bt = compute_bi_variants(aligned_bt)

    # Spec v6: add CAPE as a 4th variant. It reuses all the modeling
    # infrastructure verbatim (dual-frame z, trend battery, forward outlook,
    # full conviction). For the backtest view, apply a small publication lag.
    from src.transform.cape_variants import compute_cape_variants

    cape_variants_dict = compute_cape_variants(sh) if sh is not None else {}
    if cape_variants_dict:
        bi_desc = {**bi_desc, **cape_variants_dict}
        bi_bt = {**bi_bt, **_apply_release_lag_to_cape(cape_variants_dict)}

    # Spec v7: Q-Ratio + Equity Yield Deficit + MVCI composite. The new
    # variants are best-effort: if the FRED Z.1 net-worth series or DFII10
    # TIPS series are unavailable, the corresponding variant is skipped with
    # a WARNING and the rest of the pipeline continues.
    from src.ingest.fred_loader import load_fred_optional
    from src.transform.ey_deficit_compute import (
        EYDeficitInputMissingError,
        compute_ey_deficit,
    )
    from src.transform.qratio_compute import compute_qratio_variant

    try:
        fred_optional = load_fred_optional(api_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Optional FRED series load failed: %s", exc)
        fred_optional = {}

    vti_daily: pd.Series | None = None  # VTI ETF not yet wired into ingest layer
    nonfin_net_worth = fred_optional.get("nonfin_net_worth")
    tips_series_data = fred_optional.get("tips_10y")
    tips_series = tips_series_data.data if tips_series_data is not None else None

    q_variants = compute_qratio_variant(
        fred["equities_nonfin"], nonfin_net_worth, vti_series=vti_daily
    )
    if q_variants:
        bi_desc = {**bi_desc, **q_variants}
        bi_bt = {**bi_bt, **q_variants}  # Q-Ratio already lags Z.1 by ~10 weeks

    try:
        eyd_variants = compute_ey_deficit(sh, tips_series=tips_series)
    except EYDeficitInputMissingError as exc:
        logger.warning("EY-Deficit variant skipped: %s", exc)
        eyd_variants = {}
    if eyd_variants:
        bi_desc = {**bi_desc, **eyd_variants}
        bi_bt = {**bi_bt, **eyd_variants}

    # Spec v8a.1: Mean Reversion variant (real S&P 500 vs its own exponential
    # trend). Conceptually orthogonal to bi_spx_proxy (which divides SPX by
    # GDP); MR is purely autoregressive against the price's own long-run
    # trend, and is CMV's iconic chart.
    from src.transform.mean_reversion_compute import compute_mean_reversion_variant

    mr_variants = compute_mean_reversion_variant(sh) if sh is not None else {}
    if mr_variants:
        bi_desc = {**bi_desc, **mr_variants}
        bi_bt = {**bi_bt, **mr_variants}

    # Spec v9.0: Crestmont P/E (Easterling 2010). Real S&P 500 normalized
    # by an exponential trend of real earnings (vs CAPE's 10-year moving
    # average). 8th MVCI constituent.
    from src.transform.crestmont_compute import compute_crestmont_variant

    crestmont_variants = compute_crestmont_variant(sh) if sh is not None else {}
    if crestmont_variants:
        bi_desc = {**bi_desc, **crestmont_variants}
        bi_bt = {**bi_bt, **crestmont_variants}

    # 5. Build headline (with forward outlook) + backtest view (without, for speed).
    headline = _build_view(
        bi_desc,
        "descriptive",
        forward_returns=forward_returns_tables or None,
        bootstrap_n=bootstrap_n,
        risk_free_rate_decimal=risk_free_rate_decimal,
        n_bootstrap_prob=n_bootstrap_prob,
        include_forward_outlook=include_forward_outlook,
    )
    backtest_view = _build_view(
        bi_bt,
        "backtest",
        forward_returns=None,
        bootstrap_n=bootstrap_n,
        risk_free_rate_decimal=risk_free_rate_decimal,
        n_bootstrap_prob=n_bootstrap_prob,
        include_forward_outlook=False,
    )

    # Spec v7: build the MVCI composite from the 6 constituents' z-score series
    # and treat it as a 7th variant (with its own forward outlook + full
    # conviction). Excluded from cross_variant aggregation to avoid
    # double-counting.
    if include_forward_outlook and headline["variants"]:
        headline = _augment_view_with_mvci(
            headline,
            forward_returns=forward_returns_tables or None,
            bootstrap_n=bootstrap_n,
            risk_free_rate_decimal=risk_free_rate_decimal,
            n_bootstrap_prob=n_bootstrap_prob,
        )

    # 6. Persist outputs.
    if save_outputs:
        (OUTPUTS_DIR / "tables").mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "processed").mkdir(parents=True, exist_ok=True)
        for view_name, bi_dict in [("descriptive", bi_desc), ("backtest", bi_bt)]:
            if not bi_dict:
                continue
            df = pd.DataFrame(bi_dict)
            df.to_csv(OUTPUTS_DIR / "tables" / f"bi_series_{view_name}.csv")
            df.to_parquet(DATA_DIR / "processed" / f"bi_series_{view_name}.parquet")
        # Forward-returns parquet (primary FR source level series, if available).
        fr_primary = forward_returns_tables.get("fr_spliced")
        if fr_primary is not None:
            level = fr_primary.attrs.get("level_series")
            if isinstance(level, pd.Series):
                lvl_df = pd.DataFrame({"spliced_nominal_tr": level.astype("float64")})
                lvl_df.to_parquet(DATA_DIR / "processed" / "forward_returns.parquet")
        # Forward regressions flat CSV.
        flat = _flatten_forward_regressions(headline)
        if not flat.empty:
            flat.to_csv(
                OUTPUTS_DIR / "tables" / "forward_regressions.csv", index=False
            )
        with open(OUTPUTS_DIR / "tables" / "headline.json", "w", encoding="utf-8") as f:
            json.dump(
                _to_jsonable({"headline": headline, "backtest_view": backtest_view}),
                f,
                indent=2,
                default=str,
            )
        # Spec v8a: persist per-variant chart parquets for the dashboard.
        _save_chart_data(
            headline=headline,
            bi_desc=bi_desc,
            forward_returns_tables=forward_returns_tables,
            charts_dir=OUTPUTS_DIR / "charts",
            tv=tv,
        )

    return {
        "headline": headline,
        "backtest_view": backtest_view,
        "bi_series_descriptive": bi_desc,
        "bi_series_backtest": bi_bt,
        "forward_returns_tables": forward_returns_tables,
    }


# ---------------------------------------------------------------------------
# Spec v8a: chart-data persistence for the dashboard
# ---------------------------------------------------------------------------


_HEADLINE_LABELS_FOR_VALUE_HISTORY = {
    "bi_allequity_pct": "%",
    "bi_wilshire_pct": "%",
    "bi_spx_proxy": "%",
    "cape": "ratio",
    "qratio": "ratio",
    "ey_deficit": "%",
    "mvci": "sigma",
    "mean_reversion": "index",
    "crestmont": "ratio",
}


def _save_chart_data(
    *,
    headline: dict[str, Any],
    bi_desc: dict[str, pd.Series],
    forward_returns_tables: dict[str, pd.DataFrame],
    charts_dir: Path,
    tv: dict[str, Any] | None,
) -> None:
    """Write the 4 chart parquets consumed by ``src/viz/build_dashboard.py``."""
    from src.models.regime import classify

    charts_dir.mkdir(parents=True, exist_ok=True)

    variants = headline.get("variants", {})

    # 1. z_history.parquet  (long format: date, variant, frame, z_score, regime, regime_color)
    z_rows: list[dict[str, Any]] = []
    for vname, vdata in variants.items():
        for frame_name in ("long_run", "current_regime"):
            frame = vdata.get(frame_name, {})
            z_series = frame.get("z_score_series")
            if not isinstance(z_series, pd.Series):
                continue
            for date, z in z_series.dropna().items():
                regime, color = classify(float(z))
                z_rows.append(
                    {
                        "date": pd.Timestamp(date).normalize(),
                        "variant": vname,
                        "frame": frame_name,
                        "z_score": float(z),
                        "regime": regime,
                        "regime_color": color,
                    }
                )
    if z_rows:
        z_df = pd.DataFrame(z_rows)
        z_df.to_parquet(charts_dir / "z_history.parquet", index=False)

    # 2. value_history.parquet (long format: date, variant, value, unit)
    val_rows: list[dict[str, Any]] = []
    for vname, series in bi_desc.items():
        unit = _HEADLINE_LABELS_FOR_VALUE_HISTORY.get(vname, "")
        for date, value in series.dropna().items():
            val_rows.append(
                {
                    "date": pd.Timestamp(date).normalize(),
                    "variant": vname,
                    "value": float(value),
                    "unit": unit,
                }
            )
    # Also include MVCI level series (its equal-weight z is its own "value").
    mvci_entry = variants.get("mvci")
    if mvci_entry is not None:
        lr = mvci_entry.get("long_run", {})
        z_series = lr.get("z_score_series")
        if isinstance(z_series, pd.Series):
            for date, value in z_series.dropna().items():
                val_rows.append(
                    {
                        "date": pd.Timestamp(date).normalize(),
                        "variant": "mvci",
                        "value": float(value),
                        "unit": "sigma",
                    }
                )
    if val_rows:
        val_df = pd.DataFrame(val_rows)
        val_df.to_parquet(charts_dir / "value_history.parquet", index=False)

    # 3. sp500_with_regime.parquet (sp500 close + contemporaneous MVCI regime)
    sp500_daily: pd.Series | None = None
    if tv and "spx" in tv:
        sp500_daily = tv["spx"].data["close"]
    if sp500_daily is not None:
        sp500_monthly = sp500_daily.resample("ME").last().dropna()
        mvci_z_lr = (
            mvci_entry.get("long_run", {}).get("z_score_series")
            if mvci_entry
            else None
        )
        rows: list[dict[str, Any]] = []
        for date, close in sp500_monthly.items():
            d = pd.Timestamp(date).normalize()
            if isinstance(mvci_z_lr, pd.Series) and d in mvci_z_lr.index:
                z_val = mvci_z_lr.loc[d]
                if pd.notna(z_val):
                    regime, color = classify(float(z_val))
                else:
                    regime, color = ("Insufficient Data", "#000000")
            else:
                regime, color = ("Insufficient Data", "#000000")
            rows.append(
                {
                    "date": d,
                    "sp500_close": float(close),
                    "regime_mvci": regime,
                    "regime_color_mvci": color,
                }
            )
        pd.DataFrame(rows).to_parquet(charts_dir / "sp500_with_regime.parquet", index=False)

    # 4. scatter_data.parquet
    # Columns: date, variant, z_score_long_run, forward_{h}m_cagr for h in {1,3,12,36,60,84,120}
    scatter_rows: list[dict[str, Any]] = []
    fr_primary = forward_returns_tables.get("fr_spliced") if forward_returns_tables else None
    if fr_primary is not None:
        fr_cols = [c for c in fr_primary.columns if c.startswith("r_")]
        for vname, vdata in variants.items():
            lr = vdata.get("long_run", {})
            z_series = lr.get("z_score_series")
            if not isinstance(z_series, pd.Series):
                continue
            z_clean = z_series.dropna()
            for date, z_val in z_clean.items():
                d = pd.Timestamp(date).normalize()
                row: dict[str, Any] = {
                    "date": d,
                    "variant": vname,
                    "z_score_long_run": float(z_val),
                }
                if d in fr_primary.index:
                    for col in fr_cols:
                        cell = fr_primary.loc[d, col]
                        row[f"forward_{col[2:]}_cagr"] = (
                            float(cell) if pd.notna(cell) else float("nan")
                        )
                scatter_rows.append(row)
    if scatter_rows:
        scatter_df = pd.DataFrame(scatter_rows)
        scatter_df.to_parquet(charts_dir / "scatter_data.parquet", index=False)

    # Spec v8b §6.2 — emit diagnostics parquets after the 4 chart parquets exist.
    try:
        from src.models.diagnostics import emit_diagnostics
        emit_diagnostics(charts_dir)
    except Exception as exc:  # noqa: BLE001
        # Diagnostics are non-critical for the headline pipeline; log but don't fail.
        print(f"[orchestrator] diagnostics emit failed: {exc}")


__all__ = ["run_modeling"]
