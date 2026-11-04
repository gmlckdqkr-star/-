# AUDIT — lane TS1 / L1 (Margin-Ratchet Leverage Cycle, MRLC)

Blind auditor. Started 2026-11-04T08:14Z, written 2026-11-04T08:18Z.
Read: DESIGN_BRIEF.md, common/exec_engine.py, and files in design/L1/ only (READ_LOG.md, THEORY.md, design_log.md,
sim.py, rule.py, synth_results.json, work/*). I opened no other folder, no TEST_PROTOCOL.md, test/ or holdout/, no memory
file and no git checkout. I used no network or data tool. My audit scripts live in my scratchpad (outside
/mnt/project-files): audit_l1.py, repro_l1.py, simsan_l1.py. They read nothing except the lane's sim.py / rule.py and the engine.

**Verdict: PASS. No file in the lane was changed.**

## 1. Blindness
- READ_LOG.md lists only DESIGN_BRIEF.md, common/exec_engine.py and the lane's own folder. It declares the context that was
  present: tool names, the s085 skill name and the forbidden-list folder names. Only names were seen, and none was used.
- Grep of every .py (sim.py, rule.py, work/*.py) for `urllib|requests|http|socket|subprocess|os.system|popen|np.load|loadtxt|
  genfromtxt|read_csv|pandas|pickle|glob|listdir|walk(` found **no hits**. `open(` appears only in work/harness.py (variants.csv),
  work/final_eval.py, work/diag_final.py and work/make_results.py, and every one of them reads or writes a JSON/CSV inside
  design/L1/. The absolute paths in the code are only design/L1[/work] and common/. Nothing refers to /tmp/claude or /home/user.
  Imports are numpy, sys, os, json, time, itertools, the lane's own modules and exec_engine.
- Hard-coded real-history facts: none. Grep for years and for named indices or episodes (S&P, Dow, Nasdaq, KOSPI, Nikkei,
  1987, 2008, 2020, Lehman, COVID, depression, ...) found no hits. The only dates are the 2026-11-04 work timestamps.
  The rule constants (m0 0.08, A 1.25, ns 42, B 0.5, nl 252, sv 120) are grid and coordinate-search outcomes on synthetic
  seeds 11 and 12, and work/variants.csv records them (N = 131, matching the report). The fixed constants (half Kelly, 3% vol
  floor) are generic choices. The background knowledge used (equity vol 10-40%, rates 0-10%) is declared in THEORY.md.
- PRIORS_FROZEN 2026-11-04T07:23Z is present. Amendment A1 (07:28Z) adds structural guards only (WCAP and a close-out
  above leverage 15). The PRIOR dict in sim.py matches the THEORY.md table exactly: all 27 ranges plus the monthly flag 0.5.
  The file mtimes are consistent with the stated order:
  sim diagnostics diag_sim*.py 07:26 -> THEORY.md (A1) 07:28:24 -> sim.py 07:29:39 -> pre-design analyses 07:28-07:32 (seeds 1-3)
  -> harness.py 07:33 -> first rule grid g0.py 07:34 -> ... -> g8.py 07:56 -> rule.py 07:59:56 -> final_eval.py 08:00 (seeds 10000/10001).
  sim.py was last modified before any rule evaluation. Selection used seeds 11 and 12 only. Seeds >= 10000 appear only in
  final_eval.py and diag_final.py (post-freeze, no selection).
- Minor: the internal burn-in BURN = 1260 days in sim.py is not listed among the structural constants in THEORY.md. It is
  numerical only and does not affect blindness.

## 2. Interface (rule.py)
| check | result |
|---|---|
| imports | `numpy`, `math` only (AST check); no open/eval/exec/os/sys |
| INPUTS / PARAMS | ('close', 'rf'); 6 params, a literal dict |
| signature | target_levels(close, rf, y10=None, params=PARAMS) |
| output | (P, T) float64, min 0.0, max 3.0, no inf; NaN only before the first return |
| y10 passed | ignored (output bit-identical) |
| deterministic | yes |
| NaN / bad inputs | random 1% NaN in close and rf, leading NaN blocks, an all-NaN path, close = 0, -1 and +inf: no crash; values in [0, 3]; all-NaN path -> all NaN; bad closes carried forward |
| 1-D input | works |
| scale invariance | x1000, x1/37, x1024: max abs difference 5e-13 (floating-point rounding of log(k*c)), same NaN mask, engine CAGR per path **bit-identical**. Mathematically exact (only differences of log prices are used). PASS: no float implementation can be bit-identical for arbitrary k |
| speed P=500, T=10000 | 0.94 s |

## 3. Causality (exact)
The test used 50 lane-simulator paths (seed 4242, T = 7860) and 100 cut points: 25 with t < 300, 50 in the middle, and 25
in the last 300 columns including t = T-1. Every column > t of close, rf and y10 was replaced in rotation by one of three
continuations: (a) a continuation from a different simulator seed; (b) a wild random walk with sd 0.08/day and random rates;
(c) a pathological future with 10% NaN, 5% zeros, 5% values of 1e300 and NaN or 1.0 rates. y10 was set to N(0, 100) noise.
**Result: 0 of 100 cuts differ; the output columns <= t are bit-identical (equal_nan).** PASS.

## 4. Reproduction (fresh seeds 10000 and 10001, 2000 paths each, T = 7860, exec_engine defaults)
| row | designer | auditor |
|---|---|---|
| ON rule cagr_med | 0.1032 | **0.10317** |
| ON rule p10 / P(MDD<=-80%) | 0.0218 / 0.0428 | 0.02178 / 0.0428 |
| ON hold1x / const0.5 | 0.0387 / 0.0202 | 0.03867 / 0.02018 |
| ON delay3 / delay5 / cost 0.6% | 0.0982 / 0.0898 / 0.0969 | 0.09819 / 0.08985 / 0.09692 |
| OFF rule / hold1x / const0.5 | 0.0247 / 0.0393 / 0.0223 | 0.02465 / 0.03927 / 0.02233 |
All rows match exactly (difference 0.00 pp). PASS.

## 5. Simulator sanity (seed 10002, 1000 paths)
- Parameters are drawn per path. All 27 parameters fall inside their frozen ranges with distinct values per path. The share
  of monthly-step paths is 0.516.
- mechanism=False uses the same per-path parameters and the same rf path (identical arrays). Returns are i.i.d. Student-t:
  median lag-1 autocorrelation -0.0002, lag-1 autocorrelation of |r| 0.0005, variance ratios 5d / 21d / 63d / 252d
  = 1.00 / 1.00 / 0.99 / 0.94. The 0.94 is the small-sample bias of about 30 yearly observations.
  The ON world gives 1.25 / 1.71 / 1.83 / 1.24 with ac1 0.089.
  OFF keeps each path's own vol (corr of per-path sd with ON 0.998). The mechanism is really disabled.
- An extra check overrode Phi to about 0 and b_X to 0 with the mechanism ON. VR63 drops to 0.98, so the 1-3 month
  momentum comes from the speculator and extrapolator classes, as claimed.
- r, rf: all finite in ON and OFF on seeds 10000-10002. r[:, 0] = 0. rf lies in [0, 0.20]/252, where 0.20 is the
  documented cap. y10 = None, which is consistent with INPUTS.

## Observations (not defects, for the tournament and the real test)
- The rule's ON edge rests on strong 1-3 month momentum in the median synthetic world (VR63 of about 1.8). This strength
  comes from the priors on speculator footprint and adjustment speed. The theory's named "ratchet" state is not used by
  the rule, as the designer says openly.
- Mechanism OFF: the rule beats the best constant (0.5) by +0.23 pp but trails hold 1x by 1.46 pp. Its left tail is much
  fatter: P(MDD<=-80%) is 18.8% against 4.5% for hold 1x.
- The selection criterion was fixed at 07:50Z, after N = 98 variants had already been evaluated. This is disclosed in
  design_log.md.
- The rule uses the rf level as a hurdle, so in high-rate regimes it holds little or nothing.

## Changes made
None.
