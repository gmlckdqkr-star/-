"""RNG1: intraday range / volume info for v1's C3 vol input or a 3x->1x cap. See ../PRECOMMIT_RNG1.md (sha eb1e6ccf)."""
import sys, json, lzma, io, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import jp, ov, bk, rx, iv

def panel(sym):
    z = np.load(io.BytesIO(lzma.open('/mnt/project-files/research/data/panel_f32.npz.xz').read()), allow_pickle=True)
    t = z[sym + '|ts']; v = z[sym + '|v'].astype(float)
    df = pd.DataFrame(v[:, [1, 2, 3, 5]], columns=['H', 'L', 'C', 'V'], index=pd.to_datetime(t, unit='s').normalize())
    df = df[~df.index.duplicated()]; return df[df.index <= '2014-12-31']

NDX, SPX = panel('_NDX'), panel('_GSPC')
SPX = SPX[SPX.index >= '1982-04-21']   # theoretical H/L before (precommit)

def feats(idx, src):
    d = src.reindex(idx)                       # NaN on days without a bar
    ok = (d.H > 0) & (d.L > 0) & (d.H >= d.L)
    lr2 = np.where(ok, np.log(d.H / d.L) ** 2, np.nan)
    clv = np.where(ok & (d.H > d.L), ((d.C - d.L) - (d.H - d.C)) / (d.H - d.L), np.where(ok, 0.0, np.nan))
    dc = d.C.pct_change().values; dv = d.V.diff().values
    dist = np.where(np.isfinite(dc) & np.isfinite(dv), ((dc <= -0.002) & (dv > 0)).astype(float), np.nan)
    return lr2, clv, dist

IDX = {}
def x_index(name):
    if not IDX:
        R, M = jp.calendar('1984-01-03', '2014-12-31'); IDX['real_ndx_86_14'] = (R.index, NDX)
        a, b, *_ = iv.POOLS['dev250']; R, M = jp.calendar(a, b); IDX['dev250_glued'] = IDX['dev250_path'] = (R.index, NDX)
        R, M = jp.calendar('1928-01-03', '1985-12-31'); IDX['real_spx_55_85'] = IDX['real_spx_70_85'] = (R.index, SPX)
    return IDX[name]

def nanroll_mean(A, n):
    """rolling mean over last n columns ignoring NaN (needs >= n/2 valid), per row."""
    v = np.isfinite(A); X = np.where(v, A, 0.0)
    c = np.cumsum(np.c_[np.zeros(A.shape[0]), X], 1); k = np.cumsum(np.c_[np.zeros(A.shape[0]), v], 1)
    s = c[:, n:] - c[:, :-n]; m = k[:, n:] - k[:, :-n]
    out = np.where(m >= n / 2, s / np.maximum(m, 1), np.nan)
    return np.c_[np.full((A.shape[0], n - 1), np.nan), out]

def ctx_name(c):
    for k, v in std.contexts().items():
        if v is c: return k

def path_feats(c):
    if 'rng' in c._c: return c._c['rng']
    idx, src = c._xi if hasattr(c, '_xi') else x_index(ctx_name(c)); lr2, clv, dist = feats(idx, src)
    L = lr2[c.ii]; CL = clv[c.ii]; D = dist[c.ii]
    pk = {n: np.sqrt(nanroll_mean(L, n) / (4 * np.log(2)) * 252) for n in (10, 20)}
    cc20 = c.vol(20)
    both = np.isfinite(cc20) & np.isfinite(pk[20])
    s_cc = np.cumsum(np.where(both, cc20, 0), 1); s_pk = np.cumsum(np.where(both, pk[20], 0), 1); nb = np.cumsum(both, 1)
    k = np.where(nb >= 250, s_cc / np.maximum(s_pk, 1e-12), np.nan)
    k = np.c_[np.full((c.P, 1), np.nan), k[:, :-1]]          # use history up to t-1 for the scale
    clv20 = nanroll_mean(CL, 20)
    # causal expanding 10th pct of clv20 (>=500 obs), computed on a monthly grid then held (cost), strictly past values
    q10 = np.full(clv20.shape, np.nan)
    for t in range(500, c.T, 21):
        past = clv20[:, :t]; q = np.nanpercentile(np.where(np.isfinite(past), past, np.nan), 10, axis=1)
        cnt = np.isfinite(past).sum(1); q = np.where(cnt >= 500, q, np.nan); q10[:, t:t + 21] = q[:, None]
    Dz = np.where(np.isfinite(D), D, 0.0); cs = np.cumsum(np.c_[np.zeros(c.P), Dz], 1); dd25 = np.c_[np.zeros((c.P, 24)), cs[:, 25:] - cs[:, :-25]]
    out = dict(pkS10=k * pk[10], pkS20=k * pk[20], cc20=cc20, cc10=c.vol(10), clv20=clv20, q10=q10, dd25=dd25)
    c._c['rng'] = out; return out

def c3(c, v):
    v = np.where(np.isfinite(v), v, c.vol(20))
    B = np.where(v > 0.40, 1.0, 3.0)
    B = np.where(ov.macro_cond(c, ('shock6m',)), np.minimum(B, 1.0), B)
    off = ov.trend_gate(c, 200, 0.02, ov.macro_cond(c, ('inv', 'shock6m'))); return np.where(off, 0.0, B)

def fill(a, b): return np.where(np.isfinite(a), a, b)

def make(var):
    def m(c):
        f = path_feats(c); cc = f['cc20']
        if var == 'V1': B = c3(c, cc)
        elif var == 'R1': B = c3(c, np.fmax(cc, f['pkS20']))
        elif var == 'R2': B = c3(c, np.fmax(cc, f['pkS10']))
        elif var == 'R3': B = c3(c, np.where(np.isfinite(f['pkS20']), np.sqrt((cc ** 2 + fill(f['pkS20'], cc) ** 2) / 2), cc))
        elif var == 'R4': B = c3(c, cc); B = np.where((B == 3.0) & (f['clv20'] <= f['q10']), 1.0, B)
        elif var == 'R5': B = c3(c, cc); B = np.where((B == 3.0) & (f['dd25'] >= 5), 1.0, B)
        elif var == 'N0': B = c3(c, np.fmax(cc, f['cc10']))
        return B, rx.av23s, rx.P_av23s(.85), 0.1
    return m

if __name__ == '__main__':
    vs = sys.argv[1:] or ['V1', 'R1', 'R2', 'R3', 'R4', 'R5', 'N0']
    res = {}
    for v in vs:
        if v == 'V1':   # parity: my C3 rebuild must equal bk.C3sig on every context
            for bn, c in std.contexts().items():
                assert np.array_equal(make('V1')(c)[0], bk.C3sig(c)), bn
            print('parity OK', flush=True)
        res[v] = std.measure(v, make(v))
        json.dump(res, open('/mnt/project-files/research/rng1/results/rng1_%s.json' % '_'.join(vs), 'w'), indent=1)
