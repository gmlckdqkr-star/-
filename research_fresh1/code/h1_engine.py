"""FRESH1 H1 engine: multi-asset account with the same book-keeping as the locked MS1 engine (c3_brake/code/beng.py run1):
delay queue, cost on traded notional, average-cost basis, yearly tax on net realized gain above D, proportional tax payment,
year-end harvest, cash interest after 15.4% tax, final liquidation tax. One difference: N leveraged funds instead of one.
<=2014 data only (the caller cuts)."""
import numpy as np
from numba import njit

WARM = 300


@njit(cache=True)
def run_multi(R, RF, W, dec, W0, delay, cost, tax, D, harvest, hthr, cspr, er3, lev):
    """R (T,N) underlying daily returns (NaN = not available), RF (T,), W (T,N) target weights decided at close t where dec[t],
    W0 (N,) weights taken at k=0 (decided at close WARM-1). Returns (fin, mdd, ntrades, E path (T-WARM,), taxpaid, costpaid)."""
    T, N = R.shape
    v = np.zeros(N); b = np.zeros(N); cash = 0.0
    real = 0.0; taxp = 0.0; costp = 0.0; ntr = 0.0
    E = 1.0; pk = 1.0; mdd = 0.0
    EE = np.zeros(T - WARM)
    pend_t = -1; pend_w = np.zeros(N)
    for t in range(WARM, T):
        k = t - WARM
        if k > 0 and k % 252 == 0:
            due = tax * max(real - D, 0.0); real = 0.0
            if due > 0:
                tot = v.sum() + cash; taxp += due
                f = min(due / max(tot, 1e-300), 1.0)
                for i in range(N):
                    real += f * (v[i] - b[i]); v[i] *= (1 - f); b[i] *= (1 - f)
                cash *= (1 - f)
        if k > 0:
            for i in range(N):
                if v[i] > 0:
                    ri = R[t, i]
                    if np.isnan(ri): ri = 0.0
                    v[i] *= (1 + lev * ri - (lev - 1) * RF[t] - er3 / 252)
                    if v[i] < 0: v[i] = 0.0
            cash *= (1 + max(RF[t] - cspr / 252, 0.0) * (1 - 0.154))
        do = False
        if k == 0:
            tot = 1.0; cash = 1.0; w = W0; do = True
        elif pend_t == t:
            tot = v.sum() + cash; w = pend_w; do = True; pend_t = -1
        if do:
            tc = 0.0; chg = False
            for i in range(N):
                d0 = w[i] * tot - v[i]
                if abs(d0) > 1e-12 * max(tot, 1e-300): chg = True
                tc += cost * abs(d0)
            if chg:
                costp += tc
                sc = (tot - tc) / max(tot, 1e-300); sw = 0.0
                for i in range(N):
                    d0 = w[i] * tot - v[i]
                    if d0 < 0 and v[i] > 0:
                        fr = min(-d0 / v[i], 1.0); real += fr * (v[i] - b[i]); b[i] *= 1 - fr
                    if d0 > 0: b[i] += d0
                    v[i] = w[i] * tot * sc; sw += w[i]
                cash = (1 - sw) * tot * sc
                ntr += 1
        if harvest > 0 and k % 252 == 251:
            for i in range(N):
                if v[i] > 1e-12:
                    target = D - real; U = v[i] - b[i]; f = 0.0
                    if target < 0 and U < 0 and (harvest & 1): f = min(1.0, target / U)
                    if target > 0 and U > 0 and (harvest & 2): f = min(1.0, target / U)
                    rz = f * U; sv = f * v[i]
                    if sv > 0 and tax * abs(rz) > hthr * 2 * cost * sv:
                        tc = 2 * cost * sv; costp += tc
                        real += rz; b[i] = b[i] - (sv - rz) + (sv - tc)
                        v[i] -= tc
        E = v.sum() + cash
        if E > pk: pk = E
        if E / pk - 1 < mdd: mdd = E / pk - 1
        EE[k] = E
        if dec[t]:
            pend_t = t + delay
            for i in range(N): pend_w[i] = W[t, i]
    unr = 0.0
    for i in range(N): unr += v[i] - b[i]
    fin = E - tax * max(real + unr - D, 0.0)
    return fin, mdd, ntr, EE, taxp, costp


def signals(R, K, look, dec, trend_n=200):
    """Target weights at decision days. R (T,N) returns with NaN where unavailable. look = '12-1' or '6'.
    Uses only data up to and including day t."""
    T, N = R.shape
    ok = ~np.isnan(R); r0 = np.where(ok, R, 0.0)
    lvl = np.cumprod(1 + r0, axis=0)
    cnt = np.cumsum(ok, axis=0)                        # valid days so far
    cs = np.cumsum(np.vstack([np.zeros((1, N)), lvl]), axis=0)
    sma = np.full((T, N), np.nan); sma[trend_n - 1:] = (cs[trend_n:] - cs[:-trend_n]) / trend_n
    mom = np.full((T, N), np.nan)
    if look == '12-1': mom[252:] = lvl[252 - 21:T - 21] / lvl[:T - 252] - 1; need = 253
    else: mom[126:] = lvl[126:] / lvl[:T - 126] - 1; need = 253
    W = np.zeros((T, N))
    for t in np.flatnonzero(dec):
        elig = (cnt[t] >= need) & ok[t] & (lvl[t] > sma[t]) & ~np.isnan(mom[t])
        if not elig.any(): continue
        m = np.where(elig, mom[t], -np.inf)
        top = np.argsort(-m, kind='stable')[:K]
        top = top[np.isfinite(m[top])]
        W[t, top] = 1.0 / K
    return W


def trend_only(R, dec, col, trend_n=200):
    """Benchmark: 100% in one fund when its index is above its own 200-day average at the decision day, else cash."""
    T, N = R.shape
    r0 = np.nan_to_num(R[:, col]); lvl = np.cumprod(1 + r0)
    cs = np.cumsum(np.r_[0.0, lvl]); sma = np.full(T, np.nan); sma[trend_n - 1:] = (cs[trend_n:] - cs[:-trend_n]) / trend_n
    W = np.zeros((T, N)); d = np.flatnonzero(dec)
    W[d, col] = (lvl[d] > sma[d]).astype(float)
    return W


MS1 = dict(delay=2, cost=0.003, tax=0.22, D=0.25, harvest=3, hthr=1.0, cspr=0.02, er3=0.0245, lev=3.0)
SEALED = dict(delay=2, cost=0.004, tax=0.22, D=0.0, harvest=0, hthr=1.0, cspr=0.02, er3=0.0295, lev=3.0)


def account(R, RF, W, dec, terms):
    i0 = WARM - 1
    fin, mdd, ntr, EE, taxp, costp = run_multi(np.ascontiguousarray(R, dtype=np.float64), np.ascontiguousarray(RF, dtype=np.float64),
                                               np.ascontiguousarray(W), np.ascontiguousarray(dec), np.ascontiguousarray(W[i0]),
                                               int(terms['delay']), terms['cost'], terms['tax'], terms['D'], int(terms['harvest']), terms['hthr'],
                                               terms['cspr'], terms['er3'], terms['lev'])
    yrs = (R.shape[0] - WARM) / 252
    return dict(cagr=max(fin, 1e-9) ** (1 / yrs) - 1, mdd=mdd, ntr=ntr, yrs=yrs, taxp=taxp, costp=costp), EE
