"""AUDIT (blind auditor, lane A): gates G-ON / G-OFF (check 3) and headline reproduction (check 6).
usage: a_gates.py TAG robust(0/1) seed1 [seed2 ...]     (P = 1000 per seed, pooled)"""
import sys, time, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/A')
import numpy as np
import exec_engine as ee
import sim, rule

T = 300 + 30 * 252; P = 1000
LV = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
tag = sys.argv[1]; robust = sys.argv[2] == '1'; seeds = [int(s) for s in sys.argv[3:]]
R = dict(seeds=seeds, P_per_seed=P)
t0 = time.time()
for mech in (True, False):
    acc = {}
    def add(k, res, f='cagr'):
        acc.setdefault(k, {}).setdefault('cagr', []).append(np.asarray(res['cagr']))
        for kk in ('mdd', 'avg_level', 'trades_per_year'):
            if kk in res: acc[k].setdefault(kk, []).append(np.asarray(res[kk]))
    for sd in seeds:
        w = sim.simulate(P, T, sd, mechanism=mech); r, rf, y10 = w['r'], w['rf'], w['y10']
        close = np.cumprod(1 + r, axis=1)
        B = rule.target_levels(close, rf, y10)
        add('rule', ee.run(r, rf, B))
        if robust:
            add('rule_delay3', ee.run(r, rf, B, delay=3)); add('rule_delay5', ee.run(r, rf, B, delay=5))
            add('rule_cost2x', ee.run(r, rf, B, cost=0.006))
        for lev in (1, 2, 3): add('hold%d' % lev, ee.hold(r, rf, lev))
        for L in LV: add('const_%.1f' % L, ee.run(r, rf, np.full(r.shape, L)))
    o = {}
    for k, a in acc.items():
        c = np.concatenate(a['cagr']); d = dict(cagr_med=float(np.median(c)), cagr_p10=float(np.percentile(c, 10)),
                                                 cagr_p90=float(np.percentile(c, 90)))
        if 'mdd' in a:
            m = np.concatenate(a['mdd']); d.update(mdd_med=float(np.median(m)), p_dd80=float(np.mean(m <= -0.8)))
        if 'avg_level' in a: d['avg_level_med'] = float(np.median(np.concatenate(a['avg_level'])))
        if 'trades_per_year' in a: d['trades_per_year_med'] = float(np.median(np.concatenate(a['trades_per_year'])))
        o[k] = d
    cl = {L: o['const_%.1f' % L]['cagr_med'] for L in LV}; bL = max(cl, key=cl.get)
    o['best_const_level'] = bL; o['best_const_cagr_med'] = cl[bL]
    rc = np.concatenate(acc['rule']['cagr']); hc = np.concatenate(acc['hold1']['cagr'])
    o['frac_paths_rule_beats_hold1'] = float(np.mean(rc > hc))
    # bootstrap sd of (median rule - median hold1) for the paired paths
    g = np.random.default_rng(0); bs = []
    for _ in range(400):
        i = g.integers(0, rc.size, rc.size); bs.append(np.median(rc[i]) - np.median(hc[i]))
    o['boot_sd_med_rule_minus_med_hold1'] = float(np.std(bs))
    k = 'ON' if mech else 'OFF'
    o['rule_minus_hold1'] = o['rule']['cagr_med'] - o['hold1']['cagr_med']
    o['rule_minus_best_const'] = o['rule']['cagr_med'] - o['best_const_cagr_med']
    if mech:
        o['G_ON_pass'] = bool(o['rule_minus_hold1'] > 0 and o['rule_minus_best_const'] > 0)
    else:
        o['G_OFF_pass'] = bool(o['rule_minus_best_const'] >= -0.010)
    R[k] = o
    print(k, 'done %.0fs' % (time.time() - t0), flush=True)
for k in ('ON', 'OFF'):
    v = R[k]
    print('%s rule %.4f hold1 %.4f hold2 %.4f hold3 %.4f bc %.4f (L=%.1f) rule-h1 %+.4f (boot sd %.4f) rule-bc %+.4f frac>h1 %.3f avgL %.2f tr/yr %.1f'
          % (k, v['rule']['cagr_med'], v['hold1']['cagr_med'], v['hold2']['cagr_med'], v['hold3']['cagr_med'],
             v['best_const_cagr_med'], v['best_const_level'], v['rule_minus_hold1'], v['boot_sd_med_rule_minus_med_hold1'],
             v['rule_minus_best_const'], v['frac_paths_rule_beats_hold1'], v['rule']['avg_level_med'], v['rule']['trades_per_year_med']))
    if robust:
        print('   delay3 %.4f delay5 %.4f cost2x %.4f' % (v['rule_delay3']['cagr_med'], v['rule_delay5']['cagr_med'], v['rule_cost2x']['cagr_med']))
print('G_ON', R['ON']['G_ON_pass'], 'G_OFF', R['OFF']['G_OFF_pass'])
json.dump(R, open('/mnt/project-files/research/theory_sim/r2/design/A/audit/a_gates_%s.json' % tag, 'w'), indent=1)
