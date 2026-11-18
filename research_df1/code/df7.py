"""DF7 step A: the user's own static portfolios (QLD / GDE / RSST / DBMF) on the DF5 three-base framework (REAL, P, X; 5/10/20/30y).
<=2014 only. Engine, costs, taxes, QQQ dividend, worlds = DF5 (df5run / dfk).
Managed-futures (trend) proxy: plain multi-asset time-series momentum built a priori (NOT fitted to any product):
  markets SPX, LTT (25y Treasury proxy), GOLD (spot), USD (dollar index carry proxy), DEVX (from 1990-07); excess returns over T-bill;
  signal = mean(sign of 63/126/252-day excess log return), position = signal * (12% / sqrt(N)) / 60-day vol, cap 3x per market,
  weekly rebalance, positions use data through t-1.
Products (daily, before tax): DBMF = rf + TREND - 0.85%/yr; RSST = SPX TR + TREND - 0.99%/yr; GDE = 0.9 SPX TR + 0.1 rf + 0.9 (GOLD - rf) - 0.20%/yr;
  QLD = DF5 (2r - rf - 1.70%/yr).
Conventions: RAW = 1986-2014 as it happened (gold and trend raw); HALF = trend excess halved (gold raw); ZERO = gold and trend excess return set to 0 per world (DF5 'zx' rule).
python df7.py trend   -> results/df7_trend_stats.json (descriptive, <=2014)
python df7.py user    -> results/df7_user.json
DF7-B (PRECOMMIT_DF7.md): python df7.py main -> results/df7_main.json ; python df7.py final -> results/df7_final.json
  PRIM = neutral panel (raw=False) + trend excess at 50% of the world's proxy mean; Q = neutral + 25%; RAW = raw panel + 100%; ZERO = neutral + 0%.
Run from /tmp/df7w (never with cwd under research/)."""
import os, sys, json, time, itertools, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5lib as L, df5data as DD, df5fam as F, df5gate as GT, df5stress as ST, dfk
WARM = 300; RES = R.RES; log = R.log

# ------------------------------------------------------------------ trend proxy (by date, source calendar 1984-2014)
_T = {}
def trend_by_date(V=0.12, lbs=(63, 126, 252), volw=60, reb=5, cap=3.0):
    key = (V, lbs, volw, reb, cap)
    if key in _T: return _T[key]
    X, S = L._src('1984-01-03', '2014-12-31', 'SPX'); idx = S.index; rf = S['M_rf'].fillna(0.0)
    src = DD.src_series()
    ex = pd.DataFrame(index=idx)
    ex['SPX'] = S['SPX'] - rf
    for k in ('LTT', 'GOLD', 'USD', 'DEVX'):
        s = src[k].reindex(idx); first = src[k].index.min()
        s[(s.index >= first)] = s[(s.index >= first)].fillna(0.0)
        ex[k] = s - rf
    lg = np.log1p(ex)
    cum = lg.cumsum()
    sig = sum(np.sign(cum - cum.shift(L_)) for L_ in lbs) / len(lbs)
    vol = ex.rolling(volw).std() * np.sqrt(252)
    ok = cum.shift(max(lbs)).notna() & vol.notna()
    N = ok.sum(axis=1).replace(0, np.nan)
    w = (sig / vol).mul(V / np.sqrt(N), axis=0).clip(-cap, cap).where(ok, 0.0)
    w = w.shift(1)                                                   # decided at close t-1
    keep = np.arange(len(idx)) % reb == 0
    w = w.where(pd.Series(keep, index=idx), np.nan).ffill().fillna(0.0)
    tr = (w * ex.fillna(0.0)).sum(axis=1)
    out = dict(tr=tr, w=w, ex=ex)
    _T[key] = out
    return out

def trend_stats():
    d = trend_by_date(); tr = d['tr']; t = tr[tr.index >= '1986-01-01']
    def st(x):
        return dict(mean_ann=float(x.mean() * 252), vol_ann=float(x.std() * np.sqrt(252)), sharpe=float(x.mean() / x.std() * np.sqrt(252)),
                    cagr_ex=float(np.prod(1 + x) ** (252 / len(x)) - 1))
    out = {'1986_2014': st(t), '1986_1999': st(t[t.index < '2000-01-01']), '2000_2014': st(t[t.index >= '2000-01-01'])}
    yr = (1 + t).groupby(t.index.year).prod() - 1
    out['years'] = {int(k): round(float(v), 4) for k, v in yr.items()}
    X, S = L._src('1984-01-03', '2014-12-31', 'SPX'); ndx = S['NDX'].reindex(t.index); spx = S['SPX'].reindex(t.index)
    out['corr_ndx'] = float(np.corrcoef(t, ndx.fillna(0))[0, 1]); out['corr_spx'] = float(np.corrcoef(t, spx.fillna(0))[0, 1])
    out['gross_lev_mean'] = float(d['w'].abs().sum(axis=1)[t.index].mean())
    json.dump(out, open(RES + 'df7_trend_stats.json', 'w'), indent=1)
    return out

