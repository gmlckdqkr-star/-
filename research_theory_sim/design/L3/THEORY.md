# Salience-Gated Narrative Contagion (SGNC)

Lane TS1, blind designer L3. Family: information and learning.
Written before any simulation or rule design. Started 2026-11-04T07:55Z.

## 1. One-line statement
The market's valuation multiple is the head-count of investors who believe the currently "true" story about long-run
growth; a story change spreads through the investor population like a product adoption (a few independent scouts, then
imitation), and the speed of that spreading is throttled by attention, which is only switched on by unusually large
price moves. Prices therefore drift toward a new story along an S-shaped path whose speed depends on recent volatility.

## 2. Mechanism (who trades, under which constraints, why prices move)
- **Hidden narrative.** At each date the economy is in one of two narrative states s = +1 ("growth story is true") or
  s = -1 ("stagnation story is true"). The state is a Markov chain with mean durations D_up and D_dn (years). The state
  sets true cash-flow growth. Nobody observes s directly.
- **Fundamentals.** The cash-flow index D grows at state-dependent arithmetic rate g_s, with fundamental news shocks of
  volatility sigma_D (with exogenous slow stochastic volatility and fat tails).
- **Rational consistency.** g_s is pinned down so that a fully informed investor who knew s at every instant would earn
  the same required price return R in both states (R = rf + premium - dividend yield):
  g_up = R + h_up*(1 - exp(-dm)) and g_dn = R - h_dn*(exp(dm) - 1), where h = 1/D is the switching hazard and dm is
  the log valuation gap between the stories. (In the good state cash flows grow fast, but the rational price carries the
  risk of a jump down when the story ends; in the bad state the reverse.) This ties the size of the regime drift to the
  size and frequency of narrative swings: there is no free "regime drift" parameter.
- **Beliefs.** A fraction x_t of investors holds the growth story, 1 - x_t the stagnation story. The index trades at
  log P = log D + dm*(x - 1/2) + u (valuation is the belief-weighted mix of the two story valuations; u is a short-lived
  liquidity/noise-trader term).
- **Learning = contagion (Bass-type diffusion).** When the true story is "up", pessimists convert at rate
  a_t*(p + c*x) per year (p: independent learning from own research; c: imitation of those who already converted).
  When the true story is "down", optimists convert at rate a_t*(p + c*(1 - x)). x is kept inside [0.01, 0.99]
  (there are always a few contrarians).
- **Rationed attention gated by salience.** Investors have limited attention and look at the market seriously only when
  it is salient. The attention multiplier is a_t = clip(S_t, 0.25, 4)^eta, where S_t is the ratio of a short EWMA of
  absolute daily returns (half-life hs) to a long EWMA (half-life 250 days, "what a normal day looks like"). Calm markets
  -> learning slows; large moves -> learning accelerates -> more large moves (a feedback loop between price moves and
  learning speed). eta = 0 switches the gate off.
- **Debate noise.** Rumours and talk shift beliefs randomly, with intensity proportional to how split opinion is and to
  attention: dx_noise = sigma_n * x(1-x) * sqrt(a_t dt) * eps. These are belief swings unrelated to the true state; the
  diffusion pulls them back toward the consensus implied by the true state, so they create false mini-trends.
- **Constraint summary.** Investors are not irrational about the stories; they are attention-constrained and social.
  No one is forced to trade; price impact is via the valuation multiple only.

## 3. Why it should exist in real markets (economic argument)
- Long-run growth is not observable; it must be inferred from slow, noisy evidence and from other people. Processing
  evidence is costly, so most investors delegate to what peers believe (imitation is a cheap, rational heuristic under
  costly information). Adoption of any idea through a population with a few independent adopters and many imitators
  follows an S-curve; there is no reason investment ideas are exempt.
- Attention is scarce and competes with other activities. A market that moves little is ignored; a market that moves a
  lot is talked about. So the speed of belief transmission plausibly rises with the salience of recent moves.
- Arbitrage against a slowly spreading story is limited: the informed few cannot take unlimited positions because the
  timing of the diffusion is uncertain and debate noise can move the price against them for months.

## 4. What it predicts that a random walk does not
1. Positive autocorrelation of returns at horizons from a few weeks to about a year (the diffusion time 1/k and the
   regime drift), i.e. variance ratios above 1 at those horizons, with no corresponding predictability in the OFF world.
2. Predictability is concentrated in narrative transitions: after a story turns, the price drifts in one direction for
   months; in consensus periods the drift is the regime drift g_s (higher in the growth story, lower in the stagnation
   story), with low volatility.
3. Volatility is endogenous: it rises during transitions (split opinion -> debate noise; salience -> faster learning)
   and is low in settled consensus. Hence "low volatility + rising price" is the settled growth story and
   "high volatility + falling price" is a pessimistic cascade.
4. The start of a transition is slow when imitation dominates (psi high), then accelerates: the first part of a new
   trend is smaller than its middle part. Cumulative moves therefore predict continuation, not reversal, until the move
   is of the order of the valuation gap dm.
5. Because learning is throttled in calm markets, a story turn after a long quiet period takes longer to be priced.

