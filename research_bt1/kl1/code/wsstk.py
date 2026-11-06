"""WS1 A2/B: stock top-K engine on real cross-sections (<=2014). Blocks of h days, decision at close t_b,
entry at close t_b+1, planned exit at close t_b+1+h (KR: delayed by halts / limit-down; entry fails at limit-up).
Costs: US 0.3%/side; KR commission 0.015% + half-spread + impact (+0.3% sell tax). Tax: US 22% yearly (all P&L
treated as realized), deduction 0.25 x start, final year taxed; KR 0 capital-gains tax."""
import numpy as np, pandas as pd
from numba import njit
from scipy.special import ndtri

TAX = 0.22
DED = 0.25


@njit(cache=True)
def _kr_window(idx, trade, limdn, listed, last_row, fail, t_dec, h, elig, reuse_row, fail1):
    nb = t_dec.shape[0]; T, N = idx.shape
    R = np.full((nb, N), np.nan); ok = np.zeros((nb, N), np.bool_)
    for b in range(nb):
        e0 = t_dec[b] + 1; e1 = e0 + h
        for i in range(N):
            if not elig[b, i]:
                continue
            if e0 >= T or not listed[e0, i]:
                continue
            p0 = idx[e0, i]
            if not (p0 > 0):
                continue
            j = e1
            while j < T and listed[j, i] and ((not trade[j, i]) or limdn[j, i]):
                j += 1
            if j < T and listed[j, i]:
                R[b, i] = idx[j, i] / p0 - 1
            else:
                sx = e0                                  # end of the listed run that holds the entry
                while sx + 1 < T and listed[sx + 1, i]:
                    sx += 1
                nxt = sx + 1
                while nxt < T and not listed[nxt, i]:
                    nxt += 1
                done = False
                if nxt < T and nxt != reuse_row[i]:      # data gap inside one spell (long halt): first tradable row after it
                    j2 = nxt
                    while j2 < T and listed[j2, i] and ((not trade[j2, i]) or limdn[j2, i]):
                        j2 += 1
                    if j2 < T and listed[j2, i]:
                        R[b, i] = idx[j2, i] / p0 - 1
                        done = True
                if not done:
                    if nxt < T and nxt == reuse_row[i]:  # spell ends, code reused later
                        L = sx; f = fail1[i]
                    else:
                        L = last_row[i]; f = fail[i]
                        if L < e0:
                            L = e0
                    if f and (not trade[L, i]) and L < T - 1:
                        R[b, i] = -1.0
                    else:
                        R[b, i] = idx[L, i] / p0 - 1
            ok[b, i] = True
    return R, ok


@njit(cache=True)
def _us_window(adj, t_dec, h, elig):
    nb = t_dec.shape[0]; T, N = adj.shape
    R = np.full((nb, N), np.nan); ok = np.zeros((nb, N), np.bool_)
    for b in range(nb):
        e0 = t_dec[b] + 1; e1 = e0 + h
        for i in range(N):
            if not elig[b, i]:
                continue
            p0 = adj[e0, i]
            if not (p0 > 0):
                continue
            if e1 < T and adj[e1, i] > 0:
                R[b, i] = adj[e1, i] / p0 - 1
            else:
                # price ended inside the window: last valid price, lab delisting rule
                L = e0
                for j in range(e0, min(e1, T)):
                    if adj[j, i] > 0:
                        L = j
                r_last = adj[L, i] / p0 - 1
                # 250-day return to last price
                k0 = L - 250
                if k0 < 0:
                    k0 = 0
                base = np.nan
                for j in range(k0, L):
                    if adj[j, i] > 0:
                        base = adj[j, i]
                        break
                if base > 0 and adj[L, i] / base - 1 < -0.30:
                    R[b, i] = (1 + r_last) * 0.5 - 1
                else:
                    R[b, i] = r_last
            ok[b, i] = True
    return R, ok


class Blocks:
    """per-universe, per-h block arrays: R [nb,N] window return (nan = not eligible), entry [nb,N] entry possible,
    cb/cs [nb,N] buy/sell cost fractions, years [nb] calendar year of exit, z [nb,N] normal score of R rank."""
    pass


def build_us(U, h, start='1971-01-01'):
    dates = U['dates']; adj = U['adj']; mem = U['member']
    T = len(dates)
    t0 = int(np.searchsorted(dates.values, np.datetime64(start)))
    t_dec = np.arange(t0, T - h - 1, h)
    elig = mem[t_dec] & (adj[t_dec] > 0) & (adj[t_dec + 1] > 0)
    R, ok = _us_window(adj, t_dec, h, elig)
    B = Blocks(); B.h = h; B.t_dec = t_dec; B.dates = dates[t_dec]; B.R = R; B.elig = ok & ~np.isnan(R)
    B.entry = B.elig.copy()
    B.years = pd.DatetimeIndex(dates[np.minimum(t_dec + 1 + h, T - 1)]).year.values
    B.tax = True; B.name = 'US500'
    _scores(B)
    return B


