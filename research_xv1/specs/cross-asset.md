# Designer lens: cross-asset

Ideas only; written without running market data. Rules are quoted as the designer wrote them.

## 1. SBC-CAP: rate-shock cap conditional on the stock-bond correlation sign

**family**: v1 level modification (alarm precision). Closed families T03 / X10 (C3 variants).

**exact_rule**: Inputs at close t, all causal:
- q_s = ln(NDX_s / NDX_{s-1}).
- b_s = -(Y10_s - Y10_{s-1}), where Y10 is the daily 10-year constant-maturity yield, forward-filled on bond holidays. This is a sign-correct proxy for the daily 10-year Treasury price return.
- rho_t = Pearson correlation of (q_s, b_s) over the last N trading days ending at t. N = 252, at least 200 pairs required.
- Regime with hysteresis: NEG_t = 1 if rho_t < -0.05; NEG_t = 0 if rho_t > +0.05; otherwise NEG_t = NEG_{t-1}. Start with NEG = 0.

v1's base signal stays fam4(L_on=3, vcap=0.40, vlev=1, caution=shock6m, Lc=1). Only the caution line changes:
- shock6m_t = 1 and NEG_t = 0: B = min(B, 1), exactly as v1.
- shock6m_t = 1 and NEG_t = 1: B = min(B, Lr), with Lr = 3 (cap released).

Unchanged: the volatility cap; the trend gate, which still uses (inversion memory OR shock6m) as its condition, so trend-down plus rate shock still goes to cash; the av23s brake (s = 0.85), fed the unmodified features; the 2-day delay, costs and tax. shock6m is v1's own flag as computed by the locked engine (feature index 8 in bk.FEATS).

**instruments**: TQQQ and cash only, same as v1.

**engine_mode**: v1 with a modified base level (conditional caution cap). No extra instruments. Brake unchanged.

**parameter_points**: P1 (primary): N=252, Lr=3.
P2: N=252, Lr=2 (two-thirds TQQQ).
P3: N=504, Lr=3.
P4: N=126, Lr=3.
P5: P1 plus chip confirmation. Release only if S/NDX is also above its own 200-day average (S = Ken French Chips to 2001-07, SOXX after).
P6 (control, not for adoption): cap removed in every regime. It shows whether the regime gate, rather than plain cap removal, carries the result. If the gate matters, P6 should lose on 1986-88.

**data_needed_and_start**: Nasdaq-100 daily (from 1985) and 10-year yield daily (from 1970). Rule is live from 1986-01 after a 252-day warm-up. P5 also needs Ken French 48-industry Chips daily and SOXX (2001-07). All already in the project.

**nearest_closed_ids**: T03 (macro alarms; recombination counted as a C3 variant and stopped). X10 (C3 structure changes, 0 of 6). T07 (regime detectors). T23 / T28 (correlation-regime atoms inside the mass searches). E09 (CPI predicts the next correlation sign 63% vs 55% base). idea_check verdict: auto-reject, top match E09, then T03.

**main_failure_mode**: 1. Regime lag. A 252-day correlation turns late. An inflation-type shock arriving at the end of a negative-correlation era is taken at 3x until the trend gate or the brake reacts.
2. Weak identification. On design blocks the rule is almost the same as "drop the cap after 1998". Only 1986-88, 1992-94 and early 2025 separate it from the P6 control.
3. A 2004-type episode (front-end-led tightening inside a negative regime) is released and loses, and it sits in a weak block where v1 is already at -3.6.
4. Family-wise correction: C3 variants have already used many tries.

**own_probability_to_pass_pct**: 6

## 2. CHIP-LEAD-12M: SOXL takes a third of the TQQQ slot after a confirmed chip-cycle recovery

**family**: Vehicle choice inside v1's ON state (owner direction b, part of a). Closed families E07 / AG2 / T13.

**exact_rule**: Series: S = semiconductor total-return index, spliced by daily returns (Ken French 48-industry Chips, value-weighted, to 2001-07; SOXX adjusted close after). Q = Nasdaq-100. R = S / Q.

Signals at close t:
- DD_t = 1 if some day u in [t-503, t] has S_u <= (1-D) x max(S over [u-755, u]). In words: a drawdown of at least D from a 3-year high happened within the last 2 years. D = 0.40.
- UP_t, with hysteresis: on when S_t > 1.02 x SMA200(S); off when S_t < 0.98 x SMA200(S).
- LEAD_t: on when R_t > SMA200(R); off after R_t < SMA200(R) on 20 consecutive closes.

Entry: the first close where DD, UP and LEAD are all on, v1's final (post-brake) level is 3, and no cooldown is running.

While active: SOXL weight = a (a = 1/3) and TQQQ weight = 1 - a on every day v1's final level is 3. On any day v1's level is below 3, SOXL weight is 0 and v1 holds its usual mix. SOXL comes back when the level returns to 3 if the window is still active.

The window ends at the first of:
- H = 252 trading days after entry;
- UP off;
- LEAD off;
- trailing stop: S_t <= 0.80 x max(S since entry).
After an end by UP, LEAD or the stop there is a 63-day cooldown. A new entry needs all conditions again.

All decisions at close t are traded at t+2 with the standard cost and tax.

**instruments**: SOXL (before 2010-03, a synthetic daily 3x of S with the harness's standard fee and financing), TQQQ, cash.

**engine_mode**: Mode 1 (the extra has priority), with the extra's weight forced to 0 unless v1's final level is 3. Total leveraged exposure never exceeds v1's.

**parameter_points**: Each point is (D, a, H).
1. (0.40, 1/3, 252), primary.
2. (0.40, 1/2, 252).
3. (0.30, 1/3, 252).
4. (0.50, 1/3, 252).
5. (0.40, 1/3, 504).
6. (0.40, 1/3, 252) without the LEAD condition.

**data_needed_and_start**: Ken French Chips daily (1926 to 2001-07), SOXX (2001-07 on), SOXL (2010-03 on), Nasdaq-100. Rule is live from 1986. All already in the project.

**nearest_closed_ids**: E07 (TQQQ slot given to other 3x funds or rule-based choice: 0 of 142, rule-based -0.8 to -15.9pp). AG2 / T13 (chip bottom-buying, 0 of 8). S25 (bottleneck sectors). E12 (leading sectors at 3x). T32 (chips vs index as a cut signal). E01 (rotation). idea_check verdict: auto-reject.

**main_failure_mode**: 1. SOXL's variance. A -35% chip move inside a window (Oct 1997, 1998, 2004) costs the swapped third about -70% before the 20% trailing stop executes two days later.
2. Two large design wins decide the whole result.
3. Chip leadership over the index in 2016-2026 may be one long sector run, not a repeatable post-crash effect.

**own_probability_to_pass_pct**: 3
