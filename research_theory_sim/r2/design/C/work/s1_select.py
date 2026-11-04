"""Selection stage S1 on seeds 1-4 (P=500 each, 2000 paths per world). Final rule code path (cand.py).
Pre-declared criterion: maximise ON median CAGR minus hold1x, subject to OFF median >= best constant - 0.5 pp."""
import sys, os, itertools, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, cand
W = {m: H.world([1, 2, 3, 4], 500, m) for m in (True, False)}
BASE = {m: H.baselines(W[m]) for m in W}
print('BASE', json.dumps({str(m): {k: round(v, 4) for k, v in BASE[m].items()} for m in W}), flush=True)
CA = {m: {} for m in W}
res = []
grid = [dict(c=c, a=a, b=b, hf=hf) for c, a, b, hf in itertools.product((0.015, 0.02, 0.025), (0.15, 0.2, 0.3), (0.0, 0.04, 0.08), (20, 40))]
grid += [dict(c=c, a=a, b=a, hf=20, hm=hm) for c in (0.02,) for a in (0.1, 0.15, 0.2) for hm in (120,)]
for p in grid:
    rows = {}
    for m in W:
        L = cand.levels(W[m]['close'], cache=CA[m], **p)
        rows[m] = H.evaluate('S1 ' + ' '.join('%s=%s' % kv for kv in p.items()), L, W[m], BASE[m], 'ON' if m else 'OFF')
    res.append(dict(p=p, on=rows[True]['cagr_med'], on_h1=rows[True]['vs_hold1'], on_best=rows[True]['vs_best'],
                    off=rows[False]['cagr_med'], off_best=rows[False]['vs_best'], dd80_on=rows[True]['p_dd80'],
                    lvl_on=rows[True]['lvl'], tpy_on=rows[True]['tpy']))
    r = res[-1]
    print('%-50s ON %.4f (vs h1 %+.4f, vs best %+.4f) OFF %.4f (vs best %+.4f) dd80 %.3f lvl %.2f tpy %.1f' % (
        str(p), r['on'], r['on_h1'], r['on_best'], r['off'], r['off_best'], r['dd80_on'], r['lvl_on'], r['tpy_on']), flush=True)
json.dump(dict(base={str(m): BASE[m] for m in W}, res=res), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 's1_results.json'), 'w'), indent=1)
ok = [r for r in res if r['off_best'] >= -0.005]
ok.sort(key=lambda r: -r['on_h1'])
print('TOP (OFF constraint met):')
for r in ok[:8]: print('  ', r['p'], 'ON-h1 %+.4f OFF-best %+.4f dd80 %.3f' % (r['on_h1'], r['off_best'], r['dd80_on']))
