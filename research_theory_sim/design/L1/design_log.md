# design_log — lane TS1 / designer L1 (Margin-Ratchet Leverage Cycle)

All numbers in this log come from my own simulator (sim.py). Selection used seeds 11 and 12 only (both in 1-999);
final numbers use fresh seeds >= 10000. Every rule variant evaluated is logged with a running N in work/variants.csv
(baselines such as constant levels and holds are not counted as variants).

## Running notes (timestamped)
- 2026-11-04T07:23Z priors frozen (THEORY.md). 07:28Z amendment A1 (numerical guards, before any rule design).
- Diagnostics before rule design (seed 1, no rule evaluated): conditional forward 63-day excess returns by state;
  within-path regressions; ACF / variance ratios (work/analysis1.py, decomp.py, regress.py, acf.py).
  ON world: variance ratio 1.23 (5d), 1.69 (21d), 1.83 (63d), 1.51 (126d), 1.20 (252d), 0.97 (504d):
  momentum from days to ~3 months (gradual speculator re-/de-levering, multi-day cascades), reversal beyond
  (the leverage premium is a stationary function of trend/vol/capital state). OFF world: all ~1.
  The ratchet-gap state on its own is weakly predictive (top decile of memory/vol: higher forward excess, Kelly ~1.4
  vs ~0.1 overall); the decomposition shows predictability comes mainly from the speculator class.
- Families evaluated so far on seed 11 (P=1500, ON and OFF): F0 vol-target Kelly (N1-5), F1 + long reversal
  (N6-23), F2 + short momentum (N24-35), F3 binary trend filter (N36-50), F4 momentum + reversal + vol span
  (N51-98).
- 2026-11-04T07:50Z SELECTION CRITERION fixed now (before further search): maximise J = 0.5*ON + 0.5*OFF median after-tax
  CAGR on my simulator (mirrors the tournament score), SUBJECT TO OFF >= best constant level in OFF on the same
  seed (the rule must not lose to the best constant if the theory is false). Ties within 0.3 pp: fewer trades.
  Reason: the unconstrained J optimum (N90) has 28 trades/yr and an OFF loss of 1.5 pp vs the best constant, i.e.
  it buys ON performance with turnover that a random walk punishes.
- Coordinate search around N82 (N99-111), combinations (N112-120), ratchet-gap term G*log(memory/vol) on top of
  N119 (N121-124: changes J by <= 0.07 pp, i.e. nothing -> dropped for simplicity; the theory's named state adds no
  information beyond the two trend gaps in my own world).
- Confirmation on the second selection seed 12 (N125-131) of the 7 best seed-11 candidates.
  Feasible on BOTH seeds (OFF >= best constant OFF: 2.21% s11, 2.14% s12): N113 (J 6.61 / 6.28), N117 (6.34 / 5.98),
  N82 (5.90 / 5.78). N114, N119, N112, N116 fail the OFF constraint on seed 12 (or on both).
- 2026-11-04T07:59Z FINAL CHOICE: N113 = {m0 0.08, A 1.25, ns 42, B 0.5, nl 252, sv 120}, half Kelly fixed. Highest mean J
  among candidates feasible on both selection seeds. rule.py reproduces the candidate code (engine CAGR identical on
  seed 11: 10.71%), is causal (future perturbation leaves past targets unchanged), scale-invariant, NaN-safe,
  1.2 s for P=500 x T=10000. No selection happened after this line.
- 2026-11-04T08:07Z fresh-seed evaluation (seeds 10000 and 10001, 2000 paths each, 30 years) and diagnostics run; results below.

