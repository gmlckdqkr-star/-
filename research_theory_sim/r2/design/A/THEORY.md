# Risk-Meter Leverage Clock (RMLC) - lane TS2, round 2, designer A

Written 2026-11-04T10:51Z (timestamp from date -u), before any simulation.

## 1. One-line theory
Leveraged speculators size their positions on a slow, backward-looking risk meter (an exponentially weighted
realised-variance estimate, as margin and VaR models do); because the meter lags the price, their forced selling after
a shock and their re-leveraging after the shock are both paced by the meter, not by news, so the drift of the index is
predictably negative while the meter is climbing in a falling market and predictably positive while the meter is
decaying from a high level in a depressed market, while long calm spells quietly load the system with leverage.

## 2. Mechanism (who trades, under which constraints, why prices move)
Three kinds of traders and one fundamental news stream set the daily log return of the index.

1. Fundamental news. The log fundamental value f follows a driftless random walk with fat-tailed (Student-t) daily
   news of constant size. The equity premium and the risk-free rate are added on top of the demeaned price process.
2. Value-anchored traders (long-horizon, unlevered). They lean against the mispricing m = p - f. Their net demand moves
   the price toward value by a fraction a_v of the gap per day (slow: half-life of months to years).
3. Trend extrapolators (unlevered). Their demand follows an exponentially weighted average g of recent returns
   (half-life h_g); its price impact per day is c * g. This produces medium-term momentum and amplifies moves.
4. Leveraged speculators (the new part). They hold a fraction S of the market (in shares) with equity W (as a fraction
   of market capitalisation). Their broker / risk desk allows leverage
       lambda* = min(lambda_max, lambda_norm * sigma_ref / sqrt(M)),
   where M is an EWMA of squared daily returns with half-life h_M (the risk meter) and sigma_ref the market's normal
   daily volatility. Target holding S* = lambda* * W.
   - If S > S* (1 + b) they are over the limit and MUST sell a fraction a_dn of the excess every day (forced
     deleveraging, fast).
   - If S < S* they re-lever by a fraction a_up of the gap per day (voluntary, slow).
   - Their equity earns lambda times the excess return; outside capital drifts back toward a base share W_bar at rate
     zeta per day (new money arrives after good years, leaves after wipe-outs); W has a small floor.
   - Their trades move the price through an inelastic-market multiplier psi: a trade of dS (fraction of market cap)
     moves the log price by psi * dS.
Daily (demeaned) log return:
   x_t = df_t + a_v (f - p)_{t-1} + c g_{t-1} + psi dS_t,
then M, g, W, S update with x_t. The path is finally rescaled by one constant per path so its realised volatility
equals the drawn market volatility, and the drawn premium and the risk-free rate are added.

Why booms, crashes and recoveries follow:
- Calm: M decays -> lambda* rises -> speculators buy slowly -> prices drift up, trend traders add -> equity W of the
  speculators grows -> even more buying. Leverage and positions pile up exactly when measured risk is lowest.
- Trigger: a large (fat-tailed) news day, or simply value traders pulling an overpriced market down, lifts M. Positions
  are now over the limit and losses have cut W: forced selling, which moves the price, which lifts M and cuts W again.
  The spiral lasts as long as the forced selling itself produces returns larger than sqrt(M): days to weeks.
- Recovery: once the forced selling is done the market sits below value and below its pre-crash trend; value traders
  pull it up; as M decays the speculators (with refilled capital) start to re-lever, which adds buying. The recovery
  is paced by the decay of the meter (h_M) and by the slow refilling of capital (zeta).

## 3. Why it should exist in real markets
- Margin, haircut and VaR-based position limits are, in practice, functions of trailing realised volatility
  (EWMA variance, rolling-window VaR), so leverage capacity is mechanically procyclical and lagged.
- Leveraged and risk-targeting money (levered funds, dealers' balance sheets, volatility-targeting and risk-parity
  style allocators) is a material fraction of marginal demand, and aggregate demand for equities is inelastic, so their
  flows move prices by a multiple of their size.
- Value-anchored long-horizon investors exist but have limited, slow-moving capital, so mispricing decays slowly.
- Extrapolative expectations of retail and trend-following investors are well documented in surveys and flows.
The new piece is the clock: because the constraint is computed from past returns, the timing of forced flows is
partly predictable from past prices alone, which a trader seeing only closes can exploit.