def build_kr(K, X, h, start='1999-01-01', seed_krw=1e7, Kslots=5, adv_min=1e8, fail_mode='conservative'):
    dates = pd.to_datetime(K['dates']); T, N = X['idx'].shape
    t0 = int(np.searchsorted(dates.values, np.datetime64(start)))
    t_dec = np.arange(t0, T - h - 1, h)
    elig = X['trade'][t_dec] & (X['age'][t_dec] >= 20) & (np.nan_to_num(X['adv20'][t_dec]) >= adv_min)
    listed = X['listed']
    last_row = np.where(listed.any(0), T - 1 - np.argmax(listed[::-1], axis=0), 0).astype(np.int64)
    import wsdata as _D
    fail, reuse_row, fail1 = _D.kr_spells(K, X, fail_mode)
    R, ok = _kr_window(X['idx'], X['trade'], X['limdn'], listed, last_row, fail, t_dec, h, elig, reuse_row, fail1)
    B = Blocks(); B.h = h; B.t_dec = t_dec; B.dates = dates[t_dec]; B.R = R; B.elig = ok & ~np.isnan(R)
    e0 = t_dec + 1
    B.entry = B.elig & X['trade'][e0] & ~X['limup'][e0]
    hs = X['hs'][t_dec]; s20 = np.nan_to_num(X['s20'][t_dec], nan=0.05); adv = np.maximum(np.nan_to_num(X['adv20'][t_dec], nan=1e8), 1e6)
    B.hs = hs; B.s20 = s20; B.adv = adv; B.seed_krw = seed_krw
    B.years = pd.DatetimeIndex(dates[np.minimum(t_dec + 1 + h, T - 1)]).year.values
    B.tax = False; B.name = 'KRALL'
    _scores(B)
    return B


def set_kr_cost(B, K):
    imp = 0.7 * B.s20 * np.sqrt((B.seed_krw / K) / B.adv)
    B.cb = 0.00015 + B.hs + imp
    B.cs = 0.00015 + B.hs + imp + 0.003


def _scores(B):
    """normal scores of window-return ranks among eligible names per block"""
    R = np.where(B.elig, B.R, np.nan)
    n = B.elig.sum(1)
    order = np.argsort(np.where(B.elig, R, np.inf), axis=1, kind='stable')
    rk = np.empty_like(order); rows = np.arange(R.shape[0])[:, None]
    rk[rows, order] = np.arange(R.shape[1])[None, :]
    u = (rk + 0.5) / np.maximum(n, 1)[:, None]
    z = ndtri(np.clip(u, 1e-9, 1 - 1e-9))
    B.z = np.where(B.elig, z, np.nan); B.n = n
    B.rk = np.where(B.elig, rk, -1)


@njit(cache=True)
def _run_picks(R, entry, hs, s20, adv, kr, q, picks):
    nb, K = picks.shape
    r = np.zeros(nb); g = np.zeros(nb); cst = np.zeros(nb)
    hp = np.full(K, -1, np.int64); hcs = np.zeros(K); nh = 0
    for b in range(nb):
        nn = 0; gr = 0.0; c = 0.0
        newh = np.full(K, -1, np.int64); ncs = np.zeros(K)
        for k in range(K):
            i = picks[b, k]
            if i < 0:
                continue
            cont = False
            for m in range(nh):
                if hp[m] == i:
                    cont = True
            if kr:
                cb = 0.00015 + hs[b, i] + 0.7 * s20[b, i] * np.sqrt(q / adv[b, i])
                csl = cb + 0.003
            else:
                cb = 0.003; csl = 0.003
            if cont or entry[b, i]:
                if not cont:
                    c += cb
                v = R[b, i]
                if v == v:
                    gr += v
                newh[nn] = i; ncs[nn] = csl; nn += 1
        for m in range(nh):
            still = False
            for k in range(nn):
                if newh[k] == hp[m]:
                    still = True
            if not still:
                c += hcs[m]
        r[b] = (gr - c) / K; g[b] = gr / K; cst[b] = c / K
        hp = newh; hcs = ncs; nh = nn
    for m in range(nh):
        r[nb - 1] -= hcs[m] / K
    return r, g, cst


