# design_log - designer C, lane TS2 r2, theory "Fast Aftershocks, Slow Scars" (FASS)

All numbers are medians over paths of the 30-year after-tax CAGR from `exec_engine.run` (T = 7860, delay 2, cost 0.003)
unless stated. "vs h1" = minus the same-basis hold 1x; "vs best" = minus the best constant level of that world.
Every evaluated parameter set is logged in `work/variants.csv` (one row per world).

## Timeline
- 2026-11-04T10:46Z brief and exec_engine read; folder created.
- 2026-11-04T10:54Z READ_LOG started; THEORY.md written (no simulation before it).
- 2026-11-04T10:56Z PRIORS_FROZEN (THEORY.md). sim.py written afterwards; no prior was changed after this line.
  (After the freeze I only added a diagnostics-only `override=` argument to sim.py for the falsification stress worlds of S3;
  it does not change the priors or the default worlds.)
- 2026-11-04T10:58Z first simulator run (descriptive statistics below).
- 11:00-11:25Z exploration E1-E10 (seeds 1-3), selection S1 (seeds 1-4), S2 (seeds 5-8).
- 2026-11-04T11:25Z S3 declared and started (seeds 9-12).
- 2026-11-04T11:31Z final rule chosen by the declared S3 rule; rule.py PARAMS set; equality with the selection code path checked.
- 2026-11-04T11:32Z single fresh-seed evaluation (seeds 10001-10004) started; 11:39Z results written (synth_results.json).

## Simulator description (seed 1, P=500 and P=2000; these describe the theory, they are not targets)
| world | realised arith excess premium med [p10, p90] | vol med [p10, p90] | worst drawdown med [p10, p90] | P(MDD <= -50%) | hold 1x CAGR med [p10, p90] |
|---|---|---|---|---|---|
| ON  | 0.031 [-0.021, 0.079] | 0.177 [0.129, 0.246] | -0.554 [-0.862, -0.317] | 0.58 | 0.054 [-0.009, 0.135] |
| OFF | 0.027 [-0.016, 0.079] | 0.174 [0.127, 0.239] | -0.495 [-0.781, -0.272] | 0.49 | 0.054 [-0.012, 0.139] |
Other ON-world facts: P(a z<-3 day within the next 20 days | z<-3 today) = 0.40 vs 0.12 unconditional (OFF: 0.14 vs 0.13);
mean |r| autocorrelation (lags 1, 5, 20) 0.12 (OFF 0.00); median monthly skew -0.18 (OFF -0.28); rf median 4.6%/yr
(p5 0%, p95 13.7%). The conditional mean m(t) has a per-path time sd of about 9.5%/yr.
Comparison with the drawdown anchor (THEORY.md A5): the simulated drawdowns are deeper than my rough anchor (median about
-55% ON / -50% OFF vs the -40% to -50% I expected; P(MDD <= -50%) 0.58 / 0.49 vs 0.25-0.40). Most of this already appears
in the OFF world, i.e. it comes from the low price-index premium (3% arithmetic, ~1.5% log) with 17.5% volatility, and from
the paths with a negative drawn premium, not from the crash mechanism. Priors were frozen, so I report it rather than tune it.
Monthly skew: ON is LESS negatively skewed than OFF (prediction P5 is not borne out by my own simulator): inside crash
clusters the compensating drift and the high diffusive vol also create large up days.

