# TS2 round 2 - verifier V1 report (data up to 2014-12-31 only)

Written 2026-11-04T13:05Z by verifier V1. Independent code in this folder (`V1_*.py`); it calls the locked MS1 standard
(`research/measure_std/std.py`, sha ee4de887037c) directly and does not import `harness_r2.py`, `post2014_r2.py` or the
TS1 `harness.py`. Nothing under `theory_sim/holdout/` was opened; every series was cut at 2014-12-31 before use
(the S&P bases end 1985-12-31). No existing file was changed. Git was used read-only (log, show, ls-tree, branch --contains).

## Short answer

- **Every reported number reproduces.** MS1 (5 rules x 6 bases x base + 3 stresses), the fund confirmation E (4 rules,
  744 numbers), G1 and causality all match `r2/test/out/real_*.json`. The largest difference anywhere is 0.0006 pp, from
  a one-day convention in the calendar-year conversion of real_spx_29_85. No win count changes.
- **Primary D fails three of the four verdict levels and passes "improves on round 1".** GO-LIVE FAIL, BEATS s0.85 FAIL,
  BEATS HOLD FAIL, IMPROVES ON ROUND 1 PASS (second look on the US half). The pass is weak: D is a tracked constant
  exposure of about 1.25, not a timing rule. It beats L1 because L1 held only about 0.37x on average. The plain 1x hold
  beats L1 by more, on MS1 and on 8 of 8 funds.
- **No leak found.** The freeze holds: 211 of 211 hashes match, git commit 4a57503 holds the same four rule.py files, and
  the protocol, brief and harness are unchanged since the pre-design hash at 10:46Z. In my perturbation test D's output at
  t is unchanged by any change after t (1332 changed futures, 222 truncations, multi-path and cross-path checks).
- **Notes, not errors:** (1) D's t0 is the same minute as the freeze (12:24Z). Minute-level timestamps cannot prove the
  order to the second, but they are consistent with it. (2) The real_spx_29_85 row of D depends on the pre-1952 Saturday
  rows, which have zero returns: removing them moves D by -1.4 pp per calendar year. (3) s0.85 on the funds is very
  sensitive to the delay setting (single paths, country ETFs that reverse day to day), so the E comparison against s0.85
  is noisy. D still fails it at every delay from 1 to 6.

## 1. Freeze integrity (`V1_freeze.py` -> `V1_freeze.json`)

| Check | Result |
|---|---|
| sha256 lines in FREEZE_TS2.txt vs current files | 211 / 211 match; no missing file; no file in r2/design that the freeze leaves out |
| git 4a57503 (2026-11-04 12:24:21Z, on origin/claude/project-thread-hhwozh) | rule.py of A/B/C/D in git = freeze = current (09bcfa96, 8051732d, 861d9b27, 6246c68a); FREEZE_TS2.txt in git identical; all 204 frozen design files in the git tree with the frozen hashes |
| pre-design hashes (SHA256SUMS_PRE_DESIGN_R2.txt, 10:46Z) | brief, protocol, harness_r2.py, post2014_r2.py, freeze_r2.sh identical now |
| t0 of real_*.json vs freeze 12:24Z | A 12:28Z, B 12:29Z, C 12:29Z: after. **D 12:24Z = same minute** (D json written 12:28:21Z, about 4 min of run time, as A to C; commit at 12:24:21Z). Consistent with "after", not provable at minute resolution |
| earlier real runs | only val_R1L1 / val_sma_y10 (10:46-10:47Z, round-1 L1 and a control; no round-2 rule existed) |

## 2. MS1 recomputation (`V1_ms1.py` -> `V1_ms1_D_A_B_C_L1.json`)

