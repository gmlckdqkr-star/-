"""MC1 W3 library: custom cross-stock scores (peer / leader structure) -> lab Targets -> the lab stock engine
(lab.stocks.run1 / fast_run / null_baskets, lab.ms1.measure_series), plus the s0.85 correlation and the combo engine.
lab code is imported, never changed. Leak rules as lab: no price level, dvol, dividends, stale, symbols or first-price
dates in any decision; per-stock windows read returns after the window floor only (P.wfloor), <= 260 rows.
Decision row t reads panel rows <= t only (checked by cut()). Every number <= 2014-12-31."""
import sys, os, json, math, time
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/lab')
from lab import stocks, dsl, data, ms1

W3 = '/mnt/project-files/research/multi_cand/w3_stock_new'
SCR = '/tmp/claude-0/-home-user--/b4e475e4-5d2e-5ae5-bb04-11baf8b49e55/scratchpad/w3'
COST, DELAY, TAX = 0.003, 2, 0.22
WIN = 252          # correlation / eligibility window (rows of returns)
NPEER = 10
_P = None


def panel():
    global _P
    if _P is None:
        _P = stocks.load()
    return _P


def ndx_ret(idx):
    """lab _NDX close-to-close return on the stock calendar (ffill, NaN before 1985-10), cut at 2014-12-31."""
    s = data.series('_NDX'); s = s[s.index <= stocks.DEV_END]
    L = s.reindex(idx).ffill()
    return (L / L.shift(1) - 1.0).values


def elig_at(P, t):
    """Members with a price at t whose full WIN-row return window lies after the window floor."""
    return P.member[t] & P.has[t] & (t - P.wfloor >= WIN)


def own_ret(P, t, n, skip=0):
    Pp = P.P
    a, b = t - skip, t - skip - n
    with np.errstate(invalid='ignore', divide='ignore'):
        return Pp[a] / Pp[b] - 1.0


def peers(P, t, cols):
    """Top-NPEER most correlated other eligible names (WIN rows ending at t) for each of cols -> [n, NPEER] idx into cols."""
    X = P.rr[t - WIN + 1:t + 1][:, cols]
    X = X - X.mean(0); sd = X.std(0); sd[sd < 1e-12] = np.inf
    Z = X / sd
    C = Z.T @ Z / WIN
    np.fill_diagonal(C, -np.inf)
    k = min(NPEER, len(cols) - 1)
    return np.argpartition(-C, k - 1, axis=1)[:, :k]


def leaders(P, t, cols, nw=52, k=NPEER):
    """Leaders of each name: top-k corr(w_i[w], w_j[w-1]) over the last nw non-overlapping 5-row weeks ending at t."""
    rows = t - 5 * (nw + 1) + 1
    lr = np.log1p(P.rr[rows:t + 1][:, cols])                  # (5*(nw+1), n)
    W = lr.reshape(nw + 1, 5, -1).sum(1)                      # weekly log returns, oldest first
    F, L = W[1:], W[:-1]                                      # follower week w, leader week w-1
    F = F - F.mean(0); L = L - L.mean(0)
    sf, sl = F.std(0), L.std(0); sf[sf < 1e-12] = np.inf; sl[sl < 1e-12] = np.inf
    C = (F / sf).T @ (L / sl) / nw                            # C[i, j] = corr(follower i, lagged leader j)
    np.fill_diagonal(C, -np.inf)
    return np.argpartition(-C, k - 1, axis=1)[:, :k]


def ndx_corr(P, t, cols, nr):
    m = nr[t - WIN + 1:t + 1]
    if not np.all(np.isfinite(m)):
        return np.full(len(cols), np.nan)
    X = P.rr[t - WIN + 1:t + 1][:, cols]
    X = X - X.mean(0); mm = m - m.mean()
    sd = X.std(0) * mm.std(); sd[sd < 1e-15] = np.nan
    return (X * mm[:, None]).mean(0) / sd


