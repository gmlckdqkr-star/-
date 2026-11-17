# Designer lens: answer-first

Ideas only; written without running market data. Rules are quoted as the designer wrote them.

## 1. AK-RES7: residual answer-key classifier on v1 (full, exit-only and re-entry-only arms, plus two controls)

**family**: X04 answer-key reverse engineering (also touches T25, T07, T08, T12, T40, X10)

**exact_rule**: 1) KEY. Per design block (first to last trading day; the last block ends 2026-08-31), on the engine's Nasdaq-100 series: g_t = 3*r_t - 2*rf_t - 0.015/252, level l in {0,1,3}. K = argmax over level paths of sum_t ln(1 + (l_t/3)*g_t) - kappa * sum_t |l_t - l_(t-1)|/3 (Viterbi, free start, no terminal charge, no return outside the block). kappa = 0.25 or 0.10. kappa = 0.003 is computed only as a reported ceiling. Each key is also pushed through the real engine (0.3% per side, 22% tax, zero cash yield, trades landing on key days) to report after-tax ceilings per block.
2) ROWS AND LABELS. B_t = v1 base level (bk.C3sig) on the real path. The decision at close t is paired with K_(t+2). Rows = design-block days 64..(last-23). UP rows: B_t <= 1, label 1[K_(t+2) = 3] (v1 wrong-low). DN rows: B_t = 3, label 1[K_(t+2) = 0] (v1 wrong-high).
3) FEATURES (causal, memory <= 252 days, no price or yield levels, no calendar). C = index close. reb63 = C/min(C,63d)-1. volr = vol20/max(vol20,63d). age = days since the 252d closing high / 252. cs63 = 63d change of Baa-Aaa. brd = share of the 12 French industry indices above their own 200d SMA. ts = VIX/VIX3M where VIX3M exists, else VIX/mean(VIX,63d), else vol20/vol60. d200 = C/SMA200-1. semis = 63d log return of SOXX (French Chips before SOXX) minus that of the index. UP model: reb63(+), volr(-), age(-), cs63(-), brd(+), ts(-). DN model: d200(-), brd(-), cs63(+), ts(+), semis(-). Signs are fixed a priori.
4) MODEL. Logistic regression on z-scores (mean and SD of the training rows, clipped at +-3), L2 penalty C = 0.1, intercept free. Any coefficient with the wrong sign is removed and the model is refitted. Nothing else is tuned.
5) MAPPING WITH HYSTERESIS. UP fires after p_UP >= 0.65 on 3 consecutive closes: base' = 3. It ends after p_UP < 0.50 on 3 closes or on a new 63d closing low (then 21 days lock-out). DN fires after p_DN >= 0.35 on 3 closes: base' = min(B,1). It ends after p_DN < 0.20 on 3 closes. Otherwise base' = B. Thresholds come from break-even arithmetic, not data: a wrong early 3x costs about what a right one earns, so above 0.5; a wrong 3->1 cut costs about 3% and a right one saves about 16%, so 0.16, doubled for miscalibration. The brake rx.av23s(s=0.85) runs unchanged on base'.
6) CROSS-VALIDATION INSIDE DESIGN. Leave-one-block-out, 7 folds: fit on 6 blocks, run one continuous 1986-2026 account with that fit, score only the held-out block against v1 (paired). The nominated point is refitted on all 7 and then scored on WEAK.
7) KILL RULES (any one ends it). K1: held-out Brier skill versus the base rate <= 0 in 3 or more folds. K2: held-out mean paired difference < +2.0pp/yr, or fewer than 6 of 7 held-out blocks >= 0. K3: 200 refits with the key rotated inside each block by a random 126..(n-126) days; the real held-out mean must exceed the 99th percentile. K4: held-out gain below one third of the in-sample gain. K5: a side with fewer than 2 surviving features in 5 or more folds is declared empty. K6: P1 fails to beat control P5 by 0.5pp, or fails to beat control P6. On WEAK: mean >= +1pp, at least 4 of 5 blocks >= 0, and mean >= 0 with cost x2 and one more day of delay.

**instruments**: TQQQ (engine synthetic 3x before 2010) and cash only. No extra instrument.

**engine_mode**: v1 with a modified base level; brake rx.av23s(s=0.85) unchanged; no extras (neither mode 0 nor mode 1 is used).

**parameter_points**: P1: kappa .25, both sides. P2: kappa .10, both sides. P3: kappa .25, DN (exit) side only. P4: kappa .25, UP (re-entry) side only. P5 (control, same information): kappa .25, both sides, features limited to v1's own inputs (d200, vol20, dd252, ret63, shock6m flag, inversion-memory flag; UP signs +,-,+,+,-,-; DN signs reversed). P6 (control, no fitting): (E) if the v1 trend gate turns off within 21 trading days of the 252d closing high, base' = 1 instead of 0 for at most 63 days, ended early by v1's own re-entry or by a close 15% below the trigger-day close; (R) if B = 1 only because vol20 > 0.40 (gate open, shock6m off) and vol10 < 0.40 and C > SMA200, base' = 3. Only P1-P4 can be nominated; all 6 count for Bonferroni.

