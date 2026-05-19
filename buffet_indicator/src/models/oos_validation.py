"""Out-of-sample validation: Goyal-Welch (2008) R^2_OOS and Clark-West (2007) MSPE-adj."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def _align(z: pd.Series, r_fwd: pd.Series) -> pd.DataFrame:
    aligned = pd.concat([z, r_fwd], axis=1).dropna()
    aligned.columns = ["z", "r"]
    return aligned


def goyal_welch_oos_r2(
    z: pd.Series,
    r_fwd: pd.Series,
    train_fraction: float = 0.5,
    min_train: int = 60,
) -> dict[str, Any]:
    """Goyal-Welch (2008) out-of-sample R^2.

    ``R^2_OOS = 1 - MSE_model / MSE_benchmark`` where benchmark is the
    prevailing mean. Returns NaN if the OOS window is too short.
    """
    import statsmodels.api as sm

    aligned = _align(z, r_fwd)
    T = len(aligned)
    t_split = max(int(T * train_fraction), min_train)
    if T - t_split < 30:
        return {
            "r2_oos": float("nan"),
            "n_oos_obs": int(max(0, T - t_split)),
            "mse_model": float("nan"),
            "mse_benchmark": float("nan"),
            "oos_start_date": None,
        }

    z_arr = aligned["z"].to_numpy(dtype="float64")
    r_arr = aligned["r"].to_numpy(dtype="float64")
    mse_m_num = 0.0
    mse_b_num = 0.0

    for s in range(t_split, T - 1):
        X = sm.add_constant(z_arr[: s + 1])
        y = r_arr[: s + 1]
        model = sm.OLS(y, X).fit()
        pred = float(model.params[0] + model.params[1] * z_arr[s + 1])
        bench = float(y.mean())
        actual = float(r_arr[s + 1])
        mse_m_num += (actual - pred) ** 2
        mse_b_num += (actual - bench) ** 2

    n_oos = T - 1 - t_split
    mse_m = mse_m_num / n_oos
    mse_b = mse_b_num / n_oos
    r2_oos = 1.0 - mse_m / mse_b if mse_b > 0 else float("nan")
    return {
        "r2_oos": float(r2_oos),
        "n_oos_obs": int(n_oos),
        "mse_model": float(mse_m),
        "mse_benchmark": float(mse_b),
        "oos_start_date": aligned.index[t_split + 1],
    }


def clark_west(
    z: pd.Series, r_fwd: pd.Series, train_fraction: float = 0.5, min_train: int = 60
) -> dict[str, Any]:
    """Clark-West (2007) MSPE-adjusted statistic for nested forecast comparison.

    Tests whether the predictive model (with z) beats the prevailing-mean
    benchmark. Returns one-sided p-value (large positive CW statistic favors
    the predictive model). Reference: Clark & West (2007) J. Econometrics 138.
    """
    import statsmodels.api as sm

    aligned = _align(z, r_fwd)
    T = len(aligned)
    t_split = max(int(T * train_fraction), min_train)
    if T - t_split < 30:
        return {
            "cw_stat": float("nan"),
            "p_value": float("nan"),
            "n_oos_obs": int(max(0, T - t_split)),
        }

    z_arr = aligned["z"].to_numpy(dtype="float64")
    r_arr = aligned["r"].to_numpy(dtype="float64")
    f_t: list[float] = []
    for s in range(t_split, T - 1):
        X = sm.add_constant(z_arr[: s + 1])
        y = r_arr[: s + 1]
        model = sm.OLS(y, X).fit()
        pred_model = float(model.params[0] + model.params[1] * z_arr[s + 1])
        pred_bench = float(y.mean())
        actual = float(r_arr[s + 1])
        # f_t = (actual - bench)^2 - (actual - pred)^2 + (bench - pred)^2
        f_val = (
            (actual - pred_bench) ** 2
            - (actual - pred_model) ** 2
            + (pred_bench - pred_model) ** 2
        )
        f_t.append(f_val)

    arr = np.asarray(f_t, dtype="float64")
    n = len(arr)
    if n < 2 or arr.std(ddof=1) == 0:
        return {
            "cw_stat": float("nan"),
            "p_value": float("nan"),
            "n_oos_obs": int(n),
        }
    cw_stat = float(np.sqrt(n) * arr.mean() / arr.std(ddof=1))
    # One-sided p-value (alternative: CW > 0).
    p_value = float(1.0 - stats.norm.cdf(cw_stat))
    return {
        "cw_stat": cw_stat,
        "p_value": p_value,
        "n_oos_obs": int(n),
    }


__all__ = ["goyal_welch_oos_r2", "clark_west"]
