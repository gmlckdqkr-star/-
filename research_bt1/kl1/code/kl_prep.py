"""KL1 preparation (no performance numbers): loser definitions, block arrays for S1/S3 (SELECTION blocks only),
daily aggregate features and expanding past-only percentile atoms for S2, KR200 proxy + KR products.
Writes caches to CACHE (session scratchpad). Prints only data checks (shapes, coverage, proxy-vs-069500 correlation)."""
import os, sys, io, lzma, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/kl/nb')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wsdata as D, wsstk as S, kl_sig as SG
from numba import njit

CACHE = D.CACHE
DELAY = 2
HS = (5, 21, 63)
SEL = {'KR': ('1999-01-04', '2008-12-31'), 'US': ('1971-01-04', '1999-12-31')}
CONF = {'KR': ('2009-01-02', '2014-12-31'), 'US': ('2000-01-03', '2014-12-31')}
KR_CD = {1998: 13.3, 1999: 6.0, 2000: 6.9, 2001: 5.4, 2002: 4.9, 2003: 4.3, 2004: 3.8, 2005: 3.6, 2006: 4.5, 2007: 5.2,
         2008: 5.5, 2009: 2.6, 2010: 2.7, 2011: 3.4, 2012: 3.3, 2013: 2.7, 2014: 2.5}   # approx. CD 91d annual avg (inferred)
DY = 0.015


@njit(cache=True)
def exp_pct(x, minobs):
    """expanding past-only percentile of x[t] among x[s], s < t (valid only); nan if fewer than minobs past values.
    Fenwick tree over the rank coordinates of x (coordinates only; counts use past values only)."""
    T = x.shape[0]
    out = np.full(T, np.nan)
    ok = ~np.isnan(x)
    vals = x[ok]
    if vals.shape[0] == 0:
        return out
    srt = np.sort(vals)
    M = srt.shape[0]
    tree = np.zeros(M + 1, np.int64)
    n = 0
    for t in range(T):
        if not ok[t]:
            continue
        v = x[t]
        lo = np.searchsorted(srt, v, side='left'); hi = np.searchsorted(srt, v, side='right')
        if n >= minobs:
            # count past < v : prefix sum up to lo
            c = 0; i = lo
            while i > 0:
                c += tree[i]; i -= i & (-i)
            ce = 0; i = hi
            while i > 0:
                ce += tree[i]; i -= i & (-i)
            out[t] = (c + 0.5 * (ce - c)) / n
        i = lo + 1
        while i <= M:
            tree[i] += 1; i += i & (-i)
        n += 1
    return out


def agg_features(score, elig, ret21, ret63):
    """daily cross-sectional aggregates of one loser score over eligible names -> dict of [T] arrays."""
    s = np.where(elig, score, np.nan).astype(np.float64)
    cnt = np.sum(~np.isnan(s), axis=1)
    good = cnt >= 30
    q = np.full((s.shape[0], 3), np.nan)
    q[good] = np.nanpercentile(s[good], [1, 90, 99], axis=1).T
    p1, p90, p99 = q[:, 0], q[:, 1], q[:, 2]
    # past-only threshold: expanding mean of daily p90 up to t-1, >= 60 days
    p90s = pd.Series(p90)
    thr = p90s.expanding(min_periods=60).mean().shift(1).values
    share = np.where(good & ~np.isnan(thr), np.nansum(s > thr[:, None], axis=1) / np.maximum(cnt, 1), np.nan)
    sc = np.clip(s, p1[:, None], p99[:, None])
    mean = np.where(good, np.nanmean(sc, axis=1), np.nan)
    disp = np.where(good, np.nanstd(sc, axis=1), np.nan)
    flag = s >= p90[:, None]
    out = dict(share=share, mean=mean, disp=disp)
    for nm, rr in (('ls21', ret21), ('ls63', ret63)):
        re = np.where(elig & ~np.isnan(rr), rr, np.nan)
        mu = np.nanmean(re, axis=1)
        fl = np.where(flag & ~np.isnan(re), re, np.nan)
        nf = np.sum(~np.isnan(fl), axis=1)
        out[nm] = np.where(good & (nf >= 5), np.nanmean(fl, axis=1) - mu, np.nan)
    return out


