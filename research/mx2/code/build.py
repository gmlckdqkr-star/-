"""MX2 data builder (<=2014-12-31 only).
Outputs data/mx2.npz: window months (720 = SPX 1955-01..1985-12 + NDX 1986-01..2014-12), per-action monthly
log-growth differences vs v1 (D), boundary costs (CB), atoms (uint8 6-bit halves), atom metadata; and data/daily.npz
(daily v1 target B, r, rf, dates per segment) for exact re-checks with the MS1 engine.
Decision at month-end close e_m, executed close e_m+2 -> affects daily returns e_m+3 .. e_{m+1}+2 (MS1 delay 2).
Feature for window month M uses only data published by the close of the last trading day of M-1."""
import sys, os, json, zipfile, io, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/nbc')
sys.path.insert(0, '/mnt/project-files/research/measure_std')
import std, bk, ov
D_ = '/mnt/project-files/research/mx2/data/'
END = pd.Timestamp('2014-12-31')
FEE3 = 0.0245 / 252
COST = 0.003          # one-way, per unit of capital traded
ACTIONS = ['CUT1', 'CUT0', 'ADD3', 'ADD1']
def act(a, h):
    h = np.asarray(h, float)
    if a == 'CUT1': return np.where(h >= 3, 1.0, h)
    if a == 'CUT0': return np.zeros_like(h)
    if a == 'ADD3': return np.full_like(h, 3.0)
    if a == 'ADD1': return np.where(h <= 0, 1.0, h)

def fred(sid, col=None):
    s = pd.read_csv(D_ + 'raw_%s.csv' % sid)
    s.columns = ['date', 'v']; s['date'] = pd.to_datetime(s['date']); s['v'] = pd.to_numeric(s['v'], errors='coerce')
    s = s.dropna().set_index('date')['v'].sort_index()
    return s[s.index <= END]

def segment(ctxname):
    c = std.contexts()[ctxname]
    B = bk.C3sig(c)[0]; r = c.r[0]; rf = c.rf[0]
    return c, B, r, rf

# ---------------- v1 segments and per-window D ----------------
def seg_D(dates, B, r, rf, win_months):
    """dates: daily DatetimeIndex aligned to B,r,rf (incl. warm-up). win_months: list of Period('M') window months.
    returns D[a][m], CB[a][m] (monthly), held level h."""
    n = len(dates)
    h = np.full(n, np.nan); h[3:] = B[:-3]
    x3 = 3 * r - 2 * rf - FEE3
    def g(L, a0, b0): return np.log1p((L / 3.0) * x3[a0:b0 + 1])   # idle cash earns 0 (user rule)
    per = dates.to_period('M')
    me = pd.Series(np.arange(n), index=dates).groupby(per).last()   # month -> last trading pos
    nM = len(win_months)
    D = np.zeros((4, nM)); CB = np.zeros((4, nM)); ok = np.zeros(nM, bool)
    for j, M in enumerate(win_months):
        pm = M - 1
        if pm not in me.index or M not in me.index: continue
        a0 = me[pm] + 3; b0 = me[M] + 2
        if b0 >= n or a0 > b0 or np.isnan(h[a0 - 1:b0 + 1]).any(): continue
        ok[j] = True
        hh = h[a0:b0 + 1]; hp = h[a0 - 1:b0 + 1]
        for ai, a in enumerate(ACTIONS):
            ah = act(a, hh); ahp = act(a, hp)
            D[ai, j] = np.sum(g(ah, a0, b0) - g(hh, a0, b0))
            # intra-window trades: overlay path vs v1 path
            D[ai, j] -= COST * (np.sum(np.abs(np.diff(ahp))) - np.sum(np.abs(np.diff(hp)))) / 3.0
            # boundary switch cost (on->off or off->on at window start)
            CB[ai, j] = COST * abs(act(a, hh[:1])[0] - hh[0]) / 3.0
    return D, CB, ok

# ---------------- features (monthly, at decision month-end) ----------------
def month_end_pos(idx):
    return pd.Series(np.arange(len(idx)), index=idx).groupby(idx.to_period('M')).last()

