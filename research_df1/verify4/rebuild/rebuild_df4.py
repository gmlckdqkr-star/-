"""verify4/rebuild: independent DF4 gate screen (written from PRECOMMIT_DF4.md only; df4*.py not read).
Runs all 1,367 configs (df3.json['configs']) through dfe via df4cfg.run_any, bond-neutral per the task conventions.
<=2014 data only (dfctx asserts). Path stats: medians / percentiles only."""
import os, sys, time, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, df4cfg as F
RES = '/mnt/project-files/research/df1/results/'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/v4_rebuild/rebuild_raw.json'
W = dfe.WARM; EX_FIX = 1.3988294390226633e-4
BASES = ['dev250_path', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_29_54', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP']
FOR = ['UK', 'CA', 'AU', 'DE', 'FR', 'JP']
ids = list(json.load(open(RES + 'df3.json'))['configs'].keys()); assert len(ids) == 1367

def neutral(name, m):
    if name in ('dev250_path', 'real_ndx_86_14'): ex = EX_FIX
    else:
        ex = float(np.mean(m['rb'][:, W:] - m['rf'][:, W:])); ex = ex if ex > 0 else 0.0
    m0 = dict(m); m0['rb'] = m['rb'] - ex
    return m0, ex

def summ(o, T):
    cg, md = dfe.stats(o, T)
    if cg.shape[0] > 1:
        return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
    return dict(cagr=float(cg[0]), mdd=float(md[0]))

t0 = time.time(); R = dict(ex={}, hold={}, cfg={i: {} for i in ids})
for b in BASES:
    m = DC.market(b); T = m['r'].shape[1]; m0, ex = neutral(b, m); R['ex'][b] = ex
    R['hold'][b] = summ(dfe.run(m, np.full(m['r'].shape, 1.0))[0], T)
    for i in ids:
        c = F.cfg_of(i)
        R['cfg'][i][b + '|bx0'] = summ(F.run_any(c, m0), T)
        R['cfg'][i][b + '|std'] = summ(F.run_any(c, m), T)
        if b == 'dev250_path':
            R['cfg'][i]['E4|bx0'] = summ(F.run_any(c, m0, cost=0.006), T)
            R['cfg'][i]['E5|bx0'] = summ(F.run_any(c, m0, delay=4), T)
            R['cfg'][i]['cost3x|bx0'] = summ(F.run_any(c, m0, cost=0.009), T)
    print('%-15s ex=%.6e  hold=%s  %.0fs' % (b, ex, R['hold'][b], time.time() - t0), flush=True)
    if b == 'dev250_path': DC._M.pop(b, None)
json.dump(R, open(OUT, 'w'))
print('saved', OUT, '%.0fs' % (time.time() - t0))
