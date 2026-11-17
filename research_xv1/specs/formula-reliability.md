# Designer lens: formula-reliability

Ideas only; written without running market data. Rules are quoted as the designer wrote them.

## 1. REL-SCREEN: counted chart grammar, reliability graded on DESIGN blocks, fail-closed idle-cash overlay

**family**: Owner direction (b): mechanical formula search with out-of-sample reliability (searched, multiplicity-controlled)

**exact_rule**: 1. SERIES at close t. X = SOXX adjusted close (returns of the Ken French 48-industry Chips series spliced before SOXX's first day). Q = QQQ (Nasdaq-100 index before 1999-03). rho = X/Q. Sector set = XLB XLE XLF XLI XLK XLP XLU XLV XLY (the 12 Ken French industries until the SPDRs have 200 days). sig20, sig120 = annualised standard deviation of daily log returns.
2. STATES (20), computed for U in {X, Q}: Trend (2): hysteresis flag, on when C > 1.02*SMA200, off when C < 0.98*SMA200; and its negation. High (3): C/Hi252 >= 0.92; 0.80 to 0.92; < 0.80. Pullback (3): d = ln(C/Hi63), s = sig120*sqrt(21/252): d > -1.0s; -2.5s < d <= -1.0s; d <= -2.5s. Momentum (4): sign(C - C[t-126]) crossed with sign(C - C[t-21]). Volatility (3): sig20/sig120 < 0.8; 0.8 to 1.25; > 1.25. Relative strength (2, shared): rho > SMA100(rho); else. Breadth (3, shared): share of sectors above their own SMA200 >= 2/3; between; <= 1/3.
3. FORMULAS. One state, or the AND of two states from different families: 20 + 170 = 190 per underlying, 380 formula-states. Counted tests N = 570 in three classes: LX (hold semis when an X-formula is on), LQ (add Nasdaq exposure when a Q-formula is on), SQ (hold PSQ when a Q-formula is on). N is fixed before any return is read.
4. EMULATION. A formula's state is debounced: it switches after 3 consecutive closes. The position for return day tau is the state at tau-3 (decision at close t, trade at close t+2, the engine's convention). Cost 0.003 per unit of position change. LX and LQ edge on day tau = (position - mean position in that block) * 1x underlying return - cost (within-block exposure-matched, so an always-long formula scores 0). SQ edge = position * PSQ return - cost, counted only on days when unmodified v1 is at level 0.
5. RELIABILITY. T = mean edge / Newey-West(21) standard error over scored DESIGN days (first 63 days of each block dropped). c = number of design blocks with positive mean edge among blocks with at least 30 on-days and 30 off-days.
6. SELECTION. FWER set: stationary bootstrap (mean block 63 days, resampled inside each design block, same indices for all 570 tests, 5,000 draws, recentred); keep a formula if its Romano-Wolf step-down adjusted p <= 0.10 and c >= 6 of 7 (at least 5 eligible blocks). SOFT set: per class the top 19 of 190 by T with c >= 5, tradable only if the class passes a leave-one-design-block-out gate: for each design block k rebuild the top 19 on the other six blocks and measure its mean edge E_k on block k; require mean(E_k)/(sd(E_k)/sqrt(7)) >= 2.75 (one-sided 0.05/3, 6 degrees of freedom), E_k > 0 in at least 5 of 7 folds, and a positive Spearman correlation between the six-block T and the block-k edge in at least 5 of 7 folds. Mode-0 sanity: the kept LX or LQ set must have a positive pooled 1x return on design days when v1's level is 1 or lower, otherwise that leg is off. If every leg is off the candidate equals v1: stop, record the maximum T and the bootstrap quantiles, run nothing on WEAK.
7. COMBINATION. Inside a class, cluster kept formulas whose design-day states correlate above 0.9 and keep the best T per cluster. Vote v = share of kept formulas that are on.
8. VEHICLES AND WEIGHTS (fractions of the account). tier(v) = 1 if v >= 2/3; 0.5 if 1/3 <= v < 2/3; else 0. Semis weight = w_max * tier(v_LX); vehicle SOXL if sig20(X) < 0.30, USD if 0.30 to 0.45, SOXX if >= 0.45 (vehicle changes only after the boundary is crossed by 0.03). Nasdaq weight = w_max * tier(v_LQ); QLD if sig20(Q) < 0.30, else QQQ. PSQ weight = w_max * tier(v_SQ), only when v1 is at level 0 and both long weights are 0. In mode 0 the sum is limited to v1's idle cash and scaled pro rata. Before fund inception: synthetic daily L*r - (L-1)*bill - 0.95%/yr (PSQ: -r + bill - 0.95%/yr), the way the harness builds TQQQ.
9. WEAK GATE (once). (a) Spearman(T on design, T on weak) over the 190 formulas of each traded class >= +0.15, circular-shift p <= 0.0167. (b) Design top decile minus bottom decile is positive on weak blocks. (c) Kept set: positive edge in at least 4 of 5 weak blocks and weak edge at least 30% of design edge. (d) Account minus v1 on the five weak blocks: mean >= +1.0 pp/yr, at least 4 blocks >= 0, worst >= -3 pp, paired block-bootstrap p <= 0.05/4, same sign at cost x2 and one extra day of delay.

