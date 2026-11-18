"""E2 (report-only): where the N1 edge of L|TQQQ|DEF3|R252|e0.60|c0.80 comes from. One world at a time; <=2014 data only."""
import os, sys, json, numpy as np, pandas as pd
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df6v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df6 as D6, df5run as R, df5stress as ST, df5data as DD, df5lib as L
WARM = 300; OUT = '/tmp/df6v/limit/'
idx = {c['id']: c for c in D6.configs()}
TOP = 'L|TQQQ|DEF3|R252|e0.60|c0.80'
kd = D6.KV()['DEF3']
ER = D6.ER; DY3 = D6.DYS['DEF3']
res = {'stats': {}, 'runs': {}, 'qqq': {}}

def st(x, y, rf, sel):
    xe = (x - rf)[sel]; ye = (y - rf)[sel]
    return dict(mu_ex_ann=float(xe.mean() * 252), vol_ann=float(xe.std() * np.sqrt(252)), sharpe_ann=float(xe.mean() / xe.std() * np.sqrt(252)),
                corr_ndx=float(np.corrcoef(x[sel], y[sel])[0, 1]), beta_ndx=float(np.cov(x[sel], y[sel])[0, 1] / y[sel].var()))

for wname in ('REAL', 'P', 'X'):
    X = D6.W6(wname, 'N1', None, ['DEF3'])
    rf = np.nan_to_num(X.m['rf']); r = np.nan_to_num(X.m['r']); P, T = r.shape
    sel = np.zeros((P, T), bool); sel[:, WARM:] = True
    d3 = X.pan['DEF3'][0] + ER / 252                 # gross DEF3 after the N1 shift (mean = SPX gross mean)
    spx = X.pan['SPX'][0] + 0.001 / 252              # SPX gross total return
    S = {'NDX': st(r, r, rf, sel), 'SPX': st(spx, r, rf, sel), 'DEF3_N1': st(d3, r, rf, sel)}
    S['corr_DEF3_SPX'] = float(np.corrcoef(d3[sel], spx[sel])[0, 1])
    S['k_implied_N1'] = S['DEF3_N1']['sharpe_ann'] / S['SPX']['sharpe_ann']
    # crash behaviour: mean DEF3 / SPX return on the NDX worst 1% days, and over NDX 60-day windows in the bottom 5%
    q = np.percentile(r[sel], 1); m = sel & (r <= q)
    S['worst1pct_days'] = dict(ndx=float(r[m].mean()), spx=float(spx[m].mean()), def3=float(d3[m].mean()))
    c60 = lambda a: np.cumsum(np.log1p(a), axis=1)
    lr, ls, ld = c60(r), c60(spx), c60(d3)
    w60 = lambda c: c[:, 60:] - c[:, :-60]
    R60, S60, D60 = w60(lr), w60(ls), w60(ld); sel60 = np.zeros_like(R60, bool); sel60[:, WARM:] = True
    q5 = np.percentile(R60[sel60], 5); mm = sel60 & (R60 <= q5)
    S['worst5pct_60d'] = dict(ndx=float(np.expm1(R60[mm].mean())), spx=float(np.expm1(S60[mm].mean())), def3=float(np.expm1(D60[mm].mean())))
    res['stats'][wname] = S
    # variants (all carry DEF3 costs: ER 0.15%, DY 2.67%, except SPX_retail = the locked negative control sleeve)
    mu = d3[sel].mean(); sd3 = d3[sel].std(); ssp = spx[sel].std(); mus = spx[sel].mean()
    V = {}
    V['DEF3'] = X.pan['DEF3']
    V['SPX_retail'] = X.pan['SPX']
    V['SPX_c'] = (spx - ER / 252, DY3 / 252, 1)
    V['DEF3_hivol'] = (mu + (d3 - mu) * (ssp / sd3) - ER / 252, DY3 / 252, 1)
    V['SPX_lovol'] = (mus + (spx - mus) * (sd3 / ssp) - ER / 252, DY3 / 252, 1)
    mix = 0.7 * d3 + 0.3 * spx; V['MIX73'] = (mix - (mix[sel].mean() - mu) - ER / 252, DY3 / 252, 1)
    # Sharpe-neutral (k = 1) versions: excess mean = SPX Sharpe x own vol
    sr = (spx - rf)[sel].mean() / (spx - rf)[sel].std(); rfm = rf[sel].mean()
    def k1(a):
        ex = (a - rf)[sel]; return a - (a[sel].mean() - (rfm + sr * ex.std()))
    V['DEF3_k1'] = (k1(d3) - ER / 252, DY3 / 252, 1)
    V['SPX_lovol_k1'] = (k1(mus + (spx - mus) * (sd3 / ssp)) - ER / 252, DY3 / 252, 1)
    for nm, (cv, pa) in (('DEF3_N3low', ('N3', {'DEF3': kd['k_low']})), ('DEF3_NA', ('NA', {'DEF3': kd['delta_ann_all'] / np.sqrt(252)}))):
        V[nm] = D6.panel6(wname, cv, pa, ['DEF3'])['DEF3']
    vstats = {}
    for nm, v in V.items():
        X.pan['VAR_' + nm] = v; a = v[0]
        vstats[nm] = st(a, r, rf, sel)
    res['stats'][wname]['variants_net'] = vstats
    keys = [(None, wname)] if wname == 'REAL' else [(None, wname + '30'), (10, wname + '10')]
    for h, key in keys:
        qcg, qmd, _ = D6.bench(X, h); res['qqq'][key] = R.summ(qcg, qmd)
        for nm in V:
            cfg = dict(idx[TOP], S='VAR_' + nm)
            cg, md, _ = D6.run(cfg, X, h); s = R.summ(cg, md, qcg)
            s['med_ex'] = s['cagr'] - res['qqq'][key]['cagr']; s['p10_ex'] = s['p10'] - res['qqq'][key]['p10']
            s['ddm'] = 1 - abs(s['mdd_p10'] if wname != 'REAL' else s['mdd_med']) / abs(res['qqq'][key]['mdd_p10'] if wname != 'REAL' else res['qqq'][key]['mdd_med'])
            s['gate'] = bool(ST.gate_conds(cg, md, qcg, qmd, wname == 'REAL'))
            res['runs'].setdefault(nm, {})[key] = s
        print(wname, key, 'done', flush=True)
    del X, V; D6.drop(wname)

