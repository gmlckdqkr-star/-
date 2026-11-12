"""GX1 library (PRECOMMIT_GX1.md, revised after the two pre-freeze reviews): world signals from non-US index markets of OTHER
regions, foreign v1 hosts, US MS1 contexts. All inputs <= 2014-12-31. No US index enters any signal."""
import os, sys, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/tmp/claude-0/nbc')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import ov, mkt, jp, iv
GD = '/mnt/project-files/research/gx1/data/'; AD = '/mnt/project-files/research/at2/data/'; QD = '/mnt/project-files/research/q1_alarm/data/'
END = pd.Timestamp('2014-12-31'); W = ov.WARM
SIG_START = pd.Timestamp('1989-01-01')                      # all world signals off on rows (source rows) dated before this
REGION = {**{m: 'EU' for m in ('UK', 'DE', 'FR', 'CH', 'NL', 'ES', 'IT', 'BE', 'AT', 'IE', 'GR', 'PT', 'SE')},
          **{m: 'AP' for m in ('JP', 'HK', 'TW', 'KR', 'SG', 'IN', 'ID', 'MY', 'CN', 'AU', 'NZ')},
          **{m: 'AM' for m in ('CA', 'MX', 'BR')}, **{m: 'OT' for m in ('TR', 'IL', 'ZA')}, 'US': 'AM'}
