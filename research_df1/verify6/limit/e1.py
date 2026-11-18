"""E1 (report-only): G6 strictness probes. 1928-85 weekday KF data only (no data after 1985 is touched)."""
import os, sys, json, numpy as np, pandas as pd
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df6v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import df6 as D6, dfk, df5fam as F, df5stress as ST, df5run as R, df5lib as L
WARM = 300
OUT = '/tmp/df6v/limit/'
idx = {c['id']: c for c in D6.configs()}
TOP5 = ['L|TQQQ|DEF3|R252|e0.60|c0.80', 'L|TQQQ|DEF3|R252|e0.65|c0.70', 'L|TQQQ|DEF3|R252|e0.70|c0.60',
        'L|TQQQ|DEF3|R252|e0.60|c0.75', 'L|TQQQ|DEF3|R252|e0.55|c0.80']
d = D6.g6_data(); cal = d['cal']; n = len(cal)
assert cal.max() <= pd.Timestamp('1985-12-31')
print('cal', cal[0].date(), cal[-1].date(), n)

def mkworld(ii):
    tech, def3, rf = d['TECH'][ii], d['DEF3'][ii], d['RF'][ii]
    core = (tech - 0.002 / 252, 0.02 / 252, 1); pr = tech - 0.02 / 252
    lev = {'TQQQ': (3 * pr - 2 * rf - 0.0245 / 252, 0.0, 1), 'QLD': (2 * pr - rf - 0.017 / 252, 0.0, 1)}
    slv = (def3 - D6.ER / 252, D6.DYS['DEF3'] / 252, 1)
    return dict(core=core, lev=lev, slv=slv, P=ii.shape[0], T=ii.shape[1], ii=ii)

def go(G, assets, w, reb, recon=False):
    P, T = G['P'], G['T']
    RET = np.stack([a[0] for a in assets], 2); INC = np.stack([np.broadcast_to(np.asarray(a[1], float), (P, T)) for a in assets], 2)
    HV = np.array([a[2] for a in assets], np.int64); Wt = np.broadcast_to(np.array(w, float), (P, T, len(w))).copy()
    o, EE = dfk.run(RET, INC, Wt, F.ev_changes(Wt), HV, reb_every=reb, recon=recon)
    cg, md = dfk.stats(o, T); return cg, md, EE

def single(ii_start, ii_end=None):
    s0 = int(cal.searchsorted(pd.Timestamp(ii_start))) - WARM
    e0 = n if ii_end is None else int(cal.searchsorted(pd.Timestamp(ii_end), side='right'))
    s0 = max(s0, 0)
    return np.arange(s0, e0)[None, :]

def ddinfo(EE, ii):
    e = EE[0]; pk = np.maximum.accumulate(e); dd = e / pk - 1; t = int(np.argmin(dd)); p = int(np.argmax(e[:t + 1]))
    dates = cal[ii[0, WARM:]]
    return dict(mdd=float(dd[t]), peak=str(dates[p].date()), trough=str(dates[t].date()))

res = {}
worlds = {'R2885': single('1928-01-03'), 'R3385': single('1933-01-03'), 'R4685': single('1946-01-02'),
          'R2932': single('1928-01-03', '1932-12-31'), 'R5585': single('1955-01-03')}
for wn, ii in worlds.items():
    G = mkworld(ii); dates = cal[ii[0, WARM:]]
    qcg, qmd, qE = go(G, [G['core']], [1.0], 0, recon=True)
    sd_cg, sd_md, sE = go(G, [G['slv']], [1.0], 0, recon=True)
    res[wn] = dict(eval_from=str(dates[0].date()), eval_to=str(dates[-1].date()), core=dict(cagr=float(qcg[0]), **ddinfo(qE, ii)),
                   def3_only=dict(cagr=float(sd_cg[0]), **ddinfo(sE, ii)), cfg={})
    for i in TOP5:
        c = idx[i]
        cg, md, E = go(G, [G['lev'][c['V']], G['core'], G['slv']], [c['a'], c['b'], c['c']], c['R'], recon=True)
        ddm = 1 - abs(md[0]) / abs(qmd[0])
        res[wn]['cfg'][i] = dict(cagr=float(cg[0]), ret_ex=float(cg[0] - qcg[0]), ddm=float(ddm), gate=bool(ST.gate_conds(cg, md, qcg, qmd, True)),
                                 logdd_ratio=float(np.log(1 + md[0]) / np.log(1 + qmd[0])), **ddinfo(E, ii))
    print(wn, json.dumps(res[wn], indent=None)[:200])

# bootstraps: OLD6 (locked), OLD6 with pool restricted to 1933-01..1985-12, OLD6 excluding Depression blocks (peak 1929 .. trough 1932 + 250d)
def boot_pool(starts, P=500, years=30, block=250, seed=33):
    g = np.random.default_rng(seed); T = WARM + years * 252; nb = T // block + 1
    st = starts[g.integers(0, len(starts), (P, nb))]
    return (st[:, :, None] + np.arange(block)[None, None, :]).reshape(P, -1)[:, :T]

lvT = np.cumprod(1 + d['TECH']); pos = lambda s: int(cal.searchsorted(pd.Timestamp(s)))
pk = pos('1929-01-01') + int(np.argmax(lvT[pos('1929-01-01'):pos('1930-01-01')])); tr = pk + int(np.argmin(lvT[pk:pos('1933-12-31')]))
print('BusEq Depression peak', cal[pk].date(), 'trough', cal[tr].date(), 'drop %.3f' % (lvT[tr] / lvT[pk] - 1))
excl = np.zeros(n, bool); excl[pk:min(tr + 250, n - 1) + 1] = True
starts_x = np.array([s for s in range(1, n - 250) if not excl[s:s + 250].any()])
starts_33 = np.arange(pos('1933-01-03'), n - 250)
boots = {'OLD6': L.ov.boot_idx(n, P=500, years=30, block=250, seed=33, lo=1), 'OLD6_33': boot_pool(starts_33), 'OLD6_XDEP': boot_pool(starts_x)}
res['_meta'] = dict(dep_peak=str(cal[pk].date()), dep_trough=str(cal[tr].date()), n_starts_xdep=int(len(starts_x)), n_starts_33=int(len(starts_33)))
for wn, ii in boots.items():
    G = mkworld(ii)
    qcg, qmd, _ = go(G, [G['core']], [1.0], 0)
    scg, smd, _ = go(G, [G['slv']], [1.0], 0)
    res[wn] = dict(core=R.summ(qcg, qmd), def3_only=R.summ(scg, smd), cfg={})
    for i in TOP5:
        c = idx[i]
        cg, md, _ = go(G, [G['lev'][c['V']], G['core'], G['slv']], [c['a'], c['b'], c['c']], c['R'])
        s = R.summ(cg, md, qcg); s['ddm_p10'] = float(1 - abs(np.percentile(md, 10)) / abs(np.percentile(qmd, 10)))
        s['gate'] = bool(ST.gate_conds(cg, md, qcg, qmd)); res[wn]['cfg'][i] = s
    print(wn, 'core', res[wn]['core'])
json.dump(res, open(OUT + 'e1.json', 'w'), indent=1)