def run_picks(B, picks):
    """picks [nb, K] int (-1 = empty slot). returns per-block net returns r [nb], gross, cost."""
    K = picks.shape[1]
    if B.name == 'KRALL':
        return _run_picks(B.R, B.entry, B.hs, B.s20, B.adv, True, B.seed_krw / K, np.ascontiguousarray(picks))
    z = np.zeros((1, 1))
    return _run_picks(B.R, B.entry, z, z, z, False, 0.0, np.ascontiguousarray(picks))


def perf(B, r, paths=500, seed=11):
    """real-path after-tax CAGR and 30y resampled median (chunks of ~250 trading days)."""
    years_total = len(r) * B.h / 252.0
    E = 1.0; pnl_y = 0.0; cy = B.years[0]
    for b in range(len(r)):
        if B.years[b] != cy:
            if B.tax:
                tx = TAX * max(0.0, pnl_y - DED); E -= tx
            pnl_y = 0.0; cy = B.years[b]
        d = E * r[b]; E += d; pnl_y += d
        if E <= 1e-9:
            E = 1e-9; break
    if B.tax:
        E -= TAX * max(0.0, pnl_y - DED)
    real = max(E, 1e-9) ** (1 / years_total) - 1
    # resample: chunk = ceil(250/h) consecutive blocks
    cl = max(1, int(round(250 / B.h)))
    nch = len(r) // cl
    lg = np.log1p(np.maximum(r[:nch * cl], -0.999999)).reshape(nch, cl)
    chunk_g = np.exp(lg.sum(1)) - 1                  # chunk gross growth (pre-tax)
    rng = np.random.default_rng(seed)
    yrs_chunk = cl * B.h / 252.0
    ny = int(np.ceil(30 / yrs_chunk))
    pick = rng.integers(0, nch, (paths, ny))
    E = np.ones(paths)
    for k in range(ny):
        gch = chunk_g[pick[:, k]]
        gain = E * gch
        if B.tax:
            gain = gain - TAX * np.maximum(gain - DED, 0)
        E = np.maximum(E + gain, 1e-9)
    res = E ** (1 / (ny * yrs_chunk)) - 1
    return float(real), float(np.median(res)), float(np.percentile(res, 10))


def topk_from_signal(s, Kmax):
    """s [nb, N] with nan for ineligible -> picks [nb, Kmax] sorted by s desc (-1 if fewer eligible)."""
    ss = np.where(np.isnan(s), -np.inf, s)
    part = np.argpartition(-ss, Kmax - 1, axis=1)[:, :Kmax]
    vals = np.take_along_axis(ss, part, 1)
    o = np.argsort(-vals, axis=1)
    pk = np.take_along_axis(part, o, 1)
    v = np.take_along_axis(vals, o, 1)
    pk[~np.isfinite(v)] = -1
    return pk


def spearman_ic(B, s):
    """mean cross-sectional Spearman between s and window return over blocks (eligible names)."""
    ss = np.where(B.elig & ~np.isnan(s), s, np.nan)
    ok = ~np.isnan(ss)
    ics = []
    for b in range(ss.shape[0]):
        m = ok[b]
        if m.sum() < 10:
            continue
        a = ss[b, m]; c = B.rk[b, m]
        ra = np.argsort(np.argsort(a)); rc = np.argsort(np.argsort(c))
        ics.append(np.corrcoef(ra, rc)[0, 1])
    ics = np.array(ics)
    return float(np.mean(ics)), float(np.mean(ics) / (np.std(ics) / np.sqrt(len(ics)) + 1e-12)), len(ics)


@njit(cache=True)
def picks_o2(top, elig, K, p, seed):
    """each slot: prob p from top set, else from eligible-not-top; without replacement."""
    np.random.seed(seed)
    nb, N = top.shape
    out = np.full((nb, K), -1, np.int64)
    ti = np.empty(N, np.int64); ri = np.empty(N, np.int64)
    for b in range(nb):
        nt = 0; nr = 0
        for i in range(N):
            if top[b, i]:
                ti[nt] = i; nt += 1
            elif elig[b, i]:
                ri[nr] = i; nr += 1
        for k in range(K):
            if np.random.random() < p and nt > 0:
                j = np.random.randint(nt); out[b, k] = ti[j]; ti[j] = ti[nt - 1]; nt -= 1
            elif nr > 0:
                j = np.random.randint(nr); out[b, k] = ri[j]; ri[j] = ri[nr - 1]; nr -= 1
            elif nt > 0:
                j = np.random.randint(nt); out[b, k] = ti[j]; ti[j] = ti[nt - 1]; nt -= 1
    return out