def score_fn(kind):
    """kind -> f(P, t, cols, nr) -> (score [n], filter [n] bool)."""
    def f(P, t, cols, nr):
        n = len(cols); ok = np.ones(n, bool)
        if kind in ('H1', 'H8'):
            r = own_ret(P, t, 21)[cols]; pe = peers(P, t, cols)
            s = -(r - r[pe].mean(1))
            if kind == 'H8':
                c = ndx_corr(P, t, cols, nr)
                if not np.isfinite(c).any():
                    return s, np.zeros(n, bool)
                ok = c < np.nanmedian(c)
            return s, ok
        if kind == 'H2':
            r = own_ret(P, t, 231, 21)[cols]; pe = peers(P, t, cols)
            return r[pe].mean(1), ok
        if kind == 'H7':
            r = own_ret(P, t, 231, 21)[cols]; pe = peers(P, t, cols)
            return -(r - r[pe].mean(1)), ok
        if kind == 'H3':
            r = own_ret(P, t, 10)[cols]; ld = leaders(P, t, cols)
            return r[ld].mean(1), ok
        if kind == 'H5':
            c = ndx_corr(P, t, cols, nr)
            return -c, np.isfinite(c)
        raise KeyError(kind)
    return f


def targets(P, kind, cad='monthly', top=30, upto=None, nr=None, want_scores=False):
    """lab Targets for a custom score. upto: only decisions on rows < upto (cut check)."""
    D = np.flatnonzero(dsl.reb_rows(P.idx, cad))
    D = D[D >= P.f0]
    if upto is not None:
        D = D[D < upto]
    nr = ndx_ret(P.idx) if nr is None else nr
    f = score_fn(kind)
    picks, wts, Ks, ties, units = [], [], [], np.zeros(len(D), bool), np.zeros(len(D))
    elig = np.zeros((len(D), P.N), bool)
    S_all = {}
    for j, t in enumerate(D):
        E = elig_at(P, t)
        cols = np.flatnonzero(E)
        Sx = np.full(P.N, -np.inf)
        if len(cols) > NPEER + 1:
            s, ok = f(P, t, cols, nr)
            good = ok & np.isfinite(s)
            Sx[cols[good]] = s[good]
            elig[j, cols[good]] = True
            if want_scores:
                S_all[t] = (cols[good], s[good])
        m = int(np.isfinite(Sx).sum())
        n = min(top, m)
        p, fr, ties[j] = stocks.top_k(Sx, n)
        w = fr / top
        units[j] = n / top / len(p) if len(p) else 1.0 / top
        picks.append(p.astype(np.int64)); wts.append(w); Ks.append(top)
    tg = stocks.Targets(D, picks, wts, np.array(Ks), elig, np.ones(P.T), {}, None, None, (), ties, units)
    return (tg, S_all) if want_scores else tg


def first_start(P, tg):
    j = next((j for j in range(len(tg.dec)) if len(tg.picks[j])), None)
    return None if j is None else stocks.gate_start(P, int(tg.dec[j]), DELAY)


def sharpe_E(E, P):
    r = E.pct_change().dropna()
    rf = pd.Series(stocks.rf_on(P.idx), index=P.idx).reindex(r.index).values
    ex = r.values - rf
    return float(ex.mean() / ex.std(ddof=1) * np.sqrt(252))


def stream(P, tg, st):
    """MS1 input (as lab stocks.ms1_stream): conservative book after cost and dividend tax, before 22%."""
    o = stocks.fast_run(P, tg, stocks.H_CONS, st, COST, 0.0, DELAY, want_E=True, dtax=stocks.DIV_TAX)
    E = o['E'][0]
    r = E[1:] / E[:-1] - 1.0
    q = np.where(E[:-1] > 0, o['dnet'][0][1:] / np.where(E[:-1] > 0, E[:-1], 1.0), 0.0)
    return pd.DataFrame(dict(r=r, q=q), index=o['idx'][1:]), min(1.0, float(o['turn'][0]) / 2.0)