## 4. What it predicts that a random walk does not
1. Volatility clustering with a leverage effect: big down moves raise subsequent volatility more than up moves.
2. Phase-dependent drift: while short-horizon volatility is rising above the slow meter and the price is falling,
   the following days to weeks have negative drift (cascade); when volatility has peaked and is falling while the
   price is still well below its prior high, the following months have above-normal drift (recovery premium).
3. Calm-before-the-storm: the deepest drawdowns tend to start from low-volatility uptrends (fragility = leverage built
   in calm); large drawdowns are fast, recoveries slower but with high average returns.
4. Negative skewness of monthly returns, positive autocorrelation of returns within stress episodes, medium-term
   momentum (trend traders) and slow long-horizon mean reversion (value traders).
5. A market with no leveraged speculators (or no lag in their meter) behaves close to a random walk with a constant
   premium: then only a constant exposure (estimated online) makes sense.

## 5. How it could be false
- Real risk limits may be forward-looking (implied volatility, stress scenarios) or discretionary, so the forced flows
  are not predictable from past closes; then the rule's state variables are noise.
- Leveraged money may be too small, or market depth too large (small psi), for its flows to dominate the drift.
- In real data, high and rising realised volatility may be followed by normal or even higher returns (risk
  compensation), and the post-peak recovery premium may not exist or may be front-run so it is gone after costs and a
  two-day execution delay.
- Crashes may be caused by fundamental news clusters (exogenous volatility), not by deleveraging; then volatility
  timing helps only through risk reduction, not through drift.
- Falsified if, in the real test, the rule's phase signals do not separate low-drift from high-drift periods, i.e.
  the rule is beaten by a constant exposure of similar average level.

## 6. Published anchors (unconditional level only)
All numbers are long-run averages remembered from the finance literature; none enters the timing structure.
| quantity | source (as remembered) | number remembered | conversion applied | used centre | confidence |
|---|---|---|---|---|---|
| total-return equity premium over bills (geometric) | Dimson, Marsh & Staunton, *Triumph of the Optimists* and the annual Global Investment Returns Yearbook (multi-country, 1900 onward) | world ~4.4 %/yr, US ~5.5 %/yr, broad-market central ~5 %/yr | headline is a PRICE index: subtract the long-run dividend yield (log approx.: TR log return = price log return + dividend yield) | | medium |
| long-run dividend yield of broad markets | same sources; Siegel, *Stocks for the Long Run* (US real total return ~6.5-7 %/yr of which real price gain ~2 %/yr) | ~4 %/yr over the 20th century, ~2 %/yr in recent decades | central 3.5 %/yr across unknown eras | | medium |
| price-index premium over bills (geometric) | derived: 5.0 % - 3.5 % | | | **1.5 %/yr** | low-medium; wide prior sd 2.0 %/yr; truncation [-3 %, +7 %] covers total-return markets (~4.5-5 %) inside 2 sd |
| volatility of broad equity markets | DMS yearbook (annual SD ~17 % world, ~20 % US); long-run realised daily-return volatility of large indices ~15-19 %/yr | | annualised daily log-return SD | **17 %/yr** | medium; lognormal sd 0.25, truncated [9 %, 40 %] (country funds can be 25-30 %) |
| short-term nominal rate | DMS / Siegel bill returns: nominal bills ~3.5-4.5 %/yr long-run, real ~0.5-1 %/yr | | | **~4 %/yr** average level; long up/down regimes 0-15 % | medium |
| depth and frequency of large drawdowns | multi-country long-run price-index histories (DMS; Siegel) | over a 30-year window the worst price-index drawdown is typically around -40 % to -55 %; a drawdown deeper than -50 % happens in roughly 30-50 % of 30-year windows; deeper than -75 % is rare (a few % of windows) | none (price basis) | median worst 30y drawdown ~ -45 %, P(<-50 %) ~ 0.4, P(<-75 %) ~ 0.05 | low; used only as a sanity check of the simulated worlds, not as a fitting target |

Remembered numbers are used only for these unconditional levels. I use the central value (no haircut); uncertainty is
expressed by the wide per-path prior of section 7 (each path is a different, unknown market, brief 2c).

