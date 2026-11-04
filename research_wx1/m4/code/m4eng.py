"""WX1-M4 fast screen engine. Pre-tax, after cost, MS1 section-1 trading rules (ms1eng.run1 with tax 0 / harvest 0):
decision at close t -> trade at close t+2 (delay 2), 0.3 % per side on traded risk notional (cash free), drift between
trades, full re-trade to target when the target changes or on a forced rebalance row. Product returns:
  L = 1: u - fee1/252 (NDX/SPX 0.20 %, LTB/MTB 0.15 %, other 0.40 %); L = 2,3: L u - (L-1) rf - 2.45 %/252;
  L = -1: -u_TR + 2 rf - 2.45 %/252;  CASH: max(rf - 2 %/252, 0)(1 - 15.4 %) (MS1).
Signals read rows <= t only. Env(end=...) truncates every input at `end` BEFORE any signal is computed (discovery runs
never compute a post-1999 row)."""
import os, numpy as np, pandas as pd
from numba import njit
S = '/tmp/claude-0/-home-user--/2eb0924b-5db4-5355-95b4-4813e05ee05d/scratchpad/m4/'
LEVS = (-1, 1, 2, 3)
FEE1 = {'NDX': 0.002, 'SPX': 0.002, 'LTB': 0.0015, 'MTB': 0.0015}
SECT = ['TECH', 'SEMI', 'FIN', 'HLTH', 'ENER', 'REIT', 'UTIL', 'INDU', 'DISC', 'RETL', 'HOME', 'BANK', 'BIO', 'TRAN',
        'AERO', 'GOLDM', 'MATL', 'STAP', 'TELE']
UNIV = {
    'SECT': SECT,
    'SECT3': [s for s in SECT if s not in ('MATL', 'STAP', 'TELE')],
    'EQ': SECT + ['NDX', 'SPX', 'SMALL'],
    'MULTI': SECT + ['NDX', 'SPX', 'SMALL', 'LTB', 'MTB', 'GOLD'],
    'CORE': ['NDX', 'SPX', 'SMALL', 'LTB', 'MTB', 'GOLD'],
    'FACT': ['NDX', 'SPX', 'SMALL', 'MOM', 'QUAL', 'VAL'],
    'GROW': ['NDX', 'TECH', 'SEMI', 'BIO', 'DISC', 'SMALL'],
    'DEF': ['LTB', 'MTB', 'GOLD', 'UTIL', 'STAP', 'HLTH'],
    'NLG': ['NDX', 'LTB', 'GOLD'],
    'NL': ['NDX', 'LTB'],
    'SL': ['SPX', 'LTB'],
    'NSL': ['NDX', 'SPX', 'LTB'],
    'CLS': ['NDX', 'SMALL', 'LTB', 'MTB', 'GOLD'],
}
_BASE = None


def base():
    global _BASE
    if _BASE is None:
        _BASE = pd.read_pickle(S + 'data/m4_base.pkl')
    return _BASE


@njit(cache=True)
def run_pre(R, CR, W, FORCE, t0, delay, cost):
    """ms1eng.run1 with tax = 0 and harvest = 0 (same loop, same delay queue, same trade/cost rule). Returns equity
    E[t - t0] for t >= t0 and the trade count."""
    T, Sn = R.shape
    v = np.zeros(Sn); cash = 0.0
    q = np.zeros((delay + 1, Sn)); qf = np.zeros(delay + 1)
    cur = np.full(Sn, -99.0); held = np.zeros(Sn)
    Erec = np.zeros(T - t0); ntr = 0
    for t in range(T):
        if t >= t0:
            k = t - t0
            want = q[0].copy(); fw = qf[0]
            for j in range(delay - 1):
                q[j] = q[j + 1]; qf[j] = qf[j + 1]
            if k > 0:
                for s in range(Sn):
                    v[s] *= 1 + R[t, s]
                cash *= 1 + CR[t]
            chg = fw > 0 or k == 0
            for s in range(Sn):
                if want[s] != cur[s]:
                    chg = True
            if chg:
                tot = cash
                for s in range(Sn):
                    tot += v[s]
                if k == 0:
                    tot = 1.0; cash = 1.0
                tc = 0.0
                for s in range(Sn):
                    tc += cost * abs(want[s] * tot - v[s])
                sc = (tot - tc) / max(tot, 1e-300)
                ws = 0.0
                for s in range(Sn):
                    v[s] = want[s] * tot * sc; ws += want[s]; cur[s] = want[s]
                cash = (1 - ws) * tot * sc
                ntr += 1
            E = cash
            for s in range(Sn):
                E += v[s]
            Erec[t - t0] = E
        for s in range(Sn):
            x = W[t, s]
            held[s] = 0.0 if np.isnan(x) else x
        if t == t0 - 1:
            for j in range(delay):
                q[j] = held.copy(); qf[j] = 0.0
        elif t >= t0:
            q[delay - 1] = held.copy(); qf[delay - 1] = 1.0 if FORCE[t] else 0.0
    return Erec, ntr


def _first_days(idx, freq):
    p = idx.to_period(freq)
    m = np.r_[True, p[1:] != p[:-1]]
    return np.flatnonzero(m)


