# TS1 synthetic tournament: result

Blind tournament judge, run 2026-11-04T08:36Z to 08:41Z (times from `date -u`). Scoring follows DESIGN_BRIEF.md
section 7 exactly. Every number below is in `tournament.json`, and `python -B tournament.py` reproduces it
(deterministic, about 3 minutes on 3 processes).

**PRIMARY rule for the single real test: L1, "Margin-Ratchet Leverage Cycle" (MRLC) rule**
(`design/L1/rule.py`, sha256 `acc4cf0c...e937fb`). It scores 3.06%, against 2.28% for L2 and 1.45% for L3. That is a
lead of 0.78 pp, well outside the 0.3 pp tie band. It is still **below plain same-basis hold 1x (3.81%)**; see the caveats.

## What I read and did (blindness)
- Read: DESIGN_BRIEF.md; common/exec_engine.py; in design/L1, L2 and L3, the files THEORY.md, sim.py, rule.py,
  design_log.md and AUDIT.md, plus the key list of each synth_results.json. I did not open TEST_PROTOCOL.md, test/,
  holdout/, any other folder, any memory file or the git checkout. I used no network and no data tool.
- No real market data of any kind was used. All paths come from the three lane simulators.
- No lane file was changed. The sha256 of all six lane sim.py and rule.py files and of exec_engine.py is the same
  before and after the run (recorded in tournament.json). Modules were loaded with bytecode writing switched off.
- My context held the designer and audit summaries from the workflow. I used them only to find the files. The scores
  below come from my own runs.

## Step 1: exclusions
None. All three audits (design/L*/AUDIT.md) give the verdict **PASS** on blindness, interface, causality and reproduction.

## Setup
- P = 1000 paths per cell, T = 7860 (300 warm-up days plus 30 years), engine defaults (delay 2, cost 0.003).
- Seeds: simulator L1 uses 20000, L2 uses 20001 and L3 uses 20002. **ON and OFF of one simulator use the same seed**,
  because each lane defines its OFF world as the same seed and parameter draw with the mechanism disabled. In each cell
  all three rules and all reference rows run on the same paths.
- Rule input: `close = 100 * cumprod(1 + r)` and `rf` from the simulator. All three rules read only (close, rf).
- NaN rule: an engine CAGR that comes out NaN counts as -100% and its MDD as -100%. This happens when the 3x product
  goes negative on a day the index falls more than 1/3. The rule applies to every row. In practice **no row had a NaN
  path**, so it changed nothing.
- Reference rows (not candidates): same-basis hold 1x, 2x and 3x, and constant levels 1, 2 and 3. I added constant
  levels 0 (cash) and 0.5 as extra references, because 0.5 was the best constant in all three lanes' own worlds.

## Scores (step 3)
Score = 0.5 x the mean over the 3 simulators of the median after-tax CAGR (ON) + 0.5 x the same (OFF).

| rule | ON mean | OFF mean | **Score** | worst cell | score without own simulator (diagnostic) |
|---|---|---|---|---|---|
| **L1 MRLC** | 4.43% | 1.69% | **3.06%** | 0.17% (sim L3 OFF) | 1.38% |
| L2 Dealer Ledger | 3.22% | 1.34% | 2.28% | -0.22% (sim L3 ON) | 1.69% |
| L3 SGNC-K | 1.20% | 1.70% | 1.45% | -0.07% (sim L1 ON) | 1.36% |
| *ref: hold 1x* | 3.94% | 3.68% | *3.81%* | 3.00% | |
| *ref: const 0.5* | 1.63% | 1.69% | *1.66%* | 1.11% | |
| *ref: const 0 (cash)* | 1.62% | 1.62% | *1.62%* | 1.29% | |
| *ref: const 1* | 1.19% | 1.21% | *1.20%* | 0.49% | |
| *ref: hold 2x* | -0.53% | -1.30% | *-0.92%* | -2.76% | |
| *ref: const 2* | -0.44% | -0.49% | *-0.46%* | -1.40% | |
| *ref: hold 3x = const 3* | -6.50% | -8.05% | *-7.28%* | -11.11% | |

How stable the choice is (reported only; neither check took part in the choice):
- Paired path bootstrap, 2000 resamples, with paths resampled inside each cell. The 90% interval of L1's score is
  2.93% to 3.22%. L1 minus L2 is +0.63 to +0.95 pp. **L1 won 100% of resamples.**
- Second set of fresh seeds (20010, 20011, 20012): L1 3.17%, L2 2.21%, L3 1.53%, hold 1x 3.87%. Same order, same winner.