# ------------------------------------------------------------------ panel with products
CONV = {'RAW': (True, 1.0), 'HALF': (True, 0.5), 'ZERO': (False, 0.0), 'PRIM': (False, 0.5), 'Q': (False, 0.25)}
def conv_of(conv):
    """name -> (raw panel?, trend fraction); a float f -> neutral panel + trend fraction f (f* scan)"""
    return CONV[conv] if isinstance(conv, str) else (False, float(conv))

def panel7(wname, conv='RAW'):
    """DF5 panel (raw or neutral) + TREND/DBMF/RSST/GDE; trend excess shifted to frac x the world's own proxy mean (variance unchanged)."""
    raw, frac = conv_of(conv)
    base = DD.panel(wname, raw=raw); w = L.world(wname); m = w['m']; ii = w['ii']; idx = w['S'].index
    rf = np.nan_to_num(m['rf']); P, T = rf.shape; sel = np.zeros((P, T), bool); sel[:, WARM:] = True
    tr = trend_by_date()['tr'].reindex(idx)
    TR = np.nan_to_num(tr.values.astype(float)[ii])
    mu0 = float(TR[sel].mean()); TR = TR - (1.0 - frac) * mu0
    spx = base['SPX'][0] + 0.001 / 252                                  # SPX TR (gross)
    gold = base['GOLD'][0] + 0.0040 / 252                               # gold gross (RAW: as is; ZERO: shifted to rf mean in DD.panel)
    out = {k: v for k, v in base.items() if k in ('QQQ', 'QLD', 'TQQQ', 'SPX', 'SSO', 'UPRO', 'TBILL', 'B10', 'LTT', 'GOLD', 'DEF3', 'TMF')}
    out['TREND'] = (rf + TR, 0.0, 1)                                    # raw fund before fee (for reference)
    out['DBMF'] = (rf + TR - 0.0085 / 252, 0.0, 1)
    out['RSST'] = (spx + TR - 0.0099 / 252, DD.DY / 252, 1)
    out['GDE'] = (0.9 * spx + 0.1 * rf + 0.9 * (gold - rf) - 0.0020 / 252, 0.9 * DD.DY / 252, 1)
    out['meta'] = dict(trend_mean_ann=float(TR[sel].mean() * 252), trend_mean_ann_proxy=mu0 * 252, conv=str(conv), raw=raw, frac=frac)
    return out

class W7(R.W):
    def __init__(self, wname, conv='RAW'):
        self.name = wname; self.w = L.world(wname); self.m = self.w['m']; self.pan = panel7(wname, conv); self.conv = conv
        self.sig = R.SG.Sig(wname, 'NDX'); self._s = {}; r = self.m['r']; self.P, self.T = r.shape; self._lv = {}
        self.rfl = np.cumprod(1 + np.nan_to_num(self.m['rf']), axis=1)
    def setconv(self, conv):
        self.pan = panel7(self.name, conv); self.conv = conv; self._lv = {}

def drop(wname):
    L._WORLDS.pop(wname, None); DD._P.clear()

def job(ids, w, reb):
    def f(X):
        Wt = np.broadcast_to(np.array(w, float), (X.P, X.T, len(ids))).copy()
        return ('dfk', ids, Wt, F.ev_changes(Wt), dict(reb_every=reb))
    return f

USER = {
    'P2 QLD30/GDE30/RSST20/DBMF20': (['QLD', 'GDE', 'RSST', 'DBMF'], [0.30, 0.30, 0.20, 0.20], 252),
    'P3 QLD35/GDE30/RSST20/DBMF15': (['QLD', 'GDE', 'RSST', 'DBMF'], [0.35, 0.30, 0.20, 0.15], 252),
    'ref QLD100': (['QLD'], [1.0], 0),
    'ref GDE100': (['GDE'], [1.0], 0),
    'ref RSST100': (['RSST'], [1.0], 0),
    'ref DBMF100': (['DBMF'], [1.0], 0),
}

