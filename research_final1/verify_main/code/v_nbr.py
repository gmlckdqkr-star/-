"""Independent verifier, lane NBR (PRECOMMIT_FINAL1 section 2). Written from the PRECOMMIT text; does not import
research/final1/code/*. Own signal builder (SMA / vol / hysteresis gate re-implemented with pandas rolling), sub-accounts through
the std engine kernel (ce.runPE with the std.engine argument list), mean of after-tax finals, paired difference vs v1 per path."""
import os, sys, json, time
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/ov1/code')
import ov1lib as L, std, rx, ce, beng, bk
sys.path.insert(0, '/mnt/project-files/research/crash_overlay/code')
import strat as S_lib          # library fam4, used ONLY to cross-check my own signal
OUT = '/mnt/project-files/research/final1/verify_main/results/'
NBR5 = [(200, .40), (180, .40), (220, .40), (200, .35), (200, .45)]
NBR9 = [(sl, v) for sl in (180, 200, 220) for v in (.35, .40, .45)]
WARM = beng.WARM

def my_signal(c, sl, vcap, band=0.02):
    lvl = np.cumprod(1.0 + c.r, axis=1)
    sm = pd.DataFrame(lvl.T).rolling(sl).mean().values.T                       # trailing sl closes incl. today
    v = pd.DataFrame(np.log1p(c.r).T).rolling(20).std(ddof=0).values.T * np.sqrt(252.0)
    B = np.where(v > vcap, 1.0, 3.0)
    a6 = np.asarray(c.F['shock6m'], bool); inv = np.asarray(c.F['inv'], bool)
    B = np.where(a6, np.minimum(B, 1.0), B)                                    # caution tier: cap 1x
    cond = inv | a6
    below = lvl < sm * (1 - band); above = lvl > sm * (1 + band)
    P, T = lvl.shape; off = np.zeros(P, bool); out = np.empty((P, T))
    for t in range(T):
        off = np.where(off, ~(above[:, t] | ~cond[:, t]), below[:, t] & cond[:, t])
        out[:, t] = np.where(off, 0.0, B[:, t])
    return out

def kernel(c, B, feat, **kw):
    k = dict(beng.F1); k['fstep'] = 0.1; k.update(kw); pp, D = beng._args(k)
    o, EE = ce.runPE(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), np.ascontiguousarray(B, dtype=np.float64), feat,
                     int(pp['delay']), pp['cost'], pp['tax'], D, int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'], pp['step'],
                     rx.av23s, np.asarray(rx.P_av23s(.85), dtype=np.float64), float(pp['fstep']))
    return o[:, 0].copy(), EE

def mdd_of(E): return (E / np.maximum.accumulate(E, axis=1) - 1).min(axis=1)

t0 = time.time(); res = {}; sigchk = {}
TAGS = (('base', {}), ('delay3', {'delay': 3}), ('cost2x', {'cost': 0.006}))
for bn, c in std.contexts().items():
    feat = np.ascontiguousarray(bk.features(c)); T = c.r.shape[1]; yrs = (T - WARM) / 252.0
    sig = {}
    for p in NBR9:
        mine = my_signal(c, *p)
        lib = S_lib.fam4(c, 3.0, p[1], 1.0, caution=('shock6m',), Lc=1.0, sl=p[0], band=0.02)
        nd_all = int(np.sum(mine != lib)); nd_live = int(np.sum(mine[:, WARM - 1:] != lib[:, WARM - 1:]))
        sigchk['%s|%d_%.2f' % (bn, p[0], p[1])] = dict(cells=int(mine.size), diff_all=nd_all, diff_from_warm=nd_live)
        sig[p] = mine
    c3 = bk.C3sig(c); sigchk['%s|centre_vs_C3sig' % bn] = int(np.sum(sig[(200, .40)][:, WARM - 1:] != c3[:, WARM - 1:]))
    for tag, kw in TAGS:
        fins = {}; EEs = {}
        for p in NBR9: fins[p], EEs[p] = kernel(c, sig[p], feat, **kw)
        # v1 reference through the locked std.engine under the same terms
        rB, rbf, rbp, rfs = std.s085(c); f_v1, E_v1 = std.engine(c, rB, rbf, rbp, rfs, **kw)
        f_c = np.maximum(fins[(200, .40)], 1e-9) ** (1 / yrs) - 1
        centre_gap = float(np.max(np.abs(f_c - f_v1)))
        for nm, pts in (('NBR5', NBR5), ('NBR9', NBR9)):
            fin = np.mean([np.maximum(fins[p], 1e-9) for p in pts], axis=0)                 # equal start, never rebalanced
            cg = np.maximum(fin, 1e-9) ** (1 / yrs) - 1
            Em = np.mean([EEs[p] for p in pts], axis=0); m = mdd_of(Em); d = cg - f_v1
            row = dict(cagr=float(np.median(cg)), mdd=float(np.median(m)), d_vs_v1=float(np.median(d)), pw_vs_v1=float(np.mean(d > 1e-5)),
                       d_mean=float(np.mean(d)), v1=float(np.median(f_v1)), centre_gap=centre_gap,
                       w7=float(np.median(Em[:, 7 * 252 - 1])), w12=float(np.median(Em[:, 12 * 252 - 1])),
                       sub_cagr={'%d_%.2f' % p: float(np.median(np.maximum(fins[p], 1e-9) ** (1 / yrs) - 1)) for p in pts})
            if len(cg) > 1: row.update(p10=float(np.percentile(cg, 10)), dd80=float(np.mean(m <= -0.8)))
            res.setdefault('%s|%s' % (nm, tag), {})[bn] = row
    print(bn, 'done %.0fs' % (time.time() - t0), flush=True)
for k in ('NBR5|base', 'NBR9|base', 'NBR5|delay3', 'NBR9|delay3', 'NBR5|cost2x', 'NBR9|cost2x'):
    r = res[k]
    print('%-12s path %.6f d %+.6f pw %.3f dd80 %.3f | real %.6f d %+.6f | spx55 d %+.6f spx70 d %+.6f | centre_gap %.1e' % (
        k, r['dev250_path']['cagr'], r['dev250_path']['d_vs_v1'], r['dev250_path']['pw_vs_v1'], r['dev250_path']['dd80'],
        r['real_ndx_86_14']['cagr'], r['real_ndx_86_14']['d_vs_v1'], r['real_spx_55_85']['d_vs_v1'], r['real_spx_70_85']['d_vs_v1'],
        max(r[b]['centre_gap'] for b in r)))
b5, b9 = res['NBR5|base'], res['NBR9|base']
ok = lambda b: bool(b['dev250_path']['d_vs_v1'] > 0.003 and b['dev250_path']['pw_vs_v1'] >= 0.55 and b['real_ndx_86_14']['d_vs_v1'] > 0)
res['PASS'] = dict(NBR5=ok(b5), NBR9=ok(b9), both_path_positive=bool(b5['dev250_path']['d_vs_v1'] > 0 and b9['dev250_path']['d_vs_v1'] > 0))
res['signal_check'] = sigchk
print('PASS', res['PASS'])
print('signal cells differing from library fam4 (from WARM-1 on):', {k: v['diff_from_warm'] for k, v in sigchk.items() if isinstance(v, dict) and v['diff_from_warm']},
      '| centre vs C3sig:', {k: v for k, v in sigchk.items() if not isinstance(v, dict)})
json.dump(res, open(OUT + 'v_nbr.json', 'w'), indent=1, default=float)
print('done %.0fs' % (time.time() - t0))
