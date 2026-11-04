# design_log - lane TS2 round 2, blind designer A (Risk-Meter Leverage Clock)

All CAGR numbers are the engine's after-tax 30-year CAGR (after the final liquidation tax), `exec_engine.run` /
`exec_engine.hold`, delay 2, cost 0.003 unless stated. "med" = median over paths. "bc" = best constant level
(the single level, the same for all paths, with the highest median CAGR). Decimals: 0.0543 = 5.43 %/yr.

## 0. Timeline (UTC, from `date -u`)
| time | step |
|---|---|
| 10:46 | read DESIGN_BRIEF_R2.md and common/exec_engine.py |
| 10:51 | THEORY.md written (theory, predictions, falsification, published anchors, priors, mechanism-OFF) - before any simulation |
| 10:52-10:57 | sim.py written and run; pre-freeze calibration amendments (THEORY.md section 10: explosion guard, drawdown and rate anchors) |
| 10:57 | `PRIORS_FROZEN 2026-11-04T10:57Z` written in THEORY.md; no prior changed afterwards |
| 10:57-11:19 | rule design on selection seeds 1-5 only (N = 96 evaluations) |
| 11:20 | rule.py frozen (PARAMS literal), equivalence / causality / scale / NaN / speed checks |
| 11:21 | sim.py: robustness-only options added (`prior_width`, `mech_scale`); verified bit-identical output at defaults |
| 11:22-11:25 | final numbers on fresh seeds 10001-10008 (never used for selection) |

## 1. Simulator (frozen)
sim.py `simulate(P, T, seed, mechanism=True)`. 2000 x 7860 runs in ~10 s (ON) / ~7 s (OFF). Descriptive statistics
(seed 1, P = 2000) are in THEORY.md section 10: premium +1.4 % [-3.1, +6.2], vol 17 % [12, 23], worst 30y drawdown
-52 % (ON) / -48 % (OFF), P(DD <= -50 %) 0.55 / 0.44, 1x hold after-tax CAGR 5.2 %, mean rf 4.0 %.

Pre-freeze amendments (before any rule work): the first prior produced explosive worlds (speculators holding many
times the market); I bounded the speculator sector, made value traders more elastic for big gaps and narrowed the
trend-feedback range so the drawdown frequency sits near the published anchor. Details in THEORY.md section 10.

## 2. What the engine implies (found on seed 1 baselines, before rule design)
- Constant levels never rebalance: the L/3 sleeve of the 3x product decays relative to cash (3x vol drag + 2.45 %/yr
  fee), so constant levels are weak (bc = 0.5, ~2.3 %) while the same-basis 1x hold earns ~5.3 %.
- Reaching index exposure through 3x product + cash costs ~2.2 %/yr versus the 1x hold at rf ~4 % (cash pays
  rf - 2 % after 15.4 % tax, plus the product fee), almost independent of the level. With a central price-index
  premium of 1.5 %/yr the Kelly level is ~1. So G-ON (beat the 1x hold) needs > ~2 %/yr of timing value. This is the
  binding gate; beating the best constant is easy (and is partly a rebalancing artefact, see section 7).

## 3. Exploration of the mechanism (selection seed 1, not counted as variants: conditional statistics only)
Forward annualised excess log return from t+2 (63-day horizon unless stated):
| state at close t | ON | OFF |
|---|---|---|
| unconditional | +1.5 % | +1.6 % |
| fast/slow vol ratio > 1.2 and drawdown < -10 % (4.5 % of days), 5 / 10 / 21 days ahead | -22.9 / -15.2 / -7.2 % | +0.5 / +0.9 / +1.3 % |
| ratio > 1.4 and price < 100d-EMA (0.4 % of days), 5 / 10 days ahead | -62.9 / -40.4 % | -0.4 / +0.6 % |
| fast vol < 0.75 x its 21-day max and drawdown < -20 % (meter past peak), 5 / 63 days | +5.8 / +5.0 % | +1.3 / +1.1 % |
| calm (ratio < 0.8, drawdown > -5 %), 5 / 252 days | +9.2 / -1.4 % | +1.1 / +2.0 % |
| price > 100d-EMA + 20 % | -1.5 % | +1.4 % |
| deep drawdown (< -30 %) | +2.8 to +3.0 % | +0.5 to +1.4 % |
The theory's predictions show up in its own world: negative drift during cascades (days to weeks), a recovery
premium after the meter peaks, short-term re-leveraging drift but long-horizon fragility in calm, slow value
reversion. They are modest except the cascade, which is short (mean exit spell 13 days).

