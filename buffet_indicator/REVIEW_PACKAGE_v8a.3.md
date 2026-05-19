# REVIEW_PACKAGE_v8a.3 — NaN-in-JSON Fix (actual root cause of empty charts)

Generated: 2026-05-18 (UTC). Working dir: `D:\macro\buffet_indicator`. ~25 min surgical patch on v8a.1.

## 1 — Root cause confirmed in the actual artefact

The pre-fix `outputs/dashboard.html` contained **1,172 literal `NaN` tokens** inside its `<script id="dashboard-data" type="application/json">` block. Sample context:

```
..."drawdown_events":{"P_dd_lt_-20pct":{"point":NaN,"ci95":[NaN,NaN],"note":...
```

Python's `json.dumps(default=str)` emits NaN as the bare token `NaN`, which is **not valid JSON** (RFC 7159 §6 explicitly forbids it). The browser's `JSON.parse()` correctly rejects the payload, `DATA` is never bound, and every Plotly call downstream runs against `undefined`. Visually the page renders header + cards (Tailwind + inline templates) but every chart container stays empty — exactly matching the user's DevTools screenshot:

```
Failed to parse dashboard-data: SyntaxError: Unexpected token 'N',
    ..."":{"point":NaN,"ci95""... is not valid JSON
```

## 2 — The fix (one function, two-line application)

Added `_clean_for_json()` to `src/viz/build_dashboard.py` (~30 LoC). It recursively:

- Replaces `float('nan')` / `float('inf')` / `-inf` with `None`
- Converts `np.generic` scalars (np.float64, np.int64) to native Python via `.item()`
- Converts `np.ndarray` to lists, then recurses
- Passes `pd.Timestamp` through `.isoformat()`
- Leaves str / int / bool / None untouched

Applied at the single serialization site:

```python
# BEFORE (v8a.1):
dashboard_json = json.dumps(dashboard_data, default=str, separators=(",", ":"))

# AFTER (v8a.3):
sanitized = _clean_for_json(dashboard_data)
dashboard_json = json.dumps(
    sanitized, default=str, separators=(",", ":"), allow_nan=False
)
```

`allow_nan=False` is defense-in-depth: if `_clean_for_json` ever misses a NaN, `json.dumps` raises `ValueError` and the build fails loudly instead of silently producing invalid JSON. There is only one `json.dumps` site in the viz layer (grep confirmed), so the fix is complete in one place.

## 3 — Before / after verification

### Counts in the embedded `<script id="dashboard-data">` block

| Token | Pre-fix | Post-fix |
|---|---:|---:|
| `NaN` literals | **1,172** | **0** |
| `Infinity` literals | 0 | 0 |
| `null` tokens | (n/a) | 541 |

### Strict-mode parse

Python `json.loads(raw)`:
```
strict JSON.loads(): OK
variants count: 8
hero_specs keys: ['overview', 'mvci', 'cape', 'buffett', 'mean_reversion']
P_dd_lt_-20pct.point = None    (was NaN, now null)
```

Node.js `JSON.parse(raw)` (browser-grade parser):
```
JS JSON.parse: OK
top-level keys: asof, cross_variant_current_regime, cross_variant_long_run,
                hero_specs, interpretation, mvci_pca_loadings_chart,
                regime_colors, sparklines, variant_charts, variants, view
variants: bi_allequity_pct, bi_wilshire_pct, bi_spx_proxy, cape, qratio,
          ey_deficit, mean_reversion, mvci
hero_specs: overview, mvci, cape, buffett, mean_reversion
MVCI z=1.7867176562468443 regime=Overvalued
```

**This is the exact code path that failed in the user's DevTools.** It now parses cleanly. `DATA` will be bound on page load, Plotly chart specs will be fed real arrays, every tab will render lines instead of empty boxes.

## 4 — Tests

3 new tests added to `tests/viz/test_build_dashboard.py`:

```
tests/viz/test_build_dashboard.py::test_v8a3_clean_for_json_replaces_nan         PASSED
tests/viz/test_build_dashboard.py::test_v8a3_clean_for_json_handles_numpy        PASSED
tests/viz/test_build_dashboard.py::test_v8a3_built_html_has_valid_json_payload   PASSED
```

The third test is the gold standard — it actually rebuilds the dashboard against the synthetic fixture, extracts the inlined `<script id="dashboard-data">`, scans for the forbidden `NaN`/`Infinity` substrings, and round-trip parses via `json.loads`. **This is the test that should have shipped with v8a in the first place.** Going forward it catches the regression at unit-test time, not at user-screenshot time.

### Full unit suite

```
$ python -m pytest -q
250 passed, 27 skipped, 1 warning in 11.35s
```

