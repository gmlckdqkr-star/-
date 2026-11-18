"""E4: own frictionless, pre-tax daily vol targeting on NDX (+0.55%/yr dividend), 1-day lag, financed/invested at rf, no cost.
Compared with frictionless QQQ (same NDX + dividend, no expense) and with constant daily-rebalanced leverage. Worlds X30 and P30.
Post-hoc, report-only. Writes /tmp/df5v/limit/exp_e4.json"""
import os, sys, time, json
os.environ['NUMBA_CACHE_DIR'] = '/tmp/df5v/limit/nb'
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import numpy as np
import df5lib as L
WARM = 300; DQ = 0.0055
t0 = time.time()
def log(*a): print('%6.0fs' % (time.time() - t0), *a, flush=True)

def roll_std(a, n):
    c1 = np.cumsum(np.c_[np.zeros(a.shape[0]), a], axis=1); c2 = np.cumsum(np.c_[np.zeros(a.shape[0]), a * a], axis=1)
    out = np.full(a.shape, np.nan); m1 = (c1[:, n:] - c1[:, :-n]) / n; m2 = (c2[:, n:] - c2[:, :-n]) / n
    out[:, n - 1:] = np.sqrt(np.maximum(m2 - m1 * m1, 0) * n / (n - 1)); return out

def perf(dr):
    """dr: (P, n) daily returns from WARM+1..T-1 -> cagr, mdd"""
    lw = np.cumsum(np.log1p(dr), axis=1); lw = np.c_[np.zeros(dr.shape[0]), lw]
    yrs = dr.shape[1] / 252.0
    cg = np.exp(lw[:, -1] / yrs) - 1
    dd = lw - np.maximum.accumulate(lw, axis=1); mdd = np.expm1(dd.min(axis=1))
    return cg, mdd

def summ(cg, md, qcg, qmd):
    d = dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd_p10=float(np.percentile(md, 10)), mdd_med=float(np.median(md)),
             pair=float(np.median(cg - qcg)), win=float(np.mean(cg > qcg)))
    d['ddm'] = 1 - abs(d['mdd_p10']) / abs(float(np.percentile(qmd, 10)))
    d['gate'] = bool(d['pair'] > 0 and d['cagr'] > np.median(qcg) and d['p10'] >= np.percentile(qcg, 10) and d['ddm'] >= 0.1)
    d['both0'] = bool(d['pair'] > 0 and d['ddm'] >= 0)
    return d

OUT = {}
for wname in ('X', 'P'):
    w = L.world(wname); m = w['m']; log(wname, 'loaded', m['r'].shape)
    r = np.nan_to_num(m['r']).astype(np.float64); rf = np.nan_to_num(m['rf']).astype(np.float64)
    T = r.shape[1]; assert T == WARM + 30 * 252
    u = r + DQ / 252
    sl = slice(WARM + 1, T)                     # days with returns; decision at t-1 (1-day lag)
    qcg, qmd = perf(u[:, sl])
    res = {'QQQ_frictionless': dict(cagr=float(np.median(qcg)), p10=float(np.percentile(qcg, 10)), mdd_p10=float(np.percentile(qmd, 10)),
                                    mdd_med=float(np.median(qmd)))}
    vol_ann = float(np.median(np.std(r[:, WARM:], axis=1) * np.sqrt(252))); res['ndx_vol_median_path'] = vol_ann
    # constant leverage line
    for Lc in [0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2, 1.3, 1.5]:
        dr = Lc * u[:, sl] + (1 - Lc) * rf[:, sl]; cg, md = perf(dr); res['CONST|L%.2f' % Lc] = summ(cg, md, qcg, qmd)
    for wn in (20, 60):
        sd = roll_std(r, wn) * np.sqrt(252)
        for s in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35):
            for lm in (1.0, 1.5, 2.0, 3.0):
                Lt = np.where(np.isnan(sd), 0.0, np.minimum(lm, s / np.maximum(sd, 1e-9)))
                Lp = Lt[:, WARM:T - 1]                    # exposure decided at close t-1
                dr = Lp * u[:, sl] + (1 - Lp) * rf[:, sl]; cg, md = perf(dr)
                d = summ(cg, md, qcg, qmd); d['avgL'] = float(np.median(Lp.mean(axis=1)))
                res['VT|s%.2f|w%d|L%.1f' % (s, wn, lm)] = d
    OUT[wname] = res
    log(wname, 'QQQ', res['QQQ_frictionless'], 'gate', sum(1 for k, v in res.items() if isinstance(v, dict) and v.get('gate')),
        'both0', sum(1 for k, v in res.items() if isinstance(v, dict) and v.get('both0')))
    del w, m, r, rf, u; L._WORLDS.pop(wname, None)
json.dump(OUT, open('/tmp/df5v/limit/exp_e4.json', 'w'))
log('done')
