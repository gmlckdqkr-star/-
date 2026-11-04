# V2 verifier report: protocol, freeze, tournament, post-2014 rows (TS2 round 2)

Verifier V2, 2026-11-04T12:55Z (times from `date -u`). This file contains no number that uses data after 2014-12-31.
The post-2014 recomputation is in `../../holdout/r2/verify/V2_POST2014.md` (user only).
Own code only; nothing existing was modified; git used read-only (`git log`, `git log -g`, `git show --stat`,
`git ls-tree`).

## 0. Start condition (holdout/r2/status.txt)
Final content: `D rc=0`, `A rc=1`, `B rc=1`, `C rc=1`, `A rerun rc=0`, `B rerun rc=1`, `C rerun rc=1`, `B rerun rc=0`,
`C rerun rc=0`. So the three required "rerun rc=0" lines are present, but:
- the first post-2014 runs of A, B and C failed (rc=1), and the first reruns of B and C failed again (rc=1);
- cause (from the failed logs): a numba constant-inference error path calls `os.path.relpath`, which raised
  `FileNotFoundError` from `os.getcwd()`: the processes ran in a working directory that no longer existed. No JSON was
  written by a failed run. The successful runs are the same frozen code (hash of post2014_r2.py unchanged), t0 12:35Z
  (A), 12:36Z (B), 12:37Z (C), D 12:33Z.

