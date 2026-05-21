"""v11.1: Strategy Engine V1 — vendored v50 quant pipeline integration.

The v50 engine lives at ``D:\\macro\\quant_pipeline\\`` (outside this repo).
This package wraps subprocess invocation, output parsing, and dashboard
plumbing for the new Strategy Engine tab.
"""
from .runner import (
    check_norgate_available,
    run_v50_pipeline,
    sync_latest_outputs,
)
from .output_parser import (
    parse_v50_csv,
    parse_governance_txt,
    parse_v50_xlsx,
    compute_dashboard_metrics,
)
from .strategy_engine_config import (
    QUANT_PIPELINE_ROOT,
    V50_SCRIPT,
    QE_OUTPUT_ROOT,
    QE_LATEST_DIR,
    QE_LATEST_CSV,
    QE_LATEST_XLSX,
    QE_GOVERNANCE_DIR,
    V1_ACTIVE_STRATEGIES,
    V1_BENCHMARK_INDICES,
    V1_BENCHMARK_STOCKS,
    V1_DROPPED_STRATEGIES,
    V50_CYCLES,
    V50_FULL,
    V50_COST_LEVELS,
    ALL_EXCEL_GROUPS,
)

__all__ = [
    "check_norgate_available",
    "run_v50_pipeline",
    "sync_latest_outputs",
    "parse_v50_csv",
    "parse_governance_txt",
    "parse_v50_xlsx",
    "compute_dashboard_metrics",
    "QUANT_PIPELINE_ROOT",
    "V50_SCRIPT",
    "QE_OUTPUT_ROOT",
    "QE_LATEST_DIR",
    "QE_LATEST_CSV",
    "QE_LATEST_XLSX",
    "QE_GOVERNANCE_DIR",
    "V1_ACTIVE_STRATEGIES",
    "V1_BENCHMARK_INDICES",
    "V1_BENCHMARK_STOCKS",
    "V1_DROPPED_STRATEGIES",
    "V50_CYCLES",
    "V50_FULL",
    "V50_COST_LEVELS",
    "ALL_EXCEL_GROUPS",
]
