"""BT1 new primitives (PRECOMMIT_BT1 sec.1): F1 macro surprise / revision (ALFRED vintages), F2 S&P 500 PIT panel
aggregates, F3 cross-asset correlation regimes, F4 Shiller real earnings growth. Same calendar and lag rules as M1.
<=2014 only. Output cache/prim_bt1.npz + prim_bt1_meta.json (all c3=False, new=True)."""
import os, io, sys, json, lzma, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m1_data as D
SEAL = D.SEAL; R_ = D.R_; SCR = D.SCR
A27 = R_ + 'data/a27_macro_vintage/merged/'


def alfred_events(name, mode, quarterly=False):
    """first-release events of one ALFRED series -> DataFrame(v=first vintage date, obs, g, sur12, sur1, rev).
    mode 'log' (m/m log change), 'diff' (m/m difference), 'yoy' (12-period log change)."""
    d = pd.read_csv(A27 + 'alfred_%s_full.csv' % name)
    d['obs_date'] = pd.to_datetime(d['obs_date'])
    d['rs'] = pd.to_datetime(d['realtime_start'].astype(str).str[:10], errors='coerce')
    d['re'] = pd.to_datetime(d['realtime_end'].astype(str).str[:10].str.replace('9999-12-31', '2262-01-01'), errors='coerce')
    d['value'] = pd.to_numeric(d['value'], errors='coerce')
    d = d.dropna(subset=['value', 'rs'])
    d = d[(d['obs_date'] <= SEAL) & (d['rs'] <= SEAL)]
    by = {o: g[['rs', 're', 'value']].values for o, g in d.groupby('obs_date')}
    obs = sorted(by)
    step = pd.DateOffset(months=3 if quarterly else 1)
    lagk = (4 if quarterly else 12) if mode == 'yoy' else 1

    def val_at(o, v):
        a = by.get(o)
        if a is None: return np.nan
        m = (a[:, 0] <= v) & (a[:, 1] >= v)
        if not m.any(): return np.nan
        return float(a[m][-1, 2])

    def chg(x1, x0):
        if not (np.isfinite(x1) and np.isfinite(x0)): return np.nan
        if mode == 'diff': return x1 - x0
        if x1 <= 0 or x0 <= 0: return np.nan
        return np.log(x1 / x0)
    rows = []; gfirst = {}
    for o in obs:
        a = by[o]; i = np.argmin(a[:, 0]); v = a[i, 0]; x = float(a[i, 2])
        start_lim = (o + pd.DateOffset(months=3) if quarterly else o) + pd.Timedelta(days=120)
        if v > start_lim:            # not a genuine first release (series history loaded at a later vintage)
            continue
        if v < o + step:             # ADDENDUM_BT1_2: a 'release' dated before the reference period ends is not genuine
            continue
        op = o - step * lagk
        g = chg(x, val_at(op, v))
        if not np.isfinite(g): continue
        gfirst[o] = g
        o1 = o - step; o2 = o1 - step * lagk
        rev = chg(val_at(o1, v), val_at(o2, v)) - gfirst[o1] if o1 in gfirst else np.nan
        rows.append((v, o, g, rev))
    E = pd.DataFrame(rows, columns=['v', 'obs', 'g', 'rev']).sort_values('v').reset_index(drop=True)
    E['sur12'] = E['g'] - E['g'].shift(1).rolling(12, min_periods=12).mean()
    E['sur1'] = E['g'] - E['g'].shift(1)
    return E


def zexp(x, minn=24):
    """standardize by the past-only std (events strictly before)."""
    s = pd.Series(x); sd = s.shift(1).expanding(minn).std()
    return (s / sd).values


def decay_index(idx, events, tau):
    """events: list of (date, z). S_t = S_{t-1} exp(-1/tau) + sum of z released at t (first trading day >= date)."""
    add = np.zeros(len(idx)); seen = np.zeros(len(idx), bool)
    for dte, z in events:
        if not np.isfinite(z): continue
        p = idx.searchsorted(pd.Timestamp(dte))
        if p < len(idx): add[p] += z; seen[p] = True
    S = np.full(len(idx), np.nan); s = 0.0; k = np.exp(-1.0 / tau); started = False; nev = 0
    for t in range(len(idx)):
        s = s * k + add[t]
        if seen[t]: nev += 1
        if nev >= 12: started = True
        if started: S[t] = s
    return S


