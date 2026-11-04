"""Final fresh-seed evaluation of the frozen rule.py (seeds >= 10000, never used for selection). Writes synth_results.json."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/design/L3')
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import exec_engine as ee, sim, rule
T = 300 + 30 * 252
OUT = '/mnt/project-files/research/theory_sim/design/L3/synth_results.json'


def fix(res):
    bad = ~np.isfinite(res['cagr'])
    if bad.any():
        res = dict(res); res['cagr'] = np.where(bad, -1.0, res['cagr']); res['mdd'] = np.where(bad, -1.0, res['mdd'])
    return res


def S(res):
    s = ee.summary(fix(res))
    keep = ('cagr_med', 'cagr_p10', 'cagr_p90', 'mdd_med', 'p_dd80', 'p_dd95', 'trades_per_year_med', 'avg_level_med')
    return {k: round(s[k], 5) for k in keep if k in s}


def world(seeds, mech, prior='base', P=1000):
    rs, fs = [], []
    for sd in seeds:
        d = sim.simulate(P, T, sd, mech, prior); rs.append(d['r']); fs.append(d['rf'])
    return np.concatenate(rs), np.concatenate(fs)


def block(r, rf, full=True):
    C = np.cumprod(1 + r, axis=1) * 100.0
    B = rule.target_levels(C, rf)
    with np.errstate(all='ignore'):
        out = {'rule': S(ee.run(r, rf, B))}
        rc = fix(ee.run(r, rf, B))['cagr']
        for L in (1, 2, 3):
            out[f'hold{L}x'] = S(ee.hold(r, rf, L))
        h1 = fix(ee.hold(r, rf, 1))['cagr']
        const = {}
        for L in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
            const[str(L)] = S(ee.run(r, rf, np.full(r.shape, L)))
        out['const'] = const
        bestL = max(const, key=lambda k: const[k]['cagr_med'])
        out['best_const_level'] = float(bestL); out['best_const_cagr_med'] = const[bestL]['cagr_med']
        cb = fix(ee.run(r, rf, np.full(r.shape, float(bestL))))['cagr']
        out['share_paths_rule_gt_hold1x'] = round(float(np.mean(rc > h1)), 4)
        out['share_paths_rule_gt_best_const'] = round(float(np.mean(rc > cb)), 4)
        if full:
            out['delay3'] = S(ee.run(r, rf, B, delay=3)); out['delay5'] = S(ee.run(r, rf, B, delay=5))
            out['cost0.006'] = S(ee.run(r, rf, B, cost=0.006))
    return out


t0 = time.time()
res = {'rule_params': rule.PARAMS, 'fresh_seeds': [10000, 10001], 'P_per_seed': 1000, 'T': T}
for mech in (True, False):
    r, rf = world([10000, 10001], mech)
    res['mechanism_' + ('on' if mech else 'off')] = block(r, rf)
    del r, rf
    print('done mech', mech, round(time.time() - t0), 's', flush=True)
for prior, sd in (('narrow', 10002), ('wide', 10003)):
    for mech in (True, False):
        r, rf = world([sd], mech, prior)
        res[f'prior_{prior}_' + ('on' if mech else 'off')] = block(r, rf, full=False)
        del r, rf
        print('done', prior, mech, round(time.time() - t0), 's', flush=True)
off = res['mechanism_off']
res['mechanism_off_loss_vs_best_const'] = round(off['rule']['cagr_med'] - off['best_const_cagr_med'], 5)
json.dump(res, open(OUT, 'w'), indent=1)
print(json.dumps({k: (v['rule'] if isinstance(v, dict) and 'rule' in v else v) for k, v in res.items()}, indent=0)[:3000])
