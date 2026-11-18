"""DF6 runner (PRECOMMIT_DF6.md): levered NDX + defensive-sector static mixes. Engine, worlds, costs, taxes = DF5 (df5run/df5data/dfk).
python df6.py k        -> results/df6_k.json (k_s, Delta_s, monthly 1928-1985; run once after the lock)
python df6.py harness  -> parity check vs df5_main.json (N1, DY 2%)
python df6.py main     -> results/df6_main.json + /tmp/df6w/df6_arr.npz   (all configs under N1)
python df6.py final    -> results/df6_final.json (conventions, H1-H7, G6, grades, selection, k*, stability, report rows)
Run from /tmp/df6w (never with cwd under research/). Data <= 2014 only; pre-1986 data used only to reject."""
import os, sys, io, json, time, zipfile, itertools, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df5run as R, df5lib as L, df5data as DD, df5fam as F, df5gate as GT, df5stress as ST, dfk
WARM = 300
RES = R.RES
TMP = '/tmp/df6w/'
ER = 0.0015
DYS = {'STAP': 0.025, 'HLTH': 0.015, 'UTIL': 0.040, 'DEF3': (0.025 + 0.015 + 0.040) / 3, 'DEF2': 0.020}
REPORT_S = ['STAP', 'HLTH', 'UTIL', 'DEF2']
NEG_S = ['ENER', 'MANU', 'SHOP', 'FIN', 'TELE']
MULT = {'TQQQ': 3, 'QLD': 2}
KEYS = [('REAL', None, 'REAL'), ('P', 30, 'P30'), ('P', 10, 'P10'), ('X', 30, 'X30'), ('X', 10, 'X10')]
log = R.log
FF = '/mnt/project-files/research/broad_etf/data/raw/kf/F-F_Research_Data_Factors_daily_CSV.zip'
END86 = pd.Timestamp('1985-12-31')

# ------------------------------------------------------------------ grid (integer 0.05 units)
def grid(V):
    m = MULT[V]; out = []
    for ei in range(10, 21):
        for ci in range(6, 19):
            if ei - 20 + ci < 0 or (m - 1) * (20 - ci) - (ei - 20 + ci) < 0: continue
            a = (ei - 20 + ci) / (20 * (m - 1)); c = ci / 20; b = 1 - c - a
            out.append((ei, ci, a, max(b, 0.0)))
    return out

def cid(V, S, Rb, ei, ci): return 'L|%s|%s|R%d|e%.2f|c%.2f' % (V, S, Rb, ei / 20, ci / 20)

def configs():
    C = []
    for role, Ss, Vs, Rs in (('main', ['DEF3'], ['TQQQ', 'QLD'], [63, 252]), ('report', REPORT_S, ['TQQQ', 'QLD'], [63, 252]),
                             ('neg', NEG_S + ['SPX'], ['TQQQ'], [63])):
        for S, V, Rb in itertools.product(Ss, Vs, Rs):
            for ei, ci, a, b in grid(V):
                C.append(dict(id=cid(V, S, Rb, ei, ci), role=role, V=V, S=S, R=Rb, ei=ei, ci=ci, e=ei / 20, c=ci / 20, a=a, b=b,
                              dup_of=(cid('TQQQ', S, Rb, ei, ci) if (V == 'QLD' and a == 0) else None)))
    return C

# ------------------------------------------------------------------ k_s, Delta_s (monthly, 1928-01..1985-12)
def _kf_market():
    z = zipfile.ZipFile(FF); name = [n for n in z.namelist() if n.lower().endswith('.csv')][0]
    lines = z.read(name).decode('latin1').splitlines(); rows = []
    for ln in lines:
        p = [x.strip() for x in ln.split(',')]
        if len(p) >= 5 and p[0].isdigit() and len(p[0]) == 8:
            d = pd.Timestamp(p[0])
            if d > END86: continue                               # cut at load; nothing after 1985 is kept
            rows.append((d, float(p[1]) / 100 + float(p[4]) / 100, float(p[4]) / 100))
    df = pd.DataFrame(rows, columns=['date', 'mkt', 'rf']).set_index('date')
    return df