## Cross-matrix (step 2): median after-tax 30-year CAGR
| row | sim L1 ON (seed 20000) | sim L1 OFF (seed 20000) | sim L2 ON (seed 20001) | sim L2 OFF (seed 20001) | sim L3 ON (seed 20002) | sim L3 OFF (seed 20002) |
|---|---|---|---|---|---|---|
| **rule L1 (MRLC)** | **10.51%** | 2.31% | 2.31% | 2.58% | 0.46% | 0.17% |
| **rule L2 (Dealer Ledger)** | 5.31% | 0.55% | **4.57%** | 2.35% | -0.22% | 1.11% |
| **rule L3 (SGNC-K)** | -0.07% | 1.92% | 1.54% | 2.05% | **2.14%** | 1.13% |
| hold 1x | 3.76% | 3.85% | 5.01% | 4.20% | 3.04% | 3.00% |
| hold 2x | 0.24% | 0.50% | -0.30% | -1.64% | -1.53% | -2.76% |
| hold 3x | -3.98% | -3.63% | -8.00% | -9.40% | -7.52% | -11.11% |
| const 1 | 1.57% | 1.75% | 1.22% | 1.40% | 0.77% | 0.49% |
| const 2 | 0.18% | 0.40% | -0.47% | -0.45% | -1.01% | -1.40% |
| const 3 | -3.98% | -3.63% | -8.00% | -9.40% | -7.52% | -11.11% |
| const 0 (cash, extra) | 1.70% | 1.70% | 1.88% | 1.88% | 1.29% | 1.29% |
| const 0.5 (extra) | 1.96% | 2.11% | 1.68% | 1.85% | 1.24% | 1.11% |

Bold diagonal = a rule in its own designer's world. These cells agree with the designers' fresh-seed numbers to within
about 0.3 pp (designers: L1 10.32 / 2.47, L2 4.44 / 2.06, L3 2.26 / 1.32, ON / OFF).

### p10 of CAGR
| row | L1 ON | L1 OFF | L2 ON | L2 OFF | L3 ON | L3 OFF |
|---|---|---|---|---|---|---|
| rule L1 | 2.27% | -3.88% | -4.23% | -3.70% | -6.00% | -5.71% |
| rule L2 | -4.15% | -10.78% | -3.49% | -6.33% | -11.58% | -7.74% |
| rule L3 | -5.12% | -0.44% | -0.82% | -0.42% | -0.29% | -0.79% |
| hold 1x | -0.23% | -1.15% | 0.01% | -2.62% | -2.82% | -2.97% |
| hold 2x | -8.13% | -10.14% | -9.99% | -15.31% | -13.88% | -15.23% |
| hold 3x | -16.30% | -19.30% | -24.09% | -32.29% | -26.08% | -32.50% |
| const 1 | -0.67% | -0.65% | -1.04% | -1.05% | -1.15% | -1.22% |
| const 2 | -2.59% | -2.65% | -3.21% | -3.22% | -3.29% | -3.41% |
| const 3 | -16.30% | -19.30% | -24.09% | -32.29% | -26.08% | -32.50% |

### P(max drawdown <= -80%)
| row | L1 ON | L1 OFF | L2 ON | L2 OFF | L3 ON | L3 OFF |
|---|---|---|---|---|---|---|
| rule L1 | 3.0% | 18.1% | 14.5% | 16.1% | 28.8% | 26.1% |
| rule L2 | 39.7% | 51.2% | 22.3% | 36.2% | 50.0% | 38.3% |
| rule L3 | 15.8% | 0.0% | 0.0% | 0.0% | 0.0% | 0.2% |
| hold 1x | 1.4% | 4.4% | 5.4% | 20.1% | 15.7% | 15.7% |
| hold 2x | 61.9% | 59.2% | 77.4% | 81.9% | 76.5% | 77.7% |
| hold 3x | 91.5% | 87.1% | 98.2% | 97.0% | 93.5% | 95.6% |
| const 1 | 7.7% | 9.2% | 9.8% | 19.9% | 13.2% | 11.0% |
| const 2 | 34.8% | 28.9% | 38.5% | 45.5% | 39.2% | 36.3% |
| const 3 | 91.5% | 87.1% | 98.2% | 97.0% | 93.5% | 95.6% |

### Behaviour: average level / trades per year / share of paths beating hold 1x
| rule | L1 ON | L1 OFF | L2 ON | L2 OFF | L3 ON | L3 OFF |
|---|---|---|---|---|---|---|
| L1 | 0.83 / 13.7 / 80% | 0.77 / 11.8 / 16% | 0.46 / 7.4 / 10% | 0.46 / 6.7 / 21% | 0.70 / 8.6 / 17% | 0.60 / 7.3 / 14% |
| L2 | 1.32 / 6.0 / 56% | 1.32 / 4.1 / 7% | 0.64 / 3.2 / 36% | 0.78 / 2.7 / 22% | 1.05 / 3.0 / 9% | 0.83 / 2.3 / 17% |
| L3 | 0.34 / 3.4 / 12% | 0.29 / 2.1 / 26% | 0.18 / 1.3 / 14% | 0.16 / 1.0 / 30% | 0.21 / 1.3 / 40% | 0.15 / 1.0 / 30% |

