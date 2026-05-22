"""Session 7 §2.1.2 — RRPONTSYD pre-2013 empirical character.

Pulls RRPONTSYD daily history from FRED, computes monthly statistics, and
quantifies the pre-2013-09-23 vs post-2013-09-23 character. Used to validate
the DECISIONS.md (2026-05-24) §Q1 zero-fill rationale ("facility existed but
near-zero balances pre-2013").

References
----------
* prompt/052226/PROMPT_v11_3_session_7_DECISIONS_investigation_F_G.md §2.1.2
* DECISIONS.md 2026-05-24 §Q1
"""
from __future__ import annotations

# --- sys.path bootstrap (must precede any src.* imports) ---
import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# -----------------------------------------------------------

import yaml
import pandas as pd
from fredapi import Fred

CFG_PATH = _PROJECT_ROOT / "config.yaml"


def main() -> int:
    api_key = (yaml.safe_load(CFG_PATH.read_text()) or {}).get("fred_api_key")
    if not api_key or api_key == "PASTE_YOUR_32_CHAR_KEY_HERE":
        print("ERROR: FRED API key not configured in config.yaml")
        return 1

    fred = Fred(api_key=api_key)
    raw = fred.get_series("RRPONTSYD", observation_start="2003-02-01")
    raw.index = pd.to_datetime(raw.index)
    raw.name = "rrpontsyd"

    monthly = raw.resample("ME").last()
    cutoff = pd.Timestamp("2013-09-23")
    pre = monthly[monthly.index < cutoff]
    post = monthly[monthly.index >= cutoff]

    pre_nonnull = pre.dropna()
    post_nonnull = post.dropna()

    pct_zero_or_nan_pre = (
        (pre.isna() | (pre.abs() < 5.0)).sum() / max(1, len(pre))
    )

    print("=" * 72)
    print("RRPONTSYD pre-/post-2013-09-23 empirical character")
    print("=" * 72)
    print(f"Pre-2013-09 monthly obs (total):           {len(pre)}")
    print(f"Pre-2013-09 monthly obs (non-NaN):         {len(pre_nonnull)}")
    print(f"Pre-2013-09 max value ($B):                {pre_nonnull.max():.2f}")
    print(f"Pre-2013-09 mean of non-NaN ($B):          {pre_nonnull.mean():.2f}")
    nz_pre = pre_nonnull[pre_nonnull.abs() >= 5.0]
    if len(nz_pre) > 0:
        print(f"Pre-2013-09 mean excluding |x|<$5B ($B):   {nz_pre.mean():.2f}")
    else:
        print("Pre-2013-09 mean excluding |x|<$5B ($B):   no obs in that bucket")
    print(
        f"Pre-2013-09 fraction zero or NaN or <$5B:  {pct_zero_or_nan_pre*100:.1f}%"
    )
    print(f"Pre-2013-09 obs |x| >= $5B:                {(pre_nonnull.abs() >= 5.0).sum()}")
    print()
    print(f"Post-2013-09 monthly obs (total):          {len(post)}")
    print(f"Post-2013-09 monthly obs (non-NaN):        {len(post_nonnull)}")
    print(f"Post-2013-09 max value ($B):               {post_nonnull.max():.2f}")
    print(f"Post-2013-09 mean ($B):                    {post_nonnull.mean():.2f}")
    print()
    print("Pre vs post means ratio:", f"{(pre_nonnull.mean() or 0) / max(post_nonnull.mean(), 1.0):.4f}")
    print()
    # Verdict gates per prompt §2.1.2:
    # (a) >95% of pre-2013-09-23 non-NaN values are zero or near-zero ($-billions scale).
    # (b) Mean of pre-2013 non-NaN values << mean of post-2013 non-NaN values.
    a_threshold_pct = (pre_nonnull.abs() < 5.0).sum() / max(1, len(pre_nonnull)) * 100.0
    print("Verdict gates:")
    print(
        f"  (a) Pre-2013 non-NaN values with |x|<$5B: "
        f"{a_threshold_pct:.1f}%  (>=95% expected)"
    )
    print(
        f"  (b) Pre mean ({pre_nonnull.mean() or 0:.2f}) << post mean "
        f"({post_nonnull.mean():.2f})? "
        f"{'YES' if (pre_nonnull.mean() or 0) < 0.05 * post_nonnull.mean() else 'NO'}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
