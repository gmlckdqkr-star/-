# THEORY — "Margin-Ratchet Leverage Cycle" (MRLC)

Lane TS1, blind designer L1. Family: crowd and leverage. Written before any simulation (2026-11-04T07:23Z, see the
PRIORS_FROZEN line at the end).

## 1. One-line statement
The index carries a *leverage premium* held up by trend-extrapolating leveraged speculators whose borrowing limit is set
by lenders with a **ratchet memory of risk** (it jumps up instantly when realised volatility rises and forgets only over
years); because value holders are inelastic, the premium is built slowly in calm times, destroyed in days in a
margin-call cascade, and rebuilt slowly in a recovery during which the ratchet keeps speculators unlevered, so that
recoveries are both above-average in drift and unusually safe.

## 2. Who trades and under which constraints
1. **Value-anchored holders** (long-only institutions, households) own most of the float. They anchor on a
   fundamental value F (log f) that grows with nominal earnings and is discounted with the short rate. They are
   *inelastic*: to absorb a net flow of q (as a fraction of market capitalisation) from the other classes they need the
   price to move by beta*q in log terms, and the deviation persists as long as the other classes keep the position.
2. **Leveraged speculators** (levered funds, margin accounts) hold a position equal to leverage l times their equity
   share w of the market. Their *desired* leverage is fractional Kelly on an extrapolative belief:
   l* = c * (m0 + kappa * trend - R - s_b) / sigma_p^2, where trend is an EMA of past index returns, R the short rate,
   s_b their borrowing spread and sigma_p their own short-memory volatility estimate.
   Their *allowed* leverage is 1/H, with the lender haircut H = clip(h_k * M, H_min, 1) and **M the lender's risk
   memory, a ratchet**: M_t = max(sigma_lender_now, M_{t-1} * decay), i.e. it follows realised volatility upward at once
   (risk committees react to losses immediately) but decays with a half-life of years (stressed-risk rules, institutional
   memory, careers of the people who lived through the last purge).
   When mechanical leverage after a loss exceeds the limit they must sell (margin calls are met over a few days, a fraction
   phi_f of the excess per day). Their equity share relaxes toward a long-run share w_bar over years (new funds, inflows
   that follow performance) and is wiped out when a cascade eats their equity.
3. **Unlevered trend extrapolators**: small flows that follow a normalised trend (mild momentum).
4. **Sentiment noise**: mean-reverting shocks to demand.

Price: log p = f + beta * (Q_S + Q_X) + u, where Q_S = l*w and Q_X are the cap shares held by speculators and
extrapolators (in excess of an irrelevant constant) and u is sentiment. Orders decided at a close move the next day's
price (one-day execution lag), so cascades unfold over several days.

## 3. Why prices move the way they do (the cycle)
- **Build-up**: in calm markets sigma_p is low (desired leverage rises), the ratchet memory M decays (allowed leverage
  rises) and speculator capital accumulates. Q_S = l*w grows, value holders sell to them, and the index drifts above
  fundamental drift by beta * dQ_S/dt. The premium beta*Q_S at risk grows with the calm duration.
- **Cascade**: any shock (news, a rate rise that kills the carry, sentiment) makes losses that raise mechanical leverage,
  while the shock's volatility raises the haircut through the ratchet at once. Forced selling moves the price, which
  creates more losses. The local gain of this loop is about phi_f * beta * l * (l - 1) * w; when it exceeds 1 the
  cascade runs until the speculators are wiped out. The crash size is set by the accumulated premium, not by the trigger.
- **Recovery**: after the purge the ratchet keeps allowed leverage low for years and speculator capital is small.
  Capital returns and the memory decays, so Q_S and the premium are rebuilt: the index drifts above its fundamental
  drift, and since nobody is levered yet there is little fuel for a new cascade.
- **Rates**: speculators' carry is m0 - R - s_b. A higher short rate lowers desired leverage (selling, lower premium);
  fundamental value is also discounted with R (duration D) while nominal growth partly follows R (Fisher channel).

## 4. Why it should exist in real markets (economic argument)
Margin and haircut setting is procyclical because it is based on measured risk, and measured risk used by lenders has
an asymmetric memory: losses are recognised at once, while relaxation requires a long clean record. Leveraged demand is
extrapolative and vol-scaled because funds are judged on recent performance and run risk budgets on recent volatility.
The marginal buyer of last resort (value holders) is slow and inelastic because mandates are sticky. Each ingredient is
standard on its own; the claim here is their interaction with **two slow clocks** (lender memory decay and speculator
capital rebuild) and one fast clock (margin calls), which produces a specific, observable state variable.

## 5. What it predicts that a random walk does not
1. Volatility clustering with asymmetry, negative skew, and drawdowns that are fast (days to weeks) and *multi-day*
   (positive short-horizon return autocorrelation while volatility is high and prices fall).
2. A **ratchet gap** state: when the lender memory (proxied from price alone by a slowly decaying running max of
   realised volatility) is well above current realised volatility, the market is in a post-purge recovery: forward
   drift is above average and crash hazard is low. When the memory has decayed down to a low current volatility after a
   long calm, the premium at risk and the crash hazard are high.
3. Forward returns are higher after large drawdowns that came with a volatility spike (purge done) than after small
   ones, over horizons of months to a few years.
4. Rising short rates (relative to their recent past) lower subsequent returns through speculator de-leveraging.
A random walk (with any constant vol) predicts none of these: future returns are independent of past realised
volatility, drawdown depth and rate changes.

## 6. How it could be false
- Lender limits may be through-the-cycle or forget quickly (tau_L short): then the ratchet gap carries no information.
- The leveraged class may be tiny relative to the market (footprint beta*w_bar near 0): the index is close to a random
  walk with fundamental volatility; only constant exposure remains.
