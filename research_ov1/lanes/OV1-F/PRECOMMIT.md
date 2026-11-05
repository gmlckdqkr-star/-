# PRECOMMIT OV1-F: yen carry-unwind CUT (JPY 21-day appreciation in the top 5% of its trailing 3 years -> v1 3x to 1x for 21 days), type A

Written 2026-11-05 before any label, base rate, v1 state, signal fire/on date or strategy return was computed.
Step 1 (code/s1_inspect.py, results/s1_inspect.json) looked only at data quality and ran a synthetic code test: rows, holidays,
gaps, level range, a >4% daily-move data-error screen, first availability / first defined dates on the master calendar, and
the threshold code against brute-force numpy.percentile on random data (max diff 0, NaN pattern equal). No outcome was looked at.
The signal is the completeness critic's pre-specification; this file only fixes its ambiguities (listed in section 4, "fixes").

## 1. Hypothesis and mechanism
A sharp appreciation of the yen (the classic funding currency) marks carry-trade unwinding and forced deleveraging: speculators
long high-yield / risk assets and short yen get margin calls, funding liquidity dries up and risky assets fall together
(Brunnermeier, Nagel and Pedersen 2008, NBER Macro Annual, "Carry Trades and Currency Crashes"; the mechanism and data source are used,
no post-2014 numbers). v1's alarms see only US rates and credit and NDX price/vol, so v1 can sit at 3x through a yen squeeze.
The overlay only moves v1 from 3x to 1x while the signal is on. It never touches any other v1 state, the alarms or the brake.
New input = one safe-haven currency (JPY per USD). WX1-M1 used only the broad dollar (DTWEXM), not JPY.
idea_check (2026-11-05) printed "auto reject" on keyword overlaps only: X34 (KRW hedge structure, word 캐리), E04 (carry as a return
stream, word carry), S02 (word "per" from "percentile"). None of them is a yen-appreciation timing input for a CUT; no closed row
covers FX-rate timing. Proceeding as a new axis, N = 1.

## 2. Data (frozen)
- data/cut_DEXJPUS_le2014.csv sha256 1a3ed7e589dc8491c30a1724700ce42be8843260667d5a9092f5a17a180ac164 (rows 1971-01-04..2014-12-31,
  11478 rows, 441 empty holiday values). Raw download data/raw_DEXJPUS.csv sha256 60ba9554...; never read by lane code.
  Source https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXJPUS fetched 2026-11-05T09:08:29Z. Market data, not revised.
- v1 target: L.v1_B (bk.C3sig) on real contexts built exactly as std.contexts() builds 'real_ndx_86_14' and 'real_spx_55_85'.
- Labels and block grid: gate._frame('NDX','1984-01-03','2014-12-31','1986-01-02') and gate._frame('SPX','1928-01-03','1985-12-31','1955-01-03').

## 3. Point-in-time rule (fixed)
- DEXJPUS value dated d is usable from the first trading day after d (index d + 1 calendar day, then forward-fill onto the trading
  calendar with union + ffill as ov1lib._onto). Holiday rows (empty) are dropped first. The noon rate of day d is public at noon on d,
  so this is one day conservative. The engine then applies v1's 2-day execution delay as usual.

## 4. Signal (exact; N = 1). Implementation code/sig_f.py
- lx = log(DEXJPUS) on trading days. yen21(t) = -(lx(t) - lx(t-21)) (positive = yen appreciation).
- thr(t) = 95th percentile of yen21(t-756), ..., yen21(t-1) (756 values strictly before t), numpy default 'linear' interpolation.
- fire(t) = yen21(t) > thr(t). ON(t) = fire on any of t-20, ..., t (a fire keeps ON for 21 trading days including the fire day;
  a new fire while on extends it).