## 1. Order of events: PASS
| event | time (UTC) | evidence |
|---|---|---|
| DESIGN_BRIEF_R2.md last written | 10:39:36 | mount mtime |
| TEST_PROTOCOL_R2.md / harness_r2.py / post2014_r2.py / freeze_r2.sh written | 10:43:53 / 10:43:54 / 10:43:08 / 10:44:20 | mount mtime |
| pre-design commit 4bd392b (brief, protocol, SHA256SUMS, test code) | 10:46:04, pushed 10:46:28 | `git log -g` |
| first designer artefact (folders C, D created; B 10:46:59, A 10:51:56) | 10:46:52 | folder mtimes (this mount does not update a folder's mtime when files are added, so it is the creation time) |
| first designer file / PRIORS_FROZEN lines | B THEORY.md 10:54:42, A work/ 10:54:24; PRIORS_FROZEN B 10:54Z, C 10:56Z, D 10:56Z, A 10:57Z | mtimes, THEORY.md |
| last designer / audit file | 12:07:09 (D/AUDIT.md) | mtimes |
| tournament files | 12:17:59 - 12:23:33 | mtimes |
| freeze started / commit 4a57503 / pushed | 12:24:17.8 / 12:24:21 / 12:24:23 | /root/.cache/ts2_files.txt, `git log -g` |
| first real run (D) launched | 12:24:39.9 (t0 "12:24Z") | birth time of its task output file |
| A, B, C real runs | t0 12:28-12:29Z | real_*.json |
| post-2014 runs | t0 12:33Z (D) .. 12:37Z | holdout/r2/post2014_*.json |
- The hashes of DESIGN_BRIEF_R2.md (372a8555...), TEST_PROTOCOL_R2.md (ddf7499c...), harness_r2.py (ca54744f...),
  post2014_r2.py (f0158e16...), freeze_r2.sh (19b16f78...), exec_engine.py (c9298b26...) and round-1 L1 rule.py
  (acc4cf0c...) are identical in SHA256SUMS_PRE_DESIGN_R2.txt, in commit 4bd392b, in FREEZE_TS2.txt, in commit 4a57503
  and on disk now.
- FREEZE_TS2.txt: all 211 hash lines verify against the current files (0 mismatches) and the set of files under
  r2/design/ now equals the frozen set exactly (no file added or removed after the freeze). No design or tournament
  file was modified after 12:23:33.
- Minor (not a breach): A ran simulator diagnostics (work/diag_*.py, 10:54-10:56) before writing PRIORS_FROZEN and
  revised its priors from the simulated drawdown / rate statistics (THEORY.md section 10, documented); the brief asks
  for THEORY.md "before any simulation". D added simulator implementation notes 7 minutes after its PRIORS_FROZEN line
  (normaliser from a pilot run, a new clip of the premium factor to [0.1, 10] and a -30% daily floor), before any rule
  work. A extended sim.py at 11:21 with robustness-only options (bit-identical at defaults; the tournament uses defaults).
- The pre-design validation runs (val_R1L1, val_sma_y10, 10:43-10:47Z) used real US data <= 2014 with round-1 L1 and a
  test rule only, and ran the fund pipeline on QQQ, not on the 8 confirmation funds. The val_R1L1 t0 (10:43Z) is in the
  same minute as the last harness_r2.py write (10:43:54), so it cannot be shown from timestamps that it ran the hashed
  harness version; it does not matter for the real test, which ran the hashed version.
- RESULT_TS2_KO.md step 4 ("first opened real data after the freeze") is true for the round-2 rules; real US data had
  been opened before for the validation runs above.

## 2. Tournament: PASS (reproduced exactly)
- Re-ran `tournament.py` unchanged except `OUTDIR` (copy `V2_tournament_copy.py`, output `V2_tournament_rerun.json`,
  12:39-12:42Z, 3 workers). Field-by-field comparison with the original tournament.json, excluding only timing fields:
  **0 differences** (all cell statistics, path hashes, scores, bootstrap, stress rows).
- Scores (0.5 x mean ON + 0.5 x mean OFF of the 8 cell medians, %/yr): D 4.35 > C 3.75 > B 3.53 > A 3.52; tie set {D}
  (C is 0.60 pp behind, outside the 0.3 pp window), so PRIMARY = D without tie-break. Recomputed by hand from the cell
  medians: identical. D also has the highest worst cell (3.60, A_OFF).
- Reference rows: hold 1x 5.85, hold 2x 2.61, hold 3x = const 3.0 -1.29, const 0.5 2.99 (best single constant),
  1.0 2.81, 1.5 2.49, 2.0 1.88, 2.5 0.89, best constant per cell (hindsight) 3.03.
- Brief section 7 followed: every rule on every simulator, ON and OFF, P = 1000 per cell, fresh seeds 20000-20007 (one
  seed per cell, all rows of a cell on the same paths; not used by any designer: no 2000x seed in any design log or work
  script), score and tie rule as written, holds and best constant reported per cell, best single constant reported.
  The audit-verdict exclusion step is the judge's addition (all four PASS, so no effect).
- Notes (overstatement risks, not errors):
  - Hold 1x beats every rule in every one of the 8 cells (D -1.50 pp on the score). The round-1 problem "hold beats
    every rule in the synthetic tournament" is not solved; only the in-world design gate was added (A passed G-ON by
    +0.12 pp, B, C, D failed G-ON).
  - The "constant levels" are engine constants that never rebalance (the 3x/cash mix drifts), so D's +1.36 pp over the
    best constant is a rebalancing effect of a tracked 1.25 exposure, not theory; RESULT_TOURNAMENT.md and
    RESULT_TS2_KO.md both say so.
  - D's delay-5 score (4.37) is above its base score (4.35): D replicates the engine's delay-2 queue, so the stress rows
    are not a timing test for a rule with no timing.

## 3. Blindness spot check of THEORY.md, sim.py, rule.py (A-D): nothing disqualifying
- Calendar years appear only in literature citations of the published anchors allowed by brief 2b (Dimson-Marsh-
  Staunton 2002, Jorda et al. 2019 "1870-2015", Mehra-Prescott 1985 "1889-1978", Barro 2006, Mandelbrot 1963, Fama 1965,
  Cont 2001, Siegel, Shiller). No named index (S&P, Nasdaq, NDX, SPX, Dow, Nikkei, MSCI, VIX, QQQ/TQQQ ...), no named
  episode (1987, 2000, 2008, Lehman, COVID, Volcker, dot-com ...), no month names in any of the 12 files.
- sim.py / rule.py read no files (sim.py only adds common/ to `sys.path` inside its `describe()` helper to import
  exec_engine.py; `simulate()` does not); rule.py imports numpy and math only.
