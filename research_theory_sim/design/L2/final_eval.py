"""Final evaluation of the FROZEN rule.py on fresh seeds (never used for selection). Writes synth_results.json."""
import sys, json, time
import numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import exec_engine as ee
import sim, rule

HERE = '/mnt/project-files/research/theory_sim/design/L2/'
T = 7860; P = 1000
MAIN_SEEDS = (10000, 10001)
WIDTH_SEEDS = (10002, 10003)
LEVELS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)


def summ(res):
    c = np.asarray(res['cagr'], dtype=float).copy(); c[~np.isfinite(c)] = -1.0       # 3x product < 0 -> ruin
    m = np.asarray(res['mdd'], dtype=float).copy(); m[~np.isfinite(m)] = -1.0
    d = dict(res); d['cagr'] = c; d['mdd'] = m
    s = ee.summary(d)
    return {k: (round(v, 5) if isinstance(v, float) else v) for k, v in s.items()}


def cat(rs):
    keys = [k for k in ('cagr', 'mdd', 'w7', 'w12', 'trades_per_year', 'avg_level') if k in rs[0]]
    return {k: np.concatenate([r[k] for r in rs]) for k in keys}


def worlds(seeds, mech, width=1.0):
    out = []
    for s in seeds:
        d = sim.simulate(P, T, s, mech, width=width)
        d['close'] = np.cumprod(1 + d['r'], axis=1) * 100.0
        out.append(d)
    return out


def block(ws, robust=True, consts=True):
    B = [rule.target_levels(d['close'], d['rf'], d['y10']) for d in ws]
    o = {'rule': summ(cat([ee.run(d['r'], d['rf'], b) for d, b in zip(ws, B)]))}
    for lev in (1, 2, 3):
        o['hold%dx' % lev] = summ(cat([ee.hold(d['r'], d['rf'], lev) for d in ws]))
    if consts:
        for L in LEVELS:
            o['const%.1f' % L] = summ(cat([ee.run(d['r'], d['rf'], np.full(d['r'].shape, L)) for d in ws]))
        best = max(LEVELS, key=lambda L: o['const%.1f' % L]['cagr_med'])
        o['best_const_level'] = best; o['best_const_cagr_med'] = o['const%.1f' % best]['cagr_med']
    if robust:
        o['rule_delay3'] = summ(cat([ee.run(d['r'], d['rf'], b, delay=3) for d, b in zip(ws, B)]))
        o['rule_delay5'] = summ(cat([ee.run(d['r'], d['rf'], b, delay=5) for d, b in zip(ws, B)]))
        o['rule_cost0.006'] = summ(cat([ee.run(d['r'], d['rf'], b, cost=0.006) for d, b in zip(ws, B)]))
    return o


if __name__ == '__main__':
    t0 = time.time()
    R = dict(rule_file='rule.py', params=rule.PARAMS, inputs=list(rule.INPUTS), P_per_seed=P, T=T,
             main_seeds=list(MAIN_SEEDS), width_seeds=list(WIDTH_SEEDS),
             note='fresh seeds >= 10000, never used for selection; NaN CAGR (3x product value < 0 in the engine) counted as -100%')
    R['on'] = block(worlds(MAIN_SEEDS, True))
    R['off'] = block(worlds(MAIN_SEEDS, False))
    R['off_loss_vs_best_const'] = round(R['off']['rule']['cagr_med'] - R['off']['best_const_cagr_med'], 5)
    R['on_minus_hold1x'] = round(R['on']['rule']['cagr_med'] - R['on']['hold1x']['cagr_med'], 5)
    for w in (0.5, 1.5):
        for mech in (True, False):
            R['width%.1f_%s' % (w, 'on' if mech else 'off')] = block(worlds(WIDTH_SEEDS, mech, w), robust=False)
    R['elapsed_s'] = round(time.time() - t0, 1)
    R['ts'] = time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())
    json.dump(R, open(HERE + 'synth_results.json', 'w'), indent=1)

    def line(lab, o):
        print('%-26s med %.4f  p10 %.4f  p90 %.4f  mdd_med %.3f  p_dd80 %.3f  tpy %s  lev %s' % (
            lab, o['cagr_med'], o['cagr_p10'], o['cagr_p90'], o['mdd_med'], o['p_dd80'],
            o.get('trades_per_year_med', '-'), o.get('avg_level_med', '-')))
    for wk in ('on', 'off'):
        print('== mechanism', wk.upper(), 'seeds', MAIN_SEEDS)
        for k in ['rule', 'rule_delay3', 'rule_delay5', 'rule_cost0.006', 'hold1x', 'hold2x', 'hold3x'] + ['const%.1f' % L for L in LEVELS]:
            line(k, R[wk][k])
        print('best const', R[wk]['best_const_level'], R[wk]['best_const_cagr_med'])
    for k in ('width0.5_on', 'width0.5_off', 'width1.5_on', 'width1.5_off'):
        o = R[k]
        print('%-14s rule %.4f  hold1x %.4f  hold2x %.4f  hold3x %.4f  best const %.1f -> %.4f' % (
            k, o['rule']['cagr_med'], o['hold1x']['cagr_med'], o['hold2x']['cagr_med'], o['hold3x']['cagr_med'],
            o['best_const_level'], o['best_const_cagr_med']))
    print('OFF loss vs best const', R['off_loss_vs_best_const'], ' ON minus hold1x', R['on_minus_hold1x'], ' elapsed', R['elapsed_s'])
