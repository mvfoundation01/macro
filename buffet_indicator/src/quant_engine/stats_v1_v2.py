"""v11.2 — Statistical tests comparing V1 Combination to V2 variants.

Implements:
  - Jobson-Korkie (1981) Sharpe-difference test with Memmel (2003) correction
  - White's (2000) Reality Check via stationary bootstrap (Politis-Romano 1994)
  - Holm-Šidák step-down family-wise α correction
  - Bootstrap CI for Sharpe difference (stationary bootstrap)

Emits ``outputs/quant_engine/latest/v2_statistical_tests.csv``.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def jobson_korkie_test(
    r1: pd.Series, r2: pd.Series, ann_factor: float = 12.0
) -> dict[str, float | int]:
    """Jobson-Korkie (1981) Sharpe-difference test with Memmel (2003) correction.

    Tests H0: SR(r1) = SR(r2).

    Returns dict with sharpe_v1, sharpe_v2, sharpe_diff, z_stat, p_value, n_obs.
    """
    df = pd.concat([r1.rename("r1"), r2.rename("r2")], axis=1).dropna()
    n = len(df)
    if n < 24:
        return {
            "sharpe_v1": float("nan"), "sharpe_v2": float("nan"),
            "sharpe_diff": float("nan"), "z_stat": float("nan"),
            "p_value": float("nan"), "n_obs": n,
        }
    mu1, mu2 = df["r1"].mean(), df["r2"].mean()
    s1, s2 = df["r1"].std(ddof=1), df["r2"].std(ddof=1)
    if s1 == 0 or s2 == 0:
        return {
            "sharpe_v1": float("nan"), "sharpe_v2": float("nan"),
            "sharpe_diff": float("nan"), "z_stat": float("nan"),
            "p_value": float("nan"), "n_obs": n,
        }
    sr1 = mu1 / s1 * np.sqrt(ann_factor)
    sr2 = mu2 / s2 * np.sqrt(ann_factor)
    rho = df["r1"].corr(df["r2"])
    # Memmel (2003) corrected variance for Sharpe difference (annualized SRs).
    theta = (1.0 / n) * (
        2.0 - 2.0 * rho
        + 0.5 * sr1 ** 2 + 0.5 * sr2 ** 2
        - 0.5 * sr1 * sr2 * (1.0 + rho ** 2)
    )
    if theta <= 0 or not np.isfinite(theta):
        return {
            "sharpe_v1": float(sr1), "sharpe_v2": float(sr2),
            "sharpe_diff": float(sr2 - sr1), "z_stat": float("nan"),
            "p_value": float("nan"), "n_obs": n,
        }
    z = (sr1 - sr2) / np.sqrt(theta)
    p = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
    return {
        "sharpe_v1": float(sr1),
        "sharpe_v2": float(sr2),
        "sharpe_diff": float(sr2 - sr1),
        "z_stat": float(z),
        "p_value": float(p),
        "n_obs": int(n),
    }


def _stationary_bootstrap_indices(
    n: int, block_length: int, rng: np.random.Generator
) -> np.ndarray:
    """Generate one stationary bootstrap (Politis-Romano 1994) sample of indices."""
    p = 1.0 / max(block_length, 1)
    indices = np.empty(n, dtype=np.int64)
    indices[0] = rng.integers(0, n)
    for i in range(1, n):
        if rng.random() < p:
            indices[i] = rng.integers(0, n)
        else:
            indices[i] = (indices[i - 1] + 1) % n
    return indices


def whites_reality_check(
    benchmark_returns: pd.Series,
    rule_returns: dict[str, pd.Series],
    n_bootstrap: int = 10_000,
    block_length: int = 6,
    seed: int = 42,
) -> dict[str, float | str | int]:
    """White's (2000) Reality Check on the BEST-performing rule.

    Tests H0: max mean excess return ≤ 0 (no rule has skill over benchmark).

    Uses stationary bootstrap (Politis-Romano 1994).
    """
    df = pd.concat(
        [
            (s.rename(name) - benchmark_returns)
            for name, s in rule_returns.items()
        ],
        axis=1,
    ).dropna()
    if df.empty or df.shape[0] < 24:
        return {
            "best_rule": "n/a",
            "best_rule_excess_mean": float("nan"),
            "p_value_reality_check": float("nan"),
            "n_bootstrap": int(n_bootstrap),
            "n_obs": int(df.shape[0]),
        }
    excess = df.to_numpy(dtype=np.float64)
    n, k = excess.shape
    f_bar = excess.mean(axis=0)
    f_max_obs = np.max(f_bar) * np.sqrt(n)

    rng = np.random.default_rng(seed=seed)
    f_max_bs = np.empty(n_bootstrap, dtype=np.float64)
    for b in range(n_bootstrap):
        idx = _stationary_bootstrap_indices(n, block_length, rng)
        sample = excess[idx]
        f_bar_bs = sample.mean(axis=0) - f_bar  # center
        f_max_bs[b] = np.max(f_bar_bs) * np.sqrt(n)
    p_value = float((f_max_bs >= f_max_obs).mean())
    best_idx = int(np.argmax(f_bar))
    return {
        "best_rule": list(rule_returns.keys())[best_idx],
        "best_rule_excess_mean": float(f_bar[best_idx]),
        "p_value_reality_check": p_value,
        "n_bootstrap": int(n_bootstrap),
        "n_obs": int(n),
    }


def holm_sidak_correction(p_values: list[float], alpha: float = 0.05) -> list[bool]:
    """Holm-Šidák step-down family-wise α correction.

    Returns list[bool] of reject decisions, same order as input p_values.
    """
    n = len(p_values)
    arr = np.asarray(p_values, dtype=np.float64)
    sorted_idx = np.argsort(arr)
    sorted_p = arr[sorted_idx]
    rejected = np.zeros(n, dtype=bool)
    for i in range(n):
        m = n - i
        if m < 1:
            break
        alpha_i = 1.0 - (1.0 - alpha) ** (1.0 / m)
        if np.isfinite(sorted_p[i]) and sorted_p[i] < alpha_i:
            rejected[sorted_idx[i]] = True
        else:
            break  # step-down stops
    return rejected.tolist()


def bootstrap_sharpe_ci(
    returns: pd.Series, n_bootstrap: int = 10_000, block_length: int = 6,
    seed: int = 42, alpha: float = 0.05, ann_factor: float = 12.0,
) -> tuple[float, float, float]:
    """Stationary bootstrap CI for the annualized Sharpe ratio."""
    arr = returns.dropna().to_numpy(dtype=np.float64)
    n = len(arr)
    if n < 24:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed=seed)
    sharpes = np.empty(n_bootstrap, dtype=np.float64)
    for b in range(n_bootstrap):
        idx = _stationary_bootstrap_indices(n, block_length, rng)
        sample = arr[idx]
        sd = sample.std(ddof=1)
        if sd == 0 or not np.isfinite(sd):
            sharpes[b] = np.nan
        else:
            sharpes[b] = sample.mean() / sd * np.sqrt(ann_factor)
    sharpes = sharpes[np.isfinite(sharpes)]
    if len(sharpes) == 0:
        return float("nan"), float("nan"), float("nan")
    point_sd = arr.std(ddof=1)
    point = float(arr.mean() / point_sd * np.sqrt(ann_factor)) if point_sd > 0 else float("nan")
    lo = float(np.percentile(sharpes, 100.0 * alpha / 2))
    hi = float(np.percentile(sharpes, 100.0 * (1.0 - alpha / 2)))
    return point, lo, hi


def bootstrap_diff_ci(
    r1: pd.Series, r2: pd.Series, n_bootstrap: int = 10_000, block_length: int = 6,
    seed: int = 42, alpha: float = 0.05, ann_factor: float = 12.0,
) -> tuple[float, float, float]:
    """Stationary bootstrap CI for Sharpe(r2) - Sharpe(r1) using paired resampling."""
    df = pd.concat([r1.rename("r1"), r2.rename("r2")], axis=1).dropna()
    arr = df.to_numpy(dtype=np.float64)
    n = len(arr)
    if n < 24:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed=seed)
    diffs = np.empty(n_bootstrap, dtype=np.float64)
    for b in range(n_bootstrap):
        idx = _stationary_bootstrap_indices(n, block_length, rng)
        sample = arr[idx]
        sd1 = sample[:, 0].std(ddof=1)
        sd2 = sample[:, 1].std(ddof=1)
        if sd1 == 0 or sd2 == 0 or not np.isfinite(sd1) or not np.isfinite(sd2):
            diffs[b] = np.nan
        else:
            sr1 = sample[:, 0].mean() / sd1 * np.sqrt(ann_factor)
            sr2 = sample[:, 1].mean() / sd2 * np.sqrt(ann_factor)
            diffs[b] = sr2 - sr1
    diffs = diffs[np.isfinite(diffs)]
    if len(diffs) == 0:
        return float("nan"), float("nan"), float("nan")
    sd1 = arr[:, 0].std(ddof=1)
    sd2 = arr[:, 1].std(ddof=1)
    if sd1 == 0 or sd2 == 0:
        return float("nan"), float("nan"), float("nan")
    point = float(arr[:, 1].mean() / sd2 - arr[:, 0].mean() / sd1) * float(np.sqrt(ann_factor))
    lo = float(np.percentile(diffs, 100.0 * alpha / 2))
    hi = float(np.percentile(diffs, 100.0 * (1.0 - alpha / 2)))
    return point, lo, hi


def build_v2_statistical_tests_table(
    combo_monthly_returns: pd.Series,
    v2_returns_by_rule: dict[str, pd.Series],
    benchmark: pd.Series | None = None,
    out_path: Path | None = None,
    n_bootstrap: int = 10_000,
    block_length: int = 6,
    seed: int = 42,
) -> pd.DataFrame:
    """Build v2_statistical_tests.csv.

    Columns:
      rule, jk_sharpe_diff, jk_p_value, reality_check_p, holm_sidak_reject,
      bootstrap_ci_low, bootstrap_ci_high, passes_falsifiability.

    Falsifiability per pre-registration §3.3: REJECT (do not pass) if
    Sharpe_diff < 0.05 AND MaxDD-improvement < 3pp. We compute only the
    Sharpe and CI here; the MaxDD-improvement falsifiability is added by
    the caller (it requires the MaxDD series alignment).
    """
    if benchmark is None:
        benchmark = combo_monthly_returns

    rc = whites_reality_check(
        benchmark,
        v2_returns_by_rule,
        n_bootstrap=n_bootstrap,
        block_length=block_length,
        seed=seed,
    )

    # Compute per-rule JK + bootstrap CI.
    rule_rows: list[dict[str, object]] = []
    p_values: list[float] = []
    for rule_name, r_v2 in v2_returns_by_rule.items():
        jk = jobson_korkie_test(combo_monthly_returns, r_v2)
        point, ci_lo, ci_hi = bootstrap_diff_ci(
            combo_monthly_returns, r_v2,
            n_bootstrap=n_bootstrap, block_length=block_length, seed=seed,
        )
        rule_rows.append({
            "rule": rule_name,
            "sharpe_v1": jk["sharpe_v1"],
            "sharpe_v2": jk["sharpe_v2"],
            "jk_sharpe_diff": jk["sharpe_diff"],
            "jk_p_value": jk["p_value"],
            "reality_check_p": rc["p_value_reality_check"] if rule_name == rc["best_rule"] else float("nan"),
            "bootstrap_diff_point": point,
            "bootstrap_ci_low": ci_lo,
            "bootstrap_ci_high": ci_hi,
            "n_obs": jk["n_obs"],
            "passes_falsifiability_sharpe": bool(np.isfinite(jk["sharpe_diff"]) and jk["sharpe_diff"] >= 0.05),
        })
        p_values.append(jk["p_value"] if np.isfinite(jk["p_value"]) else 1.0)

    # Holm-Šidák step-down.
    rejected = holm_sidak_correction(p_values, alpha=0.05)
    for i, row in enumerate(rule_rows):
        row["holm_sidak_reject"] = bool(rejected[i])
    df = pd.DataFrame(rule_rows)

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
    return df


__all__ = [
    "jobson_korkie_test",
    "whites_reality_check",
    "holm_sidak_correction",
    "bootstrap_sharpe_ci",
    "bootstrap_diff_ci",
    "build_v2_statistical_tests_table",
]
