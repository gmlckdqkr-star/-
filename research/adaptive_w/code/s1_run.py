"""AW stage 1+2 (PRECOMMIT_AW.md sha ce678a79). Select on S&P 55-85/70-85, confirm on NDX 86-14 + dev250_path. <=2014."""
import sys, json, time, itertools, numpy as np
sys.path.insert(0, '/mnt/project-files/research/adaptive_w/code'); import data
OUT = '/mnt/project-files/research/adaptive_w/results/'
TRI = {'T1': (['VALPROF4_L1', 'CAPE_L3'], [.75, .15, .10]), 'T2': (['SMALL_L3', 'CAPE_L3'], [.80, .10, .10]),
       'T3': (['VALPROF4_L1', 'SMALL_L3'], [.60, .20, .20]), 'T4': (['VALPROF4_L1', 'CAPE_L3'], [.40, .30, .30]),
       'T5': (['IDX_L1', 'GOLDHV_L2'], [.70, .20, .10])}
RULES = []
for L, e in itertools.product((36, 60), (2, 4)): RULES.append(('TILT_L%d_e%d' % (L, e), 1, (L, e, 60)))
for e, a in itertools.product((0.5, 1.5), (0.01, 0.05)): RULES.append(('HEDGE_e%.1f_a%.2f' % (e, a), 2, (e, a, 0)))
for k, t in itertools.product((2, 5), (0.03, 0.10)): RULES.append(('BAYES_k%d_t%.2f' % (k, t), 3, (k, t, 0)))
for d, h in itertools.product((0.005, 0.01), (0, 0.05)): RULES.append(('DRIFT_d%.3f_h%.2f' % (d, h), 4, (d, 36, h)))
RULES = [(n + '_cap' + c, rid, prm, c) for (n, rid, prm) in RULES for c in 'AB']
def one(bn, A, B, W0, rid=0, prm=(0, 0, 0), cap='A', **kw):
    fin, E, WT = data.run(bn, A, B, W0, rid, prm, cap=cap, **kw); return data.cagr(fin, E), data.mdd(E), WT
def stage(bns, rules, extra=None):
    R = {}
    for bn in bns:
        for t, (nm, W0) in TRI.items():
            A, B = data.load(bn, nm); c0, m0, _ = one(bn, A, B, W0); R.setdefault('FIXED', {})[bn + '|' + t] = dict(c=float(np.median(c0)), dd80=float(np.mean(m0 <= -.8)))
            for (n, rid, prm, cap) in rules:
                for tag, kw in (extra or {'': {}}).items():
                    c, m, WT = one(bn, A, B, W0, rid, prm, cap, **kw); d = c - c0
                    R.setdefault(n + tag, {})[bn + '|' + t] = dict(c=float(np.median(c)), d=float(np.median(d)), win=float(np.mean(d > 0)),
                        dd80=float(np.mean(m <= -.8)), dd80_0=float(np.mean(m0 <= -.8)),
                        wfin=[float(x) for x in np.median(WT[:, -3], 0)], wmax=[float(x) for x in WT[:, 12:-2].max(axis=(0, 1))],
                        wmin=[float(x) for x in WT[:, 12:-2].min(axis=(0, 1))])
        print(bn, 'done', flush=True)
    return R
if __name__ == '__main__':
    t0 = time.time()
    R1 = stage(['real_spx_55_85', 'real_spx_70_85'], RULES)
    sc = {}
    for n, _, _, _ in RULES:
        sc[n] = min(np.mean([R1[n][bn + '|' + t]['d'] for t in TRI]) for bn in ['real_spx_55_85', 'real_spx_70_85'])
    rk = sorted(sc, key=lambda k: -sc[k]); sel = rk[0]
    fam = {}
    for n in rk:
        f = n.split('_')[0]
        if f not in fam: fam[f] = n
    print('SELECTED', sel, sc[sel], 'family best', {f: (k, round(sc[k] * 100, 3)) for f, k in fam.items()}, flush=True)
    json.dump(dict(stage1=R1, score=sc, rank=rk, selected=sel, family_best=fam), open(OUT + 's1_select.json', 'w'), indent=1)
    conf = [r for r in RULES if r[0] in set(fam.values())]
    R2 = stage(['real_ndx_86_14', 'dev250_path'], conf)
    selr = [r for r in RULES if r[0] == sel]
    R3 = stage(['dev250_path'], selr, extra={'|cost2x': dict(cost=0.006), '|lag5': dict(lag=5)})
    json.dump(dict(confirm=R2, stress=R3, selected=sel, family_best=fam), open(OUT + 's2_confirm.json', 'w'), indent=1)
    print('sec', round(time.time() - t0))