176 compared numbers per rule (cagr, mdd, w7, w12, p10, dd80, dd95, paired d and win share vs s0.85, s0.85, 1x/2x/3x
hold, average target, cash share), base plus delay 3 / delay 5 / cost 0.6% on dev250_path and real_ndx_86_14: all
differences are 0. The only nonzero difference, 6e-6 (0.0006 pp), is in the real_spx_29_85 calendar conversion. The
harness counts calendar years as days/365.25 + 1/252 and I count days/365.25. Round-1 L1 reproduces real_L1.json
(headline 5.3406%). s0.85 reproduces the locked values (16.16 / 27.03 / 31.08 / 11.94 / 12.63%). Passing garbage y10
changes no rule's output. No rule changes its inputs.

MS1 after-tax CAGR, median over paths (US rows are a second look):

| Rule | dev250_path (headline) | dev250_glued | real NDX 86-14 | real SPX 55-85 | real SPX 70-85 | real SPX 29-85 per 252 d / per cal. yr |
|---|---|---|---|---|---|---|
| **D (primary)** | **9.60%** (MDD -80.6%, P(MDD<=-80%) 52.0%, p10 1.5%) | 9.60% | 9.76% (MDD -92.1%) | 8.73% | 7.57% | 7.82% / 8.36% |
| A | 9.83% (MDD -60.4%, dd80 4.2%) | 9.83% | 11.75% | 6.93% | 7.09% | 5.42% / 5.80% |
| B | 6.57% | 6.57% | 6.81% | 5.42% | 4.74% | 5.30% / 5.66% |
| C | 3.48% | 3.48% | 5.91% | 8.38% | 4.16% | 2.03% / 2.17% |
| L1 (round 1) | 5.34% | 5.34% | 5.54% | 8.17% | 7.37% | 7.48% / 8.00% |
| s0.85 | 16.16% | 27.03% | 31.08% | 11.94% | 12.63% | 5.76% / 6.16% |
| hold 1x | 11.64% (dd80 17.6%) | 11.64% | 11.53% | 9.00% | 8.43% | 7.58% / 8.11% |
| hold 2x | 10.48% | 10.48% | 10.11% | 9.04% | 5.96% | 6.33% / 6.77% |
| hold 3x | 4.23% | 4.23% | 3.87% | 9.84% | 4.35% | 3.91% / 4.17% |

On dev250_path, D beats s0.85 on 10.6% of paths and the 1x hold on 6.8% (median paired difference -7.23 pp and -2.17 pp).
dev250_glued equals dev250_path for every rule here because none of them reads the macro flags.

Stresses (rule / s0.85 at the same delay or cost; holds unstressed):

| D | dev250_path | real NDX 86-14 |
|---|---|---|
| base | 9.60 / 16.16 | 9.76 / 31.08 |
| delay 3 | 9.53 / 16.34 | 10.12 / 30.85 |
| delay 5 | 9.83 / 16.16 | 9.66 / 29.63 |
| cost 0.6% | 9.50 / 15.14 | 9.63 / 29.90 |

All stresses of A, B, C and L1 also reproduce exactly (see json). A gains under delay: real NDX 11.75 -> 13.00% at delay 3.

**real_spx_29_85 and the Saturday sessions** (`V1_spx29_sat.py`, `V1_spx29_start.py`). The calendar has 1084 Saturday
sessions before 1952 (1038 in the measured window). On every one of them the S&P return is exactly 0: the S&P series has
no Saturday value, and the calendar does. Meanwhile rf, the product fee and the hold fee still accrue per session, and the
engine's tax year is 252 sessions. The protocol's calendar-year annualisation fixes the year count (60.80 years by 252
sessions, 56.98 calendar years). It does not remove the effect of these rows on rules. With the same measured start
(1929-06-03), per calendar year:

| Basis | D | A | L1 | s0.85 | hold 1x |
|---|---|---|---|---|---|
| with Saturday rows (protocol basis) | 8.40% | 5.95% | 8.16% | 5.99% | 8.10% |
| Saturday rows removed | 6.96% | 6.15% | 8.26% | 6.03% | 8.12% |

