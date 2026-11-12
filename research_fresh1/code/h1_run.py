"""FRESH1 H1 'lever what leads' — runs exactly the sealed design (DESIGN_FRESH1.md + AMEND_A1_FRESH1.md).
All six variants and both benchmarks are reported. <=2014 only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/-/research_fresh1/code'); sys.path.insert(0, '/mnt/project-files/research/measure_std')
import h1_engine as H
from h1_engine import WARM, MS1, SEALED
import std

Z = np.load('/home/user/fresh1_data/french_le2014.npz', allow_pickle=True)
dates = pd.to_datetime(Z['dates'].astype(str)); n12 = list(Z['names12']); r12 = Z['r12']; mkt = Z['mkt']; rff = Z['rf']
assert dates.max() <= pd.Timestamp('2014-12-31')
S7 = ['BusEq', 'Enrgy', 'Hlth', 'Money', 'Utils', 'Shops', 'Manuf']
VARS = [(K, look) for look in ('12-1', '6') for K in (1, 2, 3)]; PRIMARY = (2, '12-1')
OUT = {}

# ---- price basis: remove each industry's monthly dividend return evenly over that month's days
months = Z['months']; div = Z['m12'] - Z['x12']
ym = (dates.year * 100 + dates.month).values
dmap = pd.DataFrame(div, index=months, columns=n12).reindex(ym).values
ndays = pd.Series(1, index=ym).groupby(level=0).transform('sum').values
r12px = r12 - np.nan_to_num(dmap) / ndays[:, None]


def month_end_dec(dt, lo):
    d = np.zeros(len(dt), bool); m = (dt.year * 100 + dt.month).values
    d[:-1] = m[1:] != m[:-1]; d[-1] = False
    d[:lo] = False; d[lo] = True
    return d


def every21(T):
    d = np.zeros(T, bool); d[WARM - 1::21] = True; return d


def run_set(R, RF, dec, terms, cols_for_rot, mkt_col, be_col):
    res = {}; curves = {}
    Rrot = R[:, cols_for_rot]
    for K, look in VARS:
        W = np.zeros_like(R); W[:, cols_for_rot] = H.signals(Rrot, K, look, dec)
        res['K%d_%s' % (K, look)], curves['K%d_%s' % (K, look)] = H.account(R, RF, W, dec, terms)
    res['B0_mkt'], curves['B0_mkt'] = H.account(R, RF, H.trend_only(R, dec, mkt_col), dec, terms)
    res['B1_buseq'], curves['B1_buseq'] = H.account(R, RF, H.trend_only(R, dec, be_col), dec, terms)
    return res, curves


def boot_p(d, block=250, n=2000, seed=11):
    g = np.random.default_rng(seed); L = len(d); nb = L // block + 1
    st = g.integers(0, L - block, (n, nb)); idx = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :L]
    m = d[idx].mean(axis=1)
    return float(np.mean(m > 0)), float(np.percentile(m, 10) * 252), float(d.mean() * 252)


# ---------------- 0. parity with the locked engine (one asset, always 3x, real NDX 1986-2014)
C = std.contexts()
c = C['real_ndx_86_14']; T = c.r.shape[1]
dec0 = np.zeros(T, bool); dec0[WARM - 1] = True
r, _ = H.account(c.r[0][:, None], c.rf[0], np.ones((T, 1)), dec0, MS1)
OUT['parity_3x_hold'] = dict(mine=r['cagr'], ms1=0.038712781616948355, diff=r['cagr'] - 0.038712781616948355)
print('parity', OUT['parity_3x_hold'], flush=True)
assert abs(OUT['parity_3x_hold']['diff']) < 1e-9

# ---------------- 1. phenomenon test on French total returns 1926-2014 (tradable set S7 + Mkt)
cols = [n12.index(x) for x in S7]
Rtr = np.c_[r12[:, cols], mkt]; Rpx_f = np.c_[r12px[:, cols], np.full(len(mkt), np.nan)]
rot = list(range(8)); MK = 7; BE = 0
ERAS = {'1927_54': (None, '1954-12-31'), '1955_85': ('1955-01-03', '1985-12-31'), '1986_14': ('1986-01-02', '2014-12-31'), 'full': (None, '2014-12-31')}
ph = {}
for basis, terms in (('sealed', SEALED), ('ms1', MS1)):
    ph[basis] = {}
    for en, (a, b) in ERAS.items():
        i0 = WARM if a is None else dates.searchsorted(pd.Timestamp(a)); i1 = dates.searchsorted(pd.Timestamp(b), side='right')
        sl = slice(i0 - WARM, i1); dt = dates[sl]; dec = month_end_dec(dt, WARM - 1)
        res, cur = run_set(Rtr[sl], rff[sl], dec, terms, rot, MK, BE)
        ph[basis][en] = {k: dict(cagr=v['cagr'], mdd=v['mdd'], ntr=v['ntr']) for k, v in res.items()}
        if en == 'full':
            for k in res:
                if k != 'B0_mkt':
                    d = np.diff(np.log(cur[k])) - np.diff(np.log(cur['B0_mkt']))
                    p, lo10, mean = boot_p(d); ph[basis][en][k].update(boot_p_gt0_vs_B0=p, boot_lo10_dlog=lo10, dlog_vs_B0=mean)
            # stress on the primary: delay +5, cost x2
            for nm, tt in (('delay7', dict(terms, delay=7)), ('cost2x', dict(terms, cost=2 * terms['cost']))):
                r2, _ = run_set(Rtr[sl], rff[sl], dec, tt, rot, MK, BE)
                ph[basis][en]['stress_' + nm] = {k: r2[k]['cagr'] for k in ('K2_12-1', 'B0_mkt', 'B1_buseq')}
    print(basis, json.dumps({e: {k: round(v['cagr'], 4) for k, v in ph[basis][e].items() if isinstance(v, dict) and 'cagr' in v} for e in ph[basis]}), flush=True)
OUT['phenomenon_TR_S7'] = ph

# diagnostics: all 12 industries + Mkt, and 49 industries + Mkt (primary variant only, sealed terms, total return)
diag = {}
for nm, RR in (('all12', np.c_[r12, mkt]), ('all49', np.c_[Z['r49'], mkt])):
    N = RR.shape[1]; diag[nm] = {}
    for en, (a, b) in ERAS.items():
        i0 = WARM if a is None else dates.searchsorted(pd.Timestamp(a)); i1 = dates.searchsorted(pd.Timestamp(b), side='right')
        sl = slice(i0 - WARM, i1); dec = month_end_dec(dates[sl], WARM - 1); R = RR[sl]
        o = {}
        for K in (1, 2, 3, 5):
            W = np.zeros_like(R); W[:, :N - 1] = H.signals(R[:, :N - 1], K, '12-1', dec)   # industries only
            o['K%d' % K] = H.account(R, rff[sl], W, dec, SEALED)[0]['cagr']
        o['B0_mkt'] = H.account(R, rff[sl], H.trend_only(R, dec, N - 1), dec, SEALED)[0]['cagr']
        diag[nm][en] = o
OUT['diagnostic_TR'] = diag
print('diag', json.dumps({k: {e: {a: round(b, 4) for a, b in v[e].items()} for e in v} for k, v in diag.items()}), flush=True)

# ---------------- 2. comparison with v1 on MS1 basis, price basis, same 500 simulated paths
import jp
a, b, P, blk, seed = std.iv.POOLS['dev250']
Rcal, Mcal = jp.calendar(a, b); cal = Rcal.index
cp = C['dev250_path']; ii = cp.ii
pos = pd.Index(dates).get_indexer(cal); assert (pos >= 0).mean() > 0.999, (pos < 0).sum()
Rpx_cal = np.where(pos[:, None] >= 0, r12px[np.maximum(pos, 0)][:, cols], 0.0)
Rall = np.c_[Rpx_cal, Rcal['SPX'].fillna(0.0).values]             # 7 industries price basis + S&P 500 price index
B, bfn, bp, fs = std.s085(cp); fv1, Ev1 = std.engine(cp, B, bfn, bp, fs)
Pn, Tn = ii.shape; dec = every21(Tn)
names = ['K%d_%s' % v for v in VARS] + ['B0_mkt', 'B1_buseq']
fin = {k: np.zeros(Pn) for k in names}; mdd = {k: np.zeros(Pn) for k in names}; fin_d7 = np.zeros(Pn)
for p in range(Pn):
    R = Rall[ii[p]].copy(); R[0] = 0.0; RF = cp.rf[p]
    res, _ = run_set(R, RF, dec, MS1, rot, MK, BE)
    for k in names: fin[k][p] = res[k]['cagr']; mdd[k][p] = res[k]['mdd']
    W = np.zeros_like(R); W[:, rot] = H.signals(R[:, rot], 2, '12-1', dec)
    fin_d7[p] = H.account(R, RF, W, dec, dict(MS1, delay=7))[0]['cagr']
    if p % 100 == 99: print('paths', p + 1, flush=True)
sim = {'v1': dict(median=float(np.median(fv1)), dd80=float(np.mean(std.ce.mdd(Ev1) <= -0.8)), p10=float(np.percentile(fv1, 10)))}
for k in names:
    d = fin[k] - fv1
    sim[k] = dict(median=float(np.median(fin[k])), p10=float(np.percentile(fin[k], 10)), dd80=float(np.mean(mdd[k] <= -0.8)),
                  d_vs_v1=float(np.median(d)), win_share_vs_v1=float(np.mean(d > 1e-5)))
sim['K2_12-1_delay7'] = dict(median=float(np.median(fin_d7)), d_vs_v1=float(np.median(fin_d7 - fv1)))
OUT['sim_ms1_basis_px'] = sim
print('sim', json.dumps({k: {a: round(b, 4) for a, b in v.items()} for k, v in sim.items()}), flush=True)

# real legs on MS1 basis, price basis (v1 values are the locked references)
real = {}; dlog = []
legs = {'real_ndx_86_14': ('1984-01-03', '2014-12-31'), 'real_spx_55_85': ('1928-01-03', '1985-12-31'), 'real_spx_70_85': ('1928-01-03', '1985-12-31')}
for leg, (ca, cb) in legs.items():
    c = C[leg]; Rc, Mc = jp.calendar(ca, cb); iix = c.ii[0]; dts = Rc.index[iix]
    pos = pd.Index(dates).get_indexer(dts); assert (pos >= 0).mean() > 0.999
    R = np.c_[np.where(pos[:, None] >= 0, r12px[np.maximum(pos, 0)][:, cols], 0.0), Rc['SPX'].fillna(0.0).values[iix]]; R[0] = 0.0
    dec = month_end_dec(dts, WARM - 1)
    res, cur = run_set(R, c.rf[0], dec, MS1, rot, MK, BE)
    Bv, bfn, bp, fs = std.s085(c); f1, E1 = std.engine(c, Bv, bfn, bp, fs)
    real[leg] = {k: res[k]['cagr'] for k in res}; real[leg]['v1'] = float(f1[0])
    real[leg]['mdd_K2_12-1'] = res['K2_12-1']['mdd']
    if leg != 'real_spx_70_85':
        dlog.append(np.diff(np.log(cur['K2_12-1'])) - np.diff(np.log(E1[0])))
OUT['real_ms1_basis_px'] = real
d = np.concatenate(dlog); p, lo10, mean = boot_p(d)
OUT['fair_gate_i'] = dict(history='SPX 1955-85 + NDX 1986-2014 (v1) vs same dates (H1 primary)', p_gt0=p, lo10_dlog=lo10, mean_dlog=mean, te=float(d.std() * np.sqrt(252)))
print('real', json.dumps({k: {a: round(b, 4) for a, b in v.items()} for k, v in real.items()}), flush=True)
print('fair gate (i)', OUT['fair_gate_i'], flush=True)
json.dump(OUT, open('/mnt/project-files/research/fresh1/results/h1.json', 'w'), indent=1, default=float)
