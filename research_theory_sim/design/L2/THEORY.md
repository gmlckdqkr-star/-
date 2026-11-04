# THEORY — "Dealer Ledger" theory of the equity price of risk (lane TS1, designer L2)

Written 2026-11-04T07:24Z, before any simulation and before any rule design.

## 1. One-line statement
The equity index is priced by a leveraged intermediary sector whose risk-bearing capacity is a hidden **capital ledger**.
The ledger integrates three funding flows — (i) leveraged innovations on its equity book, (ii) the maturity-transformation
carry it earns on the term spread, (iii) mark-to-market losses on its duration book when long yields rise — and is slowly
rebuilt by retained premia and new entry. The price of risk falls exponentially in the ledger, and procyclical leverage
amplifies every shock more when the ledger is depleted. Short-rate (funding-cost) changes also move valuations directly.

## 2. Mechanism (who trades, under which constraints, why prices move)
Agents.
- **Intermediaries** (dealers, levered funds, bank trading books) are the marginal holders of equity risk. They hold a risky
  book that is `L` times their capital, financed at the short rate. They also run a maturity-transformation book (long
  bonds/loans funded short), whose size relative to capital gives a carry multiplier `c_ts` and a duration exposure `D_b`.
- **End investors** hold the rest of the market at a fixed risk appetite; they do not absorb shocks at short horizons.
- **New capital** enters the intermediary sector slowly (retained high premia, new funds, recapitalisation).

Constraint. Intermediaries face a risk limit per unit of capital. With log capital deviation `x` (0 = normal):
- the price of risk they demand is `lambda(x) = lambda0 * exp(-klam * x)`: less capital, higher required premium;
- their leverage is procyclical-in-capital: `L(x) = L0 * exp(-psi * x)` (psi = 0: they shrink the book one-for-one with
  capital; psi = 1: the book is sticky and leverage rises as capital falls). A hard limit caps `L*k <= 0.75`
  (forced deleveraging beyond it).

Price formation. A required-premium change that is expected to decay at the recapitalisation speed `kappa` moves the log
price-dividend ratio by about `-dPremium/(kappa + dy0)`. With `prem(x) ~ prem0*(1 - klam*x)` this gives a valuation
sensitivity `k = prem0*klam/(kappa + dy0)`: `d ln P = d ln D + k * dx - b_r * d rf`.

Ledger. Each day the ledger moves by the intermediaries' unexpected profit on their books (normal profits are paid out):
`dx = L*(f + k*dx - b_r*d rf) + c_ts*(s - s_bar)*dt - D_b*d y10 - kappa*x*dt`,
where `f` is cash-flow news, `s = y10 - rf` the term spread, `s_bar` a slow (5-year) average of the spread (the "normal"
carry that payout policy has adapted to). Solving the fixed point:
`dx = A * [ L*(f - b_r*d rf) + c_ts*(s - s_bar)*dt - D_b*d y10 - kappa*x*dt ]`, with amplification `A = 1/(1 - L*k)`.

Price return. `d ln P = (rf + m_p)dt - 0.5*sigma_t^2*dt + A*f + k*A*(o_t) - A*b_r*d rf`, where
`o_t = c_ts*(s - s_bar)dt - D_b*d y10 - kappa*x*dt`, `m_p = prem0 - dy0` (normal excess drift of the PRICE index) and
`sigma_t = A_t * s_f,t` (total vol rises when the ledger is depleted because `A` rises).

Feedback into rates. Intermediaries also bear duration risk, so the term premium rises when their capital is low:
`y10 = expected average short rate over 10y + tp_t + tp_x*(-x)`. This closes a second loop (low capital -> higher y10 ->
duration loss -> lower capital).

## 3. Why it should exist in real markets (economic argument)
- Whoever is marginal sets prices. Over horizons of days to a few years, the investors who can trade size against a shock
  are levered intermediaries; their capital is scarce and slow to replace (raising equity after losses is costly, and
  new entrants need time). So the shadow price of their risk constraint is a state variable for all risky assets.
- Intermediaries earn their living from carry: they borrow short and lend/hold long. A flat or inverted curve starves them
  of income for as long as it lasts; a rise in long yields marks their bond books down. Both drain the same capital that
  supports equity risk-taking, so funding conditions reach equity prices through capital, and with a delay (an integral),
  not only through the textbook discount-rate channel.
- Leverage that does not shrink fully when capital falls (sticky books, illiquid positions) makes a given news shock move
  prices more when capital is low: amplification, fire-sale pressure, high volatility after losses.
- Because capital is rebuilt slowly, the high premium demanded after losses is earned over the following months/years:
  the price drift is predictable from the ledger.

