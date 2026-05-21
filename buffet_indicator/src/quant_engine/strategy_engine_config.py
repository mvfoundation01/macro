"""Paths + constants for Strategy Engine V1 (v11.1).

All paths can be overridden via env var ``QUANT_PIPELINE_ROOT`` for portability.
The V1 lineup constants encode the user's V1 sprint scope: 4 active strategies
(DD-TARGET, ENS-Ultra, LowBeta, Combination) plus 2 benchmark indices and
11 buy-and-hold stocks. LowRisk / FACTOR-ONLY / ETF-ROTATION are dropped from
V1 (preserved via ``V11_1_DROP_STRATEGIES=0`` env override for research).
"""
from __future__ import annotations

from pathlib import Path
import os


QUANT_PIPELINE_ROOT = Path(
    os.environ.get("QUANT_PIPELINE_ROOT", r"D:\macro\quant_pipeline")
)
V50_SCRIPT = QUANT_PIPELINE_ROOT / "quant_engine_v50_FINAL.py"

MV_REPO_ROOT = Path(__file__).resolve().parents[2]
QE_OUTPUT_ROOT = MV_REPO_ROOT / "outputs" / "quant_engine"
QE_LATEST_DIR = QE_OUTPUT_ROOT / "latest"
QE_LATEST_CSV = QE_LATEST_DIR / "latest.csv"
QE_LATEST_XLSX = QE_LATEST_DIR / "latest.xlsx"
QE_GOVERNANCE_DIR = QE_LATEST_DIR / "governance"

# V1 lineup (per v11.1 spec)
V1_ACTIVE_STRATEGIES = ["DD-TARGET", "ENS-Ultra", "LowBeta", "Combination"]
V1_BENCHMARK_INDICES = ["SPY", "EW"]
V1_BENCHMARK_STOCKS = [
    "BLK", "BRK.B", "TROW", "BEN", "IVZ",
    "STT", "NTRS", "RJF", "GS", "JPM", "MS",
]
V1_DROPPED_STRATEGIES = ["LowRisk", "FACTOR-ONLY", "ETF-ROTATION"]

# v50 produces 7 cycle periods + 1 FULL period, all at 5 cost levels.
V50_CYCLES = ["Dotcom", "Bull03-07", "GFC", "LongBull", "COVID", "Bear22", "AIBull"]
V50_FULL = ["FULL"]
V50_COST_LEVELS = [15, 30, 45, 75, 100]

# 32 Excel sheets organized into 4 sub-tab groups for the dashboard.
# Must match v50's ``write_excel()`` exactly — drift would surface as
# "Sheet missing" banners in the rendered tab.
EXCEL_GROUP_CORE = [
    "Results", "Cost Stress", "Ranking", "ETF-Rotation History",
    "Bottom Catchers", "Correlations", "Turnover", "ETF Protection",
    "Holdings Overlap", "TopCatcher Details", "QA Audit", "DSR",
    "Factor Attribution", "Factor Attr Deeper", "GFC Forensic",
    "ETF Episode Audit", "Cash Protocol",
]
EXCEL_GROUP_ROBUSTNESS = [
    "Data Availability", "Bootstrap CI", "Path MC MaxDD",
    "Parametric Tail", "WF OOS Distribution", "Extreme Events",
    "Robustness Summary",
]
# Names match v50's actual XLSX output (see v50.write_excel()):
# "SP500 Head-to-Head" (not "SP500 H2H"), "Dollar Growth" (not "$ Growth"),
# "Institutional Scorecard" (not "Scorecard").
EXCEL_GROUP_INSTITUTIONAL = [
    "Strategy Ranking", "SP500 Head-to-Head", "Dollar Growth",
    "Institutional Scorecard", "Institutional Pitch", "Retail Pitch",
]
EXCEL_GROUP_GAP_CLOSERS = [
    "Realistic Slippage", "Capital Accounting", "Governance",
]
# v50 also emits 2 extra sheets not mentioned in the v11.1 spec but present
# in the canonical April-29 production run — surfacing them keeps full fidelity.
EXCEL_GROUP_EXTRAS = [
    "Complete Ranking", "Stock Deep Dive",
]
ALL_EXCEL_GROUPS = {
    "core": EXCEL_GROUP_CORE,
    "robustness": EXCEL_GROUP_ROBUSTNESS,
    "institutional": EXCEL_GROUP_INSTITUTIONAL,
    "gap_closers": EXCEL_GROUP_GAP_CLOSERS,
    "extras": EXCEL_GROUP_EXTRAS,
}