def _daily_sleeves(cut=END86):
    S = DD.src_series(); out = {}
    for k in ['STAP', 'HLTH', 'UTIL', 'TECH'] + NEG_S:
        out[k] = S[k][S[k].index <= cut]
    i3 = out['STAP'].index.intersection(out['UTIL'].index).intersection(out['HLTH'].index)
    out['DEF3'] = (out['STAP'].reindex(i3) + out['UTIL'].reindex(i3) + out['HLTH'].reindex(i3)) / 3.0
    i2 = out['STAP'].index.intersection(out['HLTH'].index)
    out['DEF2'] = (out['STAP'].reindex(i2) + out['HLTH'].reindex(i2)) / 2.0
    rf = pd.read_csv(DD.CLEAN + 'RF.csv', parse_dates=['date']).set_index('date')['r'].astype(float)
    out['RF'] = rf[rf.index <= cut]
    return out

def _monthly(s):
    return (1 + s).groupby([s.index.year, s.index.month]).prod() - 1

def kvals():
    d = _daily_sleeves(); mk = _kf_market()
    X, Sx = L._src('1928-01-03', '1985-12-31', 'SPX'); spx = Sx['SPX'].astype(float)
    M = {k: _monthly(v) for k, v in d.items() if k != 'RF'}
    M['MKT'] = _monthly(mk['mkt']); M['SPXTR'] = _monthly(spx); rfm = _monthly(d['RF'])
    df = pd.DataFrame(M); df['RF'] = rfm
    df = df[(df.index.get_level_values(0) >= 1928) & (df.index.get_level_values(0) <= 1985)].dropna()
    ex = df.drop(columns=['RF']).sub(df['RF'], axis=0)
    def sh(x): return float(x.mean() / x.std(ddof=1))
    out = {'n_months': int(len(ex)), 'first': '%d-%02d' % ex.index[0], 'last': '%d-%02d' % ex.index[-1], 'sleeves': {}}
    yrs = ex.index.get_level_values(0)
    rng = np.random.default_rng(7); nb = int(np.ceil(len(ex) / 12)); starts_max = len(ex) - 12
    boots = [np.concatenate([np.arange(s0, s0 + 12) for s0 in rng.integers(0, starts_max + 1, nb)])[:len(ex)] for _ in range(2000)]
    for s in ['DEF3', 'STAP', 'HLTH', 'UTIL', 'DEF2'] + NEG_S + ['TECH']:
        row = {}
        for mk_name in ('MKT', 'SPXTR'):
            r = {}
            for tag, sel in (('all', np.ones(len(ex), bool)), ('28_55', yrs <= 1955), ('56_85', yrs >= 1956)):
                e = ex[sel]; r['k_' + tag] = sh(e[s]) / sh(e[mk_name]); r['delta_ann_' + tag] = (sh(e[s]) - sh(e[mk_name])) * np.sqrt(12)
                r['sh_s_ann_' + tag] = sh(e[s]) * np.sqrt(12); r['sh_m_ann_' + tag] = sh(e[mk_name]) * np.sqrt(12)
            a_s = ex[s].values; a_m = ex[mk_name].values; kb = []
            for ix in boots:
                xs, xm = a_s[ix], a_m[ix]; kb.append((xs.mean() / xs.std(ddof=1)) / (xm.mean() / xm.std(ddof=1)))
            kb = np.array(kb); r['k_boot_p20'] = float(np.percentile(kb, 20)); r['k_boot_p50'] = float(np.percentile(kb, 50))
            r['k_low'] = float(min(r['k_all'], r['k_boot_p20'], r['k_28_55'], r['k_56_85']))
            r['corr'] = float(np.corrcoef(a_s, a_m)[0, 1]); r['vol_ratio'] = float(a_s.std() / a_m.std())
            row[mk_name] = {k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}
        out['sleeves'][s] = row
    json.dump(out, open(RES + 'df6_k.json', 'w'), indent=1)
    return out

def KV():
    d = json.load(open(RES + 'df6_k.json'))['sleeves']
    return {s: d[s]['MKT'] for s in d}

