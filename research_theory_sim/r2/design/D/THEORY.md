# THEORY - lane TS2 round 2, designer D

## Name
**Funding-Carry Capital Ledger (FCCL)**: the equity price of risk is set by the capital of leveraged intermediaries,
and that capital is a running ledger fed by three flows - levered equity P&L, the funding carry earned on maturity
transformation (the term spread), and duration losses when long yields rise - plus a fast risk-limit (VaR) loop that
turns recent realised volatility into tighter limits.

Written 2026-11-04T10:55Z, before any simulation.

## 1. Mechanism (who trades, under which constraints, why prices move)

Agents.
- **Outside investors** (households, pensions, unlevered funds). They hold a slowly changing equity share and do not
  arbitrage medium-run swings in the price of risk (mandates, inattention, no access to leverage). They are not the
  marginal price setters at horizons of days to a few years.
- **Leveraged intermediaries** (dealer banks, levered funds, market makers financed by prime brokers / repo). They
  absorb the residual equity risk that outside investors do not want at the current price. Their balance sheet has two
  books: (a) a levered equity / risk-absorption book and (b) a maturity-transformation carry book (long duration and
  credit, financed overnight at the short rate). Two constraints bind:
  1. a **capital constraint**: the amount of risk they can carry is proportional to their equity capital, and new
     capital arrives only slowly (equity issuance and entry are slow, payouts are sticky) - "slow-moving capital";
  2. a **risk-limit (VaR) constraint**: positions are limited by risk measured from recent realised volatility.
- **The central bank** sets the short rate in discrete steps at meetings. Policy has long trending regimes (years of
  steady tightening, years of steady easing, stable periods) with shorter cycles on top. The long yield is the
  expectation of the future short rate (anchored on a slow memory of past short rates) plus a term premium.

The capital ledger. Let `x` be the log intermediary capital relative to its normal level (`x = 0` normal). Per day:
```
x_t = (1 - kappa dt) x_{t-1}                (slow recapitalisation / payout toward normal)
      + m * e_t                              (levered P&L of the equity book, e_t = unexpected equity excess return)
      + c * (S_{t-1} - tpbar) dt             (funding carry: term spread S = y10 - short rate, minus its normal level)
      - D_y * dY_t                           (duration loss of the carry book when the long yield rises)
      + nu_x sqrt(dt) eta_t                  (idiosyncratic intermediary gains / losses, e.g. credit events)
```
Prices. Because intermediaries are the marginal risk-bearers, their capital sets the price of risk and the
amount of volatility the market can absorb:
```
sigma_t = sigma_bar/K_s * exp(-g x_{t-1}) * (v_{t-1}/sigma_bar^2)^(rho/2)          (capital + VaR-loop amplification)
mu_t    = mu_bar/K_q * exp(-b x_{t-1}) * (sigma_t/sigma_bar)^beta + phi*c*(S_{t-1} - tpbar)   (price of risk + carry inflow)
r_t     = rf_t + mu_t dt + sigma_t sqrt(dt) z_t  - phi*D_y*dY_t + phi*nu_x sqrt(dt) eta_t
v_t     = lambda_v v_{t-1} + (1 - lambda_v) e_t^2/dt                                   (VaR window: fast EWMA of variance)
```
`K_s`, `K_q` are per-path normalisers so that the path's unconditional volatility is `sigma_bar` and its unconditional
premium is `mu_bar` (same as the mechanism-off world). `phi` is the valuation sensitivity of the log price to the
non-equity ledger flows: because the risk capacity is the *realised* capital (nobody outside the constrained sector
front-runs it), a carry inflow raises prices as it accrues (a predictable drift when the spread is above normal) and a
duration loss lowers prices at once (stocks fall when long yields jump).

Why prices move the way they do.
- Equity losses drain intermediary capital with leverage `m`; low capital raises the price of risk (`b`) and lowers the
  amount of risk the sector can absorb, so volatility rises (`g`): the leverage effect and slow volatility regimes.
- Risk limits are computed on recent realised variance `v`; a burst of volatility tightens limits, liquidity provision
  shrinks and volatility stays high for weeks (`rho`, `HL_v`): fast volatility clustering.
