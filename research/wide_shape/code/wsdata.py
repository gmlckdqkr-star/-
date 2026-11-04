"""WS1 data loaders (<=2014 only). US500 = S&P 500 PIT panel v3; KRALL = KR staging_clean_a panel.
Caches arrays to the scratchpad (CACHE) because the project mount is slow."""
import os, io, lzma, numpy as np, pandas as pd

END = pd.Timestamp('2014-12-31')
CACHE = os.environ.get('WS_CACHE', '/tmp/claude-0/-home-user--/c6bd4d9c-b328-5e0a-b6d0-48efd454b715/scratchpad/ws/')
os.makedirs(CACHE, exist_ok=True)
US_SRC = '/mnt/project-files/research/data/us_stocks/sp500_le2014_v3.npz.xz'
KR_DIR = '/mnt/project-files/research/data/kr_stocks/staging_clean_a/'


def load_us():
    fn = CACHE + 'us_v3.npz'
    if not os.path.exists(fn):
        with lzma.open(US_SRC) as f:
            z = np.load(io.BytesIO(f.read()), allow_pickle=True)
        np.savez(fn, **{k: z[k] for k in z.files})
    z = np.load(fn, allow_pickle=True)
    T, N = z['shape']
    dates = pd.to_datetime(z['dates'], unit='D')
    keep = dates <= END
    adj = z['adj'][keep].astype(np.float64)
    mem = np.unpackbits(z['member'], axis=0)[:T][keep].astype(bool)
    return dict(dates=dates[keep], adj=adj, member=mem)


# ---------------- KR ----------------
FAIL_OK = ('피흡수합병', '증권거래소 상장', '유가증권시장 상장', '코스닥시장 상장', '신청에 의한 상장폐지', '지주회사', '합병', '이전상장')


def roll_sum(x, W):
    """sum of rows t-W+1..t (nan where fewer than W rows)"""
    c = np.cumsum(x, axis=0); o = np.full(x.shape, np.nan)
    o[W - 1] = c[W - 1]; o[W:] = c[W:] - c[:-W]
    return o


def _tick(px, kosdaq):
    t = np.where(px < 1000, 1, np.where(px < 5000, 5, np.where(px < 10000, 10, np.where(px < 50000, 50,
        np.where(kosdaq, 100, np.where(px < 100000, 100, np.where(px < 500000, 500, 1000)))))))
    return t.astype(np.float64)


def load_kr():
    fn = CACHE + 'kr_arrays.npz'
    if os.path.exists(fn):
        z = np.load(fn, allow_pickle=True)
        return {k: z[k] for k in z.files}
    cols = ['date', 'code', 'market', 'open', 'high', 'low', 'close', 'volume', 'amount', 'marcap', 'adj_ret']
    df = pd.concat([pd.read_parquet(KR_DIR + 'KR_PANEL_DAILY_%d.parquet' % y, columns=cols) for y in range(1998, 2015)])
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] <= END]
    st = pd.read_csv(KR_DIR + 'KR_STOCKS.csv', dtype=str)
    excl = set(st.loc[st['exclude'].notna(), 'code'])
    df = df[~df['code'].isin(excl)]
    df = df[df['code'].str[-1] == '0']          # common shares only
    dates = np.array(sorted(df['date'].unique()))
    codes = np.array(sorted(df['code'].unique()))
    di = pd.Index(dates).get_indexer(df['date']); ci = pd.Index(codes).get_indexer(df['code'])
    T, N = len(dates), len(codes)
    out = {}
    for c in ('open', 'high', 'low', 'close', 'volume', 'amount', 'marcap', 'adj_ret'):
        a = np.full((T, N), np.nan); a[di, ci] = df[c].values.astype(np.float64); out[c] = a
    kq = np.zeros((T, N), bool); kq[di, ci] = (df['market'].values == 'KOSDAQ'); out['kosdaq'] = kq
    # delisting info
    st = st.sort_values(['code', 'start']).groupby('code').last()   # last listing spell per code
    end_reason = st.reindex(codes)['end_reason'].fillna('').values
    status = st.reindex(codes)['status_2014'].fillna('').values
    fail = np.array([(s == 'delisted') and not any(k in r for k in FAIL_OK) for s, r in zip(status, end_reason)])
    out['fail'] = fail; out['delisted'] = (status == 'delisted')
    out['dates'] = dates.astype('datetime64[D]'); out['codes'] = codes
    np.savez(fn, **out)
    return out


