# PRECOMMIT OV1-A: Treasury-noise relief re-arms 3x (type B ADD overlay on v1)

Written 2026-11-05, before any signal on-date, label, base rate or strategy return was computed.
Step-1 inspection (code/s1_inspect.py, results/s1_inspect.json) looked only at data quality: row counts, gaps,
off-calendar dates, VIX coverage and level descriptives. No outcome was looked at.

## 1. Hypothesis
Hu-Pan-Wang (2013 JF) Treasury "noise" (RMS yield deviation of notes/bonds from a smooth Svensson curve, bp) measures
arbitrage-capital scarcity. After noise doubles against its own 1-year median and has then given back half the spike,
forced selling is over and the expected return to bearing risk is high (Nagel 2012; Brunnermeier-Pedersen 2009).
v1 waits in 1x/cash until NDX retakes SMA200+2%. The overlay can only RAISE v1's non-3x target to 3x; it never cuts
v1's 3x, the alarms or the brake. The input uses neither NDX price nor the macro alarms.

## 2. Data (frozen)
- data/noise_hpw_cut_le2014.csv (Date, Noise_bp), sha256 2563fb577b1fb41bac074c414eb51dfbc3c750f40143cd22ab699371fca5fdd0,
  6,999 rows 1987-01-02..2014-12-31, derived from data/Noise_Measure_2025.xlsx
  (sha256 ac1242eb854a125649a321747454156c6d600da00a9cd33a558fbdb7f9609601, https://en.saif.sjtu.edu.cn/junpan/Noise_Measure_2025.xlsx).
  The xlsx is never read by lane code (only the cut csv). Rows after 2014-12-31 are never read.
- VIX control: column 'vix' of jp.mkX(R,M,'NDX') on jp.calendar('1984-01-03','2014-12-31') (first value 1990-01-02).
- v1 target: L.v1_B(std.contexts()['real_ndx_86_14']); brake L.v1_parts(c) (av23s .85, fstep .1).
- Labels and block grid: gate._frame('NDX','1984-01-03','2014-12-31','1986-01-02').

## 3. Point-in-time rule (fixed)
Calendar = NDX trading days of jp.calendar('1984-01-03','2014-12-31').
1. Reindex Noise_bp onto that calendar. The 7 noise dates that are not NDX trading days (1996-04-05, 2007-01-02,
   2007-04-06, 2008-03-21, 2010-04-02, 2012-04-06, 2012-10-29) are DROPPED (never used; conservative).
2. Lag 1 NDX trading day: N*_t = Noise_bp dated the previous NDX trading day (value dated d usable from close d+1).
3. Forward-fill at most 5 trading days; otherwise NaN (signal off). (Inspection: longest gap 4 days, so no NaN after 1987-01-05.)
Residual caveat: single 2025 vintage; undocumented later CRSP data corrections cannot be excluded.

## 4. Signal (exact; N = 1 candidate variant)
On any 1-D sequence x (calendar for real bases, each path row for MS1 bases):
- peak_t = max(x[t-62..t]) (63 values); base_t = median(x[t-251..t]) (252 values).
- Defined only when x[t-251..t] has 252 non-NaN values (this also fills the peak window); otherwise on_t = False.
- k_t = LATEST date in t-62..t at which the max is attained. Then (t - k_t) >= 5  <=>  max(x[t-4..t]) < peak_t.
- spike_t = peak_t >= 2.0 * base_t
- relief_t = x_t <= base_t + 0.5 * (peak_t - base_t)  AND  (t - k_t) >= 5
- on_t = spike_t AND relief_t
- Constants 63, 252, 2.0, 0.5, 5 fixed a priori (court spec). No other variant is tried. N = 1.
Overlay: B_new_t = 3 if on_t and v1_B_t < 3, else v1_B_t. av23s(.85) brake and 2-day execution delay unchanged.
Bases for measure2:
- real_ndx_86_14: x = N* (L.gather on the real context; must equal the calendar series used in the kill test).
- dev250_path (HEADLINE): x = exp(L.path_series(log N*, 'dev250_path')), rolling stats computed along each path row.
  All comparisons are scale-invariant, so the cumulative log offset at block joins cancels except in windows that
  straddle a join. Path days whose source date has no noise (pre-1987) are NaN -> off -> v1.
- dev250_glued (upper bound only): x = L.gather(N*, 'dev250_glued'), rolling along each path row.
- real_spx_55_85, real_spx_70_85: no noise data -> B = v1_B ('not covered').

## 5. Kill test: type B (brief section 4, thresholds copied, not relaxed)
Brief text: "B ADD overlay (raise v1 1x/cash -> 3x when the signal fires): in v1 non-3x blocks, P(3x beats deposit | on)
>= base + 10pp AND >= 60%, >= 8 'on' blocks, both windows."
- Blocks: gate._frame grid (non-overlapping 21-trading-day blocks from 1986-01-02). Label of block at close t =
  3x NDX product (3r - 2rf - 2.45%/yr) beats deposit ((rf - 2pp) x 0.846) over trading days t+3..t+23.
- Universe: blocks with v1_B_t < 3 (v1 target at block-start close t, real_ndx_86_14).
- base = label hit rate of universe blocks in the window; cond = hit rate of universe blocks with on_t; n_on = their count.
- Windows (block membership):
  * early: block start t >= 1988-01-04 AND label end day (t+23) <= 1999-12-31. The one block whose label straddles
    into 2000 is dropped from both windows so that no 2000+ return enters the early test.
  * unseen: block start t >= 2000-01-03 (grid ends so that labels end <= 2014-12-31). Opened ONCE, only if early passes.
- PASS B iff cond >= base + 0.10 AND cond >= 0.60 AND n_on >= 8, in BOTH windows. n_on < 8 in either window = FAIL.
- Binding control (early window, reported first): the identical rule (same lag, ffill 5, 63/252/2.0/0.5/5) with VIX
  in place of N*. VIX starts 1990-01-02, so the control can fire only from about 1991. If the VIX rule has >= 1 on-block
  in the early universe AND cond_VIX > cond_noise -> CLOSE as T02 vol timing (FAIL). The VIX rule is a control, never a
  candidate, and is not counted in N. In the unseen window VIX is reported as information only.
- Deflation: N = 1 in this lane (court: one lane per information family; TED / Eurodollar partners not run, not counted),
  so the sqrt(1 + ln N) factor is 1. The binomial SE of cond is reported as information.

## 6. Pass / fail actions
- Early FAIL (any condition, or VIX control closes it) -> stop, unseen never opened, kill_verdict FAIL, CLOSE + registry row.
- Early pass -> unseen once with the same rule. Unseen FAIL -> FAIL, CLOSE + registry row.
- Both pass -> L.measure2('OV1-A', make2) with B_new on all 5 bases. FINAL PASS iff HEADLINE_MS1 (dev250_path) > 0.1616
  AND REAL_NDX > 0.3108 AND dev250_path pw_vs_s085 >= 0.55; SPX 55-85 not covered (v1 fallback, identical to v1 by
  construction); glued reported as an upper bound only; dd80 reported. Any failure -> CLOSE + registry row.
- Every counted result goes to ledger.csv (lane,variant,window,metric,value) and results/*.json; RESULT_OV1-A_KO.md in Korean.
