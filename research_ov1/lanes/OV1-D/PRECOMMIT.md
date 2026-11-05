# PRECOMMIT OV1-D: Tankan expectation error cuts v1 3x -> 1x (type A CUT overlay on v1)

Written 2026-11-05, before any signal on-date, block label, base rate or strategy return of this lane was computed.
Step-1 inspection (code/s1_inspect.py -> results/s1_inspect.json, results/s1_surprise_table.csv) looked only at the
INPUT data: parse/rebuild check against the scout's cut file, nulls, value grid, usable-date roll, release spacing and
threshold availability, plus descriptives of the surprise values over 1974-2014 (mean -0.59, sd 9.5, range -28.5..28.5,
all multiples of 0.5). No release-level on/off flag, no label, no v1 state and no return was looked at.
idea_check flags T28 (BT1) on the single word "surprise"; BT1's 48 sources are US releases vs naive means and contain no
Tankan or any non-US firm forecast error, so this is the court's new information family (non-US firms' own expectation errors).

## 1. Hypothesis (court)
Surprise_q = Actual DI(q) - Forecast DI(q) of large Japanese manufacturers (all manufacturing and electrical machinery),
the forecast made one survey earlier, is an unrevised aggregate expectation error. A bottom-tercile value is an
unanticipated global manufacturing / electronics shock. If US tech prices do not fully absorb it within the 2-day
execution delay, v1 at 3x does worse over the next month, so moving v1 3x -> 1x while it is on should help.

## 2. Data (frozen)
- data/boj_tankan_cut_le2014.csv sha256 89ff76734e41bd25178d64162d2cf50e2122eeaad5eec1c62ebede8ca686b2bc, 164 rows
  (quarter codes 197401..201404), derived from data/boj_tankan_raw.csv sha256 ab49c62a5cc8e48c7fecbb2feb9d37671ffd71a2b4769ab5cec0ee61fdc3f1ff
  (BoJ API, endDate=201404; source URL in data/MANIFEST.json). Step 1 rebuilt every column from the raw file: max abs diff 0.
- Series: TK99F1000601GCQ01000 / ...GCQ11000 (large mfg actual / forecast), TK99F1150601GCQ01000 / ...GCQ11000
  (large electrical machinery actual / forecast). Forecast value at quarter code q = forecast FOR q, made in survey q-1.
- Lane code reads only the cut csv, recomputes the surprise from its four component columns and asserts equality.
- Caveat (not measurable here): single current BoJ vintage; periodic sample re-basings (forecast on the old sample vs
  actual on the new one) are not flagged by BoJ except the Dec 2003 / Mar 2004 break, which is set to NaN.

## 3. Point-in-time rule (fixed, conservative, never tightened)
- Calendar: the shared Ken French trading calendar of jp.calendar('1928-01-03','2014-12-31') (the NDX and SPX frames are
  subsets of it).
- U_q = first trading day on/after the 1st calendar day of the 2nd month after q's end month (Mar->May, Jun->Aug,
  Sep->Nov, Dec->Feb). Step 1: roll-forward at most 2 calendar days; release spacing 61-66 trading days (125 across
  the 2004Q1 NaN). Old Feb/May/Aug/Nov survey months (1970s-80s) carry the same quarter codes and the same lag.
- The value of release q is used at close U_q and later (ON(t) uses the latest release with U_q <= t). The engine then
  applies v1's 2-day execution delay; the kill-test label starts at t+3. 2014Q4 (U in 2015) is never used.

## 4. Signal (exact; N = 1, no threshold or lag search)
- surprise_q = ((A_mfg - F_mfg) + (A_el - F_el)) / 2. NaN for 1974Q1, 1974Q2 (no forecast) and 2004Q1 (BoJ break).
- thr_q = np.percentile(valid surprises with U < U_q, 33.33) with numpy 2.5.4 default method 'linear' (the court text
  "33.33rd percentile" taken literally, not 100/3). Requires >= 20 valid prior surprises, else thr_q = NaN.
  Step 1: the 20th valid surprise is 1979Q2 (U = 1979-08-01), so with U strictly earlier the first release WITH a
  threshold is 1979Q3 at U = 1979-11-01 (court said "about 1979-08"; the exact formula governs).
- on_rel_q = (surprise_q <= thr_q); False when either is NaN. ON(t) = on_rel of the latest release with U_q <= t, held
  until the next release; False before 1979-11-01. The 2004Q1 release (U = 2004-08-02) has NaN surprise, so it switches
  the signal OFF until the 2004Q2 release.
- Code: code/tankan_sig.py sha256 96c1748ab3a7d75b42940bb64eb89f890c681db98d083d7c96aacbbf2f635f6a (releases, on_daily,
  step_series, on_path, overlay).

