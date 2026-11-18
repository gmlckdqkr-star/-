"""Verifier G6: KF 1928-01-03..1985-12-31 weekday calendar built here; Saturday returns compounded into the next weekday trading date."""
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/tmp/df6v/repro')
import mysim as M
WARM = 300
CUT = pd.Timestamp('1985-12-31')
DY3 = (0.025 + 0.015 + 0.040) / 3
tech = M.load_csv('TECH', CUT); rf = M.load_csv('RF', CUT); d3 = M.def3_series(CUT)
cal = tech.index[(tech.index >= pd.Timestamp('1928-01-03')) & (tech.index.weekday < 5)]
def wk(s):
    s = s[s.index >= pd.Timestamp('1928-01-01')]           # drop pre-calendar history instead of folding it into day 0
    pos = np.searchsorted(cal.values, s.index.values, side='left')
    ok = pos < len(cal)
    g = pd.Series(np.log1p(s.values[ok])).groupby(pos[ok]).sum()
    out = np.zeros(len(cal)); out[g.index.values] = np.expm1(g.values)
    return out
TE, RF, D3 = wk(tech), wk(rf), wk(d3)
sat = (tech.index.weekday == 5) & (tech.index >= pd.Timestamp('1928-01-03'))
info = dict(n=len(cal), first=str(cal[0].date()), last=str(cal[-1].date()), eval_start=str(cal[WARM].date()), n_saturdays_folded=int(sat.sum()),
            last_saturday=str(tech.index[sat][-1].date()) if sat.any() else None, yrs=(len(cal) - WARM) / 252)
def run(ii, cfg):
    te, r_, d_ = TE[ii], RF[ii], D3[ii]
    core = te - 0.002 / 252
    fq, mq = M.sim(core[:, :, None], np.array([0.02 / 252]), [1.0], 0); T = ii.shape[1]; qcg = M.cagr(fq, T)
    pr = te - 0.02 / 252
    lev = 3 * pr - 2 * r_ - 0.0245 / 252
    RET = np.stack([lev, core, d_ - 0.0015 / 252], 2); INC = np.array([0.0, 0.02 / 252, DY3 / 252])
    f, md = M.sim(RET, INC, [cfg['a'], cfg['b'], cfg['c']], cfg['R']); cg = M.cagr(f, T)
    return cg, md, qcg, mq
cfg = dict(a=0.20, b=0.0, c=0.80, R=252)
res = {'info': info}
cg, md, qcg, mq = run(np.arange(len(cal))[None, :], cfg)
res['R2885'] = dict(cagr=float(cg[0]), mdd=float(md[0]), core_cagr=float(qcg[0]), core_mdd=float(mq[0]),
                    dd_req=float(0.9 * mq[0]), ddm=float(1 - abs(md[0]) / abs(mq[0])))
# OLD6 bootstrap (re-implemented index draw; compare with ov.boot_idx)
n = len(cal); T = WARM + 30 * 252; nb = T // 250 + 1; g = np.random.default_rng(33); st = g.integers(1, n - 250, (500, nb))
ii = (st[:, :, None] + np.arange(250)[None, None, :]).reshape(500, -1)[:, :T]
cg, md, qcg, mq = run(ii, cfg)
res['OLD6'] = dict(cand=M.summ(cg, md, qcg), core=M.summ(qcg, mq), ddm=float(1 - abs(np.percentile(md, 10)) / abs(np.percentile(mq, 10))))
# extra (report): 63-day config
cg, md, qcg, mq = run(np.arange(len(cal))[None, :], dict(a=0.20, b=0.05, c=0.75, R=63))
res['R2885_c63'] = dict(cagr=float(cg[0]), mdd=float(md[0]), core_cagr=float(qcg[0]), core_mdd=float(mq[0]))
# where is the drawdown? (R2885 path, top config) - dates of trough only (pre-1986)
json.dump(res, open('/tmp/df6v/repro/res_G6.json', 'w'), indent=1)
print(json.dumps(res, indent=1))
