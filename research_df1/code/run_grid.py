"""DF1 grid (PRECOMMIT_DF1.md section 2): 480 + 3 static configs, plus reference rows, on selection + validation bases.
Writes results/grid.json. Every number is <=2014 development data (no post-2014 row exists in any input)."""
import sys, json, itertools, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, std, rx

KS = ('v1', 'always'); SIGS = (None, 0.10, 0.15, 0.20, 0.30); LMAX = (1.0, 1.5, 2.0, 3.0)
KNEES = {'K0': dict(kon=0), 'K1': dict(kon=1, d0=-0.10, d1=-0.20, kfl=0.25), 'K2': dict(kon=1, d0=-0.15, d1=-0.30, kfl=0.25)}
ROFF = {'RC': 0, 'RT': 1, 'RB': 2, 'RBT': 3}
BASES = DC.SEL + DC.VAL

def configs():
    C = []
    for k, s, L, kn, ro in itertools.product(KS, SIGS, LMAX, KNEES, ROFF):
        C.append(dict(id='%s|s%s|L%s|%s|%s' % (k, 'none' if s is None else s, L, kn, ro), fam='grid', k=k, sig=s, Lmax=L, knee=kn, roff=ro))
    for w in (0.3, 0.5, 0.7):
        C.append(dict(id='static|QQQ%d|bond' % int(w * 100), fam='static', w=w))
    return C

def summ(o, T, path):
    cg, md = dfe.stats(o, T)
    d = dict(cagr=float(np.median(cg)), mdd=float(np.median(md)))
    if path:
        d.update(p10=float(np.percentile(cg, 10)), mdd_p10=float(np.percentile(md, 10)),
                 pdd20=float(np.mean(md <= -0.20)), pdd30=float(np.mean(md <= -0.30)), pdd40=float(np.mean(md <= -0.40)),
                 dd80=float(np.mean(md <= -0.80)), w7=float(np.median(o[:, 2])), w12=float(np.median(o[:, 3])),
                 lev=float(np.median(o[:, 8])), ntr=float(np.median(o[:, 4])))
    else:
        d.update(w7=float(o[0, 2]), w12=float(o[0, 3]), lev=float(o[0, 8]), ntr=float(o[0, 4]))
    return d

def run_cfg(cfg, m, **extra):
    if cfg['fam'] == 'static':
        L = np.full(m['r'].shape, cfg['w']); o, _ = dfe.run(m, L, roff=2, reb_every=252, **extra)
    else:
        L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(KNEES[cfg['knee']]); kw.update(extra)
        o, _ = dfe.run(m, L, roff=ROFF[cfg['roff']], **kw)
    return o

def refs(m):
    c = m['ctx']; T = m['r'].shape[1]; path = m['r'].shape[0] > 1; R = {}
    B, bfn, bp, fs = std.s085(c); cg, E = std.engine(c, B, bfn, bp, fs, cspr=10.0)
    md = (E / np.maximum.accumulate(E, axis=1) - 1).min(axis=1)
    R['v1_locked_cash0'] = dict(cagr=float(np.median(cg)), mdd=float(np.median(md)))
    if path: R['v1_locked_cash0'].update(p10=float(np.percentile(cg, 10)), mdd_p10=float(np.percentile(md, 10)), dd80=float(np.mean(md <= -0.8)),
                                         pdd20=float(np.mean(md <= -0.2)), pdd30=float(np.mean(md <= -0.3)), pdd40=float(np.mean(md <= -0.4)),
                                         w7=float(np.median(E[:, 7 * 252 - 1])), w12=float(np.median(E[:, 12 * 252 - 1])))
    for nm, L in (('hold1x_QQQ', 1.0), ('hold3x_TQQQ', 3.0)):
        o, _ = dfe.run(m, np.full(m['r'].shape, L)); R[nm] = summ(o, T, path)
    return R

if __name__ == '__main__':
    t0 = time.time(); C = configs(); out = dict(N=len(C), configs={}, refs={})
    for bn in BASES:
        m = DC.market(bn); T = m['r'].shape[1]; path = m['r'].shape[0] > 1
        out['refs'][bn] = refs(m)
        for cfg in C:
            out['configs'].setdefault(cfg['id'], dict(cfg=cfg))[bn] = summ(run_cfg(cfg, m), T, path)
        print('%-16s done %.0fs' % (bn, time.time() - t0), flush=True)
        if bn == 'dev250_path': DC._M.pop(bn, None)
    json.dump(out, open('/mnt/project-files/research/df1/results/grid.json', 'w'))
    print('N', len(C), 'time %.0fs' % (time.time() - t0))