MARKETS = [m for m in REGION if m != 'US']
EURO = {**{m: pd.Timestamp('1999-01-01') for m in ('DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'IE', 'PT')}, 'GR': pd.Timestamp('2001-01-01')}
OECD = {'UK': 'GB', 'CA': 'CA', 'AU': 'AU', 'DE': 'DE', 'FR': 'FR', 'CH': 'CH', 'KR': 'KR', 'NL': 'NL', 'ES': 'ES', 'IT': 'IT', 'BE': 'BE',
        'AT': 'AT', 'SE': 'SE', 'IE': 'IE', 'PT': 'PT', 'GR': 'GR', 'MX': 'MX', 'IL': 'IL', 'ZA': 'ZA', 'NZ': 'NZ', 'JP': 'JP'}
HOSTS = ['UK', 'CA', 'AU', 'DE', 'FR', 'CH', 'JP', 'KR', 'NL', 'ES', 'IT', 'BE', 'AT', 'IE', 'GR', 'MX', 'ZA', 'NZ']
TR_INDEX = ('DE', 'NZ', 'BR')                                 # total-return indices (no dividend proxy added in the check)
STALE_DAYS = 10; BREAK_DAYS = 31; MIN_VALID = 5; RATE_MAX_AGE_M = 2
SIGNALS = [('B200', .5), ('B200', .6), ('B200', .7), ('B200', .8), ('D20', .25), ('D20', .40), ('D20', .55),
           ('N126', .60), ('N126', .75), ('N126', .90), ('INV', .25), ('INV', .40), ('INV', .55)]
RULES = [(k, th, mode) for mode in ('ALARM', 'CAP1') for (k, th) in SIGNALS]          # id 0-12 ALARM, 13-25 CAP1

def index(m):
    s = pd.read_csv(GD + '%s_index_le2014.csv' % m, parse_dates=['date']).set_index('date')['close'].astype(float)
    assert s.index.max() <= END and s.index.is_monotonic_increasing and not s.index.duplicated().any()
    return s

def _rate_file(sid):
    for d in (GD, AD, QD):
        if os.path.exists(d + sid + '_le2014.csv'): return d + sid + '_le2014.csv'
    return None

def monthly(sid, idx):
    """value of month m usable from the first calendar row on/after the 1st of month m+1 (AT2 rule); invalid (NaN) if the
    newest usable observation is more than RATE_MAX_AGE_M months older than last month."""
    f = pd.read_csv(_rate_file(sid), parse_dates=['observation_date']).set_index('observation_date').iloc[:, 0]
    f = pd.to_numeric(f, errors='coerce').dropna(); assert f.index.max() <= END
    obs = pd.Series(f.index, index=f.index + pd.offsets.MonthBegin(1)); f.index = f.index + pd.offsets.MonthBegin(1)
    u = idx.union(f.index); v = f.reindex(u).ffill().reindex(idx); o = obs.reindex(u).ffill().reindex(idx)
    per = idx.to_period('M'); oy = o.dt.year.values; om = o.dt.month.values
    age = (per.year.values - oy) * 12 + (per.month.values - om)                       # 1 = last month's value
    return v.where(~(age > 1 + RATE_MAX_AGE_M))

def rates(m, idx):
    """(y3m, y10) on calendar idx for market m, or None. JP: OECD 3m CD (Q1 file) + OECD long rate, both monthly."""
    if m not in OECD: return None
    cc = OECD[m]; s3 = 'IR3TCD01JPM156N' if m == 'JP' else 'IR3TIB01%sM156N' % cc; sl = 'IRLTLT01%sM156N' % cc
    if _rate_file(s3) is None or _rate_file(sl) is None: return None
    return monthly(s3, idx), monthly(sl, idx)

# ---------------- world signals ----------------
def signal_set(host):
    """markets of other regions than the host (US host: no Americas)."""
    return [m for m in MARKETS if REGION[m] != REGION[host]]

def asof_levels(cal, markets):
    """L[t,k] = last close of k dated STRICTLY before cal[t] (NaN before k's first close or if older than BREAK_DAYS);
    AGE[t,k] = days since that close. k counts in a share on day t only if AGE <= STALE_DAYS (that day only)."""
    out = np.full((len(cal), len(markets)), np.nan); age = np.full((len(cal), len(markets)), 10 ** 6)
    c = cal.values.astype('datetime64[D]')
    for j, m in enumerate(markets):
        s = index(m); d = s.index.values.astype('datetime64[D]'); v = s.values
        p = np.searchsorted(d, c, side='left') - 1
        ok = p >= 0; a = np.where(ok, (c - d[np.clip(p, 0, None)]).astype(int), 10 ** 6)
        ok &= a <= BREAK_DAYS
        out[ok, j] = v[p[ok]]; age[ok, j] = a[ok]
    return out, age

def run_len(valid):
    v = valid.astype(np.int64); cs = np.cumsum(v, axis=-1)
    reset = np.where(v == 0, cs, 0); reset = np.maximum.accumulate(reset, axis=-1)
    return cs - reset

def _roll_max(x, n):
    a = np.atleast_2d(x); out = pd.DataFrame(a.T).rolling(n, min_periods=n).max().values.T
    return out.reshape(np.shape(x))

def _roll_any(b, n):
    a = np.atleast_2d(b).astype(float); out = pd.DataFrame(a.T).rolling(n, min_periods=1).max().values.T > 0
    return out.reshape(np.shape(b))

def indicators_from_levels(L, valid):
    """L, valid: (..., T) for ONE market (calendar rows). -> dict name -> (flag, valid)."""
    rl = run_len(valid); Lz = np.where(valid, L, np.nan); out = {}
    x0 = np.where(np.isnan(Lz), 0.0, Lz); c = np.cumsum(x0, axis=-1)
    cc = np.concatenate([np.zeros(c.shape[:-1] + (200,)), c], axis=-1); m200 = (cc[..., 200:] - cc[..., :-200]) / 200
    v200 = rl >= 200; out['B200'] = (np.where(v200, Lz < m200, False), v200)
    v252 = rl >= 252; mx = _roll_max(Lz, 252); out['D20'] = (np.where(v252, Lz / mx - 1 <= -0.20, False), v252)
    v127 = rl >= 127; lag = np.full(Lz.shape, np.nan); lag[..., 126:] = Lz[..., :-126]
    out['N126'] = (np.where(v127, Lz / lag - 1 < 0, False), v127)
    return out

def _inv_inputs(cal, mk, AGE):
    """per market with rates: (inverted on the source row, valid on the source row = both rates present & index fresh)."""
    res = {}
    for j, m in enumerate(mk):
        rr = rates(m, cal)
        if rr is None: continue
        y3, y10 = rr[0].values, rr[1].values; rv = ~(np.isnan(y3) | np.isnan(y10)) & (AGE[:, j] <= STALE_DAYS)
        res[m] = (np.where(rv, (y10 - y3) < 0, False), rv)
    return res

def _inv_share(inv_in, dates_src, rows=None):
    """INV share. rows: None (historical calendar) or ii (P,T). INV_k(t) = an inverted valid row within the last 378 rows
    (min_periods 1, like ov.flags_hist), counted if valid at t. Euro members = one unit EA from their join date
    (EA valid if >= 1 member valid; EA true if more than half of the valid members are true)."""
    shp = dates_src.shape if rows is None else rows.shape
    num = np.zeros(shp); den = np.zeros(shp); ea_n = np.zeros(shp); ea_d = np.zeros(shp)
    for m, (inv, v) in inv_in.items():
        iv_, vv = (inv, v) if rows is None else (inv[rows], v[rows])
        flag = _roll_any(iv_ & vv, 378) & vv
        if m in EURO:
            d = dates_src if rows is None else dates_src[rows]; inea = d >= EURO[m].to_datetime64()
            num += np.where(inea, 0, flag); den += np.where(inea, 0, vv); ea_n += np.where(inea, flag, 0); ea_d += np.where(inea, vv, 0)
        else:
            num += flag; den += vv
    ea_valid = ea_d >= 1; ea_true = ea_valid & (ea_n > ea_d / 2)
    return num + ea_true, den + ea_valid

def world_signals(cal, host):
    """historical world signals on calendar cal for host. DataFrame: G00..G12 bool, share_*, n_*."""
    mk = signal_set(host); L, AGE = asof_levels(cal, mk); T = len(cal)
    num = {k: np.zeros(T) for k in ('B200', 'D20', 'N126')}; den = {k: np.zeros(T) for k in num}
    for j in range(len(mk)):
        valid = ~np.isnan(L[:, j]); fresh = AGE[:, j] <= STALE_DAYS; ind = indicators_from_levels(L[:, j], valid)
        for k in num:
            f, v = ind[k]; v = v & fresh; num[k] += f & v; den[k] += v
    num['INV'], den['INV'] = _inv_share(_inv_inputs(cal, mk, AGE), cal.values.astype('datetime64[ns]'))
    on = cal >= SIG_START; D = pd.DataFrame(index=cal)
    for k in num:
        D['share_' + k] = np.where((den[k] >= MIN_VALID) & on, num[k] / np.maximum(den[k], 1), np.nan); D['n_' + k] = den[k]
    for i, (k, th) in enumerate(SIGNALS):
        D['G%02d' % i] = np.nan_to_num(D['share_' + k].values, nan=-1.0) >= th
    return D

def path_world(cal, ii, host='US', L_override=None):
    """dev250_path version: day-change L(pos)/L(pos-1)-1 from the ORIGINAL previous row, validity/freshness from the original
    row, stitched along ii; indicators on the stitched level. INV: source-row inversion sign (spread not stitched, like
    std.path_flags), 378-row window on the path. Signals off on source rows dated before SIG_START."""
    mk = signal_set(host); L, AGE = asof_levels(cal, mk)
    if L_override is not None: L = L_override
    P, T = ii.shape; num = {k: np.zeros((P, T)) for k in ('B200', 'D20', 'N126')}; den = {k: np.zeros((P, T)) for k in num}
    for j in range(len(mk)):
        lv = L[:, j]; prev = np.r_[np.nan, lv[:-1]]; rk = lv / prev - 1; vk = ~np.isnan(rk)
        r = np.where(vk[ii], rk[ii], 0.0); v = vk[ii].copy(); v[:, 0] = False
        fresh = (AGE[:, j] <= STALE_DAYS)[ii]; lvl = np.cumprod(1 + r, axis=1)
        ind = indicators_from_levels(lvl, v)
        for k in num:
            f, vv = ind[k]; vv = vv & fresh; num[k] += f & vv; den[k] += vv
    num['INV'], den['INV'] = _inv_share(_inv_inputs(cal, mk, AGE), cal.values.astype('datetime64[ns]'), rows=ii)
    on = (cal.values >= SIG_START.to_datetime64())[ii]; out = {}
    for i, (k, th) in enumerate(SIGNALS):
        share = np.where((den[k] >= MIN_VALID) & on, num[k] / np.maximum(den[k], 1), -1.0); out['G%02d' % i] = share >= th
    out['_den'] = den
    return out

# ---------------- foreign hosts ----------------
def host(m, div=0.0):
    s = index(m); X = pd.DataFrame(index=s.index); X['r'] = s.pct_change().fillna(0.0)
    if div and m not in TR_INDEX: X['r'] = X['r'] + div / 252
    y3, y10 = rates(m, X.index); X['y3m'] = y3; X['y10'] = y10
    ok = X[['y3m', 'y10']].notna().all(axis=1)
    first = ok.idxmax() if ok.any() else None
    X[['y3m', 'y10']] = X[['y3m', 'y10']].ffill().fillna(0.0)
    X['rf'] = X['y3m'] / 100 / 252; X['cs'] = 0.0; X['vix'] = np.nan
    X['rb'] = mkt.bond10(X); X['p'] = (1 + X['r']).cumprod()
    i0 = max(0, X.index.get_loc(first) + 378 - W)            # first scored row = first row with both rates + 378 (AT2 rule)
    return X, i0

def acct(c, Ghist=None, Gpath=None, mode=None, delay=None):
    """v1 (+ optional world rule) on Ctx c. Ghist: bool aligned to source rows; Gpath: (P,T). Returns (cagr array, E)."""
    g = None
    if Ghist is not None: g = Ghist[c.ii]
    if Gpath is not None: g = Gpath
    if g is not None and mode == 'ALARM':
        c.F = dict(c.F); c.F['inv'] = np.asarray(c.F['inv'], bool) | g; c._c = {}
    B, bfn, bp, fs = std.s085(c); B = np.array(B, dtype=np.float64)
    if g is not None and mode == 'CAP1': B = np.where(g, np.minimum(B, 1.0), B)
    kw = dict(cspr=10.0)
    if delay is not None: kw['delay'] = delay
    return std.engine(c, B, bfn, bp, fs, **kw)

# ---------------- US contexts (replicates std.contexts) ----------------
def us_frames():
    out = {}
    R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
    i0 = X.index.searchsorted(pd.Timestamp('1986-01-02')) - W
    out['real_ndx_86_14'] = (X, F, np.arange(i0, len(X))[None, :], 'hist')
    a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
    ii = ov.boot_idx(len(X), P=P, years=30, block=blk, seed=seed, lo=1)
    out['dev250_glued'] = (X, F, ii, 'hist'); out['dev250_path'] = (X, F, ii, 'path')
    R, M = jp.calendar('1928-01-03', '1985-12-31'); X = jp.mkX(R, M, 'SPX'); F = ov.flags_hist(X)
    for nm, a in (('real_spx_55_85', '1955-01-03'), ('real_spx_70_85', '1970-01-02')):
        j0 = X.index.searchsorted(pd.Timestamp(a)) - W; out[nm] = (X, F, np.arange(j0, len(X))[None, :], 'hist')
    return out

def us_ctx(X, F, ii, kind):
    c = ov.Ctx(X, F, ii)
    if kind == 'path': c.F = std.path_flags(X, ii); c._c = {}
    return c
