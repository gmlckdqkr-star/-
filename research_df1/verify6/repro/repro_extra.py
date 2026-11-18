"""Verifier extras in X world: (i) P-calibrated (world-invariant) N1 shift applied in X; (ii) N2 with ER only on the KF (pre-2002) segment."""
import os, sys, json, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/df6v/repro/nb')
sys.path.insert(0, '/mnt/project-files/research/df1/code'); sys.path.insert(0, '/tmp/df6v/repro')
import df5lib as L, mysim as M
from gates import gate
WARM = 300; ERQ = 0.002 - 0.0055 * (1 - 0.154); DY3 = (0.025 + 0.015 + 0.040) / 3
shP = json.load(open('/tmp/df6v/repro/res_P.json'))['info']['shiftN1_ann'] / 252
w = L.world('X'); m = w['m']; ii = w['ii']; idx = w['S'].index
r = np.nan_to_num(m['r']); rf = np.nan_to_num(m['rf']); P, T = r.shape
A = np.nan_to_num(M.def3_series().reindex(idx).values.astype(float)[ii])
pre02 = (idx < pd.Timestamp('2002-01-01')).astype(float)[ii]
print('X: share of sampled days (t>=300) from the 2002-2014 ETF segment', float(1 - pre02[:, WARM:].mean()))
QQQ = r - ERQ / 252; TQ = 3 * r - 2 * rf - 0.0245 / 252; Th10 = WARM + 10 * 252
def go(S3, c):
    f, md, SN = M.sim(np.stack([TQ, QQQ, S3], 2), np.array([0.0, 0.0, DY3 / 252]), [c['a'], c['b'], c['c']], c['R'], snaps=(Th10,))
    return {'X30': (M.cagr(f, T), md), 'X10': (M.cagr(SN[Th10][0], Th10), SN[Th10][1])}
fq, mq, SNq = M.sim(QQQ[:, :, None], np.zeros(1), [1.0], 0, snaps=(Th10,))
Q = {'X30': M.summ(M.cagr(fq, T), mq), 'X10': M.summ(M.cagr(SNq[Th10][0], Th10), SNq[Th10][1])}; qc = {'X30': M.cagr(fq, T), 'X10': M.cagr(SNq[Th10][0], Th10)}
CFG = {'c252': dict(a=0.20, b=0.00, c=0.80, R=252), 'c63': dict(a=0.20, b=0.05, c=0.75, R=63)}
out = {}
for cn, c in CFG.items():
    for tag, S3 in (('Pshift', A - shP - 0.0015 / 252), ('N2_ERpre02only', A - 0.0015 / 252 * pre02)):
        o = go(S3, c); row = {k: M.summ(cg, md, qc[k]) for k, (cg, md) in o.items()}
        out[cn + '|' + tag] = {k: gate(row, Q, k) for k in ('X30', 'X10')}
        print(cn, tag, json.dumps(out[cn + '|' + tag]))
