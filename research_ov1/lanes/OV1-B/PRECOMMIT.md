# OV1-B PRECOMMIT: direction-dependent fill time (decreases at next US open)

Written 2026-11-05 by the OV1-B builder BEFORE any statistic, return split or strategy result was computed from the
QQQ/SPY opens. Data <= 2014-12-31 only. Kill type F (brief section 4). N = 1.

## 1. Idea (fixed, zero free parameters)
v1 (= s0.85 = C3 signal + av23s(.85) brake, fstep 0.1, MS1 engine beng.run1) keeps its signal, states and trade list.
Only executed exposure DECREASES change fill time: a decrease due at the close of day e (= decision close t + 2)
is filled at the OPEN of e+1 instead. Increases, unchanged days and the year-end harvest fill at the close exactly as in v1.
The old exposure is held through one more overnight session. Theory (pre-2014 literature only): US index/ETF drift accrues
close-to-open, open-to-close ~0 or negative (Cliff-Cooper-Gulen 2008, SPY 1993-2006; Kelly-Clark 2011, ETFs incl. QQQ);
attention buying lifts opening prices (Berkman-Koch-Tuttle-Zhang 2012). The rule is not selected on any data.

## 2. Data and point-in-time rule
- QQQ daily OHLC, Twelve Data (data/qqq_1day_cut_le20141231.csv, sha256 297d875c...): PRIMARY source of opens/closes.
  Split-adjusted, NOT dividend-adjusted (ex-dividend drop lands in the overnight leg: conservative against the rule).
- SPY daily OHLC 1993-01-29..1999-12-31 (data/spy_panel_19930129_19991231.csv, sha256 9368a621..., extracted from the local
  shared panel research/data/panel_f32.npz.xz = Yahoo chart v8, sha256 fa2c35b2...): PRE-GATE ONLY. The scout could not
  fetch SPY; the local panel has it, so the pre-gate is run (covered) instead of being skipped. This can only add a kill.
- QQQ from the same panel (data/qqq_panel_xcheck_le20141231.csv, sha256 40b2f44d...): cross-check only, opened for
  2000+ rows only AFTER the pre-gate has passed.
- NDX r (price index daily return) and rf: jp.mkX(R, M, 'NDX') exactly as MS1.
- PIT: lag 0 on prices. O_t is public at the open of t, C_t at the close of t. A postponed fill at the open of e+1 uses only
  O_{e+1} as its fill price; the decision is v1's decision at close t = e-2 (unchanged). No new predictive input.

## 3. Exact formulas
- Overnight leg (underlying, 1x) for NDX trading day t: on_t = O_t / C_{t-1} - 1 from raw QQQ prices, only when QQQ has a row
  at t AND at the previous NDX trading date t-1 (jp NDX calendar). Otherwise on_t = 0 (identical to v1, 'not covered').
  Covered span: 1999-03-11..2014-12-30. 2014-12-31 (no Twelve Data row), all days before 1999-03-11 and every SPX basis: on_t = 0.
- Data-quality rules (fixed now, applied to the whole QQQ series, counts reported):
  (a) |on_t| > 0.25 -> on_t = 0 (split or data artefact);
  (b) where the panel QQQ has rows at t and t-1: |on_t(TwelveData) - on_t(panel)| > 0.005 -> on_t = 0 (vendor disagreement).
  Rule (b) is evaluated after the pre-gate. No other cleaning.
- Intraday leg: id_t = (1 + r_t) / (1 + on_t) - 1 (r_t = NDX daily price return; the day total stays exactly r_t).
- Product legs inside the engine (the 1x state is 1/3 TQQQ-type + 2/3 cash, as in MS1):
  3x product: overnight 3*on_t; intraday (1 + 3 r_t - 2 rf_t - 0.0245/252) / (1 + 3 on_t) - 1.
  Cash (USD deposit): overnight 0; intraday the whole day's deposit factor (1 + max(rf_t - 0.02/252, 0) * (1 - 0.154)).
- On dev250 paths the split travels with its source day: on_path[i, j] = on[ii[i, j]]; on_path[:, 0] = 0 (as c.r[:, 0] = 0).

