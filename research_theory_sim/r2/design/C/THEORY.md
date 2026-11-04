# THEORY - "Fast Aftershocks, Slow Scars" (FASS)

Lane TS2, round 2, blind designer C. Family: rare disasters and crash risk.
Written before any simulation (started 2026-11-04T10:54Z).

## 1. One-line statement
Crash days of an equity index arrive as a self-exciting process whose true intensity spikes and decays FAST after each
crash (aftershocks, weeks to a few months), while the price-setting investors carry a SLOW, long-memory "scar" in their
perceived crash probability and, separately, part of every crash is a temporary overshoot caused by depleted
crash-insurance capital; so the disaster premium the market pays is out of phase with the risk actually present:
risk is highest in the aftershock window, while the reward per unit of risk is highest in the months after the
aftershocks have died out and the scar and the overshoot are still unwinding.

## 2. Mechanism (who trades, constraints, why prices move)
Three groups and one fundamental process.

1. Fundamental crash process (self-exciting disasters). Large down days ("crash days") are the visible face of disaster
   news (financial contagion, fire-sale feedback, policy shocks). Each crash day raises the near-term probability of
   further crash days (Hawkes branching ratio n), and this excess intensity decays quickly with an Omori-like kernel
   (a mixture of a fast and a slower exponential, together weeks to a few months). On top sits a slowly drifting,
   hidden background fragility lambda_b(t) (years). Expected crash size grows mildly with background fragility.
   Diffusive (everyday) volatility co-moves with the total crash intensity (turbulence spills into ordinary days).
2. Long-horizon holders (households, pensions, balanced funds): they hold the index and demand a disaster premium
   proportional to their PERCEIVED crash loss rate Ybar * lambda_tilde. Their perception is experience-based and has
   long memory: each experienced crash raises lambda_tilde by a "scar" that fades over years (tau_s), they price only a
   fraction theta_a of the (fast) aftershock excitation (they think of crash risk as a slowly moving probability, not as a
   self-exciting process), and only a fraction theta_b of the hidden background fragility (partial observability).
   Constraint: they do not lever and rebalance slowly, so they do not arbitrage the gap between perceived and true risk.
3. Crash-insurance providers (option writers, market makers, leveraged balance sheets): they are short crash risk. On a
   crash day their capital is hit and they must de-risk, which pushes the price below the fundamental loss: a share q of
   each crash-day drop is a temporary overshoot. It unwinds as their capital is rebuilt from premia and new entry
   (time constant tau_r, months to ~1.5 years). Constraint: capital, not beliefs, limits them.
4. Price formation. The conditional expected excess log return (annual) is

       m(t) = base + Ybar(t) * [ (1 + psi) * (lambda_tilde(t) - lambda_bar) - (lambda(t) - lambda_bar) ] + R(t)
            = base + psi * Ybar * (lambda_tilde - lambda_bar)        <- disaster premium on PERCEIVED risk
                   + Ybar * (lambda_tilde - lambda)                   <- belief gap (perceived minus true intensity)
                   + R(t)                                             <- overshoot unwinding (insurer capital rebuild)

   with lambda(t) = lambda_b(t) + H(t) the true intensity (H = aftershock excitation), and
   lambda_tilde(t) - lambda_bar = theta_a (H - Hbar) + theta_b (lambda_b - lambda_b_bar) + (S - Sbar), where S is the
   scar (an exponentially fading count of past crash days with gain theta_s and memory tau_s), and
   R(t) = delta(t) / tau_r, delta = fading sum of q * (crash-day drops). The time average of the state-dependent part is
   removed per path, so the unconditional premium equals the per-path premium drawn from the prior (section 5).
   Realised daily excess log return: x = m/252 + p(t)*Ybar(t) + sigma(t)*eps/sqrt(252) - Y*N(t), where N(t) is the
   crash-day indicator (probability p = 1 - exp(-lambda/252)), Y the crash size (Gamma) and p*Ybar compensates the expected
   crash loss, so E_t[x] = m/252.

Phases this produces: calm (low vol, rare crash days); aftershock window (very high variance, the expected return may be
below or above normal depending on how much of the aftershock risk is priced: theta_a, psi); scarred recovery (true
intensity back to background, perceived intensity and overshoot still elevated -> high expected return per unit of risk);
slow fade back to calm.

