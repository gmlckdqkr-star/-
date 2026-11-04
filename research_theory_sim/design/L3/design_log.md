# Design log, lane TS1 / blind designer L3 (theory: Salience-Gated Narrative Contagion, SGNC)

All timestamps from `date -u +%Y-%m-%dT%H:%MZ`. Synthetic data only (my sim.py). Engine: common/exec_engine.py.

## 0. Timeline
- 2026-11-04T07:51Z read brief + engine; created folder.
- 2026-11-04T07:55Z READ_LOG.md; THEORY.md written; PRIORS_FROZEN 2026-11-04T07:56Z (before any simulation).
- 2026-11-04T07:58Z sim.py written and run (descriptive stats below).
- 2026-11-04T08:00Z baselines + oracle diagnostic on design seed 1; stage-1 grids launched 08:01Z.
- 2026-11-04T08:02Z found NaN CAGR on 3/2000 OFF paths (a story-switch jump < -1/3 in one day drives the 3x product
  negative inside the engine); design evaluation now counts such paths as -100% (wipe-out); grids restarted 08:03Z.
- 2026-11-04T08:09Z-08:18Z families E, G, H added after diagnostics (all on design seed 1). A grid 'H2' is defined in
  grid1.py but was never run (not counted).
- 2026-11-04T08:20Z stage 2 (seed 1); 08:23Z stage 3 (seed 2); 08:24Z rule.py written and checked; selection recorded.
- 2026-11-04T08:25Z fresh-seed evaluation (final_eval.py) run once; 08:28Z results recorded. No change to the rule after.

## 1. Synthetic worlds (descriptive, seed 1, P = 2000, 30 years; p10/median/p90 over paths)
| statistic | mechanism ON | mechanism OFF |
|---|---|---|
| ann. mean log price return | -0.027 / 0.037 / 0.099 | -0.028 / 0.037 / 0.099 |
| ann. vol of daily returns | 0.117 / 0.181 / 0.242 | 0.136 / 0.212 / 0.290 |
| daily kurtosis | 3.4 / 4.8 / 11.7 | 7.7 / 36.9 / 153 (story switches are jumps) |
| AC of 1-month returns | -0.10 / 0.022 / 0.16 | -0.14 / -0.036 / 0.05 |
| variance ratio VR(126) | 0.53 / 1.01 / 1.73 | 0.48 / 0.81 / 1.10 |
| variance ratio VR(252) | 0.49 / 1.04 / 1.88 | 0.42 / 0.76 / 1.18 |
| rf mean | 0.008 / 0.035 / 0.065 | same |
| valuation gap dm | 0.064 / 0.148 / 0.311 | same |
| story switches per year | 0.22 / 0.41 / 1.00 | same |
Note on "same overall scale": OFF has higher DAILY vol because each story switch is a one-day jump of dm, whereas ON
spreads the same move over the diffusion; the annual-horizon variance is the same (ON 0.181^2 x 1.04 = 0.034,
OFF 0.212^2 x 0.76 = 0.034). Liquidity noise (both worlds) gives VR < 1 at short horizons.
The prior implies a small median excess price drift (premium minus dividend yield ~ +2%/yr arithmetic), so leverage is
not attractive unconditionally in these worlds. This is a consequence of the frozen priors, not a target.

## 2. Baselines on design seed 1 (P = 2000), median after-tax 30y CAGR
| | ON | OFF |
|---|---|---|
| hold 1x | 0.0300 | 0.0304 |
| hold 2x | -0.0174 | -0.0279 |
| hold 3x | -0.0753 | -0.1186 |
| const level 0.5 / 1.0 / 1.5 | 0.0140 / 0.0091 / 0.0021 | 0.0125 / 0.0066 / -0.0016 |
| const level 2.0 / 2.5 / 3.0 | -0.0077 / -0.0257 / -0.0753 | -0.0124 / -0.0310 / -0.1186 |
Constant levels are built from the 3x product + cash (2rf + 2.45%/yr product cost, 2% deposit spread, interest tax),
so a constant level 1 lags same-basis hold 1x by about 2%/yr.
Diagnostic (uses the HIDDEN true story state, not a rule, counted as N = 4 diagnostics): level 3 in growth story /
0 in stagnation story, ON world: 0.119; 2/0: 0.100; 1.5/0: 0.086; 1/0: 0.071. So the theory leaves a large
timing opportunity if the story can be inferred from prices fast enough.

