"""WX1-M4 rule grammar -> daily target weights (T x products) + forced-rebalance rows. Decisions at the first trading day
of each week / month / quarter (lab convention), read rows <= t only; the engine applies delay 2."""
import numpy as np
from m4eng import UNIV, SECT


def _ff(env, dd, Wd):
    """decision rows (nD x P) -> daily (T x P) forward filled; rows before the first decision = 0 (cash)"""
    T = env.T
    pos = np.searchsorted(dd, np.arange(T), side='right') - 1
    W = np.zeros((T, Wd.shape[1]))
    ok = pos >= 0
    W[ok] = Wd[pos[ok]]
    F = np.zeros(T, bool); F[dd] = True
    return W, F


def _prod_col(env, a, L):
    L = min(L, env.maxL[a]) if L > 0 else L
    return env.pi[(a, L)]


def _fallback(env, dd, fb):
    """(nD x P) unit weights of the fallback product per decision row"""
    P = len(env.prods); out = np.zeros((len(dd), P))
    if fb == 'CASH':
        return out
    if fb in ('LTB1', 'MTB1', 'GOLD1'):
        a = fb[:-1]; j = env.pi[(a, 1)]
        out[:, j] = env.avail[dd, env.ai[a]].astype(float)      # unavailable -> cash
        return out
    if fb == 'DEF':
        U = UNIV['DEF']; ix = [env.ai[a] for a in U]
        s = env.ret(63)[dd][:, ix]
        s = np.where(np.isnan(s), -np.inf, s)
        b = np.argmax(s, axis=1); okr = np.isfinite(s[np.arange(len(dd)), b])
        for r in np.flatnonzero(okr):
            out[r, env.pi[(U[b[r]], 1)]] = 1.0
        return out
    raise ValueError(fb)


def xs_select(env, dd, U, SC, K, wt, FL):
    """top-K by score among eligible assets of U at decision rows dd. -> asset weights (nD x |U|), filled share (nD,)"""
    ix = [env.ai[a] for a in U]
    s = SC[dd][:, ix].copy()
    elig = ~np.isnan(s)
    if FL is not None:
        f = FL[dd][:, ix]; elig &= (np.nan_to_num(f) > 0.5)
    s[~elig] = -np.inf
    K = min(K, len(U))
    order = np.argsort(-s, axis=1, kind='stable')[:, :K]
    rows = np.arange(len(dd))[:, None]
    sel = np.isfinite(s[rows, order])
    Wa = np.zeros_like(s)
    if wt == 'eq':
        Wa[rows, order] = sel / K
    else:  # inverse vol among the selected, total = m / K
        v = env.vol(63)[dd][:, ix]
        iv = np.where(np.isnan(v) | (v <= 0), 0.0, 1.0 / np.where(v > 0, v, 1.0))
        g = np.zeros_like(s); g[rows, order] = sel * iv[rows, order]
        tot = g.sum(axis=1, keepdims=True); m = sel.sum(axis=1, keepdims=True)
        Wa = np.where(tot > 0, g / np.where(tot > 0, tot, 1) * (m / K), 0.0)
    return Wa, Wa.sum(axis=1)


def _assets_to_prod(env, U, Wa, lev):
    P = len(env.prods); out = np.zeros((Wa.shape[0], P))
    for j, a in enumerate(U):
        out[:, _prod_col(env, a, lev)] += Wa[:, j]
    return out


def _dd(env, reb):
    return env.dd['M'] if reb == 'M3T' else env.dd[reb]


def _tranche(Wd, reb):
    if reb != 'M3T': return Wd
    a = Wd.copy(); n = np.ones((len(Wd), 1))
    a[1:] += Wd[:-1]; n[1:] += 1
    a[2:] += Wd[:-2]; n[2:] += 1
    return a / n


