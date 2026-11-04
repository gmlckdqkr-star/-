"""final numbers on FRESH seeds (>= 10000, never used for selection)."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L1'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import sim, rule, exec_engine as ee
np.seterr(all='ignore')
T = 7860; P = 2000; SEEDS = (10000, 10001)
KEYS = ('cagr_med', 'cagr_p10', 'cagr_p90', 'mdd_med', 'p_dd80', 'p_dd95', 'trades_per_year_med', 'avg_level_med')

def pooled(results):
    """pool path-level results across seeds then summarise"""
    out = {}
    for k in results[0]:
        if results[0][k] is None or k == 'curve': continue
        out[k] = np.concatenate([np.atleast_1d(r[k]) for r in results])
    return ee.summary(out)

def world(mech, scale):
    acc = {}
    for seed in SEEDS:
        s = sim.simulate(P, T, seed=seed, mechanism=mech, prior_scale=scale)
        r, rf = s['r'], s['rf']
        assert np.isfinite(r).all()
        close = np.cumprod(1 + r, axis=1)
        B = rule.target_levels(close, rf)
        rows = {'rule': ee.run(r, rf, B)}
        if scale == 1.0:
            rows['rule_delay3'] = ee.run(r, rf, B, delay=3)
            rows['rule_delay5'] = ee.run(r, rf, B, delay=5)
            rows['rule_cost2x'] = ee.run(r, rf, B, cost=0.006)
        for L in (1, 2, 3): rows[f'hold{L}x'] = ee.hold(r, rf, L)
        for L in (0.5, 1.0, 1.5, 2.0, 2.5): rows[f'const{L}'] = ee.run(r, rf, np.full((P, T), L))
        rows['const3.0'] = rows['hold3x']
        for k, v in rows.items(): acc.setdefault(k, []).append(v)
    summ = {k: {kk: round(float(vv), 5) for kk, vv in pooled(v).items() if kk in KEYS} for k, v in acc.items()}
    consts = {k: v['cagr_med'] for k, v in summ.items() if k.startswith('const')}
    bk = max(consts, key=consts.get)
    summ['best_const'] = dict(name=bk, level=float(bk[5:]), cagr_med=consts[bk])
    return summ

out = dict(seeds=list(SEEDS), paths_per_seed=P, T=T, rule_params=rule.PARAMS)
t0 = time.time()
for mech in (True, False):
    for scale in (1.0, 0.5, 1.5):
        key = f"{'on' if mech else 'off'}_prior{scale}"
        out[key] = world(mech, scale)
        print(key, 'rule', out[key]['rule']['cagr_med'], 'hold1x', out[key]['hold1x']['cagr_med'], 'best_const', out[key]['best_const'], '%.0fs' % (time.time() - t0), flush=True)
json.dump(out, open('/mnt/project-files/research/theory_sim/design/L1/work/final_eval.json', 'w'), indent=1)
print('done')