## Descriptive statistics of the synthetic worlds (sim.py, seed 1, 2000 paths, 30 y after warm-up; not targets)
| | ON | OFF |
|---|---|---|
| annual vol p10/50/90 | 0.113 / 0.152 / 0.192 | 0.112 / 0.152 / 0.191 |
| annual log drift p10/50/90 | 0.004 / 0.048 / 0.093 | -0.009 / 0.047 / 0.108 |
| daily skew p10/50/90 | -0.23 / -0.02 / 0.05 | -0.06 / 0.00 / 0.07 |
| excess kurtosis p10/50/90 | 0.13 / 0.54 / 5.17 | 0.23 / 0.50 / 2.46 |
| daily lag-1 autocorrelation p10/50/90 | 0.035 / 0.088 / 0.206 | -0.016 / 0.000 / 0.014 |
| lag-1 autocorrelation of abs returns p10/50/90 | -0.005 / 0.020 / 0.137 | ~0 |
| max drawdown p10/50/90 | -0.66 / -0.47 / -0.32 | -0.70 / -0.45 / -0.27 |
| short rate mean p10/50/90 | 0.018 / 0.039 / 0.071 | same path |
| speculator wipe-outs | 0.3% of paths | - |
| time-average speculator leverage p10/50/90 | 0.41 / 0.81 / 1.33 | - |
Variance ratios (ON, median path): 1.23 (5d), 1.69 (21d), 1.83 (63d), 1.51 (126d), 1.20 (252d), 0.97 (504d).
Honest reading: with the frozen wide priors the leverage cycle is MILD in the median world (desired leverage is
often below 1 because the carry m0 - R - s_b is small), margin constraints rarely bind, wipe-outs are rare, and
tails/vol clustering are weak. What is strong is the slow speculator re-/de-levering, which makes 1-3 month momentum
and a 6-24 month reversal of the premium.

## Checks of the theory's predictions inside my own simulator (seed 1 diagnostics)
1. Negative skew / vol clustering / multi-day moves: multi-day persistence YES (strong); skew and clustering only weak
   in the median world, strong in a minority of worlds.
2. Ratchet gap (memory of vol >> current vol) predicts higher returns: only in its top decile (Kelly ~1.4 vs ~0.1);
   adds nothing to the final rule (N121-124). The rule's edge is uncorrelated with the lender memory half-life tau_L
   (corr -0.04). So the named "ratchet" is not what the rule exploits; the speculator flow dynamics are.
3. Higher forward returns after deep drawdowns: YES (deepest half of drawdowns: +5.5..6.3%/yr forward excess vs
   -9..-10%/yr near the peak).
4. Rising short rates lower later returns: NOT confirmed — after the largest 126-day rate rises the forward excess was
   HIGHER (+3.5%/yr), apparently the reversal of rate-triggered (duration + speculator) sell-offs. The rule does not
   use rate changes; it uses the rate level only as the financing hurdle.

## Variants (N = 131 rule variants in total, all on selection seeds 11/12; full list in work/variants.csv)
| family | N | what | best J on its seed (ON / OFF) | best FEASIBLE J (OFF >= best const) |
|---|---|---|---|---|
| F0 vol-target half-Kelly (m0 - rf)/var | 1-5 | m0 grid | N2 3.00% (3.01 / 3.00) | N2 |
| F1 + long reversal -B*(lp - EMA_nl) | 6-23 | m0 x nl x B | N12 3.29% (4.37 / 2.20) | N9 2.91% (3.53 / 2.30) |
| F2 + short momentum A*(lp - EMA_ns) | 24-35 | ns x A | N26 5.40% (11.22 / -0.43) | N24 4.14% (5.54 / 2.75) |
| F3 binary trend filter on F0 | 36-50 | ns x m0 | N40 3.26% (6.16 / 0.36) | N48 2.22% (2.10 / 2.34) |
| F4 momentum + reversal + vol span | 51-98 | sv x A x ns x B x m0 | N90 6.93% (13.16 / 0.70) | N82 5.90% (9.27 / 2.54) |
| F5 coordinate sweep around N82 | 99-111 | one at a time | N102 6.67% (11.50 / 1.83) | N111 6.31% (10.25 / 2.38) |
| F6 combinations | 112-120 | | N116 6.95% (11.98 / 1.91) | N114 6.78% (11.34 / 2.23) |
| F7 + ratchet-gap term | 121-124 | G x memory half-life | N123 6.67% (11.05 / 2.30) | no gain vs N119 (<= +0.07 pp) |
| confirmation on seed 12 | 125-131 | 7 best candidates | N130 (=N116) 6.62% (11.63 / 1.61) | N126 (=N113) 6.28% (10.38 / 2.17) |
Selection procedure: grid / coordinate search on seed 11, criterion fixed at 07:50Z (max J = 0.5 ON + 0.5 OFF subject
to OFF >= best constant OFF), confirmation of the 7 best on seed 12, final = best mean J among candidates feasible on
both seeds (N113). Tunable parameters in the final rule: m0, A, ns, B, nl, sv (6). Half-Kelly 0.5 and the 3% vol floor
were fixed at the start and never varied.

