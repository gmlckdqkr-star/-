"""DF3 (PRECOMMIT_DF3.md sha d6bc3cf7): extreme-crash-free world X + 244 new configs + selections S1/S2 + v2 (V002).
<=2014 development data only (every input calendar ends 2014-12-31). Writes results/df3.json."""
import os, sys, json, time, itertools, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
from dfctx import std
jp, ov, iv = std.jp, std.ov, std.iv
RES = '/mnt/project-files/research/df1/results/'
EX = 1.3988294390226633e-4          # source-period mean (rb - rf) per day (select_df2_fixed.json, audit F1)
END = pd.Timestamp('2014-12-31'); BLK = 250; YRS = 30
t0 = time.time()
def log(*a): print('[%5.0fs]' % (time.time() - t0), *a, flush=True)

# ---------------------------------------------------------------- 1. episodes and the X world (PRECOMMIT s1-2)
a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= END
lv = np.cumprod(1 + X['r'].fillna(0).values); D = X.index; n = len(X)
def pos(d): return int(D.searchsorted(pd.Timestamp(d)))
def amax(x, y): i, j = pos(x), pos(y); return i + int(np.argmax(lv[i:j]))
def amin(x, y): i, j = pos(x), pos(y); return i + int(np.argmin(lv[i:j]))
tr1 = amin('1987-10-01', '1988-01-01'); pk1 = pos('1987-01-01') + int(np.argmax(lv[pos('1987-01-01'):tr1 + 1]))
pk2 = amax('2000-01-01', '2001-01-01'); tr2 = pk2 + int(np.argmin(lv[pk2:pos('2004-01-01')]))
pk3 = amax('2007-01-01', '2008-07-01'); tr3 = amin('2008-07-01', '2009-07-01')
EPI = []
excl = np.zeros(n, bool)
for nm, p_, t_ in (('E1_black_monday', pk1, tr1), ('E2_dotcom', pk2, tr2), ('E3_gfc', pk3, tr3)):
    e = min(t_ + BLK, n - 1); excl[p_:e + 1] = True
    EPI.append(dict(name=nm, peak=str(D[p_].date()), trough=str(D[t_].date()), excl_end=str(D[e].date()), depth=float(lv[t_] / lv[p_] - 1)))
    log(EPI[-1])
starts = np.array([s for s in range(1, n - BLK) if not excl[s:s + BLK].any()])
T = ov.WARM + YRS * 252; nb = T // BLK + 1
g = np.random.default_rng(7); st = starts[g.integers(0, len(starts), (P, nb))]
iiX = (st[:, :, None] + np.arange(BLK)[None, None, :]).reshape(P, -1)[:, :T]
assert not excl[iiX].any()
segs = []; i = 0
while i < n:
    if not excl[i]:
        j = i
        while j < n and not excl[j]: j += 1
        segs.append((str(D[i].date()), str(D[j - 1].date()), j - i)); i = j
    else: i += 1
log('kept segments', segs, 'allowed starts', len(starts), 'kept days', int((~excl).sum()), 'of', n)
F = ov.flags_hist(X); cX = ov.Ctx(X, F, iiX); cX.F = std.path_flags(X, iiX); cX._c = {}
CT = std.contexts(); CT['dev250x_path'] = cX
mX = DC._finish(cX, X); DC._M['dev250x_path'] = mX
log('X world built')

# ---------------------------------------------------------------- 2. configs
G1 = json.load(open(RES + 'grid.json')); G2 = json.load(open(RES + 'grid_df2.json'))
OLD = dict(G1['configs']); OLD.update(G2['configs'])
def new_configs():
    C = []
    for s, Mm, L, kn, ro, k in itertools.product((0.40, 0.50), ('M0', 'M2'), (1.5, 2.0, 3.0), ('K0', 'K1', 'K2'), ('RB', 'RBT'), RG.KS):
        C.append(dict(id='DF3|N1|%s|%s|s%s|L%s|%s|%s' % (Mm, k, s, L, kn, ro), fam='df3', M=Mm, k=k, sig=s, Lmax=L, knee=kn, roff=ro))
    for L, kn, ro, k in itertools.product((1.5, 2.0, 3.0), ('K0', 'K1', 'K2'), ('RB', 'RBT'), RG.KS):
        C.append(dict(id='DF3|N2|M2|%s|snone|L%s|%s|%s' % (k, L, kn, ro), fam='df3', M='M2', k=k, sig=None, Lmax=L, knee=kn, roff=ro))
    for s, L, ro, k in itertools.product((0.10, 0.15, 0.20, 0.30), (1.0, 1.5, 2.0, 3.0), ('RB', 'RBT'), RG.KS):
        C.append(dict(id='DF3|N3|M2|%s|s%s|L%s|K0|%s' % (k, s, L, ro), fam='df3', M='M2', k=k, sig=s, Lmax=L, knee='K0', roff=ro))
    return C
