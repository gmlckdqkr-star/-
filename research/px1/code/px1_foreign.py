import json, sys, numpy as np
from px1lib import *
import bk
MK = ['UK', 'CA', 'AU', 'DE', 'FR', 'JP']; S = specs(); assert len(S) == 270 and V1 in S
out = {}
for div in (True, False):
    tab = {}
    for m in MK:
        X, i0 = build(m, div); c = ctx(X, i0)
        if div: assert np.array_equal(signal(c, V1), bk.C3sig(c)), m          # F1 at v1 params == locked v1 signal
        tab[m] = dict(start=str(X.index[i0 + ov.WARM].date()), cagr=[float(run(c, s)[0][0]) for s in S])
        print(m, div, tab[m]['start'], 'v1 %.4f' % tab[m]['cagr'][S.index(V1)], flush=True)
    iv = S.index(V1); D = np.array([[tab[m]['cagr'][j] - tab[m]['cagr'][iv] for j in range(len(S))] for m in MK])
    score = D.mean(0); wins = (D > 1e-9).sum(0); ok = (wins >= 4) & (score >= 0.005)
    order = [j for j in np.argsort(-score) if ok[j]]
    out['div' if div else 'nodiv'] = dict(markets=tab, top=[dict(rank=r + 1, spec=list(S[j]), score=float(score[j]), wins=int(wins[j]), d=D[:, j].round(4).tolist()) for r, j in enumerate(order[:10])],
                                          n_qualified=int(ok.sum()), best_any=dict(spec=list(S[int(np.argmax(score))]), score=float(score.max())))
    print('div' if div else 'nodiv', 'qualified', int(ok.sum()), json.dumps(out['div' if div else 'nodiv']['top'][:5]), flush=True)
json.dump(out, open('/mnt/project-files/research/px1/results/foreign_le2014.json', 'w'), indent=1)
