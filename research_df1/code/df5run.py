"""DF5 runner (PRECOMMIT_DF5.md sha 23ff354b). Builds every config in every world, runs dfe/dfk, gates.
python df5run.py main   -> results/df5_main.json (+ /tmp/df5w/arr_*.npz per-path arrays)
Run from /tmp/df5w (never with cwd under research/)."""
import os, sys, json, time, itertools, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5lib as L, df5data as DD, df5sig as SG, df5fam as F, dfe, dfk, df4cfg
WARM = 300
RES = '/mnt/project-files/research/df1/results/'
TMP = '/tmp/df5w/'
MAN = json.load(open('/mnt/project-files/research/df5/data/MANIFEST.json'))['assets']
DD.set_files({k: '/mnt/project-files/research/df5/data/clean/%s.csv' % k for k in MAN if k in DD.SLEEVES or k in ('STAP', 'UTIL', 'HLTH')})
ELIG = DD.eligibility()
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)

# ------------------------------------------------------------------ world context
class W:
    def __init__(self, wname, raw=False):
        self.name = wname; self.w = L.world(wname); self.m = self.w['m']; self.pan = DD.panel(wname, raw=raw)
        self.sig = SG.Sig(wname, 'NDX'); self._s = {}
        r = self.m['r']; self.P, self.T = r.shape
        self.rfl = np.cumprod(1 + np.nan_to_num(self.m['rf']), axis=1)
        self._lv = {}
    def sigb(self, base):
        if base == 'NDX': return self.sig
        if base not in self._s: self._s[base] = SG.Sig(self.name, base)
        return self._s[base]
    def lv(self, aid):
        if aid not in self._lv: self._lv[aid] = np.cumprod(1 + self.pan[aid][0], axis=1)
        return self._lv[aid]
    def mA(self, roff_asset):
        """dfe market dict for track A: rb = net risk-off asset, idxup = T200 with REAL filler"""
        a = 'B10' if roff_asset in ('TBILL', None) else roff_asset
        rb, inc, _ = self.pan[a]
        cp = inc if isinstance(inc, np.ndarray) else np.full(rb.shape, inc)
        bl = np.cumprod(1 + rb, axis=1); bs = SG.sma(bl, 200)
        return dict(r=self.m['r'], rf=self.m['rf'], rb=rb, cpn=cp, idxup=self.sig.T(200), bondup=np.where(np.isnan(bs), False, bl > bs))
    def mB(self):
        rb, inc, _ = self.pan['B10']; bl = np.cumprod(1 + rb, axis=1); bs = SG.sma(bl, 200)
        m = dict(self.m); m['rb'] = rb; m['cpn'] = inc; m['bondup'] = np.where(np.isnan(bs), False, bl > bs)
        return m

ROFF_DFE = {'TBILL': 1, 'B10': 2, 'GOLD': 2, 'DEF3': 2}
KNEE = {'K1': dict(kon=1, d0=-0.10, d1=-0.20, kfl=0.25), 'K2': dict(kon=1, d0=-0.15, d1=-0.30, kfl=0.25)}
BASEKW = dict(erq=DD.ERQ, erb=0.0)

def cutd(d, Th):
    return {k: (v[:, :Th] if isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] >= Th else v) for k, v in d.items()}

# ------------------------------------------------------------------ builders -> job
def a8_L(sig, arm, win, lh, base):
    t2 = sig.T(200); dd = sig.dd252(); P, T = t2.shape; Lt = np.zeros((P, T))
    for p in range(P):
        armed = False; ws = -1
        for t in range(T):
            on = t2[p, t]
            if ws >= 0 and t - ws >= win: ws = -1
            if ws < 0 and not armed and dd[p, t] <= -arm: armed = True
            if armed and on: ws = t; armed = False
            inwin = ws >= 0
            if base == 'T200': Lt[p, t] = (lh if on else 0.0) if inwin else (1.0 if on else 0.0)
            else: Lt[p, t] = (lh if on else 1.0) if inwin else 1.0
    return Lt

