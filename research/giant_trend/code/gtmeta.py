"""Macro-adaptive meta strategies (PRECOMMIT_GT 4.15). Sleeves = 1x net streams of the T strategies on 1926-2014,
after costs, fees, withholding and a tax haircut (own pre-tax minus after-tax CAGR on the full run, spread monthly).
Each sleeve is then a fund-like asset 'S_<name>'."""
import sys, numpy as np
import gtsetup as G
LAGK = int(sys.argv[1]) if len(sys.argv) > 1 else 0
SLEEVES = ['BUF_T1', 'BUF_T2', 'MUN_T', 'GRA_T', 'GRA_C', 'ONE_T', 'DRU_T', 'SOR_T', 'DAL_QX', 'DAL_RP', 'TEM_T', 'MAR_T']
c, E, P, S = G.c, G.E, G.P, G.S

def _build():
    ones = np.ones(c.T, int); full = list(range(0, c.T)); out = {}
    for n in SLEEVES:
        dec = G.STRATS[n][0]()
        if LAGK: dec = S.lag(dec, LAGK)
        w, pre = E.run(dec, ones, P, full)
        yrs = (len(w) - 1) / 12; at = w[-1] ** (1 / yrs) - 1; pt = np.prod(1 + pre) ** (1 / yrs) - 1
        hair = max(pt - at, 0.0)
        s = np.r_[0.0, pre - hair / 12]          # s[t] = return of month t (month 0 has none)
        out[n] = s
        for L in (1, 2, 3):
            P[L]['S_' + n] = np.maximum(L * s - (L - 1) * c.rf - (E.DRAG[L] + E.EXTRA[L]) / 12, -0.99)
    return out

def meta_e(c, names):
    dec = [None] * c.T; dec[0] = ('w', {'MKT': 1.0})
    for t in range(61, c.T): dec[t] = ('w', {'S_' + n: 1.0 / len(names) for n in names})
    return dec

def meta_r(c, streams, look=36):
    dec = [None] * c.T; dec[0] = ('w', {'MKT': 1.0}); prev = None
    for t in range(61 + look, c.T):
        best, bs = None, -9
        for n, s in streams.items():
            x = s[t - look + 1:t + 1] - c.rf[t - look + 1:t + 1]; sr = x.mean() / x.std() if x.std() > 0 else 0
            if sr > bs: best, bs = n, sr
        tgt = {'S_' + best: 1.0}
        if tgt != prev: dec[t] = ('w', tgt); prev = tgt
    return dec

def meta_q(c, streams, minn=36):
    dec = [None] * c.T; dec[0] = ('w', {'MKT': 1.0}); prev = None; q = S._quad(c)
    for t in range(62, c.T):
        if q[t] < 0: continue
        ss = [s for s in range(61, t) if q[s] == q[t]]
        if len(ss) < minn: tgt = {'MKT': 1.0}
        else:
            sc = {n: np.mean([st[s + 1] - c.rf[s + 1] for s in ss]) for n, st in streams.items()}
            tgt = {'S_' + max(sc, key=sc.get): 1.0}
        if tgt != prev: dec[t] = ('w', tgt); prev = tgt
    return dec

def strats(tag):
    streams = _build()
    return {'META_E': (lambda: meta_e(c, SLEEVES), 'long'),
            'META_R': (lambda: meta_r(c, streams), 'long'),
            'META_Q': (lambda: meta_q(c, streams), 'long'),
            'MKT_H': G.STRATS['MKT_H']}
