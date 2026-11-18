"""stress A: full world sensitivities (cost x2, delay 3, bond-neutral + cost x2) and single real paths for 6 picks. <=2014 only."""
import os, sys, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
from dfctx import std
EX = 1.3988294390226633e-4
OUTD = '/mnt/project-files/research/df1/verify3/stress/'
t0 = time.time()
def log(*a): print('[%5.0fs]' % (time.time() - t0), *a, flush=True)

ALLC = {c['id']: c for c in RG.configs() + R2.configs()}
PICKS = dict(T25='v1|s0.1|L1.0|K1|RB', T40='v1|s0.3|L1.0|K2|RB', W40='DF2|M0|b3|v1|s0.3|L1.0|K2|RB',
             P50='DF3|N3|M2|v1|s0.2|L1.0|K0|RB', S50='static|QQQ50|bond', S70='static|QQQ70|bond')
CFG = {}
for nm, cid in PICKS.items():
    CFG[nm] = ALLC[cid] if cid in ALLC else dict(id=cid, fam='df3', M='M2', k='v1', sig=0.2, Lmax=1.0, knee='K0', roff='RB')

def run3(cfg, m, **extra):          # copied from df3.py
    L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']]); kw.update(vmode=0 if cfg['M'] == 'M0' else 2); kw.update(extra)
    o, _ = dfe.run(m, L, roff=RG.ROFF[cfg['roff']], **kw); return o
def run_any(cfg, m, **extra):
    f = cfg.get('fam')
    if f == 'df3': return run3(cfg, m, **extra)
    if f == 'df2': return R2.run_cfg(cfg, m, **extra)
    return RG.run_cfg(cfg, m, **extra)
def sm(o, m):
    Tm = m['r'].shape[1]; cg, md = dfe.stats(o, Tm)
    if cg.shape[0] == 1: return dict(cagr=float(cg[0]), mdd=float(md[0]))
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))

D3 = json.load(open('/mnt/project-files/research/df1/results/df3.json'))['configs']
RES = dict(picks=PICKS, full={}, single={})
mp = DC.market('dev250_path'); assert mp['X_index'].max() <= pd.Timestamp('2014-12-31')
mp0 = dict(mp); mp0['rb'] = mp['rb'] - EX
for nm, cfg in CFG.items():
    r = dict(base=sm(run_any(cfg, mp), mp), cost2x=sm(run_any(cfg, mp, cost=0.006), mp), delay3=sm(run_any(cfg, mp, delay=3), mp),
             bx0_cost2x=sm(run_any(cfg, mp0, cost=0.006), mp0))
    assert abs(r['base']['cagr'] - D3[cfg['id']]['P']['cagr']) < 1e-9, (nm, r['base']['cagr'], D3[cfg['id']]['P']['cagr'])
    RES['full'][nm] = r; log(nm, {k: (round(v['cagr'], 4), round(v['mdd_p10'], 4)) for k, v in r.items()})
DC._M.pop('dev250_path', None); del mp, mp0

G = {}
G.update(json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs'])
G.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
for bn in ('real_ndx_86_14',) + DC.VAL:
    m = DC.market(bn); assert m['X_index'].max() <= pd.Timestamp('2014-12-31')
    RES['single'][bn] = {}
    for nm, cfg in CFG.items():
        s = sm(run_any(cfg, m), m); RES['single'][bn][nm] = s
        if cfg['id'] in G: s['stored_diff'] = float(s['cagr'] - G[cfg['id']][bn]['cagr'])
    log(bn, {k: (round(v['cagr'], 4), round(v['mdd'], 4)) for k, v in RES['single'][bn].items()})
    DC._M.pop(bn, None)
json.dump(RES, open(OUTD + 'stress_a.json', 'w'), indent=1); log('saved')
