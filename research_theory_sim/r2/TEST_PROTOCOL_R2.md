# TS2 (round 2) real-history test protocol (fixed BEFORE any round-2 design work)

Lane: TS1 "theory first, synthetic design, one real test", round 2 (thread '과거 안 보고 이론으로 매매법 만들기'; user
2026-11-04 10:28Z: "그거 스스로 검토해서 다시 진행해봐. 이거 계속 문제 파악 후 개선하면 결국 좋아지지 않겠어?";
10:29Z: xhigh + parallel workers). Written by the orchestrator before any round-2 designer started. Designers do not read
this file. It contains no post-2014 number.

## 0. Why round 2, and what iterating costs
Self-review of round 1 (all facts <= 2014, from research/theory_sim/RESULT_TS1_KO.md):
1. The theories' premium priors were far below the real headline index: synthetic 1x hold about 3-5% vs real 11.6% MS1, so
   the Kelly-type rules held 0.3-0.4x on average. Cause in the brief: "priors WIDE and argued from first principles, no
   remembered averages" pushed every designer to a low, conservative premium.
2. In the synthetic tournament the 1x hold (3.81%) beat every rule: no design gate required beating hold or the best
   constant level in the designer's own world.
3. Price + rate inputs carry the same information as the G1-closed axis (all three rules G1 CLOSE, best 47.6%).
4. L2 levered 1.4-1.8x into a decade of rising rates (SPX 1955-85 MDD -91%): the priors had no long rate regimes.
5. Five harness defects (verifier): G1 era merge, causality by truncation, missing PRECOMMIT file name, NDX warm-up zeros,
   pre-1952 Saturday sessions in SPX 1929-85.
Changes for round 2: brief sections 2b (published central anchors, no haircut), 2c (unknown market, online learning
allowed, per-path premium/volatility), 2d (long rate regimes), 3 design gates G-ON / G-OFF; four lanes instead of three;
harness fixes in r2/test/harness_r2.py and post2014_r2.py.

Cost of iterating (stated now, before any round-2 result):
- The brief changes were made AFTER seeing round-1 real results on all US bases. Round-2 rows on US data are therefore a
  SECOND LOOK, not a clean out-of-sample test. Cumulative real-data trials on the US bases: N = 3 (round 1) + 4 (round 2) =
  7 rules in 2 rounds. The project-measured selection premium of 3-8 pp (research/measure_std/MEASURE_STD_KO.md section 3)
  applies to any best-of-rounds choice.
- Published long-run equity averages (section 2b of the brief) are themselves computed from history that overlaps the
  US test bases: a level-only look-ahead that round 1 did not have. It cannot tell a rule when to trade.
- The fresh confirmation set E below has never been run by any rule of this lane. It is opened once, after the freeze.

## 1. What is tested
- Frozen: `r2/design/{A,B,C,D}/rule.py` (+ THEORY.md, sim.py, design_log.md, AUDIT.md, synth_results.json) and the
  tournament folder, hashed by `r2/test/freeze_r2.sh` into `r2/FREEZE_TS2.txt` and committed to git before any real run.
- PRIMARY = winner of the blind synthetic tournament (brief section 7). Secondaries are reported as rows.
- Round-1 comparator: `design/L1/rule.py` (sha256 acc4cf0c..., FREEZE_TS1.txt) on every new basis.
- No re-tuning after the real test. Any later variant is round 3 (new N, new protocol, new fresh set).

## 2. Engine and inputs
- MS1 engine exactly, as TS1 section 2 (std.py sha ee4de887037c; beng F1; identity brake; fstep 0.5).
- Country funds: r = daily return of the adjusted close (panel column 4) on the US trading calendar; rf, y10 and the macro
  flags used by the s0.85 reference are the US series of that date (a USD investor holding a synthetic 3x product on the
  fund plus USD cash). Same costs, delay and tax as MS1.

## 3. Bases (all reported, nothing dropped)
A. MS1 standard via TS1 harness.measure (SECOND LOOK): dev250_path (HEADLINE), dev250_glued, real_ndx_86_14,
   real_spx_55_85, real_spx_70_85; each with same-basis 1x/2x/3x hold, s0.85, paired difference and win share.
B. real_spx_29_85: reported per 252 days (MS1 style) and per calendar year (primary for this basis).
B2. Warm-up sensitivity: real_ndx_86_14 with the closes before 1985-10-01 fed to the rule as NaN (engine unchanged).
E. FRESH CONFIRMATION, opened once after the freeze: country funds EWA, EWC, EWG, EWJ, EWU (first day 1996-03-18) and
   EWT, EWY, EWZ (first days 2000-05/07), one real path each from the fund's first day (300-day warm-up) to 2014-12-31.
   Data check done before design (no rule run): no missing US trading days, one |daily move| > 25% (EWZ 2008-10-13,
   +25.6%, a real move). Per fund: round-2 primary and secondaries, round-1 L1, s0.85, 1x/2x/3x hold.
   Stress rows on E: delay 3 and cost 0.6%.
C. Post-2014, USER ONLY (files under holdout/r2/, never memory, never other threads): US C1-C3 as TS1 section 3C;
   the 8 funds from 2015-01-02 (warm-up before) to the panel end.

## 4. Conservative checks
- delay 3, delay 5, cost 0.6% on dev250_path and real_ndx_86_14 (primary and secondaries).
- G1 (research/breakthrough/code/gate.py) with each era fed its own market's target; sig = (target >= 1.5) and
  (target > 0); trials = 7 (3 round-1 rules + 4 round-2 rules).
- Causality by future perturbation: >= 150 cut points x 3 continuations on real NDX <= 2014 (close, rf and y10 replaced
  after the cut, including NaN / zero / negative garbage), plus a multi-path and cross-path check on dev250_path. Exact.

## 5. Verdict words (fixed now)
- GO-LIVE BAR: MS1 headline >= 30.0% AND on E the primary beats s0.85 (median paired difference > 0 and >= 5 of 8 wins).
- BEATS s0.85: MS1 headline > 16.2% AND paired win share > 50% on dev250_path AND on E: median (primary - s0.85) > 0
  and >= 5 of 8 wins.
- BEATS HOLD: MS1 headline > same-basis 1x hold (11.6%) AND on E: median (primary - 1x hold) > 0 and >= 5 of 8 wins.
- IMPROVES ON ROUND 1: MS1 headline > round-1 L1 (5.34%) AND on E: median (primary - round-1 L1) > 0 and >= 5 of 8 wins.
- A level that fails either half is FAIL at that level. All US rows carry the label 'second look'. Post-2014 rows are
  confirmation only and cannot turn a FAIL into a pass.
- The 8 funds share global shocks: they are not 8 independent tests.
- If the user later prefers a secondary or a round-1 rule because of its real-data rows, that is a best-of-7 real
  selection and must be labelled so.

## 6. Round-2 lanes (theory families)
A. Crowd and leverage. B. Learning about the premium (investors who learn the drift and risk of the market).
C. Rare disasters and crash risk. D. Intermediaries, funding and monetary regimes.