## 7. Priors (drawn independently PER PATH)
Unconditional level (identical in the mechanism-ON and mechanism-OFF worlds for the same seed):
| parameter | prior | reason |
|---|---|---|
| mu_g: geometric price-index premium over rf, per year | Normal(0.015, 0.020) truncated to [-0.03, 0.07] | anchors above; wide for unknown market and for markets with reinvested distributions |
| sigma: annualised vol of daily log returns | LogNormal(log 0.17, 0.25) truncated [0.09, 0.40] | anchors above |
| rf: short rate, annual level | piecewise-linear regimes: segment length U[2, 15] y; type up (0.3) / down (0.3) / flat (0.4); trend change per segment U[1 %, 8 %]; reflected into [0, 15 %]; start level U[0.5 %, 9 %]; AR(1) wiggle sd 0.25 %; with prob 0.5 the path moves in monthly steps (21 days) | brief 2d (long trending regimes, stable periods); long-run mean ~4 % |
| y10 (percent) | 100 * (0.5 * rf + 0.5 * EWMA_2y(rf) + term spread U[0.5 %, 2.0 %] + AR noise sd 0.3 %) | provided for other rules; my theory does not use it |

Mechanism (ON world only):
| parameter | prior | reason |
|---|---|---|
| k0: fundamental share of vol before final rescale (sigma_f = k0 sigma) | U[0.6, 0.9] | most volatility is news; leverage flows add the rest |
| nu: Student-t df of daily news | U[4, 8] | fat-tailed news; extra kurtosis comes endogenously |
| a_v: value pull per day | log-U[1/1500, 1/200] | mispricing half-life ~0.5-4 years (slow valuation mean reversion) |
| c: trend-extrapolator feedback | U[0, 0.30] | from none to strong medium-term momentum, stable (< 1) |
| h_g: trend window half-life (days) | log-U[20, 120] | 1-6 month extrapolation horizons |
| W_bar: speculators' base equity share of market cap | log-U[0.01, 0.04] | small levered sector (hedge funds, margin accounts, dealers) |
| lambda_norm: allowed leverage at normal vol | U[1.5, 4.0] | typical gross leverage of levered equity money |
| lambda_max | 2 * lambda_norm | leverage cap in ultra-calm markets |
| h_M: risk-meter half-life (days) | log-U[10, 60] | EWMA risk models (~0.94 decay = 11 d) up to quarterly windows |
| b: tolerance before forced selling | U[0.0, 0.2] | margin buffer |
| a_dn: forced-selling speed per day | log-U[0.05, 0.5] | margin calls are met in days, VaR de-risking spread over weeks |
| a_up: re-leveraging speed per day | log-U[0.005, 0.05] | voluntary leverage rebuilds over 1-6 months |
| zeta: capital refill toward W_bar per day | log-U[1/1000, 1/250] | outside money returns over 1-4 years |
| W floor | 0.1 * W_bar | not all speculators fail |
| psi: price multiplier of speculator flow | log-U[2, 8] | inelastic-markets estimates (Gabaix & Koijen ~5) |
| daily return cap before rescale | [-0.25, +0.25] | numerical guard only |

Initial state: p = f, M = sigma_ref^2, W = W_bar, S = lambda_norm W_bar, g = 0; first 300 simulated days are the
warm-up columns (the engine does not trade them).

## 8. Mechanism-OFF world
Same seed -> same mu_g, sigma and rf path. Daily demeaned log return x_t = i.i.d. Student-t(nu) scaled, then rescaled
so the path's realised vol equals sigma (exactly as in the ON world); premium and rf added identically. No
speculators, no value or trend traders, no volatility clustering, no predictable drift: a random walk with the same
unconditional premium and volatility.

## 9. Planned trader logic (derived before any simulation; to be tested, not assumed)
An informed trader who knows the theory but not mu_g or sigma would
(i) hold a base exposure set by an online estimate of mu / sigma^2 (shrunk to the prior),
(ii) scale exposure down when short-horizon volatility is above its slow meter and the price is falling (cascade),
(iii) scale up when volatility has peaked and is falling while the price is far below its prior high (recovery),
(iv) trade rarely (costs, two-day delay, tax on realised gains).

