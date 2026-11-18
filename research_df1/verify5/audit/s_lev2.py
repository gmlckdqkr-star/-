import pickle, numpy as np, pandas as pd
P = pickle.load(open('/tmp/df5v/audit/lev_le2014.pkl', 'rb'))
ndx = P['_NDX'][3]; irx = P['_IRX'][3]
r = ndx.pct_change()
rf = (irx.reindex(ndx.index).ffill() / 100 / 252)
def chk(t, L, er, start=None):
    a = P[t][4].pct_change(); idx = a.dropna().index
    if start: idx = idx[idx >= pd.Timestamp(start)]
    rr = r.reindex(idx); ff = rf.reindex(idx); aa = a.reindex(idx)
    ok = rr.notna() & ff.notna() & aa.notna() & (aa.abs() < 0.5); rr, ff, aa = rr[ok], ff[ok], aa[ok]
    model = L * rr - (L - 1) * ff - er / 252
    diff = aa - model
    yrs = len(aa) / 252
    g_act = np.prod(1 + aa) ** (1 / yrs) - 1; g_mod = np.prod(1 + model) ** (1 / yrs) - 1
    te = diff.std() * np.sqrt(252)
    print('%-5s %s..%s n=%d  actual CAGR %.4f  model(L r-(L-1)rf-%.4f) CAGR %.4f  gap %+.4f/yr  mean daily diff*252 %+.4f  TE %.4f  mean rf %.4f' %
          (t, str(idx[0])[:10], str(idx[-1])[:10], len(aa), g_act, er, g_mod, g_act - g_mod, diff.mean() * 252, te, ff.mean() * 252))
    return diff
chk('QQQ', 1, 0.002 - 0.0055 * 0.846)
chk('QQQ', 1, 0.002, '2006-06-22')
chk('QQQ', 1, 0.002 - 0.0055 * 0.846, '2006-06-22')
chk('QLD', 2, 0.017)
chk('QLD', 2, 0.017, '2010-02-12')
chk('TQQQ', 3, 0.0245)
# same-date QQQ dividend yield in 2006-2014 and 2010-2014
for s in ('2006-06-22', '2010-02-12'):
    q = P['QQQ']; a = q[4].pct_change(); c = q[3].pct_change(); m = q.index >= pd.Timestamp(s)
    print('QQQ div yield (adj-close minus close return) since', s, '%.4f/yr' % ((a[m] - c[m]).mean() * 252))
