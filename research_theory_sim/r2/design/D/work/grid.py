import sys, time, json, itertools, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
import exec_engine as ee, sim, rules
T = 7860
LOG = '/mnt/project-files/research/theory_sim/r2/design/D/work/variants.jsonl'

def worlds(P=600, seed=1, **kw):
    out = {}
    for mech in (True, False):
        d = sim.simulate(P, T, seed, mechanism=mech, **kw)
        close = 1000.0 * np.cumprod(1 + d['r'], axis=1)
        out[mech] = dict(r=d['r'], rf=d['rf'], y10=d['y10'], close=close, cache={})
        base = {'hold1': ee.summary(ee.hold(d['r'], d['rf'], 1))['cagr_med']}
        cm = {L: ee.summary(ee.run(d['r'], d['rf'], np.full(d['r'].shape, L)))['cagr_med'] for L in (0.5, 1, 1.5, 2, 2.5, 3)}
        base['bestc'] = max(cm.values()); base['bestL'] = max(cm, key=cm.get)
        out[mech]['base'] = base
    return out

def evaluate(W, tag, trk=None, const=None, **prm):
    res = {}
    for mech in (True, False):
        w = W[mech]
        if const is not None: B = np.full(w['r'].shape, float(const))
        else: B = rules.target(w['close'], w['rf'], w['y10'], cache=w['cache'], **prm)
        if trk is not None: B = rules.track(B, w['close'], w['rf'], theta=trk)
        s = ee.summary(ee.run(w['r'], w['rf'], B))
        res[mech] = s
    on, off = res[True], res[False]
    prm = dict(prm); prm['trk'] = trk; prm['const'] = const
    row = dict(tag=tag, prm={k: v for k, v in prm.items() if v is not None}, on=on['cagr_med'], off=off['cagr_med'],
               on_vs_bestc=on['cagr_med'] - W[True]['base']['bestc'], off_vs_bestc=off['cagr_med'] - W[False]['base']['bestc'],
               on_vs_hold1=on['cagr_med'] - W[True]['base']['hold1'], lev_on=on['avg_level_med'], tr_on=on['trades_per_year_med'],
               lev_off=off['avg_level_med'], tr_off=off['trades_per_year_med'], dd80_on=on['p_dd80'])
    with open(LOG, 'a') as fh: fh.write(json.dumps(row) + '\n')
    print('%-10s %-60s ON %.4f (%+.4f c, %+.4f h1) OFF %.4f (%+.4f c) lev %.2f/%.2f tr %.1f/%.1f' % (
        tag, json.dumps(prm)[:60], row['on'], row['on_vs_bestc'], row['on_vs_hold1'], row['off'], row['off_vs_bestc'],
        row['lev_on'], row['lev_off'], row['tr_on'], row['tr_off']), flush=True)
    return row
