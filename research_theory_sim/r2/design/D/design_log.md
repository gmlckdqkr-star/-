# design_log - lane TS2 round 2, designer D (theory FCCL)

All timestamps from `date -u +%Y-%m-%dT%H:%MZ`. Numbers are decimals per year (0.054 = 5.4%/yr after-tax CAGR, median
over 30-year paths, engine `common/exec_engine.py` defaults: delay 2, cost 0.003).

## 0. Timeline
| time (UTC) | step |
|---|---|
| 10:46Z | read DESIGN_BRIEF_R2.md and exec_engine.py; created folder |
| 10:55Z | THEORY.md written (mechanism, anchors, priors), no simulation run yet |
| 10:56Z | `PRIORS_FROZEN 2026-11-04T10:56Z` |
| 10:57-11:03Z | sim.py written and checked against the frozen moments; two implementation bugs fixed (normaliser look-ahead, tail clips), recorded in THEORY.md "Implementation notes" (11:03Z), before any rule work; priors unchanged |
| 11:04Z | rule design starts (baselines). After this, sim.py only gained an optional `states=True` output (true mu_t, sigma_t for oracle diagnostics); simulated paths unchanged |
| 11:04-11:50Z | variant search on selection seeds 1, 2, 3, 5 |
| 11:45Z | first frozen candidate A (carry tilt) run on fresh seeds 10000-10003 |
| 11:48-11:50Z | block-world flag on fresh seeds -> check on SELECTION seed 5 -> switch to the simpler rule B |
| 11:50Z | rule.py (B) frozen; final numbers on new fresh seeds 12000-12003 |

## 1. The synthetic worlds (descriptive, not targets; `python sim.py`, seed 1, P = 2000, see sim_stats.txt)
| statistic (p10 / median / p90 over paths) | mechanism ON | mechanism OFF |
|---|---|---|
| premium over rf, arithmetic | -0.001 / 0.039 / 0.084 | -0.011 / 0.039 / 0.092 |
| volatility | 0.096 / 0.161 / 0.270 | 0.125 / 0.171 / 0.232 |
| worst drawdown of the 1x index | -0.86 / -0.46 / -0.21 | -0.72 / -0.44 / -0.26 |
| P(1x drawdown <= -50% in 30 y) | 0.44 | 0.38 |
| 1x hold after-tax CAGR | 0.007 / 0.068 / 0.137 | 0.006 / 0.068 / 0.147 |
| sd of yearly vol / mean vol | 0.19 / 0.45 / 0.94 | 0.05 / 0.07 / 0.11 |
| daily kurtosis | 6 / 16 / 52 | 4.5 / 5.9 / 13 |
Rates: short rate mean 1.1% / 4.8% / 10.1%; 74% of paths have a 10-year window with a rise of >= 3 pp, 60% one with a fall
of >= 3 pp; the rate moves on about 2.4% of days in 0.25 pp steps. 2000 x 7860 simulates in about 30 s (ON), 7 s (OFF).

