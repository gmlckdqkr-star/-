"""Re-selection with the defense metric measured in KRW (FRED DEXKOUS, <=2014): all 1,123 configs at base engine settings.
WD_krwN  = min(path USD MDD p10, real NDX 86-14 KRW MDD, SPX 29-54 USD MDD)   (only the real-NDX leg converted; ACTUAL FX)
WD_krwNP = min(path KRW MDD p10 (FX bootstrapped with the same blocks, NON-ACTUAL), real NDX KRW MDD, SPX 29-54 USD MDD)
Selection score: path median after-tax CAGR (USD, as precommitted) and, separately, path median KRW CAGR. <=2014 only."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/checks/costtax')
import ctlib as CT, dfctx as DC, dfe, run_grid as RG, run_df2 as R2
from picks_krw_lib import run_rec, kstats, fx_rel
OUT = '/mnt/project-files/research/df1/checks/costtax/'
t0 = time.time(); C = CT.all_configs(); mk = CT.markets('base')
rel_n, rel_p = fx_rel()
rows = {}
for i, c in C.items():
    r = {}
    for b in CT.SELM:
        m = mk[b]; T = m['r'].shape[1]
        if b == 'real_spx_29_54':
            cg, md = dfe.stats(R2.run_cfg(c, m), T); r['spx_mdd'] = float(md[0]); continue
        o, EE = run_rec(c, m); cg, md = dfe.stats(o, T)
        cgu, mdu, cgk, mdk = kstats(EE, o[:, 0], rel_n if b == 'real_ndx_86_14' else rel_p, True)
        if b == 'dev250_path':
            r.update(path_cagr=float(np.median(cg)), path_p10=float(np.percentile(md, 10)), path_krw_cagr=float(np.median(cgk)), path_krw_p10=float(np.percentile(mdk, 10)))
        else:
            r.update(ndx_cagr=float(cg[0]), ndx_mdd=float(md[0]), ndx_krw_cagr=float(cgk[0]), ndx_krw_mdd=float(mdk[0]))
    r['wd'] = min(r['path_p10'], r['ndx_mdd'], r['spx_mdd']); r['wd_krwN'] = min(r['path_p10'], r['ndx_krw_mdd'], r['spx_mdd'])
    r['wd_krwNP'] = min(r['path_krw_p10'], r['ndx_krw_mdd'], r['spx_mdd']); rows[i] = r
print('ran %d configs %.0fs' % (len(rows), time.time() - t0), flush=True)
def best(ids, sc):
    if not ids: return None
    b = max(ids, key=lambda i: rows[i][sc]); tie = [i for i in ids if rows[b][sc] - rows[i][sc] < 0.0005]
    return max(tie, key=lambda i: rows[i]['ndx_cagr'] if sc == 'path_cagr' else rows[i]['ndx_krw_cagr'])
res = dict(rows=rows, tiers={})
for wdk in ('wd', 'wd_krwN', 'wd_krwNP'):
    for sc in ('path_cagr', 'path_krw_cagr'):
        for tn, bud in (('A20', -0.20), ('T25', -0.25), ('T30', -0.30), ('T40', -0.40)):
            ins = [i for i in rows if rows[i][wdk] >= bud]; bu = best(ins, sc); b1 = best([i for i in ins if C[i].get('fam') != 'df2'], sc)
            res['tiers']['%s|%s|%s' % (wdk, sc, tn)] = dict(n_in=len(ins), union_best=bu, df1_best=b1, union_row=rows.get(bu), df1_row=rows.get(b1))
            if bu: print('%-9s %-14s %s n_in %4d union %-34s %s | df1 %-28s %s' % (wdk, sc, tn, len(ins), bu, {k: round(v, 4) for k, v in rows[bu].items()}, b1,
                                                                                (round(rows[b1]['path_cagr'], 4), round(rows[b1][wdk], 4)) if b1 else None), flush=True)
            else: print('%-9s %-14s %s n_in 0' % (wdk, sc, tn), flush=True)
json.dump(res, open(OUT + 'krw_reselect.json', 'w'))
print('done %.0fs' % (time.time() - t0))