What is NEW here (the combination is mine): a single hidden ledger that integrates equity innovations, term-spread carry
and duration marks; an exponential price of risk in that ledger; leverage elasticity `psi` that sets how amplification
grows when the ledger falls; and a term premium that itself loads on the ledger. Known ingredients (intermediary capital
as a pricing factor, procyclical leverage, discount-rate effect of the short rate) are combined into one dynamic system
with these specific flows.

## 4. What it predicts that a random walk does not
1. Long-horizon (months to years) reversal of excess returns: the expected excess drift is roughly
   `m_p + k*A*kappa*(-x) + k*A*c_ts*(s - s_bar) + A*b_r*E[-d rf]/dt` — high after cumulative losses, low after run-ups.
2. Volatility is a function of the depleted ledger (amplification), so it rises after cumulative losses and stays high
   while capital is low; it is persistent beyond what news-intensity clustering alone produces.
3. The term spread enters twice: the CURRENT spread above its slow norm predicts higher near-term drift (capital inflow),
   while a long PAST stretch of flat/inverted curve (cumulated negative carry) depletes the ledger and predicts high
   returns once the ledger is low (and lower returns while the drain is in progress).
4. Rising long yields hit equity contemporaneously in proportion to `D_b` and are followed by a partial recovery.
5. A rise in the short rate lowers prices now and predicts higher drift as rates mean-revert (funding-cost channel).
6. The Kelly-optimal exposure `mu/sigma^2` is state-dependent: higher when the ledger is moderately depleted and realised
   volatility has subsided, lowest after large run-ups (high ledger, low premium); in deep crunches the premium rises but
   variance rises faster (A^2), so optimal exposure can fall.

## 5. How it could be false
- Past cumulative excess returns (with a 0.5-5 year decay) carry no information about future excess returns, or the sign
  is positive (trend) at those horizons.
- Volatility after losses is unrelated to cumulative losses beyond short-lived news clustering.
- Term spread and long-yield changes carry no predictive information for equity excess returns.
- Intermediary leverage is fully countercyclical (psi ~ 0 and no price impact, k ~ 0): then A ~ 1 and the ledger does not
  matter; the market is close to a random walk with exogenous stochastic volatility (= the mechanism-off world).
- In real data the predictive part may be too weak relative to noise and costs to be exploitable; the theory allows
  that (klam and kappa have wide priors that include weak worlds).

## 6. Priors (all drawn independently, uniformly, PER PATH; each path is a different world)
Units: annual decimals unless stated; daily step dt = 1/252.

| symbol | prior | role / reason |
|---|---|---|
| `sigma0` | U[0.12, 0.26] | normal-state total vol of index log returns from cash-flow news (incl. normal amplification A0). Background: equity index vol is of order 10-40%/yr; I take a central band and let amplification and SV produce the higher states. |
| `lam0` | U[0.8, 3.0] | normal-state price of risk = expected excess TOTAL return / variance. Theory: it equals the Kelly leverage of the marginal (log-utility-like) intermediary; levered intermediaries hold books of order 1-3x their capital in equity risk. |
| `prem0` | `min(lam0*sigma0^2, 0.10)` | normal-state expected excess total return (derived). Cap at 10% because a sector earning more than that on unlevered risk would attract entry. |
| `dy0` | U[0.01, 0.05] | normal dividend yield. Background: "a few percent". The PRICE index does not earn it. |
| `m_p` | `prem0 - dy0` | normal-state arithmetic excess drift of the price index over rf (derived; may be negative in some worlds). |
| `L0` | U[1.5, 5.0] | intermediary risky book / capital in the normal state. First principles: dealers/levered funds run a few times capital; bank-like balance sheets more, but only part of that is equity risk. |
| `psi` | U[0, 1] | leverage elasticity to capital (0 = proportional deleveraging, 1 = sticky book). Unknown; full range. |
| `HLk` | U[0.5, 5] yr | half-life of the capital gap; `kappa = ln2/HLk`. Recapitalisation takes months (retained premia) to years (entry). |
| `klam` | U[0.2, 1.2] | elasticity of the price of risk to log capital. 0.2 = weak (a halving of capital raises the premium ~15%), 1.2 = strong (~2.3x). Includes weak worlds on purpose. |
| `k` | `prem0*klam/(kappa + dy0)` | valuation sensitivity of the log price to the ledger (derived, see §2). |
| `LKmax` | 0.75 (fixed) | cap on `L*k` (forced deleveraging); keeps amplification `A <= 4`. Numerical/structural limit, not tuned. |
| `s_f0` | `sigma0*(1 - min(L0*k, 0.75))` | normal-state cash-flow news vol (derived so that the normal total vol is `sigma0`). |
| `HLv` | U[10, 120] trading days | half-life of exogenous news-intensity (stochastic vol), NOT part of the mechanism. Background: volatility clusters. |
| `sv` | U[0, 0.45] | stationary sd of log news-vol; `s_f,t = s_f0*exp(h_t - sv^2)` (unit mean variance). Includes no-SV worlds. |
| `df` | U[3, 12] | Student-t degrees of freedom of daily news shocks (unit variance). Background: daily returns are fat-tailed. |
| `m_r` | U[0.00, 0.08] | long-run mean of the shadow short rate `u`; `rf = max(u, 0)` (zero lower bound). Background: short rates of a few percent, sometimes near zero. |
| `HLr` | U[1, 8] yr | half-life of short-rate deviations (policy cycles). |
| `v_r` | U[0.005, 0.025] /sqrt(yr) | short-rate shock vol. |
| `tp0` | U[-0.005, 0.025] | mean term premium of the 10y yield. |
| `HLtp` | U[0.5, 4] yr | half-life of term-premium noise. |
| `sd_tp` | U[0.002, 0.010] | stationary sd of term-premium noise. |
| `tp_x` | U[0, 0.008] | term-premium loading on depleted capital (`+tp_x` per unit of `-x`, lagged one day). |
| `y10` | `m_r + (rf - m_r)*F + tp_t + tp_x*(-x_{t-1})`, `F = (1-exp(-10a))/(10a)`, `a = ln2/HLr` | expectations part + premium. Reported in percent. |
| `c_ts` | U[0, 12] | carry multiplier: maturity-transformation book / capital. 0 = no carry channel. |
| `D_b` | U[0, 25] | duration exposure of capital (bond book/capital x duration). 0 = no duration channel. |
| `b_r` | U[0, 4] yr | direct equity valuation sensitivity to the short rate (funding-cost / discount channel; ~ persistence of rate changes x share not passed into nominal growth). |
| `monthly` | Bernoulli(0.4) | path observes rf and y10 only in 21-day steps (held constant in between); the price reacts on step days. |
| fixed | — | `s_bar` = EWMA of `s` with 5-year half-life (payout norm); `x` clipped to [-2.5, 1.5]; burn-in 500 days discarded; `x = 0`, `h = 0`, `u = m_r`, term-premium noise 0 at the start of burn-in. |

