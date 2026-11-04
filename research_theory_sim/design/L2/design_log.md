# design_log — lane TS1, blind designer L2 ("Dealer Ledger")

All numbers are from my own simulator (sim.py) and the given engine (common/exec_engine.py). No real data were used.
Objective used for selection: J = 0.5 x median after-tax 30y CAGR (mechanism ON) + 0.5 x the same (mechanism OFF), on
seeds 1-999 only, P = 1000 paths per seed, T = 7860. Final numbers: fresh seeds 10000-10003, never used before.
Every evaluation is one line in `variants_log.jsonl` (273 lines).

## Timeline (UTC, from `date -u`)
- 07:17 read DESIGN_BRIEF.md and exec_engine.py.
- 07:24 THEORY.md written, `PRIORS_FROZEN 2026-11-04T07:24Z` (before any simulation).
- 07:26 sim.py written and run (descriptive statistics below). Priors were not changed afterwards. Two later edits to
  sim.py added outputs/options only and reproduce the frozen draws exactly (checked: hold-1x median on seeds 1-2
  0.0500762 before and after): (a) diagnostic state outputs (`return_state`), (b) a `width` option for the
  narrowed/widened robustness priors (width = 1.0 is the frozen prior).
- 07:28-07:44 rule design on seeds 1, 2, 3 (selection only).
- 07:45 rule.py frozen. sha256 `498c11804256c26cc9e85d76eb1b068b940369781da0f62671afcd4c39d8975d`.
- 07:46-07:49 final_eval.py on fresh seeds 10000-10003 -> synth_results.json. No change after this.

## 1. What the synthetic worlds look like (seed 1, 2000 paths; descriptions, not targets)
- Annual vol p10/med/p90 0.143/0.206/0.307 (ON); 0.143/0.207/0.308 (OFF, matched by construction).
- Mean simple excess return of the price index p10/med/p90 -0.013/0.039/0.101 (ON); -0.031/0.030/0.102 (OFF).
- rf path means 0.010/0.042/0.075; y10 means 1.8/5.2/8.3 %; spread means -0.56/0.86/2.29 %.
- 1-year -> next-year excess-return autocorrelation: -0.156 (ON) vs -0.030 (OFF): the ledger's long-horizon reversal.
- Ledger x sd per path 0.33/0.52/0.83; amplification A path means 1.11/1.54/3.94. The A cap of 4 binds on 19% of days
  (in worlds where L0*k >= 0.75 already in the normal state) — a property of the frozen prior, kept.
- Tails: 1% of paths contain a day with an index move below -33% (the engine's 3x product then goes negative and some
  path values become NaN). Convention in all my evaluations: a NaN CAGR is counted as -100% (ruin). It moves medians
  only through those ~1% of paths.
- Same-basis holds (seeds 1-2): ON 1x 0.0501 / 2x -0.0023 / 3x -0.0732; OFF 1x 0.0412 / 2x -0.0127 / 3x -0.0871.
  Constant levels (never rebalanced, 3x product + cash): ON 0.5: 0.0172, 1.0: 0.0127, 1.5: 0.0052, 2.0: -0.0054,
  2.5: -0.0218, 3.0: -0.0732. My worlds are hostile to leverage: the median world has an excess price drift of ~3%/yr
  against ~20% vol, so full Kelly is below 1x; the cash leg pays rf - 2% taxed, so a 3x-product+cash position at
  exposure 1 costs ~2.5%/yr more than the 1x fund used for "hold 1x".

## 2. Headroom diagnostic (not a candidate rule; uses the TRUE hidden state) — 10 evaluations
Kelly with the true drift mu(x, s, rf) and true variance (A*s_f)^2, fraction c:
seed 1: c=0.5 0.0601, c=0.75 0.0613, c=1.0 0.0597; seed 2: 0.0541 / 0.0560 / 0.0542.
Volatility-only oracle (true variance, constant drift m_p): seed 1 c=0.5 0.0197; seed 2 c=0.5 0.0200, c=1.0 0.0146
(seed 1 c=1.0 gave NaN from the engine before I adopted the ruin convention).
Reading: even perfect knowledge of the ledger beats hold 1x only by about 1 pp in my world; most of that comes from the
ledger (drift) information, not from volatility timing.

