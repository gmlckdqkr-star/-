# PRECOMMIT OV1-C: foreign central-bank synchronized tightening cuts v1's 3x to 1x (type A CUT overlay on v1)

Written 2026-11-05, before any label, base rate, v1 state, signal on-date or strategy return was computed.
Step-1 inspection (code/s1_inspect.py, results/s1_inspect.json) looked only at data quality: sources, row counts, gaps,
splice levels, ECB fill, UK vs BOERUKM cross-check (differences are 2-decimal rounding only, max 0.005pp), and the first
date on which all three 126-day differences exist (SPX calendar 1959-07-31, NDX calendar 1984-07-02). No outcome was looked at.
The spec below is the court's (work/COURT_OV1.json, lane OV1-C) copied without change; nothing was tuned.

## 1. Hypothesis
Policy-rate hikes by major non-US central banks (BoJ, Bundesbank/ECB, BoE) tighten global funding and carry positions and
reduce foreign demand for long-duration growth assets. v1's alarms see only US rates and credit, so v1 can sit at 3x through a
synchronized foreign tightening. Pre-2014 support: Jensen-Mercer-Johnson (1996 JFE), Conover-Jensen-Johnson (1999 JBF),
Ang-Bekaert (2007 RFS). The overlay only moves v1 from 3x to 1x while >= 2 of the 3 banks have hiked >= 25bp over 126 trading
days. It never touches any other v1 state, the alarms or the brake. Input = foreign policy rates (new information; no NDX price).

## 2. Data (frozen; sha256 of the files read by lane code)
- JP: data/cut_INTDSRJPM193N.csv (3e9ab4e9..., Japan discount rate, IMF IFS monthly), used for months 1953-01..1985-06;
      data/cut_IRSTCI01JPM156N.csv (66f98b37..., Japan call rate, OECD MEI monthly average), used for months 1985-07..2014-12.
- DE/EZ: data/cut_ALFRED_INTDSRDEM193N_v20141231.csv (70d4d23d..., Bundesbank discount rate, ALFRED vintage 2014-12-31),
      months 1957-01..1998-12 (the current FRED INTDSRDEM193N is redefined and is NOT used);
      data/derived_ecb_mro_filled.csv (4b752c5a..., ECB MRO daily: ECBMRRFR where present, else ECBDFR + corridor), 1999-01-01..2014-12-31.
- UK: data/cut_INTDSRGBM193N.csv (678ba2bc..., UK Bank Rate, IMF IFS monthly) months 1959-01..2013-03, then 0.50 carried flat to
      2014-12-31 (BOERUKM cut file 250e9812... confirms 0.50 for every month 2013-04..2014-12).
- Full sha256 values are in data/MANIFEST.json and were re-verified by sha256sum on 2026-11-05. No row after 2014-12-31 is read.
- v1 target: L.v1_B (bk.C3sig) on the real contexts built exactly as std.contexts() builds 'real_ndx_86_14' and 'real_spx_55_85'.
- Labels and block grid: gate._frame('NDX','1984-01-03','2014-12-31','1986-01-02') and gate._frame('SPX','1928-01-03','1985-12-31','1955-01-03').

## 3. Point-in-time rule (fixed)
- Monthly value for month m (dated m-01) is usable from the first trading day on or after the 1st of month m+1.
- ECB daily value dated d is usable from the first trading day after d (index d+1 calendar day, then forward-fill).
- Forward-fill onto the trading calendar of each basis (L._onto: union + ffill). Values enter the signal at that day's close;
  v1's 2-day execution delay is applied by the engine as usual.
- Caveat (stated, not fixable): no pre-2011 ALFRED vintages exist, so first-release values cannot be checked. Policy-rate decisions
  are public on the announcement day (earlier than m+1); the OECD call-rate monthly average for month m is computable from daily
  market data at the end of month m. So m+1 is not optimistic against public information, only against the IFS/OECD vendor lag.

## 4. Signal (exact; N = 1)
- X_c = change index per c in {JP, DE_EZ, UK}: on availability dates, start level + cumulative sum of the source's own
  period-to-period changes; the change at each splice is set to 0 (JP: call 1985-07 vs discount 1985-06; DE_EZ: ECB 1999-01-01
  vs Bundesbank 1998-12). Implementation: code/sig_c.py change_index().
