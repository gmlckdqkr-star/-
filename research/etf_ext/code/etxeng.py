"""ETX engine: s0.85 + wider-ETF sleeves on the five MS1 bases (<=2014). Account = user_port_up upeng.run_port
(verified: s0.85 alone == MS1 std on all 5 bases, path diff 0). Every stream is gathered with the SAME row index c.ii as the MS1
NDX path. MS1 conditions: 0.3 %/side, 22 % yearly net realized - D 0.25, no carry-forward, year-end harvest, final liquidation tax,
cash max(rf-2%,0)*0.846, distributions 15.4 % at year end, delay 2 (s0.85 levels from beng.run_path are already in force)."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/measure_std'); sys.path.insert(0, '/mnt/project-files/research/user_port_up/code')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import std, jp, iv
import upeng as E
import etxdata as XD
WARM = E.WARM
CACHE = XD.CACHE
BASES = ['dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85']
_D = {}
STRESS = dict(lev_extra=0.0, bond_haircut=0.0, trend_scale=1.0, by_date=None, eq_bonus=0.0)   # sensitivity switches (0 = MS1 base)


def basis_dates():
    if 'bd' in _D: return _D['bd']
    out = {}
    R, M = jp.calendar('1984-01-03', '2014-12-31'); X = jp.mkX(R, M, 'NDX'); out['real_ndx_86_14'] = X.index
    a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX')
    out['dev250_glued'] = X.index; out['dev250_path'] = X.index
    R, M = jp.calendar('1928-01-03', '1985-12-31'); X = jp.mkX(R, M, 'SPX')
    out['real_spx_55_85'] = X.index; out['real_spx_70_85'] = X.index
    _D['bd'] = out; return out


def pool_context(pool):
    """dev path basis on another iv pool (e8699 / e0014), built exactly like std.contexts()['dev250_path'] (flags recomputed on the path)"""
    key = 'pool_' + pool
    if key in _D: return _D[key]
    import ov
    a, b, P, blk, seed = iv.POOLS[pool]; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
    ii = ov.boot_idx(len(X), P=P, years=30, block=blk, seed=seed, lo=1)
    c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}
    _D[key] = (c, X.index); return _D[key]


def context(bn):
    if bn.startswith('pool_'): return pool_context(bn[5:])
    return std.contexts()[bn], basis_dates()[bn]


class Basis:
    def __init__(self, bn):
        self.bn = bn; self.c, dates = context(bn); assert len(dates) > self.c.ii.max()
        src = STRESS['by_date']() if STRESS['by_date'] else XD.by_date()
        self.D = src.reindex(dates)
        self.P, self.T = self.c.ii.shape; self.K = self.T - WARM
        self.rf = np.asarray(self.c.rf, float); self.rN = np.asarray(self.c.r, float)
        self._g = {}

    def g(self, name):
        """gathered stream (P,T), NaN where the source has no data"""
        if name not in self._g:
            v = self.D[name].values.astype(float)[self.c.ii]; v[:, 0] = 0.0; self._g[name] = v
        return self._g[name]

    def cover(self, name):
        """share of scored rows (k >= WARM) with data, path median"""
        v = self.g(name)[:, WARM:]; return float(np.median(np.mean(np.isfinite(v), axis=1)))

    def z(self, name):
        return np.nan_to_num(self.g(name), nan=0.0)


# ---------------- product recipes: name -> (r, dg, do, needs) on a Basis; all (P,T) ----------------
def _lev(b, x, L):
    f = b.rf; return L * x - (L - 1) * f - (0.0095 + 0.0075 * (L - 1) + STRESS['lev_extra'] * (L - 1)) / 252

BOND = {'SHY', 'IEF', 'TLT', 'EDV'}
EQ1 = {'XLU', 'XLP', 'XLV', 'IWN', 'IWD', 'IWM', 'IWF', 'VTI', 'MTUM', 'QUAL', 'IYR', 'GDX', 'XLK', 'XLE', 'XLF', 'XLI', 'XLB', 'XLY',
       'SOXX', 'IGV', 'PJP', 'KBE', 'TEL', 'DUR', 'EFA', 'VGK', 'EWJ_P'}
LEVMAP = {'UST': ('IEF', 2), 'TYD': ('IEF', 3), 'UBT': ('TLT', 2), 'TMF': ('TLT', 3), 'EDV2': ('EDV', 2),
          'SSO': ('U_SPX', 2), 'UPRO': ('U_SPX', 3), 'QLD': ('NDX', 2),
          # stage 3: real US-listed 3x equity ETFs on BE1 1x streams (KF proxy before listing, ACTUAL 1x ETF after)
          'TNA': ('IWM', 3), 'TECL': ('XLK', 3), 'CURE': ('XLV', 3), 'UTSL': ('XLU', 3), 'FAS': ('XLF', 3), 'SOXL': ('SOXX', 3),
          'WANT': ('XLY', 3), 'DUSL': ('XLI', 3), 'DRN': ('IYR', 3)}


def product(b, name, cash_kind='ms1'):
    f = b.rf; P, T = f.shape; zero = np.zeros((P, T))
    if name == 'TQQQ': return 3 * b.rN - 2 * f - 0.0245 / 252, zero, zero, []
    if name == 'QQQ': return b.rN - 0.002 / 252, zero, zero, []
    if name == 'CASH':
        if cash_kind == 'ms1': return np.maximum(f - 0.02 / 252, 0.0) * (1 - 0.154), zero, zero, []
        if cash_kind == 'rp1': return np.maximum(f - 0.01 / 252, 0.0) * (1 - 0.154), zero, zero, []
        if cash_kind == 'sgov': return np.maximum(f - 0.0009 / 252, 0.0) * (1 - 0.154), zero, zero, []
    if name in BOND:
        x = b.z(name) - STRESS['bond_haircut'] / 252; do = np.maximum(f, 0) + (0.01 / 252 if name != 'SHY' else 0.0)
        return x, zero, do, [name]
    if name in EQ1:
        return b.z(name), zero, np.full((P, T), 0.02 / 252), [name]
    if name == 'GLD': return b.z('GLD'), zero, zero, ['GLD']
    if name in LEVMAP:
        src, L = LEVMAP[name]
        x = b.rN if src == 'NDX' else b.z(src) - (STRESS['bond_haircut'] / 252 if src in BOND else 0.0) + (STRESS['eq_bonus'] / 252 if src in EQ1 else 0.0)
        r = _lev(b, x, L) if src != 'NDX' else L * b.rN - (L - 1) * f - (0.0095 + 0.0075 * (L - 1)) / 252
        return r, zero, zero, ([] if src == 'NDX' else [src])
    spx = b.z('U_SPX'); gold = b.z('U_GOLD'); tb = b.z('U_TB') * STRESS['trend_scale']; ts = b.z('U_TS') * STRESS['trend_scale']
    if name == 'DBMF': return f + tb - 0.0085 / 252, tb, f.copy(), ['U_TB']
    if name == 'KMLM': return f + ts - 0.0090 / 252, ts, f.copy(), ['U_TS']
    if name == 'RSST': return spx + tb - 0.0099 / 252, tb, np.full((P, T), 0.018 / 252), ['U_SPX', 'U_TB']
    if name == 'GDE':
        return (0.9 * spx + 0.1 * f + 0.9 * (gold - f) - 0.0020 / 252, 0.9 * (gold - f), 0.1 * f + 0.9 * 0.018 / 252, ['U_SPX', 'U_GOLD'])
    if name == 'NTSX':
        ief = b.z('IEF')
        return (0.9 * spx + 0.1 * f + 0.6 * (ief - f) - 0.0020 / 252, 0.6 * (ief - f), 0.1 * f + 0.9 * 0.018 / 252, ['U_SPX', 'IEF'])
    if name == 'RSBT':
        ief = b.z('IEF')
        return ief + tb - 0.0102 / 252, (ief - f) + tb, f.copy(), ['IEF', 'U_TB']
    if name == 'RSSB':
        efa = b.g('EFA'); eq = np.where(np.isfinite(efa), 0.6 * spx + 0.4 * np.nan_to_num(efa), spx)
        lad = (b.z('SHY') + b.z('IEF') + b.z('TLT')) / 3.0
        return eq + (lad - f) - 0.0036 / 252, lad - f, np.full((P, T), 0.018 / 252), ['U_SPX', 'SHY', 'IEF', 'TLT']
    raise KeyError(name)


def coverage(b, name):
    r, dg, do, needs = product(b, name)
    return min([b.cover(n) for n in needs], default=1.0)


# ---------------- s0.85 levels ----------------
def s085_levels(bn, delay=2):
    fn = CACHE + 's085_lv_%s_d%d.npy' % (bn, delay)
    if os.path.exists(fn): return np.load(fn)
    c = context(bn)[0]; B, bfn, bp, fs = std.s085(c); FEAT = std.bk.features(c)
    L = np.zeros((c.P, c.T - WARM))
    for i in range(c.P):
        st, rec = std.beng.run_path(np.ascontiguousarray(c.r[i]), np.ascontiguousarray(c.rf[i]), np.ascontiguousarray(B[i], dtype=np.float64),
                                    np.ascontiguousarray(FEAT[i]), bfn, bp, fstep=fs, delay=delay)
        L[i] = rec[:, 1]
    np.save(fn, L); return L


# ---------------- run ----------------
def run(b, prods, sleeves, ws, reb='yearly', cost=0.003, tax=0.22, D=0.25, cash_kind='ms1', band=0.0, keep_curve=False):
    """prods: list of product names (must include CASH). sleeves: list of f(p) -> (W (K,J), flag (K,)). Returns per-path dict."""
    J = {n: i for i, n in enumerate(prods)}; NJ = len(prods)
    R = np.zeros((b.P, b.T, NJ)); DG = np.zeros_like(R); DO = np.zeros_like(R)
    for n, j in J.items():
        r, dg, do, _ = product(b, n, cash_kind); R[:, :, j] = r; DG[:, :, j] = dg; DO[:, :, j] = do
    R[:, 0, :] = 0.0; DG[:, 0, :] = 0.0; DO[:, 0, :] = 0.0
    notax = np.array([n == 'CASH' for n in prods])
    K = b.K; rb = np.zeros(K, bool)
    if reb == 'yearly': rb[252::252] = True
    elif reb == 'quarterly': rb[63::63] = True
    ws = np.asarray(ws, float); out = np.zeros((b.P, 7)); C = np.zeros((b.P, K)) if keep_curve else np.zeros((1, K))
    for p in range(b.P):
        Ws = np.zeros((len(sleeves), K, NJ)); Fl = np.zeros((len(sleeves), K), bool)
        for s, sl in enumerate(sleeves):
            W, fl = sl(p, J); Ws[s] = W; Fl[s] = fl
        cp = C[p] if keep_curve else C[0]
        E.run_port(np.ascontiguousarray(R[p, WARM:]), np.ascontiguousarray(DG[p, WARM:]), np.ascontiguousarray(DO[p, WARM:]),
                   Ws, Fl, ws, rb, band, notax, cost, tax, D, 0.154, out[p], cp)
    yrs = K / 252; cg = np.maximum(out[:, 0], 1e-9) ** (1 / yrs) - 1
    res = dict(cagr=cg, mdd=out[:, 1], E7=out[:, 2], E12=out[:, 3], ntr=out[:, 4] / yrs, cost=out[:, 5] / yrs)
    if keep_curve: res['curve'] = C
    return res


def row(res, ref=None):
    cg = res['cagr']; m = res['mdd']
    d = dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(m)), dd80=float(np.mean(m <= -0.8)),
             dd95=float(np.mean(m <= -0.95)), w7=float(np.median(res['E7'])), w12=float(np.median(res['E12'])), tr=float(np.median(res['ntr'])))
    if ref is not None:
        x = cg - ref['cagr']; d.update(d_ref=float(np.median(x)), pw_ref=float(np.mean(x > 1e-5)))
    return d


# ---------------- sleeve builders ----------------
def sl_s085(L, fill=None, mode='all', n_deep=21, keep_cash=0.0):
    """s0.85 sleeve on in-force levels L (P,K): TQQQ = L/3; idle = 1 - L/3 -> CASH or fill dict {prod: share}.
    mode 'all': fill the whole idle share every day. mode 'deep': fill only while L <= 1 for the last n_deep rows; fill share fixed
    at 2/3 (so L moving 0<->1 does not trade the fill), rest CASH; sold the day L > 1 is in force (L decided 2 days earlier)."""
    def f(p, J):
        lv = L[p]; K = lv.shape[0]; W = np.zeros((K, len(J))); W[:, J['TQQQ']] = lv / 3; idle = 1 - lv / 3
        if not fill: W[:, J['CASH']] += idle; fl = np.r_[True, np.diff(lv) != 0]; return W, fl
        if mode == 'all':
            for n, w in fill.items(): W[:, J[n]] += idle * w * (1 - keep_cash)
            W[:, J['CASH']] += idle * keep_cash
            fl = np.r_[True, np.diff(lv) != 0]; return W, fl
        low = (lv <= 1 + 1e-9).astype(float)
        cs = np.cumsum(np.r_[0.0, low]); run_ok = np.zeros(K, bool)
        idx = np.arange(K); st = np.maximum(idx - n_deep + 1, 0)
        run_ok = (cs[idx + 1] - cs[st]) >= np.minimum(n_deep, idx + 1) - 1e-9
        run_ok &= idx >= n_deep - 1
        fsh = np.where(run_ok, 2.0 / 3.0, 0.0)
        for n, w in fill.items(): W[:, J[n]] += fsh * w
        W[:, J['CASH']] += idle - fsh
        fl = np.r_[True, (np.diff(lv) != 0) | (np.diff(fsh) != 0)]; return W, fl
    return f


def sl_static(weights, reb_days=0):
    """fixed internal mix {prod: w}; reb_days > 0 -> internal rebalance every reb_days (else only at the portfolio rebalance)"""
    def f(p, J):
        K = None
        return weights, reb_days
    def g(p, J, K):
        W = np.zeros((K, len(J)))
        for n, w in weights.items(): W[:, J[n]] = w
        fl = np.zeros(K, bool)
        if reb_days: fl[reb_days::reb_days] = True
        fl[0] = True
        return W, fl
    return g


def bind(b, sleeve_fns):
    """wrap sleeves that need K (static) into f(p, J)"""
    out = []
    for s in sleeve_fns:
        if s.__code__.co_argcount == 3: out.append(lambda p, J, s=s: s(p, J, b.K))
        else: out.append(s)
    return out
