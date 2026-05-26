# REVIEW_REQUEST_ChatGPT55Pro_v12_design.md

> **Audience**: ChatGPT 5.5 Pro (methodology reviewer per master spec §0.5)
> **Author**: Strategist (Claude AI) on behalf of the project owner
> **Scope**: METHODOLOGY review of v11.x sprint arc (v11.2.0-stat through v11.4 LC v2.0 — all FAIL) AND design space for v12 (or formal v11.x retirement)
> **NOT in scope**: code review (parallel request goes to Codex — see `REVIEW_REQUEST_Codex_v12_design.md`)
> **Response format**: severity-tagged comments per §15 below
> **Deadline**: no rush. Major decision point. Quality > speed.

---

## §0 — Posture statement (please read first)

This is not a request to relitigate the v11.4 verdict. The v2.0 Liquidity Composite verdict is `FAIL` (1/7 criteria pass), sealed, immutable, and accepted. The verdict JSON `outputs/lc_v2_verdict.json` (SHA-256 `84a457e3f47f5ad5e11f8fc2f86adf03ea25e30fead4a99c084e99ccfa6d4180`) is the scientific record.

This **is** a request for methodology guidance on the **next decision**: given 3-of-3 consecutive pre-registered FAILs (v11.2.0-stat, v11.3.0 LC v1.0, v11.4 LC v2.0), should the project:

1. Pursue v12 (with what design)?
2. Formally retire v11.x (with what publication-worthy null finding)?
3. Pause and accumulate data (re-evaluate v2.0 as pre-registered in 2029)?

We are seeking your perspective on the methodology of that choice, NOT on whether the previous verdicts were correctly executed.

---

## §1 — Sprint arc summary (factual context)

### §1.1 — Three pre-registered hypotheses, three FAILs

| Sprint | Hypothesis | Method | Outcome | Date |
|---|---|---|---|---|
| **v11.2.0-stat** | Macro Risk Composite (MRC) statistical version predicts equity drawdowns | Quintile-cohort analysis with vintage-aware FRED data | **FAIL** | 2025 |
| **v11.3.0** | Liquidity Composite v1.0 (5 components, naive z-scoring) predicts SPXTR forward returns | Pre-registered predictive regression with HAC SE, Stambaugh, Campbell-Yogo | **FAIL** (0/7) | 2026-Q1 |
| **v11.4** | Liquidity Composite v2.0 (same 5 components + 4 amendments) predicts SPXTR forward returns | Same as v11.3 + (1) skewed-t conditional distribution per Hansen 1994, (2) two-sided criterion 4 (Amendment 2), (3) strict insufficient-sample gate (Amendment 4), (4) equipoise priors | **FAIL** (1/7) | 2026-05-25 |

### §1.2 — v11.4 sprint discipline (for calibration)

The v11.4 sprint was conducted under increasingly rigorous methodology:
- **Sealed pre-registration**: methodology committed via git annotated tag `v11.4-prereg-sealed` (commit `2a94417`, SHA-256 `c3c3ec1a…`) BEFORE running any verdict-bearing code
- **Multi-round reviewer corroboration**: ChatGPT 5.5 Pro + Codex reviewed the pre-reg over 4 rounds, contributed substantive corrections to criteria wording, library API usage, statistical formulas
- **9 Strategist mistakes caught and corrected** during pre-reg drafting, all documented in `DECISIONS.md`
- **Implementation phases A-E**: each phase reviewed against sealed pre-reg verbatim; one callback (Phase B+C) caught Strategist mistake #9 (4 wrong technical specs in implementation prompt); no code damage
- **Forward policy**: "Read sealed §X verbatim FIRST; treat Strategist examples as illustrative only" — eliminated mistakes #10, #11 in Phases D and E (0 callbacks across 25+ functions implemented)
- **21/21 §11.2 acceptance tests pass** at sprint close; 538/538 broader regression suite pass; 10/10 §16 seal-report criteria pass

The verdict cannot reasonably be attributed to implementation error. The architecture worked. The methodology held. The DATA did not support the test the methodology imposed.

### §1.3 — v2.0 verdict breakdown

