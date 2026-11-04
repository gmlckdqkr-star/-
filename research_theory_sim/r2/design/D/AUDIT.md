# AUDIT - lane TS2 round 2, design lane D (theory FCCL, rule "tracked constant exposure 1.25")

Blind auditor, 2026-11-04T11:57Z to 2026-11-04T12:08Z (all timestamps from `date -u +%Y-%m-%dT%H:%MZ`).
**Verdict: PASS.** No defect was found and no file of the designer was changed. Every gate, headline and robustness number
reproduces bit-for-bit on the designer's fresh seed 12000, and with the same sign on an extra unused fresh seed (13000).

## 0. What the auditor read and ran (blindness of the audit itself)
- Read: `r2/DESIGN_BRIEF_R2.md`, `common/exec_engine.py`, and the files in `r2/design/D/` (THEORY.md, sim.py, rule.py,
  design_log.md, READ_LOG.md, synth_results.json, sim_stats.txt, work/*.py, work/*.out, work/variants.jsonl).
- Opened nothing else under /mnt/project-files: no other lane, no round-1 folder, no test/verify/holdout, no protocol,
  RESULT or FREEZE file. No memory files, no network, no MCP data tools. Real market data was not touched.
- Context note: the auditor's session context lists tool and skill names that look like trading or market-data tools, and
  the computed task text repeats the designer's own synthetic numbers. The auditor used none of these tools. The synthetic
  numbers were used only as the claims to check.
- Audit scripts and their outputs are in `audit/` (gates.py, interface.py, causality.py, sim_check.py and the matching
  *.out). Everything ran with `/root/.cache/ts-venv/bin/python -I -B`, so no `__pycache__` was written.

## 1. Blindness - PASS
- READ_LOG.md lists only the brief, exec_engine.py and the designer's own folder. It declares the tool and skill names in
  the context as ignored, and says no project memory was present.
- Grep of every .py in the folder (rule.py, sim.py, work/*.py) for `open(`, `np.load`, `loadtxt`, `genfromtxt`,
  `read_csv`, `read_`, `urllib`, `requests`, `http`, `socket`, `subprocess`, `os.system`, `glob`, `listdir`, `/tmp/claude`,
  `/home/user` and /mnt/project-files paths found:
  - imports of `sys`, `json`, `time`, `itertools` and `numpy`, plus `exec_engine` and the designer's own modules;
  - `sys.path` inserts that point only to `theory_sim/common` and `r2/design/D` (and its `work/`);
  - `open(` used only to append the designer's own `work/variants.jsonl` and `work/final_parts2.jsonl`.
  The grep found no reads of any other file, no network use and no subprocess calls. rule.py imports only `math` and
  `numpy`, and its source contains no I/O tokens.
- Real-history facts in the mechanism: none found. The code has no calendar dates, no named indices or episodes, and no
  data tables. The rate model (0.25 pp steps at 21-day meetings, at most 0.75 pp per meeting, trend bounds 0 to 15%,
  regime lengths LogNormal(ln 5 y, 0.6)) consists of generic institutional facts with stated reasons. Each mechanism
  parameter is a wide uniform or lognormal range with an economic reason in THEORY.md section 6. rule.py's constants are
  the exec_engine constants (fee 2.45%/yr, 2% cash spread, 15.4% interest tax, warm-up 300, delay 2), a 20-day activity
  half-life and the two tuned parameters.
- Timeline. THEORY.md has `PRIORS_FROZEN 2026-11-04T10:56Z`. THEORY.md was last modified at 11:03:34. That edit is the
  "Implementation notes" section: the normaliser now comes from an independent pilot run, and two numerical clips were
  added (premium factor in [0.1, 10], daily return floored at -30%). The prior table is unchanged. The first design
  script, work/base.py (holds and constant levels), dates from 11:04:34. The first rule-family scripts, work/oracle.py and
  work/g1.py, date from 11:06 and 11:07. So the priors predate the rule-design work.
  sim.py was modified at 11:05:18 (the `states=True` option). Running the current sim.py reproduces sim_stats.txt
  (written 11:04:18) digit for digit, and `states=True` leaves the paths bit-identical, so the simulated worlds have not
  changed since rule design began.
  - Minor note (not a defect): the 11:03 implementation notes change the simulator after the PRIORS_FROZEN line. They come
    before any rule work, and the log discloses them.
  - Minor note (not a defect): the designer looked once at fresh seeds 10000-10003 with candidate A (carry tilt). After a
    flag there, the designer switched to the simpler rule B and re-ran every final number on new seeds 12000-12003. The
    design log discloses this. E0 = 1.25 and THETA = 0.35 are already the best or near-best tracked constants on
    selection seeds 1 and 2 (variants s8, s9, s11), so B's parameters were not chosen on the fresh seeds.
- N = 146 variants: 134 rows in work/variants.jsonl plus 12 configurations in work/g6.out. The final rule has 2 tuned
  parameters. Fresh seeds 10000 and above were not used for selection, apart from the disclosed flag above.

## 2. Anchors (brief 2b-2d) - PASS
- THEORY.md section 5, "Published anchors", names its sources: Dimson-Marsh-Staunton (Triumph of the Optimists and the
  Yearbook), Jorda-Knoll-Kuvshinov-Schularick-Taylor 2019, Siegel, Shiller/DMS dividend yields, Mandelbrot/Fama and DMS
  drawdowns. It gives the remembered numbers and its confidence in each. The conversion is: total-return arithmetic
  premium over bills of 6.0%, minus a 3.5% dividend yield, gives 2.5% for a price index. Markets with reinvested
  distributions keep a 6.0% centre. The volatility centre is 17%.
- Per-path draws from sim.py (P = 2000, seed 1), p10 / median / p90:

| quantity | p10 | median | p90 | centre in THEORY.md |
|---|---|---|---|---|
| mu_bar, price-index paths (n = 1257) | 0.0019 | **0.0252** | 0.0476 | 0.025 |
| mu_bar, total-return paths (n = 743) | 0.0376 | **0.0603** | 0.0820 | 0.060 |
| mu_bar, all paths (65/35 mixture) | 0.0073 | 0.0367 | 0.0715 | mixture |
| sigma_bar | 0.125 | **0.171** | 0.231 | 0.17 (log-sd 0.240 against 0.25 stated) |
| Student-t df | 3.96 | 5.73 | 7.47 | U(3.5, 8) |
| realised premium over rf, ON / OFF | | 0.0392 / 0.0392 | | |
| realised vol / sigma_bar, ON / OFF | 0.60 / 0.98 | 0.965 / 0.998 | 1.42 / 1.02 | RMS 1.06 / 1.00 |

- Haircut check: none found. 6.0% sits between the cited world (5.5-6%) and US (about 7%) arithmetic premia, near the
  multi-country average. The 3.5% dividend yield is below the cited long-run 4%, which makes the price-index premium a
  little higher, not lower. 17% volatility is the cited central value. The width of the prior is carried by the sd
  (1.8 pp on the premium, 0.25 in log on volatility), not by moving the centres.
- Drawdowns are checked as an output, as the theory says. The share of 30-year paths with a 1x drawdown of -50% or worse
  is 0.44 (ON) and 0.38 (OFF). That is a little below the "once every 30-40 years" anchor (about 0.55 by a Poisson
  reading), but the anchor counts real declines and the simulator gives nominal price drawdowns, so the gap is plausible.
- 2c: the premium and volatility are drawn per path (above), and the I_TR flag gives a two-basis mixture. PASS.
- 2d (P = 2000, seed 1):
  - 72% of paths have a 10-year window in which the short rate rises by at least 3 pp, and 64% have one in which it falls
    by at least 3 pp.
  - 30% have a steady 10-year rise (at least 3 pp, with at least 8 of the 10 yearly steps up), and 20% have a steady fall.
  - 44% have a 5-year window in which the rate stays within a 1 pp range (stable periods).
  - The rate changes on 2.4% of days, in steps of 0.25, 0.5 or 0.75 pp. PASS.

## 3. Gates, re-run on the designer's fresh seed 12000, P = 2000 per world (`audit/gates.py 12000 2000 rob`)

| world | rule | 1x hold | 2x hold | 3x hold | best constant (L) | rule - best const | rule - 1x hold | gate |
|---|---|---|---|---|---|---|---|---|
| ON | 0.054217 | 0.068185 | 0.046714 | 0.031766 | 0.041964 (1.0) | +1.22 pp | -1.40 pp | **G-ON FAIL** |
| OFF | 0.048474 | 0.065910 | 0.038223 | 0.003615 | 0.037354 (0.5) | +1.11 pp | -1.74 pp | **G-OFF PASS** |

- Constant levels 0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0:
  - ON: 0.0398 / 0.0420 / 0.0406 / 0.0379 / 0.0330 / 0.0318.
  - OFF: 0.0374 / 0.0372 / 0.0337 / 0.0290 / 0.0175 / 0.0036.
- These are identical to synth_results.json to all printed digits. The designer's gate claims (gate_on_pass = false,
  gate_off_pass = true) reproduce.
- Extra check on an unused fresh seed, 13000 (P = 1000):
  - ON: rule 0.0517, 1x hold 0.0658, best constant 0.0414 (L = 1). G-ON fails.
  - OFF: rule 0.0447, best constant 0.0347 (L = 0.5), a loss of -0.99 pp (that is, a gain). G-OFF passes.
  - Same conclusion as on seed 12000.

## 4. Interface - PASS (`audit/interface.py`)
- Imports: `math` and `numpy` only. `INPUTS = ('close', 'rf')`. `PARAMS = {'E0': 1.25, 'THETA': 0.35}` is a literal dict.
  The signature is `target_levels(close, rf, y10=None, params=PARAMS)`. The function is deterministic, and y10 is
  ignored (identical output with y10 given or None).
- Inputs are not modified (checked with array_equal, NaN-aware, after a run on edge-case inputs).
- Output: shape (P, T), float64, every value in [0, 3] and on the 0.5 grid. The rule never outputs NaN; it uses 0 for cash.
- Edge cases all run without error and end in cash where they should, then return to the market:
  - 500 leading NaN columns, 200 leading zeros, a 300-day flat stretch, a NaN gap, a single zero, an all-flat path, an
    all-NaN path, NaN rf, NaN y10, inf and negative prices;
  - short arrays (T = 400) and float32 input.
- Scale invariance: output identical (bit-equal) for close x 1000, 1e-3, 7.77, 1e6 and 0.0123, and for a series that
  starts at 1.
- Speed: P = 500, T = 10000 runs in 1.3 s, well under the 60 s limit.

## 5. Causality (exact) - PASS (`audit/causality.py`)
- 50 synthetic paths, T = 7860. The base inputs include leading NaN, a flat stretch and leading zeros.
- 100 cut points, 15 of them below 300 (t = 0, 1, 2, 5, 20, 100, 250, 297-299 and 300-303) and 6 at 7800 or later (up to
  7859); the rest are random.
- For each cut, every column after t of close, rf and y10 was replaced in rotation by one of five continuations:
  - another world's path (rescaled);
  - all NaN;
  - garbage (0, -5, +-1e300, +-inf, NaN, 1e-300 in close; 1e10, -1, NaN, inf in rf; noise of sd 1e6 in y10);
  - a crash-and-rally random walk;
  - all zeros.
- Result: 0 of 100 cuts showed any difference in columns up to t (bit-identical, NaN-aware).
- Power check: a different continuation changes later outputs on 50 of 50 paths.
- Path independence: a path run alone gives the same output as that path inside the batch.

## 6. Reproduction - PASS
- Headline rule median CAGR: ON 0.054217 and OFF 0.048474, against the designer's 0.0542 / 0.0485. The difference is
  0.00 pp (bit-identical), inside the 0.2 pp tolerance.
- Robustness on seed 12000 (P = 2000) also reproduces exactly:

| row | ON | OFF |
|---|---|---|
| delay 3 | 0.05418 | 0.04840 |
| delay 5 | 0.05422 | 0.04876 |
| cost 0.006 | 0.05299 | 0.04762 |

- Also identical: rule p10 -0.0275, P(MDD <= -80%) 0.2315, median level 1.16 (ON).
- rule.py sha256 is `6246c68a961167f51d7bfe704f8293ea3f7d7a77a98d123cd3dea79bf98fe3ec`, which matches
  synth_results.json.

## 7. Simulator sanity - PASS (`audit/sim_check.py`)
- With `mechanism=False`, `_chunk` returns before any ledger, VaR, normaliser, carry or duration term is computed:
  `r = rf + mu_bar dt + sigma_bar sqrt(dt) z`.
- ON and OFF use identical per-path mu_bar, sigma_bar and df, and identical rf and y10 paths. Their shocks agree: the
  standardised ON shock and the OFF shock correlate with a median of 0.996 (p10 0.966).
- OFF is i.i.d.:

| statistic (median over paths) | ON | OFF |
|---|---|---|
| acf of abs(r), lag 1 / 20 / 250 | 0.20 / 0.18 / 0.07 | 0.000 / 0.000 / -0.001 |
| corr(r_t, spread at t-1) | | 0.0000 |
| corr(r_t, change in y10 at t) | -0.019 | -0.0006 |

- Same unconditional level:
  - Realised premium, ON minus OFF per path: mean -0.03 pp, median +0.06 pp.
  - Realised vol / sigma_bar: median 0.965 ON against 0.998 OFF, and RMS 1.06 against 1.00. The ON world's per-path vol
    is more dispersed by construction (slow capital regimes). The level matches closely enough; this is not a defect.
- No NaN or inf in r, rf or y10 in the ON and OFF worlds, with prior_scale 0.5 or 1.5, or in the block-resampled world.
  r[:, 0] = 0.
- Disk: the folder is 0.35 MB in total, with no cache files and no `__pycache__`. Nothing over 200 MB, and nothing to delete.

## 8. Observations for the tester (no change made)
1. The rule is a constant exposure of 1.25. Its +1.1 to +1.2 pp margin over the best constant level is purely
   execution: it replicates the engine's no-rebalancing drift and resets the 3x/cash mix about 0.4 times a year. That
   margin is the same with the mechanism ON or OFF. The designer says so plainly. It is not evidence for FCCL.
2. The replica hard-codes the engine's warm-up of 300 columns, delay 2, fees, cash spread and interest tax. If the real
   test engine differs, the tracking is only approximate. The delay 3 and 5 rows show it is insensitive to the delay.
3. The rule goes to cash when more than about half of the recent days (20-day half-life) have a zero return. On a real
   series with many stale (unchanged) closes this would cause unintended cash spells. On a liquid daily index it is
   unlikely to bind.
4. In the designer's world, G-ON (beating the 1x hold) is infeasible for this instrument set at the anchored premium:
   even the designer's tracked oracle (true mu_t and sigma_t) stays below the 1x hold. The auditor did not re-run the
   oracle. The gate failure itself is reproduced and honestly reported.

## Changes made by the auditor
None to the designer's files: rule.py, sim.py, THEORY.md, design_log.md, synth_results.json and READ_LOG.md are
unchanged. Added only `AUDIT.md` and the `audit/` folder (scripts and outputs).