- CUT: B_new(t) = 1 where v1_B(t) == 3 and ON(t), else v1_B(t). av23s(.85) brake, fstep .1, 2-day delay unchanged.
- Fixes of ambiguities (made before computing anything outcome-related):
  (a) "trading days" = the MS1 master US trading calendar (jp.calendar 1928-01-03..2014-12-31; every basis calendar is a subset);
      21 and 756 are counted in positions of that calendar (real bases) or of the path row (MS1 path). FX holidays on equity
      trading days carry the previous value (4.4% of days).
  (b) "usable from t+1" = rule in section 3. (c) percentile = numpy 'linear', comparison strict '>'.
  (d) all 756 trailing yen21 values must exist, else thr undefined; any undefined value -> fire False (fallback = v1).
      On the master calendar the first defined day is 1974-02-01 (DEXJPUS starts 1971-01-04; the 1971-73 peg/Smithsonian period
      enters the trailing window of 1974-76 as specified by the critic; not changed).
  (e) "1x" = the v1 1x state (not cash).
  (f) Basis handling for measure2: real_ndx_86_14 / real_spx_55_85 / real_spx_70_85: ON from the master calendar (identical to the
      kill test) reindexed onto the basis calendar and indexed by c.ii (SPX 1955-01..1974-01 not covered -> v1).
      dev250_path (HEADLINE): lx_path = L.path_series(log DEXJPUS availability series, 'dev250_path'); yen21, thr, fire and ON are
      computed along each path row (the first 777 positions of each row are undefined -> v1; that is the first ~477 measured days,
      ~1.9 of 30 years). dev250_glued (upper bound only): ON of the ORIGINAL date (master-calendar ON gathered by L.gather), the same
      way dev250_glued takes v1's alarm flags from the original history.

## 5. Kill test: type A (brief section 4, thresholds copied, not relaxed)
Brief text: "A CUT overlay on v1 (move v1 3x -> 1x/cash when the signal fires): in 21-day blocks where v1 is at 3x,
P(3x beats deposit | signal on) must be >= 10pp BELOW the base rate of v1-3x blocks, with >= 8 'on' blocks, in BOTH windows."
- Blocks: gate._frame grid (non-overlapping 21-trading-day blocks). Label of block at close t = 3x product (3r - 2rf - 2.45%/yr)
  beats deposit ((rf - 2pp)+ x 0.846) over trading days t+3..t+23 (exactly gate._frame).
- Universe: blocks with v1_B(t) == 3 at block-start close t (era's real context). Signal = ON(t) at block-start close t.
- Windows (block membership):
  * early, era SPX: block start t in [1974-02-01, 1985-12-31] (SPX grid; label end <= 1985-12-31 by construction).
  * early, era NDX: block start t >= 1986-01-02 AND label end day (t+23) <= 1999-12-31 (a block straddling into 2000 is dropped).
  * unseen: NDX block start t >= 2000-01-03 (labels end <= 2014-12-31). Opened ONCE, only if early passes.
- Early statistic (same as the OV1 A-type template): base_e = hit rate of all universe blocks of era e; hit_on,e = hit rate of universe
  blocks with ON; drop = sum_e n_on,e x (base_e - hit_on,e) / sum_e n_on,e; n_on = sum_e n_on,e. Era-only drops reported, not gating.
- Unseen statistic: drop = base - hit_on over NDX 2000-2014 universe blocks; n_on.
- PASS A iff drop >= 0.10 AND n_on >= 8, in BOTH windows. Binomial SE / one-sided binomial p reported as information only.

## 6. Pass / fail actions
- Early FAIL -> stop, unseen never opened, measure2 not run, kill_verdict FAIL, CLOSE + registry row draft.
- Early pass -> unseen once with the identical rule. Unseen FAIL -> FAIL, CLOSE. An unseen pass is discounted: the idea generator knew
  the 2008 yen surge.
- Both pass -> L.measure2('OV1-F', make2) with B_new on all 5 bases (section 4f). FINAL PASS iff HEADLINE_MS1 > 0.1616 AND
  REAL_NDX > 0.3108 AND dev250_path pw_vs_s085 >= 0.55 AND real_spx_55_85 cagr >= v1's real_spx_55_85 cagr - 0.01. dd80 reported.
  Glued reported as upper bound only. N = 1, deflation factor sqrt(1 + ln 1) = 1.
- Every counted result -> ledger.csv (lane,variant,window,metric,value) and results/*.json; RESULT_OV1-F_KO.md in Korean.
- lab 사용: 아니오 (DEXJPUS is not in the lab panel; the overlay must run inside the MS1 engine via ov1lib).