NEW = new_configs(); assert len(NEW) == 244, len(NEW)
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
    if cg.shape[0] == 1: return dict(cagr=float(cg[0]), mdd=float(md[0]))
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))

mp = DC.market('dev250_path'); mN = DC.market('real_ndx_86_14'); mS = DC.market('real_spx_29_54')
mp0 = dict(mp); mp0['rb'] = mp['rb'] - EX
mX0 = dict(mX); mX0['rb'] = mX['rb'] - EX
ALL = [v['cfg'] for v in OLD.values()] + NEW
OUT = {}
for i, cfg in enumerate(ALL):
    r = {}
    if cfg.get('fam') == 'df3':
        r['P'] = sm(run_any(cfg, mp), mp); r['N'] = sm(run_any(cfg, mN), mN); r['S'] = sm(run_any(cfg, mS), mS)
    else:
        o = OLD[cfg['id']]
        r['P'] = {k: o['dev250_path'][k] for k in ('cagr', 'p10', 'mdd', 'mdd_p10')}
        r['N'] = {k: o['real_ndx_86_14'][k] for k in ('cagr', 'mdd')}; r['S'] = {k: o['real_spx_29_54'][k] for k in ('cagr', 'mdd')}
    r['P0'] = sm(run_any(cfg, mp0), mp0); r['X'] = sm(run_any(cfg, mX), mX); r['X0'] = sm(run_any(cfg, mX0), mX0)
    r['WD'] = min(r['P']['mdd_p10'], r['N']['mdd'], r['S']['mdd'])
    OUT[cfg['id']] = r
    if i % 200 == 0: log('config', i, '/', len(ALL))
log('configs done', len(OUT))

# parity: recompute two stored configs on dev250_path
PAR = {}
for cid in ('v1|s0.1|L1.0|K1|RB', 'v1|s0.3|L1.0|K2|RB', 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB'):
    v = sm(run_any(OLD[cid]['cfg'], mp), mp)['cagr']; PAR[cid] = (v, OLD[cid]['dev250_path']['cagr'])
    assert abs(v - OLD[cid]['dev250_path']['cagr']) < 1e-9, (cid, v)
# references (v1 locked engine cash 0, QQQ, TQQQ) on both worlds
REF = dict(P=RG.refs(mp), X=RG.refs(mX))
assert abs(REF['P']['v1_locked_cash0']['cagr'] - G1['refs']['dev250_path']['v1_locked_cash0']['cagr']) < 1e-9
assert abs(REF['P']['hold1x_QQQ']['cagr'] - G1['refs']['dev250_path']['hold1x_QQQ']['cagr']) < 1e-9
log('refs', {w: {k: round(v['cagr'], 4) for k, v in REF[w].items()} for w in REF})

# ---------------------------------------------------------------- 3. v2 = V002 (avgfix/v002_full.py engine, cash 0)
sys.path.insert(0, '/mnt/project-files/research/diversifier/code'); sys.path.insert(0, '/mnt/project-files/research/c3_create/lanes/I_INTEGRATE/code')
import ii, el, sl
el.CSPR = 10.0
jv = ii.SID.index('VALPROF4_L1'); jc = ii.SID.index('CAPE_L3')
def v2run(bn, w):
    S, SO = ii.arrays(bn); TQ, DEP, CU, IDL = ii._REFIN[bn]
    if w == (0, 0):
        Sa = np.zeros(S.shape[:2] + (1,), S.dtype); SOa = np.zeros_like(Sa); wa = np.zeros(1)
    else:
        v = S[:, :, jv].astype(np.float64) - 0.006 / 252; c = S[:, :, jc].astype(np.float64)
        Sa = np.ascontiguousarray(np.stack([v, c], 2).astype(S.dtype)); SOa = np.ascontiguousarray(np.stack([SO[:, :, jv], SO[:, :, jc]], 2)); wa = np.array(w, float)
    fin, E = el._comb(np.ascontiguousarray(TQ), np.ascontiguousarray(DEP), np.ascontiguousarray(CU), np.ascontiguousarray(IDL), Sa, SOa,
                      float(1 - wa.sum()), np.ascontiguousarray(wa), 0, 0.003, ii._PP['tax'], ii._D, int(ii._PP['harvest']), ii._PP['hthr'], 21, 0.05, 0.25)
    y = E.shape[1] / 252; cg = np.maximum(fin, 1e-9) ** (1 / y) - 1; md = (E / np.maximum.accumulate(E, 1) - 1).min(1)
    if len(cg) == 1: return dict(cagr=float(cg[0]), mdd=float(md[0]))
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)))
V2 = {}
for bn in ('dev250_path', 'dev250x_path', 'real_ndx_86_14'):
    ii._REFIN[bn] = el.ref_inputs(el.ctx(bn, cspr=10.0))
    V2[bn] = dict(v1=v2run(bn, (0, 0)), v2=v2run(bn, (.15, .10))); ii._ARR.clear(); log('v2', bn, V2[bn])
