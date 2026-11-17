# Designer lens: extreme-overlay

Ideas only; written without running market data. Rules are quoted as the designer wrote them.

## 1. Fast-crash bridge (drawdown-age key)

**family**: Capitulation ADD with v1's idle cash, restricted to fast crashes from a fresh 3-year high (closed family T40 / T13; sector choice touches E07)

**exact_rule**: Daily at close t. N = Nasdaq-100 close. H = highest N close of the last 756 trading days including t. age = trading days since the most recent day N closed at H. dd = N/H - 1. An episode is the interval between two consecutive days on which N closes at its 756-day high. SIGNAL at t if all hold: dd <= -d; age <= 63; v1 target level after the brake L <= 1; no signal yet in this episode. ACTION: buy instrument X for w x account equity (measured at close t), filled at t+2, then fixed shares. SELL ALL at the first of: (a) v1 base level (bk.C3sig) = 3 at a close; (b) 126 trading days after the signal. The engine's mode-0 cut applies on top. No price stop. No second buy in the same episode. Once age > 63 no buy is possible until N makes a new 756-day high. By construction: the 2001-03 block has zero trades (last 3-year high was 2000-03); in 2007-09 the only eligible window is the 63 days after the 2007-10-31 high; any episode can lose at most w.

**instruments**: X = TQQQ, or SOXL, or LOSER. LOSER = the 3x fund of the sector with the lowest 63-day total return at t among: semiconductors (SOXX -> SOXL), XLF -> FAS, IWM -> TNA, XLK -> TECL, XLE -> ERX (as listed; 2x after 2020-03), IYR -> DRN (from 2000). Before a fund's inception: synthetic daily 3x of the 1x series by the project's standard formula. Before the 1x ETF exists: Ken French Chips, 12-industry Money, BusEq, Enrgy, and the smallest size group.

**engine_mode**: mode 0 (v1 unchanged, v1 has priority)

**parameter_points**: 6 points: X in {TQQQ, SOXL, LOSER} x d in {20%, 25%}, with w = 20%. Fixed: 756-day high window, age limit 63, time stop 126. w = 10% and 30% to be reported as scale lines only, not as extra tries.

**data_needed_and_start**: All in the project. Nasdaq-100 index 1985 (signals from 1988 once 756 days exist; use available history before). TQQQ 2010, SOXL 2010, SOXX 2001, sector SPDRs 1998, IWM/IYR 2000, FAS/TNA/ERX 2008, TECL 2008, DRN 2009, Ken French daily industries and Chips, v1 target and base levels. Account run 1986-2026.

**nearest_closed_ids**: T40 (RSI + volume capitulation ADD: path -0.73 / -0.19 pp), T13 (bottom buying 1 of 3), X10 (asymmetric re-entry), T12, and for the SOXL and LOSER points E07 and S26. idea_check verdict: auto-reject (matched X41/E07/E03 by keyword; true nearest is T40).

**main_failure_mode**: A fast crash that opens a long bear with no rebound inside 126 days (Nikkei February 1990 pattern). Nasdaq April 2000 was close to this and is saved only if v1 itself re-enters in mid-2000 and thereby sells the sleeve. Loss then about 60-70% of w. Second: the paired block test has 3-4 active blocks; after Bonferroni over 6 points a true +1 pp/yr effect will most likely not reach significance. Third: a sleeve loss raises the account drawdown that drives v1's brake.

**own_probability_to_pass_pct**: 5

## 2. SOXL staged crash bridge (owner direction a, non-dilutive form)

**family**: Depth-staged bottom buying of a 3x sector fund with v1's idle cash (closed family T13, AG2 lane)

**exact_rule**: Daily at close t. S = semiconductor 1x total-return level (SOXX adjusted close from its first date; before that chained Ken French 'Chips' daily returns). H = highest S close of the last 756 trading days; dd = S/H - 1. An episode opens on the first day dd <= -d1 after a day S closed at its 756-day high, and ends when S next closes at a 756-day high. Episode budget = B x account equity at the close of the opening day, fixed in currency. TRANCHE k (k = 1,2,3, cost = budget/3 each): signal on the first day in the episode with dd <= -d_k AND v1 target level L <= 1, if the episode is not spent; filled t+2; fixed shares. SELL ALL at the first of: (a) v1 base level = 3 at a close; (b) after SOXL has closed at >= 2.0 x the cost-weighted average fill price, SOXL closes <= 0.65 x its highest close since the first fill; (c) 252 trading days after the first tranche signal. The engine's mode-0 cut applies on top. After any sell-all the episode is spent: no buys until a new episode opens. No price stop. By construction: between two 3-year highs of the chip index at most one budget B is at risk, there is no new 3-year high inside 2000-03 or 2007-09, and exposure ends at most 252 days after the first buy.

**instruments**: SOXL (real from 2010-03; synthetic daily 3x of SOXX 2001-07 to 2010-03 and of the Chips series before). v1's TQQQ unchanged.

**engine_mode**: mode 0 (v1 unchanged, v1 has priority)