# ------------------------------------------------------------------ panel with sleeve convention
def panel6(wname, conv, param=None, sleeves=None):
    """conv: N1 (equal arithmetic mean to S&P, DF5), N2 raw, N3 (param = {sleeve: k}), NA (param = {sleeve: daily Sharpe delta}), N4 (k=1).
    dy2: if param == 'dy2' under N1, every sleeve uses DY 2% (DF5 parity)."""
    base = DD.panel(wname, raw=True); w = L.world(wname); m = w['m']; ii = w['ii']; idx = w['S'].index
    rf = np.nan_to_num(m['rf']); P, T = rf.shape
    sel = np.zeros((P, T), bool); sel[:, WARM:] = True
    out = {k: v for k, v in base.items() if k in ('QQQ', 'QLD', 'TQQQ', 'TBILL', 'B10', 'SPX', 'SSO', 'UPRO')}
    meta = {'nanfrac': dict(base['meta']['nanfrac']), 'shift6': {}}
    spx = base['SPX'][0] + 0.001 / 252
    xm = spx - rf; m_ex = float(xm[sel].mean()); s_ex = float(xm[sel].std()); rfm = float(rf[sel].mean()); mspx = float(spx[sel].mean())
    src = DD.src_series()
    sleeves = sleeves or (['DEF3'] + REPORT_S + NEG_S)
    for s in sleeves:
        if s == 'DEF2':
            i2 = src['STAP'].index.intersection(src['HLTH'].index)
            a, _ = DD._on_cal((src['STAP'].reindex(i2) + src['HLTH'].reindex(i2)) / 2.0, idx); A = a[ii]
            meta['nanfrac']['DEF2'] = float(np.isnan(A[:, WARM:]).mean()); A = np.nan_to_num(A)
        else:
            A = base[s][0] + ER / 252
        ex = A - rf
        if conv == 'N2': sh = 0.0
        elif conv == 'N1': sh = float(A[sel].mean()) - mspx
        elif conv in ('N3', 'N4'):
            k = 1.0 if conv == 'N4' else param[s]
            sh = float(A[sel].mean()) - (rfm + k * m_ex / s_ex * float(ex[sel].std()))
        elif conv == 'NA':
            sh = float(A[sel].mean()) - (rfm + (m_ex / s_ex + param[s]) * float(ex[sel].std()))
        else: raise KeyError(conv)
        meta['shift6'][s] = sh * 252
        dy = 0.02 if (param == 'dy2' or s not in DYS) else DYS[s]
        out[s] = (A - sh - ER / 252, dy / 252, 1)
    out['meta'] = meta
    return out

class W6(R.W):
    def __init__(self, wname, conv='N1', param=None, sleeves=None):
        self.name = wname; self.w = L.world(wname); self.m = self.w['m']
        self.pan = panel6(wname, conv, param, sleeves); self.conv = conv
        self.sig = R.SG.Sig(wname, 'NDX'); self._s = {}; r = self.m['r']; self.P, self.T = r.shape; self._lv = {}
        self.rfl = np.cumprod(1 + np.nan_to_num(self.m['rf']), axis=1)

def drop(wname):
    L._WORLDS.pop(wname, None); DD._P.clear()

# ------------------------------------------------------------------ jobs
def job(cfg, X, spx_core=False, offset=None):
    lev = {'TQQQ': 'UPRO', 'QLD': 'SSO'}[cfg['V']] if spx_core else cfg['V']
    core = 'SPX' if spx_core else 'QQQ'
    if cfg.get('split'):
        ids = [lev, core, 'STAP', 'HLTH', 'UTIL']; w = [cfg['a'], cfg['b'], cfg['c'] / 3, cfg['c'] / 3, cfg['c'] / 3]
    else:
        ids = [lev, core, cfg['S']]; w = [cfg['a'], cfg['b'], cfg['c']]
    P, T = X.P, X.T; Wt = np.broadcast_to(np.array(w, float), (P, T, len(ids))).copy()
    if offset is None:
        return ('dfk', ids, Wt, F.ev_changes(Wt), dict(reb_every=cfg['R']))
    EV = np.zeros((P, T), bool); EV[:, WARM - 1] = True
    EV[:, WARM - 2 + cfg['R'] + offset::cfg['R']] = True          # dfk trades 2 days after EV -> trades at k = nR + offset (n >= 1)
    return ('dfk', ids, Wt, EV, dict(reb_every=0))

def run(cfg, X, h=None, spx_core=False, offset=None, **over):
    return R.run_job(job(cfg, X, spx_core, offset), X, h, **over)