- Constants with a link to remembered real statistics, all argued in THEORY.md as published anchors (allowed for the
  unconditional level): vol prior 0.17 (A `_PRIOR_VOL`, B `s0`), premium priors A p0 0.02, B mu0 0.03, C c 0.02,
  D E0 1.25 (= prior Kelly 0.035/0.17^2 = 1.21, D design_log 3), dividend-yield conversions (US Shiller ~4% / recent ~2%
  -> 3.5%). All four THEORY.md files cite US-specific long-run numbers (US premium ~5.5% geometric / ~7% arithmetic,
  Siegel, Shiller dividend yields) next to world numbers; they set only the level, but they are statistics of the
  headline market's own country (the protocol already labels this a level-only look-ahead).
- Structural features that may come from remembered history but are generic economics: zero-lower-bound stretches in
  B's and D's rate priors ("at 0 it stays at 0 while the trend points down"), monthly rate steps (from the brief).
- D's rule.py hard-codes engine facts given in the brief (warm-up 300, delay 2, 3x cost 2.45%/yr, cash rf - 2% after
  15.4% tax) to replicate the engine's drifting position; these are not market statistics.
- Shared scratchpad: designers' sessions could list the orchestrator's scratchpad (C's READ_LOG records seeing
  ts2_design.js, ts2_tournament.js, t_engine.py). I read those files: they hold prompts and the tournament recipe, no
  market or round-1 result numbers, so nothing could leak from them.
- READ_LOGs of all four lanes list only the brief, exec_engine.py and their own folder.

## 4. Post-2014 rows (D full, A spot check): PASS, reproduced to machine precision
Independent code `holdout/r2/verify/v2_post2014.py` (own frame assembly, splice, fill order, fund contexts, C3 product
swap, actual-product holds, summaries; only std.py and the jp/mkt loaders shared, as in round 1). 360 compared items per
rule (C1, C2, C3 and the 8 funds; base, delay 3, cost 0.6%; delay 5 for the US rows separately):
**D and A: 0 differences larger than 0.1 pp (max |difference| 2.2e-16), 0 changed win counts.** Small presentation
points (one hold row mixing two tax formulas, 0.17 pp; a wording point on delay 5; the user-only result file omits
that A's first run also failed) are listed in V2_POST2014.md. All numbers there.

## 5. Leak check: PASS
- Search of every file under r2/ (236 text files, nothing excluded) for 1158 post-2014 values from
  holdout/r2/post2014_{A,B,C,D}.json in 4-6 printed formats (4 decimals, 3 decimals where |x| >= 0.1, percent with 1 and
  2 decimals, bare percent).
- Hits exist only as coincidences: (a) files written before any post-2014 run existed (design/, tournament/, test/out/,
  DESIGN_BRIEF, TEST_PROTOCOL: all hash-frozen or dated before 12:33Z); (b) RESULT_TS2_KO.md (12:39Z): every hit is a
  pre-2015 quantity (MS1 headline, real NDX 1986-2014, E-basis medians, synthetic scores, costs), checked line by line;
  the file also contains no qualitative statement about post-2014 results; (c) verify/V1_* files: path win shares,
  cost constants. The search output itself lists post-2014 tokens and therefore stays in holdout/r2/verify/ (v2_leak.*).
- The git repository contains no holdout file (only the scripts post2014.py / post2014_r2.py).

## Verdict words for the PRIMARY D (protocol section 5, from <= 2014 rows of real_D.json; E arithmetic re-derived)
| level | MS1 headline (dev250_path) | E (8 funds, <= 2014) | verdict |
|---|---|---|---|
| GO-LIVE BAR | 9.60% < 30.0% | vs s0.85 median -2.71 pp, 3/8 | FAIL |
| BEATS s0.85 | 9.60% <= 16.2%, path win share 10.6% <= 50% | -2.71 pp, 3/8 | FAIL |
| BEATS HOLD | 9.60% <= 11.6% | vs 1x median -2.74 pp, 0/8 | FAIL |
| IMPROVES ON ROUND 1 | 9.60% > 5.34% | vs L1 median +1.77 pp, 6/8 | PASS (US rows are a second look; N = 7) |
The headline and E rows themselves are V1's scope; V2 checked only that the words follow from the reported numbers.
The post-2014 rows do not change any word.

## Files (this folder)
V2_REPORT.md, V2_tournament_copy.py, V2_tournament_rerun.json, V2_tournament_rerun.log.