## Step 4: robustness of the primary (L1 rule, same paths as the main cells)
| L1 row | L1 ON | L1 OFF | L2 ON | L2 OFF | L3 ON | L3 OFF | ON mean | OFF mean | score | worst |
|---|---|---|---|---|---|---|---|---|---|---|
| base (delay 2, cost 0.3%) | 10.51% | 2.31% | 2.31% | 2.58% | 0.46% | 0.17% | 4.43% | 1.69% | 3.06% | 0.17% |
| delay 3 | 10.07% | 2.34% | 2.26% | 2.62% | 0.65% | 0.17% | 4.32% | 1.71% | 3.02% | 0.17% |
| delay 5 | 9.04% | 2.31% | 2.32% | 2.53% | 0.81% | 0.35% | 4.06% | 1.73% | 2.89% | 0.35% |
| cost 0.6% | 9.88% | 1.65% | 1.88% | 2.21% | -0.09% | -0.28% | 3.89% | 1.19% | 2.54% | -0.28% |

P(MDD <= -80%) at cost 0.6%: 3.9 / 20.9 / 15.5 / 17.4 / 31.6 / 28.7%. Delays 3 and 5 move it by less than 2 pp.

## Choice
PRIMARY = **L1 (MRLC)**. It has the highest score by 0.78 pp, so the tie rule does not come into play. It also has the
highest worst cell of the three (0.17%, against -0.22% and -0.07%), so it would have won a tie too.

## Caveats (plain words)
1. **No lane rule beats simply holding the index at 1x.** Hold 1x scores 3.81%, against 3.06% for the winner. L1 beats
   hold 1x in only one of six cells, its own world with the mechanism on. On the other five cells it trails hold 1x
   by 1.5 to 2.8 pp. The primary is the best of three candidates, not a proven improvement on buy-and-hold.
2. **The win comes from home advantage.** About four-fifths of L1's ON mean comes from its own simulator (10.5% there,
   2.3% and 0.5% in the other two worlds). With each rule's own simulator left out, L2 would rank first (1.69%), with
   L1 (1.38%) and L3 (1.36%) behind. This diagnostic is not part of the fixed score. It says that on the worlds
   designed by the other two lanes, none of the rules has a clear edge.
3. **If its mechanism is false, L1 is no better than a constant level.** Its OFF mean of 1.69% equals constant 0.5
   (1.69%) and is barely above cash (1.62%). Hold 1x makes 3.68% there.
4. **The left tail is heavy.** Outside its home ON cell, L1's p10 CAGR is -3.7% to -6.0%. Its chance of an 80% or
   deeper drawdown is 14% to 29%, against 1% to 20% for hold 1x and 0% to 0.2% for L3 (outside L3's L1-ON cell).
5. **On the narrative-contagion world (sim L3), L1 earns less than cash** in both ON (0.46%) and OFF (0.17%), against
   1.29% for cash.
6. **Costs matter more than delay.** Doubling the cost to 0.6% takes 0.52 pp off the score and turns the worst cell
   negative. That is because L1 trades 7 to 14 times a year. Delays of 3 or 5 days cost at most 0.17 pp.
7. **The worlds are not alike.** The three OFF worlds are built differently: L1 uses i.i.d. Student-t returns; L2
   keeps stochastic volatility and fat tails; L3 turns story switches into one-day jumps. The score mixes all three.
   A synthetic tournament only ranks the rules against one another on invented worlds. It says nothing direct about
   real history.
8. **The user's 30%-a-year hope is not in sight.** The best cell of any rule is 10.5%, and that is the L1 rule in the
   world its own designer built. Constant leverage of 2x or 3x loses money in almost every synthetic world here
   (hold 3x scores -7.3%).
9. **Note on the hold 1x reference.** Hold 1x is a 1x fund costing 0.2% a year, which the rule's own instruments
   (3x product plus cash) cannot replicate. Constant level 1 trails it by 2.1 to 3.8 pp, depending on the cell. The real
   test reports the same reference.

## Files
- `tournament.py`: reproduces everything. Phases: cells, then score, then the primary's robustness row, then the
  bootstrap and the second-seed replicate.
- `tournament.json`: all numbers, the seeds of every cell, a world summary per cell, the sha256 values before and after.
- `work/cell_{main,rep}_<sim>_<on|off>.json` and `work/cagr_*.npz`: per-cell results and per-path CAGRs (used by the bootstrap).