- Monetary regimes act on the ledger. In a long tightening regime the short rate climbs toward / above the long
  yield (the long yield is anchored on a slow memory of past rates), so the carry margin compresses or turns negative
  and the long yield also rises (duration losses). Capital drains *without any equity crash*; volatility drifts up and
  the drift is lowered while long yields keep rising. In a long easing regime the curve is steep, carry is rich,
  capital rebuilds, volatility falls and the price of risk falls.
- The premium scales with risk as `sigma^beta`: `beta = 0` means the required premium does not rise with volatility,
  `beta = 1` a constant Sharpe ratio, `beta = 2` a constant price of variance (then the Kelly exposure does not depend
  on volatility). This exponent is not known; it gets a wide prior.

## 2. Why it should exist in real markets (economic argument)
- Dealers and levered funds are the natural marginal holders of short-run risk; their risk-bearing capacity is limited
  by capital and by risk limits that use recent volatility (capital and VaR constraints are institutional facts).
- Maturity transformation earns the term spread; a flat or inverted curve squeezes that margin, and rising long yields
  impose mark-to-market losses on the duration book. Both are direct balance-sheet consequences of monetary regimes.
- Capital is slow to come back after losses (issuance frictions, debt overhang), so the ledger has a multi-year memory.
- Combination claimed as new here: one single capital state, fed jointly by equity P&L, the funding carry and duration
  losses, sets both the equity price of risk and the equity volatility, while a separate fast VaR loop works on top.
  Monetary regimes therefore move equity premia and volatility *through the intermediary ledger with a lag*, not
  through the discount-rate level itself.

## 3. What it predicts that a random walk does not
1. Volatility clusters at two speeds (weeks: VaR loop; years: capital) and rises after losses (asymmetric).
2. Recent realised volatility predicts future volatility; with `beta < 2` the Kelly exposure `mu/sigma^2` falls when
   volatility is high, so exposure should be scaled down when realised volatility is high.
3. The level of the term spread positively predicts the equity drift (carry inflow into risk capacity); rising long
   yields coincide with equity declines (duration channel).
4. Long tightening regimes (flat curve, rising long yields) are followed by higher volatility and lower drift while
   they last; long easing regimes by lower volatility.
5. After capital-depleting drawdowns the price of risk is high (`b > 0`), so the premium is above normal for one to
   a few years - but volatility is high too, so the effect on the Kelly exposure has an uncertain sign (`b` vs `g`).

## 4. How it could be false
- The term spread has no (or negative) relation to the subsequent equity drift; long-yield changes are unrelated to
  same-day equity returns.
- Volatility does not cluster, or realised volatility does not predict future volatility (no VaR loop).
- Expected returns rise one-for-one with variance (`beta = 2`): then volatility timing adds nothing.
- Tightening regimes show no rise in volatility and no lower drift.
- The carry inflow is anticipated and priced at once by forward-looking investors (then `phi*c` drift is zero).
- In any of these cases a rule derived from FCCL should do no better than a constant exposure.

## 5. Published anchors (unconditional level only)
Numbers below are what I remember from the literature; they are used ONLY for the unconditional centre of the premium,
volatility and drawdown frequency, never for timing.

| source | remembered number | how sure |
|---|---|---|
| Dimson, Marsh & Staunton, *Triumph of the Optimists* (2002) and the annual *Global Investment Returns Yearbook* (1900 onward, ~20+ countries) | equity premium over bills: world index about 4.3-4.5%/yr geometric, about 5.5-6% arithmetic; US about 5.5% geometric, about 7% arithmetic; annual std of returns about 17% (world) and 20% (US) | about +-1 pp on the premia, +-2 pp on std |
| Jorda, Knoll, Kuvshinov, Schularick & Taylor (2019), "The Rate of Return on Everything, 1870-2015", 16 advanced economies | real equity total return about 6.5-7%/yr (arithmetic), real bills about 1%, so a premium over bills of about 5-6% arithmetic; country-level annual std about 20-22% | moderate |
| Siegel, *Stocks for the Long Run* | US real total return of stocks about 6.5-6.8%/yr geometric over two centuries | good |
| Shiller long-run US data / DMS on the dividend share of returns | average dividend yield about 4% over the long run (higher early, lower in late decades); most of the long-run real equity return is dividends, real price growth about 1-2%/yr | moderate |
| Mandelbrot (1963), Fama (1965) and later work on daily returns | daily index returns are fat-tailed (Student-t with roughly 3-6 degrees of freedom fits daily data) | good (qualitative) |
| long-run country return studies (DMS and similar) | real peak-to-trough declines of 50% or more happen in essentially every market over a century, typically once every 30-40 years per market; declines of 70-80%+ in a minority of markets | moderate |
| volatility of daily broad-index returns, annualised | about 15-20%, central about 17% | moderate |