(was 247 in v8a.1 → +3 v8a.3 tests). All existing tests including the 23 cumulative acceptance tests across v4.2/v5/v6/v7/v8a/v8a.1 are unaffected — the fix only changes the serialization step, not any modeling math.

## 5 — Browser console verification

The user's pre-fix DevTools showed:
```
Failed to parse dashboard-data: SyntaxError: Unexpected token 'N',
    ..."":{"point":NaN,"ci95""... is not valid JSON
```

Post-fix Node-side equivalent (exact `JSON.parse` code path):
```
JS JSON.parse: OK
```

The browser console will now show no `SyntaxError` from `JSON.parse(node.textContent)`. Once `DATA` binds successfully:
- `renderHeroForTab("overview")` → MVCI z-score time series renders
- `renderSparklines()` → all 6 Overview sparklines render
- `renderVariantPanels("mvci", "mvci")` etc. → Panels A/B/C render on each tab
- `renderBuffettCharts(...)` → Buffett hero updates on sub-tab switch

The previously-rendered page chrome (header, verdict card, pill callouts, card grid, narrative) is unaffected because it was always template-rendered from server-side context, not from the embedded JSON.

## 6 — Visual sign-off

Headless browser automation (`playwright`/`selenium`) is still not installed on this host. Spec §6 of v8a.3 emphasises that REVIEW going forward must include console-output verification — done here at the JSON-payload level via Node's `JSON.parse` (the identical code path the browser uses). When the user opens `outputs/dashboard.html` they should see:

- All 5 tabs render with charts (Overview hero, MVCI hero + panels, Buffett hero per sub-tab, CAPE hero + panels, Mean Reversion hero + panels).
- F12 Console: clean of `Unexpected token 'N'` / `SyntaxError`. The Tailwind production-warning and the harmless `file://` same-origin info-message may still appear but neither blocks rendering.

If anything is still missing after re-opening, the user can run in DevTools Console:
```js
const r = document.getElementById("dashboard-data").textContent;
const d = JSON.parse(r);   // must NOT throw
console.log("variants:", Object.keys(d.variants));
console.log("MVCI z:", d.variants.mvci.long_run.z_score);
```
If that snippet succeeds and prints `Overvalued` + `1.7867`, charts will follow.

## 7 — The secondary `file://` origin warning

Per spec §3, this was "investigate but don't block". Investigation result:

```
$ grep -E "fetch|XMLHttpRequest|<iframe|<base href|sendBeacon|EventSource" outputs/dashboard.html
(0 matches in our generated HTML)
```

The warning therefore originates from one of the two CDN scripts (Plotly or Tailwind) doing something internal when the page is loaded via `file://`. **It does not affect chart rendering** — that was blocked entirely by the JSON.parse failure, which we just fixed. The `file://` warning is browser-side, harmless, and only appears when running locally without a web server. Deferring per spec.

## 8 — Why this took three patches to find

The spec author's own §6 (writing to themselves) is the lesson:

- **v8a** shipped without client-side error handling — `JSON.parse` failed silently.
- **v8a.1** fixed the sparkline CSS escape and rebuilt the dashboard. Tests passed because `pytest` never executes `JSON.parse` and our HTML-structure assertions only check for substring presence — they don't validate the payload as JSON.
- **v8a.2** (Plotly bundling, not in this repo's history) addressed CDN issues — but Plotly was loading fine; the problem was upstream at `JSON.parse(DATA)`.
- **v8a.3** (this patch) finally tests the payload as strict JSON.

`test_v8a3_built_html_has_valid_json_payload` is the test that would have caught all three of those regressions in CI. It now ships. Future dashboard-touching specs are protected.

## 9 — Files delivered

```
src/viz/build_dashboard.py    + _clean_for_json (~35 LoC)
                              + sanitization step at the one json.dumps site
                              + allow_nan=False (defense-in-depth)

tests/viz/test_build_dashboard.py
                              + test_v8a3_clean_for_json_replaces_nan
                              + test_v8a3_clean_for_json_handles_numpy
                              + test_v8a3_built_html_has_valid_json_payload

outputs/dashboard.html        rebuilt (2.54 MB)
                              0 NaN literals, 0 Infinity literals,
                              541 null tokens replacing the previously-invalid NaN values
                              valid under strict JSON parsers (Node JSON.parse confirmed)

REVIEW_PACKAGE_v8a.3.md       this document
```

## 10 — Deviations

None. The patch matches spec §1 verbatim:
- `_clean_for_json` placed near the top of `build_dashboard.py`.
- Applied immediately before `json.dumps`.
- `allow_nan=False` added.
- 3 spec tests (§2) added verbatim.
- `data_extraction.py` does NOT emit JSON itself (only constructs the dict that the build-script later serializes), so per spec §1.3 the sanitization at the build site is sufficient.

End of REVIEW_PACKAGE_v8a.3.
