"""Selection stage S2 on NEW selection seeds 5-8 (P=500 each). Tied structure as in rule.py: hss = 4*hs, hm = hs/4.
Same pre-declared criterion as S1: maximise ON median minus hold1x subject to OFF median >= best constant - 0.5 pp."""
import sys, os, itertools, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, harness as H, cand
W = {m: H.world([5, 6, 7, 8], 500, m) for m in (True, False)}
BASE = {m: H.baselines(W[m]) for m in W}
print('BASE', json.dumps({str(m): {k: round(v, 4) for k, v in BASE[m].items()} for m in W}), flush=True)
CA = {m: {} for m in W}
grid = [dict(c=0.02, a=a, b=b, hf=hf, hs=250) for a, b, hf in itertools.product((0.3, 0.4, 0.5), (0.04, 0.08, 0.12), (40, 60))]
grid += [dict(c=0.02, a=a, b=0.08, hf=40, hs=hs) for a in (0.3, 0.4) for hs in (180, 350)]
grid += [dict(c=c, a=0.4, b=0.08, hf=40, hs=250) for c in (0.015, 0.025)]
res = []
for p in grid:
    rows = {}
    for m in W:
        L = cand.levels(W[m]['close'], c=p['c'], a=p['a'], b=p['b'], hf=p['hf'], hs=p['hs'], hss=4 * p['hs'], hm=p['hs'] / 4, cache=CA[m])
        rows[m] = H.evaluate('S2 ' + ' '.join('%s=%s' % kv for kv in p.items()), L, W[m], BASE[m], 'ON' if m else 'OFF')
    r = dict(p=p, on=rows[True]['cagr_med'], on_h1=rows[True]['vs_hold1'], on_best=rows[True]['vs_best'], off=rows[False]['cagr_med'],
             off_best=rows[False]['vs_best'], dd80_on=rows[True]['p_dd80'], p10_on=rows[True]['p10'], lvl_on=rows[True]['lvl'], tpy_on=rows[True]['tpy'])
    res.append(r)
    print('%-55s ON %.4f (vs h1 %+.4f) OFF %.4f (vs best %+.4f) dd80 %.3f p10 %.4f lvl %.2f tpy %.1f' % (
        str(p), r['on'], r['on_h1'], r['off'], r['off_best'], r['dd80_on'], r['p10_on'], r['lvl_on'], r['tpy_on']), flush=True)
json.dump(dict(base={str(m): BASE[m] for m in W}, res=res), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 's2_results.json'), 'w'), indent=1)
ok = sorted([r for r in res if r['off_best'] >= -0.005], key=lambda r: -r['on_h1'])
print('TOP (OFF constraint met):')
for r in ok[:8]: print('  ', r['p'], 'ON-h1 %+.4f OFF-best %+.4f dd80 %.3f' % (r['on_h1'], r['off_best'], r['dd80_on']))
