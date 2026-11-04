# design_log — lane TS2 round 2, designer B ("two-clock yardstick learning")
All timestamps from `date -u +%Y-%m-%dT%H:%MZ`. Selection on seeds 1-999 only; final numbers on fresh seeds >= 10000.
Every evaluated rule variant (including grid points) is appended to `work/variants.jsonl` with its running number N.

## Timeline
- 2026-11-04T10:46Z brief read; 10:47Z exec_engine.py read.
- 2026-11-04T10:53Z THEORY.md written; `PRIORS_FROZEN 2026-11-04T10:54Z`.
- 10:55-10:58Z sim.py written and run (seed 1, P=2000, ON 10.7 s, OFF 6.7 s).
- 10:59Z simulator bug fix (not a prior change): the OFF world demeaned its shock series over the window, which made the
  realised premium of every OFF path exactly equal to its true mu and created a spurious negative autocorrelation of
  multi-year returns (seen in an exploratory feature check on seed 3). Fixed to scale-only, as in the ON world. No
  rule had been evaluated before the fix.
- 11:00Z exploratory feature analysis (seeds 2, 3; not rule variants): in the ON world, forward excess returns are
  predicted by (i) the medium/long realised-vol ratio (+, about 1-year horizon: fear discount decays), (ii) the
  short/medium vol ratio (-, 1-3 month horizon: fear catching up with a new vol regime), (iii) the trailing 1-year
  excess return (-, hope reversal). In the OFF world all correlations are ~0 after the fix.
- 11:01-11:03Z ceiling checks (NOT candidate rules, they read simulator internals): seed 11, P=500.
  * hold 1x 5.9%, best constant level 0.5 -> 3.2% (ON). The instrument set has a structural handicap against hold 1x:
    at level L the portfolio earns c + L*(r - (2 rf + 2.45% + c)/3) with c = max(rf - 2%, 0)*0.846, i.e. about
    2.2%/yr less than hold 1x at the same exposure (cash spread + interest tax + product fee), before timing.
  * per-path constant level from the TRUE mu, sigma (k=0.5..1): 3.1-3.9%, below hold 1x.
  * timing oracle with the TRUE conditional drift and variance of the ON world (Kelly fractions 0.25-1): 5.2-5.6%
    vs hold 1x 5.9%. The true conditional premium swings widely (5-95%: about -50% .. +25% annualised) but has a
    memory of about one month (autocorrelation 0.46 at 21 days, 0.10 at 63 days), so after the 2-day delay, the 0.5
    level steps, costs and the cash handicap even the oracle does not beat hold 1x.
  * consequence: G-ON (beat hold 1x) is very likely infeasible in this theory's world for any causal rule. The design
    therefore also follows the brief's fallback criterion from the start (see "Selection procedure").

## Selection procedure (fixed 2026-11-04T11:05Z, before the main grids)
- Worlds: ON and OFF, selection seeds 11 and 12 (P=400 each) for coarse grids; promising variants re-checked on seeds
  21-24 (P=500 each). Fresh seeds 10000+ only for the final table.
- Score of a variant: dON = mean over seeds of (rule median CAGR - best constant level median CAGR) in the ON world,
  dOFF the same in the OFF world.
- Primary: if any variant beats hold 1x and the best constant in ON and loses <= 1 pp in OFF, take the best such.
  Otherwise (expected) take the variant with the largest min(dON, dOFF); a simpler variant (fewer active parameters)
  wins if it is within 0.10 pp of the best.

