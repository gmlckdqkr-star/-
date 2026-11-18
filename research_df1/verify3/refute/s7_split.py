import os, sys, json, time, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR','/home/claude/nbcache_std'); os.environ.setdefault('NUMBA_NUM_THREADS','2')
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
t0 = time.time(); EX = 1.3988294390226633e-4
d = json.load(open('/mnt/project-files/research/df1/results/df3.json')); C = d['configs']; ids = list(C)
G1 = json.load(open('/mnt/project-files/research/df1/results/grid.json')); G2 = json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))
OLD = dict(G1['configs']); OLD.update(G2['configs'])
def cfg_of(k):
    if k in OLD: return OLD[k]['cfg']
    p = k.split('|'); s = None if p[4] == 'snone' else float(p[4][1:])
    return dict(id=k, fam='df3', M=p[2], k=p[3], sig=s, Lmax=float(p[5][1:]), knee=p[6], roff=p[7])
def run_any(cfg, m):
    if cfg.get('fam') == 'df3':
        L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']]); kw.update(vmode=0 if cfg['M'] == 'M0' else 2)
        return dfe.run(m, L, roff=RG.ROFF[cfg['roff']], **kw)[0]
    return R2.run_cfg(cfg, m)
mp = DC.market('dev250_path'); mp0 = dict(mp); mp0['rb'] = mp['rb'] - EX; T = mp['r'].shape[1]
sel = set()
for th in (-0.40, -0.50, -0.60):
    c = sorted([k for k in ids if C[k]['WD'] >= th], key=lambda k: -C[k]['P0']['cagr'])[:6]; sel.update(c)
sel = sorted(sel); R = {}
for k in sel:
    o0 = run_any(cfg_of(k), mp0); cg0, md0 = dfe.stats(o0, T); o = run_any(cfg_of(k), mp); cg, md = dfe.stats(o, T)
    assert abs(np.median(cg0) - C[k]['P0']['cagr']) < 1e-9, (k, np.median(cg0), C[k]['P0']['cagr'])
    R[k] = (cg0, md)
print('recomputed %d configs, all match df3.json P0, %.0fs' % (len(sel), time.time() - t0))
A, B = np.arange(250), np.arange(250, 500)
for th in (-0.40, -0.50, -0.60):
    print('tier', th)
    for half, (h1, h2) in (('A->B', (A, B)), ('B->A', (B, A))):
        def wd(k, h): return min(np.percentile(R[k][1][h], 10), C[k]['N']['mdd'], C[k]['S']['mdd'])
        c1 = [k for k in sel if wd(k, h1) >= th]; c2 = [k for k in sel if wd(k, h2) >= th]
        b1 = max(c1, key=lambda k: np.median(R[k][0][h1]))
        print('   %s pick on first half: %-36s P0 first %.4f -> other half %.4f ; best on other half (WD there) %-36s %.4f' % (
            half, b1, np.median(R[b1][0][h1]), np.median(R[b1][0][h2]), max(c2, key=lambda k: np.median(R[k][0][h2])), max(np.median(R[k][0][h2]) for k in c2)))
for k in sel: print('%-38s P0 full %.4f  A %.4f  B %.4f  WD %.3f' % (k, np.median(R[k][0]), np.median(R[k][0][A]), np.median(R[k][0][B]), C[k]['WD']))
