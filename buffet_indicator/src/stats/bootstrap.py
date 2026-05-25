"""Stationary block bootstrap helpers — DRAFT_v4 §3.8 (seal 2a94417).

References
----------
- Sealed pre-reg §3.8: stationary block bootstrap, ``n_bootstrap=50_000``
  IMMUTABLE for verdict-bearing CIs, seeded via ``np.random.SeedSequence``.
- Sealed pre-reg §11.1 lines 733 (``stationary_bootstrap_ci``) and 741
  (``choose_stationary_block_length``).
- ``arch.bootstrap.optimal_block_length`` returns a DataFrame with
  ``"stationary"`` and ``"circular"`` columns; pre-reg requires the
  ``"stationary"`` column (Codex round-3 New-1 empirical verification).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

import arch.bootstrap


@dataclass(frozen=True)
class BootstrapResult:
    """Stationary block bootstrap result with byte-identical determinism.

    Attributes
    ----------
    point_estimate : float
        Statistic evaluated on the original data.
    ci_lower : float
        Lower percentile bound of the bootstrap CI.
    ci_upper : float
        Upper percentile bound of the bootstrap CI.
    n_bootstrap_used : int
        Number of bootstrap replications actually run (must equal 50_000
        for verdict-bearing quantities; see §3.8 invariant).
    block_length : int
        Block length used for the stationary bootstrap.
    block_length_source : str
        Either ``"stationary_optimal"`` or ``"fallback_2_n_third_root"``.
    seed_hex : str
        Hex digest of the ``np.random.SeedSequence`` entropy used.
    confidence_level : float
        Two-sided confidence level (e.g. 0.95 for 95% CI).
    not_evaluable_reason : str | None
        ``None`` when the CI is computable; otherwise a short code
        (``"n_lt_30"``, ``"block_gt_n_over_2"``) per §3.8.
    """

    point_estimate: float
    ci_lower: float
    ci_upper: float
    n_bootstrap_used: int
    block_length: int
    block_length_source: str
    seed_hex: str
    confidence_level: float
    not_evaluable_reason: Optional[str]


def choose_stationary_block_length(x: np.ndarray) -> int:
    """Pick the stationary-bootstrap block length per §3.8.

    Wraps ``arch.bootstrap.optimal_block_length(x)`` and returns
    ``int(ceil(result["stationary"].iloc[0]))`` (the "stationary" column,
    NOT "circular" — per Codex round-3 New-1 against installed arch==7.0.0).
    Falls back to ``int(ceil(2 * n ** (1/3)))`` when the library return is
    non-finite or non-positive. Result clamped to ``[1, max(1, n // 2)]``.

    Parameters
    ----------
    x : np.ndarray
        1-D float-coercible array of observations.

    Returns
    -------
    int
        Block length (rounded up, clamped to ``[1, n // 2]``).

    References
    ----------
    Sealed pre-reg §3.8 + §11.1 line 741. Test: ``T08``.
    """
    arr = np.asarray(x, dtype="float64").ravel()
    n = arr.size
    if n < 1:
        raise ValueError("choose_stationary_block_length requires non-empty array")

    obl = arch.bootstrap.optimal_block_length(arr)
    raw = float(obl["stationary"].iloc[0])
    if np.isfinite(raw) and raw > 0:
        block_length = int(np.ceil(raw))
    else:
        block_length = int(np.ceil(2.0 * n ** (1.0 / 3.0)))

    upper = max(1, n // 2)
    return min(max(1, block_length), upper)


def _seedseq_hex(seed: int) -> str:
    """Return a stable hex digest derived from the seed for provenance."""
    ss = np.random.SeedSequence(int(seed))
    state = ss.generate_state(4, dtype=np.uint32)
    return hashlib.sha256(state.tobytes()).hexdigest()[:16]


def _percentile_ci(samples: np.ndarray, level: float) -> tuple[float, float]:
    """Two-sided percentile CI at the given two-sided confidence level."""
    alpha = 1.0 - level
    lo = float(np.percentile(samples, 100.0 * alpha / 2.0))
    hi = float(np.percentile(samples, 100.0 * (1.0 - alpha / 2.0)))
    return lo, hi


def stationary_bootstrap_ci(
    data,
    *,
    n_bootstrap: int,
    seed: int,
    statistic: Optional[Callable] = None,
    confidence_level: float = 0.95,
    block_length: Optional[int] = None,
) -> BootstrapResult:
    """Compute a stationary block bootstrap confidence interval.

    Determinism: two runs with the same ``seed`` (and same ``data``,
    ``n_bootstrap``, ``statistic``) MUST produce byte-identical output
    (per §3.8 invariant). ``n_bootstrap`` MUST be 50_000 for any
    verdict-bearing quantity (§3.8 + §11.3 invariant #10).

    Parameters
    ----------
    data : array-like
        1-D sequence of observations (float-coercible). For per-cell
        regression CIs the caller passes the residual / score series.
    n_bootstrap : int, keyword-only
        Number of bootstrap replications.
    seed : int, keyword-only
        Seed for ``np.random.SeedSequence`` -> ``default_rng``.
    statistic : Callable[[np.ndarray], float], optional
        Function evaluated on each resample. Defaults to ``np.mean``.
    confidence_level : float, default 0.95
        Two-sided percentile level.
    block_length : int, optional
        Block length for the stationary bootstrap. If ``None``, computed
        via :func:`choose_stationary_block_length`.

    Returns
    -------
    BootstrapResult

    References
    ----------
    Sealed pre-reg §3.8 + §11.1 line 733. Tests: ``T09``, ``T19``.
    """
    arr = np.asarray(data, dtype="float64").ravel()
    n = arr.size
    stat_fn: Callable[[np.ndarray], float] = (
        statistic if statistic is not None else (lambda a: float(np.mean(a)))
    )
    seed_hex = _seedseq_hex(seed)

    if block_length is None:
        if n >= 1:
            chosen_bl = choose_stationary_block_length(arr)
            bl_source = "stationary_optimal"
        else:
            chosen_bl = 1
            bl_source = "fallback_2_n_third_root"
    else:
        chosen_bl = int(block_length)
        bl_source = "stationary_optimal"

    # §3.8 not_evaluable gates.
    if n < 30:
        return BootstrapResult(
            point_estimate=float(stat_fn(arr)) if n > 0 else float("nan"),
            ci_lower=float("nan"),
            ci_upper=float("nan"),
            n_bootstrap_used=int(n_bootstrap),
            block_length=int(chosen_bl),
            block_length_source=bl_source,
            seed_hex=seed_hex,
            confidence_level=float(confidence_level),
            not_evaluable_reason="n_lt_30",
        )
    if chosen_bl > n // 2:
        return BootstrapResult(
            point_estimate=float(stat_fn(arr)),
            ci_lower=float("nan"),
            ci_upper=float("nan"),
            n_bootstrap_used=int(n_bootstrap),
            block_length=int(chosen_bl),
            block_length_source=bl_source,
            seed_hex=seed_hex,
            confidence_level=float(confidence_level),
            not_evaluable_reason="block_gt_n_over_2",
        )

    # Deterministic RNG fed into arch.bootstrap.StationaryBootstrap.
    ss = np.random.SeedSequence(int(seed))
    rng = np.random.default_rng(ss)
    bs = arch.bootstrap.StationaryBootstrap(int(chosen_bl), arr, seed=rng)

    samples = np.empty(int(n_bootstrap), dtype="float64")
    for i, (resampled, _) in enumerate(bs.bootstrap(int(n_bootstrap))):
        # arch yields ``(args, kwargs)``; we passed positional ``arr`` so
        # ``resampled[0]`` is the resampled 1-D array.
        samples[i] = float(stat_fn(resampled[0]))

    point = float(stat_fn(arr))
    lo, hi = _percentile_ci(samples, confidence_level)
    return BootstrapResult(
        point_estimate=point,
        ci_lower=lo,
        ci_upper=hi,
        n_bootstrap_used=int(n_bootstrap),
        block_length=int(chosen_bl),
        block_length_source=bl_source,
        seed_hex=seed_hex,
        confidence_level=float(confidence_level),
        not_evaluable_reason=None,
    )
