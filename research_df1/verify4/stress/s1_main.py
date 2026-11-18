"""verify4/stress: robustness of v1|s0.3|L1.5|K0|RC vs QQQ hold under the SAME change each time. <=2014 data only.
(a) delay 3 / cost 1.5x / both on dev250_path, (b) real NDX halves, (c) real_spx_29_54_B, (d) real_spx_70_85, plus baseline (C3)."""
import os, sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, df4cfg
W = dfe.WARM; CID = 'v1|s0.3|L1.5|K0|RC'; cfg = df4cfg.cfg_of(CID); print('cfg', cfg)
OUT = dict(cfg=cfg, rows={})
def pstat(o, T):
    cg, md = dfe.stats(o, T)
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
def sstat(o, T):
    cg, md = dfe.stats(o, T); return dict(cagr=float(cg[0]), mdd=float(md[0]))
def pair(m, st, **kw):
    T = m['r'].shape[1]
    c = st(df4cfg.run_any(cfg, m, **kw), T); q = st(dfe.run(m, np.full(m['r'].shape, 1.0), **kw)[0], T)
    return dict(cand=c, qqq=q)
def show(k, r):
    c, q = r['cand'], r['qqq']
    if 'p10' in c:
        print('%-28s cand med %6.2f p10 %6.2f mddmed %6.1f mddp10 %6.1f | QQQ med %6.2f p10 %6.2f mddmed %6.1f mddp10 %6.1f | beats both(med,p10mdd) %s'
              % (k, c['cagr']*100, c['p10']*100, c['mdd']*100, c['mdd_p10']*100, q['cagr']*100, q['p10']*100, q['mdd']*100, q['mdd_p10']*100, r['beats_both']), flush=True)
    else:
        print('%-28s cand %6.2f / %6.1f | QQQ %6.2f / %6.1f | beats both %s' % (k, c['cagr']*100, c['mdd']*100, q['cagr']*100, q['mdd']*100, r['beats_both']), flush=True)
def put(k, r):
    c, q = r['cand'], r['qqq']
    r['beats_both'] = bool(c['cagr'] > q['cagr'] and (c['mdd_p10'] > q['mdd_p10'] if 'p10' in c else c['mdd'] > q['mdd']))
    OUT['rows'][k] = r; show(k, r)

# ---- dev250_path (RC and QQQ hold use no bond -> bond-neutral adjustment irrelevant)
m = DC.market('dev250_path')
for k, kw in (('path|base', {}), ('path|delay3', dict(delay=3)), ('path|cost1.5x', dict(cost=0.0045)),
              ('path|delay3+cost1.5x', dict(delay=3, cost=0.0045)), ('path|cost2x', dict(cost=0.006)), ('path|delay4', dict(delay=4)),
              ('path|cost3x', dict(cost=0.009))):
    put(k, pair(m, pstat, **kw))
DC._M.pop('dev250_path', None); del m

# ---- single-path bases
for bn in ('real_ndx_86_14', 'real_spx_55_85', 'real_spx_29_54', 'real_spx_29_54_B', 'real_spx_70_85'):
    m = DC.market(bn); d = m['X_index'][m['ctx'].ii[0]]
    OUT['rows'][bn + '|window'] = [str(d[W].date()), str(d[-1].date())]
    assert d[-1] <= np.datetime64('2014-12-31')
    print(bn, 'eval window', d[W].date(), '->', d[-1].date())
    put(bn + '|base', pair(m, sstat))
    put(bn + '|delay3+cost1.5x', pair(m, sstat, delay=3, cost=0.0045))
json.dump(OUT, open('/mnt/project-files/research/df1/verify4/stress/s1_main.json', 'w'), indent=1)
print('saved')