## 3. Selection procedure (fixed before the grids)
Objective on design seeds: J = 0.5 x median CAGR (ON) + 0.5 x median CAGR (OFF), same paths, default engine
(delay 2, cost 0.003). Reason: the theory may be false; the OFF world is the honest null. Stage 1: grids of four
theory-derived families on seed 1 (P = 2000 ON + 2000 OFF). Stage 2: refine around the best family on seed 1, then
confirm the top candidates on design seed 2 (P = 1000, ON + OFF) and pick the simplest within 0.3 pp of the best.
Final numbers: fresh seeds 10000 and 10001 (P = 1000 each), never used for selection.

Rule families (derived from the theory: an informed trader infers the hidden story from the price path and sizes by
Kelly, expected excess return / variance):
- A Kelly-trend: L = (a + b*m)/v; m = EWMA (half-life H) of daily excess log returns (annualised), v = EWMA of squared
  returns (half-life Hv, annualised).
- B bounded CUSUM / clamped log-odds (Wonham-type two-state filter): l_t = clip(l_{t-1} + z_t - mu0, -W, W),
  z = standardised excess return; L = Lmax*(l + W)/(2W).
- C drawdown from N-day high in vol units: L = Lhi if dd > -th else 0.
- D vol target tau/sigma when the H-EWMA excess drift > 0, else 0.

## 4. Variants evaluated (all on design seeds; each row = one rule configuration run ON and OFF)
Raw rows: runs_stage1_*.jsonl, runs_stage2_s1.jsonl, runs_stage3_s2.jsonl (this folder).

Stage 1, design seed 1 (P = 2000 ON + 2000 OFF), N = 434:
| family | grid | N | best J config | J | ON | OFF |
|---|---|---|---|---|---|---|
| A Kelly-trend (m/v) | a{0,.01,.02,.04} b{.25,.5,1,2} H{20,40,80,160} Hv{20,60} | 128 | a=0 b=.25 H=160 Hv=60 | 0.0121 | 0.0205 | 0.0037 |
| B bounded CUSUM | W{2,3,4,6,8} Lmax{1.5,2,2.5,3} Hv{20,60} mu0{0,.02} | 80 | W=8 Lmax=1.5 Hv=60 mu0=.02 | 0.0102 | 0.0241 | -0.0038 |
| C drawdown | N{60,120,250} th{.1,.2,.3,.5} Lhi{1.5,2,3} | 36 | N=250 th=.5 Lhi=1.5 | -0.0137 | 0.0058 | -0.0332 |
| D vol-target + trend sign | tau{.2,.3,.45,.6} H{20,40,80,160} Hv{20,60} | 32 | tau=.2 H=160 Hv=20 | -0.0015 | 0.0104 | -0.0133 |
| E story latch (Schmitt) | N{21,42,63,126,252} th{.5,1,1.5,2} Lup{1.5,3} Hv{60,250} | 80 | N=21 th=2 Lup=1.5 | 0.0062 | 0.0208 | -0.0084 |
| G Kelly on z_N (f=a+beta*z) | a{0,.005,.01,.02,.03} beta{.005..0.08} N{42,63,126,252} | 60 | a=.005 beta=.01 N=126 | 0.0183 | 0.0234 | 0.0133 |
| H G + learned premium | n0{3,10,30} beta{.01,.02,.03} kap{.5,1} N=126 | 18 | kap=.5 n0=30 beta=.02 | 0.0172 | 0.0228 | 0.0115 |
Pattern: short horizons and high levels lose (turnover, whipsaw from debate/liquidity noise, 3x-product carry). The
best configurations hold low average levels (0.2-0.7) and trade 1-6 times a year. No variant beats hold 1x
(0.030 ON / 0.030 OFF) on design data; the best ON value of any variant is 0.0243.

