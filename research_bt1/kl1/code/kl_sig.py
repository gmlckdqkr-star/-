"""KL1 loser definitions (score: larger = more likely future loser), decision-close-t information only, <=2014.
KR: from WS1 arrays (capped limit returns rc, price index idx, amount, marcap, limit-up flags).
US: S&P 500 PIT panel, prices only from first membership (WS1 signals_us rule), no dvol / dividends / price levels."""
import numpy as np, pandas as pd

CORE = ['V21', 'V63', 'V252', 'IV63', 'MX21', 'MX63', 'W21', 'W5', 'H52', 'L52', 'ML', 'SK63']
KR_ONLY = ['TO', 'ILQ+', 'ILQ-', 'SZ+', 'SZ-', 'VS+', 'VS-', 'LU+', 'LU-']
KR_DEFS = CORE + KR_ONLY            # 21 signed definitions
US_DEFS = list(CORE)                # 12


def _lag(a, k):
    return np.vstack([np.full((k, a.shape[1]), np.nan), a[:-k]])


def _roll(df, W, fn, mp=None):
    r = df.rolling(W, min_periods=mp or int(0.9 * W))
    return getattr(r, fn)().values


def _ivol(lr, W=63):
    """idiosyncratic stdev of lr vs the cross-sectional mean of lr (EW market), rolling W, nan-aware."""
    m = np.nanmean(lr, axis=1)
    ok = ~np.isnan(lr)
    x = np.where(ok, lr, 0.0); mm = np.where(ok, m[:, None], 0.0)
    def rs(a):
        c = np.cumsum(a, axis=0); o = np.full(a.shape, np.nan); o[W - 1] = c[W - 1]; o[W:] = c[W:] - c[:-W]; return o
    n = rs(ok.astype(np.float64))
    Sx, Sm, Sxx, Smm, Sxm = rs(x), rs(mm), rs(x * x), rs(mm * mm), rs(x * mm)
    n_ = np.where(n >= int(0.9 * W), n, np.nan)
    vx = Sxx / n_ - (Sx / n_) ** 2; vm = Smm / n_ - (Sm / n_) ** 2; cxm = Sxm / n_ - (Sx / n_) * (Sm / n_)
    iv = vx - np.where(vm > 1e-12, cxm * cxm / vm, 0.0)
    return np.sqrt(np.maximum(iv, 0.0))


def kr_defs(K, X):
    """dict name -> float32 [T, N]"""
    idx = X['idx']; listed = X['listed']
    rcl = np.where(listed, X['rc'], np.nan)
    lr = np.log1p(rcl); L = pd.DataFrame(lr)
    out = {}
    out['V21'] = _roll(L, 21, 'std'); out['V63'] = _roll(L, 63, 'std'); out['V252'] = _roll(L, 252, 'std')
    out['IV63'] = _ivol(np.where(X['trade'], lr, np.nan))
    R = pd.DataFrame(rcl)
    out['MX21'] = _roll(R, 21, 'max'); out['MX63'] = _roll(R, 63, 'max')
    out['W21'] = idx / _lag(idx, 21) - 1; out['W5'] = idx / _lag(idx, 5) - 1
    I = pd.DataFrame(idx)
    out['H52'] = 1 - idx / _roll(I, 252, 'max'); out['L52'] = -(idx / _roll(I, 252, 'min') - 1)
    out['ML'] = -(_lag(idx, 21) / _lag(idx, 252) - 1)
    out['SK63'] = _roll(L, 63, 'skew')
    amt = np.where(listed, np.nan_to_num(K['amount']), np.nan)
    mc = np.where(K['marcap'] > 0, K['marcap'], np.nan)
    out['TO'] = _roll(pd.DataFrame(amt / mc), 21, 'mean')
    il = np.where(X['trade'] & (amt > 0), np.abs(X['rc']) / np.where(amt > 0, amt, np.nan) * 1e9, np.nan)
    ilq = pd.DataFrame(il).rolling(21, min_periods=15).mean().values          # WS1 ILLQ definition
    out['ILQ+'] = ilq; out['ILQ-'] = -ilq
    sz = -np.log(mc); out['SZ+'] = sz; out['SZ-'] = -sz
    a5 = pd.DataFrame(amt).rolling(5, min_periods=5).sum().values; a60 = pd.DataFrame(amt).rolling(60, min_periods=60).sum().values
    vs = a5 / np.where(a60 > 0, a60, np.nan); out['VS+'] = vs; out['VS-'] = -vs
    lu = np.where(listed, pd.DataFrame(X['limup'].astype(float)).rolling(21, min_periods=1).sum().values, np.nan)
    out['LU+'] = lu; out['LU-'] = -lu
    for k in out:
        a = np.where(listed, out[k], np.nan); a[~np.isfinite(a)] = np.nan
        out[k] = a.astype(np.float32)
    return out


def us_prices(U):
    adj = U['adj'].copy(); mem = U['member']
    first = np.where(mem.any(0), np.argmax(mem, axis=0), adj.shape[0])
    rows = np.arange(adj.shape[0])[:, None]
    adj[rows < first[None, :]] = np.nan
    adj[~(adj > 0)] = np.nan
    return adj


def us_defs(U):
    adj = us_prices(U)
    r1 = adj / _lag(adj, 1) - 1
    lr = np.log1p(r1); L = pd.DataFrame(lr)
    out = {}
    out['V21'] = _roll(L, 21, 'std'); out['V63'] = _roll(L, 63, 'std'); out['V252'] = _roll(L, 252, 'std')
    out['IV63'] = _ivol(lr)
    R = pd.DataFrame(r1)
    out['MX21'] = _roll(R, 21, 'max'); out['MX63'] = _roll(R, 63, 'max')
    out['W21'] = adj / _lag(adj, 21) - 1; out['W5'] = adj / _lag(adj, 5) - 1
    A = pd.DataFrame(adj)
    out['H52'] = 1 - adj / _roll(A, 252, 'max'); out['L52'] = -(adj / _roll(A, 252, 'min') - 1)
    out['ML'] = -(_lag(adj, 21) / _lag(adj, 252) - 1)
    out['SK63'] = _roll(L, 63, 'skew')
    have = ~np.isnan(adj)
    for k in out:
        a = np.where(have, out[k], np.nan); a[~np.isfinite(a)] = np.nan
        out[k] = a.astype(np.float32)
    return out, adj
