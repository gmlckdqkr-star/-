# AUDIT: lane C (TS2 round 2), "Fast Aftershocks, Slow Scars" (FASS)

Blind auditor. Started 2026-11-04T11:40Z, finished 2026-11-04T11:50Z (times from `date -u`).

**Verdict: PASS.** No defects found and no file of the designer was changed. Every claim the designer made reproduces
bit for bit. The design gate G-ON FAILS, and the designer reports this honestly; G-OFF passes. The rule ships under the
brief's fallback clause (no variant passed both gates).

## What the auditor read
- /mnt/project-files/research/theory_sim/r2/DESIGN_BRIEF_R2.md (the rules)
- /mnt/project-files/research/theory_sim/common/exec_engine.py
- /mnt/project-files/research/theory_sim/r2/design/C/ (all files: THEORY.md, sim.py, rule.py, design_log.md,
  synth_results.json, READ_LOG.md, work/*.py, work/*.txt, work/variants.csv)
- Nothing else. No other lane, no round-1 folder, nothing else under /mnt/project-files, no memory, no network, no MCP data
  tool, no skill. No real market data. Every number below comes from the designer's own sim.py.
- Context note: my session context contained names of market-data MCP tools and skills. I ignored them.
- Auditor scripts and logs are in `audit/`: a_gates.py, a_interface.py, a_anchors.py, a_scale_engine.py and their logs and
  json output. They do not import work/harness.py, so nothing was appended to work/variants.csv.

## 1. Blindness: OK (two minor procedural notes)
- READ_LOG.md lists only the brief, exec_engine.py and the designer's own folder. It discloses the context that was present
  (MCP tool and skill names) and says it was ignored.
- Grep of every .py file (rule.py, sim.py, work/*.py) for open(, np.load, loadtxt, genfromtxt, read_csv, read_, urllib,
  requests, http, socket, subprocess, os.system, glob, listdir, scandir, pathlib, shutil, /tmp, /home and /mnt/project-files:
  - every `open(` is a write of the designer's own log or json file inside work/ (harness.py variants.csv, s*_select.py,
    final_eval.py);
  - the only /mnt/project-files paths are common/ (exec_engine) and this lane folder (t1.py, t2.py);
  - there is no network, process, glob or listdir call and no /tmp or /home path;
  - imports are numpy, math, scipy.ndimage (exploration only), json, time, itertools, importlib, and the designer's own
    modules.
- rule.py imports only `math` and `numpy` (checked with an AST parse). It has no I/O.
- Hard-coded real-history facts: none found. No calendar dates, named indices or episodes in sim.py, rule.py or the work
  scripts. A grep of THEORY.md for index names and crash years finds only the publication years of the cited papers.
  - sim.py constants (252, burn-in 756, MCAP 1.5, rf bounds [0, 0.15], monthly steps with prob 0.5) are conventions
    stated in THEORY.md.
  - rule.py constants c=0.02, a=0.2, b=0.08, hf=40, hs=350 come from logged synthetic grids (S1-S3 in variants.csv). The
    tied structure (4*hs, hs/4, cap 3, warm-up of 250 observations) is declared as fixed structure.
- PRIORS_FROZEN: THEORY.md has `PRIORS_FROZEN 2026-11-04T10:56Z`, and the THEORY.md mtime is 10:56:55. Later events:
  first simulation 10:58Z (design_log), t1.py/t2.py mtime 10:59, first variant row 11:00Z, final rule 11:31-11:32Z.
- sim.py was edited after the freeze (mtime 11:21), and the designer says so: a diagnostics-only `override=` argument.
  - Every prior in draw_params and _rates matches THEORY.md section 7.
  - The current sim.py reproduces the earliest logged baselines exactly: hold 1x on seeds 1-2 is 0.05492 ON and 0.05423 OFF,
    the same as the 11:00Z variants.csv rows. So the edit did not change the default worlds.
- Fresh seeds: selection used seeds 1-12 only (grep of all scripts). Seeds 10001-10004 appear only in final_eval.py and
  final_boot.py. variants.csv has exactly one FINAL evaluation (8 rows, 11:33-11:37Z). Seed 10009 was used only for the
  speed check.
- Variant count: variants.csv holds 167 distinct parameter-set names, not counting FINAL. The designer reports N = 169,
  which is not smaller than what was logged.
- Minor note 1 (disclosed by the designer): t1.py and t2.py were first written to the session scratchpad and then moved.
  That move listed the scratchpad directory once, which showed three file names the designer did not create. The designer
  says they were not opened. This was a write outside the own folder and one directory listing outside it. Only file names
  were seen, and the brief already describes the tournament they suggest. I see no contamination.
- Minor note 2: work/e6_regrule.py uses a centred, non-causal maximum filter. It is labelled an "upper-bound check, not a
  candidate", is not part of the rule family, and nothing from it reaches rule.py. e2 and e4 use the simulator's latent
  m(t) for diagnostics, which is allowed.
- Limitation: I cannot read the designer's session transcript. This check rests on READ_LOG.md, the code grep, file
  timestamps and the reproductions.

## 2. Anchors (brief 2b-2d): OK, with one remark on drawdowns
- THEORY.md section 6, "Published anchors", names its sources: Dimson-Marsh-Staunton (Triumph / Yearbook), Mehra-Prescott
  1985, Jorda et al. 2019, a dividend-yield split, Barro 2006 / Barro-Ursua, and Cont 2001 (qualitative). It gives the
  remembered numbers, the conversion and how sure the designer is.
  - Conversion: a total-return arithmetic premium of 6.0% minus a dividend yield of 3.0% gives a 3.0% arithmetic premium for
    the price index.
  - Priors: pi_bar ~ N(0.03, 0.02) truncated to [-0.02, 0.09]; sigma_bar ~ LogN(0.175, 0.25) truncated to [0.10, 0.35].
- Medians from sim.py on 2000 paths (seed 1; audit/anchors_seed1.log):

  | quantity | drawn per path, median [p10, p90] | realised ON | realised OFF | anchor centre |
  |---|---|---|---|---|
  | arithmetic excess of the price index over rf, per yr | 0.0306 [0.0058, 0.0551], sd 0.0193 | 0.0314 | 0.0307 | 0.030 |
  | volatility, per yr | 0.1755 [0.1275, 0.2413], log-sd 0.242 | 0.1762 | 0.1741 | 0.175 |
- Haircut check: no conservative haircut found.
  - The 6.0% total-return premium is the central value of the cited range: world 5.5-6%, Mehra-Prescott 6%, Jorda 5-6%,
    US about 7%.
  - The 3.0% dividend yield lies between the cited 4% century average and the 2% of later decades. Subtracting the 4%
    average would have given a lower premium, so the choice does not lower the centre.
  - The 17.5% volatility is central among 16.5%, 17% and 19-20%.
  - Uncertainty is expressed by a wide prior, not by moving the centre.
- 2c: premium and volatility are drawn per path and independently: premium sd 1.9 pp, volatility log-sd 0.24.
- 2d: rf paths have long trending regimes (seed 1, 2000 paths):
  - 61% of paths contain a steady 10-year uptrend of at least 3 pp (linear fit R2 >= 0.7), and 42% a steady downtrend of the
    same size. 80% contain one or the other.
  - 74% contain a stable 10-year band narrower than 1.5 pp.
  - 51% of paths have monthly steps.
  - rf ranges from 0% to 16%, median 4.45%.
- Drawdown remark: the simulated drawdowns are deeper than the designer's own drawdown anchor. Median worst drawdown is
  -55% ON and -49% OFF, against the -40% to -50% the designer expected. P(MDD <= -50%) is 0.57 ON and 0.48 OFF, against
  0.25-0.40.
  - The designer reports this and did not retune.
  - Most of the gap already appears in the iid OFF world, so it follows from the 3% premium and 17.5% volatility rather than
    from a tuned crash mechanism.
  - The effect makes leverage look worse in this simulator. It is a remark, not a defect.

## 3. Gates (fresh seeds 10001-10004, P = 500 each = 2000 paths per world): the designer's claims reproduce exactly
Script: audit/a_gates.py. Results: audit/gates_ON_10001.json and audit/gates_OFF_10001.json.

| world | rule median | hold 1x | hold 2x | hold 3x | const 0.5 / 1 / 1.5 / 2 / 2.5 / 3 | best const | rule vs hold 1x | rule vs best | gate |
|---|---|---|---|---|---|---|---|---|---|
| ON | 0.053942 | 0.054355 | 0.019743 | -0.027885 | 0.02743 / 0.02548 / 0.02123 / 0.01356 / 0.00161 / -0.02788 | 0.02743 @ 0.5 | -0.041 pp | +2.651 pp | **G-ON FAIL** |
| OFF | 0.030383 | 0.053377 | 0.015044 | -0.032699 | 0.02748 / 0.02472 / 0.01998 / 0.01298 / -0.00095 / -0.03270 | 0.02748 @ 0.5 | -2.299 pp | +0.290 pp | **G-OFF PASS** |

- These are identical to synth_results.json in every printed digit. The designer's report says gate_on_pass false and
  gate_off_pass true, and both reproduce.
- Context only: I ran a second fresh set, seeds 10005-10008 with P = 2000, not used by anyone for selection.
  - ON: rule 5.28%, hold 1x 5.38% (-0.10 pp, G-ON fails again), best constant 2.60% (+2.67 pp).
  - OFF: rule 3.09%, best constant 2.70% (+0.39 pp, G-OFF passes).
  - So the G-ON failure is stable: the rule ties with or trails hold 1x by about 0.0-0.1 pp.

## 4. Interface: OK
Script: audit/a_interface.py. Log: audit/interface.log.
- Imports are `math` and `numpy` only. INPUTS = ('close', 'rf'), and PARAMS is a literal dict with 5 entries.
- The signature is `target_levels(close, rf, y10=None, params=PARAMS)`. y10 is accepted and ignored; None and an array
  give bit-identical output.
- Inputs are not modified. The inputs were set read-only and compared bitwise after the call; close is copied and rf is
  unused.
- Output is (P, T) float64, every value in [0, 3] or NaN, with no inf. The output is deterministic.
- Edge cases ran without error or warning:
  - NaN at the start: cash until 250 valid returns.
  - a flat stretch, a zero stretch and single NaN gaps;
  - an all-NaN path and a perfectly flat path: all cash;
  - inf and negative garbage values: skipped, not used as returns;
  - a path that goes to zero and stays there: the filters freeze and the last level is kept;
  - float32 input.
- Scale invariance: close times 1000, 0.001 or 1234.5 gives the same NaN pattern and levels within 2.2e-13, with zero
  changes on the 0.5 level grid.
  - The levels are not bit-identical: (k*c)/(k*p) is rounded differently from c/p. No rule that forms price ratios can be
    bit-exact for a scale factor that is not a power of two, so this is not a defect.
  - Engine-level check (audit/a_scale_engine.py): the traded CAGR is bit-identical for close, close*1000 and close*0.001
    on 500 ON and 500 OFF paths.
- Speed: P = 500, T = 10000 runs in 2.6 s on the shared machine, well under the 60 s limit.

## 5. Causality (exact): OK
- Test setup: 50 synthetic paths (sim seed 4242, T = 7860) with NaN, flat and zero stretches in the past, and 100 cut
  points. The cut points include 0, 1, 2, 10, 120 and 248-251, 13 cuts are below 300, and the three last columns
  T-3..T-1 are included.
- At each cut, every column > t of close, rf and y10 was replaced by one of these continuations:
  - a different random walk;
  - all NaN;
  - garbage (0, -1, ±inf, 1e300, 1e-300, NaN, 5);
  - a collapse to 1e-12;
  - explosive growth.
  rf and y10 were replaced by garbage as well.
- Result: output columns <= t were bit-identical (compared as int64 views) at all 100 cuts, with 0 failures.

## 6. Reproduction: OK
- The rule's median CAGR on the fresh ON world is 0.053942, against the designer's 0.0539, a difference of 0.000 pp. The
  limit was 0.2 pp.
- Every other headline number also reproduces exactly:
  - OFF median 0.030383;
  - ON p10 -0.00536;
  - ON P(MDD <= -80%) 0.144;
  - ON average level 0.561;
  - delay 3: 0.05369, delay 5: 0.05345, cost 0.6%: 0.05285.

## 7. Simulator sanity: OK
- mechanism=False takes a separate code branch. It has iid Gaussian diffusion plus iid Bernoulli/Poisson crash days at
  the constant rate lam_bar, with the same Gamma size distribution and compensation. There is no Hawkes term, no
  background fragility, no volatility coupling, no belief gap, no scar and no overshoot.
  - The OFF world shows |excess| autocorrelation of 0.000 at lags 1, 5, 20 and 60. In ON it is 0.13, 0.12, 0.10 and 0.07.
  - The correlation of yearly log variance with the next year's excess return is 0.003 OFF and 0.338 ON.
- ON and OFF use identical drawn parameters (pi_bar, sigma_bar, jshare, Ybar, kY, lam_bar) and identical rf and y10 paths.
  The unconditional level matches:

  | world | premium median | premium pooled mean | volatility median |
  |---|---|---|---|
  | ON | 0.0314 | 0.0315 | 0.1762 |
  | OFF | 0.0307 | 0.0309 | 0.1741 |
- There are no NaN or inf values in r, rf or y10 (2000 paths each, ON and OFF), and r[:, 0] = 0.
- Disk: the folder is about 0.3 MB. No large cache was left. The only cache was a `__pycache__` folder that my own audit
  runs created at the top level, and I deleted it before finishing.

## Changes made
None. No mechanical defect was found, so no file of the designer was edited and no number was re-run after a fix. The only
files added are this AUDIT.md and the audit/ folder (scripts, logs, json).

## Remarks for the record (not defects)
- G-ON fails by 0.04 pp; the paired bootstrap CI is [-0.27, +0.21] pp. The designer says plainly that the mechanism beats
  constant levels by about 2.7 pp but gives no edge over the same-basis 1x hold after the costs of the 3x product plus cash.
  This is the honest fallback outcome the brief allows.
- The median exposure is about 0.55. In the worlds without the scar and overshoot premium (OFF, NOSCAR, FLAT), the rule
  trails hold 1x by 2.3-2.8 pp per year (designer's fresh-seed table, reproduced for OFF).