# Sheets that are intentionally N/A in V1 (ETF-ROTATION dropped → these go empty).
V1_NA_SHEETS = ["ETF-Rotation History", "ETF Protection", "ETF Episode Audit"]

# Short description for each sheet — surfaced under the section title in the UI.
SHEET_DESCRIPTIONS = {
    "Results": "Per-strategy headline metrics across 8 periods × 5 cost levels.",
    "Cost Stress": "Sharpe degradation curve across 15/30/45/75/100 bps round-trip.",
    "Ranking": "Sortable institutional ranking across the full universe.",
    "ETF-Rotation History": "Per-month ETF state transitions (N/A in V1 — ETF-ROTATION dropped).",
    "Bottom Catchers": "Worst-performing stocks per period and their attribution.",
    "Correlations": "Pairwise correlation of strategy daily returns.",
    "Turnover": "Per-month turnover ratio per strategy.",
    "ETF Protection": "Crash-protection events fired (N/A in V1 — ETF-ROTATION dropped).",
    "Holdings Overlap": "Pairwise Jaccard similarity of monthly holdings.",
    "TopCatcher Details": "Best-performing stocks per period and their attribution.",
    "QA Audit": "12-gate Point-In-Time / leakage / persistence audit results.",
    "DSR": "Deflated Sharpe Ratio (Lopez de Prado 2014 with Mertens adjustment).",
    "Factor Attribution": "Single-factor regression beta + alpha vs SPY.",
    "Factor Attr Deeper": "FF3 + momentum + low-vol four-factor decomposition.",
    "GFC Forensic": "2008-2009 stress-test forensic with per-month curve.",
    "ETF Episode Audit": "Detailed log of ETF protection episodes (N/A in V1).",
    "Cash Protocol": "Cash position management and reserve drawdown policy.",
    "Data Availability": "Per-data-series first/last bar and total coverage.",
    "Bootstrap CI": "Politis-Romano stationary block bootstrap, 21-day blocks, 10K reps.",
    "Path MC MaxDD": "Monte Carlo MaxDD distribution across 10K shuffled paths.",
    "Parametric Tail": "Gaussian / Student-t / Empirical VaR + CVaR at 95/99/99.9%.",
    "WF OOS Distribution": "Per-fold Sharpe across ~52 six-month walk-forward windows.",
    "Extreme Events": "Top-5 historical drawdowns per strategy with onset/recovery.",
    "Robustness Summary": "Pass/fail card across 4 robustness layers.",
    "Strategy Ranking": "Institutional composite ranking with weighted score.",
    "SP500 Head-to-Head": "Per-strategy head-to-head deltas vs SPY across all metrics.",
    "Dollar Growth": "$10,000 → $X dollar-growth comparison per strategy.",
    "Institutional Scorecard": "Per-dimension scorecard contributing to 81/100 PASS.",
    "Institutional Pitch": "Long-form prose pitch suitable for an institutional allocator.",
    "Retail Pitch": "Long-form prose pitch suitable for a retail audience.",
    "Realistic Slippage": "Almgren-Chriss square-root market-impact slippage per trade.",
    "Capital Accounting": "Share-level capital accounting + PnL reconciliation.",
    "Governance": "Model card, config snapshot, environment lock, change log.",
    "Complete Ranking": "Full ranking across all entities including benchmark stocks.",
    "Stock Deep Dive": "Per-stock detailed buy-and-hold attribution and contribution.",
}