class Env:
    def __init__(self, end='1999-12-31', start_eval='1964-01-02'):
        B = base()
        end = pd.Timestamp(end)
        U = B['U']; idx = U.index[U.index <= end]          # truncate first
        self.idx = idx; self.T = T = len(idx)
        self.U = U.loc[idx]; self.UTR = B['UTR'].loc[idx]
        self.rf = B['rf'].loc[idx].values.astype(float); self.cash = B['cash'].loc[idx].values.astype(float)
        self.bench = B['bench'].loc[idx].values.astype(float)
        self.macro = B['macro'].loc[idx]
        self.maxL = B['maxL']; self.inv_ok = set(B['inv_ok'])
        self.assets = list(U.columns); self.ai = {a: i for i, a in enumerate(self.assets)}
        u = self.U.values.astype(float); self.u = u
        self.avail = ~np.isnan(u)
        self.t0 = int(idx.searchsorted(pd.Timestamp(start_eval)))
        lu = np.log1p(np.nan_to_num(u))
        lp = np.cumsum(lu, axis=0)
        started = np.maximum.accumulate(self.avail, axis=0)
        lp[~started] = np.nan
        self.logp = lp
        self.crf = np.cumsum(np.log1p(self.rf))
        # products
        self.prods = []; cols = []
        for a in self.assets:
            for L in LEVS:
                if L == -1 and a not in self.inv_ok: continue
                if L > self.maxL[a]: continue
                self.prods.append((a, L)); cols.append(self._pret(a, L))
        self.prods.append(('CASH', 0)); cols.append(self.cash)
        self.PR = np.nan_to_num(np.column_stack(cols))
        self.PAV = np.column_stack([self.avail[:, self.ai[a]] if a != 'CASH' else np.ones(T, bool) for a, L in self.prods])
        self.pi = {p: i for i, p in enumerate(self.prods)}
        self.dd = {f: _first_days(idx, f) for f in ('W', 'M', 'Q')}
        mk = idx.to_period('M'); self.mkey = mk
        self._c = {}
        # month id per day for aggregation
        self.mid = np.r_[0, np.cumsum(mk[1:] != mk[:-1])]
        self.months = mk[np.r_[True, mk[1:] != mk[:-1]]]

    def _pret(self, a, L):
        u = self.u[:, self.ai[a]]
        if L == 1: return u - FEE1.get(a, 0.004) / 252
        if L == -1: return -self.UTR[a].values + 2 * self.rf - 0.0245 / 252
        return L * u - (L - 1) * self.rf - 0.0245 / 252

    # ---------------- signals (rows <= t) ----------------
    def ret(self, L, skip=0):
        k = ('ret', L, skip)
        if k not in self._c:
            lp = self.logp; T = self.T
            a = L + skip
            x = np.full_like(lp, np.nan)
            x[a:] = np.exp(lp[L:T - skip] - lp[:T - a]) - 1
            self._c[k] = x
        return self._c[k]

    def exret(self, L, skip=0):
        """window log return minus window cash log return (dual-momentum absolute test > 0)"""
        k = ('exret', L, skip)
        if k not in self._c:
            lp = self.logp; T = self.T; a = L + skip
            x = np.full_like(lp, np.nan)
            x[a:] = (lp[L:T - skip] - lp[:T - a]) - (self.crf[L:T - skip] - self.crf[:T - a])[:, None]
            self._c[k] = x
        return self._c[k]

    def vol(self, n):
        k = ('vol', n)
        if k not in self._c:
            lr = pd.DataFrame(np.log1p(self.u))
            self._c[k] = (lr.rolling(n, min_periods=n).std() * np.sqrt(252)).values
        return self._c[k]

    def sma_up(self, n):
        k = ('sma', n)
        if k not in self._c:
            P = pd.DataFrame(np.exp(self.logp))
            m = P.rolling(n, min_periods=n).mean().values
            with np.errstate(invalid='ignore'):
                self._c[k] = np.where(np.isnan(m), np.nan, (np.exp(self.logp) > m).astype(float))
        return self._c[k]

    def cross_up(self):
        k = ('x50200',)
        if k not in self._c:
            P = pd.DataFrame(np.exp(self.logp))
            a = P.rolling(50, min_periods=50).mean().values; b = P.rolling(200, min_periods=200).mean().values
            with np.errstate(invalid='ignore'):
                self._c[k] = np.where(np.isnan(b), np.nan, (a > b).astype(float))
        return self._c[k]

    def corr(self, x, y, n):
        k = ('corr', x, y, n)
        if k not in self._c:
            a = pd.Series(self.u[:, self.ai[x]]); b = pd.Series(self.u[:, self.ai[y]])
            self._c[k] = a.rolling(n, min_periods=n).corr(b).values
        return self._c[k]

    def disp(self):
        """cross-sectional std of sector 21d returns; flag = above its own trailing 252d median"""
        k = ('disp',)
        if k not in self._c:
            r = self.ret(21)[:, [self.ai[s] for s in SECT]]
            with np.errstate(all='ignore'):
                d = np.nanstd(r, axis=1)
            d[np.sum(~np.isnan(r), axis=1) < 10] = np.nan
            med = pd.Series(d).rolling(252, min_periods=200).median().values
            self._c[k] = np.where(np.isnan(med), np.nan, (d > med).astype(float))
        return self._c[k]

    def acorr(self):
        """average pairwise 63d correlation of the sectors (equal-weight variance identity); flag = above trailing 252d median"""
        k = ('acorr',)
        if k not in self._c:
            X = pd.DataFrame(self.u[:, [self.ai[s] for s in SECT]])
            n = X.shape[1]
            vi = X.rolling(63, min_periods=63).var()
            sd = np.sqrt(vi)
            vp = X.mean(axis=1).rolling(63, min_periods=63).var()
            num = vp * n * n - vi.sum(axis=1)
            den = sd.sum(axis=1) ** 2 - vi.sum(axis=1)
            ac = (num / den).values
            med = pd.Series(ac).rolling(252, min_periods=200).median().values
            self._c[k] = np.where(np.isnan(med), np.nan, (ac > med).astype(float))
        return self._c[k]

    def gate(self, g):
        """daily True = risk on. Unknown (warm-up) = on."""
        k = ('gate', g)
        if k in self._c: return self._c[k]
        T = self.T; n = self.ai['NDX']; s = self.ai['SPX']
        def up(arr, j): x = arr[:, j]; return np.where(np.isnan(x), 1.0, x) > 0.5
        M = self.macro
        mac = ~(M['inv'].values | M['shock'].values | M['csj'].values)
        if g == 'none': out = np.ones(T, bool)
        elif g == 'ndx200': out = up(self.sma_up(200), n)
        elif g == 'ndx100': out = up(self.sma_up(100), n)
        elif g == 'spx200': out = up(self.sma_up(200), s)
        elif g == 'macro': out = mac
        elif g == 'ndxvol25':
            v = self.vol(21)[:, n]; out = np.where(np.isnan(v), True, v < 0.25)
        elif g == 'ndx12m':
            x = self.exret(252)[:, n]; out = np.where(np.isnan(x), True, x > 0)
        elif g == 'macro_ndx200': out = mac & up(self.sma_up(200), n)
        else: raise ValueError(g)
        self._c[k] = out
        return out

    # ---------------- score / flag lookup ----------------
    def score(self, sc):
        """sc = ('ret', L, skip) | ('radj', L) | ('comp',) | ('rev', L) | ('lowvol', n)"""
        if sc[0] == 'ret': return self.ret(sc[1], sc[2])
        if sc[0] == 'radj':
            with np.errstate(all='ignore'): return self.ret(sc[1], 0) / self.vol(63)
        if sc[0] == 'comp':
            k = ('comp',)
            if k not in self._c:
                self._c[k] = (self.ret(21) + self.ret(63) + self.ret(126) + self.ret(252)) / 4
            return self._c[k]
        if sc[0] == 'rev': return -self.ret(sc[1], 0)
        if sc[0] == 'lowvol': return -self.vol(sc[1])
        raise ValueError(sc)

    def flag(self, f, L=252, skip=0):
        """per-asset eligibility filter (T x A float, nan = unknown -> not eligible)"""
        if f == 'none': return None
        if f == 'dm': x = self.exret(L, skip); return np.where(np.isnan(x), np.nan, (x > 0).astype(float))
        if f == 'sma200': return self.sma_up(200)
        if f == 'sma100': return self.sma_up(100)
        if f == 'sma50': return self.sma_up(50)
        if f == 'x50200': return self.cross_up()
        if f.startswith('tsm'):
            x = self.exret(int(f[3:]) * 21); return np.where(np.isnan(x), np.nan, (x > 0).astype(float))
        raise ValueError(f)

    # ---------------- run ----------------
    def run_W(self, W, FORCE):
        """W: T x nprod target weights at close t (products unavailable at t -> cash). Returns daily strategy returns
        for t >= t0 and trade count."""
        W = np.where(self.PAV, W, 0.0)
        used = np.flatnonzero(np.abs(W).sum(axis=0) > 0)
        used = used[used != self.pi[('CASH', 0)]]
        if len(used) == 0:
            used = np.array([self.pi[('CASH', 0)]])
            Wu = np.zeros((self.T, 1)); Ru = np.zeros((self.T, 1))
        else:
            Wu = np.ascontiguousarray(W[:, used]); Ru = np.ascontiguousarray(self.PR[:, used])
        E, ntr = run_pre(Ru, np.ascontiguousarray(self.cash), Wu, np.ascontiguousarray(FORCE), self.t0, 2, 0.003)
        r = np.empty_like(E); r[0] = E[0] - 1.0; r[1:] = E[1:] / E[:-1] - 1.0
        return r, ntr

    def monthly_diff(self, r, ref=None):
        """monthly sum of log(1+r) - log(1+ref) for months starting at t0 (ref default = 1x NDX bench)"""
        ref = self.bench[self.t0:] if ref is None else ref
        x = np.log1p(r) - np.log1p(ref)
        mid = self.mid[self.t0:] - self.mid[self.t0]
        return np.bincount(mid, weights=x)
