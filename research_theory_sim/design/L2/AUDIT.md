# AUDIT — lane TS1 / L2 ("Dealer Ledger"), blind auditor

Audit started 2026-11-04T08:08Z, written 2026-11-04T08:12Z (times from `date -u +%Y-%m-%dT%H:%MZ`).

**Verdict: PASS.** I changed no file in the lane except this one (AUDIT.md).

## Auditor's own blindness
I read only `research/theory_sim/DESIGN_BRIEF.md`, `research/theory_sim/common/exec_engine.py` (plus an `ls` of
`common/`) and the files in `research/theory_sim/design/L2/`. I opened no other lane, no test/ or holdout/ folder, no
TEST_PROTOCOL.md, no memory, no git checkout, and used no network or MCP data tool. My audit scripts are in my session
scratchpad (`.../scratchpad/l2audit/{audit,causal,repro,simcheck}.py`). They import only sim.py, rule.py and
exec_engine.py, and I ran them with `python -B`, so nothing was written to the lane folder.

## 1. Blindness of the designer
- READ_LOG.md lists the brief, the engine, one `ls` of design/ (empty at the time) and the designer's own files. It also
  records the context that was present (tool and skill names) and says it was not used. I found nothing that contradicts it.
- I grepped every .py file for `open(`, np.load, loadtxt, genfromtxt, read_csv, `read_`, urllib, requests, http, socket,
  subprocess, os.system and /mnt/project-files, /tmp and /home paths:
  - `open(` appears only as writes of the designer's own outputs: harness.py appends to variants_log.jsonl,
    final_eval.py writes synth_results.json, and step*.py write *_rows.json.
  - The only paths are the lane folder itself and `sys.path.insert(... /theory_sim/common)`.
  - `multiprocessing` (fork pool, gridrun.py) is used only to parallelise the grid.
  - There is no network or process access. rule.py imports only `numpy` and `math` (checked with an AST walk).
- Hard-coded history: there are no calendar years, named indices, crashes or episodes in the code or in THEORY.md
  (grep for years and index or episode names found nothing). The constants that look like real-world numbers are these:
  - the prior ranges (wide, each with a stated reason; sigma0 12-26% and dividend yield 1-5% are listed under
    "Background knowledge used");
  - the 2.45%/yr product cost and the 2% deposit spread, which come from the brief;
  - VAR_FLOOR 0.0004, a numerical guard;
  - the 5-year rate norm, which comes from THEORY.md's payout norm.
  None of them looks like a fitted real statistic.
- PRIORS_FROZEN: THEORY.md contains `PRIORS_FROZEN 2026-11-04T07:24Z`. Timing:
  - THEORY.md mtime is 07:25:25, the last write about one minute after the stamp.
  - The design log puts the first simulation at 07:26, and the first variants_log entry is 07:28:44.
  - The last variant is at 07:44:29, rule.py mtime is 07:45:05 and synth_results ts is 07:49Z.
  So the freeze comes before all rule-design work. The PRIOR dict in sim.py matches the THEORY.md §6 table exactly
  (all 20 ranges and Bernoulli(0.4)). The design log reports two later edits to sim.py (diagnostic outputs and the width
  option); they do not change the width=1 draws.
- Side note: `common/__pycache__` has an mtime of 07:25:07. The L2 folder has no __pycache__, so the designer apparently
  ran without writing bytecode. I could not attribute this cache to L2 and did not investigate other lanes (forbidden);
  it is not evidence against L2.
- Selection seeds in variants_log.jsonl are only {1, 2, 3}. There are 273 entries, which matches the reported N.
  Fresh seeds 10000-10003 appear only in final_eval.py.
- rule.py sha256 = `498c11804256c26cc9e85d76eb1b068b940369781da0f62671afcd4c39d8975d`, which matches design_log.md.

