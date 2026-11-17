import sys, numpy as np
sys.path.insert(0, '/home/user/-/research_xv1/code'); sys.path.insert(0, '/home/user/-/research_xv1/cand')
import xv1, cbase as cm
X = xv1.frame(xv1.OLD_END); v = xv1.View(X, xv1.extras(['semis', 'ret:SOXL', 'ret:QLD'], X.index)); i0 = len(X) - v.T
vix = v.c.vix[0]; ok = ~np.isnan(vix); f = int(np.argmax(ok))
print('first vix row', f, X.index[i0 + f], 'nan after first', int(np.isnan(vix[f:]).sum()), 'T', v.T)
def first(a): r = int(np.argmax(~np.isnan(a))); return r, str(X.index[i0 + r].date())
A = cm.sma(vix, 21)
print('D1', first(cm.lag(A, 126))); print('D2', first(cm.sma(vix, 252)))
med = np.full(v.T, np.nan)
for t in range(503, v.T):
    w = vix[t-503:t+1]
    if not np.isnan(w).any(): med[t] = 1
print('PRX', first(med))
print('semis nan', int(np.isnan(v.x['semis']).sum()), 'SOXL first', first(v.x['ret:SOXL']), 'QLD first', first(v.x['ret:QLD']))