def user():
    t0 = time.time(); out = {'rows': {}, 'qqq': {}, 'meta': {}}
    for conv in ('RAW', 'HALF', 'ZERO'):
        for wname, hs in (('REAL', [None]), ('P', [5, 10, 20, None]), ('X', [5, 10, 20, None])):
            X = W7(wname, conv); out['meta']['%s_%s' % (wname, conv)] = X.pan['meta']
            for h in hs:
                key = (wname + str(h or 30) if wname != 'REAL' else 'REAL') + '_' + conv
                qcg, qmd, _ = R.qqq(X, h); out['qqq'][key] = R.summ(qcg, qmd)
                for nm, (ids, w, reb) in USER.items():
                    cg, md, _ = R.run_job(job(ids, w, reb)(X), X, h); out['rows'].setdefault(nm, {})[key] = R.summ(cg, md, qcg)
            del X; drop(wname); log(conv, wname, 'done')
    json.dump(out, open(RES + 'df7_user.json', 'w'), indent=1)
    log('user done %.0fs' % (time.time() - t0))

# ================================================================== DF7-B (PRECOMMIT_DF7.md)
KEYS = [('REAL', None, 'REAL'), ('P', 30, 'P30'), ('P', 10, 'P10'), ('X', 30, 'X30'), ('X', 10, 'X10')]
RKEYS = [('REAL', None, 'REAL')] + [(w, h, '%s%d' % (w, h)) for w in ('P', 'X') for h in (5, 10, 20, 30)] + [('P125', 30, 'P125')]
FRACS = [round(0.05 * i, 2) for i in range(21)]

def configs():
    C = []
    for q, g, t in itertools.product([.2, .3, .4, .5, .6], [0, .1, .2, .3], [0, .1, .2, .3]):
        d = round(1 - q - g - t, 2) + 0.0
        if d < -1e-9: continue
        C.append(dict(id='F1|q%.1f|g%.1f|t%.1f|m%.1f' % (q, g, t, d), fam='F1', w=dict(QLD=q, GOLD=g, LTT=t, DBMF=d)))
    for q, r, g in itertools.product([.2, .3, .4, .5], [i / 10 for i in range(9)], [i / 10 for i in range(5)]):
        d = round(1 - q - r - g, 2) + 0.0
        if d < -1e-9: continue
        C.append(dict(id='F2|q%.1f|r%.1f|g%.1f|m%.1f' % (q, r, g, d), fam='F2', w=dict(QLD=q, GDE=g, RSST=r, DBMF=d)))   # step-A asset order
    ON = {'Q100': dict(QLD=1.0), 'Q50M50': dict(QLD=0.5, DBMF=0.5)}
    OFF = {'M100': dict(DBMF=1.0), 'MGT': dict(DBMF=1 / 3, GOLD=1 / 3, LTT=1 / 3), 'BILL': dict(TBILL=1.0)}
    for sg, on, off in itertools.product(['T200', 'M252'], ON, OFF):
        C.append(dict(id='F3|%s|%s|%s' % (sg, on, off), fam='F3', sig=sg, on=ON[on], off=OFF[off], onk=on, offk=off))
    return C

EXTRA = [dict(id='U|P3', fam='U', w=dict(QLD=0.35, GDE=0.30, RSST=0.20, DBMF=0.15))]     # user P3, report only (P2 = F2|q0.3|r0.2|g0.3|m0.2)

def job7(c, X):
    if c['fam'] != 'F3':
        ids = [k for k, v in c['w'].items() if v > 1e-12]; w = [c['w'][k] for k in ids]
        Wt = np.broadcast_to(np.array(w, float), (X.P, X.T, len(ids))).copy()
        return ('dfk', ids, Wt, F.ev_changes(Wt), dict(reb_every=252))
    ids = sorted(set(c['on']) | set(c['off']))
    won = np.array([c['on'].get(k, 0.0) for k in ids]); woff = np.array([c['off'].get(k, 0.0) for k in ids])
    s = X.sig.T(200) if c['sig'] == 'T200' else X.sig.M(252)
    Wt = np.where(np.asarray(s, bool)[:, :, None], won[None, None, :], woff[None, None, :])
    return ('dfk', ids, Wt, F.ev_changes(Wt), dict(reb_every=252))

