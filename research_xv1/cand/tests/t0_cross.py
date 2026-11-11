import sys, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import xv1, cbase as cm, cross
names = ['semis','ret:SOXL','ret:TLT','ret:TMF','ret:QLD','ret:TQQQ','cal:month','cal:dom','cal:dow','cal:ymod4']
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(names, X.index)); i0 = len(X) - v.T
def first(a): r = int(np.argmax(~np.isnan(a))); return r, str(X.index[i0 + r].date())
print('T', v.T, 'acc start row 300 =', X.index[i0+300].date(), 'first row', X.index[i0].date())
for k in names: print(k, 'nan count', int(np.isnan(v.x[k]).sum()), 'first', first(v.x[k]))
for nm, a in (('r', v.c.r[0]), ('rb', v.c.rb[0]), ('rf', v.c.rf[0]), ('y10', v.m['y10']), ('vol20', v.c.vol(20)[0])): print(nm, int(np.isnan(a).sum()), first(a))
dy = cross._dy(v); print('dy', first(dy))
k = cross._kappa(v.c.r[0], dy, 252); print('kappa252', first(k))
have = cross._ndx_ok(v); print('index exists from row', int(np.argmax(have)), str(X.index[i0 + int(np.argmax(have))].date()))
q = np.where(have, np.log1p(v.c.r[0]), np.nan)      # as sbc_cap: rows before the index exists are missing (NOTES G5)
for N in (126,252,504): print('rho', N, first(cross._roll_corr(q, -dy, N, min(200, N))))
R = np.where(have, cm.semis_level(v) / cm.ndx_level(v), np.nan); print('SMA200 of S/NDX', first(cm.sma(R, 200)))
# calendar projection check: projected exec day vs actual row t+2 (calendar fields only)
m, d, w, y, ok = cross._exec_day(v); T = v.T
am, ad = v.x['cal:month'], v.x['cal:dom']
bad = [(t, int(m[t]), int(d[t]), int(am[t+2]), int(ad[t+2])) for t in range(T-2) if (m[t], d[t]) != (am[t+2], ad[t+2])]
print('projection mismatches', len(bad)); print(bad[:12])
# window flags: projected vs real row t+2
import copy
class V2: pass
for st, en in (('oct','jun'),('election','jun'),('oct','apr')):
    p = cross._window(v, st, en)
    s = V2(); s.T = T
    s.x = {k: np.r_[v.x[k][2:], [np.nan, np.nan]] for k in cross.NAMES_MID}
    # real window of row t+2: apply zero-step projection
    mm, dd_, ww, yy, ok2 = cross._exec_day(s, steps=0)
    if st == 'oct': sflag = (yy == 2) & (mm >= 10)
    else:
        fm = (dd_ - ww - 1) % 7 + 1; sflag = (yy == 2) & (((mm == 11) & (dd_ >= fm + 2)) | (mm == 12))
    lastm = {'jun': 6, 'apr': 4}[en]; real = (sflag | ((yy == 3) & (mm <= lastm))) & ok2
    diff = np.flatnonzero(p[:T-2] != real[:T-2]); print(st, en, 'window flag mismatches', len(diff), 'window rows', int(p.sum()))