def bench(X, h=None, spx_core=False, **over):
    if not spx_core: return R.qqq(X, h, **over)
    P, T = X.P, X.T; Wt = np.ones((P, T, 1))
    return R.run_job(('dfk', ['SPX'], Wt, F.ev_changes(Wt), dict(reb_every=0)), X, h, **over)

def run_set(C, conv, param=None, store=None, sleeves=None, keys=KEYS):
    rows = {c['id']: {} for c in C}; Q = {}
    for wname in ('REAL', 'P', 'X'):
        ks = [k for k in keys if k[0] == wname]
        if not ks: continue
        X = W6(wname, conv, param, sleeves)
        for wn, h, key in ks:
            hh = None if h == 30 else h
            qcg, qmd, _ = bench(X, hh); Q[key] = R.summ(qcg, qmd)
            if store is not None: store['QQQ||' + key] = np.stack([qcg, qmd]).astype(np.float32)
            for c in C:
                cg, md, _ = run(c, X, hh); rows[c['id']][key] = R.summ(cg, md, qcg)
                if store is not None and key in ('P30', 'X30') and c['role'] == 'main':
                    store['%s||%s' % (c['id'], key)] = np.stack([cg, md]).astype(np.float32)
        del X; drop(wname); log(conv, wname, 'done')
    return rows, Q

def gates(rows, Q):
    G = {}
    for i, r in rows.items():
        g, sc, ddm = GT.gate_row(r, Q)
        G[i] = dict(g={k: bool(v['ok']) for k, v in g.items()}, score=float(sc), ddm=float(ddm), npass=int(sum(v['ok'] for v in g.values())),
                    fail={k: v.get('fail') for k, v in g.items() if not v['ok']})
    return G

# ------------------------------------------------------------------ G6: pre-1986 analog (KF BusEq core), weekday-compounded KF calendar
def _weekday(series, cal):
    pos = cal.searchsorted(series.index)                       # each date -> next calendar date >= it (Saturdays -> Monday)
    ok = pos < len(cal); s = series[ok]; tgt = cal[pos[ok]]
    return (1 + s).groupby(tgt).prod().reindex(cal).fillna(1.0).values - 1

_G6 = {}
def g6_data():
    if _G6: return _G6
    d = _daily_sleeves()
    cal = d['TECH'].index[(d['TECH'].index >= pd.Timestamp('1928-01-03')) & (d['TECH'].index.weekday < 5)]
    for k in ('TECH', 'DEF3', 'RF'): _G6[k] = _weekday(d[k], cal)
    _G6['cal'] = cal
    return _G6

def g6_world(name):
    d = g6_data(); n = len(d['cal'])
    if name == 'R2885': ii = np.arange(n)[None, :]
    else: ii = L.ov.boot_idx(n, P=500, years=30, block=250, seed=33, lo=1)
    tech, def3, rf = d['TECH'][ii], d['DEF3'][ii], d['RF'][ii]
    core = (tech - 0.002 / 252, 0.02 / 252, 1)
    pr = tech - 0.02 / 252
    lev = {'TQQQ': (3 * pr - 2 * rf - 0.0245 / 252, 0.0, 1), 'QLD': (2 * pr - rf - 0.017 / 252, 0.0, 1)}
    slv = (def3 - ER / 252, DYS['DEF3'] / 252, 1)
    return dict(core=core, lev=lev, slv=slv, P=ii.shape[0], T=ii.shape[1])

def g6_run(cfg, G):
    P, T = G['P'], G['T']
    def go(assets, w, reb):
        RET = np.stack([a[0] for a in assets], 2); INC = np.stack([np.broadcast_to(np.asarray(a[1], float), (P, T)) for a in assets], 2)
        HV = np.array([a[2] for a in assets], np.int64); Wt = np.broadcast_to(np.array(w, float), (P, T, len(w))).copy()
        o, _ = dfk.run(RET, INC, Wt, F.ev_changes(Wt), HV, reb_every=reb); return dfk.stats(o, T)
    qcg, qmd = go([G['core']], [1.0], 0)
    cg, md = go([G['lev'][cfg['V']], G['core'], G['slv']], [cfg['a'], cfg['b'], cfg['c']], cfg['R'])
    return cg, md, qcg, qmd

