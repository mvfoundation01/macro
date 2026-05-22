"""Sanity check: verify master & loader outputs fall within expected real-world ranges.

Run from project root: python scripts\sanity_check.py
"""
from __future__ import annotations
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path even when invoked from elsewhere
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.ingest.master_archive import load_master
from src.ingest.fred_loader import load_buffett_fred
from src.ingest.shiller_loader import load_shiller

# Expected real-world ranges (May 2026)
EXPECTED = {
    "wilshire_latest_pts":   (55_000, 80_000),   # FT-Wilshire ~68k
    "wilshire_lag_days":     (0, 7),
    "equities_all_trillion": (75.0, 100.0),       # $80-95T
    "gdp_trillion":          (28.0, 35.0),        # $30-33T
    "bi_allequity_pct":      (220.0, 350.0),
    "cape":                  (28.0, 50.0),        # current expensive market ~35-40
    "gs10":                  (0.025, 0.075),      # 2.5% - 7.5%
    "wilshire_usd_trillion": (60.0, 80.0),
    "bi_wilshire_pct":       (175.0, 260.0),
}

ok = True
issues: list[str] = []

def check(name: str, value: float, fmt: str = "{:,.2f}") -> None:
    global ok
    lo, hi = EXPECTED[name]
    in_range = lo <= value <= hi
    status = "OK " if in_range else "OUT"
    fmtval = fmt.format(value)
    print(f"  [{status}] {name:32s} = {fmtval:>14s}   (expected {lo:,}–{hi:,})")
    if not in_range:
        ok = False
        issues.append(f"{name}={value} not in [{lo},{hi}]")

print("=" * 70)
print(" SANITY CHECK — Buffett Ingestion v1.0")
print(" Run:", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
print("=" * 70)

print("\n[1] Master archive: wilshire_5000")
w = load_master("wilshire_5000")
days_lag = (datetime.now().date() - w.latest.date()).days
print(f"  range  : {w.earliest.date()} → {w.latest.date()}")
print(f"  n_obs  : {w.n_observations:,}")
print(f"  sources: {w.sources_used}")
check("wilshire_latest_pts", float(w.data.iloc[-1]))
check("wilshire_lag_days",   float(days_lag), fmt="{:.0f}")

print("\n[2] FRED")
cfg_path = _PROJECT_ROOT / "config.yaml"
cfg = yaml.safe_load(cfg_path.read_text())
fred = load_buffett_fred(api_key=cfg["fred_api_key"])
eq_all_t = float(fred["equities_all"].data.iloc[-1]) / 1_000_000  # M → T
gdp_t    = float(fred["gdp"].data.iloc[-1]) / 1_000               # B → T
check("equities_all_trillion", eq_all_t)
check("gdp_trillion",          gdp_t)
check("bi_allequity_pct",      eq_all_t / gdp_t * 100.0)

print("\n[3] Shiller")
sh = load_shiller()
cape = float(sh.data["cape"].dropna().iloc[-1])
gs10 = float(sh.data["long_rate_gs10"].dropna().iloc[-1])
# Auto-detect units: if >1, it's percent; convert to decimal
if gs10 > 1:
    gs10 = gs10 / 100.0
check("cape", cape)
check("gs10", gs10, fmt="{:.2%}")

print("\n[4] Wilshire → USD (Wilshire scaling drift: 1985 $1.00B/pt → 2020 $1.05B/pt)")
year = datetime.now().year
mult = 1.00 + (year - 1985) * (0.05 / 35.0)   # linear interp + extrapolation
wilshire_usd_t = float(w.data.iloc[-1]) * mult / 1_000.0
print(f"  scaling multiplier ({year}): ${mult:.4f}B/pt")
check("wilshire_usd_trillion", wilshire_usd_t)
check("bi_wilshire_pct",       wilshire_usd_t / gdp_t * 100.0)

print("\n" + "=" * 70)
print(" SUMMARY")
print("=" * 70)
if ok:
    print(" ✅ ALL CHECKS PASSED — ingestion layer ready for transform layer.")
    sys.exit(0)
else:
    print(f" ❌ {len(issues)} CHECK(S) FAILED:")
    for i in issues:
        print(f"   - {i}")
    print("\n  Investigate before proceeding to transform/.")
    sys.exit(1)
