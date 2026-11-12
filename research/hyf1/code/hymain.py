import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hyrun as R, uprun as U
OUT = '/mnt/project-files/research/hyf1/results/main_le2014.json'; res = {}
C4 = [(n, a) for n in (100, 200) for a in (False, True)]
ST = {'base': {}, 'a_cost2': dict(cmul=2.0, fee=0.018), 'b_delay5': dict(gdelay=5), 'c_desmooth': dict(desmooth=True),
      'all': dict(cmul=2.0, fee=0.018, gdelay=5, desmooth=True)}
for sn, kw in ST.items():
    for bn in (['dev250_path', 'real_ndx_86_14', 'dev250_glued'] if sn == 'base' else ['dev250_path', 'real_ndx_86_14']):
        ref = R.run(bn, None, cmul=kw.get('cmul', 1.0)); rows = {'v1': U.row(ref)}
        for n, a in C4:
            x = R.run(bn, n, a, **kw); rows['n%d%s' % (n, '_a5' if a else '')] = U.row(x, ref)
        res['%s|%s' % (bn, sn)] = rows
        print(bn, sn, ' '.join('%s %.2f/%+.2f(%.0f%%)' % (k, 100 * v['cagr'], 100 * v.get('d_ref', 0), 100 * v.get('pw_ref', 0)) for k, v in rows.items()), flush=True)
# HYG actual product window
ref = R.run('real_ndx_86_14', None, hyg=True); w0 = R.window(ref, '2007-04-12')
res['hyg_window'] = {}
for n, a in C4:
    x = R.run('real_ndx_86_14', n, a, hyg=True); w = R.window(x, '2007-04-12')
    res['hyg_window']['n%d%s' % (n, '_a5' if a else '')] = dict(v1=w0, cand=w, d=w - w0)
print('HYG window', json.dumps({k: round(100 * v['d'], 2) for k, v in res['hyg_window'].items()}), 'v1', round(100 * w0, 2))
json.dump(res, open(OUT, 'w'), indent=1)