## What the frozen prior implies (found in E2/E4, before any rule was chosen)
The verbal prediction P3 in THEORY.md ("reward/variance lowest inside crash clusters") is NOT what the frozen priors
produce. With the prior means (theta_a ~0.6, psi ~1) the in-cluster term (1+psi)*theta_a - 1 is positive on average, the
overshoot unwinding R(t) starts right after a crash, and the scar jumps at the crash; because the unconditional premium is
fixed per path, the calm periods carry a BELOW-average premium. E2 (seed 1, ON): binned by fast/slow variance ratio, the
realised forward 21-day excess return goes from -0.6%/yr (calmest 20%) to +16.6%/yr (most turbulent 5%), with forward
variance rising only 4x; the Kelly ratio rises from <0 to ~2.2. By drawdown depth the Kelly ratio is highest near highs.
E4 (pooled OLS of the true m(t) on causal features, seed 3): the best single predictors are SLOW: the crash-day count over
~1 year (R2 0.19) and log(var_250d / var_1000d) (R2 0.19); fast variance ratios carry little information on m (R2 <= 0.06)
but most of the information on the conditional variance (R2 0.6). All features together: R2 0.31 for m.
This is the "slow reward clock / fast risk clock" structure of the theory, with the reward clock pointing UP after turbulent
years. The rule below follows this; it is a bet on the scar + overshoot premium.

## Variants evaluated (N)
| stage | seeds (P) | family | variants | best result (ON / OFF) |
|---|---|---|---|---|
| E1 | 1-2 (1000) | variance Kelly L = c/v_f (c 0.02-0.06, hl 10/30/100) | 9 | ON loses to best const (-0.2 to -5.8 pp); OFF +0.1..+0.4 pp at c=0.02 |
| E2 | 1 (500) | diagnostics of m(t) by state (no rule) | 0 | - |
| E3 | 1-2 | turbulence L = beta*(v_f/v_s - c0) | 8 | ON 4.83% (h1 5.49%), OFF +0.46 pp vs best |
| E4 | 3 (500) | regression diagnostics (no rule) | 0 | - |
| E5 | 1-2 | scar Kelly (c + a*log(v250/v1000))/v_f | 8 | ON 4.82%, OFF +0.17 pp |
| E6 | 1-2 | upper-bound check: 17-coefficient regression filter fitted on seed 3 (not a candidate) | 2 | ON 6.07% (+0.58 pp vs h1), OFF -0.93 pp |
| E7 | 1-2 | crash-count Kelly (c + a*crashcount_250d)/v_f | 9 | ON 3.99% |
| E8 | 1-2 | two-signal Kelly (c + a*lvs + b*lvr60)/v_f20 | 12 | ON 5.66% (+0.17 pp vs h1), OFF +0.11 pp |
| E9 | 1-2 | extension of E8 | 12 | ON 6.35% (+0.86 pp), OFF +0.02 pp |
| E10 | 1-2 | one-at-a-time scan (a, hf, hs/hss, hm) | 10 | flat 6.1-6.6% ON; OFF -0.0..-0.4 pp |
| S1 | 1-4 (2000) | final code path (debiased EWMA), c x a x b x hf grid + 3 single-feature variants | 57 | best ON-h1 +0.39 pp (a=0.3, b=0.08, hf=40) |
| S2 | 5-8 (2000) | tied structure (hss=4hs, hm=hs/4), a up to 0.5, hf 40/60, hs 180-350, c | 24 | ON-h1 up to +1.03 pp (a=0.5), but P(MDD<=-80%) 0.37-0.42 |
| S3 | 9-12 (2000) | 4 worlds incl. falsification stress worlds, 18 variants | 18 | see below |
Running total N (parameter sets evaluated) = see "Final N" below.

S1 note: the final code path uses a debiased EWMA (weights renormalised over valid days, no fixed variance prior), which
makes the rule neutral in the first years of a series; the edge vs hold 1x on seeds 1-4 was smaller (+0.2..+0.4 pp) than on
seeds 1-2 with the earlier prior-initialised filters.
S2 note: the ON edge rises with a up to ~0.4-0.5 but so does the tail: P(MDD <= -80%) 0.21 (a=0.3) -> 0.31 (a=0.4) ->
0.39 (a=0.5); p10 CAGR -1.2% -> -2.0% -> -2.7%. A large a means near-maximum leverage whenever the past year was much more
volatile than the long run, which is a bet that the scar premium exists. This is why S3 adds the theory's own
falsification worlds before the final choice.

