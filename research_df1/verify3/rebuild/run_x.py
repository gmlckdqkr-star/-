import os, sys, json, time
os.environ.setdefault('NUMBA_CACHE_DIR','/home/claude/nbcache_std')
sys.path.insert(0,'/mnt/project-files/research/df1/code')
import numpy as np, pandas as pd
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
from dfctx import std
t0 = time.time()
iv = std.iv; ov = std.ov
a,b,P,blk,seed = iv.POOLS['dev250']
R,M = std.jp.calendar(a,b); X = std.jp.mkX(R,M,'NDX'); assert X.index.max() <= pd.Timestamp('2014-12-31')
ii = np.load('/tmp/vf_rebuild/ii_mine.npy')
T = ii.shape[1]

# (check) df3.py lines 16-34 construction, copied verbatim-in-logic, vs my ii
lv = np.cumprod(1 + X['r'].fillna(0).values); D = X.index; n = len(X); BLK = 250
def pos(d): return int(D.searchsorted(pd.Timestamp(d)))
def amax(x, y): i, j = pos(x), pos(y); return i + int(np.argmax(lv[i:j]))
def amin(x, y): i, j = pos(x), pos(y); return i + int(np.argmin(lv[i:j]))
tr1 = amin('1987-10-01', '1988-01-01'); pk1 = pos('1987-01-01') + int(np.argmax(lv[pos('1987-01-01'):tr1 + 1]))
pk2 = amax('2000-01-01', '2001-01-01'); tr2 = pk2 + int(np.argmin(lv[pk2:pos('2004-01-01')]))
tr2_text = amin('2000-01-01', '2004-01-01')
pk3 = amax('2007-01-01', '2008-07-01'); tr3 = amin('2008-07-01', '2009-07-01')
excl = np.zeros(n, bool)
for p_, t_ in ((pk1, tr1), (pk2, tr2), (pk3, tr3)): excl[p_:min(t_ + BLK, n - 1) + 1] = True
starts = np.array([s for s in range(1, n - BLK) if not excl[s:s + BLK].any()])
nb = (ov.WARM + 30 * 252) // BLK + 1
g = np.random.default_rng(7); st = starts[g.integers(0, len(starts), (P, nb))]
iiX = (st[:, :, None] + np.arange(BLK)[None, None, :]).reshape(P, -1)[:, :ov.WARM + 30*252]
chk = dict(df3_ii_equal_mine=bool(np.array_equal(iiX, ii)), tr2_code=int(tr2), tr2_text_rule=int(tr2_text), WARM=int(ov.WARM), P=int(P))
print('construction check', chk, flush=True)

# 3. market on my ii
F = ov.flags_hist(X); c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}
m = DC._finish(c, X)
print('market built %.0fs' % (time.time()-t0), m['r'].shape, flush=True)
chk['ctx_r_equals_X_r_ii'] = bool(np.allclose(np.nan_to_num(m['r']), np.nan_to_num(X['r'].values[ii])))

d3 = json.load(open('/mnt/project-files/research/df1/results/df3.json'))
g1 = json.load(open('/mnt/project-files/research/df1/results/grid.json')); g2 = json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))
IDS = ['v1|s0.1|L1.0|K1|RB', 'v1|s0.3|L1.0|K2|RB', 'DF2|M0|b3|v1|s0.3|L1.0|K2|RB', 'static|QQQ50|bond', 'static|QQQ70|bond']
rows = {}
for cid in IDS:
    cfg = (g1['configs'][cid] if cid in g1['configs'] else g2['configs'][cid])['cfg']
    o = R2.run_cfg(cfg, m) if cfg.get('fam') == 'df2' else RG.run_cfg(cfg, m)
    cg, md = dfe.stats(o, m['r'].shape[1])
    mine = dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
    ref = d3['configs'][cid]['X']
    rows[cid] = dict(mine=mine, df3=ref, diff={k: mine[k] - ref[k] for k in mine})
    print(cid, {k: round(v, 6) for k, v in mine.items()}, 'df3', {k: round(v, 6) for k, v in ref.items()}, flush=True)

rx = RG.refs(m)
refcmp = {}
for k in rx:
    refcmp[k] = {f: (rx[k][f], d3['refs']['X'][k].get(f)) for f in ('cagr', 'p10', 'mdd', 'mdd_p10') if f in rx[k]}
print('refs', json.dumps(refcmp), flush=True)

# bond excess note: mean(rb - rf) per day on the source (1986-01-03..2014-12-31) vs the X-world kept days, vs EX used by df3
src = (X['rb'] - X['rf']).values
w = (X.index >= pd.Timestamp('1986-01-03'))
keep = ~excl
bond = dict(EX_df3=1.3988294390226633e-4, src_all=float(np.nanmean(src[w])), src_kept=float(np.nanmean(src[w & keep])),
            path_X_median_of_path_means=float(np.median(np.nanmean((m['rb'] - m['rf'])[:, ov.WARM:], axis=1))))
print('bond excess', bond, flush=True)

# 4. engine-free sanity (plain numpy)
def plain(r):
    r = np.nan_to_num(np.asarray(r, float))[:, ov.WARM:]
    yrs = r.shape[1] / 252
    q = np.cumprod(1 + r - 0.002/252, axis=1); cg = q[:, -1] ** (1/yrs) - 1
    lvl = np.c_[np.ones(r.shape[0]), np.cumprod(1 + r, axis=1)]; md = (lvl / np.maximum.accumulate(lvl, axis=1) - 1).min(axis=1)
    return dict(pre_tax_cagr_med=float(np.median(cg)), pre_tax_cagr_p10=float(np.percentile(cg, 10)),
                idx_mdd_med=float(np.median(md)), idx_mdd_p10=float(np.percentile(md, 10)), yrs=yrs)
san = dict(X_mine=plain(X['r'].values[ii]), P_dev250=plain(std.contexts()['dev250_path'].r))
for wname, key in (('X_mine', 'X'), ('P_dev250', 'P')):
    q = d3['refs'][key]['hold1x_QQQ']
    san[wname].update(df3_aftertax_cagr_med=q['cagr'], df3_aftertax_cagr_p10=q['p10'], df3_mdd_med=q['mdd'], df3_mdd_p10=q['mdd_p10'],
                      gap_med=san[wname]['pre_tax_cagr_med'] - q['cagr'], gap_p10=san[wname]['pre_tax_cagr_p10'] - q['p10'])
print('sanity', json.dumps(san, indent=1), flush=True)
json.dump(dict(construction_check=chk, configs=rows, refs=refcmp, bond_excess=bond, sanity=san), open('/tmp/vf_rebuild/rebuild_results.json', 'w'), indent=1)
print('done %.0fs' % (time.time()-t0))