## 4. Variants evaluated (N counts every evaluated variant including grid points)
Rule families (all causal; levels in [0, 3]):
- VT: vol target k * sqrt(vlong / v_slow); VB: inverse ("vol boost"); TR: trend 100d-EMA two-level; DD: drawdown boost.
- CLOCK: state machine. normal -> base level Lb = clip(p0 / sigma_long^2 + 0.5, 0, 3) (Kelly with prior premium p0,
  sigma_long = expanding vol shrunk to 17 % with 5 years weight); cascade (fast EWMA variance hl_f > th_c^2 x slow
  meter hl_m AND log price < EMA(hl_tr)) -> L_c; leave cascade when fast < th_r^2 x meter -> recovery (L_r if
  drawdown < -d_r, until drawdown > -d_r/2) or normal. "Exit-only" = L_c = 0 and recovery = base level.

Stage 1, seed 1, P = 500 (hold1 ON 0.0506 / OFF 0.0505; bc ON 0.0215 / OFF 0.0220, L = 0.5):
| N | variant | ON | OFF |
|---|---|---|---|
| 1-4 | VT k = 1, 1.5, 2, 3 (never trades: target moves < 0.5) | 0.0208 / 0.0167 / 0.0106 / -0.0285 | 0.0213 / 0.0166 / 0.0115 / -0.0261 |
| 5-7 | VB k = 1, 1.5, 2 | 0.0208 / 0.0173 / 0.0114 | 0.0213 / 0.0167 / 0.0104 |
| 8-10 | TR lo/hi = 0.5/2, 1/3, 0/3 | 0.0230 / 0.0006 / 0.0044 | -0.0057 / -0.0350 / -0.0428 |
| 11-12 | DD<-0.2 boost 1/3, 1.5/3 | -0.0047 / -0.0040 | 0.0066 / 0.0003 |
| 13 | CLOCK Kelly base only (no cascade) | 0.0206 | 0.0205 |
| 14 | constant 1 base only | 0.0208 | 0.0213 |
| 15-18 | CLOCK th_c 1.3; d_r 0.1/0.2; L_r 2/3 (L_c 0) | 0.0450 / 0.0241 / 0.0488 / 0.0381 | 0.0197 / -0.0032 / 0.0232 / 0.0094 |
| 19-22 | CLOCK th_c 1.6; same grid | 0.0339 / 0.0316 / 0.0323 / 0.0314 | 0.0235 / 0.0204 / 0.0244 / 0.0236 |
| 23 | decomposition: exit only (th_c 1.3) | 0.0492 | 0.0280 |
| 24 | decomposition: recovery boost only | 0.0379 | 0.0258 |
| 25-37 | one-at-a-time around N=17: th_c 1.2/1.4; L_c 0.5; L_r 2.5/1.5; d_r 0.3; p0 0.03/0.0; hl_m 50/15; hl_f 10; hl_tr 50; d_exit 0.02 | 0.0467 / 0.0427 / 0.0447 / 0.0443 / 0.0499 / 0.0501 / 0.0438 / 0.0461 / 0.0499 / 0.0421 / 0.0308 / 0.0450 / 0.0498 | 0.0174 / 0.0279 / 0.0264 / 0.0174 / 0.0253 / 0.0249 / 0.0161 / 0.0267 / 0.0236 / 0.0271 / 0.0254 / 0.0244 / 0.0211 |
Finding: the cascade exit is the useful part; the recovery boost adds little in ON and costs in OFF.

