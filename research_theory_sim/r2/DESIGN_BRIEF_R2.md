# TS2 design brief (round 2): a new market theory -> a synthetic market -> a trading rule designed ONLY on synthetic data

You are a BLIND designer. You invent a new theory of how an equity index price is formed, build a simulator of that
theory, and design a trading rule using only data your own simulator generates. You never look at any real market data or
any earlier research result. Your rule will be frozen (hash-committed) and then tested once, by someone else, on several
decades of real history in more than one market. An honest failure is an acceptable outcome. Contamination is not.

This is round 2 of the lane. Sections marked (R2) are new. You do not see round 1 and must not look for it.

## 1. Blindness rules (hard)
- You may READ only: this file; `/mnt/project-files/research/theory_sim/common/exec_engine.py`; files you create in your
  own folder `/mnt/project-files/research/theory_sim/r2/design/<LANE>/` (the tournament agent: all `r2/design/*` folders).
- You may WRITE only inside your own folder.
- FORBIDDEN (do not open, list, grep or import):
  - every other path under /mnt/project-files. This includes everything else under research/theory_sim/ (the round 1
    folders design/, test/, verify/, holdout/, any RESULT or FREEZE file, any archive, r2/test/, r2/verify/,
    r2/TEST_PROTOCOL_R2.md), all other research/*, reports/*, tools/*, handoff/*, uploads/*, other lanes' folders, any
    MEMORY.md, /tmp/claude/memory, and the git checkout /home/user/-;
  - the project's named forbidden list: reports/best_results_summary_*, research/deep/, research/audit/, any diag/,
    research/mass_scan/, research/us_mix_sb_oos/, research/user_port/, research/c3_relax/RESULT_RELAX_KO.md and
    results/holdout_once.csv, research/user_v104/RESULT_V104_KO.md and results/, research/user_v107/ (RESULT_V107_KO.md,
    results/, unseen/, final/, SHARE_V107_vs_s085_KO.md), research/user_port4/ (RESULT_KO.md, results/),
    research/c3_stock_combo/, research/c3_create/fwd/, research/s085_contra/holdout/, research/theory_sim/holdout/,
    tools/s085_now/out/, tools/s085_now/cache/;
  - the lab runner (research/lab): it reads real prices;
  - any network use: no WebSearch / WebFetch, no MCP data tools (Twelve Data, Alpha Vantage, FMP, Bigdata, Gemini,
    Financial Datasets, Exa, ...), no pip/conda download of data packages (yfinance, pandas-datareader, ...).
    No price, rate, index or macro data of any real asset or period.
- Remembered history: specific crashes, years, decades, named indices and their statistics stay FORBIDDEN as inputs to the
  mechanism (the timing structure of your theory). The only remembered numbers you may use are the published long-run
  averages of section 2b, and only for the unconditional level of the premium, volatility and drawdown frequency.
- If your context already contains project memory, research results or market numbers (strategy names with returns,
  index statistics, results of earlier rounds), ignore them, do not use them, and record in READ_LOG.md that such context
  was present.
- Write READ_LOG.md: every file you opened (path and why). An auditor checks it, greps your code for file reads and
  reads your session record.
- Keep disk use small: caches in your folder under 200 MB at any time, and delete caches before you finish.

## 2. What the real test will look like (structural facts only, no data)
- Underlying: the headline market is a broad, liquid equity PRICE index (no dividends), daily closes. The same frozen
  rule is also run, separately, on other equity markets (price indices of other eras, and country equity funds whose
  adjusted prices include reinvested distributions). None is named on purpose. The rule never sees two markets at once.
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
  the same engine. The headline paths are built by resampling the real daily history of one index in blocks of 250 trading
  days into 30-year paths, so predictive structure longer than about one year is partly broken at block joins. Single
  real-history paths of several markets are reported too, each with same-basis buy-and-hold of 1x, 2x and 3x.
- Robustness rows that will be reported: delay 3 and delay 5 days; cost 0.6% per trade.
- The user's goal is the highest possible long-run after-tax growth (they hope for 30%/yr or more). Do not bend the priors
  toward that number: a rule that only works in a world tuned to make it work will fail the real test.

## 2b. Published anchors for the unconditional level (R2)
- Centre each simulator's long-run equity premium over cash, long-run volatility and the frequency and depth of large
  drawdowns on CENTRAL published long-run estimates for broad equity markets that you know from the finance literature
  (for example multi-decade, multi-country studies of equity returns over bills, or long-run national return series).
- The headline underlying is a price index. If your remembered number is a total return, convert it to a price-index
  premium and say how (the other markets may include distributions; your wide prior should cover both).
- In THEORY.md, section "Published anchors": name each source, the number you remember, the conversion you apply, and how
  sure you are. Use the central value, not a conservative haircut. Express uncertainty with a WIDE prior around the
  centre, not by moving the centre.

## 2c. Unknown market (R2)
- The premium and volatility of the market the rule will trade can differ from the broad-market centre in either
  direction, and the rule is run on several different markets.
- Draw the true premium and volatility PER PATH from a wide prior around the anchors (each path is a different market).
- A rule may estimate the premium, the volatility and the state of your mechanism online from the path it trades (data
  <= t only), starting from your prior (shrinkage, filtering). Whether it should is your design decision; test it.

## 2d. Rates (R2)
- Your rf paths (and y10 if you use it) must include long regimes, up to a decade or more, in which short rates trend
  steadily up or steadily down, as well as stable periods, in addition to whatever your theory adds.

## 3. Process (in this order; take every timestamp from `date -u +%Y-%m-%dT%H:%MZ`)
1. THEORY.md, written BEFORE any simulation: name; the mechanism (who trades, under which constraints, why prices move the
   way they do); why it should exist in real markets (economic argument); what it predicts that a random walk does not;
   how it could be false. It must be NEW: you may use known ingredients, but the mechanism / combination is your own, not a
   restatement of a textbook model. Section "Published anchors" (2b). Section "Priors": every simulator parameter with a
   range and the reason. Define a "mechanism-off" world (same unconditional premium and volatility, mechanism disabled).
   Then write a line `PRIORS_FROZEN <timestamp>` and do not change the priors after you start designing the rule.
2. sim.py: `simulate(P, T, seed, mechanism=True) -> dict(r=(P,T), rf=(P,T), y10=(P,T) or None, params=...)`, parameters
   drawn PER PATH from the prior. `r[:, 0] = 0`. Vectorised numpy; 2000 paths x 7860 days should run in a few minutes at
   most. Print descriptive statistics of your synthetic worlds (median and spread of the per-path premium, volatility,
   worst drawdown, same-basis 1x hold CAGR); they describe the theory, they are not targets.
3. Rule design on synthetic data only:
   - Derive the rule from the theory: what would an informed trader do if the theory were true, not knowing the exact
     premium and volatility of the market in front of them? Online estimation inside the rule is allowed (filters,
     rolling or expanding estimates), using data <= t only.
   - Selection on seeds 1-999 only; final numbers on fresh seeds >= 10000 that were never used for selection. Count every
     variant you evaluate (N, including grid points). At most 6 tunable parameters in the final rule.
   - Always compare with same-basis hold 1x / 2x / 3x on the same paths and with constant-level rules (levels 0.5, 1,
     ..., 3; the best constant level = the single level, the same for all paths, with the highest median CAGR).
   - Design gates (R2), on fresh seeds, P >= 1000:
     - G-ON: with the mechanism ON, the rule's median after-tax CAGR beats both the same-basis 1x hold and the best
       constant level.
     - G-OFF: with the mechanism OFF, the rule loses at most 1.0 percentage point of median CAGR against the best
       constant level of that world.
     - If no variant passes both gates, ship the simplest rule your theory implies that loses least against the best
       constant level in both worlds (it may be close to a constant exposure with online premium / volatility
       estimation), and say plainly that the mechanism added no tradeable edge after costs. That is an honest result.
   - Robustness: delay 3 and 5, cost 0.006, prior narrowed / widened, and the mechanism-off world.
4. Freeze: rule.py (interface below), synth_results.json, design_log.md.

## 4. rule.py interface (strict)
- Pure numpy: imports `numpy` and `math` only. No file or network I/O. Deterministic. Vectorised over paths. Must not
  modify its input arrays.
- `INPUTS = ('close', 'rf')` or `('close', 'rf', 'y10')`.
- `PARAMS = {...}` as a frozen literal.
- `def target_levels(close, rf, y10=None, params=PARAMS)`: inputs float64 arrays of shape (P, T); returns float64 (P, T)
  of target levels in [0, 3] (NaN = cash). Column t may use only columns <= t. Must cope with early columns (the first 300
  columns are warm-up history and are not traded), with NaN, zero or flat stretches in `close` (for example a market that
  had not opened yet), and must be scale-invariant in `close`.
- Speed: P = 500, T = 10000 in under 60 s.
- Docstring: 3-6 plain lines on what the rule does and how it follows from the theory.

## 5. Deliverables in your folder
THEORY.md, sim.py, rule.py, design_log.md (all variants with N, selection procedure, the design gates G-ON / G-OFF with
numbers, final fresh-seed table vs holds and constant levels, robustness, mechanism-off), synth_results.json, READ_LOG.md.

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
The judge also reports, per cell, the same-basis 1x hold and the best constant level, and the score of the best single
constant level (as a reference row, not a candidate).
