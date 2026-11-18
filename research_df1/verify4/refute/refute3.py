"""verify4 / refute part 3: bootstrap-seed sensitivity of the path gates (V1 V2 E1 E2 E4 E5) for RC and RB.
Same pool (NDX 1986-01-02..2014-12-31), same 500 x 30y, block 250, lo=1; only the seed changes (seed 7 = DF4). <=2014 only."""
import os, sys, json
os.environ['NUMBA_CACHE_DIR'] = '/home/claude/nbcache_verify4'
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, df4cfg
from dfctx import std
import ov, jp, iv
OUTP = sys.argv[1] if len(sys.argv) > 1 else '/tmp/v4_refute/refute3_numbers.json'
EX = 1.3988294390226633e-4; MG = 0.05
a, b, P, blk, seed0 = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= pd.Timestamp('2014-12-31')
F = ov.flags_hist(X)
IDS = ('v1|s0.3|L1.5|K0|RC', 'v1|s0.3|L1.5|K0|RB')
OUT = {}
def pst(cg, md): return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
for sd in (7, 1, 2, 3, 4, 5, 6, 11, 23, 42):
    ii = ov.boot_idx(len(X), P=P, years=30, block=blk, seed=sd, lo=1)
    c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}; m = DC._finish(c, X); m0 = dict(m); m0['rb'] = m['rb'] - EX; T = m['r'].shape[1]
    q = pst(*dfe.stats(dfe.run(m, np.full(m['r'].shape, 1.0))[0], T)); cq = dfe.stats(dfe.run(m, np.full(m['r'].shape, 1.0))[0], T)[0]
    row = dict(QQQ=q)
    for i in IDS:
        cfg = df4cfg.cfg_of(i); mm = m0 if cfg['roff'] in ('RB', 'RBT') else m
        cg, md = dfe.stats(df4cfg.run_any(cfg, mm), T); base = pst(cg, md)
        c2 = pst(*dfe.stats(df4cfg.run_any(cfg, mm, cost=0.006), T)); d4 = pst(*dfe.stats(df4cfg.run_any(cfg, mm, delay=4), T))
        g = dict(V1=base['cagr'] > q['cagr'], V2=base['mdd'] > q['mdd'] + MG, E1=base['p10'] > q['p10'], E2=base['mdd_p10'] > q['mdd_p10'] + MG,
                 E4=c2['cagr'] > q['cagr'] and c2['mdd_p10'] > q['mdd_p10'] + MG, E5=d4['cagr'] > q['cagr'] and d4['mdd_p10'] > q['mdd_p10'] + MG)
        row[i] = dict(base=base, c2=c2, d4=d4, gates=g, win_cagr_vs_q=float(np.mean(cg > cq)))
    OUT[str(sd)] = row
    print(sd, 'QQQ %.2f/%.1f' % (q['cagr'] * 100, q['mdd_p10'] * 100),
          ' | '.join('%s %.2f c2 %.2f d4 %.2f p10 %.2f mddp10 %.1f %s' % (i[-2:], row[i]['base']['cagr'] * 100, row[i]['c2']['cagr'] * 100, row[i]['d4']['cagr'] * 100,
                                                                     row[i]['base']['p10'] * 100, row[i]['base']['mdd_p10'] * 100,
                                                                     ''.join(k for k, v in row[i]['gates'].items() if not v) or 'all-pass') for i in IDS), flush=True)
json.dump(OUT, open(OUTP, 'w'), indent=1)