assert abs(V2['dev250_path']['v1']['cagr'] - 0.15180945648761046) < 1e-6 and abs(V2['dev250_path']['v2']['cagr'] - 0.16800992112481816) < 1e-6
assert abs(V2['real_ndx_86_14']['v1']['cagr'] - 0.30526) < 0.002
# bond-neutral v2: remove the 1986-2014 mean (B10 - rf) from the sleeve source bond
Ssrc = sl.src(); dts = pd.DatetimeIndex(Ssrc['dates']); w_ = (dts >= pd.Timestamp('1986-01-03')) & (dts <= END)
EXV = float(np.mean(Ssrc['B10'][w_] - Ssrc['rf'][w_])); B10orig = Ssrc['B10'].copy(); Ssrc['B10'] = B10orig - EXV
for bn in ('dev250_path', 'dev250x_path'):
    V2[bn]['v2_bx0'] = v2run(bn, (.15, .10)); ii._ARR.clear(); log('v2 bx0', bn, V2[bn]['v2_bx0'])
Ssrc['B10'] = B10orig
log('v2 bond shift/day %.4e (%.2f%%/yr) vs DF %.4e' % (EXV, EXV * 252 * 100, EX))

# ---------------------------------------------------------------- 4. selections (PRECOMMIT s4)
def pick(cands, key, tie):
    if not cands: return None
    best = max(cands, key=key); top = [c for c in cands if key(best) - key(c) <= 0.0005]
    return max(top, key=tie)
SEL = dict(S1={}, S2={})
for th in (-0.25, -0.30, -0.40, -0.50, -0.60):
    c = [k for k, r in OUT.items() if r['WD'] >= th]
    k = pick(c, lambda k: OUT[k]['P0']['cagr'], lambda k: OUT[k]['N']['cagr']); SEL['S1']['%d' % (th * 100)] = dict(n_in=len(c), pick=k)
for th in (-0.25, -0.30, -0.40):
    c = [k for k, r in OUT.items() if r['X']['mdd_p10'] >= th]
    k = pick(c, lambda k: OUT[k]['X0']['cagr'], lambda k: OUT[k]['N']['cagr']); SEL['S2']['%d' % (th * 100)] = dict(n_in=len(c), pick=k)
log('SEL', json.dumps(SEL))
res = dict(precommit_sha='d6bc3cf75dd6b53b0a729a4a1097c0a1ea398f577af31d666bca9b530ab8c4c6', N_total=len(OUT), N_new=len(NEW), episodes=EPI, kept_segments=segs,
           allowed_starts=int(len(starts)), bond_shift_df=EX, bond_shift_v2=EXV, parity=PAR, refs=REF, v2=V2, sel=SEL, configs=OUT)
json.dump(res, open(RES + 'df3.json', 'w')); log('saved df3.json')
