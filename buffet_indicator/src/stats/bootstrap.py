"""Stationary block bootstrap helpers — DRAFT_v4 §3.8 (seal 2a94417).

References
----------
- Sealed pre-reg §3.8: stationary block bootstrap, 50K immutable, seeded.
- Sealed pre-reg §11.1 lines 733 (``stationary_bootstrap_ci``) and 741
  (``choose_stationary_block_length``).
- ``arch.bootstrap.optimal_block_length`` returns a DataFrame with
  ``stationary`` and ``circular`` columns; pre-reg requires the
  ``stationary`` column.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BootstrapResult:
    """Stationary block bootstrap result with byte-identical determinism.

    Attributes
    ----------
    ci_lower : float
        Lower bound of the bootstrap CI.
    ci_upper : float
        Upper bound of the bootstrap CI.
    n_bootstrap_used : int
        Number of bootstrap replications actually run (must equal 50_000
        for verdict-bearing quantities; see §3.8 invariant).
    block_length : int
        Block length used for the stationary bootstrap.
    block_length_source : str
        Either ``"stationary_optimal"`` or ``"fallback_2_n_third_root"``.
    seed_hex : str
        Hex digest of the ``np.random.SeedSequence`` entropy used.
    """

    ci_lower: float
    ci_upper: float
    n_bootstrap_used: int
    block_length: int
    block_length_source: str
    seed_hex: str


def stationary_bootstrap_ci(
    data,
    *,
    n_bootstrap: int,
    seed: int,
) -> BootstrapResult:
    """Compute a stationary block bootstrap confidence interval.

    Determinism: two runs with the same ``seed`` MUST produce byte-identical
    output (per §3.8 invariant). ``n_bootstrap`` MUST be 50_000 for any
    verdict-bearing quantity (§3.8 + §11.3 invariant #10).

    Parameters
    ----------
    data : array-like
        1-D sequence of observations.
    n_bootstrap : int
        Number of bootstrap replications (keyword-only).
    seed : int
        Seed for ``np.random.SeedSequence`` (keyword-only).

    Returns
    -------
    BootstrapResult

    References
    ----------
    Sealed pre-reg §3.8 + §11.1 line 733. Tests: ``T09``, ``T19``.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )


def choose_stationary_block_length(x: np.ndarray) -> int:
    """Pick the stationary-bootstrap block length per §3.8.

    Wraps ``arch.bootstrap.optimal_block_length(x)`` and returns
    ``int(ceil(result["stationary"].iloc[0]))`` (the "stationary" column,
    NOT "circular" — see Codex round-3 New-1 correction).

    Parameters
    ----------
    x : np.ndarray
        1-D float array of observations.

    Returns
    -------
    int
        Block length (rounded up).

    References
    ----------
    Sealed pre-reg §3.8 + §11.1 line 741. Test: ``T08``.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
