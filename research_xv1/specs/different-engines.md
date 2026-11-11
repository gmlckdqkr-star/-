# Designer lens: different-engines

Ideas only; written without running market data. Rules are quoted as the designer wrote them.

## 1. MIDTERM-ADD: from October of a US midterm-election year to June of the next year, idle cash is put into the 3x fund even when v1 is off

**family**: Calendar (4-year US presidential cycle) used as a non-dilutive add. Registry family M01 / T04.

**exact_rule**: v1 runs unchanged and has priority (mode 0).

Definitions
- Midterm year Y: Y mod 4 = 2 (1986, 1990, ..., 2022, 2026).
- Window W(Y): every trading day from the first trading day of October of Y to the last trading day of June of Y+1, inclusive.
- vol20(t): v1's own 20-day annualised realised volatility of Nasdaq-100 daily returns at close t (the series behind v1's 40% cap).
- L_v1(t): the level v1 actually holds after its brake (0..3).

Rule
- Calendar level C(t) = 3 if vol20(t) <= 0.40, else 1, on days whose execution day (t+2) lies in W(Y). Otherwise C(t) = 0.
- Extra target weight in the 3x Nasdaq fund: x(t) = phi * max(0, C(t) - L_v1(t)) / 3.
- With phi = 1 the account's total exposure inside the window is max(L_v1, C). The calendar suspends the trend-and-macro gate, the 10-year-yield caution cap and the account-drawdown brake. The 40% volatility cap stays.
- Outside the window x = 0 and the account is exactly v1.

Execution
- Same as v1: target from close t filled at t+2, 0.3% per side, 22% tax.
- The calendar is known in advance, so the entry target is issued at the close two trading days before the first window day, and x = 0 is issued two trading days before the first trading day of July.
- The extra uses v1's 0.5-level order grid: trade only when x changes by at least 1/6 of the account or goes to zero.
- When v1 raises its own 3x weight while the extra holds the same fund, shares are re-labelled, not sold and re-bought. If the harness cannot net, charge 0.6% on the transferred amount.

Kill tests, run on DESIGN data before anything else (pre-registered)
- K1 phase placebo: the same rule with the window shifted by +1, +2 and +3 years. The true phase must be the best of the four on DESIGN blocks and the mean of the three placebos must be <= 0. Otherwise the gain is only "more exposure in off-states", which is closed (L01, T13).
- K2: no DESIGN block in which the extra was held may be worse than v1 by more than 1pp/yr.
- K3: S&P 500 total return 1954-1985 with a synthetic 3x fund and the project's existing v1-on-S&P run (8 windows): mean paired difference > 0 and at most 2 of 8 windows negative.
- K4: cost x2 and one extra day of delay.

**instruments**: TQQQ (the harness's synthetic 3x Nasdaq-100 series before 2010, the same one v1 uses). Variant P6 uses QLD (2x; synthetic before 2006). No other instrument.

**engine_mode**: Mode 0. v1 unchanged and with priority. The extra uses only cash v1 leaves idle and is cut whenever v1 needs it back.

**parameter_points**: Six points, P1 is the primary; Bonferroni over 6.
- P1: window October to June, vol cap kept (C = 3 or 1), phi = 1, TQQQ.
- P2: as P1 but no vol cap (C = 3 always).
- P3: as P1 but the window starts on the first trading day after Election Day (the Tuesday after the first Monday of November).
- P4: as P1 with phi = 0.5.
- P5: as P1 but the window ends on the last trading day of April.
- P6: as P1 but the extra instrument is QLD with the same weight formula (two thirds of the added exposure).

**data_needed_and_start**: Everything is already in the project; nothing to download.
- Nasdaq-100 daily closes (1985) and the harness's 3x and 2x Nasdaq series (TQQQ 2010, QLD 2006, synthetic before).
- v1's vol20 and held-level series.
- S&P 500 total return (1928) and the 3-month bill for kill test K3.
- Election Day is computed by rule; no data file.
First window is October 1986. The last window inside the data is October 2022 to June 2023; the 2026 window starts after the data end.

**nearest_closed_ids**: M01 (midterm-year Q2-Q3 cash: 48 phases, rank 1 p = .021 "information exists", path 15.7 (-0.5), real 14.4 (-16.6); reopen "when a combining structure exists that does not reduce exposure").
T04 (calendar pieces max +0.46pp; presidential cycle failed multiple testing; reopen none).
T13 and T40 (buying declines: 1 win of 3; capitulation add -0.73pp path, -2.18pp real).
L01 (more exposure).
E03 (idle-cash fills, tie).
idea_check verdict: auto-reject, matched M01.

**main_failure_mode**: 1. Too few events. The gain sits in two DESIGN blocks and one WEAK block, so a block bootstrap with Bonferroni over 6 will most likely call it insignificant, as T04 already did for the presidential cycle.
2. It is bottom-buying on a calendar. It buys 3x while v1's trend-and-macro gate says no and it bypasses the drawdown brake. A window like 1930-31 (index about -35%, 3x about -80% on the idle cash) would put the account deep in drawdown, and the brake would then hold v1 down for years. The share of paths reaching an 80% drawdown rises.
3. Lows often come after the October start (1974, 1978, 1998, 2002 by days to weeks). Under P2 the first weeks can lose 30-45% on the added part.
4. The evidence comes from the blocks that produced the M01 phase result, so the design-block result is not independent confirmation.

**own_probability_to_pass_pct**: 4
