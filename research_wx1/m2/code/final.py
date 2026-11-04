"""After the one-shot confirmation (no variant passed (iii)): lab-engine rows + MS1 stream for the discovery #1 variant
(failure reference, PRECOMMIT_M2 §7) and, labelled post-hoc reference only, the plain full composite ALL/EQ/C0/K20/M.
Also: confirmation-period composite IC (locked after selection), IC_eq on the WS1 oracle curve, link-bias checks.
argv: code_dir out_json ids_json(list of variant ids)"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/lab'); sys.path.insert(0, sys.argv[1])
from lab import stocks
import m2lib as M, labbridge as LB
d = M.load(); P = stocks.load()
z = np.load(M.SCR + '/ic_cache.npz'); ic, C, RR = z['ic'], z['C'], z['RR']
j86 = int(np.searchsorted(d.dd, pd.Timestamp('1986-01-01'))); j00 = int(np.searchsorted(d.dd, pd.Timestamp('2000-01-01')))
rows = range(j86, d.nd); rs = slice(j86, d.nd)
est_U = M.past_means(ic, C); est_T = M.past_means(ic, C, regime=d.up); est_M = M.past_means(ic, C, regime=d.moff)
sub = M.subsets(d); DEF = M.def_mask(d)
ones = np.ones(d.nd, np.bool_); gates = {'C0': ones, 'C1': d.up.astype(np.bool_), 'C2': (~d.moff).astype(np.bool_)}
import itertools
VAR = []
for S, W, SN, CF in itertools.product(list(sub), ['EQ', 'ICW', 'RIDGE'], (0, 1), (0, 1)):
    for Cn in ('C0', 'C1', 'C2', 'C3', 'C4', 'C5'):
        for K, Rb in itertools.product([5, 10, 20, 30, 50], ['M', 'Q', 'T']):
            VAR.append(dict(S=S, W=W, SN=SN, CF=CF, C=Cn, K=K, Rb=Rb))


def score(v):
    S, W, Cn = v['S'], v['W'], v['C']
    eU = None if W == 'EQ' else est_U
    if Cn in ('C0', 'C1', 'C2'):
        sc = M.composite(d, M.weights(d, sub[S], W, eU, rows=rows), rs)
    elif Cn == 'C3':
        a = M.composite(d, M.weights(d, sub[S], W, eU, rows=rows), rs)
        b = M.composite(d, M.weights(d, DEF, W, eU, rows=rows), rs)
        sc = np.where(d.up[:, None], a, b)
    else:
        e = est_T if Cn == 'C4' else est_M
        sc = M.composite(d, M.weights(d, sub[S], W, e, None if W == 'EQ' else est_U, rows=rows), rs)
    if v['SN']:
        sc = M.sector_neutral(d, sc, rs)
    if v['CF']:
        sc = np.where(d.crash, np.nan, sc)
    return sc, gates.get(Cn, ones)


ws = json.load(open('/mnt/project-files/research/wide_shape/results/map_summary.json'))['A2']['US500_h21']['curves']


def ic_eq(K, y):
    c = ws[str(K if K in (5, 10, 20) else 20)]
    xs, ys = np.asarray(c['ic']), np.asarray(c['cagr_real'])
    if y <= ys[0]:
        return float('-inf') if y < ys[0] - 1e-9 else 0.0
    for i in range(1, len(xs)):
        if ys[i] >= y:
            return float(xs[i - 1] + (xs[i] - xs[i - 1]) * (y - ys[i - 1]) / (ys[i] - ys[i - 1]))
    return float(xs[-1])


out = {'variants': {}}
for vid in json.load(open(sys.argv[3])):
    v = VAR[vid]
    sc, g = score(v)
    pk = M.top_picks(sc, 50, rows=rs)
    tg = LB.targets_from_picks(P, d, pk, v['K'], rb=v['Rb'], gate=g)
    rw = LB.aftertax_rows(P, tg)
    icx = M.ic_series(d, sc, RR)
    def st(a, b):
        x = icx[a:b]; x = x[np.isfinite(x)]
        return dict(mean=float(x.mean()), t=float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))), n=int(len(x)))
    rw['ic_disc'] = st(j86, j00); rw['ic_conf'] = st(j00, d.nd)
    rw['ic_eq_ws1'] = ic_eq(v['K'], rw['cons'])
    s = LB.stream(P, tg)
    np.savez(f'{M.SCR}/stream_v{vid}.npz', dates=np.array(s['dates']), ret=np.array(s['ret']), q=np.array(s['basis_add']),
             turnover=s['turnover'])
    # link-coverage stress: unlinked eligible names get a score drawn from that decision's score distribution
    rng = np.random.default_rng(99)
    sr_ = sc.copy()
    for j in rows:
        f = sc[j][np.isfinite(sc[j])]
        u = d.elig[j] & ~d.linked[j] & ~np.isfinite(sc[j])
        if v['CF']:
            u &= ~d.crash[j]
        if len(f) and u.any():
            sr_[j, u] = rng.choice(f, u.sum())
    tg2 = LB.targets_from_picks(P, d, M.top_picks(sr_, 50, rows=rs), v['K'], rb=v['Rb'], gate=g)
    rw['stress_unlinked_random'] = LB.aftertax_rows(P, tg2)['cons']
    out['variants'][str(vid)] = dict(var=v, **{k: (x if not isinstance(x, (np.floating,)) else float(x)) for k, x in rw.items()})
    print(vid, v, json.dumps(out['variants'][str(vid)], default=float)[:900], flush=True)
# EW of linked names vs all (link bias)
pkl = np.full((d.nd, d.N), -1, np.int64)
for j in rows:
    c_ = np.flatnonzero(d.elig[j] & d.linked[j]); pkl[j, :len(c_)] = c_
tgl = LB.targets_from_picks(P, d, pkl, 1, rb='M')
tgl.wts = [np.full(len(p), 1.0 / max(len(p), 1)) for p in tgl.picks]
out['ew_linked_cons'] = stocks.run1(P, tgl, stocks.H_CONS, pd.Timestamp('1986-01-02'), 0.003, 0.22, 2)['cagr_at']
out['ew_all_cons'] = stocks.ew_row(P, stocks.H_CONS, pd.Timestamp('1986-01-02'), 0.003, 0.22, 2)['cagr_at']
# confirmation-period composite IC (after the selection was locked)
icc = {}
for name in ['ALL'] + M.GNAMES + ['CLEAR', 'TOPT']:
    r = {}
    for wk in ('EQ', 'ICW', 'RIDGE'):
        sc = M.composite(d, M.weights(d, sub[name], wk, None if wk == 'EQ' else est_U, rows=rows), rs)
        x = M.ic_series(d, sc, RR)
        for nm, (a, b) in dict(disc=(j86, j00), conf=(j00, d.nd)).items():
            y = x[a:b]; y = y[np.isfinite(y)]
            r[f'{wk}_{nm}'] = dict(mean=round(float(y.mean()), 4), t=round(float(y.mean() / y.std(ddof=1) * np.sqrt(len(y))), 2), n=int(len(y)))
    icc[name] = r
    print('IC', name, r, flush=True)
out['composite_ic'] = icc
json.dump(out, open(sys.argv[2], 'w'), indent=1, default=float)
