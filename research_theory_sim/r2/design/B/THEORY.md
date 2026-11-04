# THEORY — "Two-clock yardstick learning" (TCYL)
Lane TS2, round 2, blind designer B. Written 2026-11-04T10:53Z, before any simulation or rule design.
Family: learning about the premium (investors do not know the long-run expected return and risk and learn them from
experience).

## 1. One-line statement
Investors learn the two numbers that set their demand for equities on two very different clocks: RISK from a short,
fast-fading memory of experienced absolute moves ("fear learns fast"), and the PREMIUM from a long, slowly fading memory
of experienced returns that they judge against TODAY's cash rate ("hope learns slowly, against a moving yardstick").
Because the price is set by these learned beliefs and the beliefs are learned from the price itself, both clocks feed
back into returns: the fast clock makes falls bigger than rises and leaves a fear discount that decays over weeks to
months; the slow clock inflates valuations after long good runs, deflates them after long bad runs or while cash rates
climb, and reverses over years.

## 2. Mechanism (who trades, under which constraints, why prices move)
- Fundamentals. The index has a log fundamental value f_t (the price a fully informed investor with known parameters
  would pay). Its daily change is drift + shock: df_t = (rf_t + mu - sigma^2/2)/252 + c * vol_t * eps_t, with eps_t
  fat-tailed (Student-t, unit variance) and vol_t an exogenous, persistent volatility process (news intensity). mu is the
  market's TRUE long-run arithmetic premium of the price index over cash, sigma its true long-run volatility. Neither mu
  nor sigma is known to anybody in the market, and both differ between markets.
- Investors. A population whose wealth-weighted demand for the index sets its valuation. Each investor neither knows mu
  nor sigma. As documented for experience effects, they form beliefs from returns they have lived through, with fading
  memory (older experience gets less weight; the investor base also turns over across generations):
  * Perceived premium ("hope"): m_t = exponentially weighted average of experienced annualised index returns with a LONG
    half-life h_m (years). The attractiveness of equities is judged by the gap m_t - rho * rf_t, i.e. against the cash
    rate investors see today (rho = how much of the yardstick is the current cash rate).
  * Perceived risk ("fear"): s_t = exponentially weighted average of experienced absolute daily moves (scaled to an
    annual vol) with a SHORT half-life h_s (days to months). Investors treat this recent risk as the risk they will bear
    from now on, i.e. they do not separate transient from persistent risk.
- Constraint / price formation. The supply of index exposure is fixed and the market is inelastic: a shift in the
  wealth-weighted demand moves the valuation, not the quantity. Linearising a mean-variance demand
  (m - rho*rf)/(gamma * s^2) around its long-run level gives the log valuation
      v_t = a * (m_t - rho*rf_t - pi_bar) - b * (s_t - s_bar),        log price p_t = f_t + v_t,
  where a (years) is the price sensitivity to the perceived premium, b the sensitivity to perceived risk, pi_bar and
  s_bar the long-run belief levels. Beliefs at close t already include day t's return, so the close is a fixed point of
  "price -> experienced return -> belief -> price". Writing x_t for the day's log return, the fixed point is
      x_t * (1 - A) + B * |x_t| = df_t + K_t ,
      A = a * kappa_m * 252           (slow "hope" feedback, kappa_m = daily memory gain, A < 1)
      B = b * kappa_s * c * sqrt(252) (fast "fear" feedback on absolute moves)
      K_t = b*kappa_s*s_{t-1} - a*kappa_m*m_{t-1} - a*rho*(rf_t - rf_{t-1})*252 (predictable, state-dependent part)
  so x_t = (df_t + K_t)/(1 - A + B) on up days and (df_t + K_t)/(1 - A - B) on down days.
- Why prices move the way they do.
  * A fall raises fear immediately, which lowers the valuation on the same day: falls are amplified by 1/(1-A-B), rises
    by only 1/(1-A+B) (dampened when B > A). The fear discount then decays at the fear clock while calm days arrive,
    which is a predictable upward drift (the b*kappa_s*s term of K): prices recover as fear fades.
  * Good runs raise hope; with a > 0 this raises the valuation and therefore the experienced return, which raises hope
    further (self-referential amplification 1/(1-A)). Because hope is a fading average, it eventually catches up with
    the true return and the valuation reverts: the -a*kappa_m*m term of K makes the expected return LOW when hope is
    HIGH (after long good runs) and HIGH after long bad runs.
  * Cash rates are part of the yardstick. A steady rise in rf lowers m - rho*rf until experienced returns catch up
    (experience lags by about the memory length), so valuations compress during the rise and re-expand when rates
    stabilise or fall. Long rate trends therefore produce long, slow valuation swings that a random walk does not have.
  * True volatility is persistent (vol_t) and investors learn it with a clock h_s that need not match its true
    persistence: if fear is faster than true volatility persistence, fear over-reacts to noise clusters and the gap
    (fear minus true current volatility) predicts recovery; if fear is slower, the market under-reacts at the start of
    a new high-volatility regime and the decline continues while fear catches up.

