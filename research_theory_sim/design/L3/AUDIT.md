# AUDIT of lane TS1 / L3 (theory SGNC, rule SGNC-K): blind auditor

Audit ran 2026-11-04T08:29Z to 08:36Z (times from `date -u`). Verdict: **PASS**. No file in the lane was changed except this one.

## What the auditor opened
- /mnt/project-files/research/theory_sim/DESIGN_BRIEF.md (the rules)
- /mnt/project-files/research/theory_sim/common/exec_engine.py
- every file in /mnt/project-files/research/theory_sim/design/L3/. The runs_*.jsonl files were only line-counted and not read.
- My own audit scripts in my session scratchpad, under `.../scratchpad/audit/` (iface.py, causal.py, repro.py,
  simsan.py, repro.json).
- I ran one `ls` of the scratchpad root, to check where design_lib.py caches its data. It showed only file names, and I
  opened none of those files. See note B3.

I used no network, no MCP data tools, no memory files, no other lane's folder, no test/, holdout/ or TEST_PROTOCOL.md,
and no git.

## 1. Blindness: PASS
- READ_LOG.md lists only DESIGN_BRIEF.md and common/exec_engine.py outside the lane folder. It also records that
  tool and skill names appeared in the context. It reports no numbers.
- I grepped every .py file for open(, np.load, loadtxt, genfromtxt, read_csv, read_, urllib, requests, http, socket,
  subprocess, os.system, /mnt/project-files, /tmp/claude and /home/user. What I found:
  - rule.py and sim.py: no I/O. rule.py imports only numpy and math.
  - design_lib.py: np.load and np.savez of its own simulator cache, at
    `/tmp/claude-0/-home-user--/3909d02b-.../scratchpad/l3cache`. That cache holds synthetic data only.
  - grid1.py and grid2.py write runs_*.jsonl in the lane folder. grid2.py reads a variant-list JSON passed in argv,
    and the variants it evaluated are logged in runs_stage2/3.
  - show.py reads the lane's own runs_*.jsonl. final_eval.py writes synth_results.json.
  - rules_lib.py imports scipy.ndimage, at design time only (family C).
  - No /mnt/project-files path outside the lane folder and common/ appears in any file. No /home/user path appears
    anywhere.
- Hard-coded real history: I found none. No calendar years, named indices or named episodes appear. The `20xx`
  matches were P=2000 path counts. The rule constants (a=0.005, beta=0.01, N=126, Hv=60) come from the logged
  synthetic grids (runs_stage1_G3 and stages 2 and 3). The priors are wide, and the background knowledge they use is
  declared in THEORY.md section 8.
- PRIORS_FROZEN:
  - The line `PRIORS_FROZEN 2026-11-04T07:56Z` is present in THEORY.md.
  - THEORY.md's mtime is 07:56:47, so the file was not edited after the freeze.
  - sim.py's mtime is 07:57:50.
  - The rule-design code was written later: rules_lib.py at 08:15, design_lib.py at 08:03, the grids from 08:18.
  - design_log.md's timeline agrees: grids started 08:01Z and 08:03Z.
  - So the priors predate the rule design.
- Variant count: the runs_*.jsonl files hold 449 rows in total (stage 1: 434, stage 2: 8, stage 3: 7). This matches
  the reported N=449.
- Minor procedural notes (not contamination):
  - (B1) The simulator cache and some throw-away scripts were written to the session scratchpad, which is outside the
    lane folder. The brief says "write only inside your own folder". This was disclosed in READ_LOG.md, and the files
    are synthetic.
  - (B2) The stage-2/3 variant-list JSON files are not stored in the lane folder. Their contents are reproduced row by
    row in runs_stage2_s1.jsonl and runs_stage3_s2.jsonl.
  - (B3) Other lanes appear to share this scratchpad: the listing showed file names such as `audit_l1.py`. I did not
    open them. It is a possible cross-lane channel. I found no evidence that L3 used it, and design_lib.py reads only
    its own `l3cache/s{seed}_{mech}_{P}_{prior}.npz` files.

## 2. Interface: PASS
- Imports: `numpy` and `math` only (checked with ast).
- `INPUTS = ('close', 'rf')` and `PARAMS = {'a': 0.005, 'beta': 0.01, 'N': 126, 'Hv': 60}`. The signature is
  `target_levels(close, rf, y10=None, params=PARAMS)`.
- Output on 200 lane-simulator paths:
  - Shape (200, 7860), float64, range [0, 3].
  - NaN only during warm-up, until 20 valid returns exist (0.25% of cells).
- Robustness to bad inputs: I tested leading NaN closes, NaN gaps, an all-NaN path, inf, zero and negative closes,
  NaN rf blocks and whole-path NaN rf.
  - No crash. No floating-point error, even under `np.errstate(all='raise')`.
  - Output stays finite in [0, 3] or NaN, and the all-NaN path comes back all NaN.
  - 1-D input returns shape (1, T). A 1-D rf is broadcast. T=5 works.
- Scale invariance:
  - Not bit-identical. close*1000 changes the output by at most 3e-13 (at most 6e-13 for scales 1e-3 to 1e6). The cause
    is floating-point rounding of ct/last, which cannot be avoided for a non-power-of-2 scale.
  - After 0.5-step quantisation the engine result is identical: max |dCAGR| = 0.0 on 200 paths, and 0.0 on the 2000
    fresh-seed ON paths.
  - I judged this a pass, and no fix is needed.
- Speed: P=500, T=10000 runs in 0.82 s. The rule is deterministic.

## 3. Causality (exact): PASS
- Setup: 50 lane-simulator paths (seed 4242, mechanism ON) and 100 distinct cut points t, all with y10 supplied.
  - Fixed cuts: 0, 1, 5, 19, 20, 21, 125, 126, 127, 299, 300, T-10, T-3, T-2.
  - 24 cuts below 300 and the rest random up to 7858.
- For each cut, every column > t of close, rf and y10 was replaced by a different random continuation. The close
  continuation came from another world (seed 9191, mechanism OFF), with extra random-walk noise on alternate cuts and
  injected NaNs on every fifth cut. rf and y10 were replaced by uniform random values.
- Result: columns <= t were bit-identical (`np.array_equal(..., equal_nan=True)`) in 100 of 100 cuts. No leaks.

## 4. Reproduction: PASS (exact)
Fresh seeds 10000 and 10001 (P = 1000 each), as written in design_log.md, scored with exec_engine defaults. All values
are medians of the after-tax 30-year CAGR.

| | reported | reproduced |
|---|---|---|
| rule, ON | 0.02262 | 0.022625 |
| rule p10, ON | -0.00343 | -0.003434 |
| rule p_dd80, ON | 0 | 0.000 |
| hold 1x, ON | 0.03213 | 0.032132 |
| delay 3, ON | 0.02277 | 0.022772 |
| delay 5, ON | 0.02266 | 0.022657 |
| cost 0.006, ON | 0.02131 | 0.021307 |
| rule, OFF | 0.01322 | 0.013217 |
| hold 1x, OFF | 0.03199 | 0.031994 |

- The difference is 0.00 pp on every row.
- The rule had no NaN-CAGR paths in either world, so the designer's "NaN = -100%" fix does not affect these numbers.
- In its own world the rule loses to same-basis hold 1x by about 1 pp/yr (ON) and 1.9 pp/yr (OFF). The design log
  states this honestly.

## 5. Simulator sanity: PASS (with notes)
Tested on seed 555, P = 1000, T = 7860.
- Per-path priors:
  - All 19 parameters are drawn per path, with shape (P,). They fall inside the base-prior ranges of THEORY.md
    section 6, for example D_up in [0.50, 8.00], k in [1.50, 24.9] and prem in [0.010, 0.080].
  - rf_monthly is set on 31% of paths (the prior is 0.3).
  - The ON and OFF worlds use identical parameters.
- mechanism=False disables the mechanism. Momentum is measured as the pooled slope of the forward 63-day annualised
  excess log return (from t+3) on z_126.

  | measure | ON | OFF |
  |---|---|---|
  | slope | +0.0233 | +0.0006 |
  | mean forward return after z > 1 | +3.6%/yr | +0.08%/yr |
  | mean forward return after z < -1 | -4.0%/yr | +0.04%/yr |
  | median annual-horizon variance | 0.0318 | 0.0318 |

  - The variance match shows the OFF world keeps the same scale.
  - In ON, the median lag from a story switch until beliefs x cross 0.5 is 23 days (p90: 118 days). In OFF, beliefs
    jump at the switch date.
  - The OFF random stream is identical to ON up to the post-loop i.i.d. noise, and it is deterministic.
- r, rf and y10:
  - No NaN or inf in r or rf. r[:, 0] = 0. rf lies in [0, 0.163]/yr. y10 is None, which the brief allows.
- Notes:
  - (S1) The OFF world contains one-day story-switch jumps of up to -0.98*dm, and dm is capped at 1.0. On seed 555,
    38 of 1000 OFF paths have a day with r < -1/3 (min -43%). On such a day the 3x product goes below zero inside
    exec_engine, which returns a NaN CAGR for any rule exposed that day.
    - The designer counts those paths as -100% (design_lib.fix, final_eval.fix).
    - The tournament scorer should handle NaN the same way. A plain np.median over NaN gives NaN.
    - This is a property of the theory's null world, not a rule defect. The frozen rule had 0 NaN paths on the fresh
      seeds.
  - (S2) The OFF belief jump is X_HI - X_LO = 0.98, not 1. So the rational-consistency drift, which assumes a gap of
    dm, leaves a residual expected excess drift of about h*0.02*dm, below 0.01%/yr. This is negligible.
  - (S3) The prior 'narrow'/'wide' option of simulate() exists for robustness checks only. 'base' is the default.

## Changes made
None. No mechanical defect was found, so the rule and the simulator are as the designer froze them.