Daily recursion (ON world), with lagged state: `L_t = L0*exp(-psi*x_{t-1})`, `LK = min(L_t*k, 0.75)`,
`A = 1/(1-LK)`, `L_eff = LK/k`; news `f = s_f,t*eps/sqrt(252)`;
`o = c_ts*(s_{t-1}-s_bar_{t-1})/252 - D_b*(y10_t - y10_{t-1}) - kappa*x_{t-1}/252`;
`dx = A*(L_eff*(f - b_r*d rf) + o)`; `ln P_t - ln P_{t-1} = (rf_t + m_p)/252 - 0.5*(A*s_f,t)^2/252 + f + k*dx - b_r*d rf`;
`r = exp(.) - 1`, `r[:,0] = 0`.

## 7. Mechanism-off world (same overall scale, mechanism disabled)
Same parameter draw, same random numbers, same short-rate path. Disabled: `k = 0`, `b_r = 0`, `c_ts = D_b = tp_x = 0`,
`A = 1` (no ledger, no price of risk variation, no funding channel). The price index then follows
`d ln P = (rf + m_p)dt - 0.5*sigma_off,t^2 dt + sigma_off,t*eps*sqrt(dt)` with `sigma_off,t = c_p * s_f,t` where the
per-path constant `c_p` is chosen so that the realised standard deviation of daily log excess returns equals that of the
ON path. Exogenous stochastic volatility and fat tails remain (they are not the mechanism). The y10 path loses the
`tp_x` term. Expected excess drift is constant at `m_p` (the ON world's long-run mean excess drift is also `m_p`, because
`x` is stationary).

## 8. Background knowledge used (could not be avoided; deliberately kept generic)
- Equity index volatility is of order 10-40% per year; daily returns are fat-tailed; volatility clusters.
- Dividend yields are a few percent; short rates range from about zero to high single digits (sometimes higher) and can
  sit at a zero floor; long yields usually exceed short yields by a premium that can turn negative.
- Intermediaries are levered a few times capital; equity risk premia are positive and of the order of a few percent.
- The structural facts of the test given in the brief (price index without dividends, 3x product, costs, taxes, delay,
  block-bootstrap of 250 days). I used no data, no named periods, no remembered statistics of any named index.

## 9. What an informed trader does if the theory is true (direction only; the rule is designed later on synthetic data)
Reconstruct the ledger from observables (decayed sum of excess log returns, term-spread carry relative to its norm,
long-yield changes), map it into an expected excess drift, divide by a running variance estimate, and hold a fraction of
that Kelly exposure, clipped to [0, 3].

PRIORS_FROZEN 2026-11-04T07:24Z