Stage 2, exit-only grid, seeds 2+3, P = 1000 each (mean of the two seed medians; hold1 ON 0.0529 / OFF 0.0538;
bc ON 0.0231 / OFF 0.0233, L = 0.5). Columns: ON, ON - hold1, OFF - bc, trades/yr.
| N | p0 | th_c | hl_m | ON | ON-h1 | OFF-bc | tr/yr |
|---|---|---|---|---|---|---|---|
| 38-45 | 0.00 | 1.25/1.25/1.30/1.30/1.35/1.35/1.45/1.45 | 25/40 alternating | 0.0454 0.0460 0.0438 0.0455 0.0421 0.0442 0.0367 0.0406 | -0.0075 ... -0.0162 | +0.005 to +0.007 | 0.9-4.3 |
| 46-53 | 0.01 | same | same | 0.0526 0.0536 0.0508 0.0515 0.0484 0.0507 0.0409 0.0456 | -0.0003 +0.0007 -0.0021 -0.0014 -0.0045 -0.0022 -0.0120 -0.0074 | +0.005 to +0.008 | 0.9-4.3 |
| 54-61 | 0.02 | same | same | 0.0547 **0.0563** 0.0523 0.0539 0.0497 0.0520 0.0422 0.0468 | +0.0018 **+0.0033** -0.0006 +0.0010 -0.0032 -0.0009 -0.0108 -0.0061 | +0.0026 **+0.0026** +0.0047 +0.0038 +0.0065 +0.0053 +0.0057 +0.0064 | 0.9-4.3 |
| 62-67 | 0.02 | 1.15/1.15/1.20/1.20/1.25/1.25 | 40/60 alternating | 0.0567 0.0564 0.0565 0.0559 0.0563 0.0561 | +0.0038 +0.0035 +0.0035 +0.0029 +0.0033 +0.0032 | -0.0010 -0.0019 +0.0010 +0.0005 +0.0026 +0.0021 | 4.3-7.2 |
| 68-73 | 0.03 | same | same | 0.0558 0.0553 0.0556 0.0545 0.0539 0.0543 | +0.0029 +0.0024 +0.0027 +0.0016 +0.0010 +0.0014 | -0.0082 -0.0079 -0.0059 -0.0066 -0.0038 -0.0045 | 4.3-7.2 |
Plateau: p0 = 0.02, th_c 1.15-1.25, hl_m 40-60. Chosen centre: p0 0.02, th_c 1.25 (fewest trades on the plateau with
OFF >= bc), hl_m 40.

Stage 3, one-at-a-time around (p0 0.02, th_c 1.25, hl_m 40, hl_f 5, hl_tr 20, th_r 1.0), seeds 2+3:
| N | change | ON | ON-h1 | OFF-bc | tr/yr |
|---|---|---|---|---|---|
| 74 | hl_f 3 | 0.0547 | +0.0017 | -0.0009 | 7.7 |
| 75 | hl_f 8 | 0.0505 | -0.0025 | +0.0055 | 2.0 |
| 76 | hl_tr 10 | 0.0558 | +0.0029 | +0.0016 | 4.6 |
| 77 | hl_tr 40 | 0.0530 | +0.0000 | +0.0019 | 4.0 |
| 78 | no trend condition | 0.0469 | -0.0061 | -0.0020 | 8.2 |
| 79 | th_r 0.9 | 0.0571 | +0.0042 | +0.0017 | 4.0 |
| 80 | th_r 1.1 | 0.0533 | +0.0004 | +0.0025 | 4.6 |
| 81 | recovery L_r 1.5, d_r 0.2 | 0.0572 | +0.0043 | +0.0000 | 4.3 |
| 82 | recovery L_r 2.0, d_r 0.3 | 0.0585 | +0.0056 | -0.0012 | 4.4 |
| 83 | base on the meter vol instead of long-run vol | 0.0547 | +0.0018 | +0.0018 | 4.6 |
| 84-86 | robustness rows of the centre (delay 3 / delay 5 / cost 0.006), not selection | 0.0532 / 0.0492 / 0.0503 | +0.0003 / -0.0037 / -0.0027 | +0.0019 / +0.0026 / -0.0033 | 4.3 |
| 87 | online premium estimate, prior weight 10 y | 0.0335 | -0.0194 | -0.0083 | 3.8 |
| 88 | online premium estimate, prior weight 30 y | 0.0438 | -0.0091 | -0.0027 | 4.0 |
| 89 | cascade also needs drawdown < -5 % | 0.0559 | +0.0030 | +0.0026 | 4.2 |
| 90 | cascade also needs drawdown < -3 % | 0.0563 | +0.0034 | +0.0027 | 4.3 |
Online premium estimation (brief 2c) was tested and rejected: with 17 % vol the premium is not learnable within a
path, and the moving estimate only adds level noise and trades. Online volatility estimation is kept (sigma_long).

