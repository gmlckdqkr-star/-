"""verify4/stress (e x E4/E5): pre-registered E4 (cost 2x) / E5 (delay 4) re-asked on alternative bootstrap pools.
Pool QQQ hold under the SAME change is the comparator (E4/E5 as registered compare with the base QQQ row; both shown). <=2014 only."""
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, df4cfg, std, ov, jp, iv
cfg = df4cfg.cfg_of('v1|s0.3|L1.5|K0|RC'); MG = 0.05
a, b, P, _, _ = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
assert X.index.max() <= pd.Timestamp('2014-12-31')
def pstat(o, T):
    cg, md = dfe.stats(o, T)
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
OUT = {}
for block, seed in ((250, 8), (250, 9), (125, 7), (125, 8), (125, 9), (125, 21)):
    ii = ov.boot_idx(len(X), P=P, years=30, block=block, seed=seed, lo=1)
    c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}; m = DC._finish(c, X); T = m['r'].shape[1]
    q0 = pstat(dfe.run(m, np.full(m['r'].shape, 1.0))[0], T); row = dict(qqq_base=q0)
    for k, kw in (('cost2x', dict(cost=0.006)), ('delay4', dict(delay=4)), ('delay3+cost1.5x', dict(delay=3, cost=0.0045))):
        cs = pstat(df4cfg.run_any(cfg, m, **kw), T); q = pstat(dfe.run(m, np.full(m['r'].shape, 1.0), **kw)[0], T)
        row[k] = dict(cand=cs, qqq_same=q, gate_vs_base=bool(cs['cagr'] > q0['cagr'] and cs['mdd_p10'] > q0['mdd_p10'] + MG),
                      beats_same_both=bool(cs['cagr'] > q['cagr'] and cs['mdd_p10'] > q['mdd_p10']))
        print('b%d s%-2d %-16s cand %6.2f / p10mdd %6.1f | QQQ same %6.2f / %6.1f | QQQ base %6.2f / %6.1f | E-gate(vs base,5pp) %s | beats same-change both %s'
              % (block, seed, k, cs['cagr']*100, cs['mdd_p10']*100, q['cagr']*100, q['mdd_p10']*100, q0['cagr']*100, q0['mdd_p10']*100,
                 row[k]['gate_vs_base'], row[k]['beats_same_both']), flush=True)
    OUT['b%d_s%d' % (block, seed)] = row; del m, c
json.dump(OUT, open('/mnt/project-files/research/df1/verify4/stress/s5_boot_e4e5.json', 'w'), indent=1); print('saved')
