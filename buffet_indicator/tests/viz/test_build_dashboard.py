"""Unit tests for src.viz.build_dashboard (Spec v8a section 10.1, V8A6-V8A11)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.viz.build_dashboard import build_dashboard


def _write_minimal_headline(p: Path) -> None:
    payload = {
        "headline": {
            "asof": "2026-05-31",
            "view": "descriptive",
            "interpretation": {
                "narrative_code": "MIXED",
                "narrative": "Minimal narrative for tests.",
                "primary_frame": "long_run",
            },
            "cross_variant_long_run": {
                "mean_z": 1.2,
                "agreement": 0.6,
                "combined_regime": "Overvalued",
                "same_sign": True,
            },
            "cross_variant_current_regime": {
                "mean_z": 0.5,
                "agreement": 0.2,
                "combined_regime": "Fair Value",
            },
            "variants": {
                "mvci": {
                    "headline_value": 1.5,
                    "headline_label": "MV Composite Index",
                    "headline_unit": "sigma",
                    "long_run": {
                        "z_score": 1.5,
                        "empirical_percentile": 95.0,
                        "regime": "Overvalued",
                        "regime_color": "#E87722",
                        "confidence_pct": 60.0,
                        "forward_outlook": {
                            "primary": {
                                "h_120m": {
                                    "available": True,
                                    "regression": {
                                        "alpha": 0.07, "beta": -0.02,
                                        "beta_se_nw": 0.005, "t_nw": -3.0,
                                        "r_squared": 0.3, "beta_stambaugh": -0.018,
                                    },
                                    "oos": {"goyal_welch": {"r2_oos": 0.2}},
                                    "probabilities": {"events": {
                                        "P_neg_return": {"point": 0.0, "ci95": [0.0, 0.0]},
                                        "P_below_5pct": {"point": 0.2, "ci95": [0.1, 0.3]},
                                        "P_above_7pct": {"point": 0.6, "ci95": [0.5, 0.7]},
                                    }},
                                    "bayesian": {
                                        "posterior_mean": 0.06,
                                        "ci95": [0.04, 0.08],
                                    },
                                }
                            }
                        },
                        "full_conviction": {"h_120m": {"score": 3.5, "components": {}}},
                        "schemes": {
                            "equal_weight": {"z_score": 1.5, "weights_current": {}, "explained_variance": None},
                            "inv_variance": {"z_score": 1.3, "weights_current": {}, "explained_variance": None},
                            "pca_pc1": {"z_score": 1.48, "weights_current": {"a": 0.5, "b": 0.5}, "explained_variance": 0.7},
                        },
                    },
                    "current_regime": {
                        "z_score": 0.5,
                        "empirical_percentile": 60.0,
                        "regime": "Fair Value",
                        "regime_color": "#9AA0A6",
                        "confidence_pct": 40.0,
                    },
                    "frame_interpretation": {
                        "agreement": False, "narrative_code": "MIXED", "z_spread": 1.0,
                    },
                },
                "bi_allequity_pct": _minimal_variant("Buffett (All Equity)", "%", 300.0, 1.2, 95.0),
                "bi_wilshire_pct": _minimal_variant("Buffett (Wilshire)", "%", 245.0, 1.8, 90.0),
                "bi_spx_proxy": _minimal_variant("Buffett (SPX proxy)", "%", 237.0, 1.7, 99.0),
                "cape": _minimal_variant("CAPE / Shiller P/E10", "", 36.0, 1.2, 93.0),
                "qratio": _minimal_variant("Tobin's Q-Ratio", "", 1.98, 1.0, 87.0),
                "ey_deficit": _minimal_variant("Equity Yield Deficit", "%", -0.8, 0.4, 65.0),
            },
        }
    }
    p.write_text(json.dumps(payload))


def _minimal_variant(label: str, unit: str, hv: float, z: float, pct: float) -> dict:
    return {
        "headline_value": hv,
        "headline_label": label,
        "headline_unit": unit,
        "long_run": {
            "z_score": z,
            "empirical_percentile": pct,
            "regime": "Overvalued" if z > 1 else "Fair Value",
            "regime_color": "#E87722" if z > 1 else "#9AA0A6",
            "confidence_pct": 30.0,
            "forward_outlook": {"primary": {"h_120m": {"available": False}}},
            "full_conviction": {"h_120m": {"score": 3.0, "components": {}}},
        },
        "current_regime": {
            "z_score": z * 0.5,
            "empirical_percentile": pct * 0.6,
            "regime": "Fair Value",
            "regime_color": "#9AA0A6",
            "confidence_pct": 25.0,
        },
        "frame_interpretation": {"narrative_code": "MIXED", "z_spread": 0.5},
    }


# ---------------------------------------------------------------------------
# V8A6 -- produces a valid HTML file > 100 KB and < 10 MB
# ---------------------------------------------------------------------------


def test_V8A6_build_dashboard_writes_valid_file(tmp_path: Path) -> None:
    headline_p = tmp_path / "tables" / "headline.json"
    headline_p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_headline(headline_p)

    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()
    out_p = tmp_path / "dashboard.html"
    result = build_dashboard(
        headline_path=headline_p,
        charts_dir=charts_dir,
        output_path=out_p,
    )
    assert result.exists()
    size = result.stat().st_size
    # With the minimal synthetic fixture the page is ~50 KB. The v8a acceptance
    # test uses real-data outputs and enforces the production 100 KB floor.
    assert 30_000 < size < 10_000_000


# ---------------------------------------------------------------------------
# V8A7 -- HTML contains the 4 tab markers
# ---------------------------------------------------------------------------


def test_V8A7_all_four_tab_markers(tmp_path: Path) -> None:
    headline_p = tmp_path / "tables" / "headline.json"
    headline_p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_headline(headline_p)
    out_p = tmp_path / "dashboard.html"
    p = build_dashboard(
        headline_path=headline_p,
        charts_dir=tmp_path / "charts",
        output_path=out_p,
    )
    html = p.read_text(encoding="utf-8")
    for tab in ("overview", "mvci", "buffett", "cape"):
        assert f'data-tab="{tab}"' in html


# ---------------------------------------------------------------------------
# V8A8 -- HTML embeds non-empty JSON in script tag
# ---------------------------------------------------------------------------


def test_V8A8_embeds_non_empty_json(tmp_path: Path) -> None:
    headline_p = tmp_path / "tables" / "headline.json"
    headline_p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_headline(headline_p)
    p = build_dashboard(
        headline_path=headline_p,
        charts_dir=tmp_path / "charts",
        output_path=tmp_path / "dashboard.html",
    )
    html = p.read_text(encoding="utf-8")
    m = re.search(
        r'<script id="dashboard-data" type="application/json">(.+?)</script>',
        html,
        re.DOTALL,
    )
    assert m is not None
    data = json.loads(m.group(1))
    assert "variants" in data
    assert "mvci" in data["variants"]


# ---------------------------------------------------------------------------
# V8A10 -- inlined CSS has mobile breakpoint
# ---------------------------------------------------------------------------


def test_V8A10_mobile_breakpoint_in_css(tmp_path: Path) -> None:
    headline_p = tmp_path / "tables" / "headline.json"
    headline_p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_headline(headline_p)
    p = build_dashboard(
        headline_path=headline_p,
        charts_dir=tmp_path / "charts",
        output_path=tmp_path / "dashboard.html",
    )
    html = p.read_text(encoding="utf-8")
    assert "@media (max-width: 640px)" in html


# ---------------------------------------------------------------------------
# V8A11 -- dark mode toggle JS exists
# ---------------------------------------------------------------------------


def test_V8A11_dark_mode_js_present(tmp_path: Path) -> None:
    headline_p = tmp_path / "tables" / "headline.json"
    headline_p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_headline(headline_p)
    p = build_dashboard(
        headline_path=headline_p,
        charts_dir=tmp_path / "charts",
        output_path=tmp_path / "dashboard.html",
    )
    html = p.read_text(encoding="utf-8")
    assert "applyDarkMode" in html
    assert 'id="dark-toggle"' in html


def test_missing_headline_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_dashboard(headline_path=tmp_path / "missing.json")


# ---------------------------------------------------------------------------
# Spec v8a.3: NaN-in-JSON fix
# ---------------------------------------------------------------------------


def test_v8a3_clean_for_json_replaces_nan() -> None:
    import math

    from src.viz.build_dashboard import _clean_for_json

    obj = {"a": float("nan"), "b": [1.0, float("nan"), 3.0]}
    cleaned = _clean_for_json(obj)
    assert cleaned == {"a": None, "b": [1.0, None, 3.0]}

    inf_obj = {"x": float("inf"), "y": -math.inf}
    cleaned_inf = _clean_for_json(inf_obj)
    assert cleaned_inf == {"x": None, "y": None}


def test_v8a3_clean_for_json_handles_numpy() -> None:
    import numpy as np

    from src.viz.build_dashboard import _clean_for_json

    obj = {
        "x": np.float64(1.5),
        "y": np.int64(7),
        "z": np.float64("nan"),
        "arr": np.array([1.0, np.nan, 2.0]),
    }
    cleaned = _clean_for_json(obj)
    assert cleaned["x"] == 1.5
    assert cleaned["y"] == 7
    assert cleaned["z"] is None
    assert cleaned["arr"] == [1.0, None, 2.0]


def test_v8a3_built_html_has_valid_json_payload(tmp_path: Path) -> None:
    """The dashboard's inlined JSON must parse with strict JSON (no NaN tokens)."""
    import json
    import re

    headline_p = tmp_path / "tables" / "headline.json"
    headline_p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_headline(headline_p)
    out_p = tmp_path / "dashboard.html"
    build_dashboard(
        headline_path=headline_p,
        charts_dir=tmp_path / "charts",
        output_path=out_p,
    )
    html = out_p.read_text(encoding="utf-8")
    m = re.search(
        r'<script id="dashboard-data" type="application/json">(.+?)</script>',
        html,
        re.DOTALL,
    )
    assert m is not None, "dashboard-data script tag not found"
    raw = m.group(1)
    # Hard assertion: no literal NaN/Infinity tokens (would be invalid JSON).
    assert "NaN" not in raw, "Invalid JSON: contains NaN literal"
    assert "Infinity" not in raw, "Invalid JSON: contains Infinity literal"
    # Must round-trip parse with strict JSON.
    parsed = json.loads(raw)
    assert "variants" in parsed
