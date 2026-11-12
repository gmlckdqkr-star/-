"""independent share-based re-implementation of the RU1 account spec; compare with ru.acct"""
import sys, numpy as np
sys.path.insert(0, '/mnt/project-files/research/acct3/code'); sys.path.insert(0, '/mnt/project-files/research/ru1/code')
import ac3, ru
W = ru.WARM
def mine(r, rf, L, X, dep, krw, wait, fxc, ccost=.003, ctax=.22, D=.25, er3=.0245, cspr=1.0):
    n = len(L); u = 0.0; p = 1.0; c = 1.0 * (1 - fxc) / X[W]; acb = 0.0; G = 0.0; cur = None; last = None; pend = 0.0
    taxk = 0.0; nwait = 0
    for k in range(n):
        t = k + W; x = X[t] if krw else 1.0
        if k > 0 and k % 252 == 0:
            due = ctax * max(G - D, 0.0); G = 0.0
            if due > 0:
                need = due / x; tot = u * p + c; f = min(need / tot, 1.0)
                G += f * (u * p * x - acb); acb *= 1 - f; u *= 1 - f; c *= 1 - f
                taxk += due * (1 if krw else X[t])
        if k > 0:
            p *= 1 + 3 * r[t] - 2 * rf[t] - er3 / 252
            c *= 1 + max(rf[t] - cspr / 252, 0.0) * (1 - .154)
        if dep[k] > 0:
            usd = dep[k] / X[t] * (1 - fxc); tot = u * p + c; w = u * p / tot; c += usd
            if wait and last is not None and k - last <= 4:
                pend += usd; nwait += 1
            else:
                b = w * usd; cost = ccost * b; c -= b; u += (b - cost) / p; acb += b * x
        if L[k] != cur:
            tot = u * p + c; tgt = L[k] / 3 * tot; d = tgt - u * p; cost = ccost * abs(d)
            if d < 0 and u > 0:
                su = -d / p; G += su * p * x - acb * su / u; acb -= acb * su / u; u -= su; c += -d
            elif d > 0:
                u += d / p; c -= d; acb += d * x
            s = (tot - cost) / tot; u *= s; c *= s
            if cur is not None: last = k
            cur = L[k]; pend = 0.0
    xe = X[W + n - 1]
    if krw:
        g = G + u * p * xe - acb; ft = ctax * max(g - D, 0.0); fk = (u * p + c) * xe * (1 - fxc) - ft; fu = fk / xe
    else:
        g = G + u * p - acb; ft = ctax * max(g - D, 0.0); fu = u * p + c - ft; fk = fu * xe * (1 - fxc)
    return fu, fk, nwait
B = ac3.prep(); rng = np.random.default_rng(1)
worst = 0.0; cnt = 0
for bn, npth in (('real_ndx_86_14', 1), ('dev250_path', 12)):
    b = B[bn]
    for i in range(npth):
        r, rf, L = b['R'][i], b['RF'][i], b['L'][i]; T = len(r); n = T - W
        X = np.exp(np.cumsum(rng.normal(0, 0.006, T))); X /= X[W]
        dep = np.zeros(n); dep[21::21] = 0.01
        for krw in (0, 1):
            for wait in (0, 1):
                for fxc in (0.0, 0.0025):
                    o = np.zeros(9); eu = np.zeros(n); ek = np.zeros(n)
                    ru.acct(r, rf, L, X, dep, krw, wait, fxc, .003, .22, .25, .0245, 1.0, o, eu, ek)
                    fu, fk, nw = mine(r, rf, L, X, dep, krw, wait, fxc)
                    e = max(abs(o[0] / fu - 1), abs(o[1] / fk - 1)); worst = max(worst, e); cnt += 1
                    if e > 1e-9 or nw != o[7]: print('MISMATCH', bn, i, krw, wait, fxc, o[0], fu, o[1], fk, o[7], nw)
print('cases', cnt, 'max rel diff', worst)