# ------------------------------------------------------------------ harness (DF5 parity)
def harness():
    D = json.load(open(RES + 'df5_main.json')); c = dict(id='h', role='main', V='TQQQ', S='DEF3', R=63, e=1.0, c=0.5, a=0.25, b=0.25)
    out = {}
    for wname in ('REAL', 'P', 'X'):
        X = W6(wname, 'N1', 'dy2', ['DEF3'])
        for wn, h, key in [k for k in KEYS if k[0] == wname]:
            hh = None if h == 30 else h
            qcg, qmd, _ = bench(X, hh); cg, md, _ = run(c, X, hh); s = R.summ(cg, md, qcg); st = D['rows']['A3|e1.00|c0.50|DEF3|none'][key]
            out[key] = max(abs(s[f] - st[f]) for f in ('cagr', 'p10', 'mdd_p10', 'pair')); out['Q' + key] = abs(R.summ(qcg, qmd)['cagr'] - D['qqq'][key]['cagr'])
        del X; drop(wname)
    print('harness max abs diff', out)
    return out

# ------------------------------------------------------------------ main (N1, all configs)
def main():
    os.makedirs(TMP, exist_ok=True); t0 = time.time()
    C = configs(); store = {}
    log('configs', len(C), {r: sum(c['role'] == r for c in C) for r in ('main', 'report', 'neg')})
    rows, Q = run_set(C, 'N1', store=store)
    G = gates(rows, Q)
    np.savez(TMP + 'df6_arr.npz', **store)
    json.dump(dict(meta=dict(precommit=open(RES + '../PRECOMMIT_DF6.sha256').read().split()[0], n=len(C)), configs=C, qqq=Q, rows=rows, gates=G),
              open(RES + 'df6_main.json', 'w'), indent=1)
    for role in ('main', 'report', 'neg'):
        ids = [c['id'] for c in C if c['role'] == role and not c['dup_of']]
        log(role, 'unique', len(ids), 'G1-G5', sum(G[i]['npass'] == 5 for i in ids), {k: sum(G[i]['g'][k] for i in ids) for k in ('G1', 'G2', 'G3', 'G4', 'G5')})
    log('main done %.0fs' % (time.time() - t0))

# ------------------------------------------------------------------ final
def nbrs(c, idx, radius):
    out = []
    for V in ([c['V']] if c['a'] > 0 else ['TQQQ', 'QLD']):
        for de in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if de == 0 and dc == 0: continue
                j = cid(V, c['S'], c['R'], c['ei'] + de, c['ci'] + dc)
                if j in idx and j != c['id']: out.append(j)
    # QLD a=0 points: same point under TQQQ id is the canonical copy
    return sorted(set(idx[j]['dup_of'] or j for j in out) - {c['dup_of'] or c['id']})