The same number of zero sessions placed on random weekdays gives D 6.9-7.5% (6 draws). Scaling one 1930-35 daily return
by 1 +/- 0.001 does not change D. Moving the start of the path by 0-120 sessions changes D only within 8.08-8.39%. So
D's +0.25 pp lead over the 1x hold on this basis comes from where the zero-return Saturday sessions fall. With them
removed, D is 1.2 pp behind the hold. This basis is not part of the verdict words, but D's "beats hold on S&P 1929-85"
row should not be cited.

## 3. Fresh confirmation E, re-implemented (`V1_conf.py` -> `V1_conf_price.json`, `V1_conf_ret.json`)

My own build: adjusted close (panel column 4) cut at 2014-12-31, US calendar 1990-2014, US rf / y10 / macro flags, path
from the fund's first day, measured after 300 days. Data check: no fund day off the US calendar, no US day without a fund
price, and both ways of building returns (price reindexed, or the harness's pct_change then reindex) give identical rows.
All 744 compared numbers (rule, L1, s0.85, holds, start dates, summary medians and wins; base, delay 3 and cost 0.6%) equal
the harness values exactly.

Per fund, base (after-tax CAGR):

| Fund (measured from) | D | A | B | C | L1 | s0.85 | hold 1x | hold 2x | hold 3x |
|---|---|---|---|---|---|---|---|---|---|
| EWA (1997-05-23) | 6.18 | 4.79 | 2.65 | -0.58 | 0.90 | 1.94 | 6.83 | 2.24 | -7.61 |
| EWC (1997-05-23) | 5.13 | 7.12 | 1.41 | 0.27 | 3.06 | 10.41 | 6.91 | 4.44 | -1.41 |
| EWG (1997-05-23) | 0.98 | 0.82 | -1.21 | 3.48 | 0.24 | 6.86 | 4.44 | -1.96 | -13.98 |
| EWJ (1997-05-23) | -3.28 | -2.70 | -0.10 | 0.78 | -0.17 | -6.38 | 0.06 | -10.04 | -22.71 |
| EWU (1997-05-23) | 0.91 | -0.33 | 0.92 | 0.85 | -0.57 | 4.32 | 3.46 | -2.23 | -11.82 |
| EWT (2001-08-31) | -0.53 | 2.11 | -0.44 | 0.41 | 2.56 | -1.71 | 5.16 | -1.42 | -15.71 |
| EWY (2001-07-23) | 8.10 | 6.16 | -0.50 | 0.43 | 0.11 | 12.37 | 10.65 | 6.07 | -7.61 |
| EWZ (2001-09-27) | 9.83 | 8.05 | -1.75 | 0.40 | -1.08 | 11.84 | 12.76 | 7.13 | -12.07 |

Summary, median paired difference (pp) and wins out of 8 (win = difference > 1e-5; > 0 gives the same counts):

| Rule | set | rule median | vs L1 | vs s0.85 | vs hold 1x |
|---|---|---|---|---|---|
| **D** | base | 3.05% | **+1.77, 6/8** | -2.71, 3/8 | -2.74, 0/8 |
| D | delay 3 | 2.98% | +1.55, 6/8 | -4.07, 2/8 | -3.29, 0/8 |
| D | cost 0.6% | 2.95% | +2.10, 6/8 | -1.31, 3/8 | -2.91, 0/8 |
| A | base | 3.45% | +2.23, 6/8 | -3.54, 3/8 | -3.34, 1/8 |
| A | delay 3 / cost | 4.15 / 3.09% | +2.64, 7/8 / +2.05, 6/8 | -4.65, 3/8 / -2.64, 3/8 | -2.34, 0/8 / -3.69, 0/8 |
| B | base | -0.27% | -0.64, 3/8 | -5.73, 3/8 | -5.55, 0/8 |
| C | base | 0.42% | +0.64, 5/8 | -3.43, 2/8 | -5.69, 1/8 |

D beats the 2x and 3x holds on 8/8 funds. On the funds D holds an average target of 1.11-1.32 and is never in cash.

**Why s0.85 moves so much between delay 2 and delay 3 on the funds** (`V1_s085_funds.py` -> `V1_s085_funds.json`). It
does move a lot: +0.35 to +4.88 pp per fund, larger on all 8 funds. Fund median by delay 1..6: 8.5, **5.6**, 9.7, 8.9,
7.5, 5.0%. So the base setting (delay 2) sits near the bottom of a ±2-4 pp timing-noise band. Three reasons:
1. Each fund is one path, and s0.85 trades 3.6-10.9 times a year between cash and up to 3x. The result is decided by the
   returns on a few hundred days next to its trades.
2. The country ETFs reverse from day to day much more than the NDX: lag-1 autocorrelation is -0.04 to -0.13 for 7 funds
   and -0.01 for EWZ, against -0.02 for the NDX. On average the fund fell the day after s0.85 raised its level (6 of 8
   funds) and rose the day after it cut (8 of 8). That next day is earned at the new level under delay 2 and at the old
   level under delay 3. Summed over the path, this one-day effect is about 0.8-3.7%/yr per fund and tracks the measured
   delay-3 gain (EWU 3.6 vs 4.35 pp, EWT 3.7 vs 3.84, EWG 2.75 vs 4.88, EWY 2.4 vs 2.75).
3. On the NDX the same effect is small (-0.23 pp from delay 2 to delay 3).
The verdict does not depend on this noise: D against s0.85 has 2-4 wins of 8 at every delay from 1 to 6. D against L1
has 6, 6, 6, 5, **4**, 5 wins at delays 1-6, so the E half of "improves on round 1" would fail at delay 5. Only the base
and the delay 3 / cost rows are fixed by the protocol.

## 4. G1 (`V1_g1.py` -> `V1_g1.json`), trials 7, each era fed its own market's target

| Rule | sig | NDX 86-14 hit (n 348) | SPX 55-85 hit (n 370) | lower deflated | verdict |
|---|---|---|---|---|---|
| D | target >= 1.5 | 0.468 | 0.519 | 0.377 | CLOSE |
| D | target > 0 | 0.555 | 0.557 | 0.463 | CLOSE |
| A | >= 1.5 / > 0 | 0.445 / 0.534 | 0.443 / 0.524 | 0.354 / 0.435 | CLOSE / CLOSE |
| B | >= 1.5 / > 0 | 0.443 / 0.549 | 0.468 / 0.557 | 0.351 / 0.457 | CLOSE / CLOSE |
| C | >= 1.5 / > 0 | 0.445 / 0.497 | 0.462 / 0.476 | 0.354 / 0.387 | CLOSE / CLOSE |
| L1 | >= 1.5 / > 0 | 0.445 / 0.560 | 0.505 / 0.551 | 0.354 / 0.463 | CLOSE / CLOSE |

Identical to the reported G1. The base rate of "always invested" is 0.555 (NDX) and 0.557 (SPX). D's "> 0" signal is
always on, so its hit rate is exactly that base rate. No rule's signal beats always-in by more than 0.6 pp in either era.

## 5. Causality (`V1_causal.py` -> `V1_causal.json`)

D on real NDX <= 2014: 222 cut points (200 random plus 0, 1, 2, 19-21, 59-61, 249-252, 298-304, 551, 552, T-3, T-2) x 6
kinds of future = 1332 perturbed runs. Columns after the cut were replaced by: S&P 1955-85 returns and T-bill; the NDX
reversed in time; garbage (NaN, 0, -3, inf and 1e300 closes; NaN, negative and 1e9 rf); a flat close with rf 0; close
only; rf only. B[:, :t+1] stayed identical in every run (exact, NaN-aware): **0 violations**. The future changed in 98.9%
of runs, so the test is sensitive. Truncation (rule run on columns 0..t only) also gave 0 violations on 222 cuts.
dev250_path: 12 cuts with all 500 paths perturbed gave 0 violations. Perturbing path 7 alone changed no other path and
none of path 7's past (no cross-path leak). Permuting the paths permutes the output. D is deterministic, does not change
its inputs, and ignores y10.
D's copy of the engine position uses only its own past decisions and the close and rf up to t. It also hard-codes the
engine's warm-up column (300) and delay (2). That is knowledge of the test engine, not of future data.
A, B, C and L1 (lighter: about 81 cuts x 3 kinds, 28 truncations each): 0 violations.

## 6. Verdict words (protocol section 5)

US halves are a second look (cumulative N = 7 rules in 2 rounds). The 8 funds share global shocks and are not 8
independent tests.

| Level | Bar | **D (primary)** | A (secondary) | B (secondary) | C (secondary) |
|---|---|---|---|---|---|
| GO-LIVE | MS1 >= 30.0% and E beats s0.85 | **FAIL** (9.60%; E -2.71 pp, 3/8) | FAIL (9.83%; -3.54, 3/8) | FAIL | FAIL |
| BEATS s0.85 | MS1 > 16.2%, dev250 win share > 50%, E med > 0 and >= 5/8 | **FAIL** (9.60%, 10.6%, 3/8) | FAIL (9.83%, 16.4%, 3/8) | FAIL (6.57%, 10.4%, 3/8) | FAIL (3.48%, 4.4%, 2/8) |
| BEATS HOLD | MS1 > 11.6%, E med > 0 and >= 5/8 | **FAIL** (9.60%; -2.74 pp, 0/8) | FAIL (9.83%; -3.34, 1/8) | FAIL (6.57%; 0/8) | FAIL (3.48%; 1/8) |
| IMPROVES ON ROUND 1 | MS1 > 5.34%, E med vs L1 > 0 and >= 5/8 | **PASS** (9.60%; +1.77 pp, 6/8) | PASS (9.83%; +2.23, 6/8) | FAIL (6.57% passes; E -0.64, 3/8) | FAIL (3.48% fails; E +0.64, 5/8) |

How to read the one pass: neither D nor A shows timing skill. D holds a constant, tracked exposure, and its measured
average effective exposure is 1.30 on dev250_path, against L1's average target of 0.37. Any long index position near 1x
clears this bar. The 1x hold clears it by more: 11.64% on MS1 and 8 of 8 funds against L1. If the user later prefers A
because of these rows, that is a best-of-7 real selection and has to be labelled as one.

## 7. Two explanations (`V1_explain.py` -> `V1_explain.json`)

My numpy copy of the MS1 engine matches std.engine bit for bit (max |d| = 0 for D, a tracked level 1 and a constant level 1)
and lets me remove frictions one at a time, in order. "Exposure" is the measured effective exposure 3 x (3x value) /
(3x value + cash), averaged over the days. "Ideal" is a daily-rebalanced x-times index financed at rf, with the 1x hold's
0.2% fee and only the final tax, at the same exposure.

**(a) What the 3x-product-plus-cash vehicle costs**

| Case | MS1 | no trading cost | + tax only at the end | + fee 0.6% on the 3x part (0.2% per unit) | + cash earns rf | ideal at same exposure | 1x hold |
|---|---|---|---|---|---|---|---|
| dev250_path, tracked level 1 (D code, E0 = 1.0; exposure 1.02) | **9.25** | 9.35 | 9.51 | 10.36 | 11.54 | 11.56 | **11.64** |
| dev250_path, D (E0 1.25; exposure 1.30) | **9.60** | 9.74 | 9.75 | 10.72 | 11.85 | 13.00 | 11.64 |
| real NDX 86-14, D (exposure 1.28) | **9.76** | 9.90 | 10.23 | 11.14 | 12.33 | 12.66 | 11.53 |
| real NDX 86-14, tracked level 1 (exposure 1.27) | 12.48 | 12.62 | 13.44 | 14.60 | 15.54 | 12.63 | 11.53 |

- At exposure 1, on the 500 paths, the vehicle costs **2.4 pp a year** against the 1x hold (9.25 vs 11.64%). The cash leg
  costs 1.2 pp (the 2 pp spread under rf and the 15.4% tax on interest, on about 2/3 of the money). The product fee
  (2.45% on the 3x part, against 0.6% at hold parity) costs 0.85 pp. Yearly tax instead of one final tax costs 0.16 pp.
  Trading costs 0.10 pp. The tournament's synthetic estimate of 2-2.5%/yr is confirmed on real-history paths.
- For D itself: frictions cost 2.25 pp (dev250) and 2.57 pp (real NDX). The drift band costs another 1.15 / 0.33 pp
  against daily rebalancing. So D ends **3.4 / 2.9 pp a year below an ideal levered index with the same exposure**. That
  ideal would beat the 1x hold by 1.4 / 1.1 pp. D is instead 2.0 / 1.8 pp below the 1x hold.
- The single real NDX path is noisy. With E0 = 1.0 the wider band let exposure drift well above 1 (average 1.27) and its MDD
  was -74% against -83% for the hold. It gained 2.9 pp on band luck alone (12.48% with MS1 costs). That is luck of one path,
  not a design result. On the 500 paths the same code gets 9.25%.

**(b) Why D's P(MDD <= -80%) on dev250_path is 52%**

| | 1x hold | ideal 1.10x | 1.20x | 1.25x | ideal at D's exposure (1.30) | D without frictions | D (MS1) |
|---|---|---|---|---|---|---|---|
| P(MDD <= -80%) | 17.6% | 27.0% | 36.6% | 41.6% | 48.2% | 44.4% | **52.0%** |
| median MDD | -67.8% | -72.2% | -76.2% | -78.0% | | -78.6% | -80.6% |

- **Mostly leverage on a crash-heavy source.** The source history 1986-2014 contains the 2000-03-10..2002-10-09 crash
  (NDX -82.5% peak to trough, 647 of 7312 days). 98% of the 30-year paths contain crash days, on average 670 of them.
  The 1x hold's median MDD is already -68%, so a small rise in exposure pushes many paths past -80%. The probability
  rises steeply, from 17.6% at 1x to 48% at 1.3x.
- **The vehicle adds the rest.** D runs at an effective 1.30, not 1.25, because the 3x part drifts up in rallies before
  a reset. The cash drag (2 pp spread and tax on interest) lowers equity throughout long drawdowns: removing it alone
  lowers the probability from 50.2% to 44.4%. The fee and the yearly tax add another 1.8 pp. The drift band itself
  slightly lowers the tail (44.4% against 48.2% ideal), but it does buy into falls: when the 3x part falls and exposure
  drops below 0.65, it resets to 1.0 or 1.5. On the real NDX path this took D to an MDD of -92.1%, against -83.0% for
  the 1x hold.
- By crash content (crash days in the path / 250): 0 -> D 3.8% (hold 0%), 1 -> 26%, 2 -> 38%, 3 -> 62.5%, 4 -> 78%,
  5 or more -> 88-100%. Every path where the 1x hold reached -80% also reached it for D, and so did 42% of the others.

## Files

`V1_common.py` (shared loaders), `V1_freeze.py/.json`, `V1_ms1.py` -> `V1_ms1_D_A_B_C_L1.json`, `V1_conf.py` ->
`V1_conf_price.json` / `V1_conf_ret.json`, `V1_s085_funds.py/.json`, `V1_g1.py/.json`, `V1_causal.py/.json`,
`V1_explain.py/.json`, `V1_spx29_sat.py/.json`, `V1_spx29_start.py/.json`. Run any of them with
`NUMBA_CACHE_DIR=<scratch> /root/.cache/ts-venv/bin/python -B <script>`.
