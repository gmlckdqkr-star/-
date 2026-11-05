"""MF1 runner: MS1 5 bases, v1 (s0.85) signal/brake, TQQQ vs MNQ-futures implementation. Usage: python3 -B mfrun.py [parity|grid]"""
import sys, os, json, itertools, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/measure_std'); sys.path.insert(0, os.path.dirname(__file__))
import std, beng, bk, ce, mfeng
OUT = '/mnt/project-files/research/mf1/results/'
NOTIONAL = 73e6   # 1 MNQ in KRW at start (NDX ~26,000 x $2 x 1,400 KRW, inferred)

_FEAT = {}
def run(c, bn, mode=0, L3x=3.0, W0=1e7, cont=False, cmode=0, s=0.004, fee=0.0002, m=0.07, taxf=0.11, daily=0):
    B, bfn, bp, fstep = std.s085(c)
    if bn not in _FEAT: _FEAT[bn] = np.ascontiguousarray(bk.features(c))
    k = dict(beng.F1); k['fstep'] = fstep; k['W0'] = W0; pp, D = beng._args(k)
    N0 = 0.0 if cont else NOTIONAL / W0
    o, EE = mfeng.runPF(np.ascontiguousarray(c.r), np.ascontiguousarray(c.rf), np.ascontiguousarray(B, dtype=np.float64), _FEAT[bn],
                        int(pp['delay']), pp['cost'], pp['tax'], D, int(pp['harvest']), pp['hthr'], pp['cspr'], pp['er3'], pp['step'],
                        bfn, np.asarray(bp, dtype=np.float64), float(pp['fstep']), mode, L3x, N0, cmode, s, fee, m, taxf, daily)
    yrs = EE.shape[1] / 252
    return np.maximum(o[:, 0], 1e-9) ** (1 / yrs) - 1, EE, o

def summ(fin, EE, o, ref):
    r, _ = std.row(fin, EE); d = fin - ref
    r.update(d=float(np.median(d)), pw=float(np.mean(d > 1e-5)), avglev=float(np.median(o[:, 9])),
             p_liq=float(np.mean(o[:, 10] > 0)), p_neg=float(np.mean(o[:, 11] > 0)), maxlev=float(np.max(o[:, 12])))
    return r

def parity():
    C = std.contexts()
    for bn in ('real_ndx_86_14', 'dev250_path'):
        c = C[bn]; fin, EE, o = run(c, bn, 0)
        B, bfn, bp, fs = std.s085(c); f2, E2 = std.engine(c, B, bfn, bp, fs)
        print(bn, 'mf mode0 med %.5f  std %.5f  maxabs %.2e' % (np.median(fin), np.median(f2), np.max(np.abs(fin - f2))), flush=True)

def grid(daily=0, cms=(0, 1), tag=''):
    C = std.contexts(); rows = []
    W0s = [(3e7, False), (5e7, False), (1e8, False), (1e8, True)]
    for bn, c in C.items():
        refs = {}
        for W0, cont in W0s:
            if W0 not in refs:
                refs[W0] = run(c, bn, 0, W0=W0)
                fr, Er, orr = refs[W0]
                rr = summ(fr, Er, orr, fr); rr.update(base=bn, cand='v1_TQQQ', W0=W0); rows.append(rr); print(rr, flush=True)
            fr = refs[W0][0]
            for L3x, cm, s in itertools.product((3.0, 3.5, 4.0), cms, (0.004, 0.008)):
                fin, EE, o = run(c, bn, 1, L3x=L3x, W0=W0, cont=cont, cmode=cm, s=s, daily=daily)
                rr = summ(fin, EE, o, fr)
                rr.update(base=bn, cand=tag + 'F_L%.1f_%s_c%d_s%.1f' % (L3x, 'cont' if cont else '%dM' % (W0 / 1e6), cm, s * 100), W0=W0,
                          L3x=L3x, cont=cont, cmode=cm, s=s)
                rows.append(rr); print('%-14s %-28s cagr %.4f d %+.4f pw %.2f dd80 %.2f dd95 %.2f liq %.2f neg %.3f lev %.2f max %.2f' % (
                    bn, rr['cand'], rr['cagr'], rr['d'], rr['pw'], rr.get('dd80', np.nan), rr.get('dd95', np.nan), rr['p_liq'], rr['p_neg'],
                    rr['avglev'], rr['maxlev']), flush=True)
    os.makedirs(OUT, exist_ok=True); json.dump(rows, open(OUT + 'grid%s_le2014.json' % tag, 'w'), indent=1)

if __name__ == '__main__':
    {'parity': parity, 'grid': grid, 'a1': lambda: grid(1, (0, 1, 2), 'A1_')}[sys.argv[1]]()
