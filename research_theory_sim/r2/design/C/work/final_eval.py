"""Final evaluation of the frozen rule.py on FRESH seeds (never used for selection), P=2000 per world (4 x 500 chunks).
ON world seeds 10001-10004, OFF world same seeds (mechanism=False). Robustness: delay 3/5, cost 0.006, prior narrow/wide.
Writes ../synth_results.json."""
import sys, os, json, time, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); TOP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import numpy as np, harness as H
import exec_engine as ee
spec = importlib.util.spec_from_file_location('rule', os.path.join(TOP, 'rule.py')); R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
SEEDS = [10001, 10002, 10003, 10004]


def full(w, label, robust=True):
    t0 = time.time()
    B = R.target_levels(w['close'], w['rf'])
    tr = time.time() - t0
    base = H.baselines(w)
    out = dict(label=label, n_paths=int(w['r'].shape[0]), rule_time_s=tr)
    s = ee.summary(ee.run(w['r'], w['rf'], B))
    out['rule'] = s
    out['hold'] = {L: ee.summary(ee.hold(w['r'], w['rf'], L)) for L in (1, 2, 3)}
    out['const'] = {('%.1f' % L): base['const%.1f' % L] for L in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)}
    out['best_const'] = base['best_const']; out['best_const_level'] = base['best_const_level']
    if robust:
        out['delay3'] = ee.summary(ee.run(w['r'], w['rf'], B, delay=3))
        out['delay5'] = ee.summary(ee.run(w['r'], w['rf'], B, delay=5))
        out['cost2x'] = ee.summary(ee.run(w['r'], w['rf'], B, cost=0.006))
    H.evaluate('FINAL rule.py', B, w, base, label, log=True)
    return out


def brief(o):
    s = o['rule']
    msg = '%-10s rule med %.4f p10 %.4f p90 %.4f dd80 %.3f lvl %.2f tpy %.1f | hold1 %.4f hold2 %.4f hold3 %.4f | best const %.4f @%.1f' % (
        o['label'], s['cagr_med'], s['cagr_p10'], s['cagr_p90'], s['p_dd80'], s['avg_level_med'], s['trades_per_year_med'],
        o['hold'][1]['cagr_med'], o['hold'][2]['cagr_med'], o['hold'][3]['cagr_med'], o['best_const'], o['best_const_level'])
    if 'delay3' in o:
        msg += ' | d3 %.4f d5 %.4f c2x %.4f' % (o['delay3']['cagr_med'], o['delay5']['cagr_med'], o['cost2x']['cagr_med'])
    print(msg, flush=True)


res = {}
for mech in (True, False):
    w = H.world(SEEDS, 500, mech)
    o = full(w, 'ON' if mech else 'OFF'); res[o['label']] = o; brief(o)
    del w
for nm, ov in (('NOSCAR', dict(theta_s=0.0, q=0.0)), ('FLAT', dict(theta_s=0.0, q=0.0, theta_a=1.0, theta_b=1.0, psi=0.0))):
    w = H.world(SEEDS, 500, True, override=ov)
    o = full(w, nm, robust=False); res[nm] = o; brief(o)
    del w
for s in (0.5, 1.5):
    for mech in (True, False):
        w = H.world(SEEDS, 500, mech, s=s)
        o = full(w, ('ON' if mech else 'OFF') + '_s%.1f' % s, robust=False); res[o['label']] = o; brief(o)
        del w
# timing check: P=500, T=10000
w = H.world([10009], 500, True)
c = np.concatenate([w['close'], w['close'][:, -1:] * np.cumprod(1 + w['r'][:, 1:2141], axis=1)], axis=1)[:, :10000]
t0 = time.time(); R.target_levels(c, np.zeros_like(c)); res['speed_P500_T10000_s'] = time.time() - t0
print('speed P=500 T=10000: %.1fs' % res['speed_P500_T10000_s'])
json.dump(res, open(os.path.join(HERE, 'final_raw.json'), 'w'), indent=1, default=float)
