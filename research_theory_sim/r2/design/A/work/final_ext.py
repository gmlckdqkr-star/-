"""final numbers on FRESH seeds (never used for selection): 10001-10002 main table (P=2000 pooled), 10003 prior
narrowed/widened, 10004 mechanism weak/strong.  [final_ext.py: precision extension on 10005-10008]"""
import sys, json, time
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A')
import numpy as np, exec_engine as ee, sim, rule
T = 300 + 30 * 252; P = 1000
LV = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)

def summ(c, m=None, extra=None):
    c = np.asarray(c); d = dict(cagr_med=float(np.median(c)), cagr_p10=float(np.percentile(c, 10)), cagr_p90=float(np.percentile(c, 90)))
    if m is not None: m = np.asarray(m); d.update(mdd_med=float(np.median(m)), p_dd80=float(np.mean(m <= -0.8)))
    if extra: d.update(extra)
    return d

def block(seeds, mech, robust=True, **kw):
    acc = {}
    def add(k, res, keys=('cagr', 'mdd', 'avg_level', 'trades_per_year')):
        a = acc.setdefault(k, {kk: [] for kk in keys if kk in res})
        for kk in a: a[kk].append(np.asarray(res[kk]))
    for sd in seeds:
        w = sim.simulate(P, T, sd, mechanism=mech, **kw); r, rf = w['r'], w['rf']
        cl = np.cumprod(1 + r, axis=1)
        B = rule.target_levels(cl, rf)
        add('rule', ee.run(r, rf, B))
        if robust:
            add('rule_delay3', ee.run(r, rf, B, delay=3)); add('rule_delay5', ee.run(r, rf, B, delay=5)); add('rule_cost2x', ee.run(r, rf, B, cost=0.006))
            for lev in (1, 2, 3): add('hold%d' % lev, ee.hold(r, rf, lev), keys=('cagr', 'mdd'))
        else:
            add('hold1', ee.hold(r, rf, 1), keys=('cagr', 'mdd'))
        for L in LV: add('const_%.1f' % L, ee.run(r, rf, np.full(r.shape, L)))
        del w, r, rf, cl, B
    out = {}
    for k, a in acc.items():
        c = np.concatenate(a['cagr']); m = np.concatenate(a['mdd'])
        ex = {}
        if 'avg_level' in a: ex['avg_level_med'] = float(np.median(np.concatenate(a['avg_level'])))
        if 'trades_per_year' in a: ex['trades_per_year_med'] = float(np.median(np.concatenate(a['trades_per_year'])))
        out[k] = summ(c, m, ex)
    cl = {L: out['const_%.1f' % L]['cagr_med'] for L in LV}
    bL = max(cl, key=cl.get)
    out['best_const_level'] = bL; out['best_const_cagr_med'] = cl[bL]
    # paired: fraction of paths where rule beats hold1
    rc = np.concatenate(acc['rule']['cagr']); hc = np.concatenate(acc['hold1']['cagr'])
    out['frac_paths_rule_beats_hold1'] = float(np.mean(rc > hc))
    return out


R = {}
R['ext_ON'] = block((10005, 10006, 10007, 10008), True, robust=False); print('ON done', flush=True)
R['ext_OFF'] = block((10005, 10006, 10007, 10008), False, robust=False); print('OFF done', flush=True)
json.dump(R, open('/mnt/project-files/research/theory_sim/r2/design/A/work/final_ext.json', 'w'), indent=1)
for k, v in R.items():
    print('%-10s rule %.4f  hold1 %.4f  best const %.4f (L=%.1f)  rule-h1 %+.4f  rule-bc %+.4f  frac>h1 %.3f' % (k, v['rule']['cagr_med'], v['hold1']['cagr_med'], v['best_const_cagr_med'], v['best_const_level'], v['rule']['cagr_med'] - v['hold1']['cagr_med'], v['rule']['cagr_med'] - v['best_const_cagr_med'], v['frac_paths_rule_beats_hold1']))