SERIES = [  # name, mode, quarterly, activity sign (+1 good news, -1 bad news, 0 = inflation)
    ('PAYEMS', 'log', False, 1), ('UNRATE', 'diff', False, -1), ('INDPRO', 'log', False, 1), ('TCU', 'diff', False, 1),
    ('HOUST', 'log', False, 1), ('PERMIT', 'log', False, 1), ('NEWORDER', 'log', False, 1),
    ('RSAFS', 'log', False, 1), ('CPIAUCNS', 'yoy', False, 0), ('CPILFESL', 'log', False, 0), ('PCEPILFE', 'log', False, 0)]
# ADDENDUM_BT1_2: RETAIL, CP, PNFI dropped (A27 grade reject-only: single source / revised history)


def load_panel():
    fn = SCR + 'cache/us_v3.npz'
    if not os.path.exists(fn):
        with lzma.open(R_ + 'data/us_stocks/sp500_le2014_v3.npz.xz') as f:
            z = np.load(io.BytesIO(f.read()), allow_pickle=True)
        np.savez(fn, **{k: z[k] for k in z.files})
    z = np.load(fn, allow_pickle=True)
    T, N = z['shape']
    dates = pd.to_datetime(z['dates'], unit='D'); keep = dates <= SEAL
    adj = z['adj'][keep].astype(np.float64)
    mem = np.unpackbits(z['member'], axis=0)[:T][keep].astype(bool)
    return dates[keep], adj, mem


def panel_aggregates(idx):
    dates, adj, mem = load_panel()
    T, N = adj.shape
    adj = np.where(adj > 0, adj, np.nan)
    ever = np.maximum.accumulate(mem, axis=0)                 # prices only from first membership on
    adj = np.where(ever, adj, np.nan)
    r = adj[1:] / adj[:-1] - 1; r = np.vstack([np.full((1, N), np.nan), r])
    r = np.where(np.abs(r) < 3.0, r, np.nan)                  # guard obviously broken prints (>+300% / day)
    memprev = np.vstack([np.zeros((1, N), bool), mem[:-1]])
    rm = np.where(memprev, r, np.nan)                         # return of day t for stocks that were members at t-1
    ew = np.nanmean(rm, 1); ew = np.nan_to_num(ew)
    df = pd.DataFrame(r)
    res = pd.DataFrame(r - ew[:, None])
    ivar = res.rolling(63, min_periods=40).var().values
    mx21 = df.rolling(21, min_periods=15).max().values
    hi = pd.DataFrame(adj).rolling(252, min_periods=200).max().values
    lo = pd.DataFrame(adj).rolling(252, min_periods=200).min().values
    r21 = pd.DataFrame(adj).pct_change(21, fill_method=None).values
    out = {}
    with np.errstate(all='ignore'):
        def mm(x): return np.nanmean(np.where(mem, x, np.nan), 1)
        out['agg_ivar63'] = np.log(mm(ivar))
        out['agg_max21'] = mm(mx21)
        out['agg_nearhi'] = mm((adj / hi > 0.95).astype(float) + np.where(np.isfinite(hi), 0, np.nan))
        out['agg_nearlo'] = mm((adj / lo < 1.05).astype(float) + np.where(np.isfinite(lo), 0, np.nan))
        out['agg_crash21'] = mm((r21 < -0.15).astype(float) + np.where(np.isfinite(r21), 0, np.nan))
        # factor spreads: formed on the first trading day of each month from close t-1 information, held 1 month
        mom = pd.DataFrame(adj).shift(21).values / pd.DataFrame(adj).shift(252).values - 1
        vol252 = df.rolling(252, min_periods=200).std().values
        ms = pd.Series(dates.to_period('M')); first = (ms != ms.shift(1)).values
        legs = {'wml': np.zeros(T), 'bab': np.zeros(T), 'strev': np.zeros(T)}
        cur = None
        for t in range(1, T):
            if first[t] or cur is None:
                f = t - 1; el = mem[f]
                def q(x, lo_, hi_):
                    v = np.where(el & np.isfinite(x[f]), x[f], np.nan); ok = np.isfinite(v)
                    if ok.sum() < 50: return None
                    a, b = np.nanquantile(v, [lo_, hi_])
                    return (v <= a) & ok, (v >= b) & ok
                cur = dict(wml=q(mom, .1, .9), bab=q(vol252, .2, .8), strev=q(r21, .1, .9))
            for k, sel in cur.items():
                if sel is None: continue
                lo_s, hi_s = sel; rr = r[t]
                a = np.nanmean(np.where(hi_s, rr, np.nan)); b = np.nanmean(np.where(lo_s, rr, np.nan))
                if not (np.isfinite(a) and np.isfinite(b)): continue
                if k == 'wml': legs[k][t] = a - b
                else: legs[k][t] = b - a          # bab: low vol minus high vol; strev: losers minus winners
        for k in legs:
            out['f_' + k] = np.cumsum(np.log1p(np.clip(legs[k], -0.9, None)))
        out['ew_lvl'] = np.cumsum(np.log1p(ew))
    S = {}
    nmem = mem.sum(1); t_ok = int(np.flatnonzero(nmem >= 400)[0])
    for k in legs:
        nzl = np.flatnonzero(legs[k] != 0); t_leg = int(nzl[0]) if len(nzl) else T
        out['f_' + k][:max(t_leg, t_ok)] = np.nan
    for k, v in out.items():
        s = pd.Series(v, index=dates)
        s.iloc[:max(300, t_ok)] = np.nan                       # ADDENDUM_BT1_2: no value before >= 400 members
        S[k] = D.stale_cut(idx, s.reindex(idx).values, 10)
    return S


