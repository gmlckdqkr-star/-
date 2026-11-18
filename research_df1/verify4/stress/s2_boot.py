"""verify4/stress (e): alternative bootstrap pools for dev250 source (NDX 1986-01-02..2014-12-31, 500 paths x 30y, lo=1),
built exactly like measure_std/std.py contexts()['dev250_path'] but with other block/seed. RC vs QQQ hold. <=2014 only."""
import os, sys, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, df4cfg, std, ov, jp, iv
W = dfe.WARM; CID = 'v1|s0.3|L1.5|K0|RC'; cfg = df4cfg.cfg_of(CID)
a, b, P, blk0, seed0 = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
assert X.index.max() <= pd.Timestamp('2014-12-31'); print('source', X.index.min().date(), X.index.max().date(), len(X), 'P', P)
def build(block, seed):
    ii = ov.boot_idx(len(X), P=P, years=30, block=block, seed=seed, lo=1)
    c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}
    return DC._finish(c, X)
def pstat(o, T):
    cg, md = dfe.stats(o, T)
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)),
                loss_share=float(np.mean(cg < 0)))
OUT = dict(cfg=cfg, rows={}); t0 = time.time()
VARS = [('b250_s7_check', 250, 7), ('b250_s8', 250, 8), ('b250_s9', 250, 9), ('b125_s7', 125, 7), ('b125_s8', 125, 8), ('b125_s9', 125, 9),
        ('b125_s21_dev125pool', 125, 21), ('b500_s33_dev500pool', 500, 33)]
for nm, block, seed in VARS:
    m = build(block, seed); T = m['r'].shape[1]
    c = pstat(df4cfg.run_any(cfg, m), T); q = pstat(dfe.run(m, np.full(m['r'].shape, 1.0))[0], T)
    r = dict(block=block, seed=seed, cand=c, qqq=q, beats_both=bool(c['cagr'] > q['cagr'] and c['mdd_p10'] > q['mdd_p10']),
             beats_all4=bool(c['cagr'] > q['cagr'] and c['p10'] > q['p10'] and c['mdd'] > q['mdd'] and c['mdd_p10'] > q['mdd_p10']),
             gate_like=dict(V1=c['cagr'] > q['cagr'], V2=c['mdd'] > q['mdd'] + .05, E1=c['p10'] > q['p10'], E2=c['mdd_p10'] > q['mdd_p10'] + .05))
    OUT['rows'][nm] = r
    print('%-22s cand med %6.2f p10 %6.2f mddmed %6.1f mddp10 %6.1f | QQQ med %6.2f p10 %6.2f mddmed %6.1f mddp10 %6.1f | both %s all4 %s gates %s [%.0fs]'
          % (nm, c['cagr']*100, c['p10']*100, c['mdd']*100, c['mdd_p10']*100, q['cagr']*100, q['p10']*100, q['mdd']*100, q['mdd_p10']*100,
             r['beats_both'], r['beats_all4'], r['gate_like'], time.time() - t0), flush=True)
    del m
json.dump(OUT, open('/mnt/project-files/research/df1/verify4/stress/s2_boot.json', 'w'), indent=1); print('saved')