def comp_dec(env, r):
    """rule component -> (dd, decision weights nD x P)"""
    f = r['fam']
    dd = _dd(env, r['reb'])
    if f in ('XSM', 'MR'):
        U = UNIV[r['U']]; SC = env.score(tuple(r['score']))
        L = r['score'][1] if r['score'][0] == 'ret' else 252
        sk = r['score'][2] if r['score'][0] == 'ret' else 0
        FL = env.flag(r['filt'], L=max(L, 21), skip=sk) if r['filt'] != 'mkt200' else None
        Wa, fill = xs_select(env, dd, U, SC, r['K'], r['wt'], FL)
        Wd = _assets_to_prod(env, U, Wa, r['lev'])
        if r['filt'] == 'mkt200':                      # market filter: NDX above its 200d SMA, else all to fallback
            m = np.nan_to_num(env.sma_up(200)[dd, env.ai['NDX']], nan=1.0) > 0.5
            Wd[~m] = 0.0; fill = np.where(m, fill, 0.0)
        Wd += (1 - fill)[:, None] * _fallback(env, dd, r['fb'])
        return dd, Wd
    if f == 'TSM':
        U = UNIV[r['U']]; ix = [env.ai[a] for a in U]
        on = np.nan_to_num(env.flag(r['sig'])[dd][:, ix]) > 0.5
        if r['wt'] == 'eq':
            share = np.ones((len(dd), len(U))) / len(U)
        else:
            v = env.vol(63)[dd][:, ix]; iv = np.where(np.isnan(v) | (v <= 0), 0.0, 1 / np.where(v > 0, v, 1))
            tot = iv.sum(axis=1, keepdims=True)
            share = np.where(tot > 0, iv / np.where(tot > 0, tot, 1), 1.0 / len(U))
        Wa = share * on
        Wd = _assets_to_prod(env, U, Wa, r['lev'])
        Wd += (1 - Wa.sum(axis=1))[:, None] * _fallback(env, dd, r['fb'])
        return dd, Wd
    if f == 'VT':
        a = r['A']; j = env.ai[a]
        v = env.vol(r['vn'])[dd, j]
        e = np.where(np.isnan(v) | (v <= 0), 0.0, np.minimum(r['lmax'], r['tv'] / np.where(v > 0, v, 1)))
        if r['filt'] != 'none':
            m = np.nan_to_num(env.flag(r['filt'])[dd, j]) > 0.5; e = np.where(m, e, 0.0)
        P = len(env.prods); Wd = np.zeros((len(dd), P))
        if r['ladder']:
            for L in (1, 2, 3):
                lo = L - 1; m = (e > lo) & (e <= L) if L > 1 else (e <= 1)
                if L > env.maxL[a]: continue
                Wd[m, _prod_col(env, a, L)] = e[m] / L
            used = Wd.sum(axis=1)
        else:
            Lm = env.maxL[a]; Wd[:, _prod_col(env, a, Lm)] = e / Lm; used = e / Lm
        Wd += np.clip(1 - used, 0, 1)[:, None] * _fallback(env, dd, r['fb'])
        return dd, Wd
    if f == 'RP':
        U = UNIV[r['U']]; ix = [env.ai[a] for a in U]
        v = env.vol(r['vn'])[dd][:, ix]
        iv = np.where(np.isnan(v) | (v <= 0), 0.0, 1 / np.where(v > 0, v, 1))
        tot = iv.sum(axis=1, keepdims=True)
        w = np.where(tot > 0, iv / np.where(tot > 0, tot, 1), 0.0)
        if r['filt'] != 'none':
            m = np.nan_to_num(env.flag(r['filt'])[dd][:, ix]) > 0.5; w = w * m
        k = np.ones(len(dd))
        if r['tv']:
            # portfolio vol from the unlevered weights (63d covariance of base returns), scale so lev x vol <= tv
            X = np.nan_to_num(env.u[:, ix])
            pv = np.zeros(len(dd))
            for q, t in enumerate(dd):
                if t < 63: continue
                C = np.cov(X[t - 62:t + 1].T) * 252
                pv[q] = np.sqrt(max(w[q] @ C @ w[q], 1e-12))
            Le = np.array([min(r['lev'], env.maxL[a]) for a in U])
            k = np.where(pv > 0, np.minimum(1.0, r['tv'] / (pv * r['lev'])), 0.0)
        Wa = w * k[:, None]
        Wd = _assets_to_prod(env, U, Wa, r['lev'])
        Wd += np.clip(1 - Wa.sum(axis=1), 0, 1)[:, None] * _fallback(env, dd, r['fb'])
        return dd, Wd
    if f == 'CORR':
        x, y = r['pair'].split('-')
        c = env.corr(x, y, r['n'])[dd]
        st = np.nan_to_num(c, nan=1.0) < r['c']
        P = len(env.prods); Wd = np.zeros((len(dd), P))
        jx, jy = _prod_col(env, x, r['lev']), _prod_col(env, y, r['lev'])
        Wd[st, jx] = r['w']; Wd[st, jy] = 1 - r['w']
        ns = ~st
        if r['else'] == 'FULL': Wd[ns, jx] = 1.0
        elif r['else'] == 'WCASH': Wd[ns, jx] = r['w']
        return dd, Wd
    if f in ('DISP', 'ACORR'):
        U = UNIV[r['U']]; SC = env.score(tuple(r['score']))
        Wa, fill = xs_select(env, dd, U, SC, r['K'], 'eq', None)
        Wrot = _assets_to_prod(env, U, Wa, r['lev']) + (1 - fill)[:, None] * _fallback(env, dd, 'CASH')
        flag = (env.disp() if f == 'DISP' else env.acorr())[dd]
        hi = np.nan_to_num(flag, nan=0.0) > 0.5
        P = len(env.prods)
        if f == 'DISP':
            Walt = np.zeros((len(dd), P)); Walt[:, _prod_col(env, 'NDX', r['lev'])] = 1.0
            use_rot = hi if r['map'] == 'hi_rot' else ~hi
        else:
            Walt = _fallback(env, dd, r['def'])
            use_rot = ~hi
        Wd = np.where(use_rot[:, None], Wrot, Walt)
        return dd, Wd
    if f == 'CS':
        P = len(env.prods)
        core = np.zeros((len(dd), P))
        g = env.gate(r['cgate'])[dd]
        core[g, _prod_col(env, 'NDX', r['cl'])] = 1.0
        core[~g] = _fallback(env, dd, r['cfb'])[~g]
        sat = dict(fam='XSM', U=r['U'], score=r['score'], K=r['K'], wt='eq', lev=r['lev'], filt='none', fb='CASH', reb=r['reb'])
        _, Ws = comp_dec(env, sat)
        return dd, r['cshare'] * core + (1 - r['cshare']) * Ws
    raise ValueError(f)