def evaluate(P, tg, name, null=True):
    """lab-like headline rows for a Targets object."""
    t0 = time.time()
    st86 = max(pd.Timestamp('1986-01-02'), first_start(P, tg))
    cons = stocks.run1(P, tg, stocks.H_CONS, st86, COST, TAX, DELAY, ends=True)
    base = stocks.run1(P, tg, 0.0, st86, COST, TAX, DELAY)
    all30 = stocks.run1(P, tg, stocks.H_ALL, st86, COST, TAX, DELAY)
    pre = stocks.run1(P, tg, stocks.H_CONS, st86, COST, 0.0, DELAY, dtax=0.0)
    ew = stocks.ew_row(P, stocks.H_CONS, st86, COST, TAX, DELAY)
    ndx = stocks.ndx_hold(st86, COST, TAX, DELAY)
    out = dict(name=name, start86=str(st86.date()), cons_cagr_at=cons['cagr_at'], base_cagr_at=base['cagr_at'],
               all30_cagr_at=all30['cagr_at'], mdd=cons['mdd'], turn=cons['turn'], held_ends=cons['ends'],
               pretax_cagr=pre['cagr_at'], sharpe_pretax=stocks.sharpe(pre, P), sharpe_aftertax=sharpe_E(cons['E'], P),
               ew_cagr_at=ew['cagr_at'], ndx_cagr_at=ndx['cagr_at'],
               avg_names=stocks.avg_names(P, tg, st86, DELAY), ties=stocks.tie_count(P, tg, st86, DELAY))
    st71 = max(pd.Timestamp('1971-01-04'), first_start(P, tg))
    out['start71'] = str(st71.date())
    out['cons71_cagr_at'] = stocks.run1(P, tg, stocks.H_CONS, st71, COST, TAX, DELAY)['cagr_at']
    if null:
        nb = stocks.null_baskets(P, tg, st86, DELAY)
        nr_ = stocks.fast_run(P, tg, stocks.H_CONS, st86, COST, TAX, DELAY, baskets=nb, D=stocks.N_NULL)
        x = np.sort(nr_['cagr_at']); s = out['cons_cagr_at']
        out['null'] = dict(top=float(1 - (np.mean(x < s) + 0.5 * np.mean(x == s))), median=float(np.median(x)),
                           p95=float(np.percentile(x, 95)), p99=float(np.percentile(x, 99)))
    sts = max(stocks.MS1_FROM, first_start(P, tg))
    S, share = stream(P, tg, sts)
    out['stream_start'] = str(S.index[0].date()); out['turnover_share'] = share
    m = ms1.measure_series(S.index, S['r'].values, name, turnover=share, min_cover=0.95, basis_add=S['q'].values)
    out['ms1'] = m
    out['elapsed_s'] = round(time.time() - t0, 1)
    return out, S, share


# ------------------------------------------------------------------ s0.85 correlation and combos
_S85 = None


def s085():
    global _S85
    if _S85 is None:
        _S85 = dict(np.load(os.path.join(SCR, 's085.npz')))
    return _S85


def on_source(S, bn):
    """Stock stream -> source-day returns / basis_add on the basis calendar (as lab ms1.series), [len(src)]."""
    z = s085()
    src = pd.DatetimeIndex(z[bn + '_srcdates'].astype('datetime64[D]'))
    s = S['r']
    lvl = (1.0 + s).cumprod()
    cc = (S['q'] * lvl.shift(1).fillna(1.0)).cumsum()
    L = lvl.reindex(src, method='ffill')
    v = np.array(L / L.shift(1).fillna(1.0) - 1.0, float); v[0] = 0.0
    have = np.asarray((src >= s.index[0]) & (src <= s.index[-1]))
    v = np.where(have, np.nan_to_num(v), 0.0)
    C = cc.reindex(src, method='ffill').fillna(0.0)
    qv = np.array((C - C.shift(1).fillna(0.0)) / L.shift(1).fillna(1.0), float); qv[0] = 0.0
    qv = np.where(have, np.nan_to_num(qv), 0.0)
    return v, qv, have