def final():
    t0 = time.time()
    D = json.load(open(RES + 'df6_main.json')); C = D['configs']; idx = {c['id']: c for c in C}; Q = D['qqq']; rows = D['rows']; G1 = D['gates']
    main_ids = [c['id'] for c in C if c['role'] == 'main']
    uniq = [i for i in main_ids if not idx[i]['dup_of']]
    gp = [i for i in uniq if G1[i]['npass'] == 5]
    log('N1 G-pass (unique main)', len(gp))
    kv = KV(); kd = kv['DEF3']
    conv = {'N2': ('N2', None), 'N3ks': ('N3', {'DEF3': kd['k_all']}), 'N3low': ('N3', {'DEF3': kd['k_low']}),
            'NA': ('NA', {'DEF3': kd['delta_ann_all'] / np.sqrt(252)}), 'N4': ('N4', None)}
    CM = [idx[i] for i in uniq]
    allconv = {}
    for nm, (cv, pa) in conv.items():
        r2, q2 = run_set(CM, cv, pa, sleeves=['DEF3']); allconv[nm] = dict(rows=r2, qqq=q2, gates=gates(r2, q2))
    out = dict(gpass=gp, counts={'N1': len(gp)}, H={})
    for nm in conv: out['counts'][nm] = sum(allconv[nm]['gates'][i]['npass'] == 5 for i in uniq)
    out['counts_report'] = {}
    for S in REPORT_S + NEG_S + ['SPX']:
        ids = [c['id'] for c in C if c['S'] == S and not c['dup_of']]
        out['counts_report'][S] = dict(n=len(ids), pass_=sum(G1[i]['npass'] == 5 for i in ids))
    H = {i: {} for i in gp}
    # H1 cost x2, H2 rebalance phase offsets
    for wname in ('REAL', 'P', 'X'):
        X = W6(wname, 'N1', None, ['DEF3']); single = wname == 'REAL'
        qcg, qmd, _ = bench(X, None, cost=0.006)
        for i in gp:
            cg, md, _ = run(idx[i], X, None, cost=0.006); H[i].setdefault('H1', {})[wname] = ST.gate_conds(cg, md, qcg, qmd, single)
        qcg, qmd, _ = bench(X, None)
        for i in gp:
            offs = (21, 42) if idx[i]['R'] == 63 else (63, 126)
            for o in offs:
                cg, md, _ = run(idx[i], X, None, offset=o); H[i].setdefault('H2', {})['%s_%d' % (wname, o)] = ST.gate_conds(cg, md, qcg, qmd, single)
        del X; drop(wname)
    X = W6('P125', 'N1', None, ['DEF3']); qcg, qmd, _ = bench(X)
    for i in gp:
        cg, md, _ = run(idx[i], X); H[i]['H3'] = ST.gate_conds(cg, md, qcg, qmd)
    del X; drop('P125')
    passN1 = {i for i in uniq if G1[i]['npass'] == 5}
    for i in gp:
        c = idx[i]; nb = nbrs(c, idx, 2); npass = sum(j in passN1 for j in nb)
        other = cid(c['V'], c['S'], 252 if c['R'] == 63 else 63, c['ei'], c['ci']); other = idx[other]['dup_of'] or other
        H[i]['H4'] = dict(n=len(nb), npass=npass, other_R=bool(other in passN1), ok=bool(len(nb) >= 4 and npass >= 0.75 * len(nb) and other in passN1))
        H[i]['H5'] = allconv['N2']['gates'][i]['npass'] == 5
        H[i]['H6'] = allconv['NA']['gates'][i]['npass'] == 5
        H[i]['H7'] = allconv['N3low']['gates'][i]['npass'] == 5
        H[i]['N3ks'] = allconv['N3ks']['gates'][i]['npass'] == 5
    # G6
    GR = g6_world('R2885'); GO = g6_world('OLD6')
    for i in gp:
        cg, md, qcg, qmd = g6_run(idx[i], GR); a = ST.gate_conds(cg, md, qcg, qmd, single=True)
        cg2, md2, qcg2, qmd2 = g6_run(idx[i], GO); b = ST.gate_conds(cg2, md2, qcg2, qmd2)
        H[i]['G6'] = dict(ok=bool(a and b), real=bool(a), boot=bool(b),
                         real_v=dict(cagr=float(cg[0]), mdd=float(md[0]), core_cagr=float(qcg[0]), core_mdd=float(qmd[0])),
                         boot_v=R.summ(cg2, md2, qcg2), boot_core=R.summ(qcg2, qmd2))
    for i in gp:
        h = H[i]; base_ok = all(h['H1'].values()) and all(h['H2'].values()) and h['H3'] and h['H4']['ok'] and h['H5']
        h['tier'] = 1 if (base_ok and h['H6'] and h['H7'] and h['G6']['ok']) else (2 if base_ok else 0)
        h['fails'] = [k for k, ok in (('H1', all(h['H1'].values())), ('H2', all(h['H2'].values())), ('H3', h['H3']), ('H4', h['H4']['ok']),
                                      ('H5', h['H5']), ('H6', h['H6']), ('H7', h['H7']), ('G6', h['G6']['ok'])) if not ok]
    out['H'] = H
    # selection per tier: neighbourhood-min score (radius 1 = max distance 0.05)
    def nscore(i):
        nb = nbrs(idx[i], idx, 1); return min([G1[i]['score']] + [G1[j]['score'] for j in nb])
    sel = {}
    for tier in (1, 2):
        T_ = [i for i in gp if H[i]['tier'] == tier]
        if not T_: sel[tier] = None; continue
        ns = {i: nscore(i) for i in T_}; top = max(ns.values()); tied = [i for i in T_ if ns[i] >= top - 0.0005]
        ans = max(tied, key=lambda i: G1[i]['ddm']); alt = max(T_, key=lambda i: (G1[i]['ddm'], ns[i]))
        sel[tier] = dict(answer=ans, alt=alt, n=len(T_), nscore=ns[ans])
    out['select'] = sel
    best = {}
    for i in uniq:
        k = '%s|R%d' % (idx[i]['V'], idx[i]['R'])
        if k not in best or (G1[i]['npass'], G1[i]['score']) > (G1[best[k]]['npass'], G1[best[k]]['score']): best[k] = i
    out['best'] = best
    json.dump(out, open(RES + 'df6_final.json', 'w'), indent=1, default=str)
    ans = (sel.get(1) or sel.get(2) or {}).get('answer')
    if ans:
        out['kstar'] = kstar(idx[ans]); out['stability'] = stability([i for i in gp if H[i]['tier'] == H[ans]['tier']], ans, rows, Q, idx)
    json.dump(out, open(RES + 'df6_final.json', 'w'), indent=1, default=str)
    ids = [x for x in [ans, (sel.get(1) or sel.get(2) or {}).get('alt')] if x] + list(best.values())
    ids = list(dict.fromkeys(ids))
    out['report'] = report_rows([idx[i] for i in ids], ans and idx[ans], kd)
    json.dump(out, open(RES + 'df6_final.json', 'w'), indent=1, default=str)
    log('final saved %.0fs' % (time.time() - t0))

