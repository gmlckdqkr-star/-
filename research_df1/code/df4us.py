"""DF4 addendum (post-hoc reading, labelled): pre-registered strict result = 0 configs pass all gates (R3 foreign fails).
Here: the configs passing every US gate (R1 R2 V1 V2 E1 E2 E3) get the pre-registered E4/E5 stress; picks for the horizon table.
Writes results/df4_us.json. <=2014 data only."""
import os, sys, json, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, df4cfg
RES = '/mnt/project-files/research/df1/results/'; EX = 1.3988294390226633e-4; MG = 0.05
D = json.load(open(RES + 'df4.json')); C = D['configs']; QP = D['refs']['dev250_path']['hold1x_QQQ']
US = [i for i in C if all(C[i]['g'][k] for k in ('R1', 'R2', 'V1', 'V2', 'E1', 'E2', 'E3'))]
mp = DC.market('dev250_path'); mp0 = dict(mp); mp0['rb'] = mp['rb'] - EX; T = mp['r'].shape[1]
ub = lambda c: c.get('fam') == 'static' or c.get('roff') in ('RB', 'RBT')
def pst(cfg, m, **kw):
    cg, md = dfe.stats(df4cfg.run_any(cfg, m, **kw), T)
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
OUT = {}
for i in US:
    cfg = df4cfg.cfg_of(i); m = mp0 if ub(cfg) else mp
    b = pst(cfg, m); assert abs(b['cagr'] - C[i]['P0']['cagr']) < 1e-9
    r = dict(c2=pst(cfg, m, cost=0.006), d4=pst(cfg, m, delay=4), c3=pst(cfg, m, cost=0.009), d5=pst(cfg, m, delay=5))
    r['E4'] = r['c2']['cagr'] > QP['cagr'] and r['c2']['mdd_p10'] > QP['mdd_p10'] + MG
    r['E5'] = r['d4']['cagr'] > QP['cagr'] and r['d4']['mdd_p10'] > QP['mdd_p10'] + MG
    OUT[i] = r; print(i, {k: (round(v['cagr'] * 100, 2), round(v['mdd_p10'] * 100, 1)) if isinstance(v, dict) else v for k, v in r.items()}, flush=True)
ok = [i for i in US if OUT[i]['E4'] and OUT[i]['E5']]
ans = max(ok, key=lambda i: C[i]['P0']['cagr']) if ok else None
top_us = max(US, key=lambda i: C[i]['P0']['cagr'])             # highest US-gate passer, kept as a reference row (fails E4)
sel = dict(answer=ans, ref_RB=top_us if top_us != ans else None)
print('US pass incl E4/E5:', ok, 'sel', sel)
json.dump(dict(note='post-hoc US reading: strict pre-registered result is 0 (R3 foreign gate); answer = best US-gate passer that also passes E4/E5; ref_RB = best US-gate passer', us_pass=US, stress=OUT, sel=sel), open(RES + 'df4_us.json', 'w'), indent=1)
