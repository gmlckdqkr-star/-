# XV1 candidate API (for implementers)

A candidate is a plain Python function in `research_xv1/cand/<family>.py`:

```python
import numpy as np
import xv1                      # only xv1.ref(v) and xv1.std.ident exist for a candidate (a stand-in module, not the evaluator)

def my_rule(v, **params):
    o = xv1.ref(v)              # v1 itself: dict(B=..., bfn=..., bp=..., fstep=...); B is a 1-D array of T base levels (0, 1 or 3)
    ...
    return o                    # dict(B, bfn, bp, fstep[, G, Wt, mode, inc, RB, up, dn])
```

## What the function may read (and nothing else)
All arrays have T rows: 300 warm-up rows, then the account days. Row t holds what is known at the close of day t.
- `v.c.r[0]` daily Nasdaq-100 return (row t = close t-1 to close t), `v.c.rf[0]` daily cash rate, `v.c.lvl[0]` index level
  (cumulative product of 1 + r), `v.c.vix[0]` VIX close (NaN before 1990), `v.c.rb[0]` daily 10-year bond return proxy.
- `v.c.F[name][0]` boolean macro flags of v1's chain: inv, shock, csj, shock10, shock6m, shock6m75, shock3m, inv2.
- `v.c.sma(n)[0]`, `v.c.vol(n)[0]` (annualised n-day volatility), `v.c.ewvol(hl)[0]`, `v.c.hi(n)[0]` (rolling n-day high).
- `v.m['y10']`, `v.m['y3m']`, `v.m['cs']` macro levels in percent (10-year yield, 3-month yield, Baa-Aaa spread, lagged one day).
- `v.x[name]` registered extra inputs, declared in the configuration's `names`:
  `'ret:KEY'` daily return of the adjusted close of a fund or ETF (NaN before it exists). Keys available: TQQQ QLD PSQ SH SSO
  UPRO SOXL SOXX SMH USD TECL ROM FAS TNA UWM ERX DRN TMF UBT TLT IEF SHY GLD UGL SPY QQQ IWM XLK XLF XLE XLV XLI XLP XLU XLY XLB
  IYR HYG LQD and the other keys of panel_f32; `'lvl:_VIX3M@ext'`, `'lvl:_VIX9D@ext'`, `'lvl:_TYX@ext'`, `'lvl:_FVX@ext'`
  closing levels; `'chips'` Ken French Chips industry daily return (1926 on); `'semis'` = chips until SOXX exists, SOXX after.
  `'kf:COL'` Ken French daily industry return, COL in BusEq Enrgy Money Hlth Utils NoDur Manuf Shops Telcm (only these nine
  of the 12 industries are in the project) or the size groups `'kf:Lo 20'`, `'kf:Lo 10'`, `'kf:Qnt 2'`;
  `'cal:month'` (1..12), `'cal:dom'` (day of month), `'cal:dow'` (Monday 0), `'cal:ymod4'` (calendar year modulo 4): periodic
  calendar fields only. No absolute date or year exists for a candidate.
- `v.ref_target` the level v1 wants after its brake, decided at the close of row t (a continuous number in 0..3; it comes
  into force two rows later, rounded to the engine's order grid); `v.ref_held` the level v1 actually holds on row t. Both come from v1 alone in a shadow account (the same
  kind of account the candidate is scored in; the evaluator takes care of that). Use these
  wherever a rule says "v1's level", "v1 is idle / in cash / at 1x". `xv1.ref(v)['B']` is v1's base signal before the brake.