def kstar(c):
    lo, hi = 0.5, 2.5
    def ok(k):
        r2, q2 = run_set([c], 'N3', {'DEF3': k}, sleeves=['DEF3']); return gates(r2, q2)[c['id']]['npass'] == 5
    if not ok(hi): return dict(kstar=None, note='fails even at k=2.5')
    if ok(lo): return dict(kstar=lo, note='passes at k=0.5')
    while hi - lo > 0.01:
        mid = (lo + hi) / 2
        if ok(mid): hi = mid
        else: lo = mid
    return dict(kstar=round(hi, 3))

def stability(fin, ans, rows, Q, idx, nrep=1000, seed=11):
    """resample P30 and X30 paths (same draw for every config); re-run the selection rule (neighbourhood-min score) within the answer's tier"""
    A = dict(np.load(TMP + 'df6_arr.npz')); rng = np.random.default_rng(seed); qP = A['QQQ||P30']; qX = A['QQQ||X30']
    NB = {i: [i] + nbrs(idx[i], idx, 1) for i in fin}; pool = sorted(set(j for v in NB.values() for j in v))
    real_ex = {i: rows[i]['REAL']['cagr'] - Q['REAL']['cagr'] for i in pool}; keep = picked = 0
    for _ in range(nrep):
        ixP = rng.integers(0, qP.shape[1], qP.shape[1]); ixX = rng.integers(0, qX.shape[1], qX.shape[1]); raw = {}
        for j in pool:
            cP = A['%s||P30' % j]; cX = A['%s||X30' % j]
            raw[j] = min(np.median(cP[0][ixP] - qP[0][ixP]), np.median(cX[0][ixX] - qX[0][ixX]), real_ex[j])
        sc = {i: min(raw[j] for j in NB[i]) for i in fin}
        picked += max(sc, key=sc.get) == ans
        ok = True
        for cc, q, ix in ((A['%s||P30' % ans], qP, ixP), (A['%s||X30' % ans], qX, ixX)):
            ok &= ST.gate_conds(cc[0][ix], cc[1][ix], q[0][ix], q[1][ix])
        keep += ok
    return dict(selected=picked / nrep, passes_G2G4=keep / nrep, flag=('불안정' if keep / nrep < 0.7 else 'ok'))

