"""Point-in-time (PIT) z-score per sealed pre-reg §10.1 (seal 2a94417).

This module implements the v2.0-canonical PIT z-score with the sealed
defaults ``min_window=120`` and ``strict_shift=True`` (excludes the
current observation from its own normalization).

Existing implementations in the codebase are **deliberately untouched**:

- ``src/quant_engine/mv_conditional.py::compute_pit_zscore`` (PROMPT_v11_2
  §3.2 semantics, ``min_periods=60``).
- ``src/models/zscore.py::expanding_zscore`` (used by 6+ v1.x call-sites).

v2.0 code imports :func:`pit_zscore` from this module instead.

References
----------
- Sealed pre-reg §10.1: "expanding window, mean + sample SD (Bessel n-1),
  strict PIT excluding current observation; minimum sample threshold
  n >= 120 observations before non-NaN z; all components brought to
  month-end-of-month frequency before z-scoring".
- ``PROMPT_CC_v11_4_v2_sprint_PHASE_B_C_RESUME.md`` §4 Option D1.
"""
from __future__ import annotations

import pandas as pd


def pit_zscore(
    series: pd.Series,
    min_window: int = 120,
    strict_shift: bool = True,
) -> pd.Series:
    """Compute the point-in-time z-score per sealed pre-reg §10.1.

    The window at date ``t`` uses an expanding history of ``series``.
    When ``strict_shift=True`` (per sealed §10.1), the window EXCLUDES
    the observation at ``t`` itself — i.e., ``series.shift(1)`` is used
    so the normalization for ``z[t]`` depends only on observations
    strictly prior to ``t``.

    Parameters
    ----------
    series : pd.Series
        Monthly-frequency input series. The caller is responsible for
        resampling to month-end before z-scoring (sealed §10.1).
    min_window : int, default 120
        Minimum number of observations required in the expanding window
        before a non-NaN z-score is produced. Sealed §10.1 mandates
        ``n >= 120``.
    strict_shift : bool, default True
        If True (sealed §10.1 default), the window at ``t`` is
        ``series.shift(1).expanding(min_periods=min_window)`` — strict
        PIT. If False, the window includes ``t`` itself (less strict;
        only useful for diagnostics).

    Returns
    -------
    pd.Series
        Z-score series aligned with ``series.index``. NaN where the
        expanding window has fewer than ``min_window`` non-NaN
        observations.

    Notes
    -----
    Uses Bessel-corrected (n-1) sample SD per pandas default
    (``Series.std(ddof=1)``), matching sealed §10.1.
    """
    if min_window < 2:
        raise ValueError(
            f"min_window must be at least 2 (Bessel n-1 requires n>=2); got {min_window}"
        )
    if not isinstance(series, pd.Series):
        raise TypeError(f"series must be pd.Series; got {type(series).__name__}")

    shifted = series.shift(1) if strict_shift else series
    mu = shifted.expanding(min_periods=min_window).mean()
    sd = shifted.expanding(min_periods=min_window).std()
    return (shifted - mu) / sd