def run_set(C, conv, keys=KEYS, **over):
    rows = {c['id']: {} for c in C}; Q = {}
    for wname in dict.fromkeys(k[0] for k in keys):
        X = W7(wname, conv)
        for wn, h, key in [k for k in keys if k[0] == wname]:
            hh = None if h == 30 else h
            qcg, qmd, _ = R.qqq(X, hh, **over); Q[key] = R.summ(qcg, qmd)
            for c in C:
                cg, md, _ = R.run_job(job7(c, X), X, hh, **over); rows[c['id']][key] = R.summ(cg, md, qcg)
        del X; drop(wname); log(conv, wname, 'done')
    return rows, Q

def gates(rows, Q):
    G = {}
    for i, r in rows.items():
        g, sc, ddm = GT.gate_row(r, Q)
        G[i] = dict(g={k: bool(v['ok']) for k, v in g.items()}, score=float(sc), ddm=float(ddm), npass=int(sum(v['ok'] for v in g.values())),
                    fail={k: v.get('fail') for k, v in g.items() if not v['ok']})
    return G

def sha_pre():
    try: return open(RES + '../PRECOMMIT_DF7.sha256').read().split()[0]
    except Exception: return None

def main():
    t0 = time.time(); C = configs(); assert len(C) == 198, len(C)
    rows, Q = run_set(C, 'PRIM'); G = gates(rows, Q)
    json.dump(dict(meta=dict(precommit=sha_pre(), n=len(C), conv='PRIM'), configs=C, qqq=Q, rows=rows, gates=G), open(RES + 'df7_main.json', 'w'), indent=1)
    for fam in ('F1', 'F2', 'F3'):
        ids = [c['id'] for c in C if c['fam'] == fam]
        log(fam, len(ids), 'G1-G5', sum(G[i]['npass'] == 5 for i in ids), {k: sum(G[i]['g'][k] for i in ids) for k in ('G1', 'G2', 'G3', 'G4', 'G5')})
    log('main done %.0fs' % (time.time() - t0))

def nbrs7(c, C):
    if c['fam'] == 'F3':
        return ['F3|%s|%s|%s' % ('M252' if c['sig'] == 'T200' else 'T200', c['onk'], c['offk'])]
    out = []
    for d in C:
        if d['fam'] != c['fam'] or d['id'] == c['id']: continue
        ks = set(c['w']) | set(d['w'])
        if max(abs(c['w'].get(k, 0.0) - d['w'].get(k, 0.0)) for k in ks) <= 0.1 + 1e-9: out.append(d['id'])
    return out

def fstar(cfgs):
    """per config: G1-G5 pass flag at each trend fraction (neutral panel); f* = smallest passing fraction"""
    rows = {c['id']: {f: {} for f in FRACS} for c in cfgs}; Q = {}
    for wname in ('REAL', 'P', 'X'):
        X = W7(wname, 0.0); ks = [k for k in KEYS if k[0] == wname]
        for wn, h, key in ks:
            hh = None if h == 30 else h; qcg, qmd, _ = R.qqq(X, hh); Q[key] = R.summ(qcg, qmd)
        for f in FRACS:
            X.setconv(f)
            for wn, h, key in ks:
                hh = None if h == 30 else h; qcg, qmd, _ = R.qqq(X, hh)
                for c in cfgs:
                    cg, md, _ = R.run_job(job7(c, X), X, hh); rows[c['id']][f][key] = R.summ(cg, md, qcg)
        del X; drop(wname); log('fstar', wname, 'done')
    out = {}
    for c in cfgs:
        ok = {f: gates({c['id']: rows[c['id']][f]}, Q)[c['id']]['npass'] == 5 for f in FRACS}
        passing = [f for f in FRACS if ok[f]]
        out[c['id']] = dict(fstar=(min(passing) if passing else None), ok={str(f): bool(v) for f, v in ok.items()},
                            all_above=bool(passing and all(ok[f] for f in FRACS if f >= min(passing))))
    return out

