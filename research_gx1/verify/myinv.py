"""Independent GX1 INV world-signal reproduction (no gx1lib import). Writes nothing outside /tmp/claude-0/gx1verify."""
import os, sys, json
os.environ['NUMBA_CACHE_DIR'] = '/tmp/claude-0/nbc'
sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
import ov, jp, mkt
import numpy as np, pandas as pd

GD = '/mnt/project-files/research/gx1/data/'; AD = '/mnt/project-files/research/at2/data/'; QD = '/mnt/project-files/research/q1_alarm/data/'
END = pd.Timestamp('2014-12-31'); ON_FROM = pd.Timestamp('1989-01-01')
EU = ['UK', 'DE', 'FR', 'CH', 'NL', 'ES', 'IT', 'BE', 'AT', 'IE', 'GR', 'PT', 'SE']
AP = ['JP', 'HK', 'TW', 'KR', 'SG', 'IN', 'ID', 'MY', 'CN', 'AU', 'NZ']
AM = ['CA', 'MX', 'BR']; OT = ['TR', 'IL', 'ZA']
REG = {**{m: 'EU' for m in EU}, **{m: 'AP' for m in AP}, **{m: 'AM' for m in AM}, **{m: 'OT' for m in OT}, 'US': 'AM'}
ALL30 = EU + AP + AM + OT
EA_JOIN = {m: pd.Timestamp('1999-01-01') for m in ('DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'IE', 'PT')}; EA_JOIN['GR'] = pd.Timestamp('2001-01-01')
CC = {m: m for m in ALL30}; CC['UK'] = 'GB'

def find(sid):
    hits = [d + sid + '_le2014.csv' for d in (GD, AD, QD) if os.path.exists(d + sid + '_le2014.csv')]
    assert len(hits) <= 1, hits
    return hits[0] if hits else None

def rate_ids(m):
    s3 = 'IR3TCD01JPM156N' if m == 'JP' else 'IR3TIB01%sM156N' % CC[m]; sl = 'IRLTLT01%sM156N' % CC[m]
    return s3, sl

def load_index(m):
    s = pd.read_csv(GD + '%s_index_le2014.csv' % m, parse_dates=['date']).set_index('date')['close'].astype(float)
    assert s.index.max() <= END and s.index.is_monotonic_increasing and not s.index.duplicated().any() and s.notna().all()
    return s

def load_rate(sid):
    f = pd.read_csv(find(sid), parse_dates=['observation_date']); f.columns = ['d', 'v']
    f['v'] = pd.to_numeric(f['v'], errors='coerce'); f = f.dropna().sort_values('d')
    assert f['d'].max() <= END
    return f

def rate_on(sid, cal, stale_rule):
    """value of month m usable from the first calendar row dated >= 1st of month m+1; stale_rule: invalid if newest usable
    obs month < (current month - 1) - 2."""
    f = load_rate(sid)
    om = f['d'].dt.year.values * 12 + (f['d'].dt.month.values - 1)          # obs month number
    avail = pd.to_datetime(['%04d-%02d-01' % ((x + 1) // 12, (x + 1) % 12 + 1) for x in om]).values
    c = cal.values.astype('datetime64[ns]')
    p = np.searchsorted(avail, c, side='right') - 1
    val = np.where(p >= 0, f['v'].values[np.clip(p, 0, None)], np.nan)
    if stale_rule:
        cm = cal.year.values * 12 + (cal.month.values - 1)
        age = cm - np.where(p >= 0, om[np.clip(p, 0, None)], -10 ** 6)
        val = np.where(age <= 3, val, np.nan)
    return val

def asof(cal, m):
    """age in days of the last close of m dated strictly before each calendar date (inf if none)."""
    s = load_index(m); d = s.index.values.astype('datetime64[D]'); c = cal.values.astype('datetime64[D]')
    p = np.searchsorted(d, c, side='left') - 1
    age = np.where(p >= 0, (c - d[np.clip(p, 0, None)]).astype(np.int64), 10 ** 9)
    return age

def inv_share(cal, host, verbose=False):
    K = [m for m in ALL30 if REG[m] != REG[host]]
    units = []
    for m in K:
        s3, sl = rate_ids(m)
        if find(s3) and find(sl): units.append(m)
    T = len(cal); cd = cal.values.astype('datetime64[ns]')
    num = np.zeros(T); den = np.zeros(T); ean = np.zeros(T); ead = np.zeros(T)
    per = {}
    for m in units:
        s3, sl = rate_ids(m); y3 = rate_on(s3, cal, True); yl = rate_on(sl, cal, True)
        fresh = asof(cal, m) <= 10
        v = ~np.isnan(y3) & ~np.isnan(yl) & fresh
        raw = v & (yl - y3 < 0)
        anyw = pd.Series(raw.astype(float)).rolling(378, min_periods=1).max().values > 0
        flag = anyw & v
        per[m] = (flag, v)
        if m in EA_JOIN:
            inea = cd >= EA_JOIN[m].to_datetime64()
            num += flag & ~inea; den += v & ~inea; ean += flag & inea; ead += v & inea
        else:
            num += flag; den += v
    eav = ead >= 1; eat = eav & (ean > ead / 2.0)
    num = num + eat; den = den + eav
    on = (den >= 5) & (cd >= ON_FROM.to_datetime64())
    share = np.where(on, num / np.maximum(den, 1), np.nan)
    if verbose: print('host', host, 'K', len(K), 'INV units (markets with both rate files):', units)
    return share, den, K, units, per

def spells(dates, sig, min_len=1):
    out = []; i = 0; n = len(sig)
    while i < n:
        j = i
        while j + 1 < n and sig[j + 1] == sig[i]: j += 1
        if j - i + 1 >= min_len: out.append((bool(sig[i]), str(dates[i].date()), str(dates[j].date()), j - i + 1))
        i = j + 1
    return out
