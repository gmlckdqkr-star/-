"""Direct re-run of DF7-B rows without df7.job7 / run_set / gates / df5gate.
usage: python3 -B s2_rerun.py WORLD [all]   (WORLD in REAL, P, X). <=2014 data only (worlds are built from <=2014 calendars)."""
import os, sys, json, time, itertools, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df7 as D, df5run as R, df5data as DD, dfk
sys.path.insert(0, '/tmp/df7v_repro'); import mygates as MG
WARM = 300; RES = '/mnt/project-files/research/df1/results/'; OUT = '/mnt/project-files/research/df1/verify7/repro/'
wname = sys.argv[1]; ALL = len(sys.argv) > 2 and sys.argv[2] == 'all'
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
t0 = time.time()

# ---------------- my own config grid (PRECOMMIT_DF7 section 2)
def my_configs():
    C = []
    for q, g, t in itertools.product([.2, .3, .4, .5, .6], [0, .1, .2, .3], [0, .1, .2, .3]):
        d = round(1 - q - g - t, 2)
        if d < -1e-9: continue
        C.append(dict(id='F1|q%.1f|g%.1f|t%.1f|m%.1f' % (q, g, t, abs(d)), fam='F1', w=[('QLD', q), ('GOLD', g), ('LTT', t), ('DBMF', d)]))
    for q, r, g in itertools.product([.2, .3, .4, .5], [i / 10 for i in range(9)], [i / 10 for i in range(5)]):
        d = round(1 - q - r - g, 2)
        if d < -1e-9: continue
        C.append(dict(id='F2|q%.1f|r%.1f|g%.1f|m%.1f' % (q, r, g, abs(d)), fam='F2', w=[('QLD', q), ('GDE', g), ('RSST', r), ('DBMF', d)]))
    ON = {'Q100': {'QLD': 1.0}, 'Q50M50': {'QLD': 0.5, 'DBMF': 0.5}}
    OFF = {'M100': {'DBMF': 1.0}, 'MGT': {'DBMF': 1 / 3, 'GOLD': 1 / 3, 'LTT': 1 / 3}, 'BILL': {'TBILL': 1.0}}
    for s, on, off in itertools.product(['T200', 'M252'], ['Q100', 'Q50M50'], ['M100', 'MGT', 'BILL']):
        C.append(dict(id='F3|%s|%s|%s' % (s, on, off), fam='F3', sig=s, on=ON[on], off=OFF[off]))
    C.append(dict(id='U|P3', fam='U', w=[('QLD', .35), ('GDE', .30), ('RSST', .20), ('DBMF', .15)]))
    return C
MC = my_configs(); MCI = {c['id']: c for c in MC}
DM = json.load(open(RES + 'df7_main.json')); DF = json.load(open(RES + 'df7_final.json'))
cfg_check = dict(n_mine=len([c for c in MC if c['fam'] != 'U']), ids_equal=sorted(c['id'] for c in MC if c['fam'] != 'U') == sorted(c['id'] for c in DM['configs']))
wd = []
for c in DM['configs']:
    m = MCI[c['id']]
    if c['fam'] == 'F3':
        if c['on'] != m['on'] or any(abs(c['off'][k] - m['off'][k]) > 1e-15 for k in m['off']): wd.append(c['id'])
    else:
        mw = {k: v for k, v in m['w'] if v > 1e-12}; sw = {k: v for k, v in c['w'].items() if v > 1e-12}
        if set(mw) != set(sw) or any(abs(mw[k] - sw[k]) > 1e-12 for k in mw) or [k for k in c['w'] if c['w'][k] > 1e-12] != list(mw): wd.append(c['id'])
cfg_check['weight_or_order_diffs'] = wd
log('configs', cfg_check)

# ---------------- my own signals (NDX path level; REAL pre-1985-10-01 filled with S&P TR - 2%/yr, DF5 convention)
def my_signals(X):
    w = X.w; m = w['m']; ii = w['ii']; S = w['S']
    r = np.nan_to_num(m['r']); rf = np.nan_to_num(m['rf'])
    rs = r.copy()
    if X.name == 'REAL':
        spx = np.nan_to_num(S['SPX'].values.astype(float)[ii]) - 0.02 / 252
        d = S.index.values[ii[0]]; pre = d < np.datetime64('1985-10-01'); rs[0, pre] = spx[0, pre]
    lv = np.cumprod(1 + rs, axis=1); rfl = np.cumprod(1 + rf, axis=1)
    sma = pd.DataFrame(lv.T).rolling(200).mean().values.T
    T200 = np.where(np.isnan(sma), False, lv > sma)
    k = 252; rk = np.full(lv.shape, np.nan); rk[:, k:] = lv[:, k:] / lv[:, :-k] - 1
    fk = np.full(lv.shape, np.nan); fk[:, k:] = rfl[:, k:] / rfl[:, :-k] - 1
    M252 = np.where(np.isnan(rk), False, rk > fk)
    return {'T200': T200, 'M252': M252}