**data_needed_and_start**: All in the project: Nasdaq-100 daily 1985+, 3-month bill, Moody's Baa-Aaa daily 1986+, VIX 1990+, VIX3M 2006-07+, Ken French 12 industries and the 48-industry Chips series (to 2026-08), SOXX 2001+, and the locked v1 engine output (C3sig) on the real path. First usable design row: 1989 (features use 1988 data causally).

**nearest_closed_ids**: X04, T25, T24, T08, T07, T12, T23, T28, T40, T13, T33, T38, X10, T02, T32, T15

**main_failure_mode**: Seven macro clusters against 11 coefficients: the fit memorises 'V-shaped 2020 and 2025 versus grinding 2001-02 and 2008' from two or three cases per class. A second failure is a false pass on the post-2014 design blocks, where v1 is out of sample and the new fit is in sample. A third is power: a rule active in only 3-4 blocks cannot reach 7/7 wins.

**own_probability_to_pass_pct**: 1

## 2. AK-SEL: key-agreement reliability screen for QQQ and SOXX signals (owner direction b measured against the answer key)

**family**: T08 signal rescoring and vote / E07 3x vehicle choice / X04 answer key

**exact_rule**: 1) Keys at kappa = 0.25 exactly as in AK-RES7, built separately for the Nasdaq-100 (K_Q) and for semiconductors (K_S: SOXX from 2001-07, the French 48-industry Chips series before; synthetic 3x with the same 1.5% drag, used for the label only), inside design blocks only.
2) Fixed library, computed on the instrument's own closes X (index for Q, SOXX/Chips for S). s1: X > SMA200. s2: SMA50 > SMA200. s3: X >= 0.90*max(X,252d). s4: 126d return > 0. s5: return from t-252 to t-21 > 0. s6: X > SMA20. s7: vol20 < its 252d median. s8: Baa-Aaa 63d change < 0. s9: 10y minus 3m yield > 0. s10: VIX < its 252d median (from 1991). S only, s11: 63d return of X minus 63d return of the Nasdaq-100 > 0. No owner formula is used.
3) Reliability per signal and design block: PSS_b = P(s on at t | K_(t+2) = 3) - P(s on at t | K_(t+2) = 0), on days 64..(last-23), computed only in blocks with at least 40 days in each key state (informative blocks). A signal is high-reliability if PSS_b >= 0.20 in every informative design block and there are at least 4 such blocks. H_Q and H_S are the surviving sets. If a set has fewer than 3 signals, the pre-declared result for that instrument is 'no reliable signal set exists' and its arms are not run.
4) Vote v = share of the surviving set that is on at close t.
5) Arms as listed in the parameter points. Survivors are frozen on design, then scored on WEAK with the same paired block test, cost x2 and one more day of delay.

**instruments**: TQQQ and cash (v1); SOXL as the one extra instrument (real from 2010-03; synthetic 3x SOXX 2001-2010 and 3x French Chips before, with 1.5%/yr drag, which is a proxy).

**engine_mode**: S0: mode 0 (non-dilutive, idle cash only). S1: mode 1 (SOXL has priority; v1 gets its level share of the remaining 70%). Q1: v1 with an extra cap signal. QS: Q1 plus S0.

**parameter_points**: S0: SOXL target weight min(0.30, cash v1 leaves idle) from the day v_S >= 0.75 on 3 consecutive closes until v_S < 0.50. S1: same trigger, weight 0.30, only while v1's final level >= 1. Q1: v_Q < 0.34 on 3 closes -> base' = min(B,1) until v_Q >= 0.50. QS: Q1 and S0 together. (4 points.)

**data_needed_and_start**: All in the project: Nasdaq-100 1985+, SOXX 2001+, French Chips series (to 2026-08), SOXL 2010+, Baa-Aaa 1986+, 10y and 3m yields, VIX 1990+, and the locked v1 engine.

**nearest_closed_ids**: T08, E07, X04, T23, T28, T01, X10, T32, T13, E12, S25, X41, and the AG2 lane (RESULT_AG2_KO.md)

**main_failure_mode**: Passing design because semiconductors led in 2 of the 3 real-SOXL design blocks, then failing WEAK; or a void result. The mode 1 arm also inherits the 3x-chip tail (2000-02) through the proxy years.

**own_probability_to_pass_pct**: 1
