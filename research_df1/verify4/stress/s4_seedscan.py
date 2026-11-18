"""verify4/stress (e, extended): seed scan for block 125 / 250 / 500 (seeds 1..10), RC vs QQQ hold, same construction as s2_boot.py.
Reports per-variant medians/percentiles and how many seeds keep each comparison. <=2014 only."""
import os, sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, df4cfg, std, ov, jp, iv
cfg = df4cfg.cfg_of('v1|s0.3|L1.5|K0|RC')
a, b, P, _, _ = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
assert X.index.max() <= pd.Timestamp('2014-12-31')
def pstat(o, T):
    cg, md = dfe.stats(o, T)
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
OUT = dict(cfg=cfg, rows={}, summary={})
for block in (125, 250, 500):
    for seed in range(1, 11):
        ii = ov.boot_idx(len(X), P=P, years=30, block=block, seed=seed, lo=1)
        c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}; m = DC._finish(c, X); T = m['r'].shape[1]
        cs = pstat(df4cfg.run_any(cfg, m), T); q = pstat(dfe.run(m, np.full(m['r'].shape, 1.0))[0], T)
        OUT['rows']['b%d_s%d' % (block, seed)] = dict(cand=cs, qqq=q)
        print('b%-3d s%-2d cand %6.2f %6.2f %6.1f %6.1f | QQQ %6.2f %6.2f %6.1f %6.1f | dmed %+5.2f dp10mdd %+5.1f' % (block, seed,
              cs['cagr']*100, cs['p10']*100, cs['mdd']*100, cs['mdd_p10']*100, q['cagr']*100, q['p10']*100, q['mdd']*100, q['mdd_p10']*100,
              (cs['cagr']-q['cagr'])*100, (cs['mdd_p10']-q['mdd_p10'])*100), flush=True)
        del m, c
    rr = [OUT['rows']['b%d_s%d' % (block, s)] for s in range(1, 11)]
    dm = np.array([r['cand']['cagr'] - r['qqq']['cagr'] for r in rr]); dd = np.array([r['cand']['mdd_p10'] - r['qqq']['mdd_p10'] for r in rr])
    dv2 = np.array([r['cand']['mdd'] - r['qqq']['mdd'] for r in rr]); de1 = np.array([r['cand']['p10'] - r['qqq']['p10'] for r in rr])
    OUT['summary']['b%d' % block] = dict(n=10, med_beats=int((dm > 0).sum()), p10mdd_beats=int((dd > 0).sum()), both=int(((dm > 0) & (dd > 0)).sum()),
        all_US_path_gates_5pp=int(((dm > 0) & (dd > .05) & (dv2 > .05) & (de1 > 0)).sum()),
        dmed_median_pp=float(np.median(dm) * 100), dmed_min_pp=float(dm.min() * 100), dmed_max_pp=float(dm.max() * 100),
        dp10mdd_min_pp=float(dd.min() * 100), dp10mdd_median_pp=float(np.median(dd) * 100))
    print('SUMMARY b%d' % block, OUT['summary']['b%d' % block], flush=True)
json.dump(OUT, open('/mnt/project-files/research/df1/verify4/stress/s4_seedscan.json', 'w'), indent=1); print('saved')
