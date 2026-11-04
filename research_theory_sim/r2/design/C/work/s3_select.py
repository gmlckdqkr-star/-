"""Selection stage S3 on NEW selection seeds 9-12 (P=500 each). Declared BEFORE running (see design_log.md, S3):
objective = mean over worlds {ON, OFF, NOSCAR, FLAT} of (rule median CAGR - best constant median of that world),
subject to G-ON (ON median > hold1x and > best const) and OFF >= best const - 0.5 pp.
NOSCAR = theory falsification F2 (theta_s = 0, q = 0; everything else drawn from the prior).
FLAT   = falsification F2+F5 (theta_s = 0, q = 0, theta_a = theta_b = 1, psi = 0: crash/vol clustering with a constant mean).
These stress worlds use the frozen sim with parameters overridden; the priors are not changed."""
import sys, os, itertools, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, cand
SEEDS = [9, 10, 11, 12]
WD = dict(ON=(True, None), OFF=(False, None), NOSCAR=(True, dict(theta_s=0.0, q=0.0)),
          FLAT=(True, dict(theta_s=0.0, q=0.0, theta_a=1.0, theta_b=1.0, psi=0.0)))
W = {k: H.world(SEEDS, 500, m, override=o) for k, (m, o) in WD.items()}
BASE = {k: H.baselines(W[k]) for k in W}
print('BASE', json.dumps({k: {kk: round(v, 4) for kk, v in BASE[k].items()} for k in W}), flush=True)
CA = {k: {} for k in W}
grid = [dict(c=0.02, a=a, b=b, hf=40, hs=hs) for a, b, hs in itertools.product((0.2, 0.3, 0.4, 0.5), (0.04, 0.08), (250, 350))]
grid += [dict(c=0.02, a=a, b=0.04, hf=40, hs=250) for a in (0.0, 0.1)]
res = []
for p in grid:
    r = dict(p=p)
    for k in W:
        L = cand.levels(W[k]['close'], c=p['c'], a=p['a'], b=p['b'], hf=p['hf'], hs=p['hs'], hss=4 * p['hs'], hm=p['hs'] / 4, cache=CA[k])
        row = H.evaluate('S3 ' + ' '.join('%s=%s' % kv for kv in p.items()), L, W[k], BASE[k], k)
        r[k] = row['cagr_med']; r[k + '_best'] = row['vs_best']; r[k + '_h1'] = row['vs_hold1']; r[k + '_dd80'] = row['p_dd80']
    r['obj'] = np.mean([r[k + '_best'] for k in W])
    r['gon'] = (r['ON_h1'] > 0) and (r['ON_best'] > 0); r['goff'] = r['OFF_best'] >= -0.005
    res.append(r)
    print('%-52s obj %+.4f | ON %.4f h1 %+.4f | OFF-best %+.4f | NOSCAR-best %+.4f | FLAT-best %+.4f | dd80 ON %.2f FLAT %.2f' % (
        str(p), r['obj'], r['ON'], r['ON_h1'], r['OFF_best'], r['NOSCAR_best'], r['FLAT_best'], r['ON_dd80'], r['FLAT_dd80']), flush=True)
json.dump(dict(base=BASE, res=res), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 's3_results.json'), 'w'), indent=1, default=float)
ok = sorted([r for r in res if r['gon'] and r['goff']], key=lambda r: -r['obj'])
print('TOP (gates met):')
for r in ok[:8]: print('  ', r['p'], 'obj %+.4f ON-h1 %+.4f' % (r['obj'], r['ON_h1']))