def kr_derived(K):
    """limits, capped returns, price index, eligibility features, costs (decision-time only)."""
    fn = CACHE + 'kr_derived.npz'
    if os.path.exists(fn):
        z = np.load(fn, allow_pickle=True)
        return {k: z[k] for k in z.files}
    dates = pd.to_datetime(K['dates'])
    T, N = K['close'].shape
    listed = ~np.isnan(K['close'])
    vol = np.nan_to_num(K['volume']); trade = listed & (vol > 0)
    lim = np.where(K['kosdaq'] & (dates < pd.Timestamp('2005-03-28'))[:, None], 0.12, 0.15)
    r = np.nan_to_num(K['adj_ret'])
    r = np.where(trade, r, 0.0)
    rc = np.minimum(r, lim); rc = np.maximum(rc, -0.99)
    limup = trade & (r >= lim - 0.005); limdn = trade & (r <= -lim + 0.005)
    idx = np.cumprod(1 + rc, axis=0)
    idx = np.where(listed, idx, np.nan)
    # listing age (trading rows since first listed row)
    age = np.cumsum(listed, axis=0)
    amt = np.where(listed, np.nan_to_num(K['amount']), 0.0)
    adv20 = roll_sum(amt, 20) / 20.0
    lr = np.log1p(rc); m = roll_sum(lr, 20) / 20
    s20 = np.sqrt(np.maximum(roll_sum(lr * lr, 20) / 20 - m * m, 0))
    # Abdi-Ranaldo on adjusted prices
    k = np.where(listed & (K['close'] > 0), idx / np.where(K['close'] > 0, K['close'], np.nan), np.nan)
    hi = np.log(K['high'] * k); lo = np.log(K['low'] * k); cl = np.log(idx)
    good = trade & (K['high'] > 0) & (K['low'] > 0)
    eta = np.where(good, (hi + lo) / 2, np.nan)
    prod = (cl[:-1] - eta[:-1]) * (cl[:-1] - eta[1:])
    prod = np.vstack([prod, np.full((1, N), np.nan)])
    ok = ~np.isnan(prod); pz = np.where(ok, prod, 0.0)
    W = 63
    # decision t may use pairs (j, j+1) with j+1 <= t  ->  prod rows j in [t-W, t-1]  ->  rolling sum at row t-1
    rs = roll_sum(pz, W); rn = roll_sum(ok.astype(np.float64), W)
    num = np.full((T, N), np.nan); den = np.full((T, N), np.nan)
    num[1:] = rs[:-1]; den[1:] = rn[:-1]
    ar = np.sqrt(np.maximum(4 * num / np.maximum(den, 1), 0.0))
    ar = np.where(den >= 20, ar, np.nan)
    px = np.where(listed, K['close'], np.nan)
    ht = _tick(np.nan_to_num(px, nan=1e9), K['kosdaq']) / 2 / px
    hs = np.fmax(ar / 2, ht); hs = np.where(np.isnan(hs), 0.01, hs); hs = np.minimum(hs, 0.05)
    out = dict(lim=lim, rc=rc, limup=limup, limdn=limdn, idx=idx, age=age, adv20=adv20, s20=s20, hs=hs, trade=trade, listed=listed)
    np.savez(fn, **out)
    return out

FAIL_AMBIG = ('해산 사유 발생', '존속기간 만료', '자진등록취소', '등록법인의 취소신청', '주된영업의 양도', '기타 등록취소')
_SPELLS = {}


def kr_spells(K, X, mode='conservative'):
    """Failure flag of each code's FINAL listing spell (spells ordered by end date; the cached K['fail'] came from
    groupby.last() on start order, which mixes spells when the first spell has no start date) and code-reuse info:
    reuse_row[i] = first row of a later listing spell that starts after a data gap (T if none), fail1[i] = failure flag
    of the spell that ends at that gap. mode 'lenient' (sensitivity only) treats FAIL_AMBIG reasons as non-failure."""
    if mode in _SPELLS:
        return _SPELLS[mode]
    codes = K['codes']; dates = pd.to_datetime(K['dates']); listed = X['listed']; T, N = listed.shape
    st = pd.read_csv(KR_DIR + 'KR_STOCKS.csv', dtype=str)
    st = st[st['code'].isin(set(codes))].copy()
    st['end_key'] = st['end'].fillna('9999-99-99')
    okl = FAIL_OK + (FAIL_AMBIG if mode == 'lenient' else ())
    isfail = lambda s_, r_: (s_ == 'delisted') and not any(k in r_ for k in okl)
    st = st.sort_values(['code', 'end_key'])
    fin = st.groupby('code').tail(1).set_index('code').reindex(codes)
    fail = np.array([isfail(a, b) for a, b in zip(fin['status_2014'].fillna(''), fin['end_reason'].fillna(''))])
    reuse_row = np.full(N, T, np.int64); fail1 = np.zeros(N, np.bool_)
    grp = {c: g for c, g in st.groupby('code')}
    for i in range(N):
        col = listed[:, i]
        if not col.any():
            continue
        f0 = int(np.argmax(col)); l0 = T - 1 - int(np.argmax(col[::-1]))
        seg = col[f0:l0 + 1]
        if seg.all():
            continue
        g1 = f0 + int(np.argmax(~seg)); g2 = g1 + int(np.argmax(seg[g1 - f0:]))      # gap [g1, g2), next run starts g2
        sp = grp.get(codes[i])
        if sp is None or len(sp) < 2:
            continue                                                               # one spell: long halt without rows
        st2 = pd.to_datetime(sp['start'], errors='coerce')
        near = (st2 >= dates[g2] - pd.Timedelta(days=10)) & (st2 <= dates[g2] + pd.Timedelta(days=10))
        if not near.any():
            continue
        reuse_row[i] = g2
        prev = sp[pd.to_datetime(sp['end_key'].where(sp['end_key'] != '9999-99-99'), errors='coerce') <= dates[g2]]
        if len(prev):
            r0 = prev.iloc[-1]
            fail1[i] = isfail(r0['status_2014'] if isinstance(r0['status_2014'], str) else '', r0['end_reason'] if isinstance(r0['end_reason'], str) else '')
    _SPELLS[mode] = (fail, reuse_row, fail1)
    return _SPELLS[mode]
