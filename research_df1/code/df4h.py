"""DF4 horizons (copy of df3h.py with the DF4 picks): DF3 horizons (user 06:59Z "비교는 5년 10년 20년"): the same 500 paths of both worlds (full = dev250_path, X = extreme-crash-free,
PRECOMMIT_DF3 s2) cut at 5 / 10 / 20 / 30 years; after-tax incl. final liquidation tax at the horizon. <=2014 data only.
Rows: T25, T40, W40, P50, S50, S70, v1 (locked engine, cash 0), QQQ hold, TQQQ hold, v2 (V002, cash 0) + bond-neutral variants."""
import os, sys, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
from dfctx import std
jp, ov, iv = std.jp, std.ov, std.iv
RES = '/mnt/project-files/research/df1/results/'
EX = 1.3988294390226633e-4; END = pd.Timestamp('2014-12-31'); BLK = 250
t0 = time.time()
def log(*a): print('[%5.0fs]' % (time.time() - t0), *a, flush=True)
D3 = json.load(open(RES + 'df3.json'))

# ---- X world, identical construction to df3.py (checked below)
a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= END
lv = np.cumprod(1 + X['r'].fillna(0).values); Dd = X.index; n = len(X)
def pos(d): return int(Dd.searchsorted(pd.Timestamp(d)))
def amax(x, y): i, j = pos(x), pos(y); return i + int(np.argmax(lv[i:j]))
def amin(x, y): i, j = pos(x), pos(y); return i + int(np.argmin(lv[i:j]))
tr1 = amin('1987-10-01', '1988-01-01'); pk1 = pos('1987-01-01') + int(np.argmax(lv[pos('1987-01-01'):tr1 + 1]))
pk2 = amax('2000-01-01', '2001-01-01'); tr2 = pk2 + int(np.argmin(lv[pk2:pos('2004-01-01')]))
pk3 = amax('2007-01-01', '2008-07-01'); tr3 = amin('2008-07-01', '2009-07-01')
excl = np.zeros(n, bool)
for p_, t_ in ((pk1, tr1), (pk2, tr2), (pk3, tr3)): excl[p_:min(t_ + BLK, n - 1) + 1] = True
starts = np.array([s for s in range(1, n - BLK) if not excl[s:s + BLK].any()]); assert len(starts) == D3['allowed_starts']
T30 = ov.WARM + 30 * 252; nb = T30 // BLK + 1
g = np.random.default_rng(7); st = starts[g.integers(0, len(starts), (P, nb))]
iiX = (st[:, :, None] + np.arange(BLK)[None, None, :]).reshape(P, -1)[:, :T30]
F = ov.flags_hist(X)
cP = std.contexts()['dev250_path']
cX = ov.Ctx(X, F, iiX); cX.F = std.path_flags(X, iiX); cX._c = {}
log('worlds ready')

G = json.load(open(RES + 'grid.json'))['configs']; G.update(json.load(open(RES + 'grid_df2.json'))['configs'])
D4 = json.load(open(RES + 'df4.json')); SEL = json.load(open(RES + 'df4_us.json'))['sel']
import df4cfg
PICKS = {k: df4cfg.cfg_of(v) for k, v in SEL.items() if v}
run_any = df4cfg.run_any
def st_(cg, md):
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), p90=float(np.percentile(cg, 90)), p_loss=float(np.mean(cg < 0)),
                mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
def cut(c, Th):
    k = ov.Ctx(X, F, c.ii[:, :Th]); k.F = {a_: v[:, :Th] for a_, v in c.F.items()}; k._c = {}; return k

OUT = {}
CT = std.contexts()
for wname, c0 in (('P', cP), ('X', cX)):
    for h in (5, 10, 20, 30):
        Th = ov.WARM + h * 252; c = cut(c0, Th); m = DC._finish(c, X); m0 = dict(m); m0['rb'] = m['rb'] - EX; T = m['r'].shape[1]
        r = {}
        for nm, cfg in PICKS.items():
            r[nm] = st_(*dfe.stats(run_any(cfg, m), T)); r[nm + '_bx0'] = st_(*dfe.stats(run_any(cfg, m0), T))
        OUT['%s%d' % (wname, h)] = r
        log(wname, h, ' '.join('%s %.1f/%.0f' % (k, v['cagr'] * 100, v['mdd_p10'] * 100) for k, v in r.items() if not k.endswith('_bx0')))
# parity with df4.json / df3.json (30y)
for nm, cid in SEL.items():
    if nm not in PICKS: continue
    assert abs(OUT['P30'][nm]['cagr'] - D4['configs'][cid]['P']['cagr']) < 1e-9 and abs(OUT['P30'][nm + '_bx0']['cagr'] - D4['configs'][cid]['P0']['cagr']) < 1e-9
    assert abs(OUT['X30'][nm]['cagr'] - D4['configs'][cid]['X']['cagr']) < 1e-9 and abs(OUT['X30'][nm + '_bx0']['cagr'] - D4['configs'][cid]['X0']['cagr']) < 1e-9
H3 = json.load(open(RES + 'df3_horizons.json'))['res']
for k in OUT:
    for nm in ('QQQ', 'v1', 'v2', 'v2_bx0', 'TQQQ'): OUT[k][nm] = H3[k][nm]
json.dump(dict(note='DF4 picks cut at 5/10/20/30y; QQQ/v1/v2 rows copied from df3_horizons.json', sel=SEL, res=OUT), open(RES + 'df4_horizons.json', 'w'), indent=1)
log('saved')
