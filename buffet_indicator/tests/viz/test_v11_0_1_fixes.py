"""v11.0.1 — Part 1 fix gate tests:

- Stage A: P(< 5% 10Y CAGR) label/computation
- Stage B: P(<RF), P(<5%), P(>7%) per-horizon columns populated
- Stage C: Bootstrap reps ≥ 10,000
- Stage D: AIC parametric overlay on cond-dist chart
- Stage E: direction convention registered
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Stage A — headline pill label
# ---------------------------------------------------------------------------


def test_header_pill_label_says_5pct_10y_cagr() -> None:
    text = Path("src/viz/templates/_header.html").read_text(encoding="utf-8")
    assert "P(&lt; 5% 10Y CAGR)" in text or "P(< 5% 10Y CAGR)" in text


def test_dashboard_has_5pct_pill_label() -> None:
    p = Path("outputs/dashboard.html")
    if not p.exists():
        pytest.skip("dashboard.html not built")
    text = p.read_text(encoding="utf-8")
    assert "P(&lt; 5% 10Y CAGR)" in text


# ---------------------------------------------------------------------------
# Stage B — per-horizon probability columns
# ---------------------------------------------------------------------------


def test_macro_chart_payload_has_per_horizon_events() -> None:
    """Macro chart payload should include lt_0pct/lt_rf/lt_5pct/gt_7pct events
    per indicator per horizon."""
    from src.config import TV_SPXTR
    from src.ingest.csv_loader import load_tradingview_file
    from src.ingest.shiller_loader import load_shiller
    from src.transform.forward_returns import build_forward_returns
    from src.viz.build_macro_charts import build_macro_chart_payload

    sh = load_shiller()
    spxtr_ts = load_tradingview_file(TV_SPXTR, expected_frequency="D")
    fr = build_forward_returns(
        sh, spxtr_ts.data["close"], check_continuity=False
    )
    zh = pd.read_parquet("outputs/charts/z_history.parquet")
    payload = build_macro_chart_payload(fr, z_history=zh)
    charts = payload["macro_variant_charts"]
    sample = charts.get("cs_hy_master") or {}
    ph = sample.get("per_horizon_events", {})
    assert ph, "per_horizon_events missing on cs_hy_master"
    # Each horizon should have all 4 events.
    for h_label, evs in ph.items():
        for ev_key in ("lt_0pct", "lt_rf", "lt_5pct", "gt_7pct"):
            assert ev_key in evs, f"{h_label} missing event {ev_key}"
            assert "point" in evs[ev_key]


def test_probability_table_no_em_dash_for_p5_p7() -> None:
    """Dashboard HTML should NOT render '—' in macro tab probability rows
    for P(<5%) and P(>7%); they should show real percentages now."""
    p = Path("outputs/dashboard.html")
    if not p.exists():
        pytest.skip("dashboard.html not built")
    text = p.read_text(encoding="utf-8")
    # Find a macro tab's probability table section and check.
    # We check the cs_hy_master tab (always present, full sample 1996+).
    start = text.find('data-tab="cs_hy_master"')
    end = text.find('</section>', start)
    section = text[start:end]
    assert section, "cs_hy_master section not found"
    # The macro tab should have at least one real % number in the probability
    # area (not all '—').
    import re
    pct_matches = re.findall(r"(\d{1,3})%", section)
    assert len(pct_matches) >= 4, (
        f"only {len(pct_matches)} percent values in cs_hy_master section"
    )


# ---------------------------------------------------------------------------
# Stage C — bootstrap ≥ 10,000
# ---------------------------------------------------------------------------


def test_compute_p_event_default_reps_at_least_10000() -> None:
    import inspect
    from src.viz.build_macro_charts import _compute_p_event_at_horizon
    sig = inspect.signature(_compute_p_event_at_horizon)
    n_default = sig.parameters["n_bootstrap"].default
    assert n_default >= 10_000, f"default n_bootstrap = {n_default}"


# ---------------------------------------------------------------------------
# Stage D — AIC parametric overlay
# ---------------------------------------------------------------------------


def test_cond_dist_has_parametric_fit_trace() -> None:
    """make_conditional_distribution should add a second trace (parametric
    fit curve) when given ≥ 12 samples."""
    from src.viz.chart_specs import make_conditional_distribution
    rng = np.random.default_rng(42)
    data = rng.normal(0.08, 0.05, 80).tolist()
    spec = make_conditional_distribution(data, title="Test")
    assert len(spec["data"]) >= 2, (
        "expected ≥ 2 traces (histogram + parametric)"
    )
    # The second trace should be a smooth scatter line, not another histogram.
    trace2 = spec["data"][1]
    assert trace2.get("type") == "scatter"
    assert trace2.get("mode") == "lines"


def test_cond_dist_subtitle_mentions_fit_family() -> None:
    from src.viz.chart_specs import make_conditional_distribution
    rng = np.random.default_rng(42)
    data = rng.normal(0.08, 0.05, 80).tolist()
    spec = make_conditional_distribution(data, title="Test")
    title = spec["layout"]["title"]["text"]
    # Best-fit family annotation must appear in the title.
    assert "Best fit:" in title or "AIC" in title


# ---------------------------------------------------------------------------
# Stage E — direction convention
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant", (
    "yc_10y3m", "yc_10y2y", "cs_hy_master", "cs_ig_master",
    "cs_hy_bb", "cs_hy_ccc", "margin_debt_growth", "mrc",
))
def test_variant_registry_has_direction_convention(variant: str) -> None:
    from src.viz.data_extraction import VARIANT_REGISTRY
    meta = VARIANT_REGISTRY.get(variant)
    assert meta and "direction_convention" in meta


def test_credit_spreads_flagged_contrarian() -> None:
    from src.viz.data_extraction import VARIANT_REGISTRY
    for v in ("cs_hy_master", "cs_ig_master", "cs_hy_bb", "cs_hy_ccc"):
        assert VARIANT_REGISTRY[v]["direction_convention"] == "contrarian"


def test_yield_curves_and_margin_debt_flagged_trend() -> None:
    from src.viz.data_extraction import VARIANT_REGISTRY
    for v in ("yc_10y3m", "yc_10y2y", "margin_debt_growth"):
        assert VARIANT_REGISTRY[v]["direction_convention"] == "trend"


def test_classify_regime_contrarian_high_z_green() -> None:
    """Contrarian indicator at z=+2 should show GREEN (above-average
    forward returns, contrarian buy)."""
    from src.viz.build_macro_charts import _classify_regime
    label, color = _classify_regime(2.0, convention="contrarian")
    assert "Stressed" in label
    # Green palette (master spec): #5DBB63 / #1B7A3E
    assert color in ("#5DBB63", "#1B7A3E")


def test_classify_regime_contrarian_low_z_red() -> None:
    """Contrarian indicator at z=-2 should show RED (below-average forward
    returns, complacency)."""
    from src.viz.build_macro_charts import _classify_regime
    label, color = _classify_regime(-2.0, convention="contrarian")
    assert "Tight" in label
    # Red/orange palette.
    assert color in ("#C8102E", "#E87722")


def test_classify_regime_trend_high_z_red() -> None:
    """Trend indicator at z=+2 should still show RED (bearish equities)."""
    from src.viz.build_macro_charts import _classify_regime
    label, color = _classify_regime(2.0, convention="trend")
    assert "Overvalued" in label
    assert color in ("#C8102E", "#E87722")
