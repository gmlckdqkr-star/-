"""DF3 horizons (user 06:59Z "비교는 5년 10년 20년"): the same 500 paths of both worlds (full = dev250_path, X = extreme-crash-free,
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
PICKS = {'T25': G['v1|s0.1|L1.0|K1|RB']['cfg'], 'T40': G['v1|s0.3|L1.0|K2|RB']['cfg'], 'W40': G['DF2|M0|b3|v1|s0.3|L1.0|K2|RB']['cfg'],
         'P50': dict(id='DF3|N3|M2|v1|s0.2|L1.0|K0|RB', fam='df3', M='M2', k='v1', sig=0.2, Lmax=1.0, knee='K0', roff='RB'),
         'S50': G['static|QQQ50|bond']['cfg'], 'S70': G['static|QQQ70|bond']['cfg']}
def run_any(cfg, m, **extra):
    if cfg.get('fam') == 'df3':
        L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']]); kw.update(vmode=2); kw.update(extra)
        return dfe.run(m, L, roff=RG.ROFF[cfg['roff']], **kw)[0]
    if cfg.get('fam') == 'df2': return R2.run_cfg(cfg, m, **extra)
    return RG.run_cfg(cfg, m, **extra)
def st_(cg, md):
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), p90=float(np.percentile(cg, 90)), p_loss=float(np.mean(cg < 0)),
                mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
def cut(c, Th):
    k = ov.Ctx(X, F, c.ii[:, :Th]); k.F = {a_: v[:, :Th] for a_, v in c.F.items()}; k._c = {}; return k

# ---- v2 engine (avgfix/v002_full.py)
sys.path.insert(0, '/mnt/project-files/research/diversifier/code'); sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
import ii, el, sl
el.CSPR = 10.0
jv = ii.SID.index('VALPROF4_L1'); jc = ii.SID.index('CAPE_L3')
def v2run(bn, w):
    S, SO = ii.arrays(bn); TQ, DEP, CU, IDL = ii._REFIN[bn]
    if w == (0, 0): Sa = np.zeros(S.shape[:2] + (1,), S.dtype); SOa = np.zeros_like(Sa); wa = np.zeros(1)
    else:
        v = S[:, :, jv].astype(np.float64) - 0.006 / 252; c = S[:, :, jc].astype(np.float64)
        Sa = np.ascontiguousarray(np.stack([v, c], 2).astype(S.dtype)); SOa = np.ascontiguousarray(np.stack([SO[:, :, jv], SO[:, :, jc]], 2)); wa = np.array(w, float)
    fin, E = el._comb(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Sa, SOa,
                      float(1 - wa.sum()), np.ascontiguousarray(wa), 0, 0.003, ii._PP['tax'], ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)
    y = E.shape[1] / 252; cg = np.maximum(fin, 1e-9) ** (1 / y) - 1; md = (E / np.maximum.accumulate(E, 1) - 1).min(1)
    return st_(cg, md)
Ssrc = sl.src(); dts = pd.DatetimeIndex(Ssrc['dates']); w_ = (dts >= pd.Timestamp('1986-01-03')) & (dts <= END)
EXV = float(np.mean(Ssrc['B10'][w_] - Ssrc['rf'][w_])); B10o = Ssrc['B10'].copy()

OUT = {}
CT = std.contexts()
for wname, c0 in (('P', cP), ('X', cX)):
    for h in (5, 10, 20, 30):
        Th = ov.WARM + h * 252; c = cut(c0, Th); m = DC._finish(c, X); m0 = dict(m); m0['rb'] = m['rb'] - EX; T = m['r'].shape[1]
        r = {}
        for nm, cfg in PICKS.items():
            r[nm] = st_(*dfe.stats(run_any(cfg, m), T)); r[nm + '_bx0'] = st_(*dfe.stats(run_any(cfg, m0), T))
        B, bfn, bp, fs = std.s085(c); cg, E = std.engine(c, B, bfn, bp, fs, cspr=10.0)
        r['v1'] = st_(cg, (E / np.maximum.accumulate(E, axis=1) - 1).min(axis=1))
        for nm, Lx in (('QQQ', 1.0), ('TQQQ', 3.0)): r[nm] = st_(*dfe.stats(dfe.run(m, np.full(m['r'].shape, Lx))[0], T))
        bn = '%s_h%d' % ('dev250_path' if wname == 'P' else 'dev250x_path', h); CT[bn] = c
        ii._REFIN[bn] = el.ref_inputs(el.ctx(bn, cspr=10.0))
        r['v1_el'] = v2run(bn, (0, 0)); r['v2'] = v2run(bn, (.15, .10)); ii._ARR.clear()
        Ssrc['B10'] = B10o - EXV; r['v2_bx0'] = v2run(bn, (.15, .10)); ii._ARR.clear(); Ssrc['B10'] = B10o
        OUT['%s%d' % (wname, h)] = r
        log(wname, h, ' '.join('%s %.1f/%.0f' % (k, v['cagr'] * 100, v['mdd_p10'] * 100) for k, v in r.items() if not k.endswith('_bx0')))
# parity with df3.json (30y) and with avgfix v002_full (10y full world)
C3 = D3['configs']
for nm, cid in (('T25', 'v1|s0.1|L1.0|K1|RB'), ('W40', 'DF2|M0|b3|v1|s0.3|L1.0|K2|RB'), ('S70', 'static|QQQ70|bond')):
    for w in ('P', 'X'): assert abs(OUT[w + '30'][nm]['cagr'] - C3[cid][w]['cagr']) < 1e-9, (nm, w)
for w in ('P', 'X'):
    assert abs(OUT[w + '30']['v1']['cagr'] - D3['refs'][w]['v1_locked_cash0']['cagr']) < 1e-9
    assert abs(OUT[w + '30']['QQQ']['cagr'] - D3['refs'][w]['hold1x_QQQ']['cagr']) < 1e-9
    assert abs(OUT[w + '30']['v2']['cagr'] - D3['v2']['dev250_path' if w == 'P' else 'dev250x_path']['v2']['cagr']) < 1e-9
V0 = json.load(open('/mnt/project-files/research/avgfix/results/v002_full.json'))['dev250_path_10y']
PAR10 = dict(v1_el=(OUT['P10']['v1_el']['cagr'], V0['v1']['p50']), v2=(OUT['P10']['v2']['cagr'], V0['V002']['p50']), v1_locked=OUT['P10']['v1']['cagr'])
log('parity 10y', PAR10)
json.dump(dict(note='horizon cuts of the same paths; after-tax incl. liquidation tax at the horizon; <=2014 data', parity10=PAR10, res=OUT),
          open(RES + 'df3_horizons.json', 'w'), indent=1)
log('saved')