**instruments**: Signals: SOXX (Chips proxy before 2001-07), QQQ (Nasdaq-100 index before 1999-03), 9 sector SPDRs (French 12 industries before). Traded extras: SOXL, USD, SOXX; QLD, QQQ; PSQ. v1's TQQQ unchanged.

**engine_mode**: v1 unchanged; extras in mode 0 for points P1-P3; mode 1 (extras first) for P4.

**parameter_points**: 4 points. P1: FWER set, legs LX+LQ+SQ, w_max 0.30 per leg. P2: SOFT set, leg LX only, w_max 0.30. P3: SOFT set, legs LX+LQ+SQ, w_max 0.30 per leg. P4: SOFT set, leg LX only, w_max 0.30, mode 1 (measures the cost of displacing v1; the closest in-account version of 'trade SOXL on reliable SOXX signals').

**data_needed_and_start**: All already in the project. Usable from 1986 with proxies: Chips proxy to 2001-07 then SOXX; Nasdaq-100 index then QQQ; French 12 industries for breadth to about 1999-10 then the SPDRs; real USD from 2007-02, SOXL 2010-03, QLD and PSQ 2006-06, synthetic before; 3-month bill; v1's daily level from the locked engine. The evaluator must mask sealed-block returns; indicator look-backs at the start of 2019 and 2025 read sealed-period prices as inputs only.