Stage 4, confirmation on new selection seeds 4+5, P = 1000 each (hold1 ON 0.0497; bc ON 0.0228 / OFF 0.0229):
| N | variant | ON | ON-h1 | OFF-bc |
|---|---|---|---|---|
| 91 | A: centre (exit only) | 0.0543 | +0.0045 | -0.0013 |
| 92 | B: A + th_r 0.9 | 0.0551 | +0.0054 | -0.0007 |
| 93 | C: A + recovery L_r 1.5 | 0.0543 | +0.0046 | -0.0029 |
| 94 | D: th_c 1.2 | 0.0555 | +0.0058 | -0.0022 |
| 95 | E: p0 0.015 (prior centre) | 0.0533 | +0.0036 | +0.0002 |
| 96 | F: th_c 1.3 | 0.0528 | +0.0031 | +0.0007 |

Total N = 96 (93 selection variants + 3 robustness rows on selection seeds).

## 5. Selection procedure and final rule
Selection used only seeds 1-5 (all <= 999). I kept the simplest member of the plateau that the theory implies:
exit only (no recovery boost, which adds nothing robust), th_r = 1.0 (the theory's natural "meter has stopped rising"
point; 0.9 was marginally better on both seed pairs but within noise). B and D were not preferred because their gains
are within noise and D trades more.
Final rule (rule.py, 6 tunable parameters): `PARAMS = {'p0': 0.02, 'th_c': 1.25, 'hl_f': 5, 'hl_m': 40, 'hl_tr': 20,
'th_r': 1.0}`; fixed prior constants (not tuned): prior vol 17 %, prior weight 5 years, base formula p0/sigma^2 + 0.5.
- base level = clip(p0 / sigma_long^2 + 0.5, 0, 3), sigma_long = expanding vol of live days shrunk to 17 %;
- go to 0 when EWMA variance (hl 5) > 1.25^2 x EWMA variance (hl 40) and log price < EMA(20) of log price;
- come back to the base level when EWMA variance (hl 5) < EWMA variance (hl 40).
rule.py checks (work/check_rule.py): equals the design implementation up to the live-day bookkeeping (seeds 2+3:
ON 0.0561 vs 0.0563, OFF 0.0259 vs 0.0259); scale-invariant (max diff 1e-14); causal (future perturbation leaves
earlier columns identical); input not modified; NaN / zero / flat stretches handled (EWMAs update only on live days,
NaN target before the first live return); P = 500, T = 10000 in 1.1 s.

## 6. Final numbers on FRESH seeds 10001 + 10002 (P = 2000 pooled; never used for selection)
| | ON med | ON p10 | ON p90 | ON MDD med | ON P(DD<=-80%) | OFF med | OFF p10 | OFF MDD med |
|---|---|---|---|---|---|---|---|---|
| **rule** (avg level 0.91, 4.3 trades/yr) | **0.0543** | -0.0093 | 0.1375 | -0.62 | 0.124 | **0.0246** | -0.0330 | -0.65 |
| hold 1x | 0.0531 | +0.0032 | 0.1145 | -0.52 | 0.061 | 0.0535 | +0.0038 | -0.47 |
| hold 2x | 0.0190 | -0.0762 | 0.1187 | -0.87 | 0.667 | 0.0201 | -0.0748 | -0.85 |
| hold 3x | -0.0203 | -0.1692 | 0.1208 | -0.98 | 0.939 | -0.0190 | -0.1667 | -0.97 |
| const 0.5 (= best constant, both worlds) | 0.0228 | -0.0016 | 0.0731 | -0.36 | 0.086 | 0.0229 | -0.0016 | -0.32 |
| const 1.0 | 0.0199 | | | | | 0.0203 | | |
| const 1.5 | 0.0153 | | | | | 0.0153 | | |
| const 2.0 | 0.0085 | | | | | 0.0089 | | |
| const 2.5 | -0.0025 | | | | | -0.0022 | | |
| const 3.0 | -0.0203 | | | | | -0.0190 | | |