def job(cfg, X):
    """returns ('dfe', m, L, kw) or ('dfk', ids, W, EV, kw)"""
    f = cfg['fam']; sig = X.sig; P, T = X.P, X.T
    if f in ('A1', 'A2'):
        Lt = sig.mult(cfg['sig']) * sig.lon(cfg['size'])
        kw = dict(BASEKW, roff=ROFF_DFE[cfg['roff']], vmode=0, reb_every=F.REB)
        if f == 'A2': kw.update(KNEE[cfg['knee']])
        return ('dfe', X.mA(cfg['roff']), Lt, kw)
    if f == 'A7':
        mon = X.w['S'].index.month.values[X.w['ii']]
        hi = (mon >= 11) | (mon <= 4)
        Lt = np.where(hi, cfg['hi'], cfg['lo'])
        if cfg['tgate']: Lt = Lt * sig.T(200)
        return ('dfe', X.mA(cfg['roff']), Lt.astype(float), dict(BASEKW, roff=ROFF_DFE[cfg['roff']], vmode=0, reb_every=F.REB))
    if f == 'A8':
        Lt = a8_L(sig, cfg['arm'], cfg['win'], cfg['lh'], cfg['base'])
        return ('dfe', X.mA('TBILL'), Lt, dict(BASEKW, roff=1, vmode=0, reb_every=F.REB))
    if f == 'A3':
        ids = ['TQQQ', 'QQQ', 'TBILL'] + list(dict.fromkeys(cfg['dmix']))
        a = (cfg['e'] - 1 + cfg['c']) / 2; b = 1 - cfg['c'] - a
        Wt = np.zeros((P, T, len(ids))); on = sig.T(200) if cfg['gate'] == 'T200' else np.ones((P, T), bool)
        Wt[:, :, 0] = np.where(on, a, 0.0); Wt[:, :, 1] = np.where(on, b, 0.0); Wt[:, :, 2] = np.where(on, 0.0, a + b)
        for d in cfg['dmix']: Wt[:, :, ids.index(d)] += cfg['c'] / len(cfg['dmix'])
        return ('dfk', ids, Wt, F.ev_changes(Wt), dict(reb_every=F.REB))
    if f == 'A4':
        return a4(cfg, X)
    if f == 'A5':
        ids = ['QQQ', 'QLD', 'TQQQ', cfg['D']]
        Wt = np.zeros((P, T, 4)); EV = np.zeros((P, T), bool)
        up = cfg['up']; dn = cfg['dn']
        F._ladder(sig.lv, sig.T(200), X.pan['QQQ'][0], X.pan['QLD'][0], X.pan['TQQQ'][0], X.pan[cfg['D']][0],
                  up[0] if up else 0.0, up[1] if up else 0.0, up is not None, *(dn if dn else (0.0, 0.0, 0.0)), dn is not None,
                  1 if cfg['cf'] == 'T200' else 0, cfg['d0'], Wt, EV)
        EV[:, :WARM - 1] = False
        return ('dfk', ids, Wt, EV, dict(reb_every=0))
    if f == 'A6':
        ids = ['TQQQ', 'QQQ', 'TMF', 'TBILL']; Wt = np.zeros((P, T, 4)); extra = None
        if cfg['mix'] is None:
            sT = L.roll_std(X.pan['TQQQ'][0], 60); sM = L.roll_std(X.pan['TMF'][0], 60)
            wT = (1 / np.maximum(sT, 1e-9)) / (1 / np.maximum(sT, 1e-9) + 1 / np.maximum(sM, 1e-9)); wT = np.where(np.isnan(wT), 0.5, wT)
            mo = F.monthly(P, T); held = np.zeros((P, T)); cur = np.full(P, 0.5)
            for t in range(WARM - 1, T):
                cur = np.where(mo[:, t], wT[:, t], cur); held[:, t] = cur
            Wt[:, :, 0] = held; Wt[:, :, 2] = 1 - held; extra = mo
        else:
            for k, v in cfg['mix'].items(): Wt[:, :, ids.index(k)] = v
        if cfg['gate'] == 'T200':
            off = ~sig.T(200); eq = Wt[:, :, 0] + Wt[:, :, 1]
            Wt[:, :, 3] = np.where(off, Wt[:, :, 3] + eq, Wt[:, :, 3]); Wt[:, :, 0] = np.where(off, 0, Wt[:, :, 0]); Wt[:, :, 1] = np.where(off, 0, Wt[:, :, 1])
        return ('dfk', ids, Wt, F.ev_changes(Wt, extra), dict(reb_every=F.REB))
    if f == 'A9':
        sb = X.sigb(cfg['core']); m_ = sb.mult(cfg['sig']); E = m_ * cfg['L']
        t3, q, rest = F.split_ndx(E)
        if cfg['core'] == 'SPX':
            ids = ['UPRO', 'SPX', 'TBILL']; Wt = np.stack([t3, q, rest], 2)
        else:
            ids = ['UPRO', 'SPX', 'TQQQ', 'QQQ', 'TBILL']; Wt = np.stack([t3 / 2, q / 2, t3 / 2, q / 2, rest], 2)
        return ('dfk', ids, Wt, F.ev_changes(Wt), dict(reb_every=F.REB))
    if f == 'A10':
        ids = ['TQQQ', 'QQQ', 'SOX', 'TBILL']; on = sig.T(200); a = (cfg['L'] - 1) / 2; b = 1 - cfg['ws'] - a
        Wt = np.zeros((P, T, 4)); Wt[:, :, 0] = np.where(on, a, 0); Wt[:, :, 1] = np.where(on, b, 0); Wt[:, :, 2] = np.where(on, cfg['ws'], 0)
        Wt[:, :, 3] = np.where(on, 0, 1.0)
        return ('dfk', ids, Wt, F.ev_changes(Wt), dict(reb_every=F.REB))
    raise KeyError(f)

