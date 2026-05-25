"""Bootstrap policy (50K immutable) — DRAFT_v4 §3.8 + §11.3 (seal 2a94417).

References
----------
- Sealed pre-reg §3.8 + §11.3 invariant #10: ``n_bootstrap = 50_000`` is
  IMMUTABLE for all verdict-bearing quantities. No runtime-based downsample.
- Sealed pre-reg §11.1 line 742: function signature.
"""
from __future__ import annotations

from dataclasses import dataclass


VERDICT_N_BOOTSTRAP: int = 50_000
"""Sealed-immutable bootstrap count for verdict-bearing CIs (§3.8 / §11.3)."""

DIAGNOSTIC_N_BOOTSTRAP: int = 50_000
"""Default diagnostic count; equal to verdict count to avoid divergence in
verdict-vs-diagnostic CI reporting. Diagnostic-only callers may pass a
smaller ``n_bootstrap`` directly to :func:`stationary_bootstrap_ci`, but
the policy still pins 50K as the canonical reference number.
"""


@dataclass(frozen=True)
class BootstrapPolicy:
    """Immutable bootstrap-count policy.

    Attributes
    ----------
    verdict_count : int
        Bootstrap reps for verdict-bearing CIs. MUST be 50_000.
    diagnostic_count : int
        Bootstrap reps for diagnostic-only outputs (sealed-canonical 50_000;
        diagnostic-only callers may opt to a lower count via direct
        ``stationary_bootstrap_ci(..., n_bootstrap=...)``).
    runtime_downsample_permitted : bool
        MUST be False (§3.8 / §11.3 invariant). No "runtime_exceeded"
        downsample reason is permitted for verdict-bearing quantities.
    """

    verdict_count: int
    diagnostic_count: int
    runtime_downsample_permitted: bool


def load_bootstrap_policy() -> BootstrapPolicy:
    """Return the canonical bootstrap policy per §3.8 + §11.3.

    Returns
    -------
    BootstrapPolicy
        With ``verdict_count == 50_000``, ``diagnostic_count == 50_000``,
        and ``runtime_downsample_permitted is False``.

    References
    ----------
    Sealed pre-reg §3.8 + §11.3 + §11.1 line 742. Test: ``T19``.
    """
    return BootstrapPolicy(
        verdict_count=VERDICT_N_BOOTSTRAP,
        diagnostic_count=DIAGNOSTIC_N_BOOTSTRAP,
        runtime_downsample_permitted=False,
    )


VALID_BOOTSTRAP_PURPOSES: frozenset[str] = frozenset({"verdict", "diagnostic", "test"})
"""Phase F-BLK1.E: enum of permitted purposes for bootstrap call-sites.

- ``"verdict"`` (default): n_bootstrap MUST equal :data:`VERDICT_N_BOOTSTRAP`.
- ``"diagnostic"``: configurable n_bootstrap for non-verdict-bearing outputs
  (e.g., ``outputs/diagnostics/<session>/...``).
- ``"test"``: configurable n_bootstrap for unit/integration tests.
"""


def ensure_verdict_n_bootstrap(n_bootstrap: int, purpose: str) -> None:
    """Phase F-BLK1.E: gate verdict-bearing bootstrap calls to n_bootstrap=50_000.

    Per sealed §3.8 + §11.3 invariant #10: ``n_bootstrap = 50_000`` is
    IMMUTABLE for all verdict-bearing quantities. Pre-BLK1 the CLI accepted
    arbitrary ``--n-bootstrap`` overrides and downstream sweeps propagated
    them into verdict cells (Codex Round 5 MAJOR CR-3).

    Raises
    ------
    ValueError
        If ``purpose == "verdict"`` and ``n_bootstrap != VERDICT_N_BOOTSTRAP``,
        or if ``purpose`` is not in :data:`VALID_BOOTSTRAP_PURPOSES`.
    """
    if purpose not in VALID_BOOTSTRAP_PURPOSES:
        raise ValueError(
            f"purpose must be one of {sorted(VALID_BOOTSTRAP_PURPOSES)}; "
            f"got {purpose!r}"
        )
    if purpose == "verdict" and int(n_bootstrap) != int(VERDICT_N_BOOTSTRAP):
        raise ValueError(
            f"verdict-bearing run requires n_bootstrap={VERDICT_N_BOOTSTRAP} "
            f"(sealed §3.8 IMMUTABLE); got n_bootstrap={n_bootstrap}. "
            f"Use purpose='diagnostic' or 'test' for non-verdict call paths."
        )