def report_rows(cfgs, ans, kd):
    out = {c['id']: {} for c in cfgs}; out['BENCH'] = {}
    if ans: sp = dict(ans, id=ans['id'] + '|split3R63', split=True, R=63); cfgs = cfgs + [sp]; out[sp['id']] = {}   # three ETFs held apart, quarterly rebalance
    plan = [('P', 'N1', None, [5, 10, 20, None]), ('X', 'N1', None, [5, 10, 20, None]), ('REAL', 'N1', None, [None]), ('P125', 'N1', None, [None]),
            ('XSYM', 'N1', None, [None]), ('P500', 'N1', None, [None])]
    for nm, cv, pa in (('N2', 'N2', None), ('N3ks', 'N3', {'DEF3': kd['k_all']}), ('N3low', 'N3', {'DEF3': kd['k_low']}),
                       ('NA', 'NA', {'DEF3': kd['delta_ann_all'] / np.sqrt(252)}), ('N4', 'N4', None)):
        for w in ('P', 'X', 'REAL'): plan.append((w, (cv, nm, pa), None, [None]))
    for wname, cv, pa, hs in plan:
        if isinstance(cv, tuple): cv, tag, pa = cv
        else: tag = cv
        X = W6(wname, cv, pa, ['DEF3'] if tag in ('N3ks', 'N3low', 'NA') else ['DEF3', 'STAP', 'HLTH', 'UTIL'])   # post-lock crash fix (N3/NA params exist for DEF3 only)
        for h in hs:
            key = (wname + str(h or 30) if wname in ('P', 'X') else wname) + ('' if tag == 'N1' else '_' + tag)
            qcg, qmd, _ = bench(X, h); out['BENCH'][key] = R.summ(qcg, qmd)
            for c in cfgs:
                if c.get('split') and tag in ('N3ks', 'N3low', 'NA'): continue
                cg, md, _ = run(c, X, h); out[c['id']][key] = R.summ(cg, md, qcg)
        if wname == 'P' and tag == 'N1':
            qcg, qmd, _ = bench(X, None, D=0.025); out['BENCH']['P30_100M'] = R.summ(qcg, qmd)
            for c in cfgs:
                cg, md, _ = run(c, X, None, D=0.025); out[c['id']]['P30_100M'] = R.summ(cg, md, qcg)
        del X; drop(wname); log('report', wname, tag)
    X = W6('S55', 'N2', None, ['DEF3'])
    qcg, qmd, _ = bench(X, None, True); out['BENCH']['S55_spxcore'] = R.summ(qcg, qmd)
    for c in cfgs:
        if c.get('split'): continue
        cg, md, _ = run(c, X, None, True); out[c['id']]['S55_spxcore'] = R.summ(cg, md, qcg)
    del X; drop('S55')
    GR = g6_world('R2885'); GO = g6_world('OLD6')
    for c in cfgs:
        if c.get('split'): continue
        cg, md, qcg, qmd = g6_run(c, GR); out[c['id']]['G6_R2885'] = dict(cagr=float(cg[0]), mdd=float(md[0]), core_cagr=float(qcg[0]), core_mdd=float(qmd[0]))
        cg, md, qcg, qmd = g6_run(c, GO); out[c['id']]['G6_OLD6'] = R.summ(cg, md, qcg); out['BENCH']['G6_OLD6'] = R.summ(qcg, qmd)
    return out

def report_only():
    """post-lock: final() crashed inside report_rows after gates/H tests/selection were saved. Re-run only the report rows (no gate,
    H test, tier or selection logic changes). With no tier-1/2 answer, k* is computed REPORT-ONLY for the top N1 score config."""
    D = json.load(open(RES + 'df6_main.json')); C = D['configs']; idx = {c['id']: c for c in C}; G1 = D['gates']
    out = json.load(open(RES + 'df6_final.json')); kd = KV()['DEF3']
    sel = out['select']; ans = (sel.get('1') or sel.get('2') or {}) or {}
    ans = ans.get('answer') if ans else None
    top = max(out['gpass'], key=lambda i: G1[i]['score']) if out['gpass'] else None
    ids = list(dict.fromkeys([x for x in [ans, top] if x] + list(out['best'].values())))
    if top and not ans: out['kstar_top_reportonly'] = dict(id=top, **kstar(idx[top]))
    out['report'] = report_rows([idx[i] for i in ids], ans and idx[ans], kd); out['report_ids'] = ids
    json.dump(out, open(RES + 'df6_final.json', 'w'), indent=1, default=str)
    log('report saved')

if __name__ == '__main__':
    a = sys.argv[1] if len(sys.argv) > 1 else 'main'
    if a == 'k': print(json.dumps(kvals(), indent=1)[:200])
    elif a == 'harness': harness()
    elif a == 'main': main()
    elif a == 'final': final()
    elif a == 'report': report_only()
