// MV Valuation Dashboard runtime (Spec v8b).

(function () {
  "use strict";

  // ---------------------------------------------------------------------
  // Load embedded data
  // ---------------------------------------------------------------------
  let DATA;
  try {
    const node = document.getElementById("dashboard-data");
    DATA = JSON.parse(node.textContent);
  } catch (err) {
    console.error("Failed to parse dashboard-data:", err);
    DATA = {};
  }
  window.MV_DASHBOARD = DATA;

  // ---------------------------------------------------------------------
  // Dark mode
  // ---------------------------------------------------------------------
  function applyDarkMode(enabled) {
    if (enabled) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    redrawAllPlots();
  }

  function initDarkMode() {
    const stored = window.localStorage.getItem("mv_dark_mode") === "true";
    applyDarkMode(stored);
    const btn = document.getElementById("dark-toggle");
    if (!btn) return;
    btn.addEventListener("click", () => {
      const enabled = !document.documentElement.classList.contains("dark");
      window.localStorage.setItem("mv_dark_mode", enabled ? "true" : "false");
      applyDarkMode(enabled);
    });
  }

  // ---------------------------------------------------------------------
  // Tab navigation
  // ---------------------------------------------------------------------
  function showTab(tabName) {
    document.querySelectorAll(".tab-button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabName);
    });
    document.querySelectorAll(".tab-content").forEach((c) => {
      c.classList.toggle("active", c.dataset.tab === tabName);
    });
    window.localStorage.setItem("mv_active_tab", tabName);
    renderChartsForTab(tabName);
  }

  function initTabs() {
    document.querySelectorAll(".tab-button[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => showTab(btn.dataset.tab));
    });
    // Click on overview card → jump to that tab.
    document.querySelectorAll("[data-tab-target]").forEach((card) => {
      card.addEventListener("click", () => {
        const target = card.dataset.tabTarget;
        if (target) showTab(target);
      });
    });
    const stored = window.localStorage.getItem("mv_active_tab") || "overview";
    showTab(stored);
  }

  // ---------------------------------------------------------------------
  // Buffett sub-tabs
  // ---------------------------------------------------------------------
  function initBuffettSubtabs() {
    const btns = document.querySelectorAll("[data-buffett-subtab]");
    btns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.buffettSubtab;
        btns.forEach((b) => b.classList.toggle("active", b === btn));
        document.querySelectorAll("[data-buffett-panel]").forEach((p) => {
          p.style.display = p.dataset.buffettPanel === key ? "block" : "none";
        });
        renderBuffettCharts(key);
        window.localStorage.setItem("mv_buffett_subtab", key);
      });
    });
    const stored = window.localStorage.getItem("mv_buffett_subtab") || "bi_allequity_pct";
    const target = document.querySelector(`[data-buffett-subtab="${stored}"]`);
    if (target) target.click();
  }

  // ---------------------------------------------------------------------
  // Plotly rendering
  // ---------------------------------------------------------------------
  const renderedCharts = new Set();
  const chartDivIds = [];

  // v8b.1 fix B.2: enable scroll-wheel zoom only on non-touch desktops.
  // Touch devices keep scrollZoom=false so vertical scrolling doesn't get
  // trapped inside the chart.
  const IS_TOUCH_DEVICE =
    "ontouchstart" in window ||
    (typeof navigator !== "undefined" && navigator.maxTouchPoints > 0);

  function renderPlot(divId, spec) {
    if (!spec || (!spec.data && !spec.layout)) return;
    const el = document.getElementById(divId);
    if (!el) return;
    const data = spec.data || [];
    let layout = Object.assign({}, spec.layout || {});
    const config = Object.assign(
      { responsive: true, displaylogo: false, displayModeBar: true },
      spec.config || {}
    );
    // Per-render override: only enable scrollZoom on desktop pointing devices.
    if (!IS_TOUCH_DEVICE) {
      config.scrollZoom = true;
    }
    // v11.2.2 B4 fix: apply universal Y-axis drag-zoom defaults so users can
    // pan/zoom Y axis on every chart. Caller layout still wins on explicit keys.
    if (window.MV_PlotlyConfig && window.MV_PlotlyConfig.applyUniversalDefaults) {
      layout = window.MV_PlotlyConfig.applyUniversalDefaults(layout);
    }
    if (document.documentElement.classList.contains("dark")) {
      layout.paper_bgcolor = "rgba(0,0,0,0)";
      layout.plot_bgcolor = "rgba(0,0,0,0)";
      layout.font = Object.assign({}, layout.font || {}, { color: "#e5e7eb" });
    }
    try {
      Plotly.newPlot(divId, data, layout, config);
      renderedCharts.add(divId);
      if (!chartDivIds.includes(divId)) chartDivIds.push(divId);
    } catch (err) {
      console.warn("Plotly.newPlot failed for", divId, err);
    }
  }

  function renderHeroForTab(tabName) {
    let hero = (DATA.hero_specs || {})[tabName];
    // v8b.1 D — overview hero is sentinel-referenced to the mvci hero
    // to avoid duplicating the spec in the inline JSON payload.
    if (hero === "__HERO_MVCI__") hero = DATA.hero_specs.mvci;
    if (!hero) return;
    if (tabName === "buffett") {
      const sub = window.localStorage.getItem("mv_buffett_subtab") || "bi_allequity_pct";
      const spec = hero[sub];
      if (spec) renderPlot(`hero-chart-buffett`, spec);
    } else {
      const containerId =
        tabName === "mean_reversion" ? "hero-chart-mean-reversion" : `hero-chart-${tabName}`;
      renderPlot(containerId, hero);
    }
    setTimeout(() => {
      const ids =
        tabName === "buffett"
          ? ["hero-chart-buffett"]
          : tabName === "mean_reversion"
          ? ["hero-chart-mean-reversion"]
          : [`hero-chart-${tabName}`];
      ids.forEach((id) => {
        const el = document.getElementById(id);
        if (el) Plotly.Plots.resize(el).catch(() => {});
      });
    }, 50);
  }

  function renderChartsForTab(tabName) {
    renderHeroForTab(tabName);

    if (tabName === "overview") {
      renderSparklines();
      // v11.1.1 I1 fix: wire up the MVCI+MRC mini chart on Overview tab.
      // The chart spec is in DATA.overview_mvci_mrc_mini (populated by
      // build_macro_charts.build_macro_chart_payload) but was previously
      // never injected into the #overview-cross-composite-mini div.
      if (DATA.overview_mvci_mrc_mini && DATA.overview_mvci_mrc_mini.data &&
          DATA.overview_mvci_mrc_mini.data.length > 0) {
        renderPlot("overview-cross-composite-mini", DATA.overview_mvci_mrc_mini);
      }
    } else if (tabName === "mvci") {
      renderVariantPanels("mvci", "mvci");
      const pcaDiv = document.getElementById("mvci-pca-bar");
      if (pcaDiv && DATA.mvci_pca_loadings_chart && !renderedCharts.has("mvci-pca-bar")) {
        renderPlot("mvci-pca-bar", DATA.mvci_pca_loadings_chart);
      }
    } else if (tabName === "buffett") {
      const key = window.localStorage.getItem("mv_buffett_subtab") || "bi_allequity_pct";
      renderBuffettCharts(key);
    } else if (tabName === "cape") {
      renderVariantPanels("cape", "cape");
    } else if (tabName === "crestmont") {
      renderVariantPanels("crestmont", "crestmont");
    } else if (tabName === "qratio") {
      renderVariantPanels("qratio", "qratio");
    } else if (tabName === "ey_deficit") {
      renderVariantPanels("ey_deficit", "ey_deficit");
    } else if (tabName === "mean_reversion") {
      renderVariantPanels("mean_reversion", "mean-reversion");
    } else if (tabName === "diagnostics") {
      renderDiagnostics();
    } else if (tabName === "backtest") {
      renderBacktest();
    } else if (tabName === "data") {
      renderDataTab();
    } else if (MACRO_TABS.has(tabName)) {
      renderMacroChartsForTab(tabName);
    }
    // v11.0c — update header pills to reflect the active tab's metrics.
    updateHeaderPills(tabName);
  }

  // v11.0c — set of all macro-risk tabs (constituents + composite).
  // v11.0.1 — extended with 6 derived spread tabs.
  const MACRO_TABS = new Set([
    "mrc", "yc_10y3m", "yc_10y2y", "cs_hy_master", "cs_ig_master",
    "cs_hy_bb", "cs_hy_ccc", "margin_debt_growth",
    "spread_hy_ig", "spread_ccc_bb", "spread_hy_reach_for_yield",
    "spread_hy_treasury_traditional", "spread_equity_credit_rp",
    "spread_hy_oas_3m_delta",
  ]);

  function renderMacroChartsForTab(tabName) {
    // Hero
    const hero = (DATA.macro_hero_specs || {})[tabName];
    if (hero) {
      renderPlot(`hero-chart-${tabName}`, hero);
    }
    // Panel A/B/C + conditional distribution
    const charts = (DATA.macro_variant_charts || {})[tabName];
    if (charts) {
      if (charts.panel_a) renderPlot(`${tabName}-panel-a`, charts.panel_a);
      if (charts.panel_b) renderPlot(`${tabName}-panel-b`, charts.panel_b);
      let panelC = charts.panel_c;
      if (panelC === "__SHARED_PANEL_C__") panelC = DATA.shared_panel_c;
      if (panelC) renderPlot(`${tabName}-panel-c`, panelC);
      if (charts.cond_dist) renderPlot(`${tabName}-cond-dist`, charts.cond_dist);
    }
    // MRC tab special elements.
    if (tabName === "mrc") {
      const extras = DATA.mrc_extras || {};
      if (extras.constituent_contributions) {
        renderPlot("mrc-constituent-bars", extras.constituent_contributions);
      }
      if (extras.correlation_heatmap) {
        renderPlot("mrc-corr-heatmap", extras.correlation_heatmap);
      }
      if (extras.pca_scree) {
        renderPlot("mrc-pca-scree", extras.pca_scree);
      }
      if (extras.cross_composite_quadrant) {
        renderPlot("mrc-cross-composite", extras.cross_composite_quadrant);
      }
    }
    // Belt-and-braces: resize on next tick (some charts need a re-flow).
    setTimeout(() => {
      [
        `hero-chart-${tabName}`,
        `${tabName}-panel-a`,
        `${tabName}-panel-b`,
        `${tabName}-panel-c`,
        `${tabName}-cond-dist`,
        "mrc-constituent-bars",
        "mrc-corr-heatmap",
        "mrc-pca-scree",
        "mrc-cross-composite",
      ].forEach((id) => {
        const el = document.getElementById(id);
        if (el && el.data) Plotly.Plots.resize(el).catch(() => {});
      });
    }, 50);
  }

  // v11.0c — update the 4 page-header pills (z-score, P(neg 10Y), Confidence,
  // Conviction) to reflect the active tab's metrics. Falls back to MVCI when
  // no per-tab metrics are available (Overview, MVCI, valuation tabs).
  function updateHeaderPills(tabName) {
    const macroMetrics = (DATA.macro_metrics || {})[tabName];
    const elZ = document.querySelector("[data-pill='z']");
    const elP = document.querySelector("[data-pill='p_neg']");
    const elC = document.querySelector("[data-pill='confidence']");
    const elV = document.querySelector("[data-pill='conviction']");
    if (!elZ && !elP && !elC && !elV) return;
    if (macroMetrics) {
      if (elZ) elZ.textContent = macroMetrics.z_fmt || "n/a";
      if (elP) elP.textContent = macroMetrics.p_neg_fmt || "n/a";
      if (elC) elC.textContent = macroMetrics.confidence_fmt || "n/a";
      if (elV) elV.textContent = (macroMetrics.conviction_fmt || "n/a") + " / 5";
      // Update the regime callout banner to the macro indicator's regime.
      const banner = document.querySelector("[data-regime-banner]");
      if (banner && macroMetrics.regime_color) {
        banner.style.backgroundColor = macroMetrics.regime_color;
        const txt = banner.querySelector("[data-regime-text]");
        if (txt) txt.textContent = macroMetrics.regime;
      }
    } else {
      // Reset to MVCI defaults.
      const mvciDefaults = DATA._header_defaults || {};
      if (elZ && mvciDefaults.z_fmt) elZ.textContent = mvciDefaults.z_fmt;
      if (elP && mvciDefaults.p_neg_fmt) elP.textContent = mvciDefaults.p_neg_fmt;
      if (elC && mvciDefaults.confidence_fmt) elC.textContent = mvciDefaults.confidence_fmt;
      if (elV && mvciDefaults.conviction_fmt) elV.textContent = mvciDefaults.conviction_fmt + " / 5";
      const banner = document.querySelector("[data-regime-banner]");
      if (banner && mvciDefaults.regime_color) {
        banner.style.backgroundColor = mvciDefaults.regime_color;
        const txt = banner.querySelector("[data-regime-text]");
        if (txt && mvciDefaults.regime_label) txt.textContent = mvciDefaults.regime_label;
      }
    }
  }

  function renderSparklines() {
    const sparks = DATA.sparklines || {};
    Object.keys(sparks).forEach((vkey) => {
      const id = `sparkline-${vkey}`;
      const div = document.getElementById(id);
      if (!div) return;
      if (renderedCharts.has(id)) return;
      const spec = sparks[vkey];
      if (!spec || !spec.data || spec.data.length === 0) return;
      const config = Object.assign(
        { staticPlot: true, displayModeBar: false, responsive: true },
        spec.config || {}
      );
      Plotly.newPlot(id, spec.data, spec.layout || {}, config);
      renderedCharts.add(id);
      chartDivIds.push(id);
    });
  }

  function renderBuffettCharts(variantKey) {
    renderVariantPanels(variantKey, "buffett");
  }

  function renderVariantPanels(variantKey, tabName) {
    const charts = (DATA.variant_charts || {})[variantKey];
    if (!charts) return;
    if (charts.panel_a) renderPlot(`${tabName}-panel-a-${variantKey}`, charts.panel_a);
    if (charts.panel_b) renderPlot(`${tabName}-panel-b-${variantKey}`, charts.panel_b);
    // v8b.1 D — Panel C is the same across all variants; the per-variant
    // entry is a sentinel string pointing at DATA.shared_panel_c.
    let panelC = charts.panel_c;
    if (panelC === "__SHARED_PANEL_C__") panelC = DATA.shared_panel_c;
    if (panelC) renderPlot(`${tabName}-panel-c-${variantKey}`, panelC);
  }

  function renderBacktest() {
    if (DATA.backtest_equity_curve && !renderedCharts.has("backtest-equity-curve")) {
      renderPlot("backtest-equity-curve", DATA.backtest_equity_curve);
    }
    if (DATA.backtest_drawdown_chart && !renderedCharts.has("backtest-drawdown-chart")) {
      renderPlot("backtest-drawdown-chart", DATA.backtest_drawdown_chart);
    }
    if (DATA.backtest_allocation_chart && !renderedCharts.has("backtest-allocation-chart")) {
      renderPlot("backtest-allocation-chart", DATA.backtest_allocation_chart);
    }
  }

  function renderDiagnostics() {
    if (DATA.diagnostics_correlation_chart && !renderedCharts.has("diagnostics-correlation-heatmap")) {
      renderPlot("diagnostics-correlation-heatmap", DATA.diagnostics_correlation_chart);
    }
    if (DATA.diagnostics_oos_r2_chart && !renderedCharts.has("diagnostics-oos-r2-chart")) {
      renderPlot("diagnostics-oos-r2-chart", DATA.diagnostics_oos_r2_chart);
    }
    if (DATA.diagnostics_acf_pacf_chart && !renderedCharts.has("diagnostics-acf-pacf-chart")) {
      renderPlot("diagnostics-acf-pacf-chart", DATA.diagnostics_acf_pacf_chart);
    }
    if (DATA.diagnostics_calibration_chart && !renderedCharts.has("diagnostics-calibration-chart")) {
      renderPlot("diagnostics-calibration-chart", DATA.diagnostics_calibration_chart);
    }
  }

  function renderDataTab() {
    // 1. Wire CSV download buttons (idempotent).
    document.querySelectorAll(".csv-download-btn[data-csv-key]").forEach((btn) => {
      if (btn.dataset.wired === "1") return;
      btn.dataset.wired = "1";
      btn.addEventListener("click", () => {
        const key = btn.dataset.csvKey;
        const fname = btn.dataset.csvFilename || `${key}.csv`;
        const csvText = (DATA.csv_exports || {})[key];
        if (!csvText) {
          alert(`CSV "${key}" not available — pipeline output may be missing.`);
          return;
        }
        downloadBlob(csvText, fname, "text/csv");
      });
    });
    // 2. Headline JSON download button.
    const jsonBtn = document.getElementById("download-headline-json");
    if (jsonBtn && jsonBtn.dataset.wired !== "1") {
      jsonBtn.dataset.wired = "1";
      jsonBtn.addEventListener("click", () => {
        const text = DATA.headline_json_str || "{}";
        downloadBlob(text, "mv_headline.json", "application/json");
      });
    }
    // 2b. Scatter data: rebuild CSV from inline variant_charts on click
    // (v8b.1 D bundle-size optimization — scatter_data CSV no longer inlined).
    const scatterBtn = document.getElementById("download-scatter-on-demand");
    if (scatterBtn && scatterBtn.dataset.wired !== "1") {
      scatterBtn.dataset.wired = "1";
      scatterBtn.addEventListener("click", () => {
        const csv = rebuildScatterCSV();
        if (!csv) {
          alert("Scatter data unavailable — variant chart specs missing.");
          return;
        }
        downloadBlob(csv, "mv_scatter_data.csv", "text/csv");
      });
    }
    // 3. Populate the JSON viewer (truncated for performance).
    const viewer = document.getElementById("headline-json-viewer");
    if (viewer && !viewer.dataset.populated) {
      viewer.dataset.populated = "1";
      const raw = DATA.headline_json_str || "{}";
      viewer.textContent = raw.length > 8000 ? raw.slice(0, 8000) + "\n\n... [truncated — use download button for full file]" : raw;
    }
  }

  // v8b.1 D — rebuild scatter_data CSV from inline panel B traces.
  // Each variant's Panel B carries (date, z_score, forward_120m_cagr) tuples
  // in trace 0 (Historical scatter). We reconstruct a long-format CSV
  // matching the original outputs/charts/scatter_data.parquet schema.
  function rebuildScatterCSV() {
    const variantCharts = DATA.variant_charts || {};
    if (!Object.keys(variantCharts).length) return null;
    const rows = ["date,variant,z_score_long_run,forward_120m_cagr"];
    for (const variant of Object.keys(variantCharts)) {
      const panelB = variantCharts[variant] && variantCharts[variant].panel_b;
      if (!panelB || !panelB.data || !panelB.data.length) continue;
      const hist = panelB.data[0]; // first trace = Historical
      const xs = hist.x || [];
      const ys = hist.y || [];
      const dates = hist.customdata || [];
      for (let i = 0; i < xs.length; i++) {
        // y is in % (we multiply by 100 upstream); divide back for raw CAGR
        const cagr = (ys[i] != null) ? (ys[i] / 100) : "";
        const date = dates[i] || "";
        const z = (xs[i] != null) ? xs[i] : "";
        rows.push(`${date},${variant},${z},${cagr}`);
      }
    }
    return rows.length > 1 ? rows.join("\n") : null;
  }

  function downloadBlob(text, filename, mime) {
    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function redrawAllPlots() {
    chartDivIds.forEach((divId) => {
      const div = document.getElementById(divId);
      if (!div) return;
      Plotly.relayout(div, {
        "font.color": document.documentElement.classList.contains("dark") ? "#e5e7eb" : "#1f2937",
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
      }).catch(() => {});
    });
  }

  // ---------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    initDarkMode();
    initTabs();
    initBuffettSubtabs();
  });
})();
