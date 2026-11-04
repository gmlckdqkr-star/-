# AUDIT: lane TS2, round 2, design lane B ("Two-clock yardstick learning", TCYL)

Blind auditor. Audit run 2026-11-04T11:22Z to 11:31Z (all times from `date -u +%Y-%m-%dT%H:%MZ`).
**Verdict: PASS.** No defects found and no files changed. rule.py is untouched: sha256 `8051732d8fc4d28a211491f73f73978cccb21bd6aec0de265c96e3f25366cabb`, the same hash design_log.md records at selection.
The design itself fails G-ON. The designer reports this openly and ships the brief's fallback rule, so the audit verdict does not depend on it.

## What the auditor read
- /mnt/project-files/research/theory_sim/r2/DESIGN_BRIEF_R2.md (the rules)
- /mnt/project-files/research/theory_sim/common/exec_engine.py
- /mnt/project-files/research/theory_sim/r2/design/B/ : THEORY.md, sim.py, rule.py, design_log.md, final_eval.py,
  synth_results.json, READ_LOG.md, work/*.py, work/variants.jsonl
- I opened no other path under /mnt/project-files. I used no network, no MCP or data tools and no memory.
- My audit scripts are in `audit/`: a_anchor.py, a_gates.py, a_iface.py, a_causal.py, a_selrepro.py, a_misc.py, plus
  the output logs gates_10001.txt and gates_10777.txt. I ran them with /root/.cache/ts-venv/bin/python. The
  `__pycache__` folders my imports created have been deleted.
- I could not read the designer's session record; this auditor has no access to it. The blindness check therefore
  rests on READ_LOG.md, the code and the file timestamps.

## 1. Blindness: OK
- READ_LOG.md lists the brief, exec_engine.py and the designer's own files. It also declares one temporary script in
  the session scratchpad (outside /mnt/project-files), which was later deleted. It declares that the host context
  contained skill and tool names, and says they were ignored.
- I grepped every .py file for file, network and process access (`open(`, np.load, loadtxt, genfromtxt, read_csv,
  read_, urllib, requests, http, socket, subprocess, os.system, glob, listdir, and paths). What the grep found:
  - final_eval.py writes synth_results.json in the lane folder.
  - work/lib.py reads and appends to work/variants.jsonl.
  - work/dbg1.py, work/val2.py and work/val3.py `exec(open(...))` sibling scripts in work/.
  - sys.path entries point only to `common/` and `r2/design/B`.
  - Nothing reads /tmp/claude or /home/user, and nothing uses the network or a subprocess.
  - rule.py imports `numpy` and `math` only (checked with the AST). It does no file input or output and makes no
    eval, exec or `__import__` call.
- Hard-coded real-history facts: none found.
  - No calendar dates, named indices or named episodes appear in sim.py, rule.py or work/.
  - The constants in sim.py match the THEORY.md priors one for one: mu, sigma, nu, h_v, s_v, A, B, the 0.70 cap,
    h_m, h_s, rho, rf0, regime durations, slopes, noise, jumps, the [0, 16%] bounds, monthly steps (probability 0.4),
    the y10 term premium and the 500-day burn-in.
  - The rule's own constants are the published anchors (mu0 = 3%, starting vol 0.17) and 1.25 = sqrt(pi/2), the factor
    that converts mean |x| into a standard deviation.
  - One detail is not in THEORY.md: the rate noise is damped near the zero lower bound (`min(1, L/0.01)`). It is
    mechanical and harmless.
- PRIORS_FROZEN: THEORY.md contains `PRIORS_FROZEN 2026-11-04T10:54Z`, and its mtime is 10:54:42, so it has not
  changed since the freeze. The first work script dates from 10:57 and the first logged variant from 11:00Z, so the
  freeze predates all rule design.
- Later changes to sim.py:
  - 10:59Z, OFF-world demeaning bug fix. This is a code change, not a prior change, and it was made before any rule
    variant was evaluated.
  - 11:15Z, the `prior_scale` option for robustness runs. sim.py's mtime is 11:17.
  - With the current sim.py, I reproduced variant N=1 (logged 11:00Z, seed 11, P=500) bit for bit in both worlds:
    ON 0.03343657910423925 and OFF 0.03884147676848637. I also reproduced variant N=62 (the selected C1) on seed 21 to
    every logged digit: 0.03971 / 0.04168. So the simulator with prior_scale = 1 has not changed since selection began.
- Seed discipline: variants.jsonl has 72 entries, all on seeds 11, 12 and 21-24. The fresh seed 10001 appears only in
  final_eval.py. One small inconsistency: design_log says the selection procedure was "fixed 11:05Z, before the main
  grids", but variants 1-20 were logged 11:00-11:05Z. These were coarse screens and they are counted in N, so this
  does not affect the result.

## 2. Anchors: OK
- THEORY.md section 7, "Published anchors", names its sources with numbers, the conversion and a certainty level:
  - Dimson-Marsh-Staunton (Triumph of the Optimists and the Yearbooks)
  - Jorda et al. 2019
  - Shiller's long-run US series
  - Mehra-Prescott 1985
  - a drawdown sanity range
- Conversion: a total-return arithmetic premium of 6.5% (midway between world ~6% and US ~7%) minus a 3.5% dividend
  yield gives a 3.0% price-index premium. The volatility centre is 17%.
- Cross-check: 3.0% minus sigma^2/2 (1.45%) gives a log price premium of about 1.55%. Adding 3.5% of dividends gives a
  geometric total-return premium of about 5.0%, between the cited world 4.5% and US 5.5%.
- **Not a conservative haircut.** Both centres sit at the middle of the cited ranges. A recent-era 2% dividend yield
  would imply a price premium of about 4.5%; that lies within about 0.6 prior standard deviations, so the prior covers it.
- Medians computed from sim.py on 2000 paths (from a_anchor.py):

| seed / world | drawn mu: median (sd) | drawn sigma: median | realised arithmetic premium: median [p10, p90] | realised vol: median | worst 1x drawdown: median | P(drawdown <= -50%) | P(drawdown <= -80%) |
|---|---|---|---|---|---|---|---|
| 777 ON   | 2.95% (2.46 pp) | 17.1% | 3.08% [-1.6, 7.9] | 17.1% | -47% | 0.44 | 0.058 |
| 777 OFF  | 2.95% (2.46 pp) | 17.1% | 3.08% [-2.4, 8.5] | 17.2% | -48% | 0.46 | 0.070 |
| 10001 ON | 3.05% (2.32 pp) | 17.1% | 3.15% [-1.4, 7.6] | 17.0% | -48% | 0.45 | 0.050 |
| 10001 OFF| 3.05% (2.32 pp) | 17.1% | 3.06% [-2.2, 8.2] | 17.1% | -48% | 0.46 | 0.067 |

- 2c, per-path variation: premium and volatility are drawn per path. Premium sd is 2.3-2.5 pp; volatility p10-p90 is
  about 12-24%. Realised volatility tracks the drawn sigma with correlation 0.999. The drawdown frequencies agree with
  the cited "40-60% per 30 years typical, beyond -80% rare".
- 2d, rates:
  - Regimes are 3-15 years long, back to back, each up, down or flat, with slopes of 0.2-1.2 pp/yr.
  - 69-70% of paths contain a 10-year rise of at least 3 pp, and 50% a 10-year fall of at least 3 pp. The fall share is
    lower because the zero lower bound truncates falls.
  - 86-87% contain a stable 10-year stretch (change under 0.5 pp).
  - Median rf over a path is about 4.8%.

## 3. Gates: the designer's claims reproduce
Fresh seed 10001 from design_log.md, P = 2000 (a_gates.py; output in gates_10001.txt). Values are median after-tax
30-year CAGR.

| world | rule | hold 1x | hold 2x | hold 3x | const 0.5 | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 | best const | gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ON  | 4.098% | 6.053% | 2.584% | -1.561% | 3.338% | 3.350% | 2.976% | 2.322% | 1.322% | -1.561% | 3.350% (1.0) | G-ON **FAIL** (beats best const by +0.75 pp, loses 1.95 pp to hold 1x) |
| OFF | 4.351% | 6.044% | 2.745% | -1.328% | 3.611% | 3.472% | 3.088% | 2.509% | 1.497% | -1.328% | 3.611% (0.5) | G-OFF **PASS** (+0.74 pp vs best const) |

- Every number equals synth_results.json to the last printed digit.
- The designer's claims hold: gate_on_pass = false and gate_off_pass = true.
- Extra check on a seed the designer never used (10777, P = 1000):

| world | rule | hold 1x | best const | result |
|---|---|---|---|---|
| ON  | 3.80% | 6.03% | 3.20% (0.5) | G-ON fails |
| OFF | 4.21% | 6.14% | 3.38% (0.5) | G-OFF passes, +0.83 pp |

  The same pattern holds.

## 4. Interface: OK
- Imports, names and signature: rule.py imports numpy and math only. `INPUTS = ('close', 'rf')`. `PARAMS` is a literal
  dict with 5 entries (6 are allowed). The signature is `target_levels(close, rf, y10=None, params=PARAMS)`. The
  docstring has 6 lines.
- Inputs are not modified (close, rf and y10 compared before and after the call). The rule ignores y10: output is
  identical with and without it. The output is deterministic.
- Output: shape (P, T), float64, values in [0, 3] or NaN, never inf. It is NaN for the first 60 valid returns and
  has no NaN after column 300 on a normal path.
- Edge cases (from a_iface.py):

| case | result |
|---|---|
| NaN prefix (800 columns) | first output at column 860 |
| zero prefix (500 columns) | first output at column 560 |
| flat stretch (600 columns) | level held |
| NaN gap | handled |
| zeros in the middle | handled |
| entirely flat path | all NaN, i.e. cash |
| entirely NaN path | all NaN, i.e. cash |
| inf or negative close | ignored |
| NaN rf | handled |
| negative rf | handled |

  No floating-point warnings were raised under `np.errstate(all='raise')`.
- Scale invariance:
  - Output is the same to floating-point precision but **not bit-identical** under close x1000, x0.001, x1024 and x7.3.
    The largest level difference is 1.0e-12 (1.5e-12 on 2000 paths).
  - The cause is `log(k*c)`, which is rounded separately from `log(c)`. No floating-point log formula is bit-exact for
    a general factor k such as 1000.
  - The effect never reaches a trade: on the 2000 paths of seed 10001, engine CAGRs under x1000 are bit-identical on
    every path. The engine trades in 0.5 steps with a hysteresis band, and a difference of 1e-12 never crossed it.
  - I classify this as not a defect and made no change.
- Speed: P = 500, T = 10000 takes 1.3 s.
- Observations, not interface defects (no change made, since the logic is the designer's):
  - After a flat or NaN stretch, the first valid return spans the whole gap but is counted as one day. The volatility
    estimate jumps and the level falls to near 0 for a few weeks. This only matters for a market with long internal
    gaps.
  - One finite but absurd rf value (1e307, which overflows to -inf in the EWMA) leaves the output NaN (cash) for the
    rest of the path. A real rf series cannot take such a value, and the brief requires robustness to anomalies in
    close, not in rf.

## 5. Causality (exact): OK
- Test setup (a_causal.py): 50 synthetic paths with T = 7860 and 100 cut points. 26 cuts are below 300, including
  0, 1, 5, 59, 60 and 61, and the latest is 7858.
- At each cut t, every column after t of close, rf and y10 was replaced, rotating through five kinds of continuation:
  1. a different simulated world;
  2. all NaN;
  3. garbage (0, -1, 1e300, +-inf, NaN, 1e-300, a constant; rf NaN, 1e10, -5, 0 or inf);
  4. a wild random walk with random rates;
  5. zeros.
- Result: **0 leaks.** Output columns up to t were bit-identical in every case, NaN payloads included.

## 6. Reproduction: OK
- The fresh-seed headline was re-run with exec_engine on seed 10001, P = 2000:
  - ON: rule median CAGR 4.098% vs 4.10% reported (difference 0.00 pp).
  - OFF: 4.351% vs 4.35% reported.
- Robustness rows also reproduce:
  - ON: delay 3 4.091%, delay 5 3.955%, cost 0.6% 3.839% (reported 4.09 / 3.96 / 3.84).
  - OFF: delay 3 4.319%, delay 5 4.306%, cost 0.6% 4.059% (reported 4.32 / 4.31 / 4.06).
- Other reported figures that reproduce: rule p10 -2.76%, P(drawdown <= -80%) 0.1135, average level 1.107 and 4.07
  trades/yr (all ON).

## 7. Simulator sanity: OK
- mechanism=False really disables the mechanism. The OFF branch returns the fundamental returns d + c*u and never
  calls the belief solver.
- I ran the ON solver with A = B = 0 forced. Its log returns differ from the OFF world by at most 6.4e-5 per day. The
  only difference is how the shock scale is calibrated (to the std of x versus the std of u).
- Same seed, ON vs OFF:
  - Same per-path mu, sigma, nu, h_v and s_v, and identical rf and y10 paths.
  - Same drift, and realised volatility equals sigma in both worlds (ratio median 1.000; range 0.98-1.07 ON,
    0.996-1.002 OFF).
  - Realised arithmetic premium medians match: 3.08% vs 3.08% on seed 777.
  - The mechanism visibly acts in ON: median daily skew is -1.09 ON vs 0.00 OFF.
- No NaN or inf in r, rf or y10 on 2000 paths for seeds 777 and 10001 in either world, and r[:, 0] = 0.
- Runtime for 2000 x 7860: ON 10-11 s, OFF 7-10 s.
- Disk: the lane folder is about 204 KB including audit/. There are no caches, no .npy/.npz/.pkl files, and the
  `__pycache__` folders created during the audit have been deleted.

## Changes made by the auditor
None to rule.py, sim.py, THEORY.md or the results. I added this AUDIT.md and the folder `audit/` (audit scripts and
logs only).