## Variants (N = running count in work/variants.jsonl)
| N | family | parameters | dON | dOFF | note |
|---|---|---|---|---|---|
| 1-3 | vol-scaled Kelly, slow vol (250 d), mu0 = 3% | k = 0.5, 1.0, 1.5 | (raw medians in variants.jsonl; seeds 11-12, P=500) | | k = 0.5 best; all far below hold 1x |
| 4-12 | vol-scaled Kelly | k in {0.35, 0.5, 0.75} x vol half-life in {20, 40, 160} | best +0.61 pp (k 0.5, h 20) | +0.36 pp | fast vol forecast better in ON |
| 13-16 | + fear gap bf*log(s_mid/s_fast) | bf in {0.05, 0.15} x s_mid in {80, 160} | best +0.81 pp (bf 0.05, 80) | +0.41 pp | bf 0.15 hurts OFF |
| 17-18 | + long fear discount bl*log(s_80/s_640) | bl in {0.05, 0.15} | +0.77 / +0.66 | +0.32 / -0.31 | |
| 19-20 | + hope reversal -bh*(m_1y - mu0) | bh in {0.1, 0.3} | +0.88 / +1.07 | +0.46 / +0.22 | |
| 21-38 | Kelly k*mu/s^2, with / without prior-shrunk premium learning (n0 = s^2/tau^2 years, tau = 2.5% from the prior) | k in {0.4, 0.5, 0.6} x vol half-life in {10, 20, 40} x learn in {0, 1} | best ON +0.73 (k 0.6, h 10) | | h 10 trades 7-11 per year; h 20 best balance; learning does not help (ON -0.2 pp, OFF ~0) |
| 39-54 | Kelly + fear gap + hope | k in {0.5, 0.6} x bf in {0, 0.03, 0.06} x bh in {0, 0.1, 0.2} (h 20, s_mid 80) | +0.86 .. +1.25 | +0.06 .. +0.59 | fear gap adds turnover, little value beyond the 20-day vol; best min: k 0.6, bh 0.1, bf 0 (+0.99 / +0.59) |
| 55-56 | hope against today's rf (yardstick form EWMA(252x) - 252 rf_t) | bh in {0.1, 0.2} | +0.96 / +1.16 | +0.63 / +0.41 | same as excess-return form within noise |
| 57-58 | hope with 3-year memory | bh in {0.1, 0.2} | +0.63 / +1.05 | +0.48 / +0.48 | 1-year memory better |
| 59-60 | target smoothing (EWMA 5 / 10 days) | | +0.56 / +0.47 | +0.63 / +0.54 | smoothing hurts ON |
| 61-65 | validation, seeds 21-24, P=500: C0 Kelly (k .6, h 20); C1 = C0 + hope 1y bh .1; C2 = yardstick form; C3 = yardstick bh .2; C4 = Kelly k .5 | | C0 +0.47, C1 +0.72, C2 +0.69, C3 +0.88, C4 +0.46 | C0 +0.76, C1 +0.67, C2 +0.64, C3 +0.37, C4 +0.64 | min: C1 0.67 > C2 0.64 > C4 0.46 ~ C0 0.47 > C3 0.37 |
| 66-68 | validation: C1 + learning; C0 + learning; C1 with k .5 | | +0.46 / +0.27 / +0.71 | +0.60 / +0.70 / +0.60 | learning dropped |
| 69-72 | validation: C1 neighbours k .7; h 15; h 25; bh .15 | | +0.75 / +0.79 / +0.56 / +0.78 | +0.60 / +0.54 / +0.71 / +0.54 | C1 is a local optimum of min(dON, dOFF) |

Validation seeds 21-24 (P=500 each): hold 1x minus best constant = +2.75 pp (ON), +2.41 pp (OFF); the best constant
level is 0.5 (1.0 on one seed). No variant comes within 1.5 pp of hold 1x in the ON world, so no variant passes G-ON on
selection seeds; the fallback criterion applies.
Robustness of C1 on the validation seeds (vs the base-engine best constant): delay 3 +0.68 / +0.58 pp, delay 5
+0.52 / +0.56 pp, cost 0.6% +0.46 / +0.34 pp (ON / OFF).

## Selection (2026-11-04T11:17Z, before any fresh seed was simulated)
Selected C1 = variant N 62: level = clip(0.6 * e / s^2, 0, 3), s = 20-day EWMA of 1.25*sqrt(252)*|log return|,
e = 0.03 - 0.1 * (m + s^2/2 - 0.03), m = EWMA (1-year half-life) of annualised daily log excess returns over rf.
Implemented in rule.py (pure numpy; equal to the design family up to start-up initialisation, max level difference
0.0017 on seed 21). Tunable parameters: k, h_vol, b_hope, h_hope (4 tuned) plus mu0 = 0.03 fixed at the published
anchor (not tuned) = 5 in PARAMS. Total variants evaluated N = 72 (plus 3 non-candidate ceiling checks).
rule.py sha256 at selection: 8051732d8fc4d28a211491f73f73978cccb21bd6aec0de265c96e3f25366cabb

## Simulator description (sim.py __main__, seed 1, P = 2000, after the OFF fix; descriptive, not targets)
| world | premium (arith) med [p10, p90] | vol med [p10, p90] | worst index drawdown med [p10, p90] | P(dd <= -50%) | P(dd <= -80%) | daily skew med | hold 1x CAGR med |
|---|---|---|---|---|---|---|---|
| ON  | 3.1% [-1.4, 7.9] | 16.8% [12.3, 23.0] | -47% [-73, -29] | 0.44 | 0.05 | -1.06 | 6.2% |
| OFF | 3.2% [-2.0, 8.7] | 16.9% [12.3, 23.3] | -48% [-76, -28] | 0.45 | 0.07 | +0.01 | 6.2% |
rf mean over the window: median 4.6% [0.5, 12.4]. Runtime 2000 x 7860: ON 11.6 s, OFF 6.9 s.
Robustness-only option added after selection had started (11:15Z): `simulate(..., prior_scale=w)` narrows (w < 1) or
widens (w > 1) every market prior around its centre from the same base draws; w = 1 reproduces the frozen prior
bit for bit (checked).

