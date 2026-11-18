"""verify4 / refute: independent attempts to break the DF4 claims about v1|s0.3|L1.5|K0|RC.
<=2014 data only (every market builder asserts index max <= 2014-12-31). Medians / percentiles only, no means across paths.
Run with cwd outside /mnt/project-files/research (pandas shadowing), NUMBA_CACHE_DIR=/home/claude/nbcache_verify4."""
import os, sys, json, time
os.environ['NUMBA_CACHE_DIR'] = '/home/claude/nbcache_verify4'
import numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, df4cfg
from dfctx import std
import ov, jp, iv
W = dfe.WARM; END = pd.Timestamp('2014-12-31')
RES = '/mnt/project-files/research/df1/results/'
OUTP = sys.argv[1] if len(sys.argv) > 1 else '/tmp/v4_refute/refute_numbers.json'
t0 = time.time()
def log(*a): print('[%5.0fs]' % (time.time() - t0), *a, flush=True)
D4 = json.load(open(RES + 'df4.json')); C = D4['configs']; REF = D4['refs']
H4 = json.load(open(RES + 'df4_horizons.json'))['res']
RCID = 'v1|s0.3|L1.5|K0|RC'; RC = df4cfg.cfg_of(RCID)
OUT = dict(parity={}, stress={}, tax={}, cash={}, paired={}, lookahead={}, alarm={}, xworld={}, gates={}, abroad={})

def runQ(m, **kw): return dfe.run(m, np.full(m['r'].shape, 1.0), **kw)[0]
def runC(cfg, m, **kw): return df4cfg.run_any(cfg, m, **kw)
def runL(m, L, **kw): return dfe.run(m, L, **kw)[0]
def arr(o, m): return dfe.stats(o, m['r'].shape[1])
def st(o, m):
    cg, md = arr(o, m)
    if len(cg) == 1: return dict(cagr=float(cg[0]), mdd=float(md[0]))
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mdd=float(np.median(md)), mdd_p10=float(np.percentile(md, 10)),
                p_loss=float(np.mean(cg < 0)))
def sl(m, Th):
    k = dict(m)
    for a in ('r', 'rf', 'rb', 'cpn', 'idxup', 'bondup', 'st_v1', 'st_al', 'vol20'): k[a] = m[a][:, :Th]
    return k

BASES = ['dev250_path', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85', 'real_spx_29_54', 'real_spx_29_54_B', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP']
MK = {}
# ---------------------------------------------------------------- 1. parity with df4.json / grid refs
for bn in BASES:
    m = DC.market(bn); MK[bn] = m
    if bn != 'dev250_path': assert m['X_index'].max() <= END
    r = st(runC(RC, m), m); q = st(runQ(m), m)
    key = 'P' if bn == 'dev250_path' else bn
    d = dict(rc=r, qqq=q, eval_from=str(m['X_index'][m['ctx'].ii[0, W]].date()) if bn != 'dev250_path' else '1986-2014 pool',
             eval_to=str(m['X_index'][m['ctx'].ii[0, -1]].date()) if bn != 'dev250_path' else '')
    if key in C[RCID]:
        d['rc_stored'] = C[RCID][key]; d['rc_diff'] = r['cagr'] - C[RCID][key]['cagr']
    if bn in REF:
        d['qqq_stored'] = REF[bn]['hold1x_QQQ']['cagr']; d['qqq_diff'] = q['cagr'] - REF[bn]['hold1x_QQQ']['cagr']
    OUT['parity'][bn] = d
    log('parity', bn, d['eval_from'], d['eval_to'], 'RC %.4f/%.4f' % (r['cagr'], r['mdd']), 'Q %.4f/%.4f' % (q['cagr'], q['mdd']),
        'dRC %.1e' % d.get('rc_diff', np.nan), 'dQ %.1e' % d.get('qqq_diff', np.nan))
mp = MK['dev250_path']

