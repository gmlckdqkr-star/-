# TS1 real-history test protocol (fixed BEFORE any design work)

Lane: TS1 "theory first, synthetic design, one real test" (thread '과거 안 보고 이론으로 매매법 만들기', user request 2026-11-04 07:03Z).
Written by the orchestrator before any designer started. Designers do not read this file (they get DESIGN_BRIEF.md only).
No real-data result appears in this file.

## 1. What is tested
- Frozen files: `design/L1/rule.py`, `design/L2/rule.py`, `design/L3/rule.py` (+ their THEORY.md / sim.py for the record),
  hashed in `design/tournament/PRECOMMIT_TS1.md` and committed to git before any real data is touched.
- PRIMARY = the lane rule chosen by the blind synthetic tournament (score fixed in DESIGN_BRIEF.md §7). The headline is the
  primary only. The other lane rules are reported as secondary rows. Real-data trials N_real = number of lane rules (3).
- No re-tuning after the real test. Any later variant is a new lane (new N, new precommit).

## 2. Engine and inputs
- MS1 engine exactly (research/measure_std/std.py, sha ee4de887037c...; beng F1: delay 2, 0.3%/side, 22% yearly tax with
  deduction 0.25, final liquidation tax, 3x = 3r - 2rf - 2.45%/yr, cash = max(rf-2%,0)*0.846, 0.5 steps, fstep 0.5,
  identity brake). The designers' common/exec_engine.py is parity-checked against it (test/parity_engine.py, max diff 0).
- Rule inputs: close = ctx.lvl (index level of the path), rf = ctx.rf, y10 (only if INPUTS has it): real bases = real daily
  y10 of that date; dev250_glued = original-date y10; dev250_path = path-reconstructed y10 (start value + cumulated
  resampled daily changes, the same construction std.path_flags uses).

## 3. Bases (all reported, nothing dropped)
A. MS1 standard via std.measure: dev250_path (HEADLINE), dev250_glued (upper reference), real_ndx_86_14, real_spx_55_85,
   real_spx_70_85; each with same-basis 1x/2x/3x hold and the s0.85 reference + paired difference and win share.
B. Extra out-of-era (the rule was designed blind, so all of it is out of sample): real_spx_29_85 = real S&P 500 from the
   first trading day after the 300-day warm-up (1929) to 1985-12-31, one path.
C. To now (post-2014, reported to the user only; never written to memory or sent to other threads; files under holdout/):
   C1 real NDX 2015-01-02 -> last available close, one path (300-day warm-up from 2013-2014 data);
   C2 real NDX 1986-01-02 -> last available close, one path ("past to now");
   C3 real-product check for the C1 period: actual TQQQ daily total return in place of the synthetic 3x product where the
      data exist (else row omitted with reason).
   Each with same-basis 1x/2x/3x hold and s0.85 on the same path.

## 4. Conservative stresses (on dev250_path and real_ndx_86_14, primary and secondaries)
- delay 3 (+1 day) and delay 5 (+3 days); cost 0.6%/side. Reported next to the base row.
- G1 information gate (research/breakthrough/code/gate.py) on sig = (target >= 1.5) and on sig = (target > 0), trials = 3.
- Causality test on the frozen rule (future perturbation at >= 100 random cut points on real <= 2014 data): must be exact.

## 5. Verdict words (fixed now)
- GO-LIVE BAR (user 2026-11-04): MS1 headline (dev250_path median after-tax CAGR) >= 30.0%.
- BEATS s0.85: MS1 headline > s0.85 MS1 headline on the same run (locked 16.2%) AND paired win share > 50% on dev250_path.
- Otherwise: FAIL (reported as is, with all rows). Post-2014 rows are confirmation only; they cannot turn a FAIL into a pass.
- Selection deflation: the primary was chosen on synthetic data only (no real-data selection). If the user later prefers a
  secondary because of its real-data rows, that is a best-of-3 real selection and must be labelled so.
