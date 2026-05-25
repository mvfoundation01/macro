"""§11.2 T15 — HARD GATE ancestor + detached + preseal + shallow.
DRAFT_v4 §0.3 + §8.2 (seal 2a94417). PRIORITY-FIRST.

Passing this test lifts seal report §16 success criterion #6 from
DEFERRED to PASS.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from src.stats.hard_gate import (  # noqa: E402
    HardGateIndeterminate,
    HardGateViolation,
    assert_prereg_ancestor,
)

_SEAL_COMMIT = "2a94417524e67c7b88cb05ad1ac61fafd6b5711a"


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run git in ``cwd`` with check=True; return CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )


def _make_repo(path: Path) -> None:
    """Initialize a clean local git repo at ``path``."""
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q", "-b", "main"], cwd=path)
    _git(["config", "user.email", "test@example.invalid"], cwd=path)
    _git(["config", "user.name", "Test User"], cwd=path)
    _git(["config", "commit.gpgsign", "false"], cwd=path)


def _commit(path: Path, fname: str, content: str, msg: str) -> str:
    """Write ``fname`` with ``content`` and commit; return commit SHA."""
    (path / fname).write_text(content, encoding="utf-8")
    _git(["add", fname], cwd=path)
    _git(["commit", "-q", "-m", msg], cwd=path)
    return _git(["rev-parse", "HEAD"], cwd=path).stdout.strip()


def test_hard_gate_handles_ancestor_detached_preseal_and_shallow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover sealed §11.2 T15 in four sub-cases.

    1. **ancestor**  — real ``D:\\macro`` repo + real seal commit ->
       returns ``None`` (passes the gate).
    2. **detached**  — sibling branch off a common ancestor (HEAD is not
       a descendant of the synthetic "seal") -> ``HardGateViolation``.
    3. **preseal**   — HEAD is an ancestor of the synthetic "seal":
       * ``allow_preseal=False`` (default) -> ``HardGateViolation``.
       * ``allow_preseal=True``           -> returns ``None``.
    4. **shallow**   — shallow clone -> ``HardGateIndeterminate``.

    Also asserts ``sealed=False`` is a no-op even when the SHA is unknown.

    References: DRAFT_v4 §0.3 + §8.2 + sealed pre-reg §11.2 T15.
    """
    # -------------------------------------------------------------------------
    # Sub-case 1: ancestor (real seal commit, real D:\macro repo).
    # -------------------------------------------------------------------------
    monkeypatch.chdir(_ROOT)
    pre = subprocess.run(
        ["git", "merge-base", "--is-ancestor", _SEAL_COMMIT, "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert pre.returncode == 0, (
        "precondition: real seal commit must be an ancestor of HEAD"
    )
    assert assert_prereg_ancestor(_SEAL_COMMIT, sealed=True) is None

    # Dev-mode no-op: sealed=False -> None regardless of input.
    assert assert_prereg_ancestor("0" * 40, sealed=False) is None

    # -------------------------------------------------------------------------
    # Sub-case 2: detached (sibling branch).
    # -------------------------------------------------------------------------
    repo_det = tmp_path / "detached"
    _make_repo(repo_det)
    sha_A = _commit(repo_det, "a.txt", "A", "commit A")
    sha_B = _commit(repo_det, "b.txt", "B", "commit B (synthetic seal)")
    # branch from A, add C; HEAD = C, which is not a descendant of B.
    _git(["checkout", "-q", "-b", "feature", sha_A], cwd=repo_det)
    sha_C = _commit(repo_det, "c.txt", "C", "commit C (sibling of B)")
    assert sha_C != sha_B  # sanity
    monkeypatch.chdir(repo_det)
    with pytest.raises(HardGateViolation):
        assert_prereg_ancestor(sha_B, sealed=True)

    # -------------------------------------------------------------------------
    # Sub-case 3: preseal (HEAD is ancestor of seal).
    # -------------------------------------------------------------------------
    repo_pre = tmp_path / "preseal"
    _make_repo(repo_pre)
    sha_pA = _commit(repo_pre, "a.txt", "A", "commit A")
    sha_pB = _commit(repo_pre, "b.txt", "B", "commit B (synthetic seal)")
    # Move HEAD back to A (preseal state) via detached checkout.
    _git(["checkout", "-q", sha_pA], cwd=repo_pre)
    monkeypatch.chdir(repo_pre)
    with pytest.raises(HardGateViolation):
        assert_prereg_ancestor(sha_pB, sealed=True)
    # Explicit allow_preseal=True -> accepted.
    assert assert_prereg_ancestor(
        sha_pB, sealed=True, allow_preseal=True
    ) is None

    # -------------------------------------------------------------------------
    # Sub-case 4: shallow clone.
    # -------------------------------------------------------------------------
    repo_src = tmp_path / "shallow_src"
    _make_repo(repo_src)
    _commit(repo_src, "1.txt", "1", "c1")
    sha_top = _commit(repo_src, "2.txt", "2", "c2 (synthetic seal)")
    repo_shallow = tmp_path / "shallow_clone"
    # Use file:// URL so --depth shallow semantics apply on local source.
    clone = subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--depth",
            "1",
            "--no-local",
            repo_src.as_uri(),
            str(repo_shallow),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if clone.returncode != 0:
        pytest.skip(f"shallow-clone setup unavailable: {clone.stderr.strip()}")
    # Verify the clone is actually shallow.
    sh_check = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=str(repo_shallow),
        capture_output=True,
        text=True,
        check=True,
    )
    assert sh_check.stdout.strip() == "true", "clone unexpectedly not shallow"
    monkeypatch.chdir(repo_shallow)
    with pytest.raises(HardGateIndeterminate):
        # ``sha_top`` happens to be the only commit in the shallow clone, but
        # policy forbids certifying any shallow repo regardless.
        assert_prereg_ancestor(sha_top, sealed=True)