# ---------------------------------------------------------------- 2. cost / delay stress, path + single-path US bases
STRESS = {'base': {}, 'cost0.15': dict(cost=0.0015), 'cost0.45': dict(cost=0.0045), 'cost0.6': dict(cost=0.006), 'cost0.9': dict(cost=0.009),
          'delay1': dict(delay=1), 'delay3': dict(delay=3), 'delay4': dict(delay=4), 'delay5': dict(delay=5), 'cost0.6_delay4': dict(cost=0.006, delay=4)}
for bn in ('dev250_path', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85', 'real_spx_29_54'):
    m = MK[bn]; OUT['stress'][bn] = {}
    for nm, kw in STRESS.items():
        OUT['stress'][bn][nm] = dict(rc=st(runC(RC, m, **kw), m), qqq=st(runQ(m, **kw), m))
    log('stress', bn, ' '.join('%s %.2f/%.2f' % (nm, v['rc']['cagr'] * 100, v['qqq']['cagr'] * 100) for nm, v in OUT['stress'][bn].items()))

# ---------------------------------------------------------------- 3. tax deduction / account size (D is in units of the starting capital)
TAX = {'D0.25_std': {}, 'D0.10': dict(D=0.10), 'D0.025': dict(D=0.025), 'D0': dict(D=0.0), 'D0.025_noharvest': dict(D=0.025, harvest=0),
       'pretax': dict(tax=0.0)}
for bn in ('dev250_path', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_29_54'):
    m = MK[bn]; OUT['tax'][bn] = {}
    for nm, kw in TAX.items():
        OUT['tax'][bn][nm] = dict(rc=st(runC(RC, m, **kw), m), qqq=st(runQ(m, **kw), m))
    log('tax', bn, ' '.join('%s %.2f/%.2f' % (nm, v['rc']['cagr'] * 100, v['qqq']['cagr'] * 100) for nm, v in OUT['tax'][bn].items()))

# ---------------------------------------------------------------- 4. cash interest (cspr=0: cash earns rf, taxed 15.4%)
for bn in ('dev250_path', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_29_54', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP'):
    m = MK[bn]; OUT['cash'][bn] = dict(rc_cash0=st(runC(RC, m), m), rc_cash_rf=st(runC(RC, m, cspr=0.0), m))
log('cash', {bn: (round(v['rc_cash0']['cagr'] * 100, 2), round(v['rc_cash_rf']['cagr'] * 100, 2)) for bn, v in OUT['cash'].items()})

# ---------------------------------------------------------------- 5. paired per-path RC vs QQQ, 5/10/20/30y (slice = cut, valid if causal; checked vs df4_horizons)
for h in (5, 10, 20, 30):
    Th = W + h * 252; m = sl(mp, Th) if h < 30 else mp
    cr, mr = arr(runC(RC, m), m); cq, mq = arr(runQ(m), m)
    d = dict(rc_med=float(np.median(cr)), q_med=float(np.median(cq)), rc_mdd_p10=float(np.percentile(mr, 10)), q_mdd_p10=float(np.percentile(mq, 10)),
             rc_ploss=float(np.mean(cr < 0)), q_ploss=float(np.mean(cq < 0)),
             win_cagr=float(np.mean(cr > cq)), win_mdd=float(np.mean(mr > mq)), win_both=float(np.mean((cr > cq) & (mr > mq))),
             lose_both=float(np.mean((cr < cq) & (mr < mq))),
             dcagr_med=float(np.median(cr - cq)), dcagr_p10=float(np.percentile(cr - cq, 10)), dcagr_p90=float(np.percentile(cr - cq, 90)),
             dmdd_med=float(np.median(mr - mq)), dmdd_p10=float(np.percentile(mr - mq, 10)))
    hk = 'P%d' % h
    d['parity_rc'] = d['rc_med'] - H4[hk]['answer']['cagr']; d['parity_q'] = d['q_med'] - H4[hk]['QQQ']['cagr']
    d['parity_rc_mddp10'] = d['rc_mdd_p10'] - H4[hk]['answer']['mdd_p10']; d['parity_q_mddp10'] = d['q_mdd_p10'] - H4[hk]['QQQ']['mdd_p10']
    OUT['paired']['P%d' % h] = d
    log('paired', h, {k: round(v, 4) for k, v in d.items()})

# ---------------------------------------------------------------- 6. look-ahead: truncated history must reproduce signals / target / equity before the cut
R_, M_ = jp.calendar('1984-01-03', '2014-12-31'); XN = jp.mkX(R_, M_, 'NDX'); assert XN.index.max() <= END
mN = MK['real_ndx_86_14']; i0 = int(mN['ctx'].ii[0, 0]); LN = DC.target(mN, 'v1', 0.3, 1.5); _, EN = dfe.run(mN, LN, recon=True)
for cutd in ('1987-10-30', '2000-03-31', '2002-10-31', '2008-09-30', '2011-08-31'):
    k = int(XN.index.searchsorted(pd.Timestamp(cutd))); Xc = XN.iloc[:k].copy()
    c = ov.Ctx(Xc, ov.flags_hist(Xc), np.arange(i0, k)[None, :]); mc = DC._finish(c, Xc); n = k - i0
    Lc = DC.target(mc, 'v1', 0.3, 1.5); _, Ec = dfe.run(mc, Lc, recon=True)
    eq = lambda a, b: bool(np.array_equal(np.nan_to_num(a, nan=-9), np.nan_to_num(b, nan=-9)))
    d = dict(n_days=n, st_v1_equal=eq(mc['st_v1'], mN['st_v1'][:, :n]), vol20_equal=eq(mc['vol20'], mN['vol20'][:, :n]),
             target_equal=eq(Lc, LN[:, :n]), equity_maxabsdiff=float(np.max(np.abs(Ec[0, :n - W] - EN[0, :n - W]))))
    OUT['lookahead'][cutd] = d; log('lookahead', cutd, d)

# ---------------------------------------------------------------- 7. how much of the edge is the (NDX 1986-2014 designed) alarm
ALW = df4cfg.cfg_of('always|s0.3|L1.5|K0|RC')
def pure_vt(m): L = np.minimum(1.5, 0.3 / np.maximum(m['vol20'], 1e-9)); return np.where(np.isnan(L), 0.0, L)
for bn in BASES:
    m = MK[bn]
    OUT['alarm'][bn] = dict(rc=OUT['parity'][bn]['rc'], always_trend=st(runC(ALW, m), m), pure_voltarget=st(runL(m, pure_vt(m)), m),
                            qqq=OUT['parity'][bn]['qqq'])
    a = OUT['alarm'][bn]; log('alarm', bn, ' '.join('%s %.2f/%.1f' % (k, v['cagr'] * 100, v['mdd'] * 100) for k, v in a.items()))
# exposure profile of RC on the path and real NDX
for bn in ('dev250_path', 'real_ndx_86_14'):
    L = DC.target(MK[bn], 'v1', 0.3, 1.5)[:, W:]
    OUT['alarm'][bn]['exposure'] = dict(med_share_L0=float(np.median(np.mean(L == 0, axis=1))), med_share_Lge1=float(np.median(np.mean(L >= 1, axis=1))),
                                        med_share_Lmax=float(np.median(np.mean(L >= 1.5 - 1e-12, axis=1))), med_mean_L=float(np.median(np.mean(L, axis=1))))
    log('exposure', bn, OUT['alarm'][bn]['exposure'])

# ---------------------------------------------------------------- 8. X world (DF3 construction, copied from df4h.py) paired 30y
D3 = json.load(open(RES + 'df3.json'))
a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= END
lv = np.cumprod(1 + X['r'].fillna(0).values); Dd = X.index; n = len(X); BLK = 250
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
g = np.random.default_rng(7); stt = starts[g.integers(0, len(starts), (P, nb))]
iiX = (stt[:, :, None] + np.arange(BLK)[None, None, :]).reshape(P, -1)[:, :T30]
cX = ov.Ctx(X, ov.flags_hist(X), iiX); cX.F = std.path_flags(X, iiX); cX._c = {}; mX = DC._finish(cX, X)
for h in (5, 10, 20, 30):
    m = sl(mX, W + h * 252) if h < 30 else mX
    cr, mr = arr(runC(RC, m), m); cq, mq = arr(runQ(m), m)
    d = dict(rc_med=float(np.median(cr)), q_med=float(np.median(cq)), rc_mdd_med=float(np.median(mr)), q_mdd_med=float(np.median(mq)),
             rc_mdd_p10=float(np.percentile(mr, 10)), q_mdd_p10=float(np.percentile(mq, 10)),
             win_cagr=float(np.mean(cr > cq)), win_mdd=float(np.mean(mr > mq)), win_both=float(np.mean((cr > cq) & (mr > mq))))
    hk = 'X%d' % h; d['parity_rc'] = d['rc_med'] - H4[hk]['answer']['cagr']; d['parity_q'] = d['q_med'] - H4[hk]['QQQ']['cagr']
    OUT['xworld'][hk] = d; log('xworld', hk, {k: round(v, 4) for k, v in d.items()})

# ---------------------------------------------------------------- 9. gate bookkeeping from df4.json (counts, neighbours, rank)
GK = ('R1', 'R2', 'R3', 'V1', 'V2', 'E1', 'E2', 'E3'); USK = ('R1', 'R2', 'V1', 'V2', 'E1', 'E2', 'E3')
OUT['gates']['n_all_pass_R1toE3'] = sum(all(C[i]['g'][k] for k in GK) for i in C)
OUT['gates']['us_pass'] = sorted(i for i in C if all(C[i]['g'][k] for k in USK))
OUT['gates']['r3_pass_n'] = sum(C[i]['g']['R3'] for i in C)
OUT['gates']['r3_pass_us_fail_counts'] = {k: int(sum((not C[i]['g'][k]) for i in C if C[i]['g']['R3'])) for k in USK}
OUT['gates']['r3_pass_min_us_fails'] = int(min(sum(not C[i]['g'][k] for k in USK) for i in C if C[i]['g']['R3']))
OUT['gates']['rank_P0_rc'] = int(1 + sum(C[i]['P0']['cagr'] > C[RCID]['P0']['cagr'] for i in C))
OUT['gates']['n_beat_qqq_spx55_cagr'] = int(sum(C[i]['real_spx_55_85_bx0']['cagr'] > REF['real_spx_55_85']['hold1x_QQQ']['cagr'] for i in C))
NB = {}
for ro in ('RC', 'RB', 'RT', 'RBT'):
    for nid in ('v1|s0.2|L1.5|K0|' + ro, 'v1|s0.3|L1.0|K0|' + ro, 'v1|s0.3|L2.0|K0|' + ro, 'v1|s0.3|L1.5|K1|' + ro, 'v1|s0.3|L1.5|K2|' + ro,
                'always|s0.3|L1.5|K0|' + ro, 'DF3|N1|M0|v1|s0.4|L1.5|K0|' + ro):
        if nid in C: NB[nid] = dict(us_fails=[k for k in USK if not C[nid]['g'][k]], P0=C[nid]['P0']['cagr'], R3n=C[nid]['g']['R3n'])
OUT['gates']['neighbours'] = NB
log('gates', json.dumps({k: v for k, v in OUT['gates'].items() if k != 'neighbours'}))
for k, v in NB.items(): log('  nb', k, v)

# ---------------------------------------------------------------- 10. abroad / out-of-alarm-sample bases: RC minus local hold
for bn in ('real_spx_55_85', 'real_spx_70_85', 'real_spx_29_54', 'real_spx_29_54_B', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP'):
    r = OUT['parity'][bn]['rc']; q = OUT['parity'][bn]['qqq']
    OUT['abroad'][bn] = dict(d_cagr=r['cagr'] - q['cagr'], d_mdd=r['mdd'] - q['mdd'], win_cagr=r['cagr'] > q['cagr'], win_mdd=r['mdd'] > q['mdd'])
log('abroad', {k: (round(v['d_cagr'] * 100, 2), round(v['d_mdd'] * 100, 1)) for k, v in OUT['abroad'].items()})
json.dump(OUT, open(OUTP, 'w'), indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o))
log('saved', OUTP)
