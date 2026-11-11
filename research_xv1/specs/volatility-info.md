# Designer lens: volatility-info

Ideas only; written without running market data. Rules are quoted as the designer wrote them.

## 1. IVV: equity-IV veto of the yield-shock 1x cap

**family**: IV-conditioned alarm relaxation (re-entry accelerator for v1, lens use i)

**exact_rule**: All inputs are closes up to day t; the harness trades at t+2.
Inputs: VIX close v (1990-01-02+). From the locked v1 engine at t: S_t = shock6m caution flag (macro_cond(('shock6m',)), feat 8), G_t = gate-off state (trend_gate 200d / 2% band with macro_cond(('inv','shock6m'))), vol20_t.
A_t = mean(v[t-20..t]).
Raw veto: D1: raw_t = A_t < k * A_{t-126} (equity IV lower than at the start of the same 6-month window the yield alarm looks at). D2: raw_t = A_t < mean(v[t-251..t]).
Veto state Z_t: starts 0; switches to 1 after raw is true on 5 consecutive closes; back to 0 after raw is false on 5 consecutive closes. Z_t = 0 while fewer than 147 (D1) or 252 (D2) VIX closes exist, so 1986-1990 is identical to v1.
Base level: B'_t = bk.C3sig with the single line 'B = min(B, Lc)' of strat.fam4 skipped on days with Z_t = 1. Equivalently B'_t = 3 if (S_t and not G_t and vol20_t <= 0.40 and Z_t) else B_t. S_t stays inside the gate condition (downtrend + shock still goes to cash) and the vol cap is untouched.
Brake rx.av23s(s=0.85) applied to B' unchanged. No extra instrument.
Controls that must be run alongside (not candidates): N1 = Z always 1 from 1990 (cap removed); N2a, N2b = same rule with the VIX series lagged 504 and 1008 trading days (placebo with the same duty cycle).
Pre-set design-block decision: keep a point only if (a) paired block sum vs v1 is positive, (b) no design block is worse than v1 by more than 1 pp/yr, (c) it beats N1, N2a and N2b. If N1 >= candidate, close it as a T03 C3-variant.

**instruments**: TQQQ and cash only (v1's own fund). No extra instrument.

**engine_mode**: v1 ON with a modified base level (one cap lifted by a causal signal); brake unchanged; no overlay.

**parameter_points**: 3 points: P1 = D1 with k = 1.00; P2 = D1 with k = 0.90; P3 = D2. Fixed everywhere: 21-day mean, 126-day lag (the alarm's own window), 5-day persistence. Controls N1, N2a, N2b are not counted as tries.

**data_needed_and_start**: VIX daily close, in project, 1990-01-02. Rule active from about 1990-08 (D1) or 1991-01 (D2). v1 internal flags from the locked engine. Nothing else.

**nearest_closed_ids**: T03 (macro alarms, recombination = C3 variant, stopped), T02 (VIX as timing signal), X10 (asymmetric re-entry), T33 and T38 (ADD after stress resolves), X43 (parameter neighbours).

**main_failure_mode**: 1) The cap exists for the 1987 pattern: yield shock in an uptrend with calm implied vol, then a crash. VIX starts in 1990, so the harness cannot show whether the veto would have been ON in Aug-Oct 1987; if it was, one day costs about 40 pp more than v1. 2) About even odds that IVV does not beat control N1 on the design blocks (N1 gains in 2013, loses in 1996); then the effect is only 'the cap was too strict after 1990', which is the closed T03 family. 3) Only about 8 pre-sealed episodes: a 4-of-5 design record is weak evidence. 4) The exact shock6m definition may make several of my episodes shorter than assumed.

**own_probability_to_pass_pct**: 5

## 2. PRX-SOXL: SOXL with idle cash after a market panic has resolved and semiconductors are deeply down (owner direction a)

**family**: IV-triggered idle-cash overlay (lens use ii; owner direction a with new handles)