- Crashes may be mostly driven by persistent fundamental shocks (no rebound drift): prediction 3 fails.
- Volatility may cluster for exogenous reasons unrelated to leverage (vol spikes without later rebuild drift).
In synthetic data the theory is falsifiable by sorting forward returns on the ratchet gap / drawdown state.

## 7. Priors (every simulator parameter, drawn independently PER PATH; U = uniform)
Time step one trading day (252 per year). Annual units unless noted.

| parameter | prior | reason |
|---|---|---|
| Rbar, mean short rate | U(0.00, 0.07) | nominal short rates are non-negative-ish and of order a few %; wide |
| R half-life of mean reversion | U(2, 12) y | policy rates move in slow cycles |
| R volatility | U(0.004, 0.020) per sqrt(y) | rate shocks of fractions of a percent per year; R floored at 0, capped at 0.20 |
| monthly-step rates | Bernoulli(0.5) | brief: early decades may move in monthly steps (R held for 21 days) |
| g0, real part of fundamental log drift | U(-0.01, 0.06) | price index (no dividends): real earnings growth net of dilution, could be ~0 |
| chi, pass-through of R into nominal growth | U(0, 1) | Fisher: nominal growth and nominal rates share inflation; g_t = g0 + chi*R_t |
| D, duration of fundamental value to R | U(0, 6) | value falls when the discount rate jumps; equities are long-duration but cash-flows reprice |
| sigma_f, fundamental news vol | U(0.07, 0.18) | news alone must leave room for endogenous vol (background: equity vol order 10-40%) |
| nu, Student-t dof of news | U(3.5, 30) | news can be fat-tailed or near-normal |
| beta, inverse elasticity of value holders | U(1.5, 6) | inelastic-market argument: absorbing 1% of cap needs a several-% price move |
| Phi = beta*w_bar, speculator footprint | U(0.01, 0.10) | log premium per unit of speculator leverage at normal capital; a class of a few % of cap |
| tau_w, speculator capital rebuild half-life | U(0.5, 4) y | fund launches / performance flows take years |
| c, Kelly fraction of speculators | U(0.25, 1.0) | professional risk taking is fractional Kelly |
| m0, speculators' nominal return anchor | U(0.04, 0.10) | believed long-run equity return; not indexed to R (so R moves the carry) |
| kappa, weight on trend in beliefs | U(0, 1.0) | from no extrapolation to full extrapolation of recent trend |
| tau_x, speculators' trend EMA span | U(40, 250) d | trend horizons from two months to one year |
| tau_v, speculators' vol EWMA span | U(10, 60) d | risk budgets use short windows |
| s_b, borrow spread | U(0.005, 0.03) | broker margin spreads |
| phi_v, voluntary leverage adjustment | U(0.02, 0.20) per day | discretionary repositioning takes days to weeks |
| phi_f, forced execution per day | U(0.2, 1.0) per day | margin calls are met within one to a few days |
| h_k, haircut per unit lender vol | U(1.5, 4.0) | haircut covers a multi-sigma annual move |
| H_min, haircut floor | U(0.08, 0.35) | maximum allowed leverage between about 3x and 12x |
| tau_L, lender memory half-life | U(0.5, 5) y | the ratchet: risk memory fades over one to several years |
| tau_lv, lender realised-vol window | U(5, 30) d | lenders' measured volatility is short-window |
| b_X, extrapolator feedback gain | U(0, 0.15) | next-day echo of a return through unlevered trend flows; < 0.15 keeps it stable |
| tau_X, extrapolator EMA span | U(20, 200) d | |
| sigma_u, sentiment innovation vol | U(0.02, 0.10) | demand noise beyond news |
| hl_u, sentiment half-life | U(0.1, 2.0) y | |

Structural constants (not tuned, not priors): speculator wipe-out floor w_floor = 0.02*w_bar (bankrupt class restarts
with leverage 1 at the floor); absolute leverage cap 15; speculators' perceived vol floored at 3%; daily log return
clipped to +-0.25 as a numerical guard; extrapolator flow Q_X = alpha_X*tanh(z) with alpha_X set from b_X so that the
next-day echo gain at z = 0 equals b_X.

**Background knowledge used**: equity index volatility is of order 10-40% a year; short rates are of order 0-10% and
change slowly; nominal growth and nominal rates share inflation (Fisher); margin requirements depend on measured risk;
leveraged funds use recent volatility for sizing; the "inelastic markets" idea that flows move prices by a multiple of
their size. I did not use any specific crash, year, decade, named index, or remembered average return / volatility.

## 8. Mechanism-off world
Same seed, same per-path parameter draw and the same short-rate path. The index return becomes i.i.d. Student-t(nu)
daily log returns whose mean and standard deviation equal that path's own mechanism-ON realised mean and standard
deviation of daily log returns (computed after warm-up). Same overall scale (drift and volatility), no speculators,
no ratchet, no extrapolators, no sentiment persistence, no rate-return link: a random walk.

PRIORS_FROZEN 2026-11-04T07:23Z

## Amendment A1 (implementation guard, made before any rule design; priors unchanged) — 2026-11-04T07:28Z
The first run of sim.py produced non-finite paths (2 of 500): speculator equity measured as a share of market
capitalisation grew without bound (leveraged gains in long booms, and cash held while the index collapsed), so that
their later re-levering moved prices by many log units. Two structural constants were added, no prior range changed:
(1) speculator equity share is capped at WCAP = 3 x w_bar (fund capacity: equity above it is paid out to investors);
(2) a lender closes out the speculator position when mechanical leverage exceeds the absolute cap 15 (counted as a
wipe-out). After A1 all paths are finite. Descriptive statistics are printed by sim.py and copied to design_log.md;
they were looked at only for sanity (finite, no runaway), not tuned.
