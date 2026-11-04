"""final fresh-seed evaluation of the frozen rule (seeds >= 10000, never used for selection) -> synth_results.json"""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); import exec_engine as ee
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/B'); import sim, rule

T = 300 + 30 * 252
OUT = '/mnt/project-files/research/theory_sim/r2/design/B/synth_results.json'


def block(P, seed, mech, prior_scale=1.0, extra=True):
    s = sim.simulate(P, T, seed, mech, prior_scale=prior_scale)
    r, rf = s['r'], s['rf']
    close = 100.0 * np.exp(np.cumsum(np.log1p(r), axis=1))
    B = rule.target_levels(close, rf)
    d = {}
    sm = ee.summary(ee.run(r, rf, B))
    d['rule_cagr_med'] = sm['cagr_med']; d['rule_cagr_p10'] = sm['cagr_p10']; d['rule_cagr_p90'] = sm['cagr_p90']
    d['rule_p_dd80'] = sm['p_dd80']; d['rule_mdd_med'] = sm['mdd_med']; d['rule_avg_level'] = sm['avg_level_med']
    d['rule_trades_per_year'] = sm['trades_per_year_med']
    for lev in (1, 2, 3):
        h = ee.summary(ee.hold(r, rf, lev)); d['hold%dx_cagr_med' % lev] = h['cagr_med']
        if lev == 1: d['hold1x_p_dd80'] = h['p_dd80']; d['hold1x_mdd_med'] = h['mdd_med']
    best, bl = -9.0, None
    for L in np.arange(0.5, 3.01, 0.5):
        c = ee.summary(ee.run(r, rf, np.full(r.shape, L)))['cagr_med']; d['const%.1f_cagr_med' % L] = c
        if c > best: best, bl = c, float(L)
    d['best_const_cagr_med'] = best; d['best_const_level'] = bl
    if extra:
        d['delay3_cagr_med'] = ee.summary(ee.run(r, rf, B, delay=3))['cagr_med']
        d['delay5_cagr_med'] = ee.summary(ee.run(r, rf, B, delay=5))['cagr_med']
        d['cost2x_cagr_med'] = ee.summary(ee.run(r, rf, B, cost=0.006))['cagr_med']
        p0 = dict(rule.PARAMS); p0['b_hope'] = 0.0          # reference only (not a candidate): Kelly part alone
        d['ref_kelly_only_cagr_med'] = ee.summary(ee.run(r, rf, rule.target_levels(close, rf, params=p0)))['cagr_med']
    pr = s['params']
    d['world_premium_med'] = float(np.median((r[:, ee.WARM:].mean(1) - rf[:, ee.WARM:].mean(1)) * 252))
    d['world_vol_med'] = float(np.median(r[:, ee.WARM:].std(1) * np.sqrt(252)))
    d['P'] = P; d['seed'] = seed; d['mechanism'] = mech; d['prior_scale'] = prior_scale
    return d


if __name__ == '__main__':
    t0 = time.time()
    res = {'created': time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()), 'rule_params': rule.PARAMS, 'T': T}
    res['fresh_on'] = block(2000, 10001, True)
    print('ON ', json.dumps(res['fresh_on']), flush=True)
    res['fresh_off'] = block(2000, 10001, False)
    print('OFF', json.dumps(res['fresh_off']), flush=True)
    for w, sd in ((0.5, 10002), (1.5, 10003)):
        for mech in (True, False):
            k = 'prior_x%.1f_%s' % (w, 'on' if mech else 'off')
            res[k] = block(1000, sd, mech, prior_scale=w, extra=False)
            print(k, json.dumps(res[k]), flush=True)
    on, off = res['fresh_on'], res['fresh_off']
    res['gate_on'] = dict(rule=on['rule_cagr_med'], hold1x=on['hold1x_cagr_med'], best_const=on['best_const_cagr_med'],
                          passed=bool(on['rule_cagr_med'] > on['hold1x_cagr_med'] and on['rule_cagr_med'] > on['best_const_cagr_med']))
    res['gate_off'] = dict(rule=off['rule_cagr_med'], best_const=off['best_const_cagr_med'],
                           loss_vs_best_const=off['best_const_cagr_med'] - off['rule_cagr_med'],
                           passed=bool(off['rule_cagr_med'] >= off['best_const_cagr_med'] - 0.01))
    res['runtime_s'] = time.time() - t0
    with open(OUT, 'w') as f: json.dump(res, f, indent=1, default=float)
    print('gates', res['gate_on'], res['gate_off'], 'runtime %.0fs' % res['runtime_s'])
