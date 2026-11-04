"""PSL1 step 3: books V1-V4 (PRECOMMIT_PSL1.md sec. 4) on the lab stock engine (lab.stocks.fast_run / run1 / sharpe).
Writes books.json and the MS1 input streams (streams.npz) for the selected and diagnostic books."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/lab')
from lab import stocks
feat, sc, out = sys.argv[1], sys.argv[2], sys.argv[3]
Z = np.load(feat); S = np.load(sc)
D, E, gok = Z['D'], Z['E'], Z['gok']
E = E & gok[:, None]
P = stocks.load()
dummy = dict(name='psl_dummy', family='stock_lattice', known=1, universe='sp500',
             stock=dict(rebalance='month', score='ret(21)', filter='age() >= 252', top=50))
tg0 = stocks.compile_targets(dummy, P)
assert np.array_equal(tg0.dec[tg0.dec >= D[0]], D), 'decision rows differ'
off = int(np.flatnonzero(tg0.dec == D[0])[0])
nd = len(tg0.dec)

def raw_books(X, K, mode='equal'):
    W = np.zeros((len(D), P.N))
    for j in range(len(D)):
        x = np.where(E[j] & np.isfinite(X[j]), X[j], -np.inf)
        m = int(np.isfinite(x).sum())
        if m == 0:
            continue
        p, f, _ = stocks.top_k(x, min(K, m))
        if mode == 'equal':
            W[j, p] = f / K
        else:   # probability-proportional: (p_hat - median p_hat)+, cap 5%
            med = np.median(X[j][np.isfinite(x)])
            r = np.maximum(X[j, p] - med, 0) * f
            if r.sum() > 0:
                w = r / r.sum()
                for _ in range(20):
                    w = np.minimum(w, 0.05); s = w.sum()
                    if s >= 1 - 1e-9 or (w < 0.05).sum() == 0:
                        break
                    free = w < 0.05; w[free] *= (1 - w[~free].sum()) / w[free].sum()
                W[j, p] = np.minimum(w, 0.05)
    return W

def tranche(W, n=3):
    T = np.zeros_like(W)
    for j in range(len(D)):
        a = max(0, j - n + 1)
        T[j] = W[a:j + 1].sum(0) / n
    elig = P.member[D] & P.has[D]
    return np.where(elig, T, 0.0)          # names no longer members / priced: their share stays CASH

def targets(W):
    picks, wts = [], []
    for j in range(nd):
        jj = j - off
        if jj < 0:
            picks.append(np.zeros(0, np.int64)); wts.append(np.zeros(0)); continue
        p = np.flatnonzero(W[jj] > 0); picks.append(p.astype(np.int64)); wts.append(W[jj, p])
    K = np.array([max(1, len(p)) for p in picks])
    return stocks.Targets(tg0.dec, picks, wts, K, tg0.elig, np.ones(P.T), {}, None, unit=1.0 / K)

def first_row(W):
    j = int(np.flatnonzero(W.sum(1) > 0)[0]); return P.idx[D[j] + 2 + 1]

def window_stats(tg, a, b, start):
    o = stocks.run1(P, tg, stocks.H_CONS, start, 0.003, 0.0, 2, dtax=0.0)
    E_ = o['E']; r = E_.pct_change().dropna(); r = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
    rf = pd.Series(stocks.rf_on(P.idx), index=P.idx).reindex(r.index).values
    ex = r.values - rf
    return float(ex.mean() / ex.std(ddof=1) * np.sqrt(252)), float((1 + r).prod() ** (252 / len(r)) - 1)

books = {'V1': (S['PSL'], 50, 'equal'), 'V2': (S['PROB'], 50, 'prob'), 'V3': (S['PSL'], 20, 'equal'),
         'V4': (S['DEV'], 50, 'equal')}
ew = stocks.ew_targets(P)
res, streams = {}, {}
for nm, (X, K, mode) in list(books.items()) + [('EW', (None, None, None))]:
    tg = ew if nm == 'EW' else targets(tranche(raw_books(X, K, mode)))
    st = pd.Timestamp('1976-01-02')
    dsh, dcg = window_stats(tg, '1976-01-01', '1995-12-31', st)
    csh, ccg = window_stats(tg, '1996-01-01', '2014-12-31', st)
    w86 = pd.Timestamp('1986-01-02')
    cons = stocks.run1(P, tg, stocks.H_CONS, w86, 0.003, 0.22, 2)
    a30 = stocks.run1(P, tg, stocks.H_ALL, w86, 0.003, 0.22, 2)
    pre = stocks.run1(P, tg, stocks.H_CONS, w86, 0.003, 0.0, 2, dtax=0.0)
    o = stocks.fast_run(P, tg, stocks.H_CONS, st, 0.003, 0.0, 2, want_E=True)
    Eq = o['E'][0]; r = Eq[1:] / Eq[:-1] - 1
    q = np.where(Eq[:-1] > 0, o['dnet'][0][1:] / np.where(Eq[:-1] > 0, Eq[:-1], 1.0), 0.0)
    streams[nm] = dict(dates=np.array([d.strftime('%Y-%m-%d') for d in o['idx'][1:]]), ret=r, basis_add=q,
                       turnover=min(1.0, float(o['turn'][0]) / 2))
    res[nm] = dict(design_sharpe=dsh, design_cagr_pretax=dcg, confirm_sharpe=csh, confirm_cagr_pretax=ccg,
                   w86_cons_after_tax=cons['cagr_at'], w86_all30=a30['cagr_at'], w86_mdd=cons['mdd'],
                   w86_sharpe_pretax=stocks.sharpe(pre, P), turn=cons['turn'],
                   avg_names=stocks.avg_names(P, tg, w86, 2))
    print(nm, {k: round(v, 4) for k, v in res[nm].items()}, flush=True)
sel = max(['V1', 'V2', 'V3'], key=lambda k: res[k]['design_sharpe'])
res['selected'] = sel
res['ndx_hold_w86'] = stocks.ndx_hold(pd.Timestamp('1986-01-02'), 0.003, 0.22, 2)['cagr_at']
print('selected', sel, 'NDX hold', res['ndx_hold_w86'])
json.dump(res, open(out, 'w'), indent=1)
np.savez_compressed(out.replace('.json', '_streams.npz'),
                    **{f'{k}_{f}': v[f] for k, v in streams.items() for f in ('dates', 'ret', 'basis_add')},
                    **{f'{k}_turnover': np.array(v['turnover']) for k, v in streams.items()})