def corr_s085(S):
    z = s085(); bn = 'real_ndx_86_14'
    v, _, have = on_source(S, bn)
    ii = z[bn + '_ii'][0]
    x = z[bn + '_r'][0]; y = v[ii]; h = have[ii]
    inv = ~z[bn + '_cash'][0]
    ndx = z[bn + '_ndx'][0]
    c = lambda a, b: float(np.corrcoef(a, b)[0, 1])
    return dict(corr_all=c(x[h], y[h]), corr_s085_invested=c(x[h & inv], y[h & inv]),
                corr_s085_cash_days=c(x[h & ~inv], y[h & ~inv]) if (h & ~inv).sum() > 50 else None,
                corr_ndx=c(ndx[h], y[h]), cover=float(h.mean()), n=int(h.sum()))


SHARE_S = 0.6     # calibrated: same-engine s0.85 100% = 16.21 path / 31.04 real (std 16.16 / 31.08)


def mix_run(rs, rk, qk, wk, share_k, cost=COST, tax=TAX, D=0.25, rebal=252, share_s=None):
    """Two-sleeve account on P paths (rows): s0.85 pre-tax stream rs (its trading cost inside, every year's gain
    realized) + stock stream rk (after cost and dividend tax; qk = reinvested taxed dividends -> basis) at weights
    (1 - wk, wk), re-balanced every `rebal` rows; tax every 252 rows: 22% x max(realized - D, 0), no carry-forward;
    realized = s0.85 sleeve's gain + share_k x stock unrealized + gains realized by the re-balancing sale. Entry /
    exit cost on the stock sleeve, liquidation tax at the end. -> (cagr [P], E [P, T])."""
    share_s = SHARE_S if share_s is None else share_s
    Pn, T = rs.shape
    Ws = np.full(Pn, 1.0 - wk); Wk = np.full(Pn, wk * (1 - cost))
    Bs = Ws.copy(); Bk = Wk.copy()
    E = np.zeros((Pn, T))
    for t in range(T):
        Bk = Bk + Wk * qk[:, t]
        Ws = Ws * (1 + rs[:, t]); Wk = Wk * (1 + rk[:, t])
        if (t + 1) % 252 == 0 and t + 1 < T:
            g = share_s * (Ws - Bs); Bs = Bs + g
            Rz = share_k * (Wk - Bk); Bk = Bk + Rz
            tot = Ws + Wk
            if wk > 0:
                tgt = wk * tot; sell = np.maximum(Wk - tgt, 0.0)               # stock sleeve sale realizes gains
                frac = np.where(Wk > 0, sell / np.maximum(Wk, 1e-300), 0.0)
                gr = frac * (Wk - Bk)
                Bk = Bk * (1 - frac) + 0.0; Wk = Wk - sell
                buy = np.maximum(tgt - (Wk), 0.0)                          # buy stock from s0.85 sleeve
                Ws = Ws + sell - buy; Bs = Bs + sell - buy
                Wk = Wk + buy * (1 - cost); Bk = Bk + buy * (1 - cost)
                Ws = Ws - cost * sell                                      # sale cost
                Bs = Bs - cost * sell
            else:
                gr = 0.0
            due = tax * np.maximum(g + Rz + gr - D, 0.0)
            tot = Ws + Wk
            f = np.minimum(due / np.maximum(tot, 1e-300), 1.0)
            Ws = Ws * (1 - f); Bs = Bs * (1 - f); Wk = Wk * (1 - f); Bk = Bk * (1 - f)
        E[:, t] = Ws + Wk
    fin_k = Wk * (1 - cost)
    unreal = (Ws - Bs) + (fin_k - Bk)
    fin = Ws + fin_k - tax * np.maximum(unreal - D, 0.0)
    yrs = T / 252
    return np.maximum(fin, 1e-9) ** (1 / yrs) - 1, E