def _gate_off(env, W, goff):
    if goff == 'CASH': return np.zeros_like(W)
    if goff == 'LTB1':
        out = np.zeros_like(W); out[:, env.pi[('LTB', 1)]] = 1.0; return out
    if goff == 'DELEV':
        out = np.zeros_like(W)
        for j, (a, L) in enumerate(env.prods):
            if a == 'CASH' or L == -1: continue
            out[:, env.pi[(a, 1)]] += W[:, j]
        return out
    raise ValueError(goff)


def weights(env, r):
    """full rule (incl. PAIR) -> daily W (T x P), FORCE (T,)"""
    if r['fam'] == 'PAIR':
        W1, F1 = weights(env, r['r1']); W2, F2 = weights(env, r['r2'])
        return r['alpha'] * W1 + (1 - r['alpha']) * W2, F1 | F2
    dd, Wd = comp_dec(env, r)
    Wd = _tranche(Wd, r['reb'])
    W, F = _ff(env, dd, Wd)
    g = r.get('gate', 'none')
    if g != 'none':
        G = env.gate(g)
        if r.get('gfreq', 'D') == 'R':
            Gd, _ = _ff(env, dd, G[dd].astype(float)[:, None]); G = Gd[:, 0] > 0.5
        Woff = _gate_off(env, W, r['goff'])
        W = np.where(G[:, None], W, Woff)
    return W, F


def run_rule(env, r):
    W, F = weights(env, r)
    return env.run_W(W, F)
