# PRECOMMIT OV1-E: TED spike (3-month change in DED3 - DTB3 above its trailing 5-year 90th percentile) cuts v1's 3x to 1x (type A CUT overlay on v1)

Written 2026-11-05, before any label, base rate, v1 state, signal on-date or strategy return was computed.
Step-1 inspection (code/s1_inspect.py, results/s1_inspect.json) looked only at data quality: row counts, blank rows, gaps,
value ranges, TED yearly medians, the DED3-based TED vs FRED TEDRATE cross-check (1986-2014: level corr .953, 63-day change
corr .967, median |diff| 0.11pp) and the first master trading day on which the signal is defined (1976-03-31).
No v1 state, label, return or signal on-date was looked at. The signal below is the completeness critic's pre-specified signal
(task text for lane OV1-E, round 2), copied without change. Section 4 lists the ambiguities I fixed, all before computing.

## 1. Hypothesis
When unsecured bank term funding gets scarce (3-month Eurodollar deposit rate rises against the 3-month T-bill), leveraged
intermediaries face higher margins and haircuts and sell high-beta assets (Brunnermeier-Pedersen 2009; Garleanu-Pedersen 2011;
Frazzini-Pedersen 2014). NDX at 3x is the high-beta end. v1's credit alarm reads a slow long-bond default spread (cs); TED is a
short-end bank-funding price. The overlay only moves v1 from 3x to 1x while the 3-month TED change is in the top decile of its
own trailing 5-year distribution. It never touches any other v1 state, the alarms or the brake. Input = money-market funding
spread (new information; no NDX price, not in v1's alarms, WX1-M1, BT1 or r2_resweep families).
Known hostile episodes stated a priori by the court: the Oct-Dec 1999 Y2K funding spike during the NDX blow-off, and
policy-backstop bottoms (Aug 1982, Oct 1987, Oct 1998). Literature ceiling (generator): expected drop 0-6pp vs 10pp needed, p ~ 0.02.

## 2. Data (frozen; sha256 of the files read by lane code; full values in data/MANIFEST.json)
- data/cut_DED3_le2014.csv  sha256 ae14d579b90a03355e1e63287c0ca4d39f60a782ef30f0d835523fbb956b3f61
  (FRED DED3, 3-Month Eurodollar Deposit Rate (London), daily, 1971-01-04..2014-12-31, 11,478 rows, 284 blank)
- data/cut_DTB3_le2014.csv  sha256 a021f614870981c4030437c625bdcd293743d0e12abea5065fca743ae98649f2
  (FRED DTB3, 3-Month T-bill secondary market, discount basis, daily, 1954-01-04..2014-12-31, 15,913 rows, 673 blank)
- data/cut_TEDRATE_le2014.csv (8a6b8c69...) is a data-quality cross-check only; never a signal, not in N.
- Raw files are kept as fetched (2026-11-05T09:09Z, https://fred.stlouisfed.org/graph/fredgraph.csv?id=DED3 / ?id=DTB3);
  lane code reads only the <=2014 cut files. Market quotes, not revised (no vintages needed).
- Signal library: code/sig_e.py sha256 39a9d9aa52d0eadf20c9c1b598dca0ed4251048765c9fbc0726daaa2ebe3ae30 (frozen; the test
  scripts assert this hash and this file's hash).
- v1 target: L.v1_B (bk.C3sig) on the real contexts built exactly as std.contexts() builds 'real_ndx_86_14' and 'real_spx_55_85'.
- Labels and block grid: gate._frame('NDX','1984-01-03','2014-12-31','1986-01-02') and gate._frame('SPX','1928-01-03','1985-12-31','1955-01-03').

## 3. Signal (exact; N = 1 in this lane)
Critic's text: "TED = FRED DED3 minus FRED DTB3. Market quotes, no revisions; usable from t+1 (one-day lag). Signal on at close t
if (TED_t - TED_{t-63}) is above the 90th percentile of its own trailing 5-year (1260 trading days, values strictly before t)
distribution; need >= 1260 prior observations. CUT: when on and v1 B == 3 -> 1."
Implementation (code/sig_e.py):
- TED*(t) = DED3*(t) - DTB3*(t), where X*(t) = the latest observation of X dated strictly before trading day t's calendar date.
- x(t) = TED*(t) - TED*(t-63), 63 positions back along the row.
- q90(t) = numpy.quantile(x[t-1260 .. t-1], 0.90, method='linear'); all 1260 values must be defined, else undefined.
- ON(t) = x(t) defined AND q90(t) defined AND x(t) > q90(t) (strict). Undefined -> ON False (fallback = v1).
- Overlay: B_new(t) = 1 if v1_B(t) == 3 and ON(t), else v1_B(t). av23s(.85) brake, fstep .1, 2-day execution delay unchanged.

## 4. Ambiguities fixed before computing (stated as required)
1. Calendar for "t-63" and "1260 trading days": positions on the master US trading calendar = jp.calendar('1928-01-03','2014-12-31')
   index (the SPX and NDX frames are slices of it; s1_inspect confirmed every MS1 basis date is in it). This lets NDX 1986+
   blocks use TED history from 1971 (the NDX frame itself starts 1984). On dev250_path the positions are along each path row.
2. One-day lag: each series is taken from its own latest observation dated strictly before t, forward-filled separately with no
   limit (longest DED3 gap 7 calendar days, 2001-09-10..09-17; DTB3 5). 183 DED3 observations dated on non-US-trading days
   (London open) are used at the next US close, which is still >= 1 day after their date.
3. DTB3 is used as published (discount basis). No bond-equivalent conversion (the critic's spec says DED3 - DTB3; the generator's
   earlier BEY / 21-day / expanding-window / 21-day-hold draft is NOT run and NOT counted).
4. Percentile: numpy linear interpolation over exactly 1260 values; "above" = strictly greater. No persistence or hold rule.
5. ">= 1260 prior observations" = the 1260 x values at t-1260..t-1 all defined. First defined master day: 1976-03-31.
6. Path (HEADLINE): the TED* level series on the dev250 calendar (1986-01-02..2014-12-31) is rebuilt along each path row with
   L.path_series(TED*, 'dev250_path'); x, q90 and ON are computed along the row. The first 1323 positions of each row have no
   signal (insufficient path history) and use v1. Glued (upper bound only): the master-calendar ON of each source date,
   L.gather(ON, 'dev250_glued'). Real bases: master-calendar ON (identical to the kill test) via L.gather.
   real_spx_55_85 / real_spx_70_85: ON undefined before 1976-03-31 -> v1 B ('not covered' 1955-01..1976-03).

## 5. Kill test: type A (brief section 4, thresholds copied, not relaxed)
Brief text: "A CUT overlay on v1 (move v1 3x -> 1x/cash when the signal fires): in 21-day blocks where v1 is at 3x,
P(3x beats deposit | signal on) must be >= 10pp BELOW the base rate of v1-3x blocks, with >= 8 'on' blocks, in BOTH windows."
- Blocks: gate._frame grid (non-overlapping 21-trading-day blocks). Label of block at close t = 3x product (3r - 2rf - 2.45%/yr)
  beats deposit ((rf - 2pp)+ x 0.846) over trading days t+3..t+23 (exactly gate._frame).
- Universe: blocks with v1_B(t) == 3 at block-start close t (era's real context). Signal = ON(t) at block-start close t.
- Windows (block membership):
  * early, era SPX: block start t >= 1976-03-31 and label end (t+23) <= 1985-12-31 (SPX grid from 1955-01-03).
  * early, era NDX: block start t >= 1986-01-02 AND label end (t+23) <= 1999-12-31 (the block straddling into 2000 is dropped
    from both windows so no 2000+ return enters the early test).
  * unseen: NDX block start t >= 2000-01-03 (labels end <= 2014-12-31 by construction). Opened ONCE, only if early passes.
- Early statistic (pooled, era-matched base, same rule the court fixed for OV1-C): base_e = hit rate of all universe blocks of
  era e; hit_on,e = hit rate of universe blocks with ON; drop = sum_e n_on,e x (base_e - hit_on,e) / sum_e n_on,e;
  n_on = sum_e n_on,e. SPX-only and NDX-only drops are reported but do not gate.
- Unseen statistic: drop = base - hit_on over NDX 2000-2014 universe blocks; n_on.
- PASS A iff drop >= 0.10 AND n_on >= 8, in BOTH windows. Binomial SE, z and one-sided exact binomial p of hit_on are information only.
- Verification (code/s3_check_early.py): ON re-computed on every early block date by direct lookups in the raw cut files and an
  explicit 1260-value np.percentile, plus a whole-day pandas rolling-quantile check over 1976-03-31..1999-12-31 only.

## 6. N and deflation
- Lane N = 1 (one variant: 63-day change, 1260-day window, 90th percentile, 3x -> 1x). No threshold, horizon, window, BEY,
  hold, cash-instead-of-1x or TEDRATE variant is run.
- Family N: this lane is the T33 funding/arbitrage-stress family partner of OV1-A (HPW noise, B ADD, FAIL). Family N = 2,
  deflation factor sqrt(1 + ln 2) = 1.300. The type-A gate is the brief threshold on the raw pooled drop (not relaxed, not
  tightened); the deflated lower bound drop - 2 x SE x 1.300 is reported as information. If measure2 is reached, the deflated
  excess over v1 = (value - v1 ref) / 1.300 is reported for HEADLINE and REAL (the pass sign is unchanged by this factor).

## 7. Pass / fail actions
- Early FAIL -> stop, unseen never opened, kill_verdict FAIL, CLOSE + registry row draft.
- Early pass -> unseen once with the identical rule (s2_killA.py unseen refuses to run twice). Unseen FAIL -> FAIL, CLOSE.
  An unseen pass is discounted: the idea generator and critic knew the 2007-08 TED history.
- Both pass -> code/s4_measure2.py: L.measure2('OV1-E_ted_cut', make2) with B_new on all 5 bases as in section 4.6.
  FINAL PASS iff HEADLINE_MS1 > 0.1616 AND REAL_NDX > 0.3108 AND dev250_path pw_vs_s085 >= 0.55 AND real_spx_55_85 cagr >=
  v1's real_spx_55_85 cagr - 0.01 (covered from 1976-03-31). dd80 reported. Glued reported as an upper bound only.
- Every counted result -> ledger.csv (lane,variant,window,metric,value) and results/*.json; RESULT_OV1-E_KO.md in Korean.
- lab 사용: 아니오 (Eurodollar deposit and T-bill daily rates are not in the lab panel; the test is a v1 overlay block test).