def _ndx_slot(Lx):
    a = (Lx - 1) / 2 if Lx > 1 else 0.0; return a, (1 - a) if Lx > 1 else Lx

def a4(cfg, X):
    P, T = X.P, X.T; mo = F.monthly(P, T); rfl = X.rfl
    def kr(aid, k):
        lv = X.lv('QQQ' if aid == 'NDX' else aid); out = np.full((P, T), -np.inf); out[:, k:] = lv[:, k:] / lv[:, :-k] - 1; return out
    rk = lambda k: np.r_[np.full(k, np.nan), np.zeros(0)]
    def rfk(k):
        out = np.full((P, T), np.inf); out[:, k:] = rfl[:, k:] / rfl[:, :-k] - 1; return out
    kind = cfg['kind']
    if kind == 'GEM':
        ids = ['TQQQ', 'QQQ', 'SPX', 'B10', 'TBILL']; a, b = _ndx_slot(cfg['L'])
        n = kr('NDX', 252); s = kr('SPX', 252); rr = rfk(252)
        pickN = (n > s) & (n > rr); pickS = ~pickN & (s > rr)
        tgt = np.zeros((P, T, 5)); tgt[:, :, 0] = np.where(pickN, a, 0); tgt[:, :, 1] = np.where(pickN, b, 0)
        tgt[:, :, 2] = np.where(pickS, 1.0, 0); tgt[:, :, 3] = np.where(~pickN & ~pickS, 1.0, 0)
        if cfg['L'] < 1: tgt[:, :, 4] = np.where(pickN, 1 - cfg['L'], 0)
    else:
        U = cfg['U']; uniq = list(dict.fromkeys(U))
        ids = (['TQQQ', 'QQQ'] if 'NDX' in uniq else []) + [u for u in uniq if u != 'NDX'] + ['TBILL']
        tgt = np.zeros((P, T, len(ids))); a, b = _ndx_slot(cfg['L'])
        def put(mask, aid, wgt):
            if aid == 'NDX':
                tgt[:, :, ids.index('TQQQ')] += np.where(mask, wgt * a, 0); tgt[:, :, ids.index('QQQ')] += np.where(mask, wgt * b, 0)
            else: tgt[:, :, ids.index(aid)] += np.where(mask, wgt, 0)
        if kind == 'TOP':
            lb = cfg['lb']; k = cfg['k']; R = np.stack([kr(u, lb) for u in uniq], 2); rr = rfk(lb)
            order = np.argsort(-R, axis=2, kind='stable'); rank = np.argsort(order, axis=2, kind='stable')
            for j, u in enumerate(uniq):
                sel = rank[:, :, j] < k; good = R[:, :, j] > rr
                put(sel & good, u, 1.0 / k); put(sel & ~good, 'TBILL', 1.0 / k)
        else:  # GTAA
            n = len(U)
            for u in U:
                lv = X.lv('QQQ' if u == 'NDX' else u); s = SG.sma(lv, 200); on = np.where(np.isnan(s), False, lv > s)
                put(on, u, 1.0 / n); put(~on, 'TBILL', 1.0 / n)
    # hold the month-start decision until the next decision day
    Wt = np.zeros_like(tgt); cur = tgt[:, WARM - 1, :].copy()
    for t in range(WARM - 1, T):
        cur = np.where(mo[:, t][:, None], tgt[:, t, :], cur); Wt[:, t, :] = cur
    return ('dfk', ids, Wt, mo, dict(reb_every=0))

