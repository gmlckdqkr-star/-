"""SL1 stock sleeves (PRECOMMIT_SL1 sec.1): S&P 500 point-in-time members, monthly equal-weight top-K baskets by
price-only characteristics (lab input rules: no dvol, no price level, windows <= 260 rows, prices only from the first
membership day, no stale flag, no symbols; divy used only for the 15.4% dividend tax).
Basket formed with close t_m information (t_m = month end), bought at close t_m+2, held for days t_m+3 .. t_{m+1}+2
(same 2-day delay as the BT1 engine). Delisting inside a holding: lab rule (250-day return to the last price < -30%
-> -50%, else 0), then cash. Cost 0.3% per side on the changed names at each rebalance. Output: daily simple returns
on the panel calendar (NaN before the first basket)."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt1_data as BD, m1_data as DT
SCR = DT.SCR
COST, DTAX = 0.003, 0.154
CHARS = ('MOM12', 'MOM6', 'REV1', 'LOWVOL63', 'LOWVOL252', 'HIVOL63', 'HI52', 'LOWMAX21', 'LOWBETA', 'HIBETA', 'TREND200', 'LOSER12')
KS = (10, 30)


def load():
    dates, adj, mem = BD.load_panel()
    z = np.load(SCR + 'cache/us_v3.npz', allow_pickle=True)
    divy = z['divy'][:len(dates)].astype(np.float64)
    adj = np.where(adj > 0, adj, np.nan)
    ever = np.maximum.accumulate(mem, axis=0)
    r0 = int(np.argmax(mem.any(1)))                                   # first membership row (1970-01-02)
    ever[:r0, mem[r0]] = True                                         # ADDENDUM_SL1_B: initial cohort keeps prices from its first price (lab rule)
    adj = np.where(ever, adj, np.nan)                                 # prices only from the first membership on
    # ADDENDUM_SL1_B: spike-and-revert bad prints (+100% then -45%, or -50% then +80%) are removed
    with np.errstate(all='ignore'):
        u = adj / np.vstack([np.full((1, adj.shape[1]), np.nan), adj[:-1]])
        v = np.vstack([adj[1:], np.full((1, adj.shape[1]), np.nan)]) / adj
    bad = ((u > 2.0) & (v < 0.55)) | ((u < 0.5) & (v > 1.8))
    adj = np.where(bad, np.nan, adj)
    # ADDENDUM_SL1_B: an unchanged close for >= 5 rows (counted from the past only) = no trade -> price unknown
    run = np.zeros(adj.shape, np.int32)
    for t in range(1, adj.shape[0]):
        same = adj[t] == adj[t - 1]
        run[t] = np.where(same, run[t - 1] + 1, 0)
    adj = np.where(run >= 4, np.nan, adj)                             # run >= 4 equal steps = 5 equal closes
    divy = np.where(ever, np.nan_to_num(divy), 0.0)
    return dates, adj, mem, divy


def characteristics(adj, mem):
    T, N = adj.shape
    P = pd.DataFrame(adj)
    r = P.pct_change(fill_method=None).values
    r = np.where(np.abs(r) < 3.0, r, np.nan)
    R = pd.DataFrame(r)
    memprev = np.vstack([np.zeros((1, N), bool), mem[:-1]])
    ew = np.nan_to_num(np.nanmean(np.where(memprev, r, np.nan), 1))
    ewS = pd.Series(ew)
    # beta = cov(r, ew) / var(ew) over 252 rows, both moments on each stock's valid rows (ADDENDUM_SL1_B)
    F = np.isfinite(r)
    m_r = R.rolling(252, min_periods=200).mean().values
    m_e = pd.DataFrame(np.where(F, ew[:, None], np.nan)).rolling(252, min_periods=200).mean().values
    m_ee = pd.DataFrame(np.where(F, (ew ** 2)[:, None], np.nan)).rolling(252, min_periods=200).mean().values
    m_re = pd.DataFrame(r * ew[:, None]).rolling(252, min_periods=200).mean().values
    beta = (m_re - m_r * m_e) / (m_ee - m_e * m_e)
    C = {}
    with np.errstate(all='ignore'):
        C['MOM12'] = P.shift(21).values / P.shift(252).values - 1
        C['MOM6'] = P.shift(21).values / P.shift(126).values - 1
        C['REV1'] = -(adj / P.shift(21).values - 1)
        C['LOWVOL63'] = -R.rolling(63, min_periods=50).std().values
        C['LOWVOL252'] = -R.rolling(252, min_periods=200).std().values
        C['HIVOL63'] = R.rolling(63, min_periods=50).std().values
        C['HI52'] = adj / P.rolling(252, min_periods=200).max().values
        C['LOWMAX21'] = -R.rolling(21, min_periods=15).max().values
        C['LOWBETA'] = -beta
        C['HIBETA'] = beta
        C['TREND200'] = adj / P.rolling(200, min_periods=180).mean().values
        C['LOSER12'] = -C['MOM12']
    return C


def month_ends(dates):
    ms = pd.Series(np.arange(len(dates)), index=dates)
    return ms.groupby([dates.year, dates.month]).max().values


def hold_returns(adj, divy, mem, members, t0, t1, T):
    """equal-weight buy-and-hold of 'members' over days t0..t1 (inclusive), bought at close t0-1 (every member has a
    price there). Delisting is decided inside the window only, from what is known at t1 (ADDENDUM_SL1_B): L = last real
    price row <= t1; an exit is L < t1 and (the stock left the index by t1 or has not traded for >= 10 rows); then the lab
    rule applies on day L+1 (250-row return to L < -30% -> -50%, else 0; base = first price in the window) and the slot is
    cash. A member with a shorter no-trade gap at t1 is sold at its last price. Returns daily simple returns before the
    rebalance cost."""
    idx = np.asarray(members)
    seg = adj[t0 - 1:t1 + 1, idx]                                      # includes the purchase close
    segf = pd.DataFrame(seg).ffill().values
    with np.errstate(all='ignore'):
        rr = segf[1:] / segf[:-1] - 1
    rr = np.nan_to_num(rr)
    rr = rr - DTAX * divy[t0:t1 + 1, idx]
    fin = np.isfinite(seg)
    if t1 < T - 1:
        lastloc = seg.shape[0] - 1 - np.argmax(fin[::-1], 0)            # row in seg (0 = purchase close)
        for j in np.flatnonzero(lastloc < seg.shape[0] - 1):
            i = idx[j]; L = t0 - 1 + int(lastloc[j])
            if mem[t1, i] and t1 - L < 10: continue
            w = adj[max(0, L - 250):L + 1, i]; w = w[np.isfinite(w)]
            r250 = adj[L, i] / w[0] - 1 if len(w) else 0.0
            f = 0.5 if r250 < -0.30 else 1.0
            k = L + 1 - t0
            rr[k:, j] = 0.0
            rr[k, j] = f - 1.0
    V = np.cumprod(1 + rr, 0)                                           # per-stock value (start 1)
    port = V.mean(1)
    prev = np.r_[1.0, port[:-1]]
    return port / prev - 1


def build():
    dates, adj, mem, divy = load(); T, N = adj.shape
    fin = np.isfinite(adj)
    C = characteristics(adj, mem)
    me = month_ends(dates)
    tieb = np.random.default_rng(20261104).random(N) * 1e-12            # fixed tiny tiebreak (no symbol order)
    names = ['EW'] + ['%s_K%d' % (c, k) for c in CHARS for k in KS]
    OUT = {n: np.full(T, np.nan) for n in names}; NH = {n: [] for n in names}; TURN = {n: [] for n in names}
    for n in names:
        prev = None
        for j in range(len(me) - 1):
            tm = me[j]; t0 = tm + 3; t1 = min(me[j + 1] + 2, T - 1)
            if t0 > T - 1: break
            el = mem[tm] & fin[tm]
            buy = fin[t0 - 1]                                           # real price at the purchase close tm+2 (known then)
            if n == 'EW':
                sel = np.flatnonzero(el & buy)
            else:
                c, k = n.rsplit('_K', 1); k = int(k); x = C[c][tm]
                ok = el & np.isfinite(x)
                if ok.sum() < 3 * k: continue
                cand = np.flatnonzero(ok); sc = x[cand] + tieb[cand]
                order = cand[np.argsort(-sc, kind='stable')]
                sel = order[buy[order]][:k]                             # drop names with no trade at the purchase, refill by rank
            if len(sel) == 0: continue
            hr = hold_returns(adj, divy, mem, sel, t0, t1, T)
            s = set(sel.tolist())
            tau = 1.0 if prev is None else len(s - prev) / len(s)
            hr[0] = (1 + hr[0]) * (1 - 2 * COST * tau) - 1
            OUT[n][t0:t1 + 1] = hr; NH[n].append(len(sel)); TURN[n].append(tau); prev = s
    meta = {n: dict(first=str(dates[np.flatnonzero(np.isfinite(OUT[n]))[0]].date()), avg_names=float(np.mean(NH[n])),
                    avg_turnover=float(np.mean(TURN[n][1:]))) for n in names}
    np.savez(SCR + 'cache/sleeves.npz', dates=dates.values.astype('datetime64[D]').astype(np.int64), names=np.array(names),
             **{n: OUT[n] for n in names})
    json.dump(meta, open(SCR + 'cache/sleeves_meta.json', 'w'), indent=1)
    return names, OUT, meta, dates


if __name__ == '__main__':
    import time; t = time.time()
    names, OUT, meta, dates = build()
    for n in names: print(n, meta[n])
    print('%.0fs' % (time.time() - t))
