"""LC v1.0 composite construction (3 scopes) per sealed pre-reg a8635ef §1.1 + §1.2.

Three composite scopes — DO NOT MODIFY the weights without an amendment to
the sealed pre-registration:

* ``LC_FULL``  = +0.250·z₁ + 0.200·z₂ + 0.200·z₃ + 0.200·z₄ − 0.150·z₅
                (5 components; active from 2003-01)
* ``LC_TIER2`` = +0.267·z₂ + 0.267·z₃ + 0.267·z₄ − 0.200·z₅
                (drops z₁ NetFed; active from 1987-01)
* ``LC_DEEP``  = +0.333·z₂ + 0.333·z₃ + 0.333·z₄
                (drops z₁ and z₅; active from 1973-01)

The orchestrator :func:`build_lc_v1_composites` writes
``outputs/lc_v1_composites.parquet`` after re-validating the pre-reg ancestor
invariant (spec §0.1 HARD REJECTION).

References
----------
* specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.1 — LC_FULL weights.
* specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §1.2 — TIER2/DEEP scopes.
* prompt/052226/PROMPT_v11_3_stage_3_LC_v1_session_6.md §2.D.
"""
from __future__ import annotations

import json
import subprocess  # nosec B404 - used for trusted git commands only
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from src.config import OUTPUTS_DIR, PROJECT_ROOT
from src.ingest._base import utcnow


# ---------------------------------------------------------------------------
# Sealed weights (pre-reg a8635ef §1.1 + §1.2)
# ---------------------------------------------------------------------------

#: LC_FULL weights — sum of absolute weights = 1.000 exactly.
LC_FULL_WEIGHTS: dict[str, float] = {
    "z1": 0.250,
    "z2": 0.200,
    "z3": 0.200,
    "z4": 0.200,
    "z5": -0.150,
}

#: LC_TIER2 weights — drops z₁; sum of |w| = 0.267·3 + 0.200 = 1.001 ≈ 1.000.
LC_TIER2_WEIGHTS: dict[str, float] = {
    "z2": 0.267,
    "z3": 0.267,
    "z4": 0.267,
    "z5": -0.200,
}

#: LC_DEEP weights — drops z₁ and z₅; sum of |w| = 0.333·3 = 0.999 ≈ 1.000.
LC_DEEP_WEIGHTS: dict[str, float] = {
    "z2": 0.333,
    "z3": 0.333,
    "z4": 0.333,
}

#: Active-from dates per pre-reg §1.2.
LC_FULL_ACTIVE_FROM = pd.Timestamp("2003-01-01")
LC_TIER2_ACTIVE_FROM = pd.Timestamp("1987-01-01")
LC_DEEP_ACTIVE_FROM = pd.Timestamp("1973-01-01")

#: Sealed pre-reg commit hash (specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md).
PRE_REG_COMMIT = "a8635ef"

#: Composite spec version.
COMPOSITE_VERSION = "v1.0"

#: Output parquet path under OUTPUTS_DIR.
COMPOSITES_PARQUET_FILENAME = "lc_v1_composites.parquet"


# ---------------------------------------------------------------------------
# Pre-reg ancestor check (spec §0.1 HARD GATE)
# ---------------------------------------------------------------------------