## 3. Rule family (derived from THEORY.md section 9)
`L_t = clip( (a0 - a1*ledger_t + a2*(s_t - s_bar_t) + a3*(rf_t - rf_norm_t)) / var_t , 0, 3)`
- `ledger_t` = decayed sum (half-life H years) of daily excess log returns `ln(close_t/close_{t-1}) - rf_t`
  (optionally plus `lw_c*(s - s_bar)/252 - lw_d*dy10`, the carry and duration flows of the theory; optional demeaning
  by the expanding mean);
- `var_t` = bias-corrected EWMA of squared daily log returns (half-life hv days) x 252, floored at 0.0004;
- `s` = y10/100 - 252*rf, `s_bar` = its 5-year EWMA (theory's payout norm); `rf_norm` = EWMA of 252*rf, half-life Hr.
Theory-implied magnitudes (from the prior medians): a1 ~ (A-1)*kappa ~ 0.15-0.2, H ~ HLk ~ 1.5-3 y, a0 ~ m_p ~ 0.03,
a2 ~ k*A*c_ts ~ 1, a3 ~ A*b_r*a_r ~ 0.5.

## 4. Variants evaluated (N) and selection
| stage | seeds | definition | N | best (J / ON / OFF) |
|---|---|---|---|---|
| smoke | 1 | hv40 H1 a0 .03 a1 .15 | 1 | 0.0333 / 0.0388 / 0.0278 |
| constant levels | 1,2 | L in {0.5..3} | 6 | best 0.5: ON 0.0172, OFF 0.0187 |
| oracle diagnostics | 1 or 2 | section 2 | 10 | — |
| grid1 price ledger | 1 | hv {20,40,80} x H {0.5,1,2} x a0 {0,.02,.04} x a1 {0,.1,.2,.4} | 108 | hv80 H2 a0 .04 a1 .2: 0.0342 / 0.0444 / 0.0240 |
| grid2 + spread, rf gap | 1 | 3 grid1 bases x a2 {0,1,2,4} x a3 {0,.5,1} (minus 0,0) | 33 | +a2 1 a3 1: 0.0365 / 0.0490 / 0.0240 |
| grid3 refine | 1 | hv {60,100,140} x H {1.5,2,3} x a0 {.03,.04,.05} x a1 {.15,.2,.25}, a2=a3=1 | 81 | hv140 H1.5 a0 .03 a1 .25: 0.0372 / 0.0498 / 0.0246 |
| grid4 misc | 1 | ledger carry/duration weights (8), hv 200/300, demean (2), Hr 1.5/6, a3 2, vfloor (2) | 17 | lw_d 2: 0.0377 (+0.0005, noise level); demeaning hurts (0.030) |
| validate | 2,3 | 12 shortlisted variants | 12 | all within 0.0326-0.0345 |
| select | 1,2,3 | a1 {.2,.25} x with/without y10 spread term, hv140 H1.5 a0 .03 a3 1 Hr 5 | 4 | with y10, a1 .2: 0.0355; without y10, a1 .2: 0.0346 |
| a3 check | 1,2,3 | same without a3 | 1 | 0.0338 |
| **total** | | | **273** | |

Selection decisions (each rule stated before running the stage that applied it):
1. Grids 1-3 on seed 1 picked the plateau hv ~100-140 d, H ~1.5-2 y, a0 0.03-0.04, a1 0.2-0.25, a2 ~1, a3 ~1. These sit
   where the theory says they should (section 3).
2. Extra ledger flows (lw_c, lw_d) gained <= 0.05 pp: dropped (not worth parameters). Demeaning hurt: dropped.
   Hr (rf norm) 1.5/3/6 made no difference: fixed at the theory's 5-year norm (same constant as s_bar), not tuned.
3. Seeds 2-3 validation: a1 = 0.2 more robust OFF than 0.25.
4. Pre-stated tie-break (before step 8): if the y10 version is within 0.1 pp of the version without y10 on seeds 1-3,
   take the one with fewer inputs. Result 0.0355 vs 0.0346 (0.09 pp): y10 dropped. INPUTS = ('close', 'rf').
5. Pre-stated (before step 9): drop a3 if it adds < 0.05 pp. It added 0.08 pp (ON +0.33 pp, OFF -0.18 pp): kept.

Final rule (rule.py): hv_days = 140, ledger_hl_years = 1.5, a0 = 0.03, a1 = 0.2, a3 = 1.0 -> 5 tunable parameters.
Fixed constants: rf norm half-life 5 y (theory), variance floor 0.0004 (numerical), NaN for the first 20 columns.
Checks (check_rule.py): identical to the harness family (max diff 1.8e-15); scale-invariant (close x 1234.5: diff
3.7e-13); causal (perturbing columns > t leaves columns <= t unchanged: diff 0.0); copes with NaN close/rf; P=500 x
T=10000 in 1.0 s.

## 5. Final fresh-seed results (seeds 10000-10001, 2000 paths, T = 7860, delay 2, cost 0.3%)
Median after-tax 30y CAGR (p10 / p90 / median MDD / P(MDD <= -80%)):

| | mechanism ON | mechanism OFF |
|---|---|---|
| **rule** | **0.0444** (-0.0369 / 0.1022 / -0.602 / 0.247) | **0.0206** (-0.0641 / 0.0709 / -0.708 / 0.377) |
| hold 1x | 0.0498 (0.0005 / 0.1100 / -0.553 / 0.051) | 0.0404 (-0.0217 / 0.1134 / -0.606 / 0.193) |
| hold 2x | -0.0029 | -0.0133 |
| hold 3x | -0.0770 | -0.0893 |
| const 0.5 | 0.0162 (best constant) | 0.0169 (best constant) |
| const 1.0 | 0.0106 | 0.0115 |
| const 1.5 | 0.0034 | 0.0044 |
| const 2.0 | -0.0066 | -0.0060 |
| const 2.5 | -0.0229 | -0.0236 |
| const 3.0 | -0.0770 | -0.0893 |
| rule trades/yr, avg level | 3.3, 0.67 | 2.7, 0.80 |

Robustness (same fresh paths):
| row | ON | OFF |
|---|---|---|
| delay 3 | 0.0445 | 0.0209 |
| delay 5 | 0.0455 | 0.0204 |
| cost 0.6% | 0.0425 | 0.0190 |

Prior narrowed (width 0.5) / widened (width 1.5), fresh seeds 10002-10003:
| | rule | hold 1x | hold 2x | hold 3x | best const |
|---|---|---|---|---|---|
| narrowed ON | 0.0548 | 0.0557 | 0.0093 | -0.0649 | 0.0163 (0.5) |
| narrowed OFF | 0.0270 | 0.0464 | -0.0064 | -0.0825 | 0.0176 (0.5) |
| widened ON | 0.0399 | 0.0511 | -0.0223 | -0.1038 | 0.0211 (0.5) |
| widened OFF | 0.0178 | 0.0324 | -0.0351 | -0.1200 | 0.0224 (0.5) |

Mechanism-off loss against the best constant-level rule: rule 0.0206 vs const 0.5 at 0.0169 -> **no loss (+0.37 pp)**
(the variance scaling still helps against the exogenous stochastic volatility). In the widened-prior OFF world the
rule falls 0.46 pp BELOW the best constant (0.0178 vs 0.0224).

## 6. Honest assessment
- In my own world the rule does NOT beat same-basis hold 1x: -0.54 pp with the mechanism ON, -1.98 pp OFF, and it
  carries much more deep-drawdown risk (P(MDD <= -80%) 0.25 vs 0.05 ON). It never comes near 2x or 3x hold, which
  are poor in these worlds anyway.
- It clearly beats every constant level of the 3x-product+cash instrument (+2.8 pp ON, +0.4 pp OFF), and is
  insensitive to delay 3/5 (slow signal) and loses ~0.2 pp at doubled cost.
- Selection optimism: the same rule scored 0.0471 ON on selection seeds 1-3 vs 0.0444 on fresh seeds (about -0.3 pp).
- Why hold 1x is so hard here: the rule can only hold the 3x product plus cash paying rf - 2% after tax, so any exposure
  near 1 costs ~2.5%/yr more than the 1x fund; even the true-state oracle only beat hold 1x by ~1 pp.
- What the real test could show: the rule is a long-horizon contrarian (adds exposure after cumulative losses once
  realised variance allows, goes to cash after strong run-ups) with a funding-cost tilt (more exposure when the short
  rate is above its 5-year norm). If real long-horizon returns trend instead of revert, or if block resampling at 250
  days breaks the 1.5-year ledger, the rule behaves like its mechanism-off result: about vol-scaled cash-heavy exposure.
- Nothing here was tuned toward the user's 30%/yr hope; in my worlds no rule I found gets close to that.