## 2. Interface (rule.py)
| check | result |
|---|---|
| imports | `numpy`, `math` only |
| INPUTS / PARAMS | `('close','rf')` / `{'hv_days':140.0,'ledger_hl_years':1.5,'a0':0.03,'a1':0.2,'a3':1.0}` (5 tunables, <= 6) |
| signature | `target_levels(close, rf, y10=None, params=PARAMS)`; a y10 passed in is ignored (output bit-identical) |
| output | (P,T) float64, values in [0,3]; NaN only in columns < 20 (warm-up) |
| NaN / bad inputs | 1% random NaN in close and rf, an all-NaN row, a 400-day NaN start, close = 0, close < 0 and close = inf: runs with `np.errstate(all='raise')` without error. Output stays in [0,3] or NaN with no inf, and the engine runs on it. 1-D input also works. |
| scale invariance | close x1000 and x1e-3: max abs diff 2.3e-13 (floating-point rounding of log(c*k)), so not bit-identical. Through the engine, the CAGRs are bit-identical on 200 audit paths and on all 2000 headline paths (ON and OFF, with close x1000). Accepted as invariant up to floating-point rounding; no fix possible or needed. |
| speed | P=500, T=10000: 1.02 s |
| deterministic | yes (repeat calls bit-identical) |

## 3. Causality (exact)
- Setup: 50 lane-simulator paths (seed 4242, mechanism ON, T = 7860) at 100 cut points: 28 with t < 300 (including
  t = 0, 1, 19, 20, 21, 299), 21 with t >= T-200 (including T-2 and T-1), and the rest in the middle.
- Every column > t of close, rf and y10 was replaced by a continuation of one of three kinds, in rotation:
  1. a different simulated world (seed 9191) continuing from close[t];
  2. a wild random continuation;
  3. garbage values (NaN, 0, negative, inf, 1e300 in close; NaN, inf and ±1 in rf).
- Result: output columns <= t were **bit-identical in 100/100 cases** (0 violations, max diff 0.0).

## 4. Reproduction (fresh seeds as in design_log.md / final_eval.py: 10000 and 10001, P = 1000 each, T = 7860, delay 2, cost 0.3%, close normalised x100)
| quantity | designer | auditor |
|---|---|---|
| rule cagr_med ON | 0.04444 | **0.04444** |
| rule cagr_med OFF | 0.02063 | 0.02063 |
| hold 1x ON / OFF | 0.04981 / 0.04043 | 0.04981 / 0.04043 |
| delay 3 / delay 5 / cost 0.6% (ON) | 0.04446 / 0.04554 / 0.04248 | 0.04446 / 0.04554 / 0.04248 |

The match is exact, well within 0.2 pp. The designer counts a NaN engine CAGR as -100%. On these seeds the rule had
0 NaN CAGRs, so the raw median and the convention median are the same.

## 5. Simulator sanity
- Parameters are drawn per path (seed 555, P=400). Every prior parameter lies within its THEORY.md range and spreads
  over at least 80% of it. Monthly-rate share is 0.425, against a theory value of 0.4. A different seed gives
  different worlds.
- ON and OFF share the same parameter draw and a bit-identical rf path. On daily-rate paths, y10(ON) - y10(OFF) equals
  `tp_x*(-x_{t-1})` to 1e-9, so OFF only loses the tp_x term.
- The mechanism is really off. The OFF log excess return is exactly `m_p/252 - 0.5*so^2/252 + so*eps/sqrt(252)` with
  `so = c_p*s_f`: the reconstructed shocks have mean 0.0006 and sd 1.007. The random draws do not depend on the state,
  so no ledger, carry, duration or rate term enters OFF. Diagnostics (ON vs OFF):
  - 1y->1y excess autocorrelation: -0.165 vs -0.036. The OFF value is about the small-sample bias -1/n for n = 30.
  - corr(true ledger, next-year excess): -0.287 vs -0.059. The OFF value is small-sample (Stambaugh) bias with an
    overlapping, persistent regressor.
  - corr(true ledger, next-63-day vol): -0.377 vs 0.002.
  - Median annual vol: 0.212 vs 0.212, matched by construction.
- NaN/inf: none in r, rf or y10 on the 4 headline worlds (2000 paths each for ON and OFF). Also r[:,0] = 0 and the
  shapes are (P,T).
- Observations, not defects (they follow from the frozen priors and do not affect the rule's validity):
  - About 1% of paths contain a day with r < -1/3, which takes the engine's 3x product negative. The designer documents
    this and uses the ruin convention.
  - A few extreme up days occur, up to about +280% in one OFF path (t-tails with df near 3, times the c_p scale).
  - y10 can reach about -3.5%. The rule does not read y10.

## Changes made
None. No mechanical defect was found.