**nearest_closed_ids**: T23, T28, E11 (mass searches, incl. sector 3x and -1x shapes); T08 (votes, bundles); X08 (owner's graded formulas); E07 (SOXL and other 3x funds); X41 (QLD, PSQ by state); T15 (breadth); T32 (SMH/QQQ)

**main_failure_mode**: Empty selected set. If not empty: the kept formulas are trend states that are almost never on while v1 is idle, so the overlay is inert; three of the seven design blocks are post-2012 semiconductor bull markets and can dominate T while all weak blocks are 2012 or earlier; losses on extras deepen the ACCOUNT drawdown, so the brake cuts v1 later (hidden dilution even in mode 0).

**own_probability_to_pass_pct**: 3

## 2. AGREE-4 SOXL: semiconductor unanimity overlay in v1's idle cash (fixed rule, nothing searched)

**family**: Owner direction (b), fixed high-agreement rule: SOXX conditions -> SOXL/USD/SOXX, non-dilutive

**exact_rule**: SERIES at close t: X = SOXX adjusted close (Chips proxy before 2001-07); Q = Nasdaq-100; rho = X/Q; sector set = 9 sector SPDRs (French 12 industries before the SPDRs have 200 days); sig20, sig120 = annualised standard deviation of daily log returns of X.
FOUR CONDITIONS: a1 semis trend = hysteresis flag on X (on when X > 1.02*SMA200, off when X < 0.98*SMA200). a2 leadership = rho > SMA100(rho). a3 breadth = at least 2/3 of the sector series above their own SMA200. a4 calm = sig20(X) <= 1.25*sig120(X). K = a1+a2+a3+a4.
STATE: ON when K = 4 on three consecutive closes. OFF when a1 = 0, or when K <= 2 on three consecutive closes. Otherwise unchanged.
WEIGHT: when ON, target w_max of the account, limited to the cash v1 leaves idle (mode 0), cut when v1 needs it back; 0 when OFF.
VEHICLE: SOXL if sig20(X) < 0.30; USD if 0.30 to 0.45; SOXX if >= 0.45; the vehicle changes only after the boundary is crossed by 0.03.
v1 runs unchanged.
DESIGN-STAGE GO/NO-GO (no tuning afterwards): on design days when v1's level is 1 or lower, the mean net 1x SOXX return must be non-decreasing across K <= 2, K = 3, K = 4; it must be positive for K = 4 in at least 4 of the design blocks where K = 4 and idle cash coincide on 20 or more days; and the ON state must form at least 8 separate episodes in DESIGN. Otherwise stop.
WEAK GATE: account minus v1 on the five weak blocks: mean >= +1.0 pp/yr, at least 4 blocks >= 0, worst >= -3 pp, paired block-bootstrap p <= 0.05/5, same sign at cost x2 and one extra day of delay.

**instruments**: Signals: SOXX (Chips proxy before 2001-07), Nasdaq-100, 9 sector SPDRs (French 12 industries before). Traded extras: SOXL, USD, SOXX. v1's TQQQ unchanged.

**engine_mode**: v1 unchanged + extras in mode 0 (non-dilutive).

**parameter_points**: 5 points. B1: w_max 0.30, vehicle ladder. B2: w_max 0.60, ladder. B3: w_max 0.30, SOXX 1x only (separates information from leverage). B4: w_max 0.30, ladder, ON at K >= 3 (if agreement measures reliability, edge per day on must be lower than B1). B5: w_max 0.30, ladder, allowed only when v1's base signal is 1 because of the 10-year-yield caution flag while its Nasdaq trend flag is up (isolates the mechanism; excludes level-0 and brake states).

**data_needed_and_start**: All in the project. From 1986 with proxies (Chips, French 12 industries); real SOXX 2001-07, SPDRs 1998-12, USD 2007-02, SOXL 2010-03; v1's daily level and its caution flag from the locked engine.

**nearest_closed_ids**: E07 (SOXL in place of TQQQ), E03 (idle-cash fills), X41 (QQQ/SPY/QLD fills by state), T32 (SMH/QQQ divergence), T15 (breadth), T13 and AG2 (semiconductor bottom buying)

**main_failure_mode**: A crash from a calm, unanimous uptrend inside the caution state (1987 is in a WEAK block and the t+2 delay rules out a timely exit). Only about 10-12 episodes in 40 years, so the block bootstrap is unlikely to reach Bonferroni significance. Overlay losses raise the account drawdown and trigger the brake on v1. Short holding periods realise taxable gains.

**own_probability_to_pass_pct**: 3

## 3. QQQ-AGREE: unanimity lift of v1's caution tier plus slow-bear PSQ

**family**: Owner direction (b), QQQ leg: QQQ conditions -> TQQQ level; inverse by state

**exact_rule**: SERIES at close t: Q = Nasdaq-100 (QQQ); X = SOXX (Chips proxy before 2001-07); rho = X/Q; sector set as in the other candidates; sig20, sig120 on Q.
SIX CONDITIONS on Q: b1 trend = hysteresis flag (on when Q > 1.02*SMA200, off when Q < 0.98*SMA200). b2 near high = Q >= 0.92*Hi252. b3 momentum = Q > Q[t-126] and Q > Q[t-21]. b4 calm = sig20 <= 1.25*sig120. b5 breadth = at least 2/3 of sectors above their SMA200. b6 semis leading = rho > SMA100(rho). K_Q = sum.
ADD (modified base level): if v1's base signal equals 1 solely because of the caution flag (10-year yield up more than 1 pp in 6 months, with 20-day volatility <= 0.40 and the trend gate not off) and K_Q = 6 on three consecutive closes, set the base level to L_add. Return to v1's own level when K_Q <= 4 on three consecutive closes or b1 = 0. The brake rx.av23s (s = 0.85) is applied on top, unchanged.
PSQ (extra, mode 0): when v1's level is 0 AND b1 has been off for at least 42 consecutive closes AND Q < 0.80*Hi252 AND Q < Q[t-126] AND rho < SMA100(rho), hold PSQ at weight w_S. Exit when v1's level is above 0, or b1 turns on, or Q > Q[t-21] on 5 consecutive closes.
DESIGN-STAGE GO/NO-GO: ADD needs at least 6 episodes in DESIGN, mean Nasdaq return on caution-tier days non-decreasing in K_Q (<= 4, 5, 6) and positive at K_Q = 6 in at least 4 design blocks. PSQ needs at least 4 episodes and a positive pooled net PSQ return. A leg that fails is dropped.
WEAK GATE: account minus v1 on the five weak blocks: mean >= +1.0 pp/yr, at least 4 blocks >= 0, worst >= -3 pp, paired block-bootstrap p <= 0.05/4, same sign at cost x2 and one extra day of delay.

**instruments**: Signals: Nasdaq-100/QQQ, SOXX (Chips proxy before), sector SPDRs (French 12 industries before). Traded: TQQQ through v1's level; PSQ as an extra.

**engine_mode**: v1 with a modified base level (ADD); PSQ as an extra in mode 0.

**parameter_points**: 4 points. C1: ADD with L_add = 2. C2: ADD with L_add = 3. C3: PSQ only, w_S = 0.30. C4: ADD with L_add = 2 plus PSQ at 0.30.

**data_needed_and_start**: All in the project. From 1986; real PSQ from 2006-06, synthetic before (-r + bill - 0.95%/yr); v1's level and caution flag from the locked engine.

**nearest_closed_ids**: T01 and X10 (v1 variants), T03 (macro alarms), X41 (QLD mid-step, PSQ in the cash state), T33/T38/T40 (earlier attempts to raise v1 from 1x or cash), T23 (shapes with -1x), X32 (long/inverse accuracy map)

**main_failure_mode**: It overrides the one part of v1 that is known to carry information. October 1987 (WEAK block). PSQ losses in bear-market rallies (2001 spring and autumn, early 2009) and after late entries. Too few episodes for significance.

**own_probability_to_pass_pct**: 2

## 4. PURE-LADDER: SOXX/QQQ agreement ladder choosing 3x, 2x, 1x, inverse or cash, v1 switched off (the owner's literal proposal)

**family**: Owner direction (b), stand-alone method: SOXX signals -> SOXL, QQQ signals -> TQQQ, inverse/2x/1x by state

**exact_rule**: SERIES at close t: X = SOXX (Chips proxy before 2001-07), Q = Nasdaq-100/QQQ, rho = X/Q, sector set as in the other candidates.
K_X (0 to 6) = semis trend flag (hysteresis 1.02/0.98 around SMA200 of X) + [rho > SMA100(rho)] + [at least 2/3 of sectors above SMA200] + [sig20(X) <= 1.25*sig120(X)] + [X > X[t-126] and X > X[t-21]] + [X >= 0.92*Hi252(X)].
K_Q (0 to 6) = Nasdaq trend flag (same hysteresis on Q) + [Q >= 0.92*Hi252] + [Q > Q[t-126] and Q > Q[t-21]] + [sig20(Q) <= 1.25*sig120(Q)] + [at least 2/3 of sectors above SMA200] + [rho > SMA100(rho)].
Each close, the target is one rung (a rung change needs 3 consecutive closes):
1. K_X = 6: 100% semis vehicle: SOXL if sig20(X) < 0.30, USD if 0.30 to 0.45, SOXX if >= 0.45.
2. else K_Q >= 5: 100% Nasdaq vehicle: TQQQ if sig20(Q) < 0.25, QLD if 0.25 to 0.35, QQQ if >= 0.35.
3. else K_Q is 3 or 4: 100% QQQ.
4. else bear unanimity (Nasdaq trend flag off for at least 42 closes, Q < 0.80*Hi252, Q < Q[t-126], rho < SMA100(rho)): 50% PSQ, 50% cash.
5. else cash.
No v1 signal and no brake.
GO/NO-GO before WEAK: on DESIGN blocks the account must be at or above v1 in at least 5 of 7 blocks, including one of the two bear blocks (2001-03, 2007-09). WEAK gate: account minus v1 on the five weak blocks: mean >= +1.0 pp/yr, at least 4 blocks >= 0, paired block-bootstrap p <= 0.05/3, same sign at cost x2 and one extra day of delay.

**instruments**: SOXL, USD, SOXX, TQQQ, QLD, QQQ, PSQ, cash. Signals: SOXX (Chips proxy before), Nasdaq-100/QQQ, sector SPDRs (French 12 industries before).

**engine_mode**: v1 switched off entirely (pure new method); one instrument at a time.

**parameter_points**: 3 points. E1: full ladder. E2: SOXX only (rungs 1 and 5: the literal 'reliable SOXX signals -> SOXL'). E3: QQQ only (rungs 2 to 5).

**data_needed_and_start**: All in the project. From 1986 with proxies; real QLD and PSQ 2006-06, USD 2007-02, TQQQ and SOXL 2010, synthetic before.

**nearest_closed_ids**: E01 (sector and 3x rotation), E07 (0 of 142), E12 (leading sectors at 3x: 3.2% vs 16.2%), T43 (volatility-scaled trend ladder: 8.3% vs 16.2%), X32 (accuracy map), T23 (exposure shapes with 3/2/1/-1x), AG2

**main_failure_mode**: Compounding loss and whipsaw in 3x vehicles; full 3x exposure into October 1987 and the 2000 and 2008 turns with a t+2 delay; no macro alarms.

**own_probability_to_pass_pct**: 1