Diagnostics behind family G (design seed 1, ON, pooled over paths; forward 21-day excess log return from t+3):
z_63 > 1: +6 to +7%/yr; |z| <= 1: ~0; z < -1: -7 to -9%/yr. Slope peaks at N = 63-126 days. Conditioning on
salience (short/long vol ratio) did not change the slope much. Gains vs hold 1x rise with omega and dm (narrative
share and valuation gap), not with k (learning speed) in this prior.

Stage 2, design seed 1, N = 8: G with a single vol estimate (Hz = Hv) for the top-4 (a, beta, N), Hv {60, 250}.
Best: a=.005 beta=.01 N=126 Hv=Hz=60: J 0.01825 (vs 0.01833 with separate Hz = 250): simpler and equal.

Stage 3, design seed 2 (P = 1000 ON + 1000 OFF), N = 7 (confirmation of the top candidates):
| candidate | params | J | ON | OFF |
|---|---|---|---|---|
| G, Hz = Hv = 60 | a=.005 beta=.01 N=126 | 0.01792 | 0.02335 | 0.01249 |
| G, Hz = 250 | a=.005 beta=.01 N=126 Hv=60 | 0.01803 | 0.02331 | 0.01275 |
| G, Hz = Hv = 250 | a=.005 beta=.015 N=126 | 0.01715 | 0.02267 | 0.01162 |
| G, Hz = Hv = 60 | a=0 beta=.015 N=126 | 0.01704 | 0.02211 | 0.01196 |
| H | kap=.5 n0=30 beta=.02 N=126 | 0.01692 | 0.02296 | 0.01088 |
| B (best ON in stage 1) | W=8 Lmax=1.5 Hv=60 | 0.01082 | 0.02432 | -0.00268 |
| G (best ON in G) | a=.01 beta=.02 N=126 Hv=60 Hz=250 | 0.01578 | 0.02470 | 0.00685 |
Design-seed-2 baselines: hold 1x 0.0317 ON / 0.0326 OFF; cash (level 0) 0.0139 / 0.0139; level 0.5 0.0141 / 0.0119.

Total rule-variant evaluations N = 434 + 8 + 7 = 449 (plus 4 hidden-state oracle diagnostics, not rules).