## 3. Why it should exist in real markets (economic argument)
- Contagion / fire-sale feedback makes crash risk self-exciting on short horizons: losses force sales that cause more losses
  until balance sheets are repaired or policy steps in, so aftershock risk is concentrated and short-lived.
- Experience-based belief formation and belief scarring after tail events make perceived tail probabilities long-memory:
  agents who lived through a crash keep demanding compensation for it long after the true conditional risk has decayed.
- Limits to arbitrage: the parties who are short crash insurance are capital constrained; a crash depletes their capital, so
  the price of crash risk (and the price discount) overshoots and only normalises as capital is rebuilt.
- Long-only, unlevered holders cannot exploit the gap between perceived and true risk, and capital-constrained
  intermediaries cannot do it right after a crash, so the gap is not arbitraged away by the marginal investors.
- The new element (my own combination) is the PHASE MISMATCH between a fast true risk clock (aftershock kernel) and two
  slow reward clocks (belief scar and insurer-capital rebuild), and its consequence for a levered investor whose growth
  depends on reward / variance rather than on reward alone.

## 4. Predictions that a random walk (or iid fat-tailed returns) does not make
P1. Large down days cluster in time beyond chance; the clustering decays over weeks to a few months.
P2. Everyday volatility rises with the recent density of crash days (volatility clustering tied to crash clustering).
P3. The reward-to-variance ratio is lowest inside crash clusters and highest in the 3-18 months after a cluster ends.
P4. Returns over the 6-18 months after a cluster of crash days are above the unconditional mean (scar + overshoot unwind):
    crashes are partly recovered.
P5. Negative skew of multi-week returns; drawdowns deeper than an iid model with the same volatility would produce.
P6. Implication for a levered growth investor (not a prediction about prices): exposure should scale with
    reward / variance, i.e. fall quickly when crash days and turbulence appear and come back while the scar and overshoot
    are still paying, before volatility is fully back to calm levels.

## 5. How it could be false
F1. Large down days are no more clustered than an iid fat-tailed model implies (n ~ 0).
F2. Beliefs adjust fast (theta_s ~ 0 or tau_s short) and there is no overshoot (q ~ 0): then there is no post-cluster
    premium and re-entry timing has no value; only variance timing is left.
F3. The market fully prices aftershock risk and over-compensates it (theta_a ~ 1 with large psi): then expected returns are
    highest inside the cluster and de-levering during clusters loses the best days.
F4. Crashes are permanent (no recovery) and followed by lower, not higher, returns.
F5. Volatility does not co-move with crash risk, or the premium scales one-for-one with variance (then variance timing
    adds nothing for a levered investor).
The prior below is deliberately wide enough to contain F2 and F3 cases (q, theta_s, psi, theta_a all include values that
switch parts of the mechanism off or reverse its sign for the in-cluster phase).

## 6. Published anchors (section 2b of the brief)
Remembered numbers (no data opened; memory only), with the conversion I apply and how sure I am.

A1. Dimson, Marsh & Staunton, "Triumph of the Optimists" (2002) and their annual Global Investment Returns Yearbook
    (Credit Suisse, later UBS), 1900 onward, ~20+ countries. Remembered: world equity premium over bills about 4.0-4.5%
    per year geometric and about 5.5-6% arithmetic; US about 5.5% geometric and about 7% arithmetic; annual standard
    deviation of world equities about 17%, US about 19-20%, typical single countries 20-30%.
    Sureness: moderate (each number +-1 pp).
A2. Mehra & Prescott (1985), "The Equity Premium: A Puzzle": US 1889-1978, arithmetic premium over bills about 6%, equity
    standard deviation about 16.5%. Sureness: fairly sure.
A3. Jorda, Knoll, Kuvshinov, Schularick & Taylor (2019), "The Rate of Return on Everything, 1870-2015" (16 countries):
    real equity total returns around 6.5-7% per year, real bills around 1%, so a premium over bills around 5-6%;
    dividend yields averaging roughly 4%. Sureness: moderate.
A4. Dividend yield / capital-gain split (DMS, long-run national series): over the long run most of the real equity return
    came from dividends, with a long-run average dividend yield of roughly 4%, and lower yields (around 2%) in the later,
    buyback-heavy part of the long samples. Sureness: moderate on the 4% century average, low on the exact later level.
