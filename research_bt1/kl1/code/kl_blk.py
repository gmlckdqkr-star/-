"""KL1 block engines for S1 (market ex-losers) and S3 (ex-loser sleeve + index product), numba.
Equal weight over held names each block; costs only for names entering / leaving (WS1 convention); entry fails
(KR limit-up / no trade at the entry close) -> name not bought this block (weight renormalised over the held names)."""
import numpy as np
from numba import njit, prange

C_STK = {'KR': 0.004, 'US': 0.003}      # sleeve-weight change cost (S3 transitions)
C_ETF = {'KR': 0.0015, 'US': 0.003}


@njit(cache=True)
def pct_ranks(sc, base):
    """sc [nb, N] float32 raw score, base [nb, N] bool -> percentile rank in [0,1] among base & finite (nan else)."""
    nb, N = sc.shape
    out = np.full((nb, N), np.nan, np.float32)
    idx = np.empty(N, np.int64); v = np.empty(N)
    for b in range(nb):
        m = 0
        for i in range(N):
            x = sc[b, i]
            if base[b, i] and x == x:
                idx[m] = i; v[m] = x; m += 1
        if m < 2:
            continue
        o = np.argsort(v[:m], kind='mergesort')
        for j in range(m):
            out[b, idx[o[j]]] = j / (m - 1)
    return out


@njit(cache=True)
def s1_returns(P, defs, nd, form, k, q, reg, base, R, entry, hsb, impf, kr, seed):
    """P [ndef, nb, N]; defs int[4]; form 0 single 1 comp 2 vote; reg [nb] int8 (1 = apply exclusion).
    KR costs: buy = hsb + impf*sqrt(seed/n), sell = buy + 0.003 (hsb = 0.00015 + half spread, impf = 0.7 s20 / sqrt(adv)).
    US: 0.003 per side. Returns net block returns r [nb] and number held [nb]."""
    nb, N = base.shape
    r = np.zeros(nb); nh = np.zeros(nb)
    prev = np.zeros(N, np.bool_); cur = np.zeros(N, np.bool_); fl = np.zeros(N, np.bool_)
    comp = np.empty(N); vals = np.empty(N)
    nprev = 0
    for b in range(nb):
        for i in range(N):
            fl[i] = False
        if reg[b] == 1 and q > 0:
            if form == 0:
                d = defs[0]
                for i in range(N):
                    v = P[d, b, i]
                    if v == v and v >= 1.0 - q:
                        fl[i] = True
            elif form == 1:
                m = 0
                for i in range(N):
                    s = 0.0; c = 0
                    for j in range(nd):
                        v = P[defs[j], b, i]
                        if v == v:
                            s += v; c += 1
                    if c > 0:
                        comp[i] = s / c; vals[m] = comp[i]; m += 1
                    else:
                        comp[i] = np.nan
                if m > 1:
                    srt = np.sort(vals[:m])
                    pos = int(np.floor((1.0 - q) * m))
                    if pos > m - 1:
                        pos = m - 1
                    thr = srt[pos]
                    for i in range(N):
                        if comp[i] == comp[i] and comp[i] >= thr:
                            fl[i] = True
            else:
                for i in range(N):
                    c = 0
                    for j in range(nd):
                        v = P[defs[j], b, i]
                        if v == v and v >= 1.0 - q:
                            c += 1
                    if c >= k:
                        fl[i] = True
        n = 0
        for i in range(N):
            cur[i] = base[b, i] and (not fl[i]) and (prev[i] or entry[b, i])
            if cur[i]:
                n += 1
        gr = 0.0; cnew = 0.0; cdrop = 0.0
        qk = seed / max(n, 1); qp = seed / max(nprev, 1)
        for i in range(N):
            if cur[i]:
                v = R[b, i]
                if v == v:
                    gr += v
                if not prev[i]:
                    cnew += (hsb[b, i] + impf[b, i] * np.sqrt(qk)) if kr else 0.003
            elif prev[i]:
                cdrop += (hsb[b, i] + impf[b, i] * np.sqrt(qp) + 0.003) if kr else 0.003
        if n > 0:
            r[b] = gr / n - cnew / n
        if nprev > 0:
            r[b] -= cdrop / nprev
        nh[b] = n
        for i in range(N):
            prev[i] = cur[i]
        nprev = n
    return r, nh


@njit(cache=True)
def s3_returns(rs, g, cw, gi, w, on, offmode, c_stk, c_etf):
    """rs sleeve block returns, g lever-product window returns, cw cash, gi inverse; on [nb] int8 (1 on / 0 off).
    Target weights (stock, lever, cash, inverse): on (1-w, w, 0, 0); off by mode: 0 (1,0,0,0) 1 (0,0,1,0)
    2 (1-w,0,w,0) 3 (1-w,0,0,w). Transition / drift cost = c_stk |d stock| + c_etf (|d lever| + |d inverse|)."""
    nb = rs.shape[0]
    r = np.zeros(nb)
    ws = 0.0; wl = 0.0; wc = 1.0; wi = 0.0          # start in cash
    for b in range(nb):
        if on[b] == 1:
            ts, tl, tc, ti = 1.0 - w, w, 0.0, 0.0
        elif offmode == 0:
            ts, tl, tc, ti = 1.0, 0.0, 0.0, 0.0
        elif offmode == 1:
            ts, tl, tc, ti = 0.0, 0.0, 1.0, 0.0
        elif offmode == 2:
            ts, tl, tc, ti = 1.0 - w, 0.0, w, 0.0
        else:
            ts, tl, tc, ti = 1.0 - w, 0.0, 0.0, w
        cost = c_stk * abs(ts - ws) + c_etf * (abs(tl - wl) + abs(ti - wi))
        if b == 0:
            cost = c_etf * (tl + ti)                  # sleeve entry cost already inside rs
        rb = ts * rs[b] + tl * g[b] + tc * cw[b] + ti * gi[b]
        r[b] = rb - cost
        den = 1.0 + rb
        if den <= 1e-9:
            den = 1e-9
        ws = ts * (1 + rs[b]) / den; wl = tl * (1 + g[b]) / den; wc = tc * (1 + cw[b]) / den; wi = ti * (1 + gi[b]) / den
    return r


@njit(cache=True)
def window_prod(Xc, e0, h, T):
    """compound product daily returns Xc over days e0+1 .. e0+h (held from close e0 to close e0+h)."""
    nb = e0.shape[0]; out = np.zeros(nb)
    for b in range(nb):
        g = 1.0
        for t in range(e0[b] + 1, min(e0[b] + h + 1, T)):
            g *= 1 + Xc[t]
        out[b] = g - 1
    return out


def monthly(lgdiff, mon, nmon):
    """sum block log differences into month slots (block -> month of its decision date)."""
    out = np.zeros(nmon, np.float64)
    np.add.at(out, mon, lgdiff)
    return out