## 2. A structural fact found first: the instrument set cannot beat the 1x hold in this world
Baselines on selection seed 1 (P = 600): ON hold1 0.069, best constant level 0.042 (L = 1); OFF hold1 0.070, best
constant 0.037 (L = 0.5). The level-L portfolio earns cash (max(rf - 2%, 0) after 15.4% tax) plus L times the index
excess minus product costs; at central premium 2.5-3.7% and vol 17% the frictional drag is about 2-2.5%/yr versus the
1x hold. Oracle diagnostics (NOT rules; exposure computed from the simulator's TRUE mu_t and sigma_t, seed 1):
| diagnostic | ON | OFF |
|---|---|---|
| untracked oracle mu_t/sigma_t^2, best fraction (1.5) | 0.0619 | 0.0407 |
| tracked oracle (see section 4), fraction 1.0 | 0.0623 | 0.0536 |
| tracked static oracle (true per-path mu_bar, sigma_bar) | 0.0547 | 0.0536 |
| tracked partial oracle: true sigma_t only | 0.0495 | - |
| tracked partial oracle: true mu_t only | 0.0528 | - |
| tracked partial oracle: true carry drift only | 0.0578 | - |
| same-basis 1x hold | 0.0683 | 0.0698 |
Even a rule that knew the true drift and volatility every day stays below the 1x hold. **G-ON (beat the 1x hold) is
infeasible in the FCCL world under the anchored priors**; I did not change the priors to make it feasible.
The partial oracles also show what the mechanism is worth if known exactly: volatility timing is worth LESS than nothing
(the premium rises with risk when capital is scarce: beta, b), the carry channel about +0.3 pp.

## 3. Variant search (selection seeds 1, 2, 3, 5 only). N = 146 rule variants evaluated
Every evaluation is one rule configuration on one selection seed, mechanism ON and OFF on the same paths.
Full list with numbers: `work/variants_table.md` (generated from `work/variants.jsonl`), plus 12 tracked-constant
configurations in `work/g6.out` (seed 3). Breakdown:
| stage | what | N |
|---|---|---|
| s1 (seed 1, P=600) | vol-scaled fractional Kelly with funding hurdle: f x hv x p grid | 18 |
| s2 (seed 1, P=600) | same, hv up to 250, p 1.0/1.5/2.0 | 32 |
| s3 (seed 1, P=1200) | refinements, abs-vol estimator, cap Lmax | 11 |
| s4 (seed 1, P=1200) | theory tilts: carry (term spread), capital ledger, rate trend, online premium | 14 |
| s5 (seed 1, P=2000) | tilts re-run at P=2000 | 13 |
| g6 (seed 3, P=1000) | constant exposure with drift tracking, 4 levels x 3 penalties (each world separately) | 12 |
| s7 (seed 1, P=2000) | tracked constants and tracked vol-Kelly | 12 |
| s8 (seed 1, P=2000) | tracked: constant, funding-adjusted, slow vol, carry, ledger | 12 |
| s9 (seed 1, P=2000) | tracked: penalty, smoothed carry | 6 |
| s10 (seed 1, P=2000) | tracked: carry tilt on a constant exposure (no funding term) | 6 |
| s11 (seed 2, P=2000) | confirmation of the top candidates on a second seed | 8 |
| s12 (seed 5, P=2000, 250-day block-resampled worlds) | A (carry tilt) vs B (plain tracked) | 2 |
| total | | 146 |

What was learned (each point is backed by rows in variants_table.md):
1. **Untracked** vol-scaled Kelly rules (s1-s5) beat the best constant level by about +0.2 to +1.0 pp in ON and -0.4 to
   +1.2 pp in OFF. The tracking results below show that most of this came from occasional level changes that re-set the
   drifting 3x/cash mix, not from timing.
2. **Execution, not timing.** The engine does not rebalance while the level is unchanged, so a "constant level" is in fact
   a buy-and-hold of the 3x product and cash; the 3x share decays (volatility drag of the 3x product) and the exposure
   drifts. Tracking the effective exposure (replicating the engine's position inside the rule and changing level only when
   that clearly helps) raised a constant exposure of 1.25-1.5 to about 0.054-0.056 ON and 0.048-0.050 OFF, i.e. +1.0 to
   +1.3 pp over the best constant level in BOTH worlds (g6, s7, s8).
3. With tracking, every timing component LOST against the tracked constant: volatility scaling (p = 1, 1.5, 2; 60- or
   500-day estimates) -0.3 to -1.2 pp in ON, about -0.4 to +0.1 pp in OFF; capital-ledger tilt (contrarian, q = 1, 2) -0.2
   to -0.5 pp in ON, about 0 in OFF; funding-hurdle adjustment k(rf) -0.15 to -0.3 pp in both worlds; online premium
   estimation already hurt untracked (-0.3 to -0.6 pp ON, -0.1 to -0.5 pp OFF).
4. The term-spread carry tilt was the only theory component with a gain: smoothed (120-day) spread, +0.18 exposure per
   1 pp of spread above 1%: ON +0.10 (seed 1) / +0.03 (seed 2), OFF +0.06 / +0.07 over the tracked constant 1.25 - inside
   the noise (paired median differences about +-0.1 pp at P = 2000). In 250-day block-resampled worlds (the construction of
   the headline test) it lost: seed 5 ON -0.05, OFF -0.05.

Selection procedure. Objective on selection seeds: the median CAGR in ON and in OFF against the best constant level of
the same world (the brief's fallback criterion: lose least against the best constant level in both worlds), ties broken
toward fewer parameters. First choice (11:45Z): candidate A = tracked exposure 1.25 + carry tilt (4 parameters:
E0 1.25, TILT 0.18/pp, HSM 120 days, THETA 0.35). Its fresh-seed robustness row in a block-resampled OFF world (seed
10003) showed it 0.37 pp below the plain tracked exposure. That fresh-seed observation triggered the selection-seed check
s12 (seed 5, block worlds), which confirmed that the tilt does not help there (-0.05 ON and OFF). Because the carry gain was
inside the noise on seeds 1-2 and negative on seed 5, I shipped the simpler rule B and **re-ran every final number on new
fresh seeds 12000-12003** that had never been used. Disclosure: seeds 10000-10003 were looked at once for candidate A; the
switch to B was decided on selection-seed evidence (s11, s12) plus that flag.

## 4. The shipped rule (rule.py, 2 tunable parameters)
`PARAMS = {'E0': 1.25, 'THETA': 0.35}`, `INPUTS = ('close', 'rf')`.
- Desired exposure D = E0 = 1.25 (0 while the market is not trading: activity indicator from non-zero returns, 20-day
  half-life). 1.25 is also close to the prior's fractional-Kelly value mu0/sigma0^2 = 0.035/0.17^2 = 1.21.
- The rule replicates the engine's executed position: decision -> trade two closes later, levels in 0.5 steps, trade only
  when the target moves by >= 0.5, the 3x/cash mix drifting with 3r - 2rf - 2.45%/yr and max(rf - 2%, 0) x 0.846. At each
  close it compares the effective exposure if it keeps the level with the exposure of each reachable level plus a penalty
  THETA = 0.35, and keeps or changes the level accordingly. About 0.4 level changes per year.
- Fixed constants (not tuned): engine constants above, warm-up 300 columns, delay 2, level grid 0..3.
- Checks: P = 500, T = 10000 in 2.1 s; inputs not modified; causal (changing data after t leaves targets <= t
  unchanged); invariant to rescaling `close`; NaN / zero / flat stretches -> cash; NaN rf -> 0; imports numpy and math only.

How it follows from the theory: FCCL says the price of risk is high exactly when intermediary capital is scarce and
volatility is high, and that monetary regimes act through a slow ledger. Under the wide prior on how the premium scales
with risk (beta in [0, 2]) the expected Kelly exposure does not fall with volatility, so a trader who does not know the
market in front of him should not time volatility; the carry signal is real in the model but too weak to pay for its noise
and costs. What the theory leaves is a constant growth-oriented exposure; executing it without exposure drift is the only
part that pays. **Plainly: the FCCL mechanism added no tradeable edge after costs.** The margin over the best constant level
is an execution effect that is the same with the mechanism ON or OFF.

## 5. Design gates (fresh seed 12000, P = 2000 per world)
| world | rule | same-basis 1x hold | 2x hold | 3x hold | best constant level (L) | rule - best constant | rule - 1x hold | gate |
|---|---|---|---|---|---|---|---|---|
| mechanism ON | **0.0542** | 0.0682 | 0.0467 | 0.0318 | 0.0420 (L = 1.0) | +0.0122 | -0.0140 | **G-ON FAIL** (beats best constant, not 1x hold) |
| mechanism OFF | **0.0485** | 0.0659 | 0.0382 | 0.0036 | 0.0374 (L = 0.5) | +0.0111 | -0.0174 | **G-OFF PASS** (loss -1.11 pp, i.e. a gain) |
Constant levels (ON): 0.5: 0.0398, 1.0: 0.0420, 1.5: 0.0406, 2.0: 0.0379, 2.5: 0.0330, 3.0: 0.0318.
Constant levels (OFF): 0.5: 0.0374, 1.0: 0.0372, 1.5: 0.0337, 2.0: 0.0290, 2.5: 0.0175, 3.0: 0.0036.
Rule details ON: p10 -0.0275, p90 0.118, P(MDD <= -80%) 0.23, median MDD -0.57, median nominal level 1.16 (effective
exposure about 1.25), 0.37 trades/yr. OFF: p10 -0.0233, p90 0.125, P(MDD <= -80%) 0.16, median MDD -0.58, level 1.23.
Reference (not shipped) candidate A with carry tilt on the same seeds: ON 0.0545, OFF 0.0495.

## 6. Robustness (fresh seeds 12000-12003)
| row | ON rule | ON best const | ON 1x hold | OFF rule | OFF best const | OFF 1x hold |
|---|---|---|---|---|---|---|
| base (seed 12000, P=2000) | 0.0542 | 0.0420 | 0.0682 | 0.0485 | 0.0374 | 0.0659 |
| delay 3 | 0.0542 | | | 0.0484 | | |
| delay 5 | 0.0542 | | | 0.0488 | | |
| cost 0.006 | 0.0530 | | | 0.0476 | | |
| prior narrowed x0.5 (12001, P=1000) | 0.0531 | 0.0371 | 0.0687 | 0.0493 | 0.0328 | 0.0658 |
| prior widened x1.5 (12002, P=1000) | 0.0494 | 0.0434 | 0.0642 | 0.0472 | 0.0408 | 0.0647 |
| 250-day block-resampled 60-y synthetic history (12003, P=1000) | 0.0545 | 0.0458 | 0.0707 | 0.0499 | 0.0400 | 0.0680 |
(constant-level baselines are not re-run under delay / cost; the hold does not depend on them.)
The rule is insensitive to delay (it trades rarely) and loses 0.1 pp at double cost. It beats the best constant level in
every row and never beats the 1x hold. Candidate A (carry tilt) for comparison: narrowed ON 0.0555 / OFF 0.0485, widened
0.0515 / 0.0464, block 0.0543 / 0.0477.

## 7. Mechanism-off world
Same per-path mu_bar, sigma_bar, Student-t shocks and rates paths; i.i.d. returns (THEORY.md section 7). The rule is the
same constant tracked exposure in both worlds, so its OFF result differs from ON only through the market: +1.1 pp over
the best constant level, -1.7 pp versus the 1x hold.

## 8. Concerns and honest limits
- The rule's advantage over constant levels is execution only (re-setting the drifting 3x/cash mix); any rule that tracks
  its effective exposure would get it. It is not evidence for FCCL.
- The rule replicates the engine's constants (fees, cash spread, tax rate on interest, delay 2, warm-up 300). If the real
  engine differs, the tracking is approximate (delay 3 and 5 rows show it is not sensitive to the delay).
- E0 = 1.25 is tuned to the anchored prior (price-index premium centre 2.5%, total-return markets 6%, vol 17%). In a
  market with a lower premium or higher vol than the prior centre the exposure is too high; the widened-prior row shows
  the rule still above the best constant level but by less (+0.6 pp).
- Exposure 1.25 through a 3x product has deeper drawdowns than the 1x hold (P(MDD <= -80%) 0.23 vs 0.15 ON).
- The user's hoped-for 30%/yr is far outside what this theory and these anchors allow (1x hold median about 6.8%).