# 1928-85 (weekday KF calendar): DEF3 vs BusEq (TECH) and vs KF market
d = D6.g6_data(); mk = D6._kf_market()
cal = d['cal']; mkt = D6._weekday(mk['mkt'], cal)
tech, def3, rf = d['TECH'], d['DEF3'], d['RF']
def st2(x, y):
    xe = x - rf; return dict(mu_ex_ann=float(xe.mean() * 252), vol_ann=float(xe.std() * np.sqrt(252)), sharpe_ann=float(xe.mean() / xe.std() * np.sqrt(252)),
                             corr_tech=float(np.corrcoef(x, y)[0, 1]))
O = {'TECH': st2(tech, tech), 'DEF3': st2(def3, tech), 'MKT': st2(mkt, tech)}
O['corr_DEF3_MKT'] = float(np.corrcoef(def3, mkt)[0, 1])
for a, b in (('1928-01-01', '1985-12-31'), ('1933-01-01', '1985-12-31'), ('1946-01-01', '1985-12-31')):
    m = (cal >= pd.Timestamp(a)) & (cal <= pd.Timestamp(b))
    O['corr_DEF3_TECH_%s_%s' % (a[:4], b[:4])] = float(np.corrcoef(def3[m], tech[m])[0, 1])
    O['volratio_DEF3_TECH_%s_%s' % (a[:4], b[:4])] = float(def3[m].std() / tech[m].std())
q = np.percentile(tech, 1); m = tech <= q
O['worst1pct_days'] = dict(tech=float(tech[m].mean()), def3=float(def3[m].mean()), mkt=float(mkt[m].mean()))
res['stats']['KF1928_85'] = O
json.dump(res, open(OUT + 'e2.json', 'w'), indent=1)
print('saved')