## 3. Why it should exist in real markets (economic argument)
- Means are statistically hard to learn and variances are easy (a mean needs decades, a variance needs weeks of daily
  data). People who learn from their own experience therefore end up with a slow, sticky belief about the premium and a
  fast, jumpy belief about risk; nobody in the market knows the true parameters, so there is no "rational anchor" that
  arbitrage can lean on with confidence.
- Experience effects (beliefs and risk taking shaped by lifetime returns, with fading weights) and extrapolative
  expectations are documented in surveys and portfolio data; fading memory is also what generational turnover of the
  investor base produces mechanically.
- Benchmarking equities against the current cash rate (a visible, salient alternative) with an experience-based estimate
  of equity returns is a natural heuristic; it makes the perceived premium move with rates long before experienced
  returns adjust.
- Demand for broad index exposure is inelastic at the aggregate level (index funds, mandates, few long-horizon
  arbitrageurs with enough capital), so belief shifts move prices rather than quantities.

## 4. What it predicts that a random walk does not
P1. Asymmetry: down days larger than up days (negative skewness of daily returns) and volatility rising after declines
    (leverage effect), generated endogenously by fear feedback.
P2. Fear-gap recovery: when recent realised volatility (the market's fear) is high relative to a slower estimate of the
    true current volatility, subsequent returns over the next weeks to months are above normal (the fear discount
    decays). In parameter regions where fear is slower than true volatility persistence, the sign flips at the onset of
    volatility regimes (continuation).
P3. Slow reversal: trailing multi-year excess returns (relative to cash) predict LOWER returns over the next years.
P4. Rate yardstick: rate rises coincide with valuation compression beyond fundamentals, steady rate trends with slow
    valuation drifts, which reverse when the trend ends.
P5. Excess volatility: price volatility larger than fundamental volatility (not observable from prices alone).
In expectation the premium is constant; it is the conditional expected return that moves, with two clocks.

## 5. How it could be false
- Investors (or arbitrageurs) learn risk with the right persistence and separate transient from persistent volatility:
  then the fear term predicts nothing (P2 fails), the asymmetry is only exogenous.
- Prices do not respond to experience-based premium beliefs (aggregate demand elastic, or beliefs anchored on a fixed
  prior): P3 and P4 fail.
- Feedback coefficients small: the market is indistinguishable from the mechanism-off world (exogenous volatility
  clustering plus fat tails around a constant premium).
- Real rate shocks that move fundamentals (not modelled here) could dominate the rate-yardstick channel.

## 6. Mechanism-off world
Same per-path true premium mu, same per-path unconditional volatility sigma, same exogenous volatility process vol_t,
same fat-tailed shock sequence eps_t, same rf and y10 paths. The learned beliefs no longer move the price (a = b = 0, so
A = B = 0, v_t = 0): returns are the fundamental returns. In both worlds the shock scale c is set per path so that the
realised daily volatility of the index equals sigma (the ON world is solved twice: once to measure the feedback
amplification, once with the corrected scale), and the log drift is the same, so the unconditional premium and
volatility match path by path.

## 7. Published anchors (section 2b of the brief)
All numbers are remembered central values; no data were looked up.
| source | remembered number | conversion | certainty |
|---|---|---|---|
| Dimson, Marsh & Staunton, "Triumph of the Optimists" (2002) and the annual Global Investment Returns Yearbooks (1900 onwards, ~20+ countries) | world equity premium over bills, total return: about 4.5%/yr geometric, about 6% arithmetic; US about 5.5% geometric, about 7% arithmetic; std of annual real equity returns ~17% world, ~20% US, 20-30% for many single countries | total -> price index: subtract the long-run dividend yield (below) | moderate (+-1 pp on the premium) |
| Jorda, Knoll, Kuvshinov, Schularick & Taylor (2019, QJE), "The Rate of Return on Everything, 1870-2015", 16 advanced economies | real equity total return about 6.5-7%/yr, real bill return about 1%; dividend income about 4%/yr of it, real capital gain about 2.5%/yr | premium total ~5.5-6% arithmetic; price-only part ~ total minus ~4% income | moderate |
| Shiller's long-run US series (from 1871) | average dividend yield ~4%+ over the long run, ~2% in recent decades; real price growth ~2%/yr | dividend yield used for the conversion: 3.5% (between the 20th-century ~4% and the recent ~2%) | moderate |
| Mehra & Prescott (1985), "The equity premium: a puzzle" | US equity premium about 6% (arithmetic, total return over short bills) | consistent with the above | high on the order of magnitude |
| long-run national return series (same sources), drawdowns | a broad national index typically suffers at least one 40-60% peak-to-trough decline in a 30-year window; declines beyond 80% are rare (a handful of national cases per century) | used only as a sanity range for the simulated worst drawdown of 1x hold, not as a target and not for timing | low |

Centre used for the simulator (unconditional level only):
- Price-index arithmetic premium over cash: total-return premium centre 6.5% (between the world ~6% and the US ~7% since
  the headline is a large broad market) minus dividend yield 3.5% = **3.0%/yr**. Total-return markets (the country funds
  with reinvested distributions) sit near 6-6.5%; the wide prior covers them.
- Volatility of daily returns (annualised): **17%** centre (world-ish broad index), wide lognormal prior covering
  10%-30% (single-country funds are more volatile).
- Drawdown frequency: not imposed; reported as a check.

## 8. Priors (every simulator parameter, drawn independently PER PATH; each path is a different market)
Unconditional level (both worlds):
| parameter | prior | reason |
|---|---|---|
| mu (true arithmetic premium of the price index over cash, annual) | Normal(0.030, 0.025) truncated to [-0.03, 0.10] | anchor 3.0% (section 7); sd 2.5 pp covers total-return markets (~6%) and poor markets (~0 to -2%) |
| sigma (unconditional annualised vol of daily returns) | lognormal, median 0.17, log-sd 0.25, truncated [0.08, 0.40] | anchor 17%; covers calm broad indices and volatile single-country funds |
| nu (Student-t tail index of fundamental shocks) | Uniform[4, 12] | fat tails of news; feedback adds more tail in the ON world |
| h_v (half-life of the exogenous log-volatility process) | log-uniform[20, 500] trading days | news intensity persists from weeks to years; wide because unknown |
| s_v (stationary sd of log volatility) | Uniform[0.15, 0.55] | from mild to strong volatility clustering |
| volatility shock innovations | Gaussian, independent of return shocks | no built-in leverage effect; in the ON world it arises from fear feedback |

Mechanism (ON world only; OFF sets A = B = 0):
| parameter | prior | reason |
|---|---|---|
| A (slow hope feedback = a * kappa_m * 252) | Uniform[0.00, 0.45] | from no effect to strong self-referential amplification (vol x 1.8); must stay < 1 for stability |
| h_m (half-life of experience memory) | log-uniform[1.5, 12] years | experience effects span from a business cycle to a large part of an investor lifetime |
| B (fast fear feedback = b * kappa_s * 1.25 * sqrt(252)) | Uniform[0.00, 0.40] | from none to falls amplified by up to ~1/(1-A-B) |
| h_s (half-life of fear memory) | log-uniform[10, 150] trading days | fear of a crash fades over weeks to about half a year |
| rho (weight of today's cash rate in the yardstick) | Uniform[0.3, 1.0] | investors compare with cash, partly with other anchors |
| stability cap | if A + B > 0.70, both are scaled down proportionally to A + B = 0.70 | prevents explosive feedback |
| initial beliefs | m_0, s_0 at their long-run levels plus noise; a 500-day burn-in precedes column 0 | removes start-up transients |

Rates (both worlds, exogenous; section 2d):
| parameter | prior | reason |
|---|---|---|
| starting short rate | Uniform[0.00, 0.08] annual | low to high rate eras |
| regime durations | Uniform[3, 15] years, back to back | long regimes up to more than a decade |
| regime type | up / down / flat with probability 1/3 each | steady trends and stable periods |
| trend slope | Uniform[0.2, 1.2] pp per year (sign by type) | slow steady drifts of the policy rate |
| rate noise | AR(1) deviation, sd 0.3 pp, half-life ~6 months; jumps of +-1 pp at rate 0.15 per year | cycles and policy surprises |
| bounds | rate kept in [0, 0.16]; at 0 it stays at 0 while the trend points down (zero lower bound stretches) | |
| monthly steps | with probability 0.4 a path's rate moves only in 21-day steps | early-decade data |
| y10 | 100 * (0.5*rf + 0.5*(2-year average of rf) + term premium) + slow noise, term premium Uniform[0.5, 2.5] pp, floor 0.2% | provided for other lanes' rules; not used by this theory's mechanism |

Fundamental drift: (rf_t + mu - sigma^2/2)/252 per day (so the arithmetic premium over cash is mu in both worlds).

PRIORS_FROZEN 2026-11-04T10:54Z