| # | Criterion | Status | Value | Threshold |
|---|---|---|---|---|
| C1 | OOS R² @ 1Y LC_TIER2 > 0.005 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.005 |
| C2 | OOS R² @ 3Y LC_TIER2 > 0.020 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.020 |
| C3 | OOS R² @ 5Y LC_TIER2 > 0.040 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.040 |
| C4 | LC_FULL \|t_NW\| > 1.65 (Amendment 2, two-sided) | NOT_EVALUABLE_COUNTED_FAIL | — | 1.65 |
| C5 | ADF rejects all 5 components (Holm-Šidák α=0.05) | **FAIL_STATISTICAL** | max p ≈ 0.7648 (z4 DXY) | 0.05 |
| C6 | max VIF < 5.0 | **PASS** | ≈ 1.70 | 5.0 |
| C7 | Bonferroni any cell p < 0.0025 | NOT_EVALUABLE_COUNTED_FAIL | — | 0.0025 |

Decision rule: `n_pass >= 4 of 7` → PASS. Result: 1/7 pass → FAIL.

### §1.4 — Root cause analysis (Strategist's interpretation)

Two distinct failure modes, both traceable to specific design choices:

**Failure mode A — Data-window short → NOT_EVALUABLE on 4 of 7 criteria.**

Root cause: z4 (DXY_inv) data bottleneck. ICE_DXY historical parquet unavailable; pipeline fell back to DTWEXBGS (FRED's broad trade-weighted dollar index) starting 2006-01. The 120-month strict-shift PIT z-score warmup pushed the composite valid-start to ~2016-01. With data_cutoff ~2026-03 and OOS split at 2021-01-31, the OOS window is ~62 months. After accounting for HAC overlap (h-1 for h-year horizon), effective sample at 5Y horizon is ~3 observations — far below sealed §3.4's gate of `n_obs_oos < max(60, 3·HAC_lag)`.

This is **not a methodology problem; it's a data-window-vs-strict-gate interaction**. Amendment 4's strict gate (added to v2.0 specifically to prevent over-claiming on tiny samples) collided with the data history we actually had.

**Failure mode B — z4 (DXY) near-unit-root.**

C5 (ADF rejects all 5 at Holm-Šidák α=0.05) failed because z4 has max ADF p ≈ 0.7648. The DXY broad-trade-weighted index, even after the splice transformation and PIT z-scoring, is not stationary at conventional levels.

Critical observation: **z4 is a LEVEL transformation of DXY (log-levels-space additive splice per sealed §10.1)**. z1 (NetFed) is also a LEVEL (raw difference of WALCL−WDTGAL−RRPONTSYD). The other three (z2 M2 YoY, z3 BankLend YoY, z5 FundingStress spread) are rates or differences — and are presumably more stationary.

If z4 had been constructed as `Δlog(DXY)` (YoY or 12-month rate of change) rather than log-level, it would almost certainly pass ADF AND would not require 120-month PIT warmup AND would have longer data history (rate-of-change doesn't need long history to z-score).

**This is the substantive scientific finding of v11.4**: the v2.0 composite mixed level-family and rate-family variables, and the level-family components drove both failure modes.

### §1.5 — Sealed §6.4 trigger

v2.0 FAIL is the third consecutive pre-reg FAIL on this research line. Sealed §6.4 specifies that 3-of-3 FAIL is itself informative and triggers a meta-DECISIONS authorship documenting:
- Falsified claims (with confidence)
- Unresolved claims (where verdict was not_evaluable)
- Recommended pivots

This is a Strategist deliverable, currently pending Phase F closeout. The Strategist's draft will be circulated to reviewers; this REVIEW REQUEST is the upstream input that informs the meta-DECISIONS authorship.

---

## §2 — Owner's intuition (the question that prompted this review)

The owner asks (paraphrased):

> "Liệu chúng ta có nên phân tích thêm các tốc độ của liquidity như kiểu velocity of M2 money stock, YoY change về các thể loại liquidity, etc? Tôi thấy có cả M3 nữa này (MABMM301USM189S OECD series), có thể phân tích cả tốc độ YoY change gì đó nữa."

Translation: "Should we additionally analyze liquidity *speed* metrics — like M2 velocity, YoY changes on liquidity categories? I see there's M3 too (the OECD MABMM301USM189S series), we could analyze rate-of-change there as well."

This is a substantive design question that maps onto the failure-mode analysis: the owner is intuiting that **rate-of-change family** may be more appropriate than the level-family choices that drove v2.0 failures.

The owner is correct that this direction is plausible. **The methodology question for you is**: how do we pursue this WITHOUT committing post-hoc selection / garden-of-forking-paths sins?

---

## §3 — The candidate v12 hypothesis space

Strategist enumerates 7 candidate design directions for v12 (if v12 is pursued at all). Each has different methodological risks. We seek your guidance on which is most defensible.

### v12-A — Same 5 components, all converted to rate-of-change

Keep the v2.0 structure (5 components, 3 scopes LC_FULL/LC_TIER2/LC_DEEP, same composite weights) but:
- z1 NetFed: convert from LEVEL to **Δ12 log(NetFed)** (12-month log change)
- z4 DXY: convert from log-LEVEL to **Δ12 log(DXY)** YoY
- z2, z3, z5: already rate-family, unchanged
- Splice rules per sealed §10.1 remain
- PIT z-score, composite construction unchanged
- All 7 criteria, decision rule unchanged
- New oos_split_date (no reuse of 2021-01-31 v2.0 OOS window)

Rationale: targets the specific failure modes (level → stationary + longer history) with the smallest possible perturbation to the pre-registered v2.0 architecture. Minimal additional researcher degrees of freedom.

### v12-B — v2.0 + M2 velocity (M2V) as 6th component

Add z6 = M2V (M2V FRED series, quarterly, interpolated to monthly via spline or step function).

Theoretical grounding: Friedman-Schwartz (1963), Friedman (1969) — quantity theory of money posits velocity as the missing link between money stock and nominal output. 2020 M2V collapse from ~1.5 to ~1.1 was a regime-defining event.

Concerns:
- Quarterly frequency requires interpolation (peeking risk)
- M2V is a *derived* ratio of two series we likely already have correlations with
- Empirical evidence for M2V → equity returns specifically is THINNER than for M2V → inflation/nominal GDP

### v12-C — v2.0 + M3 YoY growth as 6th component

Add z6 = `Δ12 log(MABMM301USM189S)` (OECD-defined US M3 broader money aggregate, monthly).

Theoretical grounding: M3 includes large-denomination time deposits, institutional MMFs, repos — broader money than M2, captures more "near-money" liquidity.

Concerns:
- **MAJOR**: US Fed discontinued M3 reporting in 2006. The MABMM301USM189S series is **OECD-reconstructed**, not Fed-published. Reviewers should weigh whether OECD methodology produces a series fit for predictive analysis.
- Need to verify data quality, vintage discipline, splice consistency at the 2006 boundary

### v12-D — Pure velocity composite (radical redesign)

Components = {M2V, monetary base velocity, credit velocity (loans/deposits), DXY rate-of-change, funding stress rate-of-change}. Drop all level variables.

Theoretical grounding: if v2.0 FAILed on level-family interference, maybe a purely rate-family / velocity-family composite is internally consistent.

Concerns:
- **MAJOR methodology risk**: this is the version most subject to post-hoc-selection critique. We'd be choosing v12 design specifically because it avoids what failed in v2.0. Reviewers should weigh the multiple-testing inflation.
- More component selection degrees of freedom

### v12-E — Two-stage composite (stock + flow)

Construct TWO separate composites:
- LC_STOCK (levels: NetFed, DXY, ...) — tests level-family hypothesis
- LC_FLOW (rates: M2 YoY, BankLend YoY, M2V, M3 YoY, ...) — tests flow-family hypothesis

Pre-register criteria for each separately. PASS for v12 requires EITHER composite to pass (more permissive) OR BOTH to pass (less permissive).

Concerns:
- Doubles the multiple-testing burden
- Could be defended as separating two scientifically distinct hypotheses

### v12-F — Extension wait (no v12 implementation, just pre-commit to 2029 re-evaluation)

Don't implement v12. Instead, pre-commit (sealed pre-reg) to:
- In 2029-Q1, re-run the v2.0 pipeline on accumulated data through 2029-Q1
- By then, OOS window grows from 62 months → 98 months → many cells become evaluable
- Verdict published at that point

Rationale: if v2.0's only real problem is NOT_EVALUABLE (data-window-short), waiting fixes it. C5 (ADF) might still fail, but the other 4 NOT_EVALUABLE cells get a real evaluation.

Concerns:
- Long latency (3+ years)
- Doesn't address the C5 substantive finding (DXY non-stationarity)
- Owner may not have 3 years of patience

### v12-G — Formal retirement (no v12 implementation, publish 3-of-3 FAIL as the result)

Don't implement v12. The 3-of-3 FAIL across v11.2.0-stat, v11.3.0, v11.4 is itself a publishable null finding:
- Pre-registered hypothesis class: "macro/liquidity composites built from standard FRED inputs predict equity returns"
- Verdict across 3 increasingly rigorous attempts: pre-registered FAIL
- Publication venue: any reputable empirical finance journal accepts negative results when pre-registration is sealed

Rationale: rigor demands accepting null findings when the methodology says null. The architecture worked; we have the receipts.

Concerns:
- Doesn't continue the research program
- May be premature given that v2.0 specifically had data-window constraints (not pure null evidence)

---

## §4 — Specific questions for ChatGPT 5.5 Pro

We seek substantive opinion on the following. Please tag each response per §15.

### Q1 — Post-hoc selection critique

If we pursue v12-A (convert z1, z4 from level to rate-of-change), how does this differ from the textbook critique:
- "You ran v2.0, it failed, now you're modifying the components to make it pass — this is p-hacking / garden of forking paths"

Strategist's defense: the modification is **theoretically motivated** (rate-of-change family has stronger predictive-finance literature support per §5 below), NOT outcome-motivated (we're not picking variables because they DID pass; we're picking a family because the FAILURE MODE revealed a methodological mismatch).

But the reviewer's job is to push back. Is this defense adequate? What would strengthen it?

### Q2 — Multiple-testing correction across sprint iterations

Across v11.2.0-stat (1 hypothesis × N criteria), v11.3.0 (7 criteria), v11.4 (7 criteria) = 15+ tests already conducted. If v12 introduces 7 more criteria, family-wise error rate compounds.

What's the appropriate correction? Options:
- **Bonferroni across iterations**: significance threshold = 0.05 / (n_iterations × n_criteria) → very conservative
- **Pre-commitment penalty**: each iteration's pre-reg counts; v12 threshold tighter than v11.4's
- **Independence assumption**: v12 hypothesis class is methodologically distinct from v11.4 (level vs rate); treat as independent test → no compounding
- **Pre-registration absolution**: pre-registration eliminates p-hacking concern; multiple tests acceptable if each is sealed → no compounding

We lean toward (b) or (d). Which is more defensible? Are there explicit precedents in pre-registered empirical finance for this question?

### Q3 — Empirical finance literature on velocity vs level for equity prediction

The Strategist's read of the literature:
- **Adrian, Etula, Muir (2014, JF)** — intermediary leverage *growth* predicts cross-sectional equity returns. Rate-family.
- **López-Salido, Stein, Zakrajšek (2017, JF)** — credit spread *changes* and lending *growth* predict macro recessions. Rate-family.
- **Brunnermeier, Pedersen (2009, JF)** — funding liquidity *shocks* (not levels) predict market liquidity, asset prices. Rate/shock family.
- **Bauer, Swanson (2023, AER)** — monetary policy *surprise shocks* predict equity returns via term-premia. Shock-family.

We don't recall strong evidence for M2 LEVEL → equity returns specifically. M2 LEVEL → inflation, yes (quantity theory). M2 GROWTH → equity, weaker evidence.

Questions:
- (a) Are there papers we're missing on the LEVEL family predicting equity returns?
- (b) Is M2V specifically supported in equity-prediction literature? Or is its support mainly for inflation/nominal GDP?
- (c) What's the case for or against US M3 (OECD-derived) as a predictive variable?

### Q4 — Held-out OOS period for v12

v2.0 used OOS split = 2021-01-31 (data-driven; v1.0 sealed dates 2011-01/2013-01 pre-dated v2.0 composite valid start of 2016-01 per sealed §3.2.1).

For v12, we need an OOS period that hasn't been touched in v11.x. Options:
- (a) **Post-2024 OOS** (~16 months as of 2026-05). Too short for criteria at h≥1Y.
- (b) **Pre-1970 OOS** (data before v11.x methodology was conceived). Excellent regime separation but requires deep history sources.
- (c) **International OOS** (run v12 on EUR/JPY/GBP markets, US methodology). True out-of-population.
- (d) **Cross-validated OOS** (k-fold time-series CV with v12 windows non-overlapping with v11.x windows). Statistically clean but complex to pre-register.

What's the cleanest path? Are there published precedents?

### Q5 — Significance threshold for v12

If we pursue v12, should the criteria thresholds be:
- (a) **Same as v2.0** (e.g., OOS R² > 0.04 at 5Y) — same hypothesis class, same bar
- (b) **Tighter than v2.0** (e.g., OOS R² > 0.06 at 5Y) — penalty for iteration
- (c) **Looser than v2.0** (e.g., OOS R² > 0.02 at 5Y) — acknowledge that v2.0's bars were aggressive

Our intuition: (b) — make v12's bar TIGHTER as a multiple-testing penalty. But (b) makes PASS harder, possibly making v12 a near-certain FAIL.

### Q6 — When is 3-of-3 FAIL "enough"?

Stated bluntly: at what point should the research program be RETIRED rather than iterated? Specifically:
- (a) 3 FAILs across distinct hypothesis classes (v11.2 statistical, v11.3 LC v1.0, v11.4 LC v2.0) — significant enough to retire?
- (b) Need 5+ before retirement?
- (c) Retirement is qualitative; depends on whether failure modes are diagnosed and addressable
- (d) Failure-mode analysis suggests v2.0 was data-window-bound, not theory-bound → retain hypothesis class, iterate

What's the principled answer? Are there precedents in pre-registered finance literature for "we tried, it failed, here's the null"?

### Q7 — Publication strategy

If v12 is NOT pursued (v12-G), how should the 3-of-3 FAIL finding be published?

Possible venues / formats:
- (a) Working paper at NBER / SSRN: "Liquidity Composites Do Not Robustly Predict Equity Returns: Evidence from Three Pre-Registered Tests"
- (b) Journal submission to *Journal of Financial Economics* (negative results section if any)
- (c) Replication-and-extension paper extending Adrian-Etula-Muir or similar with pre-registered failure
- (d) Methodology paper on the sealed-pre-reg architecture itself, with the failures as evidence of discipline

Which venue is most appropriate? Are there examples of pre-registered failure papers in empirical finance to model on?

### Q8 — Velocity-specific theoretical grounding

The owner's specific intuition is about VELOCITY (turnover speed). Theoretically:
- M2V = nominal_GDP / M2_stock = inverse money demand
- High M2V = money working harder = expansionary
- Low M2V = money idle (precautionary cash hoarding) = recessionary
- 2020 M2V collapse to ~1.1 was unprecedented

Question: is velocity a fundamentally different variable family from "rate of change of stock", or is it mathematically related such that adding M2V to a composite that already has M2 YoY growth adds little marginal information?

Specifically: `M2V = nominal_GDP / M2` ⇒ `Δlog(M2V) = Δlog(nominal_GDP) − Δlog(M2)`. So M2V change is mechanically (Δ nominal GDP − Δ M2). If we already have M2 growth as z2, are we double-counting?

Or does VELOCITY capture something dynamically distinct (regime-shift behavior, precautionary demand) that pure flow growth doesn't?

### Q9 — Strategist's leaning, for your pushback

The Strategist's current lean:
- **v12-A is most defensible** (smallest perturbation, theoretically grounded, minimal new researcher DOF)
- Pre-register with TIGHTER thresholds (Q5 option b) as multiple-testing penalty
- Use post-2024 OOS plus extend-to-2029 dual track (Q4 hybrid)
- If v12-A fails, retire the research program (Q6 — diagnosis exhausted)

We seek pushback on each leaning. What's wrong with this plan?

### Q10 — Anything we haven't asked

If there's a methodology angle we've missed entirely, please raise it.

---

## §5 — Pre-commitments (these hold regardless of your input)

Whatever the review concludes, the project pre-commits to:

1. **No reverse-engineering v2.0 verdict.** The verdict is sealed, signed, and final.
2. **No retroactive amendment of v11.x methodology.** Sealed pre-regs are immutable.
3. **Same seal-then-implement discipline for v12** (if pursued). Multi-round reviewer corroboration, sealed-immutable artifact, callback safety net for implementation.
4. **Explicit theoretical justification per v12 component**, citing literature, NOT citing "what would have made v2.0 pass."
5. **Pre-registration BEFORE data exploration.** v12 sealed pre-reg complete before any candidate data analysis.
6. **Public attribution.** Reviewer contributions documented in v12 pre-reg's authorship section, same as v11.4.

These commitments are the floor. Your review can raise them higher.

---

## §6 — What we're NOT asking

Out of scope for this review request:

- Code review of Phase A-E implementations (parallel request to Codex)
- Recomputation of v2.0 verdict (sealed and final)
- Library version sensitivity testing (Codex empirical task)
- Specific bootstrap parameter recommendations (sealed §3.8 IMMUTABLE)
- Phase F deliverables (`requirements.lock` pin + pinned re-run + display framing)
- Personal opinions on the owner's research preferences

---

## §7 — Parallel review

A separate request goes to Codex (`REVIEW_REQUEST_Codex_v12_design.md`) covering:
- Empirical execution: pull candidate v12 component data, compute ADF/KPSS/autocorrelation for each
- Library-version sensitivity verification (arch 7.0 vs 8.0)
- Cross-check verdict JSON byte-identity claim
- Data quality assessment for M3 (OECD series), M2V interpolation, etc.

Your methodology input + Codex's empirical findings together will inform §6.4 meta-DECISIONS and the v12 go/no-go decision.

---

## §8 — Artifacts available for your reference

All published to `https://github.com/mvfoundation01/macro/tree/spec/liquidity-composite-v2.0`:

| Artifact | Path | Purpose |
|---|---|---|
| Sealed v2.0 pre-reg | `buffet_indicator/specs/MV_LIQUIDITY_COMPOSITE_V2_PREREGISTER.md` | Authoritative methodology |
| Sealed SHA-256 verification | embedded above | `c3c3ec1a83e4cb9cf8f7c35523f0542530cfc4bb2e986ae49ddab23c1bed8b05` |
| v2.0 verdict JSON | `buffet_indicator/outputs/lc_v2_verdict.json` | Final empirical result |
| Verdict JSON SHA-256 | `buffet_indicator/outputs/lc_v2_verdict.json.sha256` | `84a457e3f47f5ad5e11f8fc2f86adf03ea25e30fead4a99c084e99ccfa6d4180` |
| Human-readable summary | `buffet_indicator/outputs/lc_v2_verdict_summary.md` | Plain-language verdict |
| Vintage approximation note | `outputs/v2_sprint_vintage_approximation_note.md` | §B Phase B+C arbitration (PIT vintage = observation-date) |
| Sprint progress reports | `outputs/v2_sprint_phase_progress_*.md` | Session-by-session log |
| DECISIONS log | `DECISIONS.md` | All arbitration history |
| Phase E source code | `buffet_indicator/src/models/v2_panel_builder.py`, `v2_verdict_run.py`, `v2_criteria.py` | Implementation |

You may request specific artifact contents to be pasted in your reply if needed. Strategist will provide.

---

## §9 — Owner's broader context

The project owner is a non-academic empirical investor building this for personal decision-making, NOT for academic publication primarily. The seal-then-implement architecture and pre-registered evaluation discipline are owner-led methodological choices to:
- Self-enforce intellectual honesty against confirmation bias
- Generate auditable scientific record
- Allow third parties (you) to evaluate the work without conflict of interest

The owner is comfortable with a FAIL outcome and is asking the right next question. Your role is to ensure the next step (v12 or retirement) is also methodologically defensible.

---

## §10 — A note on the cost of caution

A standing trade-off the owner faces:
- **More iterations** = more multiple-testing burden, slower convergence to truth, but more chances to find genuine signal
- **Fewer iterations / earlier retirement** = lower false-positive risk, but possible failure to find signal that exists

The owner has demonstrated commitment to rigorous pre-registration (3 sealed pre-regs, 25+ reviewer-corroborated decisions). The question is now: given the sunk cost of methodological infrastructure, is one more carefully-designed iteration (v12) worth the multiple-testing penalty?

Your honest opinion on this trade-off is welcomed.

---

## §11 — On 'velocity' family epistemics

A meta-question that bridges Q3 and Q8:

The owner's intuition about velocity is grounded in Friedman's quantity theory. But Friedman's mature work (1969, 1971 *Optimum Quantity of Money*) treats velocity as an INPUT to monetary policy thinking, NOT primarily as a predictor of asset returns. The asset-return-prediction literature uses velocity mostly through different channels (intermediary-balance-sheet shocks, credit-market frictions, etc.).

So: is the owner's intuition about velocity-predicts-equity-returns:
- (a) A real signal that the literature has under-tested?
- (b) A theoretically suggestive but empirically weak hypothesis?
- (c) Mathematically constrained by what's already in v2.0 (M2 YoY)?

We seek your honest read.

---

## §12 — Cross-iteration data leakage

A subtle methodology concern:

The same underlying data (FRED M2SL, BUSLOANS, etc.) has been used across v11.2.0-stat, v11.3.0, v11.4. Across these iterations, the methodology has been adjusted but the data substrate is largely shared.

Is there an information-leakage concern when v12 uses the SAME data substrate (just different transformations)? Or is data-substrate sharing acceptable as long as:
- Transformations are pre-registered
- OOS windows don't overlap across iterations
- Theoretical motivation is independent

We lean toward "acceptable with proper pre-registration." But want to be sure.

---

## §13 — On retirement / publication framing

If v12 is NOT pursued and we publish the 3-of-3 FAIL finding:

Strategist proposes the framing: *"Pre-registered Tests of Three Macro/Liquidity Composites for Equity Return Prediction: Three Null Results"*

Key elements:
- Independent pre-registration of each hypothesis (sealed-immutable artifacts)
- Methodology evolved between iterations (transparency)
- Each verdict is mechanical, not adjudicated by author preference
- The architecture itself is contribution-worthy (methodology paper potential)

Is this framing accurate? Are there pre-registered finance papers we should cite as precedent?

---

## §14 — Specific intellectual provocations (please push back)

Strategist intentionally states three claims that may be wrong; please challenge with evidence:

1. **CLAIM**: "v2.0 FAILed because z1 and z4 were level-family while z2, z3, z5 were rate-family. Converting z1 and z4 to rate-family would fix the failure modes."
   - **Possible counter**: maybe levels are correct for these variables, and the data window was simply too short. Maybe v2.0 just needs more time.

2. **CLAIM**: "Velocity (M2V) and rate-of-change-of-stock (M2 YoY) capture different information; both belong in v12."
   - **Possible counter**: mathematically related (Δlog(M2V) = Δlog(GDP) − Δlog(M2)), so adding both inflates correlation with GDP cycles.

3. **CLAIM**: "M3 (OECD-derived MABMM301USM189S) is a legitimate predictor variable for v12."
   - **Possible counter**: US Fed discontinued M3 in 2006 specifically because they didn't think it added information beyond M2. OECD reconstruction may not be reliable.

Please push back on each.

---

## §15 — Response format

Per master spec §0.5.3 adapted for design-question reviews. Tag each comment with:

| Tag | Meaning |
|---|---|
| `ENDORSE` | Agree with Strategist's position |
| `CHALLENGE` | Disagree, here's why |
| `REFINE` | Agree directionally but suggest modification |
| `ESCALATE` | Raises a question Strategist should think more about |
| `LITERATURE` | Points to a paper/methodology that's relevant |
| `BLOCKER` | If v12 cannot proceed without addressing |
| `MAJOR` | Important consideration |
| `MINOR` | Nice-to-have refinement |

Format: number your comments (1, 2, 3, ...). For each, cite which §X.Q this responds to (e.g., `[§4.Q1 ENDORSE]` or `[§14 CLAIM-1 CHALLENGE]`).

End with a **VERDICT** section stating:
- Most defensible v12 design (your top pick from v12-A through v12-G)
- Confidence in that pick (0-100)
- Top 3 risks the Strategist should mitigate
- Pre-conditions before v12 is sealed (if any)

---

## §16 — Acknowledgment of your previous contributions

Across the v11.4 sprint, ChatGPT 5.5 Pro contributed substantively (per `DECISIONS.md`):
- Round 2 review: caught the algebraically-redundant two-tier decision rule
- Round 3 review: caught Strategist mistake #4 (8.9% arithmetic fabrication; actual value 2.7566%)
- Multiple methodology corrections to criteria wording
- Hansen 1994 skewed-t implementation guidance

We expect your work on v12 to be of similar quality. Authorship credit will be documented in the v12 sealed pre-reg (if v12 is pursued) or in the meta-DECISIONS / null-finding paper (if v12 is not pursued).

---

## §17 — One ask, finally

If you have to choose ONE thing to focus your review on, it is:

> **"Should v12 even be pursued? Or is the 3-of-3 FAIL itself the result, and the project should accept that and write it up?"**

That single question is the most important one. All others are subsidiary.

— Strategist (Claude AI)
2026-05-25

End of REVIEW REQUEST. Standing by for your response.