A5. Barro (2006) "Rare disasters and asset markets in the twentieth century" and Barro & Ursua (2008/2009) on
    macroeconomic disasters and stock-market crashes: macro disasters (large consumption/GDP drops) roughly 1.5-2% per
    country-year with mean size around 25-30%; stock-market crashes (cumulative multi-year real return of -25% or worse)
    roughly 3-4% per country-year, with mean real declines around 40-45%. Sureness: low-moderate.
A6. Stylised facts of daily index returns (e.g. Cont 2001, "Empirical properties of asset returns"): fat tails, volatility
    clustering, negative skew, large down days rare but clustered. Qualitative only; no number used.

Conversions applied
- Headline underlying is a PRICE index. Price-index arithmetic premium over cash = total-return arithmetic premium minus the
  dividend yield. Centre: total-return arithmetic premium 6.0% (A1 world ~5.5-6%, A2 ~6%, A3 ~5-6%; US-type markets ~7%),
  minus a central dividend yield of 3.0% (between the ~4% long-run century average of A3/A4 and the ~2% of the later,
  buyback-heavy decades, because the headline index covers several recent-ish decades and buybacks move payout into price
  growth) = 3.0% per year arithmetic excess of the price index over cash.
  Prior: per path, pi_bar ~ Normal(0.030, 0.020) truncated to [-0.02, 0.09]. The +2 sd end (7%) covers total-return
  funds with reinvested distributions (premium ~6-7%) and high-premium markets; the -2 sd end (-1%) covers poor markets
  and high-yield price indices.
- Volatility: centre 17.5% annual (A1 world 17%, US 19-20%, A2 16.5%). Prior: per path, sigma_bar ~ LogNormal(median
  0.175, log-sd 0.25) truncated to [0.10, 0.35] (90% band ~12%-26%; single-country funds can be 25-30%).
- Premium and volatility are drawn independently (I do not impose a constant Sharpe ratio across markets).
- Drawdowns (A5): a 25%+ real crash about once per 25-30 country-years implies roughly one such episode per 30-year path.
  For a nominal price index this suggests a median 30-year maximum drawdown of roughly -40% to -50% and a sizeable minority
  of paths (~25-40%) with a drawdown beyond -50%. I do not tune the crash parameters to hit this; I report the simulated
  drawdown distribution and compare it with this anchor.