def shiller():
    x = pd.read_excel(R_ + 'data/macro_regime/raw/SHILLER_ie_data_IA_20141222172333.xls', sheet_name='Data', header=None, skiprows=8)
    x = x[pd.to_numeric(x[0], errors='coerce').notna()]
    dd = pd.to_numeric(x[0]); y = np.floor(dd).astype(int); m = np.round((dd - y) * 100).astype(int)
    ix = pd.to_datetime(dict(year=y, month=m, day=1))
    Dv = pd.Series(pd.to_numeric(x[2], errors='coerce').values, index=ix)
    Ev = pd.Series(pd.to_numeric(x[3], errors='coerce').values, index=ix)
    Cv = pd.Series(pd.to_numeric(x[4], errors='coerce').values, index=ix)
    return Dv / Cv, Ev / Cv


def build():
    R, M = D.cal(); idx = R.index
    P = {}; meta = {}

    def add(name, arr, kind, freq, src):
        a = np.asarray(arr, float); assert a.shape == (len(idx),), name
        P[name] = a; f = np.flatnonzero(np.isfinite(a))
        meta[name] = dict(kind=kind, freq=freq, src=src, c3=False, new=True, first=str(idx[f[0]].date()) if len(f) else None)
    # ---- F1 ----
    act_ev, inf_ev, rev_ev = [], [], []
    for nm, mode, qtr, sign in SERIES:
        E = alfred_events(nm, mode, qtr)
        lim = 230 if qtr else 130
        D.STALE = lim
        add('sur_' + nm, D.place(idx, E['v'], E['sur12'].values), 'rate', 'q' if qtr else 'm', 'ALFRED %s first release minus trailing-12 mean' % nm)
        add('rev_' + nm, D.place(idx, E['v'], E['rev'].values), 'rate', 'q' if qtr else 'm', 'ALFRED %s revision of previous period' % nm)
        D.STALE = 130
        zs = zexp(E['sur12'].values); zr = zexp(E['rev'].values)
        if sign != 0:
            act_ev += [(v, sign * z) for v, z in zip(E['v'], zs)]; rev_ev += [(v, sign * z) for v, z in zip(E['v'], zr)]
        else:
            inf_ev += [(v, z) for v, z in zip(E['v'], zs)]
    add('msi21', decay_index(idx, act_ev, 21), 'rate', 'd', 'activity surprise index, decay 21d')
    add('msi63', decay_index(idx, act_ev, 63), 'rate', 'd', 'activity surprise index, decay 63d')
    add('inf63', decay_index(idx, inf_ev, 63), 'rate', 'd', 'inflation surprise index, decay 63d')
    add('rev63', decay_index(idx, rev_ev, 63), 'rate', 'd', 'activity revision index, decay 63d')
    # ---- F2 ----
    for k, v in panel_aggregates(idx).items():
        if k == 'ew_lvl':
            spx = np.cumsum(np.log1p(R['SPX'].fillna(0.0).values))
            add('ew_spx', v - spx, 'rate', 'd', 'log EW S&P 500 members / S&P TR')
        else:
            add(k, v, 'rate', 'd', 'S&P 500 PIT panel aggregate ' + k)
    # ---- F3 ----
    spx = pd.Series(np.log1p(R['SPX'].fillna(0.0).values), index=idx)
    dy = -pd.Series(M['y10'].values, index=idx).diff(); dc = pd.Series(M['cs'].values, index=idx).diff()
    import numpy as _n
    z0 = np.load(SCR + 'cache/prim.npz'); usd = pd.Series(z0['usd'], index=idx)
    du = np.log(usd).diff()
    for nm, other, w in (('c_sb63', dy, 63), ('c_sb252', dy, 252), ('c_sc63', dc, 63), ('c_sc252', dc, 252)):   # c_su252 dropped (revised usd, reject-only)
        c = spx.rolling(w, min_periods=int(w * .8)).corr(other)
        add(nm, c.values, 'rate', 'd', 'rolling corr S&P vs ' + nm)
    cv = spx.rolling(252, min_periods=200).cov(dy); vv = dy.rolling(252, min_periods=200).var()
    add('b_sb252', (cv / vv).values, 'rate', 'd', 'beta of S&P on -dy10, 252d')
    cm = pd.read_excel(R_ + 'open_data/raw/CMO_monthly.xlsx', sheet_name='Monthly Prices', header=None, skiprows=6)
    cm = cm[cm[0].astype(str).str.match(r'^\d{4}M\d{2}$')]
    cm.index = pd.to_datetime(cm[0].str.replace('M', '-') + '-01'); cm = cm[cm.index <= SEAL]
    au = np.log(pd.to_numeric(cm[69], errors='coerce')).diff()
    sm = spx.groupby(idx.to_period('M')).sum(); sm.index = sm.index.to_timestamp()
    cg = sm.rolling(36, min_periods=30).corr(au.reindex(sm.index))
    add('c_sg36', D.monthly_m2(idx, cg.dropna(), 2), 'rate', 'm', '36m corr S&P monthly vs gold monthly, m+2')
    # ---- F4 (ADDENDUM_BT1_2): Shiller monthly E/D are interpolated between quarter-end values -> use quarter-end
    # rows only (trailing four-quarter totals), known from the first trading day of quarter-end month + 4 ----
    Dr, Er = shiller(); Er = Er[Er.index <= SEAL].dropna(); Dr = Dr[Dr.index <= SEAL].dropna()
    qe = lambda s: s[s.index.month.isin([3, 6, 9, 12])]
    le = np.log(qe(Er)[qe(Er) > 0]); ld = np.log(qe(Dr)[qe(Dr) > 0])
    D.STALE = 230
    def addq(name, s, src):
        s = s.dropna(); add(name, D.place(idx, s.index + pd.offsets.MonthBegin(4), s.values), 'rate', 'q', src)
    g12 = le - le.shift(4)
    addq('e_g12', g12, 'Shiller real E (quarter-end, 4Q trailing) 4Q log change, +4m')
    addq('e_g3', le - le.shift(1), 'Shiller real E 1Q log change, +4m')
    addq('e_acc', g12 - g12.shift(1), 'E growth acceleration (quarterly), +4m')
    addq('d_g12', ld - ld.shift(4), 'Shiller real D 4Q log change, +4m')
    addq('payout', (ld - le), 'log D/E quarter-end, +4m')
    D.STALE = 130
    # ---- F5 (ADDENDUM_BT1_2, scout): gold/platinum ratio (Huang-Kilic 2019), industrial electricity sales growth
    # (Da-Yang-Yun 2017) ----
    pt = pd.to_numeric(cm[70], errors='coerce'); gold = pd.to_numeric(cm[69], errors='coerce')
    gp = np.log(gold / pt); gp = gp[gp.index >= '1972-01-01']        # gold pegged before the 1971-72 float
    add('gp_ratio', D.monthly_m2(idx, gp.dropna(), 2), 'rate', 'm', 'log gold/platinum (World Bank CMO monthly avg) m+2, 1972-')
    el = pd.read_csv(R_ + 'bt1/data/EIA_MER_T07.06_fetched20261104.csv')
    el = el[(el['MSN'] == 'ESICPUS') & (el['YYYYMM'] % 100 != 13)].copy()
    el['d'] = pd.to_datetime((el['YYYYMM'] // 100).astype(str) + '-' + (el['YYYYMM'] % 100).astype(str) + '-01')
    es = pd.Series(pd.to_numeric(el['Value'], errors='coerce').values, index=el['d']).sort_index()
    es = es[es.index <= SEAL]
    eg = np.log(es / es.shift(12)).dropna()
    add('elec_ind_g12', D.monthly_m2(idx, eg, 3), 'rate', 'm', 'EIA MER industrial electricity sales yoy log change, m+3 (COARSE: current vintage)')
    return idx, P, meta


if __name__ == '__main__':
    idx, P, meta = build()
    for k, m in meta.items():
        a = P[k]; f = np.isfinite(a); l = np.flatnonzero(f)
        m['last'] = str(idx[l[-1]].date()) if len(l) else None
        print('%-14s %-4s %-2s first=%s last=%s n=%d' % (k, m['kind'], m['freq'], m['first'], m['last'], f.sum()))
    np.savez_compressed(SCR + 'cache/prim_bt1.npz', dates=idx.values.astype('datetime64[D]').astype(np.int64), **P)
    json.dump(meta, open(SCR + 'cache/prim_bt1_meta.json', 'w'), indent=1)
    print(len(P), 'new primitives')