## 5. How it could be false
- If learning is fast (diffusion time of days) the drift is gone before a rule that trades two days later can act; then
  the theory is economically irrelevant even if true.
- If the valuation gap between stories is small relative to fundamental noise, transitions are not detectable.
- If real return autocorrelation at 1-12 month horizons is zero or negative, or if trends in the index are not
  followed by continuation after a lag of a few days, the theory is falsified.
- If volatility is not higher during directional moves than in calm consensus phases, the salience mechanism is wrong.
- A rule built on it would fail if real trends are mostly debate noise (false trends), so that trading costs and whipsaw
  outweigh the captured drift.

## 6. Priors (each path draws its own world; all draws independent)
Daily time step dt = 1/252. "logU" = log-uniform.

| parameter | prior | reason |
|---|---|---|
| D_up, mean duration of growth story | logU[0.5, 8] yr | a story about long-run growth must persist at least months to move valuations; > 8 yr would give too few episodes to matter in a 30-yr life; symmetric prior with D_dn on purpose (no assumed asymmetry) |
| D_dn, mean duration of stagnation story | logU[0.5, 8] yr | same argument |
| sigma_D, fundamental news vol | U[0.08, 0.22] /yr | cash-flow news of a diversified index is a fraction of total equity risk (background knowledge: index vol of order 10-30%/yr) |
| omega, narrative share of variance | U[0.05, 0.60] | narrative swings must matter (> 5%) but cannot dominate everything; dm = sigma_D*sqrt(omega/(1-omega)/nu), nu = 2/(D_up+D_dn) switches/yr; dm capped at 1.0 |
| k = p + c, learning speed at normal attention | logU[1.5, 25] /yr | diffusion time constant from about 2 weeks to 8 months; faster would make the theory irrelevant, slower would make a story change take many years |
| psi = c/k, imitation share | U[0, 0.95] | from pure independent learning (exponential approach) to strongly social (late, sharp S-curve) |
| eta, salience elasticity of attention | U[0, 1.5] | 0 = no gate; 1.5 = attention 8x when moves are 4x their norm |
| hs, salience half-life | U[5, 40] days | how fast "the market is moving a lot" registers with people: one to eight weeks |
| sigma_n, debate noise | U[0, 1.5] /sqrt(yr) in belief units | from none to belief swings comparable to a quarter of the valuation gap per year at split opinion |
| premium (total excess return) | U[0.01, 0.08] /yr | investors must be paid for bearing equity risk; wide (background knowledge: positive, a few %) |
| div_yield (price index omits dividends) | U[0.00, 0.05] /yr | background knowledge: dividend yields of a few % |
| rf mean | U[0.00, 0.07] /yr | background knowledge: short rates between zero and high single digits |
| rf mean-reversion half-life | logU[2, 15] yr | policy-rate cycles are slow |
| rf stationary sd | U[0.005, 0.03] /yr | rates wander by a few points; floored at 0, capped at 0.2 |
| rf monthly-step flag | Bernoulli(0.3) | the brief says early rates may move in monthly steps: then rf is held constant over 21-day blocks |
| stochastic-vol half-life (fundamental) | logU[20, 500] days | exogenous vol clustering, present in ON and OFF worlds |
| stochastic-vol sd of log vol | U[0, 0.5] | from none to strong; normalised so E[v^2] = 1 |
| fat-tail df (Student-t, unit variance) | U[3, 12] | daily news has fat tails (background knowledge) |
| liquidity noise u: stationary sd | U[0, 0.02] | short-lived price pressure, a nuisance (both worlds) |
| liquidity noise half-life | U[1, 10] days | |
| belief bounds | x in [0.01, 0.99] (fixed) | a few contrarians always exist |
| long salience norm | EWMA half-life 250 days (fixed) | "a normal day" is judged against about a year of experience |
| initial state | s0 = +1 with prob D_up/(D_up+D_dn); x0 at that consensus | stationary start |

## 7. Mechanism-off world (same overall scale, mechanism disabled)
Same parameter draws and same random numbers (same story switch dates, fundamentals, rf, stochastic vol, liquidity
noise). Learning is instantaneous and complete: x jumps to the consensus of the true story at the switch date (a rational,
fully attentive market). Attention gating is irrelevant. The debate-noise variance of the ON path is replaced by i.i.d.
Gaussian noise with the same path-average variance. Each switch still moves the log price by dm (as a jump instead of a
diffusion), so total narrative variance, required return R and fundamental risk are the same. In the OFF world the
expected price return including jump risk is R in both states: no predictable excess drift.

## 8. Background knowledge used
- Equity index volatility is of order 10-30% per year; equity risk premia are positive and a few % per year; dividend
  yields are a few %; short rates range from zero to high single digits; rates are slow-moving.
- Daily returns have fat tails and volatility clusters (generic stylised facts, no specific episodes).
- The Bass diffusion model (innovation + imitation) from the product-adoption literature and the general idea of limited
  attention. The combination (Markov true story with rational-consistency growth, Bass diffusion of beliefs, salience-
  gated attention feedback, debate noise proportional to opinion split) is my own.
- No specific crashes, years, decades, named indices, or their return/volatility statistics were used.

PRIORS_FROZEN 2026-11-04T07:56Z