- On any 1-D row x_c (full trading calendar for real bases, each path row for MS1 resampled bases):
  d_c(t) = x_c(t) - x_c(t-126) (126 positions back along the row); up_c(t) = d_c(t) >= 0.25 (pp; float tolerance 1e-9).
- ON(t) = [sum_c up_c(t) >= 2] AND all three d_c(t) defined. Undefined -> ON False (fallback = v1).
- Overlay: B_new(t) = 1 if v1_B(t) == 3 and ON(t), else v1_B(t). av23s(.85) brake, fstep .1, 2-day delay unchanged.
- Constants 126, 0.25, 2-of-3, country set and the 3x->1x move are fixed by the court a priori. No threshold, window,
  country-set, '>= 1' or BIS-nine-bank variant is run. N = 1, so the deflation factor sqrt(1 + ln N) = 1.
- SPX real bases: ON forced False before 1960-01-04 (court: covered from 1960; 1955-59 = v1 B).

## 5. Kill test: type A (brief section 4, thresholds copied, not relaxed)
Brief text: "A CUT overlay on v1 (move v1 3x -> 1x/cash when the signal fires): in 21-day blocks where v1 is at 3x,
P(3x beats deposit | signal on) must be >= 10pp BELOW the base rate of v1-3x blocks, with >= 8 'on' blocks, in BOTH windows."
- Blocks: gate._frame grid (non-overlapping 21-trading-day blocks). Label of block at close t = 3x product (3r - 2rf - 2.45%/yr)
  beats deposit ((rf - 2pp)+ x 0.846) over trading days t+3..t+23 (exactly gate._frame).
- Universe: blocks with v1_B(t) == 3 at block-start close t (era's real context). Signal = ON(t) at block-start close t.
- Windows (block membership):
  * early, era SPX: block start t in [1960-01-04, 1985-12-31] (SPX grid; labels end <= 1985-12-31 by construction).
  * early, era NDX: block start t >= 1986-01-02 AND label end day (t+23) <= 1999-12-31 (the block straddling into 2000 is dropped
    from both windows so no 2000+ return enters the early test).
  * unseen: NDX block start t >= 2000-01-03 (labels end <= 2014-12-31). Opened ONCE, only if early passes.
- Early statistic (court, pooled with era-matched base): base_e = hit rate of all universe blocks of era e; hit_on,e = hit rate of
  universe blocks with ON; drop = sum_e n_on,e x (base_e - hit_on,e) / sum_e n_on,e; n_on = sum_e n_on,e.
  NDX-only and SPX-only drops are reported, but do not gate.
- Unseen statistic: drop = base - hit_on over NDX 2000-2014 universe blocks; n_on.
- PASS A iff drop >= 0.10 AND n_on >= 8, in BOTH windows. Binomial SE of hit_on reported as information only.

## 6. Pass / fail actions
- Early FAIL -> stop, unseen never opened, kill_verdict FAIL, CLOSE + registry row proposal.
- Early pass -> unseen once with the identical rule. Unseen FAIL -> FAIL, CLOSE + registry row.
  An unseen pass is discounted (the idea generator knew the 2000 and 2005-07 foreign tightening history).
- Both pass -> L.measure2('OV1-C', make2) with B_new on all 5 bases:
  real_ndx_86_14 / real_spx_55_85 / real_spx_70_85: ON from the full-calendar X_c (identical to the kill test), indexed by c.ii;
  dev250_path (HEADLINE): x_c = L.path_series(X_c, 'dev250_path'), ON along each path row;
  dev250_glued (upper bound only): x_c = L.gather(X_c, 'dev250_glued'), ON along each path row.
  FINAL PASS iff HEADLINE_MS1 > 0.1616 AND REAL_NDX > 0.3108 AND dev250_path pw_vs_s085 >= 0.55 AND real_spx_55_85 cagr >= v1's
  real_spx_55_85 cagr - 0.01. dd80 reported. N = 1, deflation factor 1. Any failure -> CLOSE + registry row.
  Information-only PIT sensitivity if measure2 is reached: monthly values lagged 2 more months (usable from m+3); not a variant,
  not counted in N, cannot rescue a fail; if it flips a pass, that is reported as a caveat.
- Every counted result -> ledger.csv (lane,variant,window,metric,value) and results/*.json; RESULT_OV1-C_KO.md in Korean.
- lab 사용: 아니오 (foreign policy rates are not in the lab panel).