### Design gates (fresh seeds, P = 2000)
| gate | rule | comparison | margin | verdict |
|---|---|---|---|---|
| G-ON vs 1x hold | 0.0543 | 0.0531 | +0.0012 | PASS (thin) |
| G-ON vs best constant (0.5) | 0.0543 | 0.0228 | +0.0315 | PASS |
| G-OFF: rule - best constant >= -0.010 | 0.0246 | 0.0229 | +0.0017 | PASS |
Precision extension, fresh seeds 10005-10008 (P = 4000, same frozen rule, run after the table above and reported
whatever it showed): ON rule 0.0540 vs hold1 0.0514 (+0.0026) vs bc 0.0227; OFF rule 0.0230 vs bc 0.0229 (+0.0001).
Both gates pass again. Paired view: the rule beats the 1x hold on only 46-47 % of ON paths (it wins the median by a
fatter right tail, p90 13.8 % vs 11.5 %, with a worse left tail, p10 -0.9 % vs +0.3 %).

### Robustness (fresh seeds)
| row | ON rule | ON - hold1 | ON - bc | OFF rule | OFF - bc |
|---|---|---|---|---|---|
| default (delay 2, cost 0.003) | 0.0543 | +0.0012 | +0.0315 | 0.0246 | +0.0017 |
| delay 3 | 0.0514 | -0.0017 | +0.0286 | 0.0242 | +0.0013 |
| delay 5 | 0.0465 | -0.0066 | +0.0237 | 0.0246 | +0.0017 |
| cost 0.006 | 0.0481 | -0.0050 | +0.0253 | 0.0182 | -0.0047 |
| prior narrowed (width 0.5, seed 10003) | 0.0543 | +0.0014 (h1 0.0528) | +0.0317 | 0.0241 | +0.0014 |
| prior widened (width 1.5, seed 10003) | 0.0554 | +0.0038 (h1 0.0516) | +0.0308 | 0.0239 | -0.0007 |
| mechanism weak (S0 x 0.5, seed 10004) | 0.0363 | -0.0135 (h1 0.0498) | +0.0139 | | |
| mechanism strong (S0 x 1.5, seed 10004) | 0.0690 | +0.0200 (h1 0.0490) | +0.0464 | | |

## 7. Honest assessment
- The mechanism produces a real, tradeable signal in its own world: while the rule is out of the market (selection
  seed 2, design implementation) the ON drift
  is -17.6 %/yr (OFF: +1.5 %/yr), out ~11 % of the time in ~2 spells per year of ~13 days.
- After the cost of reaching exposure through 3x product + cash (~2.2 %/yr vs the 1x hold) almost all of that edge is
  used up: the rule beats the 1x hold by only 0.1-0.3 pp of median CAGR, on fewer than half of the paths, and it loses
  to the 1x hold with delay 3 (-0.17 pp), delay 5 (-0.66 pp), double cost (-0.50 pp) or a weaker mechanism
  (-1.35 pp). G-ON passes at the default settings only; I do not consider the edge over the 1x hold robust.
- The large margin over the best constant level is mostly structural: constant levels never rebalance, so their 3x
  sleeve decays; any rule that re-trades a few times a year gets rebalanced (in the OFF world the rule beats bc by
  +0.2 pp with no edge at all). G-OFF passing means the rule is not harmful in a random walk, not that it has skill.
- The rule has deeper drawdowns than the 1x hold (median MDD -62 % vs -52 %; P(DD <= -80 %) 12 % vs 6 %): its base
  level is high in low-volatility markets and its 3x sleeve is not rebalanced between trades.
- The rule ignores rf and y10. Its average level is ~0.9, chosen by a Kelly formula with a 2 % price premium prior;
  in a market with a much higher premium it will under-lever relative to the best constant level.
