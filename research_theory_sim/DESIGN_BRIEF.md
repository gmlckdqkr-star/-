# TS1 design brief: a new market theory -> a synthetic market -> a trading rule designed ONLY on synthetic data

You are a BLIND designer. You invent a new theory of how an equity index price is formed, build a simulator of that
theory, and design a trading rule using only data your own simulator generates. You never look at any real market data or
any earlier research result. Your rule will be frozen (hash-committed) and then tested once, by someone else, on about a
century of real history. An honest failure is an acceptable outcome. Contamination is not.

## 1. Blindness rules (hard)
- You may READ only: this file; `/mnt/project-files/research/theory_sim/common/exec_engine.py`; files you create in your
  own folder `/mnt/project-files/research/theory_sim/design/<LANE>/` (the tournament agent: all `design/*` folders).
- You may WRITE only inside your own folder.
- FORBIDDEN (do not open, list, grep or import):
  - every other path under /mnt/project-files (research/*, reports/*, tools/*, handoff/*, uploads/*, other lanes' folders,
    research/theory_sim/test/, research/theory_sim/holdout/, research/theory_sim/TEST_PROTOCOL.md), any MEMORY.md,
    /tmp/claude/memory, the git checkout /home/user/-;
  - the project's named forbidden list: reports/best_results_summary_*, research/deep/, research/audit/, any diag/,
    research/mass_scan/, research/us_mix_sb_oos/, research/user_port/, research/c3_relax/RESULT_RELAX_KO.md and
    results/holdout_once.csv, research/user_v104/RESULT_V104_KO.md and results/, research/user_v107/ (RESULT_V107_KO.md,
    results/, unseen/, final/, SHARE_V107_vs_s085_KO.md), research/user_port4/ (RESULT_KO.md, results/),
    research/c3_stock_combo/, research/c3_create/fwd/, research/s085_contra/holdout/, tools/s085_now/out/, tools/s085_now/cache/;
  - the lab runner (research/lab): it reads real prices;
  - any network use: no WebSearch / WebFetch, no MCP data tools (Twelve Data, Alpha Vantage, FMP, Bigdata, Gemini,
    Financial Datasets, Exa, ...), no pip/conda download of data packages (yfinance, pandas-datareader, ...).
    No price, rate, index or macro data of any real asset or period.
- Do not calibrate to remembered history: no specific crashes, years, decades, named indices or their average returns or
  volatilities. Priors must be WIDE and argued from theory / first principles. Where you could not avoid general
  background knowledge (for example "equity volatility is of order 10-40% a year"), say so in THEORY.md under
  "Background knowledge used".
- If your context already contains project memory, research results or market numbers (strategy names with returns,
  index statistics), ignore them, do not use them, and record in READ_LOG.md that such context was present.
- Write READ_LOG.md: every file you opened (path and why). An auditor checks it and greps your code for file reads.

## 2. What the real test will look like (structural facts only, no data)
- Underlying: a broad, liquid equity PRICE index (no dividends), daily closes. It is not named on purpose.
- Instruments: a 3x daily-leveraged product on that index plus cash. A target level L in [0, 3] is held as L/3 in the 3x
  product and the rest in cash. The rules are exactly those in `common/exec_engine.py`: 0.3% cost per trade, a target
  decided at close t trades at close t+2, levels in 0.5 steps, NO rebalancing while the held level is unchanged (the
  product/cash mix drifts until the level changes), 22% yearly tax on net realised gains above a deduction, final
  liquidation tax. The 3x product costs 2*rf + 2.45%/yr on top of 3x the index; cash earns max(rf - 2%, 0) after 15.4% tax.
- Inputs the rule may read at close t (and nothing else: no volume, no volatility index, no fundamentals):
  `close` = index level up to t (normalised arbitrarily: the rule must be scale-invariant),
  `rf` = daily short-term risk-free rate up to t (simple, per day; it is also what cash pays and what leverage costs),
  optional `y10` = 10-year government bond yield in percent up to t. In early decades the rates may move in monthly steps.
- Headline metric: the MEDIAN over 30-year paths of the after-tax CAGR (after the final liquidation tax), computed with
  the same engine. The headline paths are built by resampling the real daily history in blocks of 250 trading days into
  30-year paths, so predictive structure longer than about one year is partly broken at block joins. Single real-history
  paths are reported too, plus same-basis buy-and-hold of 1x, 2x and 3x.
- Robustness rows that will be reported: delay 3 and delay 5 days; cost 0.6% per trade.
- The user's goal is the highest possible long-run after-tax growth (they hope for 30%/yr or more). Do not bend the priors
  toward that number: a rule that only works in a world tuned to make it work will fail the real test.

## 3. Process (in this order; take every timestamp from `date -u +%Y-%m-%dT%H:%MZ`)
1. THEORY.md, written BEFORE any simulation: name; the mechanism (who trades, under which constraints, why prices move the
   way they do); why it should exist in real markets (economic argument); what it predicts that a random walk does not;
   how it could be false. It must be NEW: you may use known ingredients, but the mechanism / combination is your own, not a
   restatement of a textbook model. Section "Priors": every simulator parameter with a range and the reason. Define a
   "mechanism-off" world (same overall scale, mechanism disabled). Then write a line `PRIORS_FROZEN <timestamp>` and do not
   change the priors after you start designing the rule.
2. sim.py: `simulate(P, T, seed, mechanism=True) -> dict(r=(P,T), rf=(P,T), y10=(P,T) or None, params=...)`, parameters
   drawn PER PATH from the prior (each path is a different world). `r[:, 0] = 0`. Vectorised numpy; 2000 paths x 7860 days
   should run in a few minutes at most. Print descriptive statistics of your synthetic worlds; they describe the theory,
   they are not targets.
3. Rule design on synthetic data only:
   - Derive the rule from the theory: what would an informed trader do if the theory were true? Online estimation inside
     the rule is allowed (filters, rolling or expanding estimates), using data <= t only.
   - Selection on seeds 1-999 only; final numbers on fresh seeds >= 10000 that were never used for selection. Count every
     variant you evaluate (N, including grid points). At most 6 tunable parameters in the final rule.
   - Always compare with same-basis hold 1x / 2x / 3x on the same paths and with constant-level rules.
   - Robustness: delay 3 and 5, cost 0.006, prior narrowed / widened, and the mechanism-off world (report the loss there
     against the best constant-level rule).
4. Freeze: rule.py (interface below), synth_results.json, design_log.md.

## 4. rule.py interface (strict)
- Pure numpy: imports `numpy` and `math` only. No file or network I/O. Deterministic. Vectorised over paths.
- `INPUTS = ('close', 'rf')` or `('close', 'rf', 'y10')`.
- `PARAMS = {...}` as a frozen literal.
- `def target_levels(close, rf, y10=None, params=PARAMS)`: inputs float64 arrays of shape (P, T); returns float64 (P, T)
  of target levels in [0, 3] (NaN = cash). Column t may use only columns <= t. Must cope with early columns (the first 300
  columns are warm-up history and are not traded) and with NaN; must be scale-invariant in `close`.
- Speed: P = 500, T = 10000 in under 60 s.
- Docstring: 3-6 plain lines on what the rule does and how it follows from the theory.

## 5. Deliverables in your folder
THEORY.md, sim.py, rule.py, design_log.md (all variants with N, selection procedure, final fresh-seed table vs holds and
constant levels, robustness, mechanism-off), synth_results.json, READ_LOG.md.

## 6. Engine
```
import sys; sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
res = ee.run(r, rf, B)          # B = target levels (P, T); res['cagr'] etc.
ee.summary(res)['cagr_med']     # the headline objective (median after-tax 30y CAGR)
ee.summary(ee.hold(r, rf, 1))   # same-basis 1x hold (2, 3 likewise)
```
Use T = 300 + 30*252 = 7860 for the standard 30-year horizon.

## 7. Synthetic tournament (run later by a separate blind agent; fixed now)
Every lane rule is run on every lane simulator, mechanism ON and OFF, on fresh seeds 20000-20999 (P = 1000 per cell).
Score = 0.5 x mean over simulators of the median after-tax CAGR with mechanism ON + 0.5 x the same with mechanism OFF.
Ties within 0.3 percentage points: the higher worst cell wins. The winner is the PRIMARY rule for the single real test.
