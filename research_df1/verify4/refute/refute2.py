"""verify4 / refute part 2: start/end-date sensitivity of the thin S&P edges (R2), horizon rows copied from df3_horizons,
R2 detail of the neighbours. <=2014 data only."""
import os, sys, json, time
os.environ['NUMBA_CACHE_DIR'] = '/home/claude/nbcache_verify4'
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, df4cfg
W = dfe.WARM; RES = '/mnt/project-files/research/df1/results/'
OUTP = sys.argv[1] if len(sys.argv) > 1 else '/tmp/v4_refute/refute2_numbers.json'
D4 = json.load(open(RES + 'df4.json')); C = D4['configs']
RC = df4cfg.cfg_of('v1|s0.3|L1.5|K0|RC'); OUT = dict(window={}, h3_copy={}, nb_r2={})
def cut(m, s, e):
    k = dict(m)
    for a in ('r', 'rf', 'rb', 'cpn', 'idxup', 'bondup', 'st_v1', 'st_al', 'vol20'): k[a] = m[a][:, s:m[a].shape[1] - e]
    return k
def one(m, **kw):
    T = m['r'].shape[1]
    a = dfe.stats(df4cfg.run_any(RC, m, **kw), T); b = dfe.stats(dfe.run(m, np.full(m['r'].shape, 1.0), **kw)[0], T)
    return float(a[0][0]), float(a[1][0]), float(b[0][0]), float(b[1][0])
# start shifted 0..2y (signals are causal, checked in refute.py, so a later start = same rule started later); end cut 0..2y
for bn in ('real_spx_55_85', 'real_spx_70_85', 'real_ndx_86_14', 'real_spx_29_54'):
    m = DC.market(bn); res = {}
    for kw_name, kw in (('std', {}), ('cost2x', dict(cost=0.006)), ('delay4', dict(delay=4)), ('D0.025', dict(D=0.025))):
        rows = []
        for s in range(0, 505, 21):
            rows.append(('s', s) + one(cut(m, s, 0), **kw))
        for e in range(21, 505, 21):
            rows.append(('e', e) + one(cut(m, 0, e), **kw))
        dc = np.array([r[2] - r[4] for r in rows]); dm = np.array([r[3] - r[5] for r in rows])
        res[kw_name] = dict(n=len(rows), share_cagr_win=float(np.mean(dc > 0)), dcagr_min=float(dc.min()), dcagr_med=float(np.median(dc)),
                            dcagr_max=float(dc.max()), share_mdd_win=float(np.mean(dm > 0)), dmdd_min=float(dm.min()), dmdd_med=float(np.median(dm)))
    OUT['window'][bn] = res
    print(bn, json.dumps({k: {a: round(b, 4) for a, b in v.items()} for k, v in res.items()}), flush=True)
H3 = json.load(open(RES + 'df3_horizons.json'))['res']; H4 = json.load(open(RES + 'df4_horizons.json'))['res']
for k in H4:
    for nm in ('QQQ', 'v1', 'v2', 'v2_bx0'):
        OUT['h3_copy']['%s_%s' % (k, nm)] = all(abs(H4[k][nm][a] - H3[k][nm][a]) < 1e-12 for a in H4[k][nm])
print('h3 copy all equal:', all(OUT['h3_copy'].values()))
for nid in ('v1|s0.3|L1.5|K0|RC', 'v1|s0.2|L1.5|K0|RC', 'v1|s0.3|L1.0|K0|RC', 'v1|s0.3|L2.0|K0|RC'):
    OUT['nb_r2'][nid] = dict(spx55=C[nid]['real_spx_55_85_bx0'], P0=C[nid]['P0'])
    print(nid, OUT['nb_r2'][nid])
json.dump(OUT, open(OUTP, 'w'), indent=1)
