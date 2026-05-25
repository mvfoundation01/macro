"""Sample-size evaluability gate (§3.4) — DRAFT_v4 §3.4 + §3.9 (seal 2a94417).

References
----------
- Sealed pre-reg §3.4 (Amendment 4): evaluability gate formula
  ``n_obs_oos < max(60, 3 * hac_lag) OR n_eff < 30 -> not_evaluable``
  (strict ``<`` on either boundary; ``n_obs_oos == 60`` / ``n_eff == 30.0``
  are evaluable per §3.9 comparator table).
- Sealed pre-reg §11.1 line 730: function signature.
"""
from __future__ import annotations

import math
from typing import Literal


N_OBS_OOS_FLOOR: int = 60
"""Minimum n_obs_oos for evaluability (§3.4 / §3.9): n_obs_oos == 60 -> evaluable."""

N_EFF_FLOOR: float = 30.0
"""Minimum n_eff for evaluability (§3.4 / §3.9): n_eff == 30.0 -> evaluable."""


def sample_gate_status(
    n_obs_oos: int,
    hac_lag: int,
    n_eff: float,
) -> Literal["evaluable", "not_evaluable"]:
    """Decide whether a (composite x horizon) cell is statistically evaluable.

    Per §3.4 (Amendment 4) the cell is ``evaluable`` iff::

        n_obs_oos >= max(60, 3 * hac_lag) AND n_eff >= 30.0

    Strict ``<`` is used on the §3.4 inequalities per §3.9 comparator
    table; boundary cases (``n_obs_oos == 60``, ``n_eff == 30.0``) are
    ``evaluable``.

    Parameters
    ----------
    n_obs_oos : int
        Number of out-of-sample observations (post forecast origin).
    hac_lag : int
        Newey-West HAC lag from :func:`compute_hac_lag` (non-negative).
    n_eff : float
        Effective sample size after autocorrelation deflation.

    Returns
    -------
    Literal["evaluable", "not_evaluable"]

    References
    ----------
    Sealed pre-reg §3.4 + §3.9 + §11.1 line 730. Tests: ``T02``, ``T03``.
    """
    if not math.isfinite(float(n_eff)):
        return "not_evaluable"
    required_n_obs = max(N_OBS_OOS_FLOOR, 3 * int(hac_lag))
    if int(n_obs_oos) < required_n_obs:
        return "not_evaluable"
    if float(n_eff) < N_EFF_FLOOR:
        return "not_evaluable"
    return "evaluable"