# ------------------------------------------------------------------ run one job on a world (full or horizon cut)
def run_job(jb, X, h=None, **over):
    Th = WARM + h * 252 if h else X.T
    if jb[0] == 'dfe':
        _, m, Lt, kw = jb; kw = dict(kw); kw.update(over)
        mm = cutd(m, Th) if h else m
        o, _ = dfe.run(mm, Lt[:, :Th], **kw); cg, md = dfe.stats(o, Th); return cg, md, o[:, 0]
    _, ids, Wt, EV, kw = jb; kw = dict(kw); kw.update(over)
    RET, INC, HV = DD.stack(X.pan, ids)
    o, _ = dfk.run(RET[:, :Th], INC[:, :Th], Wt[:, :Th], EV[:, :Th], HV, **kw); cg, md = dfk.stats(o, Th); return cg, md, o[:, 0]

def run_B(cid, X, h=None, **over):
    cfg = df4cfg.cfg_of(cid); m = X.mB(); Th = WARM + h * 252 if h else X.T
    if h: m = cutd(m, Th)
    kw = dict(BASEKW); kw.update(over)
    o = df4cfg.run_any(cfg, m, **kw); cg, md = dfe.stats(o, Th); return cg, md, o[:, 0]

def qqq(X, h=None, **over):
    Th = WARM + h * 252 if h else X.T; m = X.mA('TBILL'); m = cutd(m, Th) if h else m
    kw = dict(BASEKW); kw.update(over)
    o, _ = dfe.run(m, np.ones((X.P, Th)), **kw); cg, md = dfe.stats(o, Th); return cg, md, o[:, 0]

def summ(cg, md, qcg=None):
    d = dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd_med=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)),
             ploss=float(np.mean(cg < 0)))
    if qcg is not None: d['pair'] = float(np.median(cg - qcg)); d['win'] = float(np.mean(cg > qcg))
    return d

# ------------------------------------------------------------------ v1 held path (track B ladder)
def v1_held(X):
    sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
    c = X.w['ctx']; B, bfn, bp, fs = std.s085(c); feat = std.bk.features(c)
    import beng
    P, T = X.P, X.T; held = np.zeros((P, T)); cg = np.zeros(P)
    for p in range(P):
        s, rec = beng.run_path(np.ascontiguousarray(c.r[p]), np.ascontiguousarray(c.rf[p]), np.ascontiguousarray(B[p], dtype=np.float64),
                               np.ascontiguousarray(feat[p]), bfn, np.asarray(bp, dtype=np.float64), cspr=10.0, fstep=fs)
        cur = rec[:, 1]; hd = np.empty(T); hd[:WARM - 1] = 0.0; hd[WARM - 1] = cur[0]
        hd[WARM:T - 2] = cur[2:]; hd[T - 2:] = cur[-1]; held[p] = np.maximum(hd, 0.0); cg[p] = s['cagr'][0]
    return held, cg

def vjob(cfg, X, held):
    P, T = X.P, X.T; Wt = np.zeros((P, T, 2)); EV = np.zeros((P, T), bool)
    up = cfg['up']
    F._vladder(held, X.pan['TQQQ'][0], X.pan[cfg['D']][0], up[0] if up else 1e9, up[1] if up else 0.0, cfg['d0'], Wt, EV)
    EV[:, :WARM - 1] = False
    return ('dfk', ['TQQQ', cfg['D']], Wt, EV, dict(reb_every=0))

def vconfigs():
    C = [dict(id='BV|v1approx', fam='BV', track='B', D='TBILL', up=None, d0=0.0, cat=('BV', 'base'), num={})]
    for D, up, d0 in itertools.product(['DEF3', 'VALUE', 'TBILL', 'GOLD'], ['U1', 'U2', 'U3'], [0.0, 0.3]):
        C.append(dict(id='BV|%s|%s|d%.1f' % (D, up, d0), fam='BV', track='B', D=D, up={'U1': (0.25, 0.10), 'U2': (0.5, 0.2), 'U3': (1.0, 0.3)}[up], d0=d0,
                      cat=('BV', D), num={'up': (int(up[1]) - 1, 3), 'd0': ([0.0, 0.3].index(d0), 2)}))
    return C