def atoms_from_features(F, minobs):
    """F: dict name -> [T]. Returns int8 A [n_atoms, T] (1/0/-1 unknown) and meta list."""
    QS = (0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9)
    A = []; meta = []
    for nm, f in F.items():
        f = np.asarray(f, np.float64)
        ch = f - np.r_[np.full(21, np.nan), f[:-21]]
        for tr, x in (('lvl', f), ('chg21', ch)):
            p = exp_pct(x, minobs)
            unk = np.isnan(p)
            for qv in QS:
                for dr in ('>', '<'):
                    a = (p > qv) if dr == '>' else (p < qv)
                    a = np.where(unk, -1, a.astype(np.int8)).astype(np.int8)
                    A.append(a); meta.append(dict(feat=nm, tr=tr, q=qv, dir=dr))
    return np.stack(A), meta


def blocks(dates, h, a, b, delay=DELAY):
    """decision rows every h trading days from the first date >= a; keep blocks whose window ends <= b (planned)."""
    T = len(dates)
    t0 = int(np.searchsorted(dates.values, np.datetime64(a)))
    tb = int(np.searchsorted(dates.values, np.datetime64(b), side='right')) - 1
    t_dec = np.arange(t0, T - h - delay, h)
    t_dec = t_dec[t_dec + delay + h <= tb]
    return t_dec


def kr200_proxy(K, X):
    dates = pd.to_datetime(K['dates']); T, N = X['idx'].shape
    mc = np.where(X['listed'] & (K['marcap'] > 0) & ~K['kosdaq'], K['marcap'], np.nan)
    rc = X['rc']
    mon = dates.year * 12 + dates.month
    r = np.zeros(T); cons = np.zeros(N, bool)
    for t in range(1, T):
        if mon[t] != mon[t - 1]:
            v = mc[t - 1]; ok = ~np.isnan(v)
            cons = np.zeros(N, bool)
            if ok.sum() > 0:
                top = np.argsort(-np.where(ok, v, -1))[:200]; cons[top] = True; cons &= ok
        w = np.where(cons & ~np.isnan(mc[t - 1]), mc[t - 1], 0.0)
        r[t] = (w * np.nan_to_num(rc[t])).sum() / w.sum() if w.sum() > 0 else 0.0
    return pd.Series(r, index=dates)


def kr_products(r_p, dates):
    rf = np.array([KR_CD[d.year] / 100 / 252 for d in dates])
    rt = r_p + DY / 252
    X = np.empty((5, len(r_p)))
    X[1] = 2 * rt - rf - 0.010 / 252
    X[0] = X[1]                              # unused (no 3x in KR)
    X[2] = rt - 0.0015 / 252
    X[3] = np.maximum(rf - 0.01 / 252, 0.0) * (1 - 0.154)
    X[4] = -rt + rf - 0.010 / 252
    return np.ascontiguousarray(X), rf


def check_proxy(px):
    with lzma.open('/mnt/project-files/research/data/panel_f32.npz.xz') as f:
        z = np.load(io.BytesIO(f.read()), allow_pickle=True)
    ts = pd.to_datetime(z['069500.KS|ts'], unit='s').normalize(); v = z['069500.KS|v'][:, 4].astype(float)
    e = pd.Series(v, index=ts); e = e[(e.index >= '2002-10-01') & (e.index <= '2006-12-31')]
    er = e.pct_change().dropna(); pr = px.reindex(er.index).dropna(); er = er.reindex(pr.index)
    return dict(n=int(len(pr)), corr=float(np.corrcoef(er.values, pr.values)[0, 1]), period='2002-10..2006-12')