# ---------------- my own target weights / event flags
def build(c, X, SIG):
    P, T = X.P, X.T
    if c['fam'] != 'F3':
        ids = [k for k, v in c['w'] if v > 1e-12]; wv = np.array([v for k, v in c['w'] if v > 1e-12])
        W = np.empty((P, T, len(ids))); W[:] = wv
        EV = np.zeros((P, T), bool); EV[:, WARM - 1] = True
        return ids, W, EV
    ids = sorted(set(c['on']) | set(c['off']))
    won = np.array([c['on'].get(k, 0.0) for k in ids]); woff = np.array([c['off'].get(k, 0.0) for k in ids])
    s = SIG[c['sig']]
    W = np.where(s[:, :, None], won[None, None, :], woff[None, None, :])
    EV = np.zeros((P, T), bool); EV[:, 1:] = (s[:, 1:] != s[:, :-1]); EV[:, WARM - 1] = True; EV[:, :WARM - 1] = False
    return ids, W, EV

def run(c, X, SIG, h, cost=0.003):
    ids, W, EV = build(c, X, SIG)
    RET, INC, HV = DD.stack(X.pan, ids)
    Th = WARM + h * 252 if h else X.T
    o, _ = dfk.run(RET[:, :Th], INC[:, :Th], W[:, :Th], EV[:, :Th], HV, delay=2, cost=cost, tax=0.22, D=0.25, harvest=3, hthr=1.0, reb_every=252)
    cg, md = dfk.stats(o, Th)
    return cg, md

def summ(cg, md, qcg):
    return dict(cagr=float(np.median(cg)), p10=float(np.quantile(cg, 0.1)), mdd_med=float(np.median(md)), mdd_p10=float(np.quantile(md, 0.1)),
                pair=float(np.median(cg - qcg)), win=float(np.mean(cg > qcg)), ploss=float(np.mean(cg < 0)))

def qqq_dfk(X, h):
    Th = WARM + h * 252 if h else X.T
    RET, INC, HV = DD.stack(X.pan, ['QQQ']); W = np.ones((X.P, Th, 1)); EV = np.zeros((X.P, Th), bool); EV[:, WARM - 1] = True
    o, _ = dfk.run(RET[:, :Th], INC[:, :Th], W, EV, HV, reb_every=0); return dfk.stats(o, Th)

FIELDS = ('cagr', 'p10', 'mdd_med', 'mdd_p10', 'pair', 'win', 'ploss')
def cmp(mine, stored):
    return {f: float(mine[f] - stored[f]) for f in FIELDS if f in stored and f in mine}

KEYS = {'REAL': [('REAL', None)], 'P': [('P30', None), ('P10', 10)], 'X': [('X30', None), ('X10', 10)]}[wname]
TARGET = ['F2|q0.2|r0.7|g0.1|m0.0', 'F2|q0.3|r0.2|g0.3|m0.2', 'F1|q0.4|g0.0|t0.0|m0.6', 'F3|M252|Q100|M100', 'F3|T200|Q100|M100',
          'F1|q0.6|g0.0|t0.0|m0.4', 'F2|q0.2|r0.5|g0.3|m0.0', 'F3|M252|Q50M50|BILL', 'F3|T200|Q50M50|MGT', 'F1|q0.3|g0.2|t0.2|m0.3',
          'F2|q0.5|r0.5|g0.0|m0.0']
out = dict(world=wname, cfg_check=cfg_check, sig_check={}, qqq={}, prim={}, fstar={}, report={}, panel_meta={})

X = D.W7(wname, 'PRIM'); log('world loaded', X.P, X.T, '%.0fs' % (time.time() - t0))
SIG = my_signals(X)
for s, n in (('T200', 200), ('M252', 252)):
    ref = X.sig.T(200) if s == 'T200' else X.sig.M(252)
    out['sig_check'][s] = dict(ndiff=int(np.sum(SIG[s] != np.asarray(ref, bool))), ndiff_after_warm=int(np.sum(SIG[s][:, WARM - 1:] != np.asarray(ref, bool)[:, WARM - 1:])),
                               on_frac=float(SIG[s][:, WARM:].mean()), switches_path0=int(np.sum(SIG[s][0, WARM:] != SIG[s][0, WARM - 1:-1])))
