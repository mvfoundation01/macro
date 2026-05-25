"""Sample-size evaluability gate (§3.4) — DRAFT_v4 §3.4 (seal 2a94417).

References
----------
- Sealed pre-reg §3.4: evaluability gate formula
  ``n_obs_oos >= max(60, 3 * hac_lag) AND n_eff >= 30``.
- Sealed pre-reg §11.1 line 730: function signature.
"""
from __future__ import annotations

from typing import Literal


def sample_gate_status(
    n_obs_oos: int,
    hac_lag: int,
    n_eff: float,
) -> Literal["evaluable", "not_evaluable"]:
    """Decide whether a (composite x horizon) cell is statistically evaluable.

    Per §3.4 the cell is ``evaluable`` iff
    ``n_obs_oos >= max(60, 3 * hac_lag) AND n_eff >= 30`` (strict ``<``
    on either boundary yields ``not_evaluable``).

    Parameters
    ----------
    n_obs_oos : int
        Number of out-of-sample observations (post forecast origin).
    hac_lag : int
        Newey-West HAC lag from :func:`compute_hac_lag`.
    n_eff : float
        Effective sample size after autocorrelation deflation.

    Returns
    -------
    Literal["evaluable", "not_evaluable"]

    References
    ----------
    Sealed pre-reg §3.4 + §11.1 line 730. Tests: ``T02``, ``T03``.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