**exact_rule**: Closes up to t; traded at t+2.
v = VIX close. m_t = median(v[t-503..t]); rule inactive until 504 VIX closes exist (from 1992-01).
P_t = max(v[t-62..t]); tau_t = date of that maximum.
PANIC_t = P_t >= 1.75 * m_t.
RES_t = PANIC_t and v_s <= 0.60 * P_t for every s in [t-4, t] (five straight closes at least 40% below the 63-day peak).
X = SOXX total-return close (Ken French 'Chips' before 2001-07). dd_s = X_s / max(X[s-503..s]) - 1. SEMI_t = min(dd[t-62..t]) <= -D.
ENTRY at t: RES_t and SEMI_t and no open sleeve and tau_t later than the last exit. Target SOXL weight = W of account equity (synthetic 3x daily of X before 2010-03, built like the project's synthetic 3x fund).
Funding: mode 0, so the weight is min(W, cash v1 leaves idle) and the harness cuts it whenever v1 needs the cash. With carry = 1 the sleeve switches to mode 1 at entry and keeps up to W until exit.
While open, target = drifted weight (no rebalancing), capped at 0.40 of equity.
EXIT at the first of: E1 X_t <= 0.75 * X_entry; E2 v_t >= 0.85 * P_entry (panic returns); E3 after X has closed above 1.02 * SMA200(X) at least once since entry, the first close below 0.98 * SMA200(X) (the cycle-top exit); E4 756 trading days; E5 (mode 0) the harness cut has taken the sleeve to zero.
One entry per VIX peak. v1 itself unchanged.

**instruments**: SOXL (extra), TQQQ and cash (v1). SOXX and VIX as signals only.

**engine_mode**: v1 unchanged + 1 extra instrument in mode 0 (non-dilutive). One parameter point uses mode 1 after entry to allow the hold to the cycle top.

**parameter_points**: 4 points (D, W, carry): (0.30, 0.15, 0); (0.30, 0.30, 0); (0.40, 0.30, 0); (0.30, 0.15, 1). Fixed: 1.75 x 2-year median, 40% retreat for 5 days, 25% stop on SOXX, 0.85 re-panic, 200d/2% exit.

**data_needed_and_start**: All in project: VIX 1990+, SOXX 2001+, SOXL 2010+, Ken French Chips before 2001. Needs the evaluator's synthetic 3x semiconductor series before 2010-03. Active from 1992-01.

**nearest_closed_ids**: T13 (bottom buying, SOX 1 win of 3), AG2 record inside T13/E07 (0 of 8, stand-alone -3.1..+2.7%/yr, lost when 30-50% was carved out of v1), E07 (SOXL in place of TQQQ), T40 (capitulation ADD), X41, T02, S25.

**main_failure_mode**: 1) A panic that is not the last one: the 1.75 threshold separates April 2001 (about 1.65, no entry, would have lost 60% of the sleeve) from September 2001 (about 1.8) by a hair, so the result is fragile to the threshold. 2) Decay: a flat, volatile bridge period loses a third of the sleeve (2001-11). 3) Sample: about 5 design events, all known to me and mostly wins, so the design fit is in-sample by construction. 4) Weak blocks hold one or two small events; the sealed blocks probably none (see note), so it cannot be confirmed.

**own_probability_to_pass_pct**: 3

## 3. PRX-QLD: early re-entry from v1's cash state after a resolved panic, handed back to v1

**family**: IV-triggered idle-cash overlay (re-entry bridge for v1, lens uses i and ii)

**exact_rule**: Closes up to t; traded at t+2.
v, m_t, P_t, tau_t as in PRX-SOXL. PANIC_t = P_t >= a * m_t. RES_t = PANIC_t and v_s <= 0.60 * P_t for every s in [t-4, t]. Inactive until 504 VIX closes exist.
ENTRY at t: RES_t and v1 base level B_t = 0 (gate off: downtrend with a macro flag) and no open position and tau_t later than the last exit. Target QLD weight = W of account equity, mode 0, held at constant target W (synthetic 2x daily Nasdaq-100 before 2006-06).
EXIT at the first of: X1 B_t > 0 (v1's own gate turns on; v1 takes over at its own level); X2 v_t >= 0.85 * P_entry; X3 126 trading days.
One entry per VIX peak. v1 itself unchanged; brake unchanged.

**instruments**: QLD (extra), TQQQ and cash (v1). VIX as signal only.

**engine_mode**: v1 unchanged + 1 extra instrument in mode 0 (uses only cash v1 leaves idle).

**parameter_points**: 4 points (a, W): (1.75, 0.33); (1.75, 0.50); (2.00, 0.33); (2.00, 0.50). Exposure added is 0.67x or 1.0x of the account. Fixed: 40% retreat for 5 days, 0.85 re-panic, 126-day limit.

**data_needed_and_start**: All in project: VIX 1990+, QLD 2006+, Nasdaq-100 index for the synthetic 2x before 2006. Active from 1992-01.

**nearest_closed_ids**: T40 (RSI + volume capitulation ADD: path -0.73, real -2.18), T33 (stress resolved -> ADD; 56 of 59 days already 3x), T38 (75% early, 40% later), X41 (QLD as a middle state: path -0.18, real -2.2), T13, T02.

**main_failure_mode**: 1) Two informative events in 36 years; the weak blocks contain none, so the 'must hold on weak blocks' step is empty. 2) A resolved panic followed by a second leg down (spring 2001 type; excluded only because its ratio was about 1.65 < 1.75): a 2x position loses 50-70% of the sleeve before X2 fires if VIX stays below 85% of the old peak. 3) V-shaped recoveries (2020) give nothing because v1 re-enters at the same time.

**own_probability_to_pass_pct**: 2