**parameter_points**: 6 points: depth set A = (-30, -40, -50)% or set B = (-40, -50, -60)% below the 3-year high, x budget B = 10%, 20%, 30% of the account. Fixed: 756-day window, thirds, 2.0x / 0.65 trailing exit, 252-day time stop.

**data_needed_and_start**: All in the project: SOXX 2001, SOXL 2010, Ken French Chips daily, v1 target and base levels. Account run 1986-2026.

**nearest_closed_ids**: T13 (chip-index bottoms 1 win of 3; 18 variants best 4 of 7), AG2 lane (8 staged 3x-chip rules -3.1..+2.7%/yr alone 1950-2014, all worse when mixed with v1), T40, L03, L04, E03. idea_check verdict: auto-reject, matched T13.

**main_failure_mode**: Grinding bear: tranches are bought far above the low and lose 60-100% of the budget once per bear. At B = 30% a full loss can push the account drawdown past about 53%, where v1's brake starts cutting, so v1 re-enters at roughly 2x instead of 3x. With set B the rule trades in only 3-4 events in 40 years, which cannot be validated.

**own_probability_to_pass_pct**: 2

## 3. Panic-peak bridge (VIX / VIX3M normalisation)

**family**: Volatility term-structure signal used to add risk with v1's idle cash after acute panic ends (closed family T02; related T32, T05)

**exact_rule**: Active from the first date both VIX and VIX3M exist. Daily at close t: R = VIX / VIX3M. Arm day = any day with R >= theta. Episode = interval between two consecutive 756-day closing highs of the Nasdaq-100. SIGNAL at t if all hold: there is an arm day between t-40 and t-3; R <= 1.00 on t, t-1 and t-2; v1 target level L <= 1; no position open; no signal yet in this episode. ACTION: buy X for 20% of account equity at close t, filled t+2, fixed shares. SELL ALL at the first of: (a) v1 base level = 3 at a close; (b) R >= 1.10 at a close; (c) 63 trading days after the signal. Engine's mode-0 cut applies on top. No price stop. At most one loss of 20% per episode by construction.

**instruments**: X = TQQQ or SOXL (synthetic 3x before 2010). Signals: VIX, VIX3M.

**engine_mode**: mode 0 (v1 unchanged, v1 has priority)

**parameter_points**: 4 points: theta in {1.15, 1.25} x X in {TQQQ, SOXL}. Fixed: 3-day normalisation at 1.00, re-inversion exit 1.10, 40-day arm memory, 63-day time stop, size 20%.

**data_needed_and_start**: All in the project: VIX 1990, VIX3M 2006-07, TQQQ/SOXL 2010 plus synthetic, Nasdaq-100, v1 levels. Rule is inactive before VIX3M starts, so blocks before 2007 are identical to v1.

**nearest_closed_ids**: T02 (VIX and VIX/VIX3M timing closed; other 2006+ volatility series closed for lack of sample), T32, T05, T33 (funding-stress ADD: fired when v1 was already 3x). idea_check verdict: auto-reject, matched T02.

**main_failure_mode**: Too little time between the signal and v1's re-entry to matter; or normalisation followed by a second leg down (January to March 2009). Only 4 design blocks and 1 weak block carry any data.

**own_probability_to_pass_pct**: 3

## 4. Hold-to-cycle-top variant (owner's literal wording; dilutive after v1 re-enters)

**family**: Crash entry from idle cash, then the sleeve keeps priority over v1 until a trailing exit (closed families E07 and AG2 carve-out)

**exact_rule**: Entry exactly as the staged candidate with depth set (-40, -50, -60)% below the 756-day high of the chip series, budget 20% of account equity at episode opening, three tranches, each bought only on a day with v1 target level L <= 1. After the first fill the sleeve has priority: it is NOT sold when v1 returns to 3x; v1's fund receives (L/3) x (equity minus sleeve value). SELL ALL at the first of: (a) after the fund has closed at >= 2.0 x the cost-weighted average fill price, it closes <= 0.65 x its highest close since the first fill; (b) 756 trading days after the first tranche signal. No price stop. One budget per episode (episode ends at the next 756-day high of the chip series).

**instruments**: Point 1: SOXL (3x). Point 2: USD (2x semiconductors, real from 2007; synthetic 2x before). v1's TQQQ diluted by the sleeve's current weight.

**engine_mode**: mode 1 for the sleeve once bought (entry still requires idle cash). This is outside the pure mode-0 lens and is listed only so that the owner's 'held to the cycle top' is tested as written.

**parameter_points**: 2 points: SOXL or USD. Everything else fixed.

**data_needed_and_start**: All in the project: SOXX 2001, SOXL 2010, USD 2007, Ken French Chips, v1 levels. Account run 1986-2026.

**nearest_closed_ids**: E07 (replacing part of v1's on-state TQQQ with another 3x fund: -0.8..-15.9 pp), AG2 lane / T13 (30-50% chip sleeve beside v1: 11.1-14.7% vs 16.2%), L03. idea_check verdict: auto-reject, matched E07.

**main_failure_mode**: Same early-entry loss as the staged candidate, plus dilution of v1 in ordinary recoveries where semiconductors do not lead. A 3-year time cap means a failed position bleeds from volatility decay for up to three years.

**own_probability_to_pass_pct**: 1.5
