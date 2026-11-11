# Designer lens: v1-weak-states

Ideas only; written without running market data. Rules are quoted as the designer wrote them.

## 1. FCR: fast-crash floor (hold 1x instead of cash when the gate fires within 30 trading days of a 252-day high)

**family**: v1 base-level change: gate graded by the speed of the break (V-shaped re-entry and confidence-weighted intermediate level in one rule)

**exact_rule**: All v1 signals are unchanged: OFF state machine, volatility cap, caution cap, brake. At the first day g of each OFF episode (OFF_g true, OFF_{g-1} false): H = max close of the Nasdaq-100 over days g-251..g, h = the last day in that window with close = H, a = g - h in trading days. The episode is FAST if a <= A. While OFF and FAST, the base level is 1.0 instead of 0. When v1's own OFF ends (close > 1.02 x SMA200, or the macro flag clears), v1's normal level resumes. SLOW episodes (a > A) are exactly v1. Optional demotion (point P3): if close < (1 - D) x H at any day of a FAST episode, the level is 0 for the rest of that episode. Optional upgrade (point P4): in a FAST episode, from day g+10 on, while close > SMA50 the level is v1's ungated level (3, or 1 under the volatility or caution cap); it returns to the 1.0 floor if close < 0.97 x SMA50. Decisions at close t are traded at t+2 like everything else.

**instruments**: TQQQ and cash only. Level 1 is one-third TQQQ, the same as v1's own 1x state.

**engine_mode**: v1 running with a modified base level; brake rx.av23s (s = 0.85) unchanged on top; no extra instruments, so modes 0 and 1 are not used.

**parameter_points**: Four points, primary fixed in advance. P1 (primary): A = 30, no demotion, no upgrade. P2: A = 21. P3: A = 30 with depth demotion D = 0.35. P4: A = 30 with the SMA50 upgrade. Pass rule: P1 must be positive, and at least two of P2 to P4 must have the same sign on the design blocks.

**data_needed_and_start**: Already in the project: Nasdaq-100 daily index (1985) and the 10-year and 3-month yields v1 already uses. Testable on every block from 1986.

**nearest_closed_ids**: T01, T12, T13, T40 (crash and bottom adds); X10 (asymmetric re-entry); the unconditional off-level 'offlev' in rx.rgen. idea_check verdict: auto-reject (matched T33 and T01).

**main_failure_mode**: A fast break that starts a long bear (Japan 1990 type: break within 30 days of the high, then about -48%). The floor then holds 1x through the whole OFF episode, a loss of 30 to 40% of the account where v1 loses nothing; one such miss erases all five gains. Gains sit in only four or five blocks, so the paired block bootstrap is unlikely to clear Bonferroni over four points. Cheap kill test before any account run: on the S&P 500 from 1928 and the 13 holdout ETFs (data to 2014 plus design years only), take every first close below 0.98 x SMA200 within 30 days of a 252-day high and compare the index at the next close above 1.02 x SMA200 with the index two days after the break. Kill if the median ratio is 1.00 or lower, or if more than one episode in four ends below 0.80.

**own_probability_to_pass_pct**: 5

## 2. PGC: brief post-gain cut (owner direction c, registered as a kill test)

**family**: v1 extra cap signal: temporary cut of the 3x share right after a large run-up

**exact_rule**: G_t = close_t / close_{t-63} - 1 on the Nasdaq-100. If G_t >= g, no cut is active, and at least 63 trading days have passed since the last cut ended, a cut starts at t and lasts K decision days (t to t+K-1). During a cut the level is min(v1 level, c). Everything else is v1. Level 2 is two-thirds TQQQ; level 1 is one-third TQQQ. The proceeds stay in cash and are not moved to safe assets, which the owner already tested (-1.0 to -4.4pp/yr).

**instruments**: TQQQ and cash only.

**engine_mode**: v1 running with an extra cap signal; brake unchanged; no extra instruments.

**parameter_points**: Five points. P1 (primary): g = 0.30, c = 1, K = 21. P2: g = 0.30, c = 2, K = 21. P3: g = 0.30, c = 1, K = 42. P4: g = 0.25, c = 1, K = 21. P5: trigger on the 126-day return >= 0.50 instead, with c = 1 and K = 21.

**data_needed_and_start**: Already in the project: Nasdaq-100 daily index. Testable on every block from 1986.

**nearest_closed_ids**: L03 (lock-in, -2 to -7pp), M04 (ratchet, -36.4 to 12.2), T27 (overbought exits, path -0.4 to 2.3%), T26. idea_check verdict: auto-reject (matched L03 and L04).

**main_failure_mode**: Momentum continues after large 63-day gains, and each cut realises gains. Kill test on design blocks only: sum the log-growth difference between the capped and uncapped level over all cut windows. If the sum is zero or negative before tax, close the idea and record it under L03.

**own_probability_to_pass_pct**: 1.5