## 5. Selection (pre-registered rule: simplest within 0.3 pp of the best J on seed 2)
Best seed-2 J = 0.01803. Candidates within 0.3 pp: all G/H rows. Simplest = G with one vol estimate (4 tunable
parameters a, beta, N, Hv). Chosen: a = 0.005, beta = 0.01, N = 126, Hv = 60 -> rule.py ("SGNC-K").
Decision recorded before any fresh-seed run (fresh-seed evaluation launched 2026-11-04T08:25Z).
How it follows from the theory: after a story turn the contagion drift lasts months, so the vol-scaled 6-month
excess return z is the informed trader's best simple statistic of "which story is spreading"; Kelly sizing f/sigma^2
with a small baseline premium (a = 0.5%/yr, the prior's premium net of the 3x-product carry) and a fractional slope
(beta = 1%/yr per unit z, about a third of the pooled predictive slope) to absorb estimation error, costs and tax.
Consequence: the rule is in cash most of the time and holds level 0.5-1.5 only after strong positive 6-month moves.
rule.py was checked (check_rule.py): P=500 x T=10000 in 0.7 s, causal, scale-invariant (1e-14), copes with NaN,
matches the design implementation after warm-up (max diff 1e-4 after column 1000; median CAGR 0.02301 vs 0.02309).

## 6. Final fresh-seed results (seeds 10000 + 10001, P = 2 x 1000 per world, never used for selection; 2026-11-04T08:28Z)
Median after-tax 30y CAGR (p10 in brackets), same paths for every row. Source: synth_results.json (final_eval.py).
| | mechanism ON | mechanism OFF |
|---|---|---|
| **rule SGNC-K** | **0.0226** (-0.0034) | **0.0132** (-0.0090) |
| hold 1x | 0.0321 | 0.0320 |
| hold 2x | -0.0151 | -0.0282 |
| hold 3x | -0.0767 | -0.1167 |
| const level 0 (cash) | 0.0135 | 0.0135 |
| const 0.5 / 1.0 / 1.5 | 0.0142 / 0.0094 / 0.0026 | 0.0126 / 0.0067 / -0.0005 |
| const 2.0 / 2.5 / 3.0 | -0.0072 / -0.0245 / -0.0767 | -0.0118 / -0.0302 / -0.1167 |
| best constant level | 0.5 -> 0.0142 | 0 -> 0.0135 |
| rule: P(MDD <= -80%) | 0.000 | 0.003 |
| rule: median MDD | -0.246 | -0.245 |
| rule: trades/yr, avg level (medians) | 1.4, 0.22 | 1.0, 0.16 |
| share of paths rule > hold 1x | 0.42 | 0.30 |
| share of paths rule > best constant | 0.66 | 0.32 |

Robustness (fresh seeds, median CAGR):
| | ON | OFF |
|---|---|---|
| delay 3 | 0.0228 | 0.0133 |
| delay 5 | 0.0227 | 0.0133 |
| cost 0.006 | 0.0213 | 0.0120 |
| prior narrowed (seed 10002): rule / hold 1x / best const | 0.0237 / 0.0342 / 0.0140 (L=0) | 0.0123 / 0.0343 / 0.0140 (L=0) |
| prior widened (seed 10003): rule / hold 1x / best const | 0.0242 / 0.0306 / 0.0177 (L=0.5) | 0.0149 / 0.0306 / 0.0149 (L=0.5) |
Mechanism-off loss vs the best constant-level rule: -0.0003 (rule 0.0132 vs cash 0.0135).

## 7. Honest verdict
- In its own synthetic world the rule does NOT beat same-basis hold 1x (0.0226 vs 0.0321 ON; 0.0132 vs 0.0320 OFF).
  It beats every constant level of the 3x-product/cash route when the mechanism is on (+0.8 pp over the best
  constant), and costs almost nothing when the mechanism is off (-0.03 pp vs cash). It is insensitive to delay 3/5.
- Why hold 1x wins: under the frozen priors the median excess price drift is small (premium minus dividend yield
  about +2%/yr arithmetic), and every level built from the 3x product + cash pays about 2 pp/yr more carry than the
  1x hold (2rf + 2.45% product cost, deposit spread 2%, interest tax). The story-timing edge that the theory creates
  is real (hidden-state oracle 1/0: 0.071 on design data) but only about 1 pp/yr of it can be captured causally,
  because each story turn is masked by fundamental noise, debate noise and liquidity noise.
- The selected rule is therefore mostly in cash (median average level 0.22) and goes to level 0.5-1.5 only after
  strong positive 6-month moves. Under the theory this is what a log-utility informed trader should do in these
  worlds; it is not a high-growth rule, and I do not expect it to approach the user's 30%/yr hope.
- Selection used J = 0.5 ON + 0.5 OFF (fixed before the grids). The best ON-only design variants (bounded CUSUM
  W=8, Lmax=1.5; or G with a=.01, beta=.02) reached 0.024-0.025 ON on design seeds, still below hold 1x, with worse
  OFF results (-0.003 to +0.007).
- Weak points: the level is f/sigma^2 with a fixed baseline premium a = 0.5%/yr taken from my prior; in a world with a
  much larger premium the rule under-invests (it does not learn the premium; the learning variant H was within the
  tie band but not simpler). The tie between near-cash variants is within sampling noise.