def bconfigs():
    ids = sorted(df4cfg.OLD.keys()) + sorted(json.load(open(RES + 'df3.json'))['configs'].keys())
    ids = list(dict.fromkeys(ids)); C = []
    for i in ids:
        c = df4cfg.cfg_of(i); C.append(dict(id=i, fam='B', track='B', cfgB=c))
    return C

WORLDS_MAIN = [('REAL', None), ('P', 30), ('P', 10), ('X', 30), ('X', 10)]

def main():
    t0 = time.time()
    CA = F.configs(ELIG); CB = bconfigs(); CV = vconfigs()
    log('configs A %d  B %d  BV %d' % (len(CA), len(CB), len(CV)))
    out = dict(meta=dict(precommit='23ff354b3b8b60dfc3e3875effa9d7e8e1a917059e4c829b0183884b1a88bfe2', elig=ELIG, N_A=len(CA), N_B=len(CB), N_BV=len(CV)),
               qqq={}, rows={}, shifts={})
    ARR = {}
    for wname in ('REAL', 'P', 'X'):
        X = W(wname); out['shifts'][wname] = {k: v * 252 for k, v in X.pan['meta']['shift'].items()}; out['shifts'][wname + '_missing'] = X.pan['meta']['missing']
        hs = [None] if wname == 'REAL' else [30, 10]
        Q = {}
        for h in hs:
            hh = None if h == 30 else h
            cg, md, fin = qqq(X, hh); key = wname + ('' if h is None else str(h)); Q[key] = cg
            out['qqq'][key] = summ(cg, md); ARR[('QQQ', key)] = (cg, md)
            # parity: dfk QQQ hold == dfe QQQ hold
            Th = WARM + hh * 252 if hh else X.T
            RET, INC, HV = DD.stack(X.pan, ['QQQ']); Wq = np.ones((X.P, Th, 1)); E0 = np.zeros((X.P, Th), bool); E0[:, WARM - 1] = True
            o2, _ = dfk.run(RET[:, :Th], INC[:, :Th], Wq, E0, HV); out['qqq'][key]['parity_dfk'] = float(np.max(np.abs(o2[:, 0] - fin)))
        log(wname, 'QQQ', {k: round(v['cagr'] * 100, 2) for k, v in out['qqq'].items()})
        held = None
        for grp, CC in (('A', CA), ('BV', CV), ('B', CB)):
            if grp == 'BV':
                held, v1cg = v1_held(X); out.setdefault('v1locked', {})[wname] = float(np.median(v1cg))
            for i, cfg in enumerate(CC):
                if grp == 'A': jb = job(cfg, X)
                elif grp == 'BV': jb = vjob(cfg, X, held)
                for h in hs:
                    hh = None if h == 30 else h; key = wname + ('' if h is None else str(h))
                    if grp == 'B': cg, md, fin = run_B(cfg['id'], X, hh)
                    else: cg, md, fin = run_job(jb, X, hh)
                    out['rows'].setdefault(cfg['id'], dict(fam=cfg['fam'], track=cfg['track']))[key] = summ(cg, md, Q[key])
                    if key in ('P30', 'X30', 'P10', 'X10', 'REAL'): ARR[(cfg['id'], key)] = (cg.astype(np.float32), md.astype(np.float32))
                    if key == 'P30': ARR[(cfg['id'], 'finP30')] = fin
                if grp == 'A': del jb
                if i % 100 == 0: log(wname, grp, i, '%.0fs' % (time.time() - t0))
        del X; L._WORLDS.pop(wname, None); DD._P.clear()
    json.dump(out, open(RES + 'df5_main.json', 'w'))
    np.savez_compressed(TMP + 'df5_arr.npz', **{'%s||%s' % k: np.stack(v) if isinstance(v, tuple) else v for k, v in ARR.items()})
    log('saved', '%.0fs' % (time.time() - t0))

if __name__ == '__main__':
    if sys.argv[1] == 'main': main()
