"""Parity: theory_sim/common/exec_engine.run (numpy, given to designers) vs MS1 engine beng.run1 (numba) on random noise.
No market data is used."""
import sys, os, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/root/.cache/ts_nb')
sys.path.insert(0, '/mnt/project-files/research/c3_brake/code'); sys.path.insert(0, '/mnt/project-files/research/theory_sim/common')
import beng, exec_engine as ee
from numba import njit
@njit
def ident(k, E, pk, b, held, x, st, p): return b
g = np.random.default_rng(11); P, T = 64, 300 + 30 * 252
r = g.standard_t(4, (P, T)) * 0.011 + 0.0003; r[:, 0] = 0
rf = np.repeat(np.abs(np.cumsum(g.normal(0, 0.0002, (P, T // 21 + 1)), axis=1) + 0.0002)[:, :, None], 21, axis=2).reshape(P, -1)[:, :T]
worst = 0.0
for kind in range(4):
    if kind == 0: B = np.full((P, T), 3.0)
    elif kind == 1: B = g.choice([0, 1, 1.5, 2, 3, np.nan], (P, T), p=[.2, .2, .1, .1, .35, .05])
    elif kind == 2: B = np.clip(np.cumsum(g.normal(0, .15, (P, T)), axis=1) % 3.4, 0, 3)
    else: B = np.repeat(g.choice([0, .3, .7, 1.2, 2.6, 3], (P, T // 40 + 1)), 40, axis=1)[:, :T]
    for dl in (1, 2, 3, 5):
        for cost in (0.003, 0.006):
            a = ee.run(r, rf, B, delay=dl, cost=cost, curve=True)
            pp, D = beng._args(dict(delay=dl, cost=cost))
            out = np.zeros((P, beng.NOUT)); EE = np.zeros((P, T - beng.WARM))
            for i in range(P):
                rec = np.zeros((T - beng.WARM, 4))
                beng.run1(r[i], rf[i], np.ascontiguousarray(B[i]), np.zeros((T, 12), np.float32), dl, cost, pp['tax'], D,
                          int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'], pp['step'], ident, np.zeros(1), out[i], rec, 1, pp['fstep'])
                EE[i] = rec[:, 0]
            d1 = np.max(np.abs(a['final'] - out[:, 0]) / np.maximum(np.abs(out[:, 0]), 1e-12))
            d2 = np.max(np.abs(a['mdd'] - out[:, 2])); d3 = np.max(np.abs(a['curve'] - EE) / np.maximum(np.abs(EE), 1e-12))
            worst = max(worst, d1, d2, d3)
            print('kind %d delay %d cost %.3f  rel.final %.2e  mdd %.2e  curve %.2e  med cagr %.4f' % (kind, dl, cost, d1, d2, d3, np.median(a['cagr'])))
print('WORST', worst, 'PARITY_OK' if worst < 1e-9 else 'PARITY_FAIL')
