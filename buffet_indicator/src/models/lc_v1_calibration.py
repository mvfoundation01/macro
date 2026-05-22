"""LC v1.0 calibration layer (Session 7 §2.G).

Implements per master spec §3.9:

* **Brier score + Murphy (1973) decomposition** for binary tail-event forecasts:
  ``BS = Reliability − Resolution + Uncertainty``.
* **Reliability diagram** with Wilson confidence bands.
* **Probability Integral Transform (PIT)** test for continuous forward-return
  forecast calibration — Diebold-Gunther-Tay (1998).
* **CRPS (Continuous Ranked Probability Score)** for Gaussian forecasts —
  Gneiting-Raftery (2007) closed-form.
* **Logarithmic (Ignorance) score** — Good (1952).

Reference list
--------------
* Murphy, A.H. (1973), J. Applied Meteorology 12(4) pp. 595-600.
* Diebold, F.X., Gunther, T.A. & Tay, A.S. (1998), International Economic
  Review 39(4) pp. 863-883.
* Gneiting, T. & Raftery, A.E. (2007), JASA 102(477) pp. 359-378.
* Good, I.J. (1952), JRSS-B 14(1) pp. 107-114.
* specs/MV_LIQUIDITY_COMPOSITE_PREREGISTER.md (a8635ef) §3.8 (backtest split).
* prompt/052226/PROMPT_v11_3_session_7_DECISIONS_investigation_F_G.md §2.G.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import kstest, norm  # type: ignore[import-untyped]


# ---------------------------------------------------------------------------
# Brier score + Murphy (1973) decomposition
# ---------------------------------------------------------------------------


@dataclass
class BrierDecomposition:
    """Murphy (1973) decomposition of the Brier score."""
    brier_score: float
    reliability: float
    resolution: float
    uncertainty: float
    n_bins_used: int
    bin_edges: np.ndarray
    bin_centers: np.ndarray
    observed_freqs_per_bin: np.ndarray
    n_per_bin: np.ndarray


def compute_brier_decomposition(
    forecast_probs: np.ndarray,
    realized_outcomes: np.ndarray,
    n_bins: int = 10,
) -> BrierDecomposition:
    """Murphy (1973) decomposition: ``BS = Reliability − Resolution + Uncertainty``.

    Parameters
    ----------
    forecast_probs : np.ndarray
        Shape (T,) — predicted probabilities (in [0, 1]) at each date.
    realized_outcomes : np.ndarray
        Shape (T,) — 0/1 indicators of actual events.
    n_bins : int
        Number of forecast-probability bins (default 10 ⇒ deciles).

    Returns
    -------
    BrierDecomposition

    Reference
    ---------
    Murphy, A.H. (1973), J. Applied Meteorology 12(4) pp. 595-600.
    """
    p = np.asarray(forecast_probs, dtype=float)
    y = np.asarray(realized_outcomes, dtype=float)
    if p.shape != y.shape:
        raise ValueError(f"shape mismatch: p={p.shape} y={y.shape}")
    if len(p) == 0:
        raise ValueError("empty input")
    n = len(p)

    brier_score = float(np.mean((p - y) ** 2))
    base_rate = float(np.mean(y))
    uncertainty = float(base_rate * (1.0 - base_rate))

    # Bin forecasts into n_bins equal-probability quantile bins (or fewer if
    # the forecast probabilities are clustered).
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_idx = np.digitize(p, bin_edges[1:-1], right=False)

    observed_freqs = np.full(n_bins, np.nan)
    n_per_bin = np.zeros(n_bins, dtype=int)
    forecast_means = np.full(n_bins, np.nan)
    for b in range(n_bins):
        mask = bin_idx == b
        n_b = int(mask.sum())
        n_per_bin[b] = n_b
        if n_b > 0:
            observed_freqs[b] = float(y[mask].mean())
            forecast_means[b] = float(p[mask].mean())

    valid = n_per_bin > 0
    n_used = int(valid.sum())

    if n_used == 0:
        reliability = float("nan")
        resolution = float("nan")
    else:
        # Reliability = (1/N) Σ_b n_b · (f_b − o_b)²
        reliability = float(
            np.sum(
                n_per_bin[valid] * (forecast_means[valid] - observed_freqs[valid]) ** 2
            ) / n
        )
        # Resolution = (1/N) Σ_b n_b · (o_b − ō)²
        resolution = float(
            np.sum(n_per_bin[valid] * (observed_freqs[valid] - base_rate) ** 2) / n
        )

    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    return BrierDecomposition(
        brier_score=brier_score,
        reliability=reliability,
        resolution=resolution,
        uncertainty=uncertainty,
        n_bins_used=n_used,
        bin_edges=bin_edges,
        bin_centers=bin_centers,
        observed_freqs_per_bin=observed_freqs,
        n_per_bin=n_per_bin,
    )


def wilson_interval(
    successes: int, n: int, alpha: float = 0.05,
) -> tuple[float, float]:
    """Wilson score CI for a binomial proportion.

    Used for the per-bin uncertainty band in the reliability diagram.
    """
    if n == 0:
        return float("nan"), float("nan")
    z = float(norm.ppf(1 - alpha / 2.0))
    p_hat = successes / n
    centre = (p_hat + z * z / (2.0 * n)) / (1.0 + z * z / n)
    half = (
        z * np.sqrt(p_hat * (1.0 - p_hat) / n + z * z / (4.0 * n * n))
        / (1.0 + z * z / n)
    )
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))


# ---------------------------------------------------------------------------
# CRPS (Continuous Ranked Probability Score) for Gaussian forecasts
# ---------------------------------------------------------------------------


def compute_crps(
    forecast_mean: np.ndarray,
    forecast_sd: np.ndarray,
    realized: np.ndarray,
) -> float:
    """CRPS for Gaussian forecasts (Gneiting-Raftery 2007 closed-form).

    .. math::

        CRPS(N(μ, σ²), y) = σ · [ (y-μ)/σ · (2Φ((y-μ)/σ) − 1)
                                + 2φ((y-μ)/σ) − 1/√π ]

    Returns the AVERAGE CRPS across the forecast/realized array. Lower is better.

    Reference: Gneiting & Raftery (2007), JASA 102(477) pp. 359-378.
    """
    mu = np.asarray(forecast_mean, dtype=float)
    sd = np.asarray(forecast_sd, dtype=float)
    y = np.asarray(realized, dtype=float)
    if not (len(mu) == len(sd) == len(y)):
        raise ValueError(
            f"length mismatch: mu={len(mu)} sd={len(sd)} y={len(y)}"
        )
    if len(mu) == 0:
        return float("nan")
    if (sd <= 0).any():
        # Degenerate forecast — fall back to absolute error.
        return float(np.mean(np.abs(y - mu)))
    z = (y - mu) / sd
    crps_t = sd * (z * (2.0 * norm.cdf(z) - 1.0) + 2.0 * norm.pdf(z) - 1.0 / np.sqrt(np.pi))
    return float(np.mean(crps_t))


# ---------------------------------------------------------------------------
# Logarithmic (Ignorance) score for Gaussian forecasts
# ---------------------------------------------------------------------------


def compute_log_score(
    forecast_mean: np.ndarray,
    forecast_sd: np.ndarray,
    realized: np.ndarray,
) -> float:
    """Average logarithmic (Ignorance) score for Gaussian forecasts.

    .. math::

        L̄ = −\\frac{1}{T} Σ_t  log φ((y_t − μ_t)/σ_t) / σ_t

    Lower is better. Reference: Good (1952), JRSS-B 14(1) pp. 107-114.
    """
    mu = np.asarray(forecast_mean, dtype=float)
    sd = np.asarray(forecast_sd, dtype=float)
    y = np.asarray(realized, dtype=float)
    if not (len(mu) == len(sd) == len(y)):
        raise ValueError(
            f"length mismatch: mu={len(mu)} sd={len(sd)} y={len(y)}"
        )
    if len(mu) == 0:
        return float("nan")
    if (sd <= 0).any():
        return float("nan")
    log_dens = norm.logpdf(y, loc=mu, scale=sd)
    return float(-np.mean(log_dens))


# ---------------------------------------------------------------------------
# PIT histogram + K-S test
# ---------------------------------------------------------------------------


@dataclass
class PITResult:
    pit_values: np.ndarray
    histogram_counts: np.ndarray
    histogram_bins: np.ndarray
    ks_pvalue: float
    ks_statistic: float


def compute_pit(
    forecast_mean: np.ndarray,
    forecast_sd: np.ndarray,
    realized: np.ndarray,
    n_bins: int = 10,
) -> PITResult:
    """Probability Integral Transform calibration test.

    For each t, compute ``u_t = Φ((y_t − μ_t)/σ_t)``. Under correct forecast
    distribution, ``u_t`` is iid Uniform(0,1). The K-S test against the
    uniform null is reported as ``ks_pvalue`` — small ⇒ miscalibration.

    Reference: Diebold-Gunther-Tay (1998), Int. Economic Review 39(4).
    """
    mu = np.asarray(forecast_mean, dtype=float)
    sd = np.asarray(forecast_sd, dtype=float)
    y = np.asarray(realized, dtype=float)
    if not (len(mu) == len(sd) == len(y)):
        raise ValueError("length mismatch")
    if len(mu) == 0:
        empty = np.array([], dtype=float)
        bins = np.linspace(0.0, 1.0, n_bins + 1)
        return PITResult(
            pit_values=empty, histogram_counts=np.zeros(n_bins, dtype=int),
            histogram_bins=bins, ks_pvalue=float("nan"),
            ks_statistic=float("nan"),
        )
    if (sd <= 0).any():
        # Degenerate; PIT undefined.
        bins = np.linspace(0.0, 1.0, n_bins + 1)
        return PITResult(
            pit_values=np.array([], dtype=float),
            histogram_counts=np.zeros(n_bins, dtype=int),
            histogram_bins=bins, ks_pvalue=float("nan"),
            ks_statistic=float("nan"),
        )
    pit = norm.cdf((y - mu) / sd)
    ks = kstest(pit, "uniform")
    hist, edges = np.histogram(pit, bins=n_bins, range=(0.0, 1.0))
    return PITResult(
        pit_values=pit,
        histogram_counts=hist,
        histogram_bins=edges,
        ks_pvalue=float(ks.pvalue),
        ks_statistic=float(ks.statistic),
    )


# ---------------------------------------------------------------------------
# Reliability diagram (returns matplotlib Figure object; saving is caller's job)
# ---------------------------------------------------------------------------


def render_reliability_diagram(
    decomp: BrierDecomposition,
    title: str = "",
    *,
    isotonic_overlay: bool = True,
) -> Any:
    """Render a reliability diagram using matplotlib. Returns the Figure.

    The caller is responsible for saving via ``fig.savefig(...)``.

    Includes Wilson confidence band per bin and an optional isotonic
    regression overlay via ``sklearn.isotonic.IsotonicRegression``.
    """
    import matplotlib

    matplotlib.use("Agg")  # non-interactive backend (no display)
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="perfect calibration")

    valid = decomp.n_per_bin > 0
    if valid.any():
        centers = decomp.bin_centers[valid]
        obs = decomp.observed_freqs_per_bin[valid]
        n_b = decomp.n_per_bin[valid]
        sizes = 50.0 + 10.0 * np.sqrt(n_b)

        # Wilson confidence intervals per bin.
        ci_lo = np.empty_like(obs)
        ci_hi = np.empty_like(obs)
        for i, (o, n) in enumerate(zip(obs, n_b)):
            lo, hi = wilson_interval(int(round(o * n)), int(n))
            ci_lo[i] = lo
            ci_hi[i] = hi
        # vlines for the CI band (matplotlib doesn't have a single API for
        # asymmetric per-point bars in a scatter; use errorbar).
        ax.errorbar(
            centers, obs,
            yerr=[obs - ci_lo, ci_hi - obs],
            fmt="o", capsize=3, alpha=0.7, label="observed freq (Wilson 95%)",
        )
        ax.scatter(centers, obs, s=sizes, alpha=0.3)

        if isotonic_overlay and len(centers) >= 2:
            try:
                from sklearn.isotonic import IsotonicRegression  # type: ignore[import-untyped]
                iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
                iso.fit(centers, obs)
                xs = np.linspace(0.0, 1.0, 100)
                ax.plot(xs, iso.predict(xs), "r-", alpha=0.6, label="isotonic fit")
            except Exception:  # nosec B110 - sklearn is optional; skip overlay if unavailable  # pragma: no cover
                pass

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_xlabel("Forecast probability")
    ax.set_ylabel("Observed frequency")
    ax.legend(loc="upper left", fontsize=8)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig


def render_pit_histogram(
    pit_result: PITResult,
    title: str = "",
) -> Any:
    """Render a PIT histogram using matplotlib. Returns the Figure."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4))
    centres = (pit_result.histogram_bins[:-1] + pit_result.histogram_bins[1:]) / 2.0
    width = pit_result.histogram_bins[1] - pit_result.histogram_bins[0]
    ax.bar(centres, pit_result.histogram_counts, width=width * 0.9, alpha=0.6)
    # Uniform null overlay.
    total = int(pit_result.histogram_counts.sum())
    n_bins_real = len(pit_result.histogram_counts)
    if total > 0:
        ax.axhline(total / n_bins_real, color="k", linestyle="--", alpha=0.6,
                   label="uniform null")
    ax.set_xlim(0.0, 1.0)
    ax.set_xlabel("PIT value")
    ax.set_ylabel("count")
    full_title = title
    if np.isfinite(pit_result.ks_pvalue):
        full_title += f"  (K-S p={pit_result.ks_pvalue:.4f})"
    if full_title:
        ax.set_title(full_title)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return fig


__all__ = [
    "BrierDecomposition",
    "PITResult",
    "compute_brier_decomposition",
    "wilson_interval",
    "compute_crps",
    "compute_log_score",
    "compute_pit",
    "render_reliability_diagram",
    "render_pit_histogram",
]