## 10. Pre-freeze calibration amendments (made after the first simulator runs, BEFORE any rule was designed or evaluated)
The first implementation of the section-7 priors produced impossible worlds, and its drawdown frequency was far
above the anchors. Changes (each with its reason); no rule, signal or conditional return was looked at for these:
1. Explosion guard (worlds where speculators held 15-85x the whole market and the price rose >100 %/yr): the
   speculators' size is now drawn as their gross position share S0 = lambda_norm * W_bar ~ log-U[0.01, 0.04]
   (was W_bar ~ log-U[0.01, 0.04], i.e. positions up to 16 % of the market); lambda_norm ~ U[1.5, 3.5];
   lambda_max = 1.5 lambda_norm (was 2x); speculator equity is capped at 2 W_bar (profits above are paid out) and
   their holding at 30 % of the market; psi ~ log-U[2, 6] (was [2, 8]).
2. Value traders become more elastic for large mispricings (limits to arbitrage relax as the gap grows):
   pull = a_v * m * (1 + (m / 0.3)^2) instead of a_v * m.
3. Drawdown anchor (P(worst 30y DD <= -50 %) was 0.72 in ON vs anchor ~0.4): trend feedback c ~ U[0, 0.15]
   (was [0, 0.30]); value pull a_v ~ log-U[1/1000, 1/150] (half-life ~3 months to ~2.7 years; was [1/1500, 1/200]).
4. Rate anchor (the first generator averaged 5.5 %/yr vs the ~4 % anchor): start level U[0.5 %, 7 %], trend change
   per segment U[1 %, 6 %], reflection into [0, 12 %], final clip [0, 13 %].
Resulting descriptive statistics (seed 1, P = 2000, 30 traded years; descriptions, not targets):
| | mechanism ON | mechanism OFF |
|---|---|---|
| per-path log premium, median [p10, p90] | +1.4 % [-3.1 %, +6.2 %] | +1.4 % [-3.0 %, +6.3 %] |
| volatility | 17.0 % [12.4 %, 23.4 %] | 17.0 % [12.4 %, 23.4 %] |
| worst 30y drawdown, median [p10, p90] | -52 % [-75 %, -34 %] | -48 % [-72 %, -29 %] |
| P(worst DD <= -50 %) / P(<= -75 %) | 0.55 / 0.10 | 0.44 / 0.08 |
| same-basis 1x hold after-tax CAGR | 5.2 % [0.1 %, 11.6 %] | 5.2 % [0.1 %, 11.9 %] |
| mean rf | 4.0 % | 4.0 % |
| monthly skew (median) | -0.21 | 0.00 |
| daily kurtosis (median) | 5.6 | 5.5 |
The ON world sits a little above the drawdown anchor (by construction the mechanism adds crash risk); I accept that
rather than weakening the mechanism further.

## 11. Final frozen prior (what sim.py draws)
| parameter | frozen prior |
|---|---|
| mu_g | Normal(0.015, 0.020) truncated [-0.03, 0.07] |
| sigma | LogNormal(log 0.17, 0.25) truncated [0.09, 0.40] |
| nu | U[4, 8] |
| rf | regimes: length U[2, 15] y; up 0.3 / down 0.3 / flat 0.4; change U[1 %, 6 %]; start U[0.5 %, 7 %]; reflect [0, 12 %]; AR(1) sd 0.25 % (phi = 1 - 1/60); clip [0, 13 %]; monthly steps with prob 0.5 |
| y10 | 100 (0.5 rf + 0.5 EWMA_2y(rf) + U[0.5 %, 2 %] + AR(1) sd 0.3 %) |
| k0 | U[0.6, 0.9] |
| a_v | log-U[1/1000, 1/150]; pull = a_v m (1 + (m/0.3)^2) |
| c | U[0, 0.15] |
| h_g | log-U[20, 120] d |
| S0 = lambda_norm W_bar | log-U[0.01, 0.04] |
| lambda_norm | U[1.5, 3.5]; lambda_max = 1.5 lambda_norm |
| h_M | log-U[10, 60] d |
| b | U[0, 0.2] |
| a_dn | log-U[0.05, 0.5] /d |
| a_up | log-U[0.005, 0.05] /d |
| zeta | log-U[1/1000, 1/250] /d |
| psi | log-U[2, 6] |
| bounds | W in [0.1 W_bar, 2 W_bar]; S <= 0.3; pre-scale daily return clipped to [-0.25, 0.25] |
Mechanism-OFF: i.i.d. Student-t(nu) returns, realised vol rescaled to sigma, same mu_g and rf (section 8).

PRIORS_FROZEN 2026-11-04T10:57Z
