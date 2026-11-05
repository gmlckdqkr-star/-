import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
import ii
BASES = ['dev250_path', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85', 'dev250_glued']
ws = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [0.5]
out = {}
for bn in BASES:
    t0 = time.time()
    fin, E = ii.run(bn, 1.0, {}); r0 = ii.stats(bn, fin, E)
    out['%s|S085' % bn] = {k: float(r0[k]) for k in ('cagr', 'dd80', 'mdd', 'p10') if k in r0}
    c0 = np.log(fin)
    for s in ii.SID:
        for w in ws:
            fin, E = ii.run(bn, 1 - w, {s: w}); r = ii.stats(bn, fin, E)
            d = (np.log(fin) - c0) / (E.shape[1] / 252)
            out['%s|%s|%.2f' % (bn, s, w)] = dict(cagr=float(r['cagr']), dd80=float(r.get('dd80', np.nan)), mdd=float(r['mdd']),
                                                    dmed=float(np.median(d)), win=float(np.mean(d > 0)))
    print(bn, round(time.time() - t0), flush=True)
json.dump(out, open('mix50_%s.json' % sys.argv[1].replace(',', '_') if len(sys.argv) > 1 else 'mix50.json', 'w'), indent=1)
