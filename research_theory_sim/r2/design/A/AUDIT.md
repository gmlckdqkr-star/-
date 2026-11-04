# AUDIT - lane TS2 round 2, lane A (Risk-Meter Leverage Clock, RMLC)

Blind auditor. Started 2026-11-04T11:29Z, finished 2026-11-04T11:40Z (timestamps from `date -u`).
Files I opened: `r2/DESIGN_BRIEF_R2.md`, `common/exec_engine.py`, and files in `r2/design/A/`, nothing else. I did not
look at any other lane, round-1 folder, test/verify/holdout folder, TEST_PROTOCOL, RESULT or FREEZE file. I used no
memory, no network and no market data. All my scripts and their outputs are in `r2/design/A/audit/` (a_*.py, a_*.json,
a_*.log). Python: /root/.cache/ts-venv/bin/python, numpy 2.5.4.
Hashes of the audited files, which I left unchanged:
(sha256)
rule.py `09bcfa965c852429a4919a1f50c64322f4d82c314099bde72f0bbec31cb7e9b3`,
sim.py `30957f2d9928363b77c89020312726c3e5d7631740b9814f3894ae6911cffe53`,
THEORY.md `e87eaeedb57cd197cede7877e4721da722429f8fdd6fd4e61e3977f4cf273d64`.

**Verdict: PASS.** All seven checks pass. I found no mechanical defect, so rule.py and sim.py are unchanged. The gate
claims reproduce exactly. The edge over the 1x hold is thin, and the designer says so honestly (see 3 and 8).

## 1. Blindness - OK
- READ_LOG.md lists only the brief, exec_engine.py and the designer's own files. It also records that names of
  project skills and strategies were present in the session context and were ignored. I could not read the
  designer's session record, so this check rests on READ_LOG, the code grep and the file timestamps.
