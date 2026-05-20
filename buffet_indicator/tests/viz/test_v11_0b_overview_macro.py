"""v11.0b tests for the Overview tab's Macro Risk Snapshot section."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.models.macro_orchestrator import classify_quadrant


TEMPLATE_DIR = Path("src/viz/templates")


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _stub_overview_ctx() -> dict:
    return {
        "asof_label": "2026-05-31",
        "regime_color": "#E87722",
        "regime_label": "Overvalued",
        "mvci_z_fmt": "+1.79",
        "p_below5_fmt": "65%",
        "confidence_fmt": "82%",
        "conviction_fmt": "3.8",
        "hero_interpretation": {
            "what_this_shows": "x", "how_to_read": "y", "current_reading": "z",
        },
        "why_mvci": "stub",
        "overview_cards": [],
        "xv_mean_z_fmt": "+1.5",
        "xv_agreement_fmt": "0.85",
        "xv_combined_regime": "Overvalued",
        "xv_same_sign": "Yes",
        "interpretation_narrative": "stub narrative",
        "interpretation_code": "OV_AGREE",
        "macro_risk_snapshot": {
            "regime": "Fair Value",
            "regime_color": "#9AA0A6",
            "z_fmt": "-0.47",
            "p_neg_fmt": "12%",
            "p_neg_ci_fmt": "[5%, 19%]",
            "confidence_fmt": "60%",
            "conviction_fmt": "2.3",
            "quadrant": "high_val_low_stress",
            "quadrant_label": "High Valuation × Low Stress",
            "mean_forward_ret_fmt": "+8.9%",
            "quadrant_n_months": 77,
            "corr_fmt": "+0.16",
            "top_contributors": [
                {"variant_key": "margin_debt_growth",
                 "label": "Margin Debt 12M Growth",
                 "abs_z_fmt": "1.60", "z_fmt": "+1.60"},
                {"variant_key": "cs_ig_master",
                 "label": "IG OAS (master)",
                 "abs_z_fmt": "1.40", "z_fmt": "-1.40"},
                {"variant_key": "cs_hy_bb",
                 "label": "HY BB OAS",
                 "abs_z_fmt": "1.16", "z_fmt": "-1.16"},
            ],
        },
    }


def test_overview_template_renders_with_macro_section() -> None:
    env = _env()
    tmpl = env.get_template("tab_overview.html")
    html = tmpl.render(**_stub_overview_ctx())
    assert "Macro Risk Snapshot" in html


def test_overview_includes_cross_composite_mini_chart() -> None:
    env = _env()
    tmpl = env.get_template("tab_overview.html")
    html = tmpl.render(**_stub_overview_ctx())
    assert 'id="overview-cross-composite-mini"' in html


def test_overview_quadrant_indicator_present_and_highlights_active() -> None:
    env = _env()
    tmpl = env.get_template("tab_overview.html")
    html = tmpl.render(**_stub_overview_ctx())
    # All 4 quadrant cells should exist.
    assert "High Val &times; High Stress" in html
    assert "High Val &times; Low Stress" in html
    assert "Low Val &times; High Stress" in html
    assert "Low Val &times; Low Stress" in html
    # The active one (high_val_low_stress) should be highlighted.
    assert "bg-orange-50 border-orange-300 font-semibold" in html


def test_overview_top_3_contributors_listed() -> None:
    env = _env()
    tmpl = env.get_template("tab_overview.html")
    html = tmpl.render(**_stub_overview_ctx())
    assert "Top 3 macro-risk contributors" in html
    assert "Margin Debt 12M Growth" in html
    assert "IG OAS (master)" in html
    assert "HY BB OAS" in html


def test_classify_quadrant_matches_template_logic() -> None:
    # Sanity: the same quadrant labels used in the template come from
    # classify_quadrant() in the orchestrator. (Synthetic edge cases.)
    assert classify_quadrant(2.0, 1.5) == "high_val_high_stress"
    assert classify_quadrant(1.8, -0.5) == "high_val_low_stress"
    assert classify_quadrant(-0.5, 1.2) == "low_val_high_stress"
    assert classify_quadrant(-2.0, -1.5) == "low_val_low_stress"


def test_overview_omits_macro_section_when_data_absent() -> None:
    """If macro_risk_snapshot is None / absent, the Macro section disappears."""
    env = _env()
    tmpl = env.get_template("tab_overview.html")
    ctx = _stub_overview_ctx()
    ctx["macro_risk_snapshot"] = None
    html = tmpl.render(**ctx)
    assert "Macro Risk Snapshot" not in html
