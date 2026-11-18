import os, sys, time, numpy as np
sys.dont_write_bytecode = True
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/audit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5lib as L, df5data as DD, df5fam as F, dfe, dfk
X = R.W('REAL')
m = X.m; r = np.nan_to_num(m['r'])[0]; rf = np.nan_to_num(m['rf'])[0]
idx = X.w['S'].index.values[X.w['ii'][0]]
print('T', X.T, 'WARM date', str(idx[300])[:10], 'last', str(idx[-1])[:10], 'first', str(idx[0])[:10])
# QQQ via engine
cg, md, fin = R.qqq(X); print('QQQ engine cagr %.4f mdd %.4f' % (cg[0], md[0]))
# independent buy and hold (pre-tax, with initial cost, dividend proxy)
x = r[301:] - DD.ERQ/252
E = np.cumprod(1+x)*(1-0.003); pk = np.maximum.accumulate(np.r_[1.0, E]); dd = (np.r_[1.0,E]/pk - 1).min()
print('indep QQQ pretax mult %.3f mdd %.4f' % (E[-1], dd))
# T200 timing independent (pre-tax, cost 0.3%, delay 2, cash = T-bill ETF untaxed)
sig = X.sig.T(200)[0].astype(float)
w = np.zeros(len(r)); held = sig[299]
for t in range(300, len(r)): w[t] = sig[t-2] if t-2 >= 299 else sig[299]
# w[t] is the exposure decided at close t-2 and executed at close t -> earns return t+1
Ev = 1.0 - 0.003; Es = [Ev]; cur = sig[299]
for t in range(301, len(r)):
    Ev *= (1 + cur*(r[t]-DD.ERQ/252) + (1-cur)*(rf[t]-0.001/252))
    new = sig[t-2]
    if new != cur: Ev *= (1 - 0.003*abs(new-cur)); cur = new
    Es.append(Ev)
Es = np.array(Es); pk = np.maximum.accumulate(Es)
print('indep T200 pretax CAGR %.4f mdd %.4f switches %d' % (Es[-1]**(252/(len(r)-300))-1, (Es/pk-1).min(), int(np.abs(np.diff(sig[299:])).sum())))
jb = R.job(dict(fam='A1', sig='T200', size=('F',1.0), roff='TBILL'), X)
for kw in [dict(), dict(tax=0.0), dict(tax=0.0, cost=0.0)]:
    cg, md, fin = R.run_job(jb, X, None, **kw); print('engine T200', kw, 'cagr %.4f mdd %.4f' % (cg[0], md[0]))
# where is the T200 MDD? reconstruct with recon
o, EE = dfe.run(jb[1], jb[2], recon=True, **dict(jb[3]))
E = EE[0]; pk = np.maximum.accumulate(E); i1 = np.argmin(E/pk-1); i0 = np.argmax(E[:i1+1])
print('T200 engine MDD from', str(idx[300+i0])[:10], 'to', str(idx[300+i1])[:10], '%.3f' % (E[i1]/E[i0]-1))