## 4. Engine (code/eng_ov1b.py, copy of beng.run1 with split legs)
mode 0 = v1 (all fills at close; must equal std.engine to 1e-12 on all 5 bases for any ON input).
mode 1 = the rule. Day t order:
 1. tax-block boundary (k > 0, k % 252 == 0): due = 22% x max(realized - D, 0); realized reset (as v1).
 2. OPEN of t: v0 (3x product) *= (1 + 3 on_t); cash unchanged.
    If a decrease was pending from close t-1: rebalance to it NOW (same cost model as v1: 0.3% x |traded TQQQ value|; realized
    gain booked as v1 does; trade count +1).
    If t is a tax boundary and due > 0: the tax-payment sale (proportional sale of v0 and cash, as v1, no trading cost as v1)
    happens HERE, after the overnight leg (v1: at the previous close).
 3. INTRADAY: v0 *= (1 + 3r - 2rf - er3/252) / (1 + 3 on_t); cash *= deposit factor.
 4. CLOSE of t: if want != cur:
    - increase (want > cur), first day k = 0, a decrease due on the LAST day of a 252-day tax block (k % 252 == 251) or on the
      last day of the path -> fill at the close exactly as v1 (keeps the harvest and the tax year identical to v1; there is no
      next open on the last path day);
    - any other decrease -> pending, filled at the open of t+1 (step 2).
    Year-end harvest (k % 252 == 251) at the close exactly as v1.
 5. E at close t (brake input av23s, drawdown, equity record): MTM; on a day with a pending decrease, E is the value the v1
    rebalance would leave at the close-t prices (pending cost accrued at close prices). With on = 0 this makes mode 1 equal to
    v1 to rounding (parity requirement 1e-12 relative on final values and equity curves).
 Decision queue, delay 2, 0.5/0.1 steps, brake, tax, harvest, final liquidation tax: unchanged.

## 5. Kill test (type F, thresholds copied from brief section 4 and the court spec, not relaxed)
EARLY / pre-gate (run before any 2000+ open is read):
 (i) SPY 1993-02-01..1999-03-10 joined to QQQ 1999-03-11..1999-12-31: x_t = ln(O_t/C_{t-1}) - ln(C_t/O_t). PASS needs
     mean(x) > 0 AND Newey-West t >= 2 (Bartlett lag 10). Days whose previous row is not the previous NDX trading date are
     dropped (counted). Stale opens (O_t == C_{t-1}) are counted and reported, not removed.
 (ii) real_ndx_86_14, v1 (mode 0) decrease-execution days e with e+1 in 1993-02-01..1999-12-31: S = sum |delta exposure| x on_{e+1}
     (on from SPY before 1999-03-11, from QQQ after; simple returns; |delta exposure| in index units, e.g. 3x->1x = 2;
     tax-payment sales counted with delta = level x sold fraction; decreases due on k % 252 == 251 excluded as in the rule).
     PASS needs S > 0.
 If (i) or (ii) fails -> CLOSE (kill_verdict FAIL), measure2 is not run, unseen opens are not read.
UNSEEN / F test (only if the pre-gate passes): run the measure2-equivalent ONCE (code/measure.py: same loop as ov1lib.measure2,
 candidate through eng_ov1b mode 1, reference s0.85 through std.engine). F PASS needs dev250_path d_vs_s085 > +0.005 AND
 real_ndx_86_14 d (candidate cagr - v1 cagr) > 0.
FINAL PASS (only if F passes): HEADLINE_MS1 (dev250_path cagr) > 0.1616 AND REAL_NDX > 0.3108 AND dev250_path pw_vs_s085 >= 0.55;
 real SPX 55-85 / 70-85: not covered (on = 0 -> v1 fallback, must equal v1); N = 1; stress stated; glued = upper bound only.

## 6. Variants and N
N = 1 (the rule above). Report-only, never selectable, not counted:
 - stress: extra +0.1%/side opening-auction cost on every postponed fill (incl. the postponed tax sale's TQQQ part);
 - descriptive unseen statistics after the F test: (i)-type x_t mean/NW t on QQQ 2000-01-03..2014-12-30 and (ii)-type S on
   real_ndx 2000-2014; counts of postponed fills; data-quality counts.

## 7. On pass / fail
- FAIL anywhere -> CLOSE, results/*.json + ledger lines + RESULT_OV1-B_KO.md, and a registry row text in results/registry_row.txt
  (the lane writes only inside its folder; the coordinator adds the row to the closed registry).
- FINAL PASS -> report HEADLINE_MS1, REAL_NDX, glued (upper bound), SPX rows (not covered), pw, dd80, stress, N = 1, as a
  candidate execution rule on top of v1; no further variants are tried in this lane.
