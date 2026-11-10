# CAPIT amendment A1 (FINAL1) - written 2026-11-10 15:3xZ, after the CAP1/CAP2 no-sample fail and BEFORE any A1 computation

Parent: lanes/CAPIT/PRECOMMIT.md sha256 ec06110c92bf... (unchanged). Frozen definitions: code/cap.py (CODE_FREEZE.sha256, unchanged).

## Why
CAP1/CAP2 (Nasdaq volume >= 2.0x / 2.5x the previous-60-day median) gave 0 trigger days in 1986-1999, so the user's idea
(RSI bottom + abnormal volume) was never measured. The verifier and the judge both labelled it "no-sample fail, not a measured negative".

## What had been seen before this was written (contamination statement)
- Signal side only, early window: volume-ratio percentiles 99% = 1.51 and 99.9% = 1.95; 78 days with RSI(14) <= 30, max ratio on them 1.94.
- Trigger COUNTS at the 2.0x / 2.5x thresholds in 2000-2014 (1 day / 0 days). No outcome.
- The descriptive DEPTH table (forward returns after -30..-70% drawdown crossings, including 2000-2014).
- No outcome (hit rate, return, engine result) of any RSI + volume trigger has been computed or seen.
Status: a threshold changed after a result = contaminated amendment. A FAIL is a measured negative and closes the idea.
A PASS is only a candidate: it needs an independent verifier and the user's decision, and is reported with this label.

## Variants (N = 2 here; lane total N = 4)
- CAPA1: RSI(14) <= 30 AND volume ratio >= 1.5 at close t. Effect window 42 trading days.
- CAPA2: RSI(14) <= 30 at least once in t-2..t AND max volume ratio in t-2..t >= 1.5. Effect window 63 trading days.
1.5 = the early-window 99th percentile of the ratio (1.51) rounded. Nothing else changes: Wilder RSI on the context / path price,
ratio = volume / median(previous 60 rows) glued from the source date, overlay B' = 3 where ON and the v1 base target < 3, v1 brake unchanged
(av23s .85, fstep .1). S&P 1955-85 bases: no Nasdaq volume -> equal to v1 (not covered).

## Measurement (no kill-test gate: the type-B universe has only 31 early blocks; trigger list is printed as information)
Direct engine runs on real_ndx_86_14, dev250_path (headline) and dev250_glued (upper bound), each against v1 under the SAME terms:
base, delay 3, cost x2. This opens the 2000-2014 outcomes of these two variants once.
Attribution on real NDX (base terms): overlay active only in 1986-01-02..1999-12-31, and only in 2000-01-03..2014-12-31.

## Rule
PASS (candidate) = path paired median d >= +0.5pp AND path win ratio >= .55 AND real NDX d > 0
                   AND both signs kept at delay 3 and at cost x2 AND real-NDX attribution d >= 0 in both halves.
Anything else = FAIL (measured). No further threshold, window or RSI variants after this run.
Outputs: results/capA_measure.json; section "A1" appended to RESULT_CAPIT_KO.md.
