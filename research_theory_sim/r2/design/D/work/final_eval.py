"""final numbers on FRESH seeds (>= 10000, never used for selection) with the frozen rule.py"""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/theory_sim/common'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D')
sys.path.insert(0, '/mnt/project-files/research/theory_sim/r2/design/D/work')
import exec_engine as ee, sim, rule, rules, rule_A_carry
T = 7860
OUT = '/mnt/project-files/research/theory_sim/r2/design/D/work/final_parts2.jsonl'

def S(res):
    s = ee.summary(res)
    return {k: s[k] for k in ('cagr_med', 'cagr_p10', 'cagr_p90', 'p_dd80', 'mdd_med', 'avg_level_med', 'trades_per_year_med') if k in s}

def block(name, P, seed, mech, full=True, rob=False, **kw):
    t0 = time.time()
    d = sim.simulate(P, T, seed, mechanism=mech, **kw)
    r, rf, y = d['r'], d['rf'], d['y10']
    close = 1000.0 * np.cumprod(1 + r, axis=1)
    B = rule.target_levels(close, rf, y)
    out = dict(name=name, P=P, seed=seed, mechanism=mech, kw=kw)
    out['rule'] = S(ee.run(r, rf, B))
    out['ruleA_carry'] = S(ee.run(r, rf, rule_A_carry.target_levels(close, rf, y)))
    for lev in (1, 2, 3):
        out['hold%d' % lev] = S(ee.hold(r, rf, lev))
    cm = {}
    for L in (0.5, 1.0, 1.5, 2.0, 2.5):
        cm[L] = S(ee.run(r, rf, np.full(r.shape, L)))
    cm[3.0] = out['hold3']
    out['const'] = {str(k): v['cagr_med'] for k, v in cm.items()}
    bl = max(cm, key=lambda k: cm[k]['cagr_med']); out['best_const_level'] = bl; out['best_const'] = cm[bl]['cagr_med']
    out['tracked_const_1.25'] = S(ee.run(r, rf, rules.track(np.full(r.shape, 1.25), close, rf, theta=0.35)))
    if rob:
        out['delay3'] = S(ee.run(r, rf, B, delay=3)); out['delay5'] = S(ee.run(r, rf, B, delay=5))
        out['cost2x'] = S(ee.run(r, rf, B, cost=0.006))
        out['hold1_cost'] = out['hold1']['cagr_med']
    out['secs'] = time.time() - t0
    with open(OUT, 'a') as fh: fh.write(json.dumps(out) + '\n')
    print(name, 'ruleA %.4f' % out['ruleA_carry']['cagr_med'], 'rule %.4f hold1 %.4f bestc %.4f (L=%s) trk1.25 %.4f lev %.2f tr %.2f' % (
        out['rule']['cagr_med'], out['hold1']['cagr_med'], out['best_const'], bl, out['tracked_const_1.25']['cagr_med'],
        out['rule']['avg_level_med'], out['rule']['trades_per_year_med']), ('delay3 %.4f delay5 %.4f cost2x %.4f' % (
        out['delay3']['cagr_med'], out['delay5']['cagr_med'], out['cost2x']['cagr_med'])) if rob else '', '(%.0fs)' % out['secs'], flush=True)

if __name__ == '__main__':
    which = sys.argv[1]
    if which == 'gates':
        block('fresh_ON', 2000, 12000, True, rob=True)
        block('fresh_OFF', 2000, 12000, False, rob=True)
    elif which == 'rob':
        block('narrow_ON', 1000, 12001, True, prior_scale=0.5)
        block('narrow_OFF', 1000, 12001, False, prior_scale=0.5)
        block('wide_ON', 1000, 12002, True, prior_scale=1.5)
        block('wide_OFF', 1000, 12002, False, prior_scale=1.5)
        block('block_ON', 1000, 12003, True, block=True)
        block('block_OFF', 1000, 12003, False, block=True)