def final():
    t0 = time.time()
    D = json.load(open(RES + 'df7_main.json')); C = D['configs']; idx = {c['id']: c for c in C}; Q = D['qqq']; rows = D['rows']; G = D['gates']
    gp = [c['id'] for c in C if G[c['id']]['npass'] == 5]
    log('PRIM G1-G5 pass', len(gp), {f: sum(idx[i]['fam'] == f for i in gp) for f in ('F1', 'F2', 'F3')})
    out = dict(meta=dict(precommit=sha_pre()), gpass=gp, H={}, counts={})
    H = {i: {} for i in gp}
    if gp:
        for wname in ('REAL', 'P', 'X'):                                              # H1 cost x2 (QQQ too), REAL / P30 / X30
            X = W7(wname, 'PRIM'); single = wname == 'REAL'
            qcg, qmd, _ = R.qqq(X, None, cost=0.006)
            for i in gp:
                cg, md, _ = R.run_job(job7(idx[i], X), X, None, cost=0.006); H[i].setdefault('H1', {})[wname] = ST.gate_conds(cg, md, qcg, qmd, single)
            del X; drop(wname)
        X = W7('P125', 'PRIM'); qcg, qmd, _ = R.qqq(X)                                 # H3 P125 30y
        for i in gp:
            cg, md, _ = R.run_job(job7(idx[i], X), X); H[i]['H3'] = ST.gate_conds(cg, md, qcg, qmd)
        del X; drop('P125')
        rq, qq = run_set([idx[i] for i in gp], 'Q'); GQ = gates(rq, qq)                 # H5 trend 25%
        out['Q'] = dict(rows=rq, qqq=qq, gates=GQ)
        for i in gp:
            nb = nbrs7(idx[i], C); npass = sum(G[j]['npass'] == 5 for j in nb)
            ok4 = (npass == len(nb)) if idx[i]['fam'] == 'F3' else (len(nb) >= 4 and npass >= 0.75 * len(nb))
            H[i]['H4'] = dict(n=len(nb), npass=npass, ok=bool(ok4))
            H[i]['H5'] = bool(GQ[i]['npass'] == 5)
            h = H[i]; base = all(h['H1'].values()) and h['H3'] and h['H4']['ok']
            h['tier'] = 1 if (base and h['H5']) else (2 if base else 0)
            h['fails'] = [k for k, ok in (('H1', all(h['H1'].values())), ('H3', h['H3']), ('H4', h['H4']['ok']), ('H5', h['H5'])) if not ok]
    out['H'] = H
    def nscore(i): return min([G[i]['score']] + [G[j]['score'] for j in nbrs7(idx[i], C)])
    sel = {}
    for tier in (1, 2):
        T_ = [i for i in gp if H[i]['tier'] == tier]
        if not T_: sel[tier] = None; continue
        ns = {i: nscore(i) for i in T_}; top = max(ns.values()); tied = [i for i in T_ if ns[i] >= top - 0.0005]
        sel[tier] = dict(answer=max(tied, key=lambda i: G[i]['ddm']), n=len(T_), nscore=ns[max(tied, key=lambda i: G[i]['ddm'])])
    out['select'] = sel
    out['counts'] = dict(gpass=len(gp), tier1=sum(H[i]['tier'] == 1 for i in gp), tier2=sum(H[i]['tier'] == 2 for i in gp),
                         by_fail={k: sum(k in H[i]['fails'] for i in gp) for k in ('H1', 'H3', 'H4', 'H5')})
    best = {}
    for c in C:
        k = c['fam']
        if k not in best or (G[c['id']]['npass'], G[c['id']]['score']) > (G[best[k]]['npass'], G[best[k]]['score']): best[k] = c['id']
    out['best'] = best
    json.dump(out, open(RES + 'df7_final.json', 'w'), indent=1, default=str)
    ans = (sel.get(1) or sel.get(2) or {}).get('answer')
    rep_ids = list(dict.fromkeys([x for x in [ans] if x] + list(best.values()) + ['F2|q0.3|r0.2|g0.3|m0.2']))
    rep = [idx[i] for i in rep_ids] + EXTRA
    out['fstar'] = fstar([idx[i] for i in rep_ids])
    json.dump(out, open(RES + 'df7_final.json', 'w'), indent=1, default=str)
    out['report'] = {}
    for conv in ('PRIM', 'RAW', 'ZERO'):
        rr, qq = run_set(rep, conv, keys=RKEYS); out['report'][conv] = dict(rows=rr, qqq=qq)
        json.dump(out, open(RES + 'df7_final.json', 'w'), indent=1, default=str)
    out['report_ids'] = [c['id'] for c in rep]
    json.dump(out, open(RES + 'df7_final.json', 'w'), indent=1, default=str)
    log('final saved %.0fs' % (time.time() - t0))

if __name__ == '__main__':
    a = sys.argv[1] if len(sys.argv) > 1 else 'user'
    if a == 'trend': print(json.dumps(trend_stats(), indent=1)[:1500])
    elif a == 'user': user()
    elif a == 'main': main()
    elif a == 'final': final()
