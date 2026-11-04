# RESULT_TOURNAMENT - lane TS2, round 2: blind synthetic tournament

Judge run 2026-11-04T12:11Z to 2026-11-04T12:22Z (timestamps from `date -u`). Final computation 12:18Z-12:20Z.
Scoring as fixed in `r2/DESIGN_BRIEF_R2.md` section 7. All numbers are synthetic; none comes from market data.

## Verdict

**PRIMARY = rule D** (lane D, "Funding-Carry Capital Ledger", a tracked constant index exposure of 1.25).

- Score 4.35 %/yr. The runner-up is rule C at 3.75 %/yr, so D leads by 0.60 pp. That is twice the 0.3 pp tie window,
  and the tie-break was not needed (the tie set held D alone).
- D also has the highest worst cell, 3.60 % (A_OFF).
- D wins in 100 % of 2000 paired bootstrap resamples (Table 8).
- D beats the best single constant level (0.5, score 2.99 %/yr) by +1.36 pp.
- D does NOT beat the same-basis 1x hold (score 5.85 %/yr): it is -1.50 pp behind, and it is behind in every one of the
  eight cells.

In plain words: the rule that travels best across the four designers' worlds has no market timing at all. It holds one
fixed exposure and keeps the drifting 3x/cash mix close to that exposure. None of the three timing rules (A, B, C)
carried its edge into the other designers' worlds.

## What was run

- Exclusions (step 1): none. All four lanes have audit verdict PASS (the `Verdict:` line of each AUDIT.md: A, B, C and
  D all PASS), so all four rules and all four simulators are in the matrix.
- Matrix (step 2): 4 rules x 4 simulators x mechanism ON/OFF, which makes 8 cells (simulator x world). Each cell has
  P = 1000 paths and T = 7860 (300 warm-up columns plus 30 traded years), and runs on `common/exec_engine.py` with its
  defaults (delay 2, cost 0.003).
- Seeds: each cell has its own fresh seed, and every rule and reference row in a cell runs on the same paths.

  | cell | A_ON | A_OFF | B_ON | B_OFF | C_ON | C_OFF | D_ON | D_OFF |
  |---|---|---|---|---|---|---|---|---|
  | seed | 20000 | 20001 | 20002 | 20003 | 20004 | 20005 | 20006 | 20007 |

  The call is `simulate(1000, 7860, seed, mechanism=...)` of that lane's sim.py, with all other arguments at their
  defaults (the frozen prior). The stress rows of step 4 reuse the same seeds. A sha256 of r confirmed that they ran on
  the same paths in all 8 cells.
- Inputs to the rules:
  - `close = cumprod(1 + r)` along time, so close[:, 0] = 1 (all four rules are scale-invariant);
  - `rf` = the simulator's daily rate.
  - No rule declares `y10` in INPUTS, so none received it.
  - Each rule got its own copies of the inputs, and the copies were checked unchanged afterwards.
  - Every output was float64 of shape (P, T), with no value outside [0, 3] and no inf. NaN (cash) appeared only in each
    rule's warm-up: A before its first live day, B for 60 columns, C for 250 columns, D never.
- Reference rows, on the same paths in each cell:
  - same-basis hold 1x and 2x (`ee.hold`);
  - hold 3x, which equals the constant level 3.0: `ee.hold(r, rf, 3)` is exactly `run(r, rf, B = 3)`;
  - the constant levels 0.5, 1, 1.5, 2, 2.5 and 3 through `ee.run`.
- Score (step 3):
  - Score_j = 0.5 x the mean over the 4 simulators of the cell median CAGR with mechanism ON, plus 0.5 x the same with
    mechanism OFF.
  - Tie rule: every candidate within 0.003 of the top score is tied, and the tied candidate with the highest worst cell
    (its lowest of the 8 cell medians) wins.
  - Holds and constant levels get the same score as reference rows; they are not candidates.
  - "Best single constant level" means the one level, the same in all cells, with the highest score.
