"""Recompute v1.0 realized OOS sample counts — DRAFT_v4 §10.3 footnote (seal 2a94417).

References
----------
- Sealed pre-reg §10.3 footnote: deferred ``n_obs_oos`` recomputation
  for the 12 (composite x horizon) cells, called from the v2.0 sprint
  to lift the ``<NOT_EVALUABLE_WITHOUT_OOS_N>`` placeholders.
- Sealed pre-reg §11.1 line 738: function signature.
"""
from __future__ import annotations

import pandas as pd


def collect_v1_realized_sample_counts(
    ref: str = "spec/liquidity-composite-v1.0",
) -> pd.DataFrame:
    """Recompute the realized OOS sample counts for the v1.0 sealed cells.

    Reads the v1.0 sealed verdict + tables at the given git ref and
    recomputes per-cell ``n_obs_oos`` using the v2.0 ``s + h <= t`` rule
    (§3.4). Used to replace the ``_insample`` proxy in §10.3 column 3.

    Parameters
    ----------
    ref : str, default ``"spec/liquidity-composite-v1.0"``
        Git ref (branch/tag/SHA) at which to read v1.0 artifacts.

    Returns
    -------
    pd.DataFrame
        Columns: ``composite``, ``horizon_months``, ``n_obs_oos``,
        ``oos_split_date``, ``evaluable`` (per v2.0 §3.4 gate).

    References
    ----------
    Sealed pre-reg §10.3 footnote + §11.1 line 738.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
