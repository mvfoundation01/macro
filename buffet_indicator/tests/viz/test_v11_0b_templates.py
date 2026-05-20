"""v11.0b tests for the 8 new macro-indicator tab templates."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape


TEMPLATE_DIR = Path("src/viz/templates")
NEW_TAB_KEYS = (
    "yc_10y3m",
    "yc_10y2y",
    "cs_hy_master",
    "cs_ig_master",
    "cs_hy_bb",
    "cs_hy_ccc",
    "margin_debt_growth",
    "mrc",
)


@pytest.fixture(scope="module")
def env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _stub_variant(key: str) -> dict:
    return {
        "regime": "Fair Value",
        "regime_color": "#9AA0A6",
        "z_fmt": "+0.42",
        "p_neg_fmt": "12%",
        "p_neg_ci_fmt": "[5%, 19%]",
        "confidence_fmt": "60%",
        "conviction_fmt": "2.3",
        "interpretation": {
            "why_it_matters": "Stub interpretation copy for the template smoke test.",
            "panel_a": "Stub panel-A interpretation.",
        },
        "regression_rows": [
            {
                "horizon_label": "1Y",
                "beta_fmt": "-0.03",
                "se_hh_fmt": "0.01",
                "t_hh_fmt": "-2.1",
                "p_fmt": "0.04",
                "r2_in_fmt": "0.05",
                "r2_oos_fmt": "0.02",
                "n_obs": 240,
                "conviction_fmt": "2.3",
            }
        ],
        "probability_rows": [
            {
                "horizon_label": "1Y",
                "p_neg_fmt": "12%",
                "p_neg_ci_fmt": "[5%, 19%]",
                "p_below_rf_fmt": "45%",
                "p_below_5_fmt": "35%",
                "p_above_7_fmt": "40%",
            }
        ],
        "mrc_variants": [
            {
                "scheme_label": "Equal weight",
                "z_fmt": "+0.42",
                "p_neg_fmt": "12%",
                "p_neg_ci_fmt": "[5%, 19%]",
                "confidence_fmt": "60%",
                "conviction_fmt": "2.3",
            }
        ],
        "cross_composite_current": {
            "quadrant_label": "High Valuation × Low Stress",
            "mean_ret_fmt": "+8.9%",
            "n_months": 77,
        },
    }


# ---------------------------------------------------------------------------
# 1) Each template renders without error against synthetic data
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", NEW_TAB_KEYS)
def test_template_renders_without_error(key: str, env: Environment) -> None:
    tmpl_path = TEMPLATE_DIR / f"tab_{key}.html"
    assert tmpl_path.exists(), f"missing template {tmpl_path}"
    tmpl = env.get_template(f"tab_{key}.html")
    html = tmpl.render(variants={key: _stub_variant(key)})
    assert isinstance(html, str) and len(html) > 200
    assert "[object Object]" not in html


@pytest.mark.parametrize("key", NEW_TAB_KEYS)
def test_template_handles_missing_variant(key: str, env: Environment) -> None:
    """Template should gracefully render an empty-state placeholder."""
    tmpl = env.get_template(f"tab_{key}.html")
    html = tmpl.render(variants={})
    assert "No data" in html


# ---------------------------------------------------------------------------
# 2) Each template includes the required 9 sections (regex markers)
# ---------------------------------------------------------------------------


# Match section header pattern (h3 / h2 boldly named one of the 9 sections, OR an HTML comment marker).
SECTION_MARKERS = (
    re.compile(r"<!-- 1\. Header strip", re.I),
    re.compile(r"<!-- 2\. Hero chart", re.I),
    re.compile(r"<!-- 3\. Three-panel block", re.I),
    re.compile(r"<!-- 4\. Horizon selector pills", re.I),
    re.compile(r"<!-- 5\. Predictive regression", re.I),
    re.compile(r"<!-- 6\. Conditional distribution", re.I),
    re.compile(r"<!-- 7\. Probability table", re.I),
    re.compile(r"<!-- 8\. Interpretation", re.I),
    re.compile(r"<!-- 9\. About", re.I),
)


@pytest.mark.parametrize("key", NEW_TAB_KEYS)
def test_template_contains_nine_required_sections(key: str) -> None:
    text = (TEMPLATE_DIR / f"tab_{key}.html").read_text(encoding="utf-8")
    for i, pat in enumerate(SECTION_MARKERS, start=1):
        assert pat.search(text), f"tab_{key}.html missing section {i}"


# ---------------------------------------------------------------------------
# 3) MRC tab contains the C.3 special elements
# ---------------------------------------------------------------------------


def test_mrc_tab_has_cross_variant_table() -> None:
    text = (TEMPLATE_DIR / "tab_mrc.html").read_text(encoding="utf-8")
    assert "MRC weighting variants" in text
    assert "{% for row in v.mrc_variants %}" in text


def test_mrc_tab_has_constituent_contribution_chart() -> None:
    text = (TEMPLATE_DIR / "tab_mrc.html").read_text(encoding="utf-8")
    assert 'id="mrc-constituent-bars"' in text
    assert "Constituent contributions" in text


def test_mrc_tab_has_correlation_heatmap() -> None:
    text = (TEMPLATE_DIR / "tab_mrc.html").read_text(encoding="utf-8")
    assert 'id="mrc-corr-heatmap"' in text
    assert "rolling 60-month correlation" in text


def test_mrc_tab_has_pca_scree_plot() -> None:
    text = (TEMPLATE_DIR / "tab_mrc.html").read_text(encoding="utf-8")
    assert 'id="mrc-pca-scree"' in text
    assert "variance explained" in text.lower()


def test_mrc_tab_has_cross_composite_quadrant_chart() -> None:
    text = (TEMPLATE_DIR / "tab_mrc.html").read_text(encoding="utf-8")
    assert 'id="mrc-cross-composite"' in text
    assert "Cross-composite quadrant" in text


# ---------------------------------------------------------------------------
# 4) Hero chart container present
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", NEW_TAB_KEYS)
def test_template_has_hero_chart_container(key: str) -> None:
    text = (TEMPLATE_DIR / f"tab_{key}.html").read_text(encoding="utf-8")
    assert f'id="hero-chart-{key}"' in text


# ---------------------------------------------------------------------------
# 5) NBER recession overlay relied on chart-spec infrastructure (no direct
#    template work needed — but verify the data_tab_group attribute is set
#    so the dashboard JS can route active group highlighting).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", NEW_TAB_KEYS)
def test_template_has_macro_risk_group_attribute(key: str) -> None:
    text = (TEMPLATE_DIR / f"tab_{key}.html").read_text(encoding="utf-8")
    assert 'data-tab-group="macro_risk"' in text