- Stress (step 4), for the primary only: the same 8 cells at delay 3, delay 5 and cost 0.006. The constant levels were
  re-run at cost 0.006 and at delay 5 as a same-setting reference. They do not depend on the delay, because the engine
  pre-fills its order queue at the end of the warm-up.
- Noise check (not part of the scoring): a paired bootstrap over paths, resampling paths within each cell (2000
  resamples, seed 777). It covers only path sampling noise, not model uncertainty.
- Lane files: the sha256 of every rule.py and sim.py, and of exec_engine.py, is identical before and after the run
  (recorded in tournament.json). Every hash printed in an AUDIT.md matches:
  - A rule `09bcfa96...` and A sim `30957f2d...`;
  - B rule `8051732d...`;
  - D rule `6246c68a...` (C's audit printed no hash).

  No lane file was modified, and no `__pycache__` was written (python -B).

## Tables

### Table 1. Scores (median after-tax 30y CAGR, %/yr)

| row | kind | score | mean ON | mean OFF | worst cell | worst cell is |
|---|---|---|---|---|---|---|
| rule A | candidate | 3.52 | 3.92 | 3.12 | 2.50 | A_OFF |
| rule B | candidate | 3.53 | 3.18 | 3.88 | 0.52 | C_ON |
| rule C | candidate | 3.75 | 4.16 | 3.33 | 2.60 | A_OFF |
| **rule D (PRIMARY)** | candidate | 4.35 | 4.52 | 4.18 | 3.60 | A_OFF |
| hold1 | reference | 5.85 | 5.83 | 5.87 | 5.25 | C_ON |
| hold2 | reference | 2.61 | 2.66 | 2.55 | 1.21 | C_ON |
| hold3 | reference | -1.29 | -1.12 | -1.46 | -3.67 | C_ON |
| const_0.5 | reference | 2.99 | 2.95 | 3.02 | 2.21 | A_OFF |
| const_1.0 | reference | 2.81 | 2.84 | 2.79 | 1.89 | A_OFF |
| const_1.5 | reference | 2.49 | 2.55 | 2.44 | 1.44 | A_OFF |
| const_2.0 | reference | 1.88 | 1.97 | 1.79 | 0.71 | A_OFF |
| const_2.5 | reference | 0.89 | 1.01 | 0.78 | -0.28 | A_OFF |
| const_3.0 | reference | -1.29 | -1.12 | -1.46 | -3.67 | C_ON |
| best constant per cell (hindsight) | reference | 3.03 | 3.03 | 3.02 | 2.21 | A_OFF |

### Table 2. Cross-matrix: median after-tax CAGR (%/yr), rule x simulator world

| row | A_ON (seed 20000) | A_OFF (seed 20001) | B_ON (seed 20002) | B_OFF (seed 20003) | C_ON (seed 20004) | C_OFF (seed 20005) | D_ON (seed 20006) | D_OFF (seed 20007) |
|---|---|---|---|---|---|---|---|---|
| rule A | 5.43 | 2.50 | 3.61 | 3.11 | 2.80 | 2.73 | 3.86 | 4.12 |
| rule B | 4.04 | 3.10 | 3.74 | 4.24 | 0.52 | 3.52 | 4.44 | 4.67 |
| rule C | 3.70 | 2.60 | 3.83 | 3.22 | 5.69 | 3.40 | 3.44 | 4.10 |
| rule D | 4.51 | 3.60 | 4.18 | 4.21 | 3.89 | 3.79 | 5.49 | 5.12 |
| hold 1x | 5.43 | 5.34 | 5.77 | 5.69 | 5.25 | 5.49 | 6.88 | 6.99 |
| hold 2x | 2.02 | 1.96 | 2.34 | 2.59 | 1.21 | 1.88 | 5.08 | 3.76 |
| hold 3x | -2.34 | -1.95 | -2.09 | -1.08 | -3.67 | -3.13 | 3.60 | 0.34 |
| const 0.5 | 2.23 | 2.21 | 3.02 | 3.32 | 2.67 | 2.73 | 3.91 | 3.83 |
| const 1.0 | 1.98 | 1.89 | 2.76 | 3.19 | 2.41 | 2.44 | 4.19 | 3.65 |
| const 1.5 | 1.62 | 1.44 | 2.41 | 2.89 | 1.92 | 2.11 | 4.23 | 3.32 |
| const 2.0 | 0.86 | 0.71 | 1.95 | 2.24 | 1.19 | 1.39 | 3.88 | 2.81 |
| const 2.5 | -0.24 | -0.28 | 0.88 | 1.41 | -0.27 | 0.16 | 3.66 | 1.82 |
| const 3.0 | -2.34 | -1.95 | -2.09 | -1.08 | -3.67 | -3.13 | 3.60 | 0.34 |

Best constant level per cell: A_ON 0.5 (2.23), A_OFF 0.5 (2.21), B_ON 0.5 (3.02), B_OFF 0.5 (3.32), C_ON 0.5 (2.67), C_OFF 0.5 (2.73), D_ON 1.5 (4.23), D_OFF 0.5 (3.83)

### Table 3. p10 of after-tax CAGR (%/yr)

| row | A_ON (seed 20000) | A_OFF (seed 20001) | B_ON (seed 20002) | B_OFF (seed 20003) | C_ON (seed 20004) | C_OFF (seed 20005) | D_ON (seed 20006) | D_OFF (seed 20007) |
|---|---|---|---|---|---|---|---|---|
| rule A | -0.73 | -3.91 | -3.09 | -3.21 | -3.78 | -3.83 | -1.86 | -3.21 |
| rule B | -0.65 | -1.75 | -2.86 | -2.40 | -10.93 | -1.59 | -1.44 | -1.02 |
| rule C | -0.31 | -0.87 | -0.94 | -2.06 | -0.70 | -0.94 | -2.55 | -0.41 |
| rule D | -2.00 | -2.96 | -3.17 | -2.53 | -3.05 | -3.35 | -2.06 | -2.77 |
| hold 1x | 0.16 | 0.02 | -0.40 | -0.13 | -0.79 | -0.40 | 0.70 | 0.16 |
| hold 2x | -8.00 | -8.22 | -8.48 | -8.13 | -10.28 | -9.28 | -8.47 | -8.94 |
| hold 3x | -17.89 | -16.93 | -18.33 | -18.74 | -21.79 | -20.48 | -23.84 | -18.76 |
| const 0.5 | -0.15 | -0.21 | -0.36 | -0.31 | -0.45 | -0.45 | 0.01 | -0.07 |
| const 1.0 | -0.75 | -0.84 | -1.02 | -0.99 | -1.11 | -1.15 | -0.59 | -0.72 |
| const 1.5 | -1.61 | -1.71 | -1.91 | -1.84 | -1.97 | -2.04 | -1.41 | -1.61 |
| const 2.0 | -2.82 | -2.96 | -3.15 | -3.04 | -3.21 | -3.21 | -2.64 | -2.76 |
| const 2.5 | -4.83 | -4.98 | -5.24 | -5.03 | -5.29 | -5.31 | -4.57 | -4.81 |
| const 3.0 | -17.89 | -16.93 | -18.33 | -18.74 | -21.79 | -20.48 | -23.84 | -18.76 |

### Table 4. P(MDD <= -80%) (share of paths)

| row | A_ON (seed 20000) | A_OFF (seed 20001) | B_ON (seed 20002) | B_OFF (seed 20003) | C_ON (seed 20004) | C_OFF (seed 20005) | D_ON (seed 20006) | D_OFF (seed 20007) |
|---|---|---|---|---|---|---|---|---|
| rule A | 0.120 | 0.212 | 0.134 | 0.169 | 0.296 | 0.197 | 0.171 | 0.166 |
| rule B | 0.058 | 0.088 | 0.122 | 0.118 | 0.370 | 0.067 | 0.064 | 0.059 |
| rule C | 0.015 | 0.022 | 0.083 | 0.134 | 0.127 | 0.025 | 0.226 | 0.009 |
| rule D | 0.188 | 0.178 | 0.165 | 0.192 | 0.323 | 0.218 | 0.216 | 0.163 |
| hold 1x | 0.069 | 0.051 | 0.050 | 0.077 | 0.176 | 0.071 | 0.149 | 0.065 |
| hold 2x | 0.704 | 0.604 | 0.595 | 0.592 | 0.728 | 0.633 | 0.507 | 0.559 |
| hold 3x | 0.949 | 0.898 | 0.888 | 0.866 | 0.923 | 0.908 | 0.733 | 0.855 |
| const 0.5 | 0.077 | 0.057 | 0.038 | 0.065 | 0.120 | 0.059 | 0.045 | 0.084 |
| const 1.0 | 0.155 | 0.134 | 0.094 | 0.121 | 0.182 | 0.140 | 0.100 | 0.149 |
| const 1.5 | 0.298 | 0.220 | 0.162 | 0.212 | 0.266 | 0.248 | 0.177 | 0.255 |
| const 2.0 | 0.468 | 0.393 | 0.328 | 0.363 | 0.409 | 0.412 | 0.306 | 0.373 |
| const 2.5 | 0.820 | 0.737 | 0.689 | 0.700 | 0.772 | 0.749 | 0.585 | 0.676 |
| const 3.0 | 0.949 | 0.898 | 0.888 | 0.866 | 0.923 | 0.908 | 0.733 | 0.855 |

### Table 5. Rules: average held level (median over paths; mean in brackets) and trades per year (median)

| row | A_ON (seed 20000) | A_OFF (seed 20001) | B_ON (seed 20002) | B_OFF (seed 20003) | C_ON (seed 20004) | C_OFF (seed 20005) | D_ON (seed 20006) | D_OFF (seed 20007) |
|---|---|---|---|---|---|---|---|---|
| rule A | 0.90 (1.07); 4.3 tr/yr | 0.91 (1.08); 4.5 tr/yr | 0.90 (1.01); 5.3 tr/yr | 0.96 (1.06); 4.1 tr/yr | 0.92 (1.03); 3.7 tr/yr | 0.90 (1.05); 4.0 tr/yr | 1.13 (1.16); 4.2 tr/yr | 0.90 (1.06); 4.4 tr/yr |
| rule B | 0.76 (0.85); 1.6 tr/yr | 0.79 (0.88); 1.7 tr/yr | 1.13 (1.20); 4.1 tr/yr | 1.11 (1.16); 4.3 tr/yr | 1.03 (1.12); 3.1 tr/yr | 0.74 (0.83); 1.3 tr/yr | 1.57 (1.62); 4.3 tr/yr | 0.74 (0.84); 1.5 tr/yr |
| rule C | 0.53 (0.62); 0.8 tr/yr | 0.58 (0.65); 0.8 tr/yr | 0.59 (0.66); 1.2 tr/yr | 0.60 (0.68); 1.2 tr/yr | 0.56 (0.64); 1.0 tr/yr | 0.50 (0.56); 0.9 tr/yr | 0.71 (0.78); 1.3 tr/yr | 0.55 (0.61); 0.8 tr/yr |
| rule D | 1.24 (1.23); 0.5 tr/yr | 1.23 (1.23); 0.4 tr/yr | 1.22 (1.22); 0.4 tr/yr | 1.23 (1.23); 0.4 tr/yr | 1.23 (1.23); 0.5 tr/yr | 1.23 (1.23); 0.5 tr/yr | 1.16 (1.17); 0.4 tr/yr | 1.23 (1.22); 0.4 tr/yr |

### Table 6. Rules: share of paths beating the same-basis hold 1x / the cell's best constant level

| row | A_ON (seed 20000) | A_OFF (seed 20001) | B_ON (seed 20002) | B_OFF (seed 20003) | C_ON (seed 20004) | C_OFF (seed 20005) | D_ON (seed 20006) | D_OFF (seed 20007) |
|---|---|---|---|---|---|---|---|---|
| rule A | 0.47 / 0.74 | 0.05 / 0.47 | 0.18 / 0.45 | 0.11 / 0.40 | 0.16 / 0.43 | 0.06 / 0.45 | 0.10 / 0.36 | 0.06 / 0.45 |
| rule B | 0.25 / 0.71 | 0.08 / 0.59 | 0.18 / 0.50 | 0.20 / 0.54 | 0.07 / 0.28 | 0.15 / 0.56 | 0.19 / 0.43 | 0.12 / 0.57 |
| rule C | 0.28 / 0.70 | 0.14 / 0.52 | 0.26 / 0.58 | 0.20 / 0.41 | 0.49 / 0.71 | 0.20 / 0.54 | 0.16 / 0.39 | 0.17 / 0.49 |
| rule D | 0.21 / 0.69 | 0.04 / 0.63 | 0.09 / 0.55 | 0.10 / 0.56 | 0.13 / 0.59 | 0.06 / 0.57 | 0.10 / 0.53 | 0.07 / 0.60 |

### Table 7. Primary (rule_D) under stress: median after-tax CAGR (%/yr) per cell and score

| setting | A_ON | A_OFF | B_ON | B_OFF | C_ON | C_OFF | D_ON | D_OFF | score | mean ON | mean OFF | worst cell | best single constant score, same setting |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| delay 2, cost 0.003 (default) | 4.51 | 3.60 | 4.18 | 4.21 | 3.89 | 3.79 | 5.49 | 5.12 | 4.35 | 4.52 | 4.18 | 3.60 | 2.99 |
| delay 3 | 4.53 | 3.60 | 4.18 | 4.20 | 3.87 | 3.77 | 5.54 | 5.10 | 4.35 | 4.53 | 4.17 | 3.60 | 2.99 (level 0.5) |
| delay 5 | 4.58 | 3.61 | 4.21 | 4.22 | 3.92 | 3.77 | 5.58 | 5.04 | 4.37 | 4.57 | 4.16 | 3.61 | 2.99 (level 0.5) |
| cost 0.006 | 4.43 | 3.51 | 4.07 | 4.12 | 3.81 | 3.72 | 5.40 | 5.05 | 4.26 | 4.43 | 4.10 | 3.51 | 2.97 (level 0.5) |

### Table 8. Paired bootstrap over paths (2000 resamples within each cell): score differences (pp)

| difference | point | sd | 90% interval | share of resamples > 0 |
|---|---|---|---|---|
| rule_D minus rule_A | 0.83 | 0.05 | [0.75, 0.93] | 1.000 |
| rule_D minus rule_B | 0.82 | 0.06 | [0.71, 0.92] | 1.000 |
| rule_D minus rule_C | 0.60 | 0.07 | [0.50, 0.71] | 1.000 |
| rule_D minus hold1 | -1.50 | 0.05 | [-1.59, -1.44] | 0.000 |
| rule_D minus const_0.5 | 1.36 | 0.06 | [1.27, 1.47] | 1.000 |

Share of bootstrap resamples in which each candidate wins under the full scoring rule (tie window and tie-break included): rule_A 0.000, rule_B 0.000, rule_C 0.000, rule_D 1.000

### Table 9. The synthetic worlds of the cells (medians over paths of the 30 traded years)

| cell | seed | arithmetic premium of the index over rf | volatility | worst index drawdown | mean rf |
|---|---|---|---|---|---|
| A_ON | 20000 | 3.08 | 17.41 | -52.7 | 4.00 |
| A_OFF | 20001 | 3.14 | 16.83 | -47.6 | 4.07 |
| B_ON | 20002 | 2.88 | 17.07 | -47.4 | 4.49 |
| B_OFF | 20003 | 3.15 | 16.93 | -48.5 | 4.06 |
| C_ON | 20004 | 2.90 | 17.55 | -55.4 | 4.31 |
| C_OFF | 20005 | 3.18 | 17.37 | -49.2 | 4.32 |
| D_ON | 20006 | 4.11 | 15.82 | -46.0 | 4.60 |
| D_OFF | 20007 | 3.81 | 17.22 | -45.6 | 4.90 |


## Reading the tables

- **The timing rules A and C do best in their own ON world, and only there does any rule reach the 1x hold.**
  - Rule C in C_ON: 5.69 % against hold 1x at 5.25 %. This is the only cell in which any rule beats the 1x hold, and C
    does so on 49 % of the paths.
  - Rule A in A_ON: 5.43 %, level with the 1x hold (5.43 %; A is 0.004 pp below), winning on 47 % of paths.
  - In the other seven cells, A and C land between -0.8 and +1.5 pp from the cell's best constant level, and 1.7 to
    3.4 pp below the 1x hold.
  - Rule B does not stand out in its own world: it is behind D in B_ON (3.74 % against 4.18 %) and level with D in B_OFF
    (4.24 % against 4.21 %).
  - Rule B's worst cell is C_ON at 0.52 %, with P(MDD <= -80 %) of 0.37. B levers up when its 20-day volatility
    estimate is low, and that is hit hard in a world of clustered crash days.
- **Rule D ranks first or second of the four rules in every cell (first in 5 of the 8).**
  - Its cell medians run from 3.60 % to 5.49 %.
  - It beats the cell's best constant level in all 8 cells, by +0.89 to +2.28 pp, on 53-69 % of paths.
  - It has both the highest ON mean (4.52 %) and the highest OFF mean (4.18 %) of the four candidates.
- **The constant levels are weak for a structural reason, not because exposure is bad.** The engine does not rebalance
  while the level stays the same. So a "constant level" is really a buy-and-hold of the 3x product next to cash, and its
  3x share shrinks over time (volatility drag and the 2.45 %/yr fee). The best constant level is 0.5 in 7 of the 8 cells
  (1.5 in D_ON). Choosing the best level separately in each cell, with hindsight, scores only 3.03 %.

## Caveats in plain words

1. **The primary is not a timing rule, and its win says nothing in favour of any market theory.**
   - Rule D holds an index exposure of 1.25 through the 3x product plus cash.
   - It rebuilds the engine's position internally and changes level only when the drifting 3x/cash mix has moved the
     effective exposure clearly away from 1.25. That happens about 0.4 times a year.
   - Its lead over the constant levels (+1.36 pp in the score) is an execution effect that works the same with the
     mechanism ON or OFF (ON mean 4.52 %, OFF mean 4.18 %). Its own designer and auditor say the same.
   - It wins because the timing edges of A, B and C did not carry over to the other designers' worlds, and because they
     held less exposure (C about 0.55, A about 0.9).
2. **It loses to simply holding the index (1x) everywhere.**
   - Hold 1x scores 5.85 %/yr against 4.35 % for rule D: -1.50 pp, bootstrap interval [-1.59, -1.44] pp.
   - Rule D is below the 1x hold in all 8 cells and beats it on only 4-21 % of paths.
   - At the anchored premium (about 3 % arithmetic for a price index), reaching exposure through a 3x product plus cash
     costs roughly 2-2.5 %/yr against a 1x hold. The cost comes from the cash spread, the tax on interest and the
     product fee.
   - The hoped-for 30 %/yr is far outside every synthetic number here: the best cell median of any row is 6.99 %
     (hold 1x, D_OFF).
3. **It has a fatter left tail than the 1x hold.**
   - P(MDD <= -80 %) is 0.16-0.32 per cell for rule D, against 0.05-0.18 for the 1x hold.
   - Its p10 CAGR is -2.0 % to -3.4 %, against about -0.8 % to +0.7 % for the 1x hold.
   - The reason is that it holds 1.25x exposure, partly in a 3x product that drifts between re-sets.
4. **The margin is clear statistically but narrow in its source.**
   - The bootstrap (D wins in 100 % of resamples; +0.60 pp over C, interval [+0.50, +0.71]) covers only the noise of
     sampling 1000 paths.
   - It does not cover the fact that all four simulators were centred on similar published anchors (premium about 3 %,
     volatility about 17 %), nor that each designer's world is weighted equally.
   - D's own world has the highest premium (about 4 %, because 35 % of its paths are total-return markets). D's rule
     does best there (5.49 % / 5.12 %), and those cells raise its mean.
5. **Robustness rows (Table 7).** Rule D is insensitive to the delay: 4.35 % at delay 3 and 4.37 % at delay 5,
   against 4.35 % at the default. Double cost (0.006) costs 0.09 pp (4.26 %). It stays far above the best constant
   level under each same setting (2.97-2.99 %).
6. **What the rule assumes about the real test.**
   - It hard-codes the engine's constants to track its own position: 300 warm-up columns, delay 2, the 2.45 %/yr
     product fee, the 2 % cash spread and the 15.4 % interest tax.
   - In this tournament the engine is the same as the one the rule copies, so the tracking is exact at delay 2 and only
     approximate at delays 3 and 5 (which the stress rows show to be harmless). If the real test engine differs, the
     tracking is only approximate.
   - It goes to cash when more than about half of recent days (20-day half-life) show no price change. That is right for
     a market that has not opened yet. It could cause unwanted cash spells on a series with many stale closes.
   - The exposure 1.25 comes from the designer's prior. It will be too high in a market with a much lower premium or
     higher volatility, and too low in one with a higher premium.
7. **Synthetic only.** These numbers come only from the four blind designers' simulators. They are not evidence about
   real markets. The single real test decides.

## Reproduction

`/root/.cache/ts-venv/bin/python -I -B tournament.py` rewrites tournament.json. It is deterministic and took 1 min 50 s
on 4 cores, and it produced the same numbers twice. `tournament.py --tables` then prints Tables 1-9 above from
tournament.json. `--P 50` is a quick smoke test that writes tournament_smoke.json; that file was deleted.

No cache was written: results pass between the worker processes in memory. The judge's temporary reading copies in the
session scratchpad (outside /mnt/project-files) were deleted at the end.

## What the judge read (blindness)

The judge read only these files. Nothing else under /mnt/project-files/research/theory_sim was opened, including round
1, test/, verify/, holdout/, r2/test/, r2/verify/, TEST_PROTOCOL files, and RESULT or FREEZE files. The judge used no
memory, no network and no market data.
- `r2/DESIGN_BRIEF_R2.md`
- `common/exec_engine.py`
- For each of r2/design/A, B, C and D: THEORY.md, sim.py, rule.py, design_log.md, AUDIT.md and synth_results.json
- The directory listings of those four folders

The session context contained names of market-data tools and skills; they were not used.

Listing the session scratchpad once, while deleting the judge's own temporary copies there, showed four file names
the judge did not create: blindcheck.py, tourn_args.json, ts2_design.js and ts2_tournament.js. They look like the
workflow's own files. They were not opened.

The judge also listed the round-2 `design/` folder (which showed only A-D), the `common/` folder and its
`__pycache__`.

## Files

- `tournament.py`: the script that reproduces everything here.
- `tournament.json`: all the numbers. It holds, for each cell, the median, p10, p90, P(MDD <= -80 %) and median MDD of
  every row, plus the average level, trades per year and paired win shares of the rules. It also holds the scores, the
  tie set, the stress rows, the bootstrap results, the seeds and the file hashes.
- `RESULT_TOURNAMENT.md`: this file.