Conversion to the headline basis (price index, premium over the short rate, arithmetic per year):
- Central total-return arithmetic premium over bills for a broad market: **6.0%** (between the world index ~5.5-6% and
  the US ~7%; the multi-country average is near 6%).
- Price index: subtract the dividend yield. Central dividend yield **3.5%** (long-run average about 4%, lower in later
  decades; the headline era is unknown). Price-index arithmetic premium over bills centre = 6.0 - 3.5 = **2.5%/yr**.
  (Geometric = arithmetic - sigma^2/2 = about 1.1% at sigma = 17%.)
- Markets with reinvested distributions (country funds): centre **6.0%** (fund costs roughly offset by the higher
  premium of single-country markets).
- Volatility centre **17%/yr** (daily-return based), wide log-normal prior.
- Drawdown frequency: not imposed; checked as an output (share of 30-year paths with a >= 50% drawdown of the 1x hold).
Uncertainty is expressed by the wide prior below, not by moving the centre.

## 6. Priors (every simulator parameter, drawn PER PATH; dt = 1/252)
Unconditional level
| parameter | prior | reason |
|---|---|---|
| `I_TR` (market includes reinvested distributions) | Bernoulli(0.35) | the rule also runs on total-return country funds |
| `mu_bar` arithmetic excess drift over rf (per yr) | Normal(0.025 + 0.035*I_TR, 0.018), clipped [-0.02, 0.10] | anchors above; wide sd covers eras and countries |
| `sigma_bar` (per yr) | LogNormal(ln 0.17, 0.25), clipped [0.09, 0.40] | anchor 17%; country funds can be far more volatile |
| `df` of daily shocks (standardised Student-t) | Uniform(3.5, 8) | fat daily tails |
Rates (exogenous monetary regime; identical in mechanism ON and OFF)
| parameter | prior | reason |
|---|---|---|
| initial short rate `R0` | Uniform(0.005, 0.09) | wide range of starting regimes |
| initial regime | uniform over {up, down, stable} | |
| regime duration | LogNormal(ln 5 yr, 0.6), clipped [1, 20] yr | brief 2d: regimes up to a decade or more |
| trend slope in up / down regimes | +-Uniform(0.002, 0.009) per yr per yr; stable: Normal(0, 0.0005) | 10-year regime moves the rate 2-9 pp |
| regime transitions | to each of the two other regimes with prob 0.5 | no favoured sequence |
| trend bounds | [0, 0.15]; hitting 0 in a down regime -> stable (zero bound); hitting 0.15 in an up regime -> down | |
| policy cycle (OU on the target) | half-life Uniform(0.5, 2) yr, sd Uniform(0.002, 0.012) | shorter cycles inside regimes |
| meetings | every 21 trading days (random phase); moves of 0.25 pp steps toward target, at most 0.75 pp | rates move in steps |
| long-yield anchor `M` | EMA of the short rate, half-life Uniform(2, 6) yr | slow memory of past rates |
| weight of current short rate in y10, `omega` | Uniform(0.2, 0.5) | 10-year average of expected short rates |
| term premium `TP` (OU, daily) | mean `tpbar` Uniform(0.003, 0.020), sd Uniform(0.003, 0.010), half-life Uniform(0.5, 3) yr | normal carry and its noise |
| y10 | 100*max(omega*R + (1-omega)*M + TP, -0.005) (percent) | spread S = y10/100 - R |
Mechanism (intermediary capital ledger, VaR loop; all switched off in the mechanism-off world)
| parameter | prior | reason |
|---|---|---|
| capital half-life `HL_x` (kappa = ln2/HL_x) | LogNormal(ln 2 yr, 0.4), clipped [0.7, 6] yr | slow-moving capital: one to several years |
| equity leverage of the ledger `m` | Uniform(1, 3) | intermediary capital moves 1-3x the equity excess return |
| carry sensitivity `c` | Uniform(2, 8) | a carry book levered ~5x turns a 1 pp spread deviation into 2-8%/yr of capital |
| duration sensitivity `D_y` | Uniform(0, 6) | a 1 pp rise in the long yield costs 0-6% of capital |
| idiosyncratic capital shocks `nu_x` | Uniform(0, 0.15) per sqrt(yr) | credit events unrelated to equity |
| vol sensitivity to capital `g` | Uniform(0.2, 1.2) | low capital -> less risk absorption -> higher vol |
| VaR-loop strength `rho` | Uniform(0.2, 0.7) | partial self-excitation of variance (stationary for rho < 1) |
| VaR window half-life `HL_v` | Uniform(5, 40) trading days | risk limits use weeks of data |
| price-of-risk sensitivity `b` | Uniform(0, 1.5) | low capital -> higher required premium |
| premium-volatility exponent `beta` | Uniform(0, 2) | unknown: constant premium (0), constant Sharpe (1), constant price of variance (2) |
| valuation sensitivity `phi` | Uniform(0.05, 0.25) | how much non-equity ledger flows move the log price |
| initial `x_0` | Normal(0, (m sigma_bar)^2/(2 kappa)) clipped [-2, 2]; `v_0 = sigma_bar^2` | approximately stationary start |
| clips | x in [-3, 3]; sigma_t in [0.3, 5] x sigma_bar | numerical safety |
| normalisers | `K_s` = path RMS of sigma_t (pass 1) / sigma_bar; `K_q` = path mean of exp(-b x)(sigma/sigma_bar)^beta (pass 2) | path unconditional vol ~ sigma_bar, premium ~ mu_bar |