def kr_main():
    t0 = time.time()
    K = D.load_kr(); X = D.kr_derived(K)
    dates = pd.to_datetime(K['dates']); T, N = X['idx'].shape
    elig_d = X['trade'] & (X['age'] >= 20) & (np.nan_to_num(X['adv20']) >= 1e8)
    px = kr200_proxy(K, X)
    chk = check_proxy(px); print('KR200 proxy vs 069500 daily corr', chk, flush=True)
    P, rf = kr_products(px.values, dates)
    np.savez(CACHE + 'kr_idx.npz', r=px.values, rf=rf, X=P, dates=dates.values.astype('datetime64[D]'))
    defs = SG.kr_defs(K, X); print('KR defs', len(defs), '%.0fs' % (time.time() - t0), flush=True)
    idx = X['idx']
    ret21 = idx / SG._lag(idx, 21) - 1; ret63 = idx / SG._lag(idx, 63) - 1
    F = {}
    for d in SG.CORE + ['TO', 'ILQ+']:
        a = agg_features(defs[d], elig_d, ret21, ret63)
        for k, v in a.items():
            F['%s_%s' % (k, d.replace('+', ''))] = v
    re21 = np.where(elig_d, ret21, np.nan)
    F['gen_disp21'] = np.nanstd(re21, axis=1); F['gen_neg21'] = np.nanmean(np.where(np.isnan(re21), np.nan, re21 < 0), axis=1)
    print('KR features', len(F), '%.0fs' % (time.time() - t0), flush=True)
    A, meta = atoms_from_features(F, 252)
    np.save(CACHE + 'kr_atoms.npy', A); json.dump(meta, open(CACHE + 'kr_atoms_meta.json', 'w'))
    pd.DataFrame(F, index=dates).to_pickle(CACHE + 'kr_feats.pkl')
    print('KR atoms', A.shape, 'known share in selection', float((A[:, (dates >= '2000-01-01') & (dates <= '2008-12-31')] >= 0).mean()), flush=True)
    # selection block arrays
    fail, reuse_row, fail1 = D.kr_spells(K, X, 'conservative')
    listed = X['listed']; last_row = np.where(listed.any(0), T - 1 - np.argmax(listed[::-1], axis=0), 0).astype(np.int64)
    for h in HS:
        t_dec = blocks(dates, h, *SEL['KR'])
        el = elig_d[t_dec]
        R, ok = S._kr_window(X['idx'], X['trade'], X['limdn'], listed, last_row, fail, t_dec + DELAY - 1, h, el, reuse_row, fail1)
        e0 = t_dec + DELAY
        elig = ok & ~np.isnan(R)
        entry = elig & X['trade'][e0] & ~X['limup'][e0]
        sc = np.stack([defs[d][t_dec] for d in SG.KR_DEFS]).astype(np.float32)
        mon = ((dates[t_dec].year - 1999) * 12 + dates[t_dec].month - 1).values
        np.savez(CACHE + 'kr_blk_h%d.npz' % h, t_dec=t_dec, R=R.astype(np.float32), elig=elig, entry=entry, sc=sc,
                 hs=X['hs'][t_dec].astype(np.float32), s20=np.nan_to_num(X['s20'][t_dec], nan=0.05).astype(np.float32),
                 adv=np.maximum(np.nan_to_num(X['adv20'][t_dec], nan=1e8), 1e6).astype(np.float32),
                 mcap=np.nan_to_num(K['marcap'][t_dec]).astype(np.float32), mon=mon)
        print('KR h', h, 'blocks', len(t_dec), dates[t_dec[0]].date(), dates[t_dec[-1]].date(), 'mean elig', float(elig.sum(1).mean()), '%.0fs' % (time.time() - t0), flush=True)


def us_main():
    t0 = time.time()
    U = D.load_us(); dates = U['dates']; mem = U['member']
    defs, adj = SG.us_defs(U)
    T, N = adj.shape
    elig_d = mem & ~np.isnan(adj)
    ret21 = adj / SG._lag(adj, 21) - 1; ret63 = adj / SG._lag(adj, 63) - 1
    F = {}
    for d in SG.CORE:
        a = agg_features(defs[d], elig_d, ret21, ret63)
        for k, v in a.items():
            F['%s_%s' % (k, d)] = v
    print('US features', len(F), '%.0fs' % (time.time() - t0), flush=True)
    A, meta = atoms_from_features(F, 504)
    np.save(CACHE + 'us_atoms.npy', A); json.dump(meta, open(CACHE + 'us_atoms_meta.json', 'w'))
    pd.DataFrame(F, index=dates).to_pickle(CACHE + 'us_feats.pkl')
    np.save(CACHE + 'us_dates.npy', dates.values.astype('datetime64[D]'))
    print('US atoms', A.shape, flush=True)
    adjU = U['adj']
    for h in HS:
        t_dec = blocks(dates, h, *SEL['US'])
        el = mem[t_dec] & (adjU[t_dec] > 0) & (adjU[t_dec + DELAY] > 0)
        R, ok = S._us_window(adjU, t_dec + DELAY - 1, h, el)
        elig = ok & ~np.isnan(R)
        sc = np.stack([defs[d][t_dec] for d in SG.US_DEFS]).astype(np.float32)
        mon = ((dates[t_dec].year - 1971) * 12 + dates[t_dec].month - 1).values
        np.savez(CACHE + 'us_blk_h%d.npz' % h, t_dec=t_dec, R=R.astype(np.float32), elig=elig, entry=elig, sc=sc, mon=mon)
        print('US h', h, 'blocks', len(t_dec), dates[t_dec[0]].date(), dates[t_dec[-1]].date(), 'mean elig', float(elig.sum(1).mean()), '%.0fs' % (time.time() - t0), flush=True)


if __name__ == '__main__':
    which = sys.argv[1]
    kr_main() if which == 'KR' else us_main()
