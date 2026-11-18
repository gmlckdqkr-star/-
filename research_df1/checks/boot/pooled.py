"""Check 'boot' part 2: pooled block-250 basis. Re-runs every DF1+DF2 config on base seed 7 + seeds 11/23/37/51 (block 250, P=500 each),
keeps per-path after-tax CAGR and MDD, and redoes the union tier selection (incl. DF2 gates) on the 2,500 pooled paths
(median CAGR, 10th-percentile MDD over all 2,500 paths). Same method as the headline, just 5x more paths.  NON-ACTUAL bootstrap paths,
source 1986-01-02..2014-12-31 only."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boot_pools as BP, dfe, run_df2 as R2

USE = ('base_s7_b250', 's11_b250', 's23_b250', 's37_b250', 's51_b250')
IDS = list(BP.CFG)

def paths(nm):
    fn = BP.CACHE + 'paths_%s.npz' % nm
    if os.path.exists(fn):
        z = np.load(fn); return z['cg'], z['md']
    m = BP.build(*BP.POOLS[nm]); T = m['r'].shape[1]; cg = np.zeros((len(IDS), 500)); md = np.zeros((len(IDS), 500))
    for k, i in enumerate(IDS): cg[k], md[k] = dfe.stats(R2.run_cfg(BP.CFG[i], m), T)
    np.savez(fn, cg=cg, md=md); print('paths', nm, 'done', flush=True); return cg, md

CG, MD = zip(*[paths(n) for n in USE]); CG = np.concatenate(CG, axis=1); MD = np.concatenate(MD, axis=1)
tab = {i: dict(cagr=float(np.median(CG[k])), mdd_p10=float(np.percentile(MD[k], 10))) for k, i in enumerate(IDS)}

def gate_pooled(i):
    a, b = [], []
    for nm in USE:
        m = BP.build(*BP.POOLS[nm]); T = m['r'].shape[1]; W = dfe.WARM
        ex = float(np.mean(m['rb'][:, W:] - m['rf'][:, W:])); m0 = dict(m); m0['rb'] = m['rb'] - ex
        a.append(dfe.stats(R2.run_cfg(BP.CFG[i], m0), T)[0]); b.append(dfe.stats(R2.run_cfg(BP.CFG[i], m, cost=0.006), T)[0])
    return float(np.median(np.concatenate(a))), float(np.median(np.concatenate(b)))

res = dict(pools=USE, n_paths=int(CG.shape[1]), tiers={}, picks={})
for name, bud in BP.TIERS:
    ins = [i for i in IDS if BP.wd(i, tab) >= bud]; t = dict(n_in=len(ins))
    if ins:
        ub = BP.best_of(ins, tab); d1 = BP.best_of([i for i in ins if BP.CFG[i]['fam'] != 'df2'], tab); adopt = ub
        t.update(union_best=ub, union_best_cagr=tab[ub]['cagr'], df1_best=d1, df1_best_cagr=tab[d1]['cagr'])
        if BP.CFG[ub]['fam'] == 'df2' and d1:
            gb, g1 = gate_pooled(ub), gate_pooled(d1)
            t['gate'] = dict(df2_bondx0=gb[0], df1_bondx0=g1[0], df2_cost2x=gb[1], df1_cost2x=g1[1])
            if not (gb[0] > g1[0] and gb[1] > g1[1]): adopt = d1
        t.update(adopted=adopt, adopted_cagr=tab[adopt]['cagr'], adopted_wd=BP.wd(adopt, tab))
        t['top5'] = [(i, round(tab[i]['cagr'], 5), round(BP.wd(i, tab), 5)) for i in sorted(ins, key=lambda i: -tab[i]['cagr'])[:5]]
    res['tiers'][name] = t
for tn, p in BP.PICKS.items():
    bud = dict(BP.TIERS)[tn]; ins = [i for i in IDS if BP.wd(i, tab) >= bud]; pl = ins if p in ins else ins + [p]
    res['picks'][tn] = dict(id=p, path=tab[p]['cagr'], mdd_p10=tab[p]['mdd_p10'], wd=BP.wd(p, tab), in_tier=bool(BP.wd(p, tab) >= bud),
                            rank=sorted(pl, key=lambda i: -tab[i]['cagr']).index(p) + 1, n_in=len(ins),
                            still_adopted=res['tiers'][tn].get('adopted') == p)
json.dump(res, open(BP.OUT + 'pooled_b250.json', 'w'), indent=1)
for tn, t in res['tiers'].items(): print(tn, json.dumps(t))
for tn, p in res['picks'].items(): print('pick', tn, json.dumps(p))
