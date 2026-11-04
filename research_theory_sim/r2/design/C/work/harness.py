"""Design harness (designer C). Synthetic data only, from ../sim.py. Logs every evaluated variant to variants.csv."""
import sys, os, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import numpy as np
import sim
import exec_engine as ee

T = 300 + 30 * 252
LOG = os.path.join(HERE, 'variants.csv')


def world(seeds, P, mech, s=1.0, override=None):
    rs, fs = [], []
    for sd in seeds:
        d = sim.simulate(P, T, sd, mechanism=mech, prior_scale=s, override=override)
        rs.append(d['r']); fs.append(d['rf'])
    r = np.concatenate(rs); rf = np.concatenate(fs)
    close = 100.0 * np.cumprod(1 + r, axis=1)
    return dict(r=r, rf=rf, close=close)


def baselines(w):
    out = {}
    for L in (1, 2, 3):
        out['hold%d' % L] = ee.summary(ee.hold(w['r'], w['rf'], L))['cagr_med']
    best = (-9, None)
    for L in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        c = ee.summary(ee.run(w['r'], w['rf'], np.full(w['r'].shape, L)))['cagr_med']
        out['const%.1f' % L] = c
        if c > best[0]: best = (c, L)
    out['best_const'] = best[0]; out['best_const_level'] = best[1]
    return out


def evaluate(name, B, w, base, tag='', delay=2, cost=0.003, log=True):
    res = ee.run(w['r'], w['rf'], B, delay=delay, cost=cost)
    s = ee.summary(res)
    row = dict(name=name, tag=tag, cagr_med=s['cagr_med'], p10=s['cagr_p10'], p_dd80=s['p_dd80'],
               lvl=s['avg_level_med'], tpy=s['trades_per_year_med'],
               vs_hold1=s['cagr_med'] - base['hold1'], vs_best=s['cagr_med'] - base['best_const'])
    if log:
        new = not os.path.exists(LOG)
        with open(LOG, 'a') as f:
            if new: f.write('time,name,tag,cagr_med,p10,p_dd80,avg_level,trades_py,vs_hold1,vs_bestconst\n')
            f.write('%s,%s,%s,%.5f,%.5f,%.4f,%.3f,%.2f,%.5f,%.5f\n' % (
                time.strftime('%Y-%m-%dT%H:%M', time.gmtime()), name, tag, row['cagr_med'], row['p10'], row['p_dd80'],
                row['lvl'], row['tpy'], row['vs_hold1'], row['vs_best']))
    return row


def fmt(row):
    return '%-40s %-8s med %.4f p10 %.4f dd80 %.3f lvl %.2f tpy %.1f | vs h1 %+.4f vs best %+.4f' % (
        row['name'][:40], row['tag'], row['cagr_med'], row['p10'], row['p_dd80'], row['lvl'], row['tpy'],
        row['vs_hold1'], row['vs_best'])