## S3 declaration (written before S3 was run, 2026-11-04T11:25Z)
Seeds 9-12, P=2000 per world. Worlds: ON, OFF, NOSCAR (falsification F2: theta_s = 0, q = 0), FLAT (F2 + F5:
theta_s = 0, q = 0, theta_a = theta_b = 1, psi = 0; crash and volatility clustering remain but the conditional mean is
constant). Objective: mean over the four worlds of (rule median CAGR - best constant median of that world). Constraints:
G-ON on seeds 9-12 (ON median > hold 1x and > best constant) and OFF >= best constant - 0.5 pp. Ties within 0.1 pp:
lower P(MDD <= -80%) in ON. Grid: c = 0.02, hf = 40, a in {0.2, 0.3, 0.4, 0.5} x b in {0.04, 0.08} x hs in {250, 350},
plus a in {0.0, 0.1} with b = 0.04, hs = 250 (18 variants).

## S3 results (seeds 9-12, P=2000 per world; c = 0.02, hf = 40)
Baselines: ON hold1 5.46%, best const 2.62% (@0.5); OFF hold1 5.47%, best 2.64%; NOSCAR best 2.67%; FLAT best 2.66%.
| a | b | hs | objective | ON | ON - h1 | OFF - best | NOSCAR - best | FLAT - best | P(MDD<=-80%) ON / FLAT |
|---|---|---|---|---|---|---|---|---|---|
| 0.2 | 0.04 | 250 | +0.86 pp | 5.29% | -0.17 pp | +0.45 | +0.34 | +0.00 | 0.11 / 0.13 |
| 0.2 | 0.04 | 350 | +0.82 | 5.29% | -0.17 | +0.42 | +0.26 | -0.06 | 0.11 / 0.14 |
| 0.2 | 0.08 | 250 | +0.86 | 5.30% | -0.15 | +0.46 | +0.38 | -0.07 | 0.14 / 0.15 |
| **0.2** | **0.08** | **350** | **+0.88** | **5.48%** | **+0.02** | **+0.41** | **+0.34** | **-0.09** | **0.13 / 0.16** |
| 0.3 | 0.04 | 250 | +0.84 | 5.70% | +0.24 | +0.43 | +0.16 | -0.31 | 0.20 / 0.28 |
| 0.3 | 0.04 | 350 | +0.82 | 5.62% | +0.17 | +0.52 | +0.08 | -0.32 | 0.19 / 0.26 |
| 0.3 | 0.08 | 250 | +0.79 | 5.78% | +0.32 | +0.35 | +0.07 | -0.39 | 0.22 / 0.31 |
| 0.3 | 0.08 | 350 | +0.86 | 5.91% | +0.45 | +0.45 | +0.10 | -0.39 | 0.20 / 0.29 |
| 0.4 | 0.04 | 250 | +0.74 | 5.93% | +0.48 | +0.40 | -0.13 | -0.62 | 0.28 / 0.40 |
| 0.4 | 0.04 | 350 | +0.76 | 5.86% | +0.40 | +0.51 | -0.11 | -0.59 | 0.25 / 0.36 |
| 0.4 | 0.08 | 250 | +0.68 | 6.01% | +0.55 | +0.29 | -0.21 | -0.72 | 0.30 / 0.42 |
| 0.4 | 0.08 | 350 | +0.76 | 6.15% | +0.69 | +0.37 | -0.23 | -0.61 | 0.27 / 0.40 |
| 0.5 | 0.04 | 250 | +0.55 | 6.09% | +0.63 | +0.26 | -0.48 | -1.03 | 0.36 / 0.50 |
| 0.5 | 0.04 | 350 | +0.65 | 6.09% | +0.63 | +0.38 | -0.35 | -0.88 | 0.32 / 0.46 |
| 0.5 | 0.08 | 250 | +0.52 | 6.16% | +0.70 | +0.17 | -0.45 | -1.16 | 0.38 / 0.52 |
| 0.5 | 0.08 | 350 | +0.64 | 6.31% | +0.86 | +0.31 | -0.45 | -0.98 | 0.33 / 0.48 |
| 0.0 | 0.04 | 250 | +0.35 | 2.86% | -2.60 | +0.23 | +0.55 | +0.40 | 0.07 / 0.02 |
| 0.1 | 0.04 | 250 | +0.73 | 4.54% | -0.92 | +0.46 | +0.40 | +0.15 | 0.05 / 0.04 |
Selection by the declared rule: the highest objective among gate-passing variants is a=0.2, b=0.08, hs=350 (+0.88 pp); the
other gate-passing variants within 0.1 pp (a=0.3 with b/hs variants, +0.79..+0.86) have higher P(MDD<=-80%), so the
tie-break keeps a=0.2, b=0.08, hs=350. Its G-ON margin on seeds 9-12 was only +0.02 pp, i.e. a coin flip; I did not
re-select after seeing that. The S3 table shows the trade-off honestly: a larger scar coefficient a buys ON-world CAGR
(up to +0.9 pp over hold 1x) at the price of losses in the theory's own falsification worlds and a much fatter tail.