## 5. Overlay and MS1 bases (used only if both kill windows pass)
- B_new = 1 where L.v1_B == 3 and ON, else L.v1_B. Brake L.v1_parts(c) (av23s .85, fstep .1) and 2-day delay unchanged.
- real_ndx_86_14: ON = L.gather(on_daily) (identical to the kill-test series).
- dev250_path (HEADLINE): step series S (cumulative surprise, stepping on each U_q; NaN surprise steps 0), release flag
  F (1 on every U_q day, else 0), T (thr_q on release days, sentinel -1e9 when thr is NaN, forward-filled). On each path
  row: the latest surprise at day t = jump of L.path_series(S) on the last path day j <= t with L.gather(F) == 1;
  ON(t) = jump_j <= L.gather(T)_j. Path day 0 has no jump -> treated as a release with no information (OFF). Before the
  first release on a path: OFF (v1). No fixed-lag difference of S is used.
- dev250_glued (upper bound only): ON = L.gather(on_daily, 'dev250_glued').
- real_spx_55_85 / real_spx_70_85: ON = L.gather(on_daily) (covered from 1979-11-01; before that ON = False -> v1 B).
- Checks to run before measure2 numbers are read: on_path on the real basis equals gather(on_daily); on dev250_path the
  court construction equals a direct source-index construction.

## 6. Kill test: type A (brief section 4, thresholds copied, not relaxed)
Brief text: "A CUT overlay on v1 (move v1 3x -> 1x/cash when the signal fires): in 21-day blocks where v1 is at 3x,
P(3x beats deposit | signal on) must be >= 10pp BELOW the base rate of v1-3x blocks, with >= 8 'on' blocks, in BOTH windows."
- Blocks/labels: gate._frame grids, NDX ('NDX','1984-01-03','2014-12-31','1986-01-02') and SPX
  ('SPX','1928-01-03','1985-12-31','1955-01-03'). Label of block at close t = 3x product (3r - 2rf - 2.45%/yr) beats deposit
  ((rf - 2pp) x 0.846) over trading days t+3..t+23.
- Universe: blocks with v1 target == 3 at block-start close t (L.v1_B on a context built exactly like std.contexts()
  real_spx_55_85 / real_ndx_86_14). On-block: universe block with ON(t) True.
- Early window (eras): SPX blocks with 1979-08-01 <= t <= 1985-12-31 (court bounds; ON is False until 1979-11-01, those
  blocks count in the SPX base only) and NDX blocks with t >= 1986-01-02 and label end (t+23) <= 1999-12-31 (the block
  whose label straddles into 2000 is dropped from both windows). Unseen window: NDX blocks with t >= 2000-01-03.
- base_era = label mean over universe blocks of the era; hit_on,era = label mean over its on-blocks.
  drop = sum_era n_on,era x (base_era - hit_on,era) / sum_era n_on,era (era-matched). Unseen has one era (drop = base - hit_on).
- PASS A in a window iff drop >= 0.10 (float tolerance 1e-12) AND total n_on >= 8. Must pass in BOTH windows.
  NDX-only early numbers are reported and do not gate.
- Code: code/s2_killA.py sha256 2b3d3309aa6214c9aec71b475341cd6ed47f7362bb66941aa67117c05ba7fac7 (asserts this file's sha256;
  'unseen' refuses to run unless results/killA_early.json has early_pass true and refuses a second opening).
- Deflation: N = 1 (one variant, no alternative threshold, lag, sector mix or hold rule computed), so sqrt(1 + ln N) = 1.
  Binomial SE of hit_on reported as information.

## 7. Pass / fail actions
- Early FAIL (either condition) -> stop; unseen never opened; measure2 not run; kill_verdict FAIL; CLOSE + registry row
  proposal in results/ (nothing written outside the lane folder).
- Early pass -> unseen once (same code, same rule). Unseen FAIL -> FAIL, CLOSE + registry row.
- Both pass -> L.measure2('OV1-D', make2) on all 5 bases with section 5. FINAL PASS iff HEADLINE_MS1 (dev250_path cagr)
  > 0.1616 AND REAL_NDX > 0.3108 AND dev250_path pw_vs_s085 >= 0.55 AND real SPX not worse than v1 by > 1pp where covered:
  (i) real_spx_55_85 cagr - v1 >= -0.01 and (ii) annualized growth of the engine equity curve EE (aligned to context dates
  after warm-up) from the first trading day >= 1979-08-01 to 1985-12-31, candidate - v1 >= -0.01. dd80 reported; glued
  reported as an upper bound only; N = 1 and no deflation stated. Any failure -> CLOSE + registry row.
- Every counted result goes to ledger.csv (lane,variant,window,metric,value) and results/*.json; RESULT_OV1-D_KO.md in Korean.