## 7. Priors (every simulator parameter; drawn PER PATH; U = uniform)
Market level (brief 2b/2c):
| parameter | prior | reason |
|---|---|---|
| pi_bar (arith. excess of price index over rf, /yr) | N(0.030, 0.020), trunc [-0.02, 0.09] | anchors A1-A4, conversion above |
| sigma_bar (total vol, /yr) | LogN(median 0.175, sd_log 0.25), trunc [0.10, 0.35] | anchors A1-A2 |
Crash process:
| jshare (share of total variance from crash days) | U(0.10, 0.35) | fat tails: a few big days carry a large part of variance (A6) |
| Ybar (mean crash-day log drop) | U(0.025, 0.055) | 2.5-5 daily sigmas at 17.5% vol: "large down days" |
| k_Y (Gamma shape of crash size) | U(1.5, 4.0) | size dispersion; low k = heavier crash-size tail |
| lambda_bar (mean crash days /yr) | derived: jshare*sigma_bar^2 / (Ybar^2 (1+1/k_Y)) | keeps the unconditional variance at sigma_bar^2 |
| n (Hawkes branching ratio) | U(0.30, 0.80) | share of crash days that are aftershocks; < 1 for stationarity |
| tau_1 (fast kernel, trading days) | U(5, 30) | Omori-like fast decay |
| tau_2 (slow kernel, trading days) | U(40, 160) | Omori-like long tail of the kernel |
| w_1 (weight of fast kernel) | U(0.3, 0.8) | |
| tau_b (background fragility time scale, years) | U(1, 6) | slowly moving hidden fragility |
| s_b (stationary sd of log background) | U(0.2, 0.9) | how much the hidden disaster probability varies |
| xi (crash size elasticity to background) | U(0.0, 0.5) | "expected size varies over time" |
| zeta (diffusive variance elasticity to lambda/lambda_bar) | U(0.3, 1.0) | P2; diffusive variance normalised so its mean is (1-jshare) sigma_bar^2 |
Beliefs and pricing:
| theta_a (priced share of aftershock excitation) | U(0.2, 1.0) | market models crash risk as slow; 1 = fully priced |
| theta_b (priced share of background fragility) | U(0.0, 1.0) | partial observability |
| theta_s (scar gain: perceived extra crash days per experienced crash, integrated) | U(0.0, 0.6) | 0 = no scar (F2) |
| tau_s (scar memory, years) | U(0.5, 3.0) | experience-based long memory |
| psi (premium markup per unit of perceived expected crash loss) | U(0.0, 2.0) | 0 = risk-neutral pricing of crashes; >1 = strong aversion |
| q (temporary overshoot share of each crash-day drop) | U(0.0, 0.5) | 0 = no insurer-capital channel (F2/F4) |
| tau_r (overshoot unwind time, years) | U(0.25, 1.5) | capital rebuild speed |
Rates (brief 2d; identical in ON and OFF worlds; not linked to the crash mechanism in this theory):
| rf start level (/yr) | U(0.00, 0.08) | wide range of rate eras |
| rf regime length (years) | U(4, 15), regimes follow each other | long steady regimes |
| rf regime type | up / down / stable, prob 1/3 each | trends of a decade or more |
| rf trend slope (pp per year) | U(0.2, 0.8) | e.g. 0.5 pp/yr over 12 yrs = 6 pp |
| rf noise | OU around the regime path, sd 0.4 pp, time scale 0.5 yr | |
| rf bounds | reflected into [0, 0.15]; a trend that hits a bound turns stable | |
| monthly steps | with prob 0.5 per path rf and y10 are held flat within 21-day months | early-decade data |
| y10 (percent) | 100*(rf + spread), spread OU mean U(0.005, 0.02), sd 0.01, time scale U(1, 3) yrs, floor 0.1% | term spread |
Fixed simulator conventions (not priors): 252 days/yr; internal burn-in of 756 days discarded so states start stationary;
at most one crash day per day; Gaussian diffusion; the state-dependent part of m(t) is capped at +-1.5/yr and its path
time-average removed; base = pi_bar - 0.5*sigma_bar^2 (log premium, so the arithmetic excess is ~pi_bar);
simple index return r = exp(x + log(1 + rf)) - 1; r[:, 0] = 0.
Prior narrowing / widening (robustness): every U(a, b) becomes U(c - s(c - a), c + s(b - c)) around its centre c, and the
normal / log-normal sds are multiplied by s, with s = 0.5 (narrow) or 1.5 (wide), clipped to the hard bounds
pi_bar in [-0.04, 0.12], sigma_bar in [0.07, 0.45], n in [0, 0.9], thetas in [0, 1], q in [0, 0.7], other params > 0.

## 8. Mechanism-off world
Same per-path pi_bar, sigma_bar, jshare, Ybar, k_Y and the same rf / y10 paths. Returns are iid: Gaussian diffusion with
variance (1 - jshare) sigma_bar^2 plus iid Poisson crash days at constant rate lambda_bar with the same Gamma crash size,
compensated so that the arithmetic excess return is ~pi_bar. No self-excitation, no background fragility, no vol
coupling, no perceived-vs-true gap, no scar, no overshoot, no predictable mean. Same unconditional premium, volatility,
crash-day frequency and crash size distribution as the ON world.

## 9. What an informed trader would do (derived before any simulation)
Not knowing pi_bar, sigma_bar or the mechanism parameters of the market in front of him, a growth (Kelly) investor sets
exposure L ~ E_t[excess return] / Var_t[return], capped to [0, 3]. Under FASS:
- Var_t is driven by the fast clock: estimate it with a short-memory variance of daily returns (crash days included),
  so exposure drops within days of a crash cluster;
- E_t is a prior premium (shrunk towards the anchor, since a 30-year sample cannot pin down a 3% premium) plus a slowly
  fading post-crash term (scar + overshoot) that is observable from the recent history of large down moves / drawdown
  depth, and which keeps exposure up during the recovery even while variance is still somewhat elevated;
- trading costs, the 0.5 level grid and taxes call for smoothing of the target.
The OFF world tells how much this costs when the mechanism is absent: variance is then constant and the rule should sit
near a constant level.

PRIORS_FROZEN 2026-11-04T10:56Z