## Final fresh-seed table (final_eval.py, run 2026-11-04T11:19Z; seed 10001, P = 2000 per world)
Median after-tax 30-year CAGR (p10, P(MDD <= -80%) where shown).
| world | rule | rule p10 | rule P(dd80) | rule avg level | trades/yr | hold 1x | hold 2x | hold 3x | const 0.5 | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 | best const |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ON  | 4.10% | -2.76% | 0.114 | 1.11 | 4.1 | 6.05% | 2.58% | -1.56% | 3.34% | 3.35% | 2.98% | 2.32% | 1.32% | -1.56% | 3.35% (1.0) |
| OFF | 4.35% | -2.53% | 0.115 | 1.08 | 4.2 | 6.04% | 2.74% | -1.33% | 3.61% | 3.47% | 3.09% | 2.51% | 1.50% | -1.33% | 3.61% (0.5) |
hold 1x P(dd80): ON 0.053, OFF 0.070. Reference row (not a candidate, b_hope = 0, Kelly part alone): ON 3.79%, OFF 4.12%.

## Design gates (fresh seeds, P = 2000)
| gate | requirement | rule | comparator(s) | result |
|---|---|---|---|---|
| G-ON | rule > hold 1x and rule > best constant (ON) | 4.10% | hold 1x 6.05%, best constant 3.35% | **FAIL** (beats the best constant by +0.75 pp, loses 1.95 pp to hold 1x) |
| G-OFF | rule >= best constant - 1.0 pp (OFF) | 4.35% | best constant 3.61% | **PASS** (+0.74 pp) |

## Robustness (fresh seeds)
| check | ON | OFF |
|---|---|---|
| base (delay 2, cost 0.3%) | 4.10% | 4.35% |
| delay 3 | 4.09% | 4.32% |
| delay 5 | 3.96% | 4.31% |
| cost 0.6% | 3.84% | 4.06% |
| prior narrowed x0.5 (seed 10002, P = 1000): rule / best const / hold 1x | 3.62% / 2.72% / 5.87% | 4.21% / 3.13% / 6.15% |
| prior widened x1.5 (seed 10003, P = 1000): rule / best const / hold 1x | 3.99% / 3.60% / 6.10% | 4.52% / 4.13% / 6.40% |
The rule beats the best constant level in every cell (by +0.4 to +1.1 pp) and loses to hold 1x in every cell
(by 1.6 to 2.3 pp). It is insensitive to delay (vol forecast and hope have memories of weeks and a year).

## Conclusion (honest)
- The mechanism produces large conditional premium swings in the ON world (true conditional premium roughly -50% to
  +25% annualised, 5-95%), but they live about a month. After the 2-day delay, 0.5 level steps, 0.3% costs, taxes and
  the structural handicap of the 3x-product-plus-cash instrument set (about 2.2%/yr below hold 1x at equal exposure),
  neither the shipped rule nor a timing oracle with the true conditional drift beats hold 1x. No variant passed G-ON.
- Following the brief's fallback, the shipped rule is the simplest theory-implied rule that loses least against the
  best constant level in both worlds: a fractional Kelly bet (k = 0.6) on the anchored 3% premium, scaled by a fast
  (20-day) volatility estimate (risk learned fast), tilted against the market's slowly learned hope (1-year
  experienced excess return, coefficient 0.1). It beats the best constant level by about 0.75 pp in both worlds, mostly
  through volatility scaling (Kelly part alone: +0.44 pp ON, +0.51 pp OFF); the hope tilt adds about 0.3 pp ON and
  0.2 pp OFF on fresh seeds (0.25 / -0.1 pp on selection seeds).
- The mechanism added no tradeable edge large enough to beat hold 1x after costs. In the real test, expect the rule to
  sit near the best constant level plus a volatility-timing gain, and below 1x buy-and-hold whenever the market's
  premium is near the anchor; it carries more deep-drawdown risk than hold 1x (P(dd80) 0.11 vs 0.05-0.07) because it
  can reach level 3 in calm periods.
- Things that could make it worse on real data: if index returns show momentum over 1 year rather than reversal, the
  hope tilt costs (it is small); if volatility spikes come with higher, not lower, subsequent returns faster than 20
  days, the fast vol scaling sells too late into recoveries.
