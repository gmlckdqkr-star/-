"""AW stress fix: s1_run stage R3 compared cost-2x rule to cost-1x fixed. Here both sides use the same cost. dev250_path, <=2014."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/adaptive_w/code'); import data, s1_run
OUT = '/mnt/project-files/research/adaptive_w/results/'
sel = json.load(open(OUT + 's1_select.json')); names = set(sel['family_best'].values()); R = {}
for t, (nm, W0) in s1_run.TRI.items():
    A, B = data.load('dev250_path', nm)
    for tag, kw in {'cost2x': dict(cost=0.006), 'lag5': dict(lag=5)}.items():
        f0, E0, _ = data.run('dev250_path', A, B, W0, cost=kw.get('cost', 0.003)); c0 = data.cagr(f0, E0)
        for (n, rid, prm, cap) in [r for r in s1_run.RULES if r[0] in names]:
            f, E, _ = data.run('dev250_path', A, B, W0, rid, prm, cap=cap, **kw); d = data.cagr(f, E) - c0
            R.setdefault(n, {}).setdefault(tag, {})[t] = float(np.median(d))
for n in R:
    print(n, {k: (round(np.mean(list(v.values())) * 100, 3), [round(x * 100, 2) for x in v.values()]) for k, v in R[n].items()})
json.dump(R, open(OUT + 's2b_stress.json', 'w'), indent=1)