def build_features():
    import jp
    R, M = jp.calendar('1928-01-03', '2014-12-31')
    idx = R.index
    rtr = R['SPX'].fillna(0.0).copy()
    m86 = idx >= pd.Timestamp('1986-01-01')
    rtr[m86] = R['NDX'].fillna(0.0)[m86]
    P = (1 + rtr).cumprod()
    me = month_end_pos(idx); per = me.index; ep = me.values; nM = len(ep)
    F = {}
    def lag(a, k):
        o = np.full(len(a), np.nan); o[k:] = a[:-k]; return o
    Pm = P.values[ep]
    for k in (1, 3, 6, 12): F['ret%d' % k] = Pm / lag(Pm, k) - 1
    for k in (3, 6, 10, 12): F['gap%d' % k] = Pm / pd.Series(Pm).rolling(k).mean().values - 1
    F['dd12'] = Pm / pd.Series(Pm).rolling(13).max().values - 1
    lr = rtr.values
    def win(t, k): return lr[ep[t - k] + 1:ep[t] + 1]
    for nm, k in (('rv1', 1), ('rv3', 3), ('rv12', 12)):
        F[nm] = np.array([np.std(win(t, k)) * np.sqrt(252) if t >= k else np.nan for t in range(nM)])
    F['vr1_12'] = F['rv1'] / F['rv12']
    F['worst3'] = np.array([win(t, 3).min() if t >= 3 else np.nan for t in range(nM)])
    F['dnshare3'] = np.array([np.mean(win(t, 3) < 0) if t >= 3 else np.nan for t in range(nM)])
    F['skew3'] = np.array([pd.Series(win(t, 3)).skew() if t >= 3 else np.nan for t in range(nM)])
    # rates (daily H.15 / repo panel; same-day publication)
    y3 = M['y3m'].ffill().values[ep]; y10 = M['y10'].ffill().values[ep]; cs = M['cs'].ffill().values[ep]
    F['y3'] = y3; F['y10'] = y10; F['slope'] = y10 - y3
    for k in (1, 3, 6, 12): F['dy3_%d' % k] = y3 - lag(y3, k); F['dy10_%d' % k] = y10 - lag(y10, k)
    for k in (3, 6, 12): F['dsl_%d' % k] = F['slope'] - lag(F['slope'], k)
    F['minsl12'] = pd.Series(F['slope']).rolling(12).min().values; F['minsl24'] = pd.Series(F['slope']).rolling(24).min().values
    F['y3_min24'] = y3 - pd.Series(y3).rolling(24).min().values; F['y10_min12'] = y10 - pd.Series(y10).rolling(12).min().values
    F['cs'] = cs
    for k in (1, 3, 6, 12): F['dcs_%d' % k] = cs - lag(cs, k)
    def daily_ext(s):   # same-day published daily series -> value at month-end (ffill, max 10 bdays stale)
        return s.reindex(idx.union(s.index)).ffill(limit=10).reindex(idx).values[ep]
    dff = daily_ext(fred('DFF')); F['dff_y3'] = dff - y3
    for k in (3, 6): F['ddff_%d' % k] = dff - lag(dff, k)
    y2 = daily_ext(fred('DGS2')); F['y2_y3'] = y2 - y3; F['dy2_6'] = y2 - lag(y2, 6)
    y1 = daily_ext(fred('DGS1')); y5 = daily_ext(fred('DGS5')); F['curv'] = 2 * y5 - y1 - y10
    ted = daily_ext(fred('TEDRATE')); F['ted'] = ted; F['dted_3'] = ted - lag(ted, 3)
    vxo = daily_ext(fred('VXOCLS')); F['vxo'] = vxo; F['dvxo_1'] = vxo - lag(vxo, 1); F['vxo_rv1'] = vxo / 100 / F['rv1']
    # sectors / size (daily industry returns from the repo panel)
    secs = ['TECH', 'FIN', 'ENER', 'HLTH', 'UTIL', 'STAP', 'MANU', 'SHOP', 'TELE', 'SMALL', 'MICRO']
    SP = {s: (1 + R[s].fillna(0.0)).cumprod().values[ep] for s in secs + ['SPX']}
    above = np.array([[SP[s][t] > np.mean(SP[s][t - 9:t + 1]) if t >= 9 else np.nan for s in secs] for t in range(nM)], float)
    F['breadth'] = np.nanmean(above, axis=1)
    r1 = np.array([[SP[s][t] / SP[s][t - 1] - 1 if t >= 1 else np.nan for s in secs] for t in range(nM)])
    F['disp1'] = np.nanstd(r1, axis=1)
    def rel(a, b, k): return (SP[a] / lag(SP[a], k)) / (SP[b] / lag(SP[b], k)) - 1
    F['small_3'] = rel('SMALL', 'SPX', 3); F['small_12'] = rel('SMALL', 'SPX', 12)
    F['tech_3'] = rel('TECH', 'SPX', 3); F['tech_12'] = rel('TECH', 'SPX', 12)
    F['util_3'] = rel('UTIL', 'SPX', 3); F['fin_3'] = rel('FIN', 'SPX', 3); F['ener_6'] = rel('ENER', 'SPX', 6); F['stap_3'] = rel('STAP', 'SPX', 3)
    Bp = (1 + R['B10'].fillna(0.0)).cumprod().values[ep]
    F['bond_3'] = Bp / lag(Bp, 3) - 1; F['bond_6'] = Bp / lag(Bp, 6) - 1
    rb = R['B10'].fillna(0.0).values
    def corr(t, k):
        a = lr[ep[t - k] + 1:ep[t] + 1]; b = rb[ep[t - k] + 1:ep[t] + 1]
        return np.corrcoef(a, b)[0, 1] if np.std(a) > 0 and np.std(b) > 0 else np.nan
    F['sbcorr3'] = np.array([corr(t, 3) if t >= 3 else np.nan for t in range(nM)])
    F['sbcorr12'] = np.array([corr(t, 12) if t >= 12 else np.nan for t in range(nM)])
    # momentum factor (Ken French daily UMD, percent)
    z = zipfile.ZipFile(D_ + 'raw_F-F_Momentum_Factor_daily_CSV.zip'); txt = z.read(z.namelist()[0]).decode('latin1').splitlines()
    rows = [l.split(',') for l in txt if l[:8].strip().isdigit() and len(l.split(',')) >= 2]
    umd = pd.Series([float(x[1]) / 100 for x in rows], index=pd.to_datetime([x[0].strip() for x in rows], format='%Y%m%d'))
    umd = umd[umd.index <= END].reindex(idx).fillna(0.0)
    U = (1 + umd).cumprod().values[ep]
    F['umd_1'] = U / lag(U, 1) - 1; F['umd_3'] = U / lag(U, 3) - 1; F['umd_12'] = U / lag(U, 12) - 1
    uv = umd.values; F['umd_rv3'] = np.array([np.std(uv[ep[t - 3] + 1:ep[t] + 1]) if t >= 3 else np.nan for t in range(nM)])
    F['umd_rv3'][: np.argmax(np.cumsum(np.abs(uv))[ep] > 0) + 3] = np.nan
    # FX (H.10 noon rates, same day)
    for sid, nm in (('DEXJPUS', 'jpy'), ('DEXUSUK', 'gbp'), ('DEXSZUS', 'chf'), ('DEXCAUS', 'cad')):
        v = daily_ext(fred(sid))
        F[nm + '_3'] = v / lag(v, 3) - 1
        if nm == 'jpy': F['jpy_1'] = v / lag(v, 1) - 1
    def monthly_lag(s, L):   # monthly series value for month X usable from end of month X+L
        s = s.copy(); s.index = s.index.to_period('M') + L
        return pd.Series(s.values, index=s.index).reindex(per).ffill(limit=2).values
    tw = monthly_lag(fred('TWEXMMTH'), 1); F['twex_3'] = tw / lag(tw, 3) - 1; F['twex_12'] = tw / lag(tw, 12) - 1
    oil = monthly_lag(fred('WTISPLC'), 1)
    for k in (3, 6, 12): F['oil_%d' % k] = oil / lag(oil, k) - 1
    nq = daily_ext(fred('NASDAQCOM'))
    F['nqrel_3'] = (nq / lag(nq, 3)) / (SP['SPX'] / lag(SP['SPX'], 3)) - 1
    F['nqrel_12'] = (nq / lag(nq, 12)) / (SP['SPX'] / lag(SP['SPX'], 12)) - 1
    # initial claims NSA (week ending Sat, released next Thu -> usable 6 days after week end)
    ic = pd.read_csv('/mnt/project-files/research/data/macro_n/raw/ICNSA.csv'); ic.columns = ['date', 'v']
    ic['date'] = pd.to_datetime(ic['date']) + pd.Timedelta(days=6); ic = ic.set_index('date')['v'].astype(float)
    ic = ic[ic.index <= END]
    ic4 = ic.rolling(4).mean(); ic52 = ic.rolling(52).mean()
    a = ic4.reindex(idx.union(ic4.index)).ffill(limit=10).reindex(idx).values[ep]
    a52 = ic52.reindex(idx.union(ic52.index)).ffill(limit=10).reindex(idx).values[ep]
    F['claims_yoy'] = a / lag(a, 12) - 1; F['claims_v52'] = a / a52 - 1
    # global (MX1 units: 6 foreign markets + own rates, >=4 markets present)
    import pickle
    U6 = pickle.load(open('/mnt/project-files/research/mx1/data/units.pkl', 'rb'))
    gu = U6['SPX']; gm = {p: i for i, p in enumerate(gu['per'])}
    for k in ('g_breadth', 'g_ret12', 'g_dy3_6'):
        F[k] = np.array([gu['F'][k][gm[p]] if p in gm else np.nan for p in per])
    return per, F