log('signals', out['sig_check'])
if wname == 'REAL':
    d = X.w['S'].index.values[X.w['ii'][0]]
    out['real_dates'] = dict(first=str(d[0])[:10], warm=str(d[WARM])[:10], last=str(d[-1])[:10], T=int(X.T),
                             r_nan_after_warm=int(np.isnan(X.m['r'][0, WARM:]).sum()))
    assert str(d[-1])[:10] <= '2014-12-31'

def qset(X, conv, store):
    Q = {}; QA = {}
    for key, h in KEYS:
        qcg, qmd, _ = R.qqq(X, h); Q[key] = dict(cagr=float(np.median(qcg)), p10=float(np.quantile(qcg, 0.1)), mdd_med=float(np.median(qmd)),
                                                   mdd_p10=float(np.quantile(qmd, 0.1)), ploss=float(np.mean(qcg < 0)))
        kcg, kmd = qqq_dfk(X, h)
        out['qqq'].setdefault(conv, {})[key] = dict(mine=Q[key], d_stored=cmp(Q[key], store[key]),
                                                     dfk_parity_cg=float(np.max(np.abs(kcg - qcg))), dfk_parity_md=float(np.max(np.abs(kmd - qmd))))
        QA[key] = qcg
    return Q, QA

# ---------------- PRIM main rows
Q, QA = qset(X, 'PRIM', DM['qqq'])
out['panel_meta']['PRIM'] = X.pan['meta']
ids_run = list(dict.fromkeys(TARGET + ([c['id'] for c in DM['configs']] if wname == 'REAL' else [])))
def prim_rows(ids_run):
  for n, i in enumerate(ids_run):
    for key, h in KEYS:
        cg, md = run(MCI[i], X, SIG, h); s = summ(cg, md, QA[key])
        out['prim'].setdefault(i, {})[key] = dict(mine=s, d=cmp(s, DM['rows'][i][key]))
    if n % 25 == 0: log('prim', n, len(ids_run), '%.0fs' % (time.time() - t0))
    if n % 25 == 0: json.dump(out, open(OUT + 's2_%s.json' % wname, 'w'), indent=1)
prim_rows(ids_run)
log('prim done', '%.0fs' % (time.time() - t0))

# ---------------- f* spot checks (neutral panel, float trend fraction)
FS = {'F2|q0.2|r0.7|g0.1|m0.0': [0.65, 0.7], 'F2|q0.3|r0.2|g0.3|m0.2': [0.75, 0.8]}
for i, fr in FS.items():
    for f in fr:
        X.setconv(f); out['panel_meta'][str(f)] = X.pan['meta']
        for key, h in KEYS:
            qcg, _, _ = R.qqq(X, h)
            cg, md = run(MCI[i], X, SIG, h); out['fstar'].setdefault(i, {}).setdefault(str(f), {})[key] = summ(cg, md, qcg)
log('fstar done', '%.0fs' % (time.time() - t0))

# ---------------- RAW / ZERO report rows (REAL and X10 only)
if wname in ('REAL', 'X'):
    RK = [k for k in KEYS if k[0] in ('REAL', 'X10')]
    for conv in ('ZERO', 'RAW'):
        X.setconv(conv); out['panel_meta'][conv] = X.pan['meta']
        for key, h in RK:
            qcg, qmd, _ = R.qqq(X, h); qs = dict(cagr=float(np.median(qcg)), p10=float(np.quantile(qcg, 0.1)), mdd_med=float(np.median(qmd)), mdd_p10=float(np.quantile(qmd, 0.1)), ploss=float(np.mean(qcg < 0)))
            out['report'].setdefault(conv, {}).setdefault('qqq', {})[key] = dict(mine=qs, d=cmp(qs, DF['report'][conv]['qqq'][key]))
            for i in DF['report_ids']:
                cg, md = run(MCI[i], X, SIG, h); s = summ(cg, md, qcg)
                out['report'][conv].setdefault('rows', {}).setdefault(i, {})[key] = dict(mine=s, d=cmp(s, DF['report'][conv]['rows'][i][key]))
    log('report done', '%.0fs' % (time.time() - t0))
json.dump(out, open(OUT + 's2_%s.json' % wname, 'w'), indent=1)
if ALL:
    X.setconv('PRIM'); assert X.pan['meta']['frac'] == 0.5 and not X.pan['meta']['raw']
    prim_rows([c['id'] for c in DM['configs'] if c['id'] not in out['prim']])
    log('all done', '%.0fs' % (time.time() - t0))
json.dump(out, open(OUT + 's2_%s.json' % wname, 'w'), indent=1)
del X; D.drop(wname); log('saved', '%.0fs' % (time.time() - t0))