def combos(S, share, weights=(0.0, 0.2, 0.3)):
    z = s085(); out = {}
    for bn in ('real_ndx_86_14', 'dev250_path'):
        v, qv, have = on_source(S, bn)
        ii = z[bn + '_ii']
        rk, qk = v[ii], qv[ii]
        cov = float(have[ii].mean())
        rs = z[bn + '_r']
        res = {}
        for wk in weights:
            f, E = mix_run(rs, rk, qk, wk, share)
            res[wk] = f
        base = res[0.0]
        row = dict(cover=cov, s085_same_engine=float(np.median(base)))
        for wk in weights[1:]:
            d = res[wk] - base
            mdd = lambda E: np.min(E / np.maximum.accumulate(E, 1), 1) - 1
            row[f'w{int(wk * 100)}'] = dict(cagr=float(np.median(res[wk])), d=float(np.median(d)),
                                             pw=float(np.mean(d > 1e-5)))
        out[bn] = row
    return out


def filler(S, share=1.0):
    """H4: s0.85 with its cash days replaced by the stock stream (0.3% each switch in / out), same mix engine."""
    z = s085(); out = {}
    for bn in ('real_ndx_86_14', 'dev250_path'):
        v, qv, have = on_source(S, bn)
        ii = z[bn + '_ii']; rk = v[ii]; qk = qv[ii]
        cash = z[bn + '_cash'] & have[ii]
        rs = z[bn + '_r']
        sw = np.zeros_like(cash); sw[:, 1:] = cash[:, 1:] != cash[:, :-1]
        rmod = np.where(cash, rk, rs) - COST * sw
        f0, _ = mix_run(rs, rk, qk, 0.0, 1.0)
        f1, _ = mix_run(rmod, rk, np.zeros_like(qk), 0.0, 1.0)
        d = f1 - f0
        out[bn] = dict(base=float(np.median(f0)), filled=float(np.median(f1)), d=float(np.median(d)),
                       pw=float(np.mean(d > 1e-5)), cash_share=float(cash.mean()), cover=float(have[ii].mean()))
    return out


def ic(P, S_all, h=21):
    """Mean cross-sectional Spearman IC of the score at t vs the return from close t+2 to close t+2+h (after the
    2-day delay), over decisions 1986..2014 whose window ends <= the panel end."""
    Pp = P.P; vals = []
    for t, (cols, s) in S_all.items():
        if P.idx[t] < pd.Timestamp('1986-01-02') or t + 2 + h >= P.T:
            continue
        with np.errstate(invalid='ignore', divide='ignore'):
            fr = Pp[t + 2 + h, cols] / Pp[t + 2, cols] - 1.0
        ok = np.isfinite(fr) & np.isfinite(s)
        if ok.sum() < 30:
            continue
        a = pd.Series(s[ok]).rank().values; b = pd.Series(fr[ok]).rank().values
        vals.append(np.corrcoef(a, b)[0, 1])
    vals = np.array(vals)
    return dict(ic_mean=float(vals.mean()), ic_t=float(vals.mean() / vals.std(ddof=1) * np.sqrt(len(vals))),
                n=int(len(vals)), note='ret from t+2 close: survivors only (no delisting return), diagnostic')


def cut_check(P, kind, cad, top, cuts=(0.35, 0.6, 0.85)):
    """Recompute the targets on panels cut at 3 rows (rows < c only) and compare every decision before c."""
    full = targets(P, kind, cad, top)
    res = []
    for fc in cuts:
        c = int(P.f0 + fc * (P.T - P.f0))
        Pc = P.cut(c)
        tc = targets(Pc, kind, cad, top, nr=ndx_ret(P.idx)[:c])
        n = len(tc.dec); same = True
        for j in range(max(0, n - 24), n):
            if not (np.array_equal(tc.picks[j], full.picks[j]) and np.allclose(tc.wts[j], full.wts[j])):
                same = False
        res.append(dict(cut=str(P.idx[c].date()), decisions=n, same=same))
    return dict(ok=all(r['same'] for r in res), cuts=res)
