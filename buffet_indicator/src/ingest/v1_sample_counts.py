"""Recompute v1.0 realized OOS sample counts — DRAFT_v4 §10.3 footnote (seal 2a94417).

References
----------
- Sealed pre-reg §10.3 footnote: deferred ``n_obs_oos`` recomputation
  for the 12 (composite x horizon) cells. The v1.0 sealed pre-reg and
  verdict.json reported sample counts on an in-sample basis
  (``n_obs_insample``); v2.0 §3.4 gate uses an OOS basis (``n_obs_oos``).
  This function reads v1.0's sealed regression table at the given git ref
  and returns a per-cell schema-correct DataFrame for downstream
  recomputation by the Phase E verdict writer.
- Sealed pre-reg §11.1 line 738: function signature.
"""
from __future__ import annotations

import io
import subprocess
from pathlib import Path
from typing import Optional

import pandas as pd


V1_REGRESSION_TABLE_PATH: str = (
    "buffet_indicator/outputs/tables/lc_v1_predictive_regression.csv"
)


class V1SampleCountsLoadError(RuntimeError):
    """Raised when the v1.0 regression CSV cannot be loaded via git show."""


def _repo_root() -> Path:
    """Locate the repo root by walking up until a ``.git`` directory is found."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".git").exists():
            return parent
    return here.parents[3]


def _read_csv_at_ref(ref: str, path: str, root: Path) -> Optional[pd.DataFrame]:
    """``git show ref:path`` and parse as CSV. Returns None on error."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "show", f"{ref}:{path}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    try:
        return pd.read_csv(io.StringIO(proc.stdout))
    except (ValueError, pd.errors.ParserError):
        return None


def collect_v1_realized_sample_counts(
    ref: str = "spec/liquidity-composite-v1.0",
) -> pd.DataFrame:
    """Recompute the realized OOS sample counts for the v1.0 sealed cells.

    Reads the v1.0 sealed regression table at the given git ref
    (``buffet_indicator/outputs/tables/lc_v1_predictive_regression.csv``)
    and produces a per-cell schema-correct DataFrame.

    .. note::
        v1.0's CSV exposes ``n_obs_insample`` and ``oos_split_date`` only.
        Computing the v2.0 ``s + h <= t`` ``n_obs_oos`` requires the v1.0
        composite panel and the v1.0 data cutoff. Until the v1.0 panel
        builder is wired into the v2.0 sprint as a dependency (Phase E
        verdict writer task), this function returns ``n_obs_oos`` as
        ``NaN`` with ``recomputation_status="deferred"``. The schema is
        otherwise valid and consumable by the Phase E writer; callers
        treat deferred rows as ``not_evaluable`` per §10.3 footnote.

    Parameters
    ----------
    ref : str, default ``"spec/liquidity-composite-v1.0"``
        Git ref (branch/tag/SHA) at which to read v1.0 artifacts.

    Returns
    -------
    pd.DataFrame
        Columns: ``composite``, ``horizon_months``, ``n_obs_insample``,
        ``n_obs_oos`` (NaN if deferred), ``oos_split_date`` (string ISO),
        ``recomputation_status`` (``"deferred"`` or ``"computed"``),
        ``evaluable_v2`` (bool — False when deferred).

    Raises
    ------
    V1SampleCountsLoadError
        If the v1.0 regression CSV cannot be loaded at ``ref``.

    References
    ----------
    Sealed pre-reg §10.3 footnote + §11.1 line 738.
    """
    root = _repo_root()
    df = _read_csv_at_ref(ref, V1_REGRESSION_TABLE_PATH, root)
    if df is None:
        raise V1SampleCountsLoadError(
            f"could not load {V1_REGRESSION_TABLE_PATH!r} at ref {ref!r}; "
            "verify the v1.0 branch / tag is present and the path is correct."
        )

    required = {"scope", "horizon_years", "n_obs_insample", "oos_split_date"}
    missing = required - set(df.columns)
    if missing:
        raise V1SampleCountsLoadError(
            f"v1.0 CSV missing required columns: {sorted(missing)!r}"
        )

    out_rows = []
    for _, row in df.iterrows():
        composite = str(row["scope"])
        horizon_years = int(row["horizon_years"])
        horizon_months = horizon_years * 12
        n_obs_insample = int(row["n_obs_insample"])
        oos_split_date = str(row["oos_split_date"])
        out_rows.append(
            {
                "composite": composite,
                "horizon_months": horizon_months,
                "n_obs_insample": n_obs_insample,
                "n_obs_oos": float("nan"),
                "oos_split_date": oos_split_date,
                "recomputation_status": "deferred",
                "evaluable_v2": False,
            }
        )

    return pd.DataFrame(out_rows)