## Final rule (frozen in rule.py)
L_t = clip( (c + a*log(v_hs/v_4hs) + b*log(v_hs/4 / v_hs)) / (252 * v_hf), 0, 3 ), NaN (cash) until 250 valid returns.
v_h = debiased EWMA (half-life h trading days) of squared daily log returns over valid days (finite, positive, non-zero
change). PARAMS: c = 0.02, a = 0.2, b = 0.08, hf = 40, hs = 350 (5 tunable parameters; the very slow half-life 4*hs = 1400,
the mid half-life hs/4 = 87.5, the cap 3 and the 250-observation warm-up are fixed structure). Inputs: close only (rf is
accepted but unused). Pure numpy + math, causal, scale-invariant, does not modify inputs (work/t_rule_edge.py passes:
NaN at the start, flat stretches, zeros, single gaps, scale x1234.5, future-perturbation causality check).
Speed: P=500, T=10000 in 1.1 s.
Theory reading: c/(252 v_hf) is a fractional Kelly on the anchor premium (c ~ 0.7 x (3% - 0.25% vehicle cost)); the a-term
is the slow reward clock (scar + overshoot: the past ~year more volatile than the past ~4 years -> higher expected return);
the b-term is the medium-term turbulence premium; the denominator is the fast risk clock (40-day half-life variance).

## Final numbers on FRESH seeds 10001-10004 (P = 2000 per world; never used for selection)
| world | rule med | p10 | p90 | P(MDD<=-80%) | avg level | trades/yr | hold 1x | hold 2x | hold 3x | const 0.5 / 1 / 1.5 / 2 / 2.5 / 3 | best const |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ON  | 5.39% | -0.54% | 15.45% | 0.144 | 0.56 | 1.1 | 5.44% (dd80 0.165) | 1.97% | -2.79% | 2.74 / 2.55 / 2.12 / 1.36 / 0.16 / -2.79 | 2.74% @0.5 |
| OFF | 3.04% | -0.94% | 9.75% | 0.025 | 0.51 | 0.9 | 5.34% (dd80 0.084) | 1.50% | -3.27% | 2.75 / 2.47 / 2.00 / 1.30 / -0.10 / -3.27 | 2.75% @0.5 |
Paired bootstrap over paths (90% CI): ON rule - hold1x = -0.04 pp [-0.27, +0.21]; ON rule - best const = +2.65 pp
[+2.40, +2.90]; OFF rule - best const = +0.29 pp [+0.15, +0.46]; OFF rule - hold1x = -2.30 pp.

