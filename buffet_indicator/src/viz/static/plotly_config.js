// MV Valuation Dashboard — universal Plotly configuration (v11.2.2)
//
// Single source of truth for:
//   - B4 fix: yaxis drag-zoom enabled (fixedrange: false, autorange: true)
//   - B1 fix: valid d3-format strings only (no +,.Nf — that's rejected by Plotly 2.35.2)
//   - Strategy color palette across all 9 EA surfaces + Strategy Engine
//   - Equity-curve layout helpers (range slider + zoom buttons)
//
// Loaded as a regular <script> (NOT ES module) — exposes window.MV_PlotlyConfig.

(function () {
  "use strict";

  // ==========================================================================
  // CONFIG (passed as 3rd arg to Plotly.newPlot)
  // ==========================================================================
  var plotlyConfigDefault = {
    responsive: true,
    scrollZoom: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
    toImageButtonOptions: {
      format: "png",
      filename: "chart",
      height: 800,
      width: 1200,
      scale: 2
    }
  };

  // ==========================================================================
  // LAYOUT — universal defaults that ENABLE drag-zoom on Y axis (B4)
  // ==========================================================================
  var plotlyLayoutDefault = {
    dragmode: "pan",
    hovermode: "x unified",
    margin: { l: 60, r: 20, t: 40, b: 60 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0.02)",
    font: { family: "Inter, system-ui, sans-serif", size: 12 },
    xaxis: {
      fixedrange: false,
      autorange: true,
      showspikes: true,
      spikemode: "across",
      spikethickness: 1,
      spikecolor: "#999",
      spikedash: "dot"
    },
    yaxis: {
      fixedrange: false,
      autorange: true,
      type: "linear",
      showspikes: true,
      spikemode: "across",
      spikethickness: 1,
      spikecolor: "#999",
      spikedash: "dot"
    },
    legend: {
      orientation: "h",
      x: 0.5, xanchor: "center",
      y: -0.15, yanchor: "top"
    }
  };

  // ==========================================================================
  // EQUITY-CURVE LAYOUT — adds range slider + zoom buttons
  // ==========================================================================
  var plotlyLayoutEquityCurve = mergeLayoutShallow(plotlyLayoutDefault, {
    xaxis: {
      fixedrange: false,
      autorange: true,
      showspikes: true,
      spikemode: "across",
      spikethickness: 1,
      spikecolor: "#999",
      spikedash: "dot",
      rangeslider: { visible: true, thickness: 0.05 },
      rangeselector: {
        buttons: [
          { count: 1, label: "1Y", step: "year", stepmode: "backward" },
          { count: 3, label: "3Y", step: "year", stepmode: "backward" },
          { count: 5, label: "5Y", step: "year", stepmode: "backward" },
          { count: 10, label: "10Y", step: "year", stepmode: "backward" },
          { step: "all", label: "All" }
        ],
        x: 0, y: 1.15
      }
    }
  });

  // ==========================================================================
  // STRATEGY COLOR PALETTE
  // V1 = primary blue (operational); V2 = orange tones (DIAGNOSTIC)
  // SPY/EW = grays (benchmark)
  // ==========================================================================
  var strategyColors = {
    "V1_Combination": "#1F77B4",
    "V2_R-PRIMARY":   "#FF7F0E",
    "V2_R-ALT1":      "#FFB78C",
    "V2_R-ALT2":      "#FFCBA8",
    "SPY":            "#666666",
    "EW":             "#999999"
  };

  // ==========================================================================
  // Universal layout-merge helpers
  // ==========================================================================
  function mergeLayoutShallow(base, override) {
    var out = Object.assign({}, base, override);
    if (base.xaxis || override.xaxis) {
      out.xaxis = Object.assign({}, base.xaxis || {}, override.xaxis || {});
    }
    if (base.yaxis || override.yaxis) {
      out.yaxis = Object.assign({}, base.yaxis || {}, override.yaxis || {});
    }
    if (base.legend || override.legend) {
      out.legend = Object.assign({}, base.legend || {}, override.legend || {});
    }
    if (base.margin || override.margin) {
      out.margin = Object.assign({}, base.margin || {}, override.margin || {});
    }
    return out;
  }

  // ==========================================================================
  // Apply UNIVERSAL drag-zoom defaults to a chart-spec layout (B4 fix).
  // Called from dashboard.js renderPlot() so every existing chart inherits
  // yaxis.fixedrange=false + autorange=true WITHOUT touching chart_specs.py.
  // Caller layout wins on any keys it explicitly sets.
  // ==========================================================================
  function applyUniversalDefaults(layout) {
    layout = layout || {};
    var xaxis = Object.assign({}, plotlyLayoutDefault.xaxis, layout.xaxis || {});
    var yaxis = Object.assign({}, plotlyLayoutDefault.yaxis, layout.yaxis || {});
    layout.xaxis = xaxis;
    layout.yaxis = yaxis;
    if (layout.dragmode === undefined) layout.dragmode = "pan";
    return layout;
  }

  // ==========================================================================
  // High-level renderer for NEW v11.2.2 charts (equity curves, EA surfaces).
  // Existing charts use dashboard.js renderPlot() — this is for code that
  // wants the full universal-defaults experience including range slider /
  // log toggle.
  // ==========================================================================
  function renderChart(divId, data, layoutOverrides, configOverrides, opts) {
    opts = opts || {};
    var baseLayout = opts.equityCurve ? plotlyLayoutEquityCurve : plotlyLayoutDefault;
    var layout = mergeLayoutShallow(baseLayout, layoutOverrides || {});
    var config = Object.assign({}, plotlyConfigDefault, configOverrides || {});
    Plotly.newPlot(divId, data, layout, config);

    if (opts.logToggle) {
      var btnId = divId + "-log-toggle";
      var existing = document.getElementById(btnId);
      if (existing) existing.remove();
      var btn = document.createElement("button");
      btn.id = btnId;
      btn.className = "ml-2 px-2 py-1 text-xs border rounded bg-white hover:bg-gray-50";
      btn.textContent = "Y: linear";
      btn.onclick = function () {
        var gd = document.getElementById(divId);
        var current = (gd.layout && gd.layout.yaxis && gd.layout.yaxis.type) || "linear";
        var next = current === "log" ? "linear" : "log";
        Plotly.relayout(gd, { "yaxis.type": next });
        btn.textContent = "Y: " + next;
      };
      var parent = document.getElementById(divId);
      if (parent && parent.parentElement) parent.parentElement.appendChild(btn);
    }
  }

  // ==========================================================================
  // Public API
  // ==========================================================================
  window.MV_PlotlyConfig = {
    plotlyConfigDefault: plotlyConfigDefault,
    plotlyLayoutDefault: plotlyLayoutDefault,
    plotlyLayoutEquityCurve: plotlyLayoutEquityCurve,
    strategyColors: strategyColors,
    mergeLayout: mergeLayoutShallow,
    applyUniversalDefaults: applyUniversalDefaults,
    renderChart: renderChart
  };
})();