## 7. Mechanism-off world
Same per-path `mu_bar`, `sigma_bar`, `df`, the same Student-t shocks `z_t` and the same rates paths (rf, y10):
`r_t = rf_t + mu_bar dt + sigma_bar sqrt(dt) z_t`. No ledger, no VaR loop, no carry drift, no rate-equity link:
i.i.d. fat-tailed returns with the same unconditional premium and volatility.

## 8. What an informed trader would do (qualitative, before any simulation)
Not knowing `mu_bar`, `sigma_bar` or the mechanism parameters, a growth-maximising trader would hold an exposure close
to a fractional Kelly level `mu_hat / sigma_hat^2`, after the funding cost of the leveraged product, with
- `sigma_hat` from recent realised volatility (the VaR loop and the capital state make it predictable),
- a premium estimate that starts from the anchor prior and can tilt with the funding carry (term spread),
- possibly a tilt with the estimated capital ledger (past equity P&L), whose sign is uncertain under the prior.
The rule must also not lose in the mechanism-off world, so tilts must be modest.

PRIORS_FROZEN 2026-11-04T10:56Z

## Implementation notes (added 2026-11-04T11:03Z, after the first simulator test, BEFORE any rule design; priors unchanged)
Found while checking that the simulator matches the frozen moments (no rule had been written or run):
1. Normalisers. Using the path's own realised RMS of sigma_t (and mean of the premium factor) leaks the path's future
   shocks into its scale: with the leverage effect, paths with bad shocks get scaled down, which biased the realised
   premium up by about 0.9 pp/yr. `K_s` and `K_q` are now computed from an independent pilot run of the same path
   parameters and rates path (fresh shocks, 3 x T long). The ledger is driven by the equity shock measured at the
   path's normal volatility scale (sigma_bar * A_t, where sigma_t = sigma_bar * A_t / K_s), so one pass suffices.
2. Clips (numerical safety, as in section 6): sigma_t in [0.3, 5] x sigma_bar is applied after normalisation; the premium
   factor exp(-b x)(sigma/sigma_bar)^beta is clipped to [0.1, 10] (a required premium beyond 10x normal is not
   meaningful and made the normaliser unstable); daily index returns are floored at -30%.
After these fixes the realised premium of the ON world matches the OFF world (mean deviation from mu_bar about
+0.1 to +0.2 pp in both worlds; median about +0.2 pp higher in ON), and realised volatility has median 0.96 x sigma_bar.
