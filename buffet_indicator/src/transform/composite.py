"""Liquidity Composite v2.0 construction (LC_FULL, LC_TIER2, LC_DEEP).

Per sealed pre-reg §1.1 + §1.2 + §10.1 (seal 2a94417) and
``PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md`` §5.

Three scope-fixed weight schemes:

- ``LC_FULL``  (effective start 2003-01-31): all 5 components.
- ``LC_TIER2`` (effective start 1987-01-31): drops z1 (NetFed); renormalized.
- ``LC_DEEP``  (effective start 1973-01-31): drops z1 and z5; renormalized.

Normalization is **sum-of-absolute-values approximately 1.0**, not
signed-sum-equals-1 (z5's negative weight is preserved as the directional
sign for funding stress).

NaN propagation: at any date where a REQUIRED component (per scope) is
NaN, the composite is NaN. No silent weight reallocation.

Effective-start dates are POLICY: dates before a scope's effective start
are NaN even if the underlying components are non-NaN earlier.
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

Scope = Literal["LC_FULL", "LC_TIER2", "LC_DEEP"]


SCOPE_WEIGHTS: dict[str, dict[str, float]] = {
    "LC_FULL":  {"z1":  0.25,  "z2":  0.20,  "z3":  0.20,  "z4":  0.20,  "z5": -0.15},
    "LC_TIER2": {                "z2":  0.267, "z3":  0.267, "z4":  0.267, "z5": -0.200},
    "LC_DEEP":  {                "z2":  0.333, "z3":  0.333, "z4":  0.333                },
}


SCOPE_EFFECTIVE_START: dict[str, pd.Timestamp] = {
    "LC_FULL":  pd.Timestamp("2003-01-31"),
    "LC_TIER2": pd.Timestamp("1987-01-31"),
    "LC_DEEP":  pd.Timestamp("1973-01-31"),
}


# Sanity check at module load: each scope's weights have Σ|w| ≈ 1.0.
for _scope, _w in SCOPE_WEIGHTS.items():
    _abs_sum = sum(abs(v) for v in _w.values())
    if not (0.99 <= _abs_sum <= 1.01):
        raise AssertionError(
            f"{_scope} weights Σ|w|={_abs_sum:.4f} not within [0.99, 1.01]; "
            f"check SCOPE_WEIGHTS dict"
        )


def build_composite(
    z1: pd.Series | None,
    z2: pd.Series,
    z3: pd.Series,
    z4: pd.Series,
    z5: pd.Series | None,
    *,
    scope: Scope,
) -> pd.Series:
    """Construct the LC v2.0 composite z-score series for the given scope.

    All inputs are PIT z-scores (output of
    :func:`src.transform.pit_zscore.pit_zscore`). Scope-fixed weights and
    effective-start dates are applied per sealed §10.1 + arbitration §5.

    Parameters
    ----------
    z1 : pd.Series | None
        NetFed liquidity z-score. Required for ``LC_FULL``; ignored for
        ``LC_TIER2``/``LC_DEEP`` (may be None).
    z2, z3, z4 : pd.Series
        M2-growth, BankLend-growth, DXY-inverse z-scores. Required by all
        three scopes.
    z5 : pd.Series | None
        Funding-stress z-score. Required for ``LC_FULL`` and ``LC_TIER2``;
        ignored for ``LC_DEEP`` (may be None).
    scope : {"LC_FULL", "LC_TIER2", "LC_DEEP"}, keyword-only.

    Returns
    -------
    pd.Series
        Composite z-score series named ``f"{scope}_composite"``. NaN
        before the scope's effective start and at any date where a
        required component is NaN.

    Raises
    ------
    ValueError
        Unknown ``scope`` or a required component is None for that scope.
    """
    if scope not in SCOPE_WEIGHTS:
        raise ValueError(
            f"unknown scope {scope!r}; expected one of {list(SCOPE_WEIGHTS)}"
        )

    weights = SCOPE_WEIGHTS[scope]
    required = list(weights.keys())

    name_to_series = {"z1": z1, "z2": z2, "z3": z3, "z4": z4, "z5": z5}
    for name in required:
        if name_to_series[name] is None:
            raise ValueError(
                f"scope={scope} requires component {name!r} but None was passed"
            )

    df = pd.concat(
        {name: name_to_series[name] for name in required},
        axis=1,
    )

    any_nan_mask = df[required].isna().any(axis=1)

    composite = pd.Series(np.nan, index=df.index, name=f"{scope}_composite")
    weighted_sum = sum(weights[name] * df[name] for name in required)
    composite.loc[~any_nan_mask] = weighted_sum.loc[~any_nan_mask]

    effective_start = SCOPE_EFFECTIVE_START[scope]
    composite.loc[composite.index < effective_start] = np.nan

    return composite