def atoms_from(per, F, win_months):
    """expanding-window percentile rank (>=24 prior obs, values up to and incl. decision month only)."""
    perl = list(per); pos = {p: i for i, p in enumerate(perl)}
    dec = [pos.get(M - 1, -1) for M in win_months]
    names, bits = [], []
    QS = np.arange(1, 10) / 10
    for fn, v in F.items():
        v = np.asarray(v, float); rk = np.full(len(v), np.nan)
        for t in range(len(v)):
            if not np.isfinite(v[t]): continue
            past = v[:t + 1]; past = past[np.isfinite(past)]
            if len(past) >= 25: rk[t] = (np.sum(past < v[t]) + 0.5 * (np.sum(past == v[t]) - 1)) / (len(past) - 1)
        x = np.array([rk[d] if d >= 0 else np.nan for d in dec])
        for q in QS:
            for sgn in ('>', '<'):
                b = (x > q) if sgn == '>' else (x < q)
                b = np.where(np.isfinite(x), b, False)
                names.append('%s%s%.1f' % (fn, sgn, q)); bits.append(b)
    return names, np.array(bits, bool)

def main():
    # window months
    spx_w = pd.period_range('1955-01', '1985-12', freq='M'); ndx_w = pd.period_range('1986-01', '2014-12', freq='M')
    W = list(spx_w) + list(ndx_w)
    import jp
    C = std.contexts()
    Dl, CBl, OKl, daily = [], [], [], {}
    for nm, ctxn, a, b, wm in (('SPX', 'real_spx_55_85', '1928-01-03', '1985-12-31', spx_w), ('NDX', 'real_ndx_86_14', '1984-01-03', '2014-12-31', ndx_w)):
        Rr, Mm = jp.calendar(a, b); X = jp.mkX(Rr, Mm, nm)
        c = C[ctxn]; j0 = int(c.ii[0, 0]); dates = X.index[j0:j0 + c.r.shape[1]]
        assert np.allclose(X['r'].values[j0 + 1:j0 + c.r.shape[1]], c.r[0][1:])
        B = bk.C3sig(c)[0]
        D, CB, ok = seg_D(dates, B, c.r[0], c.rf[0], list(wm))
        Dl.append(D); CBl.append(CB); OKl.append(ok)
        daily[nm] = dict(dates=np.array(dates.values, 'datetime64[D]'), B=B, r=c.r[0], rf=c.rf[0])
    D = np.concatenate(Dl, 1); CB = np.concatenate(CBl, 1); OK = np.concatenate(OKl)
    per, F = build_features()
    names, bits = atoms_from(per, F, W)
    bits &= OK[None, :]
    # drop duplicate and degenerate atoms (on in <12 or >708 of 720 windows) -- frequency only, no returns used
    cnt = bits.sum(1); keep = (cnt >= 12) & (cnt <= len(W) - 12)
    _, first = np.unique(np.packbits(bits, axis=1), axis=0, return_index=True)
    uniq = np.zeros(len(names), bool); uniq[first] = True; keep &= uniq
    names = [n for n, k in zip(names, keep) if k]; bits = bits[keep]
    # pack into 6-bit halves (120 halves, padded to 128 bytes)
    nA = len(names); H = len(W) // 6
    A8 = np.zeros((nA, 128), np.uint8)
    for k in range(6): A8[:, :H] |= (bits[:, k::6].astype(np.uint8) << k)
    yr = np.array([p.year for p in W]); seg = np.array([0] * len(spx_w) + [1] * len(ndx_w))
    np.savez_compressed(D_ + 'mx2.npz', D=D, CB=CB, OK=OK, A8=A8, bits=bits, names=np.array(names), yr=yr, seg=seg,
                        win=np.array([str(p) for p in W]), feat_names=np.array(list(F.keys())))
    np.savez_compressed(D_ + 'daily.npz', **{'%s_%s' % (s, k): v for s, d in daily.items() for k, v in d.items()})
    print('windows', len(W), 'ok', OK.sum(), 'features', len(F), 'atoms', nA)
    for ai, a in enumerate(ACTIONS): print(a, 'sumD_all_on %.3f' % D[ai].sum(), 'nonzero months', int((D[ai] != 0).sum()))
    fa = {fn: int(np.isfinite(np.asarray(v, float)).sum()) for fn, v in F.items()}
    json.dump(dict(features=fa, n_atoms=nA, actions=ACTIONS), open(D_ + 'build_meta.json', 'w'), indent=1)

if __name__ == '__main__':
    main()