## Design gates (fresh seeds, P = 2000)
| gate | requirement | result | pass |
|---|---|---|---|
| G-ON | ON rule median > hold 1x (5.44%) and > best constant (2.74%) | 5.39%: -0.04 pp vs hold 1x, +2.65 pp vs best constant | **NO** (fails vs hold 1x by 0.04 pp; statistically a tie) |
| G-OFF | OFF rule median >= best constant - 1.0 pp | 3.04% vs 2.75%: +0.29 pp | YES |

## Robustness (fresh seeds)
| row | ON median | OFF median |
|---|---|---|
| base (delay 2, cost 0.3%) | 5.39% | 3.04% |
| delay 3 | 5.37% | 3.04% |
| delay 5 | 5.34% | 3.04% |
| cost 0.6% | 5.29% | 2.99% |
| prior narrowed (s = 0.5) | 5.39% (hold1 5.36%, best const 2.41%) | 3.02% (best const 2.51%) |
| prior widened (s = 1.5) | 5.36% (hold1 5.45%, best const 3.03%) | 3.09% (best const 2.97%) |
| NOSCAR stress (F2: no scar, no overshoot) | 3.10% (hold1 5.42%, best const 2.75%) | - |
| FLAT stress (F2+F5: clustering, constant mean) | 2.63% (hold1 5.46%, best const 2.75%) | - |
Mechanism-off world: the rule sits near level 0.5 (median average level 0.51, < 1 trade/yr) and beats the best constant by
+0.29 pp because its fast variance estimate adapts the level to each path's volatility; it is 2.3 pp behind hold 1x there,
as every level-0.5 strategy is (the 3x product + cash vehicle costs about 2.4%/yr against hold 1x at any level).

## Conclusion (honest)
- The mechanism is tradeable against constant levels: in the ON world the rule beats the best constant level by ~2.7 pp
  per year, with a lower 80%-drawdown probability than hold 1x (0.144 vs 0.165). In the OFF world it costs nothing (+0.3 pp
  vs the best constant).
- It does NOT beat the same-basis hold 1x in the ON world on fresh seeds (-0.04 pp, a statistical tie), so G-ON fails.
  The reason is structural: the price-index premium of the anchors is ~3% arithmetic, and holding any level through the
  3x product + cash costs ~2.4%/yr against hold 1x; timing has to recover that drag before it can win.
- Variants with a larger scar coefficient (a = 0.3-0.5) did beat hold 1x on selection seeds by +0.2 to +1.0 pp, but they
  lose in the theory's own falsification worlds (NOSCAR, FLAT) and roughly double to triple P(MDD <= -80%). Under my
  declared selection rule I shipped the conservative one; I did not re-select after the fresh-seed result.
- Because no tested rule passed both gates on fresh seeds, the shipped rule is also the "fallback" of the brief: a simple
  online-volatility Kelly exposure with a slow theory term, which beats the best constant level in both worlds.
  The crash mechanism added edge over constant exposure, but no edge over buy-and-hold 1x after the vehicle's costs.
- Expected weakness on real data: if real post-turbulence periods do not carry the scar/overshoot premium (the FLAT world),
  the rule ends slightly below the best constant (-0.12 pp in FLAT) and far below hold 1x; and the median exposure ~0.55
  means it captures only part of any calm-period premium.

## Final N
N = 169 parameter-set evaluations (E1 9, E3 8, E5 8, E6 2 upper-bound, E7 9, E8 12, E9 12, E10 10, S1 57, S2 24, S3 18),
each evaluated in both ON and OFF worlds (S3 in four worlds); the final rule was evaluated once on the fresh seeds.
All rows: work/variants.csv. Scripts: work/e1_varkelly.py ... work/e10_scan.py, work/s1_select.py, work/s2_select.py,
work/s3_select.py, work/final_eval.py, work/final_boot.py; logs work/s1_log.txt, s2_log.txt, s3_log.txt, final_log.txt.