- Grep of every .py in the folder (rule.py, sim.py, work/*.py) for `open(`, np.load, loadtxt, genfromtxt, read_csv,
  `read_`, urllib, requests, http, socket, subprocess, os.system, glob, listdir and for paths. The only file I/O is
  json read/write of the designer's own files in work/ (variant_count.json, base_s23/45.json, final_eval/ext.json).
  The only outside path is the `sys.path` import of `common/exec_engine.py`. There are no paths under /tmp/claude or
  /home/user, no network and no subprocess. rule.py imports only `math` and `numpy` and does no I/O.
- Real-history facts: there are no calendar dates, named indices, named episodes or crash dates anywhere in THEORY.md,
  sim.py or rule.py. The only year is "1900 onward", which describes the DMS source in the anchor table. Every
  mechanism constant has a theory reason in THEORY.md section 7/11. For transparency, two priors are justified by
  structural or industry numbers from the literature rather than by market statistics: psi ~ log-U[2, 6] ("inelastic
  markets, Gabaix-Koijen ~5") and h_M ~ log-U[10, 60] d (EWMA decay 0.94, about 11 d). Both are known ingredients with
  wide priors and say nothing about timing, so I do not count them as contamination.
- PRIORS_FROZEN: the line is `PRIORS_FROZEN 2026-11-04T10:57Z`. THEORY.md mtime is 10:57:34 and the file was not
  changed afterwards. The first rule-design files are harness.py and base.py at 10:57:58, then explore1.py at 10:58:59.
  The pre-freeze scripts (diag_explode/diag_path/diag_dd.py, 10:54-10:55) look only at explosion and drawdown
  calibration, not at conditional returns or rules. The design_log timeline matches the mtimes (rule.py 11:20,
  final_eval 11:23, final_ext 11:25, synth_results 11:26).
- sim.py was edited at 11:21, after the freeze, to add robustness-only options (`prior_width`, `mech_scale`).
  `work/sim_frozen_copy.py` differs only by those options. I confirmed the default output is bit-identical to that
  copy (r, rf, ON and OFF; audit/a_anchors_sim.json `sim_equals_frozen_copy: true`). The prior table in THEORY.md
  section 11 matches the sim.py code line by line.

## 2. Anchors (brief 2b-2d) - OK, with notes
- THEORY.md section 6 "Published anchors" names its sources: Dimson-Marsh-Staunton (Triumph of the Optimists /
  Yearbook) and Siegel. It gives the remembered numbers: TR premium over bills 4.4 % world, 5.5 % US, centre 5.0 %;
  dividend yield about 4 % (20th century) and about 2 % (recent), centre 3.5 %; volatility 17 % world / 20 % US
  annual SD, 15-19 % daily; bills about 4 %; drawdown frequencies. It states the conversion (price premium = TR premium
  minus dividend yield, giving 1.5 %) and how sure the designer is.
- Medians drawn from sim.py, P = 2000, seed 777 (audit/a_anchors_sim.json):
  | quantity | anchor centre | sim prior median [p10, p90] | realised per path, ON | realised per path, OFF |
  |---|---|---|---|---|
  | log price premium over rf | 1.5 %/yr | 1.49 % [-0.95 %, 4.13 %] (sd 1.92 %) | 1.60 % [-3.0 %, 6.3 %] | 1.65 % [-3.0 %, 6.4 %] |
  | volatility | 17 %/yr | 17.1 % [12.5 %, 23.7 %] (log-sd 0.244) | 17.1 % | 17.1 % |
  | mean rf | ~4 %/yr | | 4.1 % | 4.1 % |
  | worst 30y DD, median | ~-45 % (low confidence) | | -52.8 % | -48.1 % |
  | P(DD <= -50 %) / P(DD <= -75 %) | ~0.4 / a few % | | 0.56 / 0.09 | 0.46 / 0.07 |
  The premium and volatility centres sit on the anchors.
- Haircut check: the 1.5 % price-premium centre is the brief's required TR-to-price conversion, set out in full, not a
  conservative haircut of the cited premium. The TR centre of 5.0 % is the midpoint of the cited 4.4 % and 5.5 %.
  Note: the 3.5 % dividend yield leans toward the 20th-century level. With a recent-decades yield (2-3 %) the centre
  would be 2-3 %. The wide prior (sd 2 %, truncation [-3 %, +7 %]) covers that, and the rule's p0 = 0.02 sits above the
  centre, so I do not flag it. The 17 % volatility centre is the middle of the cited range. Lower volatility does not
  make a leveraged rule look worse, so it is not a conservative choice either.
- 2c, per-path variation: mu_g and sigma are drawn per path (sd 1.9 % and log-sd 0.24). The realised premium spread
  (3.74 %) is wider than pure sampling noise (3.13 %), consistent with sqrt(3.13^2 + 1.92^2) = 3.67 %. OK.
- 2d, rates: there are piecewise-linear regimes of 2-15 years (up 0.3 / down 0.3 / flat 0.4), and half of the paths
  move in monthly steps. 70 % of paths have a 10-year window in which the 1-year-smoothed rate moves by at least 3 pp
  (54 % up, 34 % down). The longest monotone run of yearly rate changes has median 9 years [p10 5, p90 14], and 63 % of
  paths have one of 8 years or more. 99 % of paths have a stable 5-year window (within 0.5 pp). OK.
- Note: the mechanism-ON world is somewhat more crash-prone than the drawdown anchor (median -53 % vs -45 %,
  P(<-75 %) 0.09 vs about 0.05). That tilts the world mildly in favour of a crash-exit rule. The designer reports and
  accepts this (THEORY.md section 10), and the anchor itself is low confidence. I note it but do not fail it.

## 3. Gates (P >= 1000, fresh seeds) - reproduced
Re-run with exec_engine on the designer's fresh seeds 10001+10002 (P = 2000 pooled; audit/a_gates_main.json):
| world | rule | hold 1x | hold 2x | hold 3x | best const (L) | rule - h1 | rule - bc | gate |
|---|---|---|---|---|---|---|---|---|
| ON | 0.0543 | 0.0531 | 0.0190 | -0.0203 | 0.0228 (0.5) | +0.0012 (bootstrap sd 0.0012) | +0.0315 | G-ON PASS |
| OFF | 0.0246 | 0.0535 | 0.0201 | -0.0190 | 0.0229 (0.5) | -0.0289 | +0.0017 (>= -0.010) | G-OFF PASS |
Constant levels ON: 0.5 0.0228, 1 0.0199, 1.5 0.0153, 2 0.0085, 2.5 -0.0025, 3 -0.0203. Every value matches
design_log.md / synth_results.json to the last digit.
Further fresh seeds:
- Designer's precision extension 10005-10008 (P = 4000), re-run: ON 0.0540 vs h1 0.0514 (+0.0026, sd 0.0008) vs bc
  0.0227. OFF 0.0230 vs bc 0.0229 (+0.0001). Both pass and match the design log.
- Auditor's own fresh seeds 10601-10604 (P = 4000, never used by the designer): ON 0.0556 vs h1 0.0532 (+0.0024, sd
  0.0008) vs bc 0.0241. OFF 0.0254 vs bc 0.0242 (+0.0012). Both gates pass.
The gate claims reproduce. G-ON against the 1x hold is thin: +0.1 to +0.3 pp, and the rule beats the 1x hold on only
46 % of ON paths. In the OFF world the rule is 2.9 pp below the 1x hold, which is the structural cost of reaching
exposure through the 3x product plus cash. It beats the best constant only because constant levels are never
rebalanced.

## 4. Interface - OK
(audit/a_interface.json, a_causality.json)
- Imports: `math` and `numpy` only (AST check), no I/O tokens. `INPUTS = ('close', 'rf')`. `PARAMS` is a dict literal
  with 6 parameters. Signature: `target_levels(close, rf, y10=None, params=PARAMS)`. The docstring has 6 lines.
- Inputs are not modified (close, rf and y10 compared before and after). Output is float64 of shape (P, T), with finite
  values in [0, 1.87] here (clipped to [0, 3] by construction) and NaN only before the first live return. There are no
  inf values. The output is deterministic and the same with or without y10. rf is not used, and NaN in rf changes
  nothing.
- NaN / zero / flat / garbage in close: paths with a late open, zeros before the open, a flat stretch, a holiday gap,
  bad zeros, a never-moving path, an all-NaN path, negative values and inf all run without error. Output is NaN before
  the first live day and finite afterwards. Untouched rows are bit-identical.
- Scale invariance: for close x 1000, 1e-3, 1234.5, 7e6 and 1e-4, the outputs differ by at most 1.4e-14 (floating-point
  rounding of log(close*s)). The NaN pattern, the cascade (level 0) pattern and the levels rounded to the 0.5 grid are
  identical. On 2000 fresh paths (seed 10001, ON and OFF, scales 1000 and 1e-4), the engine CAGRs are bit-identical on
  every path. Strict bit-identity of the continuous level is impossible for any rule that computes with close values,
  because close*1000 is itself rounded. I do not count this as a defect, and no fix is possible or needed.
- Speed: P = 500, T = 10000 takes 0.66 s (limit 60 s).

## 5. Causality (exact) - OK
50 synthetic paths, 100 cut points per world, run in both the ON and OFF worlds (seeds 9191 and 9192). Each run had 16
cuts below 300 (including 0, 1, 2, 298, 299) and 16 in the last 60 columns (up to T-2 = 7858). Some paths also had a
late open, a gap or a flat stretch. At each cut, every column > t of close, rf and y10 was replaced by one of: a
random walk, all-NaN, garbage (+-inf, -1, 1e300, 1e-300, 0, NaN), all zeros, or lognormal jumps with 20 % NaN.
Output columns <= t were identical in all 200 cases, both by `array_equal(equal_nan)` and by raw bytes. Zero failures.
(A first version of this test, in a_interface.py, missed the near-end cuts because of a sorting slip in my own script.
a_causality.py corrects that and is the result I report.)

## 6. Reproduction - OK
Headline rule median CAGR on fresh seeds 10001+10002 with mechanism ON: designer 0.0543, auditor 0.054341. The
difference is 0.000 pp (tolerance 0.2 pp). The robustness rows also reproduce exactly: delay 3 0.0514, delay 5 0.0465,
cost 0.006 0.0481 (OFF: 0.0242 / 0.0246 / 0.0182). Rule p10 -0.0093 and P(DD <= -80 %) 0.1245 match, as does average
level 0.91 with 4.3 trades/yr.

## 7. Simulator sanity - OK
- `mechanism=False` skips `_mech_path` entirely. Returns are i.i.d. Student-t(nu), rescaled to realised volatility
  sigma. The mechanism parameters are drawn but unused, to keep the random stream aligned. For the same seed, mu_g,
  sigma, nu, rf and y10 are bit-identical between ON and OFF. The paired realised premium differs ON-OFF by median
  -0.04 pp (mean -0.06 pp), and realised volatility by 1e-5 (rescaled exactly). So the unconditional premium and
  volatility are the same.
- OFF has no structure: median lag-1 autocorrelation of returns -0.0008, of squared returns -0.0015, of 20-day returns
  -0.0003. ON shows the mechanism's momentum (20-day autocorrelation +0.074) and weak lag-1 clustering in squared
  returns (+0.006, diluted by the t(4-8) news tails).
- There is no NaN or inf in r, rf or y10 across 2000 x 7860 paths in either world, nor in the robustness worlds
  (prior_width 0.5 / 1.5, mech_scale 0.5 / 1.5). r[:, 0] = 0. rf lies in [0, 13 %], y10 in [0, 14.7 %].
  Note: the fat-tailed prior gives rare extreme days (largest daily return +51 % / -35 % in OFF over 15.7 million
  path-days). These are rare and the same in both worlds, so I take no action.
- Disk: folder total is about 0.4 MB, and no file is over 1 MB. A leftover `__pycache__/` (28 KB, written at 11:28:41,
  after the READ_LOG note said it had been deleted) was removed. It is a bytecode cache, not a deliverable. My own
  runs used PYTHONDONTWRITEBYTECODE and created no caches.

## 8. Changes made by the auditor
- None to rule.py, sim.py, THEORY.md, design_log.md, synth_results.json or READ_LOG.md, so there are no before/after
  numbers to report.
- Housekeeping: I deleted `r2/design/A/__pycache__/` (bytecode cache, 28 KB). This has no effect on any number.
- Added `AUDIT.md` and `audit/` (the auditor's scripts and results, about 70 KB).

## Summary for the tournament
The frozen rule does what the theory says. It holds a Kelly-style base level (about 0.9 on average) and goes to cash
during the cascade phase of its own leverage-cycle world. It passes both design gates, and the result reproduces
bit-exactly. The edge over the same-basis 1x hold is small (+0.1 to +0.3 pp), wins on fewer than half the paths, and
turns negative with delay 3, delay 5, double cost or a weaker mechanism, as the designer reports. Most of its margin
over the best constant level comes from the engine's no-rebalancing rule, not from skill (OFF world: +0.0 to +0.2 pp).