def _verify_pre_reg_ancestor(
    pre_reg_commit: str = PRE_REG_COMMIT,
    repo_root: Path = PROJECT_ROOT,
) -> str:
    """Verify ``pre_reg_commit`` is an ancestor of HEAD.

    Per master spec §0.1, any LC artifact written before the pre-reg commit's
    git timestamp is HARD-REJECTED. Equivalently, we require the pre-reg
    commit to be an ANCESTOR of HEAD before writing artifacts.

    Returns
    -------
    str
        The current HEAD SHA-1.

    Raises
    ------
    RuntimeError
        If the ancestor check fails or git is not available.
    """
    try:
        result = subprocess.run(  # nosec B603 B607
            ["git", "merge-base", "--is-ancestor", pre_reg_commit, "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(
            f"Pre-reg ancestor check: git invocation failed ({exc!r})"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"Pre-reg invariant VIOLATED: {pre_reg_commit} is not an ancestor "
            f"of HEAD. Spec §0.1 HARD REJECTION — refuse to write composite parquet."
        )
    sha = subprocess.run(  # nosec B603 B607
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        capture_output=True, text=True,
        check=True,
    ).stdout.strip()
    return sha


# ---------------------------------------------------------------------------
# Composite formulas
# ---------------------------------------------------------------------------


def compute_lc_full(
    z1: pd.Series,
    z2: pd.Series,
    z3: pd.Series,
    z4: pd.Series,
    z5: pd.Series,
) -> pd.Series:
    """LC_FULL = +0.250·z₁ + 0.200·z₂ + 0.200·z₃ + 0.200·z₄ − 0.150·z₅.

    Active from 2003-01. NaN where any component is NaN.
    """
    aligned = pd.concat(
        [z1.rename("z1"), z2.rename("z2"), z3.rename("z3"),
         z4.rename("z4"), z5.rename("z5")],
        axis=1, join="outer",
    )
    lc = (
        LC_FULL_WEIGHTS["z1"] * aligned["z1"]
        + LC_FULL_WEIGHTS["z2"] * aligned["z2"]
        + LC_FULL_WEIGHTS["z3"] * aligned["z3"]
        + LC_FULL_WEIGHTS["z4"] * aligned["z4"]
        + LC_FULL_WEIGHTS["z5"] * aligned["z5"]
    )
    lc[aligned.index < LC_FULL_ACTIVE_FROM] = np.nan
    lc.name = "LC_FULL"
    return lc


def compute_lc_tier2(
    z2: pd.Series,
    z3: pd.Series,
    z4: pd.Series,
    z5: pd.Series,
) -> pd.Series:
    """LC_TIER2 = +0.267·z₂ + 0.267·z₃ + 0.267·z₄ − 0.200·z₅.

    Drops z₁ NetFed. Active from 1987-01. NaN where any component is NaN.
    """
    aligned = pd.concat(
        [z2.rename("z2"), z3.rename("z3"), z4.rename("z4"), z5.rename("z5")],
        axis=1, join="outer",
    )
    lc = (
        LC_TIER2_WEIGHTS["z2"] * aligned["z2"]
        + LC_TIER2_WEIGHTS["z3"] * aligned["z3"]
        + LC_TIER2_WEIGHTS["z4"] * aligned["z4"]
        + LC_TIER2_WEIGHTS["z5"] * aligned["z5"]
    )
    lc[aligned.index < LC_TIER2_ACTIVE_FROM] = np.nan
    lc.name = "LC_TIER2"
    return lc


def compute_lc_deep(
    z2: pd.Series,
    z3: pd.Series,
    z4: pd.Series,
) -> pd.Series:
    """LC_DEEP = +0.333·z₂ + 0.333·z₃ + 0.333·z₄.

    Drops z₁ and z₅. Active from 1973-01. NaN where any component is NaN.
    """
    aligned = pd.concat(
        [z2.rename("z2"), z3.rename("z3"), z4.rename("z4")],
        axis=1, join="outer",
    )
    lc = (
        LC_DEEP_WEIGHTS["z2"] * aligned["z2"]
        + LC_DEEP_WEIGHTS["z3"] * aligned["z3"]
        + LC_DEEP_WEIGHTS["z4"] * aligned["z4"]
    )
    lc[aligned.index < LC_DEEP_ACTIVE_FROM] = np.nan
    lc.name = "LC_DEEP"
    return lc


# ---------------------------------------------------------------------------
# Orchestrator: assemble + write parquet
# ---------------------------------------------------------------------------


def assemble_composites_frame(
    z1: pd.Series,
    z2: pd.Series,
    z3: pd.Series,
    z4: pd.Series,
    z5: pd.Series,
) -> pd.DataFrame:
    """Compute all 3 composite scopes and return as a DataFrame.

    Output schema:

    ============  ====================  =================================
    Column        Dtype                 Semantics
    ============  ====================  =================================
    ``date``      datetime64[ns] index  Monthly EOM, UTC-naive, sorted asc
    ``LC_FULL``   float64               NaN before 2003-01
    ``LC_TIER2``  float64               NaN before 1987-01
    ``LC_DEEP``   float64               NaN before 1973-01
    ============  ====================  =================================
    """
    lc_full = compute_lc_full(z1, z2, z3, z4, z5)
    lc_tier2 = compute_lc_tier2(z2, z3, z4, z5)
    lc_deep = compute_lc_deep(z2, z3, z4)

    full_idx = lc_full.index.union(lc_tier2.index).union(lc_deep.index).sort_values()
    df = pd.DataFrame(
        {
            "LC_FULL": lc_full.reindex(full_idx),
            "LC_TIER2": lc_tier2.reindex(full_idx),
            "LC_DEEP": lc_deep.reindex(full_idx),
        },
        index=full_idx,
    )
    df.index.name = "date"
    return df[["LC_FULL", "LC_TIER2", "LC_DEEP"]].sort_index()


def write_composites_parquet(
    df: pd.DataFrame,
    *,
    output_path: Path | None = None,
    enforce_pre_reg: bool = True,
    repo_root: Path = PROJECT_ROOT,
) -> Path:
    """Write the composite DataFrame to parquet with pre-reg metadata.

    File-level metadata block (per master spec §2.4.3):

    * ``pre_reg_commit``    — ``a8635ef``
    * ``composite_version`` — ``v1.0``
    * ``build_timestamp_utc`` — ISO-8601 UTC at write time
    * ``head_sha``          — current git HEAD SHA at write time
    * ``weights_full``, ``weights_tier2``, ``weights_deep`` — JSON dicts

    Parameters
    ----------
    df : pd.DataFrame
        Output of :func:`assemble_composites_frame`.
    output_path : Path, optional
        Override the default ``OUTPUTS_DIR / COMPOSITES_PARQUET_FILENAME``.
    enforce_pre_reg : bool
        If True (default), verify ``a8635ef`` is an ancestor of HEAD before
        writing. Set False only in synthetic-data unit tests that run
        outside a git working tree.
    repo_root : Path
        Used for the ancestor check; tests may override.

    Returns
    -------
    Path
        The on-disk path of the written parquet.
    """
    output_path = output_path or (OUTPUTS_DIR / COMPOSITES_PARQUET_FILENAME)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    head_sha = ""
    if enforce_pre_reg:
        head_sha = _verify_pre_reg_ancestor(repo_root=repo_root)

    build_ts = pd.Timestamp(utcnow()).isoformat()

    table = pa.Table.from_pandas(df, preserve_index=True)
    existing_meta = table.schema.metadata or {}
    new_meta = {
        **existing_meta,
        b"pre_reg_commit": PRE_REG_COMMIT.encode(),
        b"composite_version": COMPOSITE_VERSION.encode(),
        b"build_timestamp_utc": build_ts.encode(),
        b"head_sha": head_sha.encode(),
        b"weights_full": json.dumps(LC_FULL_WEIGHTS).encode(),
        b"weights_tier2": json.dumps(LC_TIER2_WEIGHTS).encode(),
        b"weights_deep": json.dumps(LC_DEEP_WEIGHTS).encode(),
        b"spec_section": b"a8635ef MV_LIQUIDITY_COMPOSITE_PREREGISTER.md sec 1.1+1.2",
    }
    table = table.replace_schema_metadata(new_meta)

    # Atomic write: .tmp → rename per master spec §2.4.4 step 6.
    tmp = output_path.with_suffix(".parquet.tmp")
    pq.write_table(table, tmp, compression="snappy")
    import os
    os.replace(tmp, output_path)
    return output_path


def read_composites_metadata(path: Path | None = None) -> dict[str, str]:
    """Read back the file-level metadata block from the composites parquet.

    Returns a dict with string values (bytes decoded as utf-8). Used by tests
    and by downstream code that wants to verify the pre-reg pedigree of a
    composite file on disk.
    """
    path = path or (OUTPUTS_DIR / COMPOSITES_PARQUET_FILENAME)
    meta = pq.read_metadata(path).schema.to_arrow_schema().metadata or {}
    return {
        (k.decode() if isinstance(k, bytes) else k):
            (v.decode() if isinstance(v, bytes) else v)
        for k, v in meta.items()
    }


def build_lc_v1_composites(
    *,
    z1: pd.Series,
    z2: pd.Series,
    z3: pd.Series,
    z4: pd.Series,
    z5: pd.Series,
    output_path: Path | None = None,
    enforce_pre_reg: bool = True,
    repo_root: Path = PROJECT_ROOT,
) -> tuple[pd.DataFrame, Path]:
    """One-shot orchestrator: compute composites + write parquet with metadata.

    Returns ``(dataframe, parquet_path)``.
    """
    df = assemble_composites_frame(z1=z1, z2=z2, z3=z3, z4=z4, z5=z5)
    path = write_composites_parquet(
        df,
        output_path=output_path,
        enforce_pre_reg=enforce_pre_reg,
        repo_root=repo_root,
    )
    return df, path


__all__ = [
    "LC_FULL_WEIGHTS",
    "LC_TIER2_WEIGHTS",
    "LC_DEEP_WEIGHTS",
    "LC_FULL_ACTIVE_FROM",
    "LC_TIER2_ACTIVE_FROM",
    "LC_DEEP_ACTIVE_FROM",
    "PRE_REG_COMMIT",
    "COMPOSITE_VERSION",
    "COMPOSITES_PARQUET_FILENAME",
    "compute_lc_full",
    "compute_lc_tier2",
    "compute_lc_deep",
    "assemble_composites_frame",
    "write_composites_parquet",
    "read_composites_metadata",
    "build_lc_v1_composites",
]
