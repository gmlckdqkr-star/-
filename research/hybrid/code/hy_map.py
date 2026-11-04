"""PRECOMMIT_HY1 section 5 (E): strengths / weaknesses map (descriptive, not trials). Data <= 2014-12-31.
  A. standalone MS1 rows (5 bases) for s0.85 and the 24 I_INTEGRATE streams: CAGR (median), MDD, -80% share, Sharpe
  B. real-path era splits from the standalone equity curves: 1955-69, 1970-85 (real S&P basis), 1986-99, 2000-14 (real NDX basis)
  C. regime-conditional 21-day block returns (days k+3..k+23, pre-tax sleeve returns) vs the s0.85 sleeve, two real eras
     states at close k: index above/below 210-day mean, 21-day vol above expanding 80th pct, 10y rate 252-day change > 0,
     10y < bill (inversion), index < -15% from its 252-day high, s0.85 held level (>= 2.5 / between / 0)
  D. block-return correlation with the s0.85 sleeve and co-drawdown (stream return in the s0.85 worst 10% blocks)
Output results/map_le2014.json"""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import hy_common as C, hyeng as H, ii, el, sl

OUT = '/mnt/project-files/research/hybrid/results/map_le2014.json'
BASES = ['dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85']
ERAS = {'real_spx_55_85': [('1955-69', '1955-01-01', '1969-12-31'), ('1970-85', '1970-01-01', '1985-12-31')],
        'real_ndx_86_14': [('1986-99', '1986-01-01', '1999-12-31'), ('2000-14', '2000-01-01', '2014-12-31')]}


def exp_pct(x, q):
    """expanding percentile of x using values up to and including t (NaN before 63 obs); same as hy_info.exp_pct"""
    import bisect
    out = np.full(x.shape, np.nan); v = []
    for t in range(len(x)):
        if np.isfinite(x[t]): bisect.insort(v, x[t])
        if len(v) >= 63: out[t] = v[min(int(q * (len(v) - 1)), len(v) - 1)]
    return out


def dates_of(bn):
    c = el.ctx(bn); S = sl.src()
    full = np.asarray(S['dates'])[c['off'] + np.asarray(c['ii'])[0]]
    return full[H.WARM:], full


def part_a(res):
    for bn in BASES:
        t0 = time.time()
        fin, E = ii.run(bn, 1.0, {})
        r = ii.stats(bn, fin, E); res['A|%s|S085' % bn] = {k: float(v) for k, v in r.items() if k in ('cagr', 'mdd', 'dd80', 'SR_c', 'p10')}
        if bn in ERAS: res['_E|%s|S085' % bn] = E[0]
        for s in ii.SID:
            fin, E = ii.run(bn, 0.0, {s: 1.0})
            r = ii.stats(bn, fin, E); res['A|%s|%s' % (bn, s)] = {k: float(v) for k, v in r.items() if k in ('cagr', 'mdd', 'dd80', 'SR_c', 'p10')}
            if bn in ERAS: res['_E|%s|%s' % (bn, s)] = E[0]
        print('A', bn, round(time.time() - t0, 1), flush=True)


def part_b(res):
    for bn, eras in ERAS.items():
        d, _ = dates_of(bn)
        for s in ['S085'] + ii.SID:
            e = res['_E|%s|%s' % (bn, s)]
            for nm, a, b in eras:
                m = (d >= np.datetime64(a)) & (d <= np.datetime64(b)); ix = np.where(m)[0]
                if len(ix) < 2: continue
                i0 = max(ix[0] - 1, 0); i1 = ix[-1]
                yrs = (i1 - i0) / 252.0; seg = e[i0:i1 + 1]
                g = (seg[-1] / seg[0]) ** (1 / yrs) - 1; mdd = float(np.min(seg / np.maximum.accumulate(seg) - 1))
                res['B|%s|%s' % (nm, s)] = dict(cagr=float(g), mdd=mdd)


def states(bn, T):
    c = el.ctx(bn)
    rfull = np.asarray(c['r'])[0]; lvl = np.cumprod(1 + rfull)
    I = sl.inputs(np.asarray(c['ii']), c['off']); y10 = np.asarray(I['y10'][0]); rf = np.asarray(c['rf'])[0] * 252
    n = len(rfull)
    sma = np.full(n, np.nan); cs = np.r_[0, np.cumsum(lvl)]
    for t in range(209, n): sma[t] = (cs[t + 1] - cs[t - 209]) / 210
    hi252 = np.array([lvl[max(t - 251, 0):t + 1].max() for t in range(n)])
    lr = np.log1p(rfull); vol21 = np.full(n, np.nan); c1 = np.r_[0, np.cumsum(lr)]; c2 = np.r_[0, np.cumsum(lr * lr)]
    for t in range(21, n):
        m = (c1[t + 1] - c1[t - 20]) / 21; vol21[t] = np.sqrt(max((c2[t + 1] - c2[t - 20]) / 21 - m * m, 0) * 252)
    v80 = exp_pct(vol21, 0.8)
    ch = np.r_[np.full(252, np.nan), y10[252:] - y10[:-252]]
    sh = lambda a: a[H.WARM:H.WARM + T]
    _, _, CU, _ = H.ref(bn)
    return dict(above10m=sh(lvl > sma), vol_hi=sh(vol21 > v80), rate_up=sh(ch > 0), inverted=sh(y10 < rf),
                dd15=sh(lvl / hi252 - 1 < -0.15), lvl_full=CU[0] >= 2.5, lvl_zero=CU[0] <= 0)


def part_cd(res):
    for bn in ERAS:
        R = C.sleeve_returns(bn, ii.SID)[0]; T, M = R.shape
        f, _ = C.block_logsum(R[None]); ks = C.block_starts(T, 252)
        G = np.stack([f(k)[0] for k in ks]); st = states(bn, T)
        X = G[:, 1:] - G[:, :1]
        for nm, flag in st.items():
            fl = np.asarray(flag)[ks].astype(bool)
            for val, sel in ((1, fl), (0, ~fl)):
                if sel.sum() < 5: continue
                res['C|%s|%s=%d' % (bn, nm, val)] = dict(n=int(sel.sum()), s085=float(G[sel, 0].mean()),
                                                         ex={s: float(X[sel, j].mean()) for j, s in enumerate(ii.SID)},
                                                         beat={s: float((X[sel, j] > 0).mean()) for j, s in enumerate(ii.SID)})
        worst = G[:, 0] <= np.quantile(G[:, 0], 0.10)
        res['D|%s' % bn] = dict(corr={s: float(np.corrcoef(G[:, 0], G[:, j + 1])[0, 1]) for j, s in enumerate(ii.SID)},
                                worst_n=int(worst.sum()), worst_s085=float(G[worst, 0].mean()),
                                worst_mean={s: float(G[worst, j + 1].mean()) for j, s in enumerate(ii.SID)},
                                worst_pos={s: float((G[worst, j + 1] > 0).mean()) for j, s in enumerate(ii.SID)})
        print('CD', bn, flush=True)


if __name__ == '__main__':
    res = {}
    part_a(res); part_b(res); part_cd(res)
    json.dump({k: v for k, v in res.items() if not k.startswith('_E|')}, open(OUT, 'w'), indent=1)
    print('done')
