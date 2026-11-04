"""PL1 per-stock mega lattice (PRECOMMIT_PL1.md)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/indiv_stock/is7/code'); import us7lib as U
L = U.L
OUT = '/mnt/project-files/research/s085_weak/pl1/'
d, R = U.load(dr_fail=-0.5)
T, N = d.T, d.N
ME = L.month_ends(d.dates, '1970-12-01', '2014-12-31')
Pm, Rm = d.Pm, d.Rm
roll = lambda X, n, fn: getattr(pd.DataFrame(X).rolling(n, min_periods=n), fn)().to_numpy()
vol126 = roll(Rm, 126, 'std'); max252 = roll(Pm, 252, 'max'); sma200 = roll(Pm, 200, 'mean')
m = np.nan_to_num(L.mkt_ew(d, R)); ew = np.cumprod(1 + m); ews = pd.Series(ew).rolling(200, min_periods=200).mean().to_numpy()
ex = ME + 2; K = len(ME)
NC = 486
cell = np.full((K, N), -1, np.int64); elig = np.zeros((K, N), bool)
for k, t in enumerate(ME):
    el = d.mem[t] & d.fin[t]
    def ret(n, skip=0):
        a, b = t - skip - n, t - skip
        return Pm[b] / Pm[a] - 1 if a >= 0 else np.full(N, np.nan)
    F = [ret(231, 21), ret(21), vol126[t], Pm[t] / max252[t] - 1, Pm[t] / sma200[t] - 1]
    ok = el.copy()
    for f in F: ok &= np.isfinite(f)
    if ok.sum() < 30: continue
    c = np.zeros(N, np.int64)
    for f in F:
        q = pd.Series(np.where(ok, f, np.nan)).rank(pct=True).to_numpy()
        b = np.where(q <= 1 / 3, 0, np.where(q <= 2 / 3, 1, 2)); c = c * 3 + b
    ms = int(np.isfinite(ews[t]) and ew[t] > ews[t])
    c = c * 2 + ms
    cell[k] = np.where(ok, c, -1); elig[k] = ok
# realized excess return over holding period of decision k (exec ex[k] -> ex[k+1])
Y = np.full((K, N), np.nan)
for k in range(K - 1):
    a, b = ex[k], min(ex[k + 1], T - 1)
    if a >= T - 1: break
    seg = np.nan_to_num(R[a + 1:b + 1]); G = np.prod(1 + seg, axis=0) - 1
    sel = elig[k]; Y[k] = np.where(sel, G - G[sel].mean(), np.nan)

def estimates(kappa, perm=None):
    """est[k, i] using observations from decisions j <= k-2. perm: stock-table permutation (null)."""
    S = np.zeros((N, NC)); n = np.zeros((N, NC)); Sc = np.zeros(NC); Nc = np.zeros(NC)
    E = np.full((K, N), np.nan); EP = np.full((K, N), np.nan)
    for k in range(K):
        j = k - 2
        if j >= 0:
            ok = elig[j] & np.isfinite(Y[j])
            ii = np.where(ok)[0]; cc = cell[j, ii]; yy = Y[j, ii]
            np.add.at(S, (ii, cc), yy); np.add.at(n, (ii, cc), 1); np.add.at(Sc, cc, yy); np.add.at(Nc, cc, 1)
        ii = np.where(elig[k])[0]
        if len(ii) == 0: continue
        cc = cell[k, ii]; Mc = Sc[cc] / (Nc[cc] + 50)
        src = ii if perm is None else perm[ii]
        if kappa is None: E[k, ii] = Mc
        else: E[k, ii] = (S[src, cc] + kappa * Mc) / (n[src, cc] + kappa)
        EP[k, ii] = Mc
    return E, EP

def ic(E):
    v = []
    for k in range(K - 1):
        if d.dates[ME[k]] < pd.Timestamp('1976-01-01'): continue
        x, y = E[k], Y[k]; ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() > 30: v.append(pd.Series(x[ok]).rank().corr(pd.Series(y[ok]).rank()))
    v = np.array(v); return dict(ic=float(v.mean()), t=float(v.mean() / v.std() * np.sqrt(len(v))), n=len(v))

t76 = np.searchsorted(ME, np.searchsorted(d.dates, pd.Timestamp('1976-01-01')))
def backtest(E, top=20):
    def choose(k):
        if k < t76 or not np.isfinite(E[k]).any(): return np.where(elig[k], 1.0, np.nan), None
        return np.where(elig[k], E[k], np.nan), top
    return U.run_var(d, R, ME, choose)

def report(tag, res):
    net, gross, tau = res['net'], res['gross'], res['tau']
    s = {'ALL76': L.stats(net, '1976-01-01', '2014-12-31'), 'A': L.stats(net, '1976-01-01', '1995-12-31'), 'B': L.stats(net, '1996-01-01', '2014-12-31')}
    msr = L.ms1(gross, tau)
    return dict(tag=tag, tau=round(tau, 3), cagr_pretax_76_14=s['ALL76']['cagr'], shx_76_14=s['ALL76']['shx'], shx_A=s['A']['shx'], shx_B=s['B']['shx'],
                min_shx=min(s['A']['shx'], s['B']['shx']), mdd=s['ALL76']['mdd'], ms1_path=msr['dev250_path']['cagr'], ms1_dd80=msr['dev250_path'].get('dd80'),
                ms1_real_ndx=msr['real_ndx_86_14']['cagr'], s085_path=msr['dev250_path']['s085'], hold1x_path=msr['dev250_path']['hold1x'])

if __name__ == '__main__':
    out = {'IC': {}, 'BT': {}}
    ES, EP = estimates(12); EO, _ = estimates(1)
    V = {'PL-S': ES, 'PL-O': EO, 'PL-P': EP, 'PL-D': ES - EP}
    for kname, E in V.items(): out['IC'][kname] = ic(E); print(kname, out['IC'][kname], flush=True)
    rng = np.random.default_rng(11); nulls = []
    for s in range(5):
        perm = rng.permutation(N); EN, _ = estimates(12, perm); out['IC']['N%d' % (s + 1)] = ic(EN); nulls.append(EN)
        print('N%d' % (s + 1), out['IC']['N%d' % (s + 1)], flush=True)
    out['BT']['EW'] = report('EW', U.run_var(d, R, ME, lambda k: (np.where(elig[k], 1.0, np.nan), None))); print(out['BT']['EW'], flush=True)
    for kname, E in list(V.items()) + [('N1', nulls[0])]:
        out['BT'][kname] = report(kname, backtest(E)); print(out['BT'][kname], flush=True)
    json.dump(out, open(OUT + 'pl1_results.json', 'w'), indent=1)
