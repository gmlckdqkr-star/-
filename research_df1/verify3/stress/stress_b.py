"""stress B: rebuild the X world (df3.py section 1, copied) with seeds 7 (parity), 8, 9; picks + RG.refs. <=2014 only."""
import os, sys, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
from dfctx import std
jp, ov, iv = std.jp, std.ov, std.iv
EX = 1.3988294390226633e-4
END = pd.Timestamp('2014-12-31'); BLK = 250; YRS = 30
OUTD = '/mnt/project-files/research/df1/verify3/stress/'
t0 = time.time()
def log(*a): print('[%5.0fs]' % (time.time() - t0), *a, flush=True)

ALLC = {c['id']: c for c in RG.configs() + R2.configs()}
PICKS = dict(T25='v1|s0.1|L1.0|K1|RB', T40='v1|s0.3|L1.0|K2|RB', W40='DF2|M0|b3|v1|s0.3|L1.0|K2|RB',
             P50='DF3|N3|M2|v1|s0.2|L1.0|K0|RB', S50='static|QQQ50|bond', S70='static|QQQ70|bond')
CFG = {nm: (ALLC[cid] if cid in ALLC else dict(id=cid, fam='df3', M='M2', k='v1', sig=0.2, Lmax=1.0, knee='K0', roff='RB')) for nm, cid in PICKS.items()}
def run3(cfg, m, **extra):
    L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']]); kw.update(vmode=0 if cfg['M'] == 'M0' else 2); kw.update(extra)
    o, _ = dfe.run(m, L, roff=RG.ROFF[cfg['roff']], **kw); return o
def run_any(cfg, m, **extra):
    f = cfg.get('fam')
    if f == 'df3': return run3(cfg, m, **extra)
    if f == 'df2': return R2.run_cfg(cfg, m, **extra)
    return RG.run_cfg(cfg, m, **extra)
def sm(o, m):
    Tm = m['r'].shape[1]; cg, md = dfe.stats(o, Tm)
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))

# ---- df3.py section 1 (copied; only the seed changes)
a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= END
lv = np.cumprod(1 + X['r'].fillna(0).values); D = X.index; n = len(X)
def pos(d): return int(D.searchsorted(pd.Timestamp(d)))
def amax(x, y): i, j = pos(x), pos(y); return i + int(np.argmax(lv[i:j]))
def amin(x, y): i, j = pos(x), pos(y); return i + int(np.argmin(lv[i:j]))
tr1 = amin('1987-10-01', '1988-01-01'); pk1 = pos('1987-01-01') + int(np.argmax(lv[pos('1987-01-01'):tr1 + 1]))
pk2 = amax('2000-01-01', '2001-01-01'); tr2 = pk2 + int(np.argmin(lv[pk2:pos('2004-01-01')]))
pk3 = amax('2007-01-01', '2008-07-01'); tr3 = amin('2008-07-01', '2009-07-01')
excl = np.zeros(n, bool)
for nm, p_, t_ in (('E1_black_monday', pk1, tr1), ('E2_dotcom', pk2, tr2), ('E3_gfc', pk3, tr3)):
    e = min(t_ + BLK, n - 1); excl[p_:e + 1] = True
starts = np.array([s for s in range(1, n - BLK) if not excl[s:s + BLK].any()])
T = ov.WARM + YRS * 252; nb = T // BLK + 1
log('allowed starts', len(starts), 'P', P)
F = ov.flags_hist(X)
D3 = json.load(open('/mnt/project-files/research/df1/results/df3.json'))
RES = dict(picks=PICKS, seeds={})
for SEED in [int(s) for s in sys.argv[1:]]:
    g = np.random.default_rng(SEED); st = starts[g.integers(0, len(starts), (P, nb))]
    iiX = (st[:, :, None] + np.arange(BLK)[None, None, :]).reshape(P, -1)[:, :T]
    assert not excl[iiX].any()
    cX = ov.Ctx(X, F, iiX); cX.F = std.path_flags(X, iiX); cX._c = {}
    mX = DC._finish(cX, X); mX0 = dict(mX); mX0['rb'] = mX['rb'] - EX
    log('seed', SEED, 'world built')
    r = {}
    for nm, cfg in CFG.items():
        r[nm] = dict(X=sm(run_any(cfg, mX), mX), X0=sm(run_any(cfg, mX0), mX0))
    r['refs'] = RG.refs(mX)
    if SEED == 7:
        for nm, cfg in CFG.items():
            for w in ('X', 'X0'):
                for k in ('cagr', 'mdd_p10'):
                    assert abs(r[nm][w][k] - D3['configs'][cfg['id']][w][k]) < 1e-9, (nm, w, k, r[nm][w][k], D3['configs'][cfg['id']][w][k])
        for k in ('v1_locked_cash0', 'hold1x_QQQ', 'hold3x_TQQQ'):
            assert abs(r['refs'][k]['cagr'] - D3['refs']['X'][k]['cagr']) < 1e-9, k
        log('seed 7 parity with df3.json OK')
    RES['seeds'][str(SEED)] = r
    log('seed', SEED, {k: (round(v['X']['cagr'], 4), round(v['X']['mdd_p10'], 4)) for k, v in r.items() if k != 'refs'},
        {k: (round(v['cagr'], 4), round(v['mdd_p10'], 4)) for k, v in r['refs'].items()})
    json.dump(RES, open(OUTD + 'stress_b_%s.json' % '_'.join(sys.argv[1:]), 'w'), indent=1)
    del cX, mX, mX0
log('saved')