- `v.feat` the 12 brake features of v1 (read-only), `v.T` the number of rows.
- Shared helpers in `cand/cbase.py` (import cbase as cm): `cm.lev(r1, rf, L)` modelled fund, `cm.fund(v, 'SOXL', r1, 3)` fund
  spliced with its model, `cm.level`, `cm.sma`, `cm.roll_max`, `cm.roll_min`, `cm.vol`, `cm.lag`, `cm.hyst`, `cm.trend_flag`,
  `cm.consec`, `cm.debounce`, `cm.since`, `cm.breadth(v)` (needs `cm.SECTOR_NAMES` in the configuration's names),
  `cm.semis_level(v)` (needs 'semis'), `cm.ndx_level(v)`. Use them instead of writing your own; all are causal.
Source gate (evaluator v6, an allow-list; a file that fails it cannot be registered): module-level `import numpy`,
`import xv1` and `import <helper>` (a file of the candidate's own folder whose name is not a standard-library module name)
only; no from-import, no import inside a function, no class; numpy only through the functions and constants in
`xv1._NP_OK`, one level deep (`np.X`, never `np.X.Y`; no `np.empty`: use `np.zeros` / `np.full`); built-ins only those in
`xv1._BI_OK` (no print, open, hash, id, type, exit, getattr ...); no name or attribute that begins with `_` except the
file's own module-level names, none that contains `__`, none of the attributes in `xv1._BAN_ATTR`; no assignment to any
attribute; no `global` / `nonlocal`; no integer literal above 999, no string literal (other than a docstring) with a
year 19xx / 20xx, no display of more than 64 elements (the same rules apply to parameter values). The code is executed
from the gated bytes, never through the import system, and every call runs a new copy of the module (no state survives
between calls). The object `v` holds write-protected copies; changing or replacing one of its inputs, or raising, voids
the configuration. Instruments: a model only on an unlevered series; a real fund only spliced with a model of its own
leverage (xv1._LEV).
Forbidden: dates, row numbers as calendar positions, files, caches, module-level data, random numbers,
anything from the future. No date literal in the source. Use only causal operations: no centred windows, no backward
fill, no shift to negative lags, no statistic over the whole array (quantile, mean, max, z-score with full-sample moments).
An expanding or rolling statistic that ends at row t is fine. No threshold on the absolute height of a price level
(index level, a cumulative product of returns): use ratios (level / its average, level / its past value). The evaluator
multiplies `v.c.lvl` by 2 and by 0.5 and voids a candidate whose outputs change. Thresholds on yields, spreads, VIX are fine. Rows where an input is NaN: hold the v1 level / weight 0.

## What it returns
- `B` (T,) base level for the 3x Nasdaq fund, values in [0, 3] (v1 uses 0, 1, 3). The brake `bfn` with parameters `bp` runs
  on top inside the engine; keep `bfn`, `bp`, `fstep` exactly as `xv1.ref(v)` returns them (v1's brake), or use
  `bfn=xv1.std.ident, bp=np.zeros(1)` with an order step of your own for no brake. Any other brake or parameter is void.
- Extra instruments (optional): `G` (T, J) daily returns net of fund costs (NaN where the instrument does not exist),
  `Wt` (T, J) target weights of total account equity decided at the close of row t (each in 0..1, at most 1 per row in
  total, never on a row where the instrument is missing nor on the four rows before such a row). Every held instrument must
  be a registered return input, a modelled fund (L = 3, 2, 1, -1) on the index, the bond return or a registered 1x input (or
  a splice of two), or a registered fund return spliced with such a model: the evaluator rebuilds it and voids anything else.
  Before a 3x fund exists use the modelled series `3 * r1x - 2 * rf - 0.0245 / 252` on its 1x series (2x: `2 * r1x - rf - 0.0170 / 252`, the same fee 0.0095 plus 0.0075 per borrowed unit; `cbase.lev` and `cbase.fund` do this).
- `mode` 0: v1 has priority, extras use only cash v1 leaves idle (cut pro rata when v1 needs it). With `inc` 0 they are
  re-set to target inside the idle cash at every change of v1's level; with `inc` 1 a tranche is never re-set: it is cut
  pro rata when idle cash is short and not bought back, and a tranche that does not fit lapses. `mode` 1: extras have
  priority, the 3x Nasdaq fund gets level/3 of the rest; a change of v1's level leaves the extras untouched.
- `inc` 0: `Wt` means "hold this share of the account"; between re-sets the position drifts. A re-set happens when `Wt`
  changes, when `RB[t, j] = 1` (rebalance flag decided at close t), or by bands: actual weight above `Wt * (1 + up[j])`
  (profit skim) or below `Wt * (1 - dn[j])` (refill). Leave `up` / `dn` out (or use `xeng.OFF`) to switch a side off.
  `inc` 1: tranche rule (a higher `Wt` adds fresh money; a lower one sells pro rata; RB and bands ignored).
- Everything is traded by the engine two closes after the decision (delay 2), 0.3% cost per side, 22% yearly tax. The
  candidate cannot change engine terms. Do not apply the delay yourself.

## What an implementer may run (and nothing else)
From /home/user, never from under /mnt/project-files:
`NUMBA_CACHE_DIR=/home/claude/nbcache_xv1 ~/.cache/lab/ms1-venv/bin/python -B script.py`
- First line after the imports: `import t_world; t_world.old()` (declares the <= 2014 test world; nothing after 2014 can be built).
- The one call: `pre = xv1._prepare(make, names, xv1.OLD_END)` (view, validated output, instrument check); `xv1.gate(path)` must be empty.
- The causality test: `xv1.prefix_test(None, names, end=xv1.OLD_END, n_rand=25, pre=pre)` and `xv1.scale_test(make, names, pre=pre)` must return PASS.
- Activity counts: on how many rows B differs from v1's B, on how many rows a weight is non-zero, how many events.
- Never compute, print or look at a return, growth figure, equity curve, win rate or any other performance number of a
  candidate, on any period. Never call `xv1.run_batch`, `_design_account`, `_run`, `_run_eng`, `reference_table` or any scoring
  function. Never use an end date after 2014-12-31. Tuning a parameter to data is forbidden: parameters come from the
  written rule only.