## FINAL RULE (rule.py)
level_t = clip( 0.5 * [0.08 + 1.25*(lp_t - EMA42(lp)_t) - 0.5*(lp_t - EMA252(lp)_t) - 252*rf_t] / var_t , 0, 3 ),
var_t = 252 * EWMA120(log-return^2) (bias-corrected, floor 0.03^2). Inputs: close, rf.

## Fresh seeds 10000-10001 (4000 paths, 30 y, after tax): median CAGR (p10, P(MDD<=-80%))
| | mechanism ON | mechanism OFF |
|---|---|---|
| **rule** | **10.32%** (2.18%, 4.3%) | **2.47%** (-4.24%, 18.8%) |
| hold 1x | 3.87% (-0.03%, 2.0%) | 3.93% (-1.22%, 4.8%) |
| hold 2x | 0.32% | 0.29% |
| hold 3x | -3.72% | -3.78% |
| const 0.5 (best constant in both) | 2.02% (-0.03%, 4.0%) | 2.23% (-0.02%, 4.5%) |
| const 1.0 / 1.5 / 2.0 / 2.5 | 1.69 / 1.10 / 0.24 / -1.24% | 1.86 / 1.26 / 0.34 / -1.12% |
Trades/year 13.4 (ON), 11.4 (OFF); average level 0.80 (ON), 0.75 (OFF).
Mechanism-off: the rule beats the best constant level by +0.23 pp in median (loss vs best constant = -0.23 pp) but
LOSES to same-basis hold 1x by 1.46 pp and has a much fatter left tail (p10 -4.2% vs -0.0%; P(MDD<=-80%) 19% vs 4.5%).

## Robustness (fresh seeds)
| row | ON | OFF |
|---|---|---|
| base (delay 2, cost 0.3%) | 10.32% | 2.47% |
| delay 3 | 9.82% | 2.46% |
| delay 5 | 8.98% | 2.45% |
| cost 0.6% | 9.69% | 1.79% |
| prior narrowed (x0.5 width) | 15.65% (best const 1.65%, hold1x 3.84%) | 2.06% (best const 1.85%) |
| prior widened (x1.5 width) | 8.30% (best const 2.88%, hold1x 4.42%) | 3.37% (best const 3.05%) |
| 250-day block-resampled 30y paths from 100y ON paths | 10.52% (hold1x 3.84%, const0.5 2.30%) | - |
Edge attribution (ON, seed 10000): the rule's edge over const 0.5 rises with the effective speculator footprint
(Phi x time-average leverage): quartiles 1-4 give rule 4.2 / 8.8 / 14.4 / 23.3% vs const0.5 ~2%; corr(edge, Phi) +0.52,
corr(edge, phi_v) +0.17, corr(edge, kappa) +0.16, corr(edge, tau_L) -0.04.

## Concerns (honest)
- The synthetic predictability that the rule harvests (R^2 of 5-7% for 1-3 month forward excess returns in the median
  ON world) is a property of my priors on the speculators' adjustment speed and trend weight. If the real index has
  much weaker 1-3 month momentum / 1-2 year reversal, the rule falls back to its OFF behaviour: about the best constant
  level in median, with a clearly worse left tail than constant 0.5 and worse than hold 1x.
- The rule uses the short-rate LEVEL as the financing hurdle: in high-rate regimes it holds little or nothing.
- The theory's distinctive state (the lender-memory ratchet) did not earn a place in the rule.
