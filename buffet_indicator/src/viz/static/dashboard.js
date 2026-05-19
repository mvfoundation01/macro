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

  function renderPlot(divId, spec) {
    if (!spec || (!spec.data && !spec.layout)) return;
    const el = document.getElementById(divId);
    if (!el) return;
    const data = spec.data || [];
    const layout = Object.assign({}, spec.layout || {});
    const config = Object.assign(
      { responsive: true, displaylogo: false, displayModeBar: true },
      spec.config || {}
    );
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
    const hero = (DATA.hero_specs || {})[tabName];
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
    } else if (tabName === "qratio") {
      renderVariantPanels("qratio", "qratio");
    } else if (tabName === "ey_deficit") {
      renderVariantPanels("ey_deficit", "ey_deficit");
    } else if (tabName === "mean_reversion") {
      renderVariantPanels("mean_reversion", "mean-reversion");
    } else if (tabName === "diagnostics") {
      renderDiagnostics();
    } else if (tabName === "data") {
      renderDataTab();
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
    if (charts.panel_c) renderPlot(`${tabName}-panel-c-${variantKey}`, charts.panel_c);
  }

  function renderDiagnostics() {
    if (DATA.diagnostics_correlation_chart && !renderedCharts.has("diagnostics-correlation-heatmap")) {
      renderPlot("diagnostics-correlation-heatmap", DATA.diagnostics_correlation_chart);
    }
    if (DATA.diagnostics_oos_r2_chart && !renderedCharts.has("diagnostics-oos-r2-chart")) {
      renderPlot("diagnostics-oos-r2-chart", DATA.diagnostics_oos_r2_chart);
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
    // 3. Populate the JSON viewer (truncated for performance).
    const viewer = document.getElementById("headline-json-viewer");
    if (viewer && !viewer.dataset.populated) {
      viewer.dataset.populated = "1";
      const raw = DATA.headline_json_str || "{}";
      viewer.textContent = raw.length > 8000 ? raw.slice(0, 8000) + "\n\n... [truncated — use download button for full file]" : raw;
    }
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
