"""RNG1 robustness for R1 (post-hoc checks, not selection): other dev pools (block 125/500, eras 86-99 / 00-14), delay 3, and real NDX yearly diff."""
import sys, json, numpy as np, pandas as pd
import rng; from rng import std, jp, ov, iv, rx, make
out = {}
def run(c, var, delay):
    B, bf, bp, fs = make(var)(c); return std.row(*std.engine(c, B, bf, bp, fs, delay=delay))
def ctx_pool(name):
    a, b, P, blk, seed = iv.POOLS[name]; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
    ii = ov.boot_idx(len(X), P=P, years=30, block=blk, seed=seed, lo=1); c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}
    c._xi = (R.index, rng.NDX); return c
jobs = [('dev250_path', std.contexts()['dev250_path'], 3), ('real_ndx_86_14', std.contexts()['real_ndx_86_14'], 3)]
for p in ('dev125', 'dev500', 'e8699', 'e0014'): jobs.append((p + '_path', ctx_pool(p), 2))
for nm, c, dl in jobs:
    (a, fa), (b, fb) = run(c, 'R1', dl), run(c, 'V1', dl); d = fa - fb
    out['%s_delay%d' % (nm, dl)] = dict(R1=a['cagr'], V1=b['cagr'], d_med=float(np.median(d)), pw=float(np.mean(d > 1e-5)), dd80_R1=a.get('dd80'), dd80_V1=b.get('dd80'))
    print(nm, dl, out['%s_delay%d' % (nm, dl)], flush=True)
    if hasattr(c, '_xi'): del c
# real NDX yearly: equity curves at delay 2
c = std.contexts()['real_ndx_86_14']
R, M = jp.calendar('1984-01-03', '2014-12-31'); dates = R.index[c.ii[0]][ov.WARM:]
eq = {}
for v in ('R1', 'V1'):
    B, bf, bp, fs = make(v)(c); f, E = std.engine(c, B, bf, bp, fs); eq[v] = pd.Series(E[0], index=dates[-E.shape[1]:])
    out['real_days_B_differs_%s' % v] = None
B1 = make('R1')(c)[0][0]; B0 = make('V1')(c)[0][0]
out['real_frac_days_C3_differs'] = float(np.mean(B1[ov.WARM:] != B0[ov.WARM:]))
yr = pd.DataFrame({v: eq[v].resample('YE').last().pct_change() for v in eq}).dropna()
yr['d'] = yr.R1 - yr.V1; out['real_yearly_diff'] = {str(k.year): round(float(x), 4) for k, x in yr['d'].items() if abs(x) > 1e-4}
print(out['real_frac_days_C3_differs'], out['real_yearly_diff'])
json.dump(out, open('../results/robust_R1.json', 'w'), indent=1)
