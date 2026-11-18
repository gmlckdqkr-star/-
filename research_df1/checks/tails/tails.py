"""Check 'tails' (DF1/DF2 other-checks, 2026-11-18): execution delay, synthetic one-day gap, exposure creep.
All data <= 2014-12-31. Synthetic gap paths are NON-ACTUAL (a real return is overwritten with -20% / -25%).
Stages (argv[1]): delay | creep | gap | scan | all.  Writes stage JSON to OUTD; tails_merge.py builds result.json."""
import sys, os, json, copy, time, inspect, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2, std, ov, jp, iv
import lh1run as LH
from numba import njit, prange

OUTD = '/mnt/project-files/research/df1/checks/tails'
W = dfe.WARM
G = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']
G.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
PICKS = {'T25': 'v1|s0.1|L1.0|K1|RB', 'T30': 'v1|s0.2|L1.0|K1|RB', 'T40': 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB',
         'T40alt_df1': 'v1|s0.3|L1.0|K2|RB'}        # T40alt = DF1 tier-C best (select_df2_fixed.json 'adopted'), reference only
LIM = {'T25': -0.25, 'T30': -0.30, 'T40': -0.40, 'T40alt_df1': -0.40}
SEL = ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54')

# ---------------------------------------------------------------- recording engine: dfe.run1 source, verbatim, + weight record
_src = inspect.getsource(dfe.run1)
_src = _src.replace('@njit(cache=True)\n', '').replace('def run1(', 'def run1r(')
_old = '            rec[t - WARM] = E\n'
assert _src.count(_old) == 1
_src = _src.replace(_old, '            rec[t - WARM, 0] = E\n            rec[t - WARM, 1] = v[0] / E\n            rec[t - WARM, 2] = v[1] / E\n')
_ns = dict(np=np, WARM=W, _w=dfe._w)
exec(_src, _ns)
run1r = njit(_ns['run1r'])

@njit(parallel=True)
def runPr(R, RF, RB, CP, IU, BU, L, delay, cost, tax, D, harvest, hthr, cspr, er3, erq, erb, ertb,
          step_hi, step_lo, roff, vmode, kon, d0, d1, kfl, reb_every):
    P, T = R.shape; out = np.zeros((P, 9)); EE = np.zeros((P, T - W, 3))
    for i in prange(P):
        rec = np.zeros((T - W, 3))
        run1r(R[i], RF[i], RB[i], CP[i], IU[i], BU[i], L[i], delay, cost, tax, D, harvest, hthr, cspr, er3, erq, erb, ertb,
              step_hi, step_lo, roff, vmode, kon, d0, d1, kfl, reb_every, out[i], rec, 1)
        EE[i] = rec
    return out, EE

def cfg_args(cfg, m):
    """same L and engine kwargs as run_df2.run_cfg / run_grid.run_cfg (grid + df2 families)."""
    L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']]); kw['roff'] = RG.ROFF[cfg['roff']]
    if cfg.get('fam') == 'df2':
        kw.update(step_lo=R2.BANDS[cfg['band']][0], step_hi=R2.BANDS[cfg['band']][1], vmode=0 if cfg['M'] == 'M0' else 2)
    return L, kw

def run_rec(cfg, m, **extra):
    L, kw = cfg_args(cfg, m); p = dict(dfe.DEF); p.update(kw); p.update(extra)
    f = lambda a, dt=np.float64: np.ascontiguousarray(a, dtype=dt)
    return runPr(f(m['r']), f(m['rf']), f(m['rb']), f(m['cpn']), f(m['idxup'], np.bool_), f(m['bondup'], np.bool_), f(L),
                 int(p['delay']), p['cost'], p['tax'], p['D'], int(p['harvest']), p['hthr'], p['cspr'], p['er3'], p['erq'], p['erb'],
                 p['ertb'], p['step_hi'], p['step_lo'], int(p['roff']), int(p['vmode']), int(p['kon']), p['d0'], p['d1'], p['kfl'],
                 int(p['reb_every']))

def cfg_of(pk): return dict(G[PICKS[pk]]['cfg'])

def met(cg, md, lim=None):
    d = dict(cagr_med=float(np.median(cg)), cagr_p10=float(np.percentile(cg, 10)), mdd_med=float(np.median(md)),
             mdd_p10=float(np.percentile(md, 10)), mdd_min=float(np.min(md)))
    if len(md) > 1:
        for x in (-0.25, -0.30, -0.40, -0.50): d['P_mdd_lt_%d' % int(-x * 100)] = float(np.mean(md < x))
        if lim is not None: d['P_breach_tier'] = float(np.mean(md < lim))
    return d

def v1_locked(c):
    B, bfn, bp, fs = std.s085(c); cg, E = std.engine(c, B, bfn, bp, fs, cspr=10.0)
    md = (E / np.maximum.accumulate(E, axis=1) - 1).min(axis=1); return cg, md

def hold1x(m):
    o, _ = dfe.run(m, np.full(m['r'].shape, 1.0)); return dfe.stats(o, m['r'].shape[1])

def X_of(name):
    if name.startswith('dev250'):
        a, b, P, blk, seed = iv.POOLS['dev250']; R, M = jp.calendar(a, b); return jp.mkX(R, M, 'NDX')
    if name == 'real_ndx_86_14':
        R, M = jp.calendar('1984-01-03', '2014-12-31'); return jp.mkX(R, M, 'NDX')
    if name == 'real_spx_29_54': return LH.build(LH.END, 'A')
    raise ValueError(name)

def gap_market(c0, X, days, g, rep=1):
    """NON-ACTUAL: copy of context c0 (optionally each path repeated rep times), r[p, days[p]] overwritten with g,
    level / sma / vol / signals / idxup rebuilt through dfctx._finish. Macro flags, rf, bond unchanged."""
    c = copy.copy(c0); P0 = c0.P
    R = lambda a: np.repeat(a, rep, axis=0) if rep > 1 else a
    c.ii = R(c0.ii); c.r = R(c0.r).copy(); c.rf = R(c0.rf); c.rb = R(c0.rb)
    c.vix = R(c0.vix) if c0.vix is not None else None
    c.F = {k: R(v) for k, v in c0.F.items()}; c.P = P0 * rep
    if days is not None:
        c.r[np.arange(c.P), days] = g
    c.lvl = np.cumprod(1 + c.r, axis=1); c._c = {}
    assert X.index.max() <= np.datetime64('2014-12-31')
    return DC._finish(c, X)

# ---------------------------------------------------------------- stage 1: execution delay
def stage_delay():
    res = {}
    for bn in SEL:
        m = DC.market(bn); T = m['r'].shape[1]
        for pk in PICKS:
            for d in (1, 2, 3, 4, 5):
                o = R2.run_cfg(cfg_of(pk), m, delay=d); cg, md = dfe.stats(o, T)
                res['%s|%s|d%d' % (pk, bn, d)] = met(cg, md, LIM[pk])
        print('delay', bn, 'done', flush=True)
    tab = {}
    for pk in PICKS:
        for d in (1, 2, 3, 4, 5):
            a = res['%s|dev250_path|d%d' % (pk, d)]; b = res['%s|real_ndx_86_14|d%d' % (pk, d)]; s = res['%s|real_spx_29_54|d%d' % (pk, d)]
            wd = min(a['mdd_p10'], b['mdd_med'], s['mdd_med'])
            tab['%s|d%d' % (pk, d)] = dict(path_cagr=a['cagr_med'], path_mdd_p10=a['mdd_p10'], ndx_cagr=b['cagr_med'], ndx_mdd=b['mdd_med'],
                                           spx29_cagr=s['cagr_med'], spx29_mdd=s['mdd_med'], WD=wd, in_tier=bool(wd >= LIM[pk]))
            print('%-11s d%d path %.4f p10mdd %.4f | ndx %.4f/%.4f | spx29 %.4f/%.4f | WD %.4f %s' % (
                pk, d, a['cagr_med'], a['mdd_p10'], b['cagr_med'], b['mdd_med'], s['cagr_med'], s['mdd_med'], wd, 'IN' if wd >= LIM[pk] else 'OUT'))
    # sanity: d2 equals the grid, d3 equals robust rows
    chk = {}
    for pk in PICKS:
        g = G[PICKS[pk]]
        chk[pk] = dict(path=abs(tab['%s|d2' % pk]['path_cagr'] - g['dev250_path']['cagr']), p10=abs(tab['%s|d2' % pk]['path_mdd_p10'] - g['dev250_path']['mdd_p10']),
                       ndx=abs(tab['%s|d2' % pk]['ndx_mdd'] - g['real_ndx_86_14']['mdd']), spx=abs(tab['%s|d2' % pk]['spx29_mdd'] - g['real_spx_29_54']['mdd']))
    print('d2 vs grid max abs diff', chk, flush=True)
    json.dump(dict(rows=res, table=tab, d2_vs_grid_absdiff=chk), open(OUTD + '/stage_delay.json', 'w'), indent=1)

# ---------------------------------------------------------------- stage 3: exposure creep (+ recorder parity)
def creep_stats(EE, mask=None):
    x = 3 * EE[:, 1:, 1] + EE[:, 1:, 2]          # NDX exposure at close t (after rebalance) = exposure for day t+1, k>=1
    t3 = 3 * EE[:, 1:, 1]
    d = dict(share_3wT_gt_1p5=float(np.mean(t3 > 1.5 + 1e-9)), share_3wT_gt_1p75=float(np.mean(t3 > 1.75)), share_3wT_gt_2=float(np.mean(t3 > 2.0)),
             max_3wT=float(np.max(t3)), p99_3wT=float(np.percentile(t3, 99)), p999_3wT=float(np.percentile(t3, 99.9)),
             max_exposure=float(np.max(x)), share_exposure_gt_1p5=float(np.mean(x > 1.5 + 1e-9)))
    if EE.shape[0] > 1:
        pm = t3.max(axis=1); ps = (t3 > 1.5 + 1e-9).mean(axis=1)
        d.update(per_path_max_med=float(np.median(pm)), per_path_max_p90=float(np.percentile(pm, 90)),
                 per_path_share_gt1p5_med=float(np.median(ps)), per_path_share_gt1p5_p90=float(np.percentile(ps, 90)),
                 P_path_ever_gt_1p75=float(np.mean(pm > 1.75)), P_path_ever_gt_2=float(np.mean(pm > 2.0)))
    return d

def stage_creep():
    res = dict(parity={}, creep={})
    for bn in SEL:
        m = DC.market(bn); T = m['r'].shape[1]
        for pk in PICKS:
            o_ref = R2.run_cfg(cfg_of(pk), m); o, EE = run_rec(cfg_of(pk), m)
            res['parity']['%s|%s' % (pk, bn)] = float(np.max(np.abs(o - o_ref)))
            res['creep']['%s|%s' % (pk, bn)] = creep_stats(EE)
            print('creep %-11s %-15s parity %.1e' % (pk, bn, res['parity']['%s|%s' % (pk, bn)]), {k: round(v, 4) for k, v in res['creep']['%s|%s' % (pk, bn)].items()}, flush=True)
            if pk == 'T40' and bn == 'real_ndx_86_14':
                t3 = 3 * EE[0, 1:, 1]; i = int(np.argmax(t3)); dates = m['X_index'][m['ctx'].ii[0, W + 1:]]
                res['T40_realndx_max_date'] = str(dates[i].date()); res['T40_realndx_days_gt1p5'] = int(np.sum(t3 > 1.5 + 1e-9))
                yrs = {}
                for dt, v in zip(dates, t3):
                    if v > 1.5 + 1e-9: yrs[dt.year] = yrs.get(dt.year, 0) + 1
                res['T40_realndx_gt1p5_by_year'] = yrs; print('T40 real NDX max at', res['T40_realndx_max_date'], 'by year', yrs)
    json.dump(res, open(OUTD + '/stage_creep.json', 'w'), indent=1)

# ---------------------------------------------------------------- stage 2: gap injection on dev250_path
def gap_day_exposure(EE, days):
    k = days - 1 - W                                  # weights at close of day d-1 carry the gap day
    w = EE[np.arange(EE.shape[0]), k]; return 3 * w[:, 1] + w[:, 2]

def stage_gap():
    m0 = DC.market('dev250_path'); c0 = m0['ctx']; X = X_of('dev250_path'); P, T = c0.r.shape
    st = m0['st_v1']; res = dict(scen={}, meta={})
    base_real = {pk: (G[PICKS[pk]]['real_ndx_86_14']['mdd'], G[PICKS[pk]]['real_spx_29_54']['mdd']) for pk in PICKS}
    days = {}
    for sd in (23, 2026):
        days['rand_s%d' % sd] = np.random.default_rng(sd).integers(W + 1, T, size=P)
    g = np.random.default_rng(23); dd = np.zeros(P, np.int64)
    for p in range(P):
        t = np.arange(W + 3, T)
        good = t[(st[p, t - 1] >= 3) & (st[p, t - 2] >= 3) & (st[p, t - 3] >= 3)]
        dd[p] = g.choice(good)
    days['invested_s23'] = dd
    res['meta']['gap_rule'] = 'r[p, day_p] overwritten by g (NON-ACTUAL); rand: uniform scoring day in [WARM+1, T-1]; invested: uniform among days whose 3 prior closes had v1 state 3 (pre-gap signal)'
    res['meta']['days_quantiles'] = {k: [int(x) for x in np.percentile(v, [0, 25, 50, 75, 100])] for k, v in days.items()}
    scen = [('base', None, 0.0)]
    for dk in days:
        for gg in (-0.20, -0.25): scen.append(('%s|g%d' % (dk, int(-gg * 100)), dk, gg))
    for name, dk, gg in scen:
        t0 = time.time()
        m = m0 if dk is None else gap_market(c0, X, days[dk], gg)
        D = days[dk] if dk is not None else None
        r = {}
        for pk in PICKS:
            o, EE = run_rec(cfg_of(pk), m); cg, md = dfe.stats(o, T); a = met(cg, md, LIM[pk])
            a['WD'] = min(a['mdd_p10'], *base_real[pk]); a['in_tier'] = bool(a['WD'] >= LIM[pk])
            if D is not None:
                ex = gap_day_exposure(EE, D); a['gapday_exp_med'] = float(np.median(ex)); a['P_gapday_exp_gt0'] = float(np.mean(ex > 0.01))
                a['P_gapday_exp_ge1'] = float(np.mean(ex >= 0.999))
                br = md < LIM[pk]
                a['P_breach_given_exp_ge1'] = float(np.mean(br[ex >= 0.999])) if np.any(ex >= 0.999) else None
                a['P_breach_given_exp_gt0'] = float(np.mean(br[ex > 0.01])) if np.any(ex > 0.01) else None
                a['gapday_exp_p90'] = float(np.percentile(ex, 90)); a['gapday_exp_max'] = float(np.max(ex))
            if name in ('rand_s23|g20', 'rand_s23|g25', 'invested_s23|g20', 'invested_s23|g25'):
                for dl in (3, 5):
                    o2, _ = run_rec(cfg_of(pk), m, delay=dl); cg2, md2 = dfe.stats(o2, T); b = met(cg2, md2, LIM[pk])
                    b['WD'] = min(b['mdd_p10'], *base_real[pk]); a['delay%d' % dl] = b
            r[pk] = a
        cg, md = hold1x(m); r['QQQ_1x_hold'] = met(cg, md)
        cg, md = v1_locked(m['ctx']); r['v1_locked_cash0'] = met(cg, md)
        res['scen'][name] = r
        print('== gap %-22s %.0fs' % (name, time.time() - t0), flush=True)
        for k, a in r.items():
            print('   %-15s cagr %.4f p10mdd %.4f mddmed %.4f P<-25 %.3f P<-30 %.3f P<-40 %.3f %s %s' % (
                k, a['cagr_med'], a['mdd_p10'], a['mdd_med'], a['P_mdd_lt_25'], a['P_mdd_lt_30'], a['P_mdd_lt_40'],
                ('WD %.4f %s' % (a['WD'], 'IN' if a['in_tier'] else 'OUT')) if 'WD' in a else '',
                ('gapexp med %.2f P>0 %.2f P>=1 %.2f Pbr|>=1 %s' % (a['gapday_exp_med'], a['P_gapday_exp_gt0'], a['P_gapday_exp_ge1'], a['P_breach_given_exp_ge1'])) if 'gapday_exp_med' in a else ''), flush=True)
        if dk is not None: del m
    json.dump(res, open(OUTD + '/stage_gap.json', 'w'), indent=1)

# ---------------------------------------------------------------- stage 2b: gap scan on the two real bases (every 10th scoring day)
def stage_scan():
    res = {}
    for bn in ('real_ndx_86_14', 'real_spx_29_54'):
        m0 = DC.market(bn); c0 = m0['ctx']; X = X_of(bn); T = c0.r.shape[1]
        dates = m0['X_index'][c0.ii[0]]
        D = np.arange(W + 1, T, 10); rep = len(D)
        res[bn] = dict(n_gap_dates=int(rep), step=10)
        for gg in (-0.20, -0.25):
            t0 = time.time(); m = gap_market(c0, X, D, gg, rep=rep); r = {}
            for pk in PICKS:
                o, EE = run_rec(cfg_of(pk), m); cg, md = dfe.stats(o, T); a = met(cg, md, LIM[pk])
                a['base_mdd'] = G[PICKS[pk]][bn]['mdd']; ex = gap_day_exposure(EE, D)
                a['gapday_exp_med'] = float(np.median(ex)); a['P_gapday_exp_gt0'] = float(np.mean(ex > 0.01))
                i = int(np.argmin(md)); a['worst_gap_date'] = str(dates[D[i]].date()); a['worst_gap_exp'] = float(ex[i])
                r[pk] = a
            cg, md = hold1x(m); r['QQQ_1x_hold'] = met(cg, md)
            cg, md = v1_locked(m['ctx']); r['v1_locked_cash0'] = met(cg, md)
            res[bn]['g%d' % int(-gg * 100)] = r
            print('== scan %s g%.2f (%d dates) %.0fs' % (bn, gg, rep, time.time() - t0), flush=True)
            for k, a in r.items():
                print('   %-15s mddmed %.4f p10 %.4f min %.4f P<-25 %.3f P<-30 %.3f P<-40 %.3f %s' % (
                    k, a['mdd_med'], a['mdd_p10'], a['mdd_min'], a['P_mdd_lt_25'], a['P_mdd_lt_30'], a['P_mdd_lt_40'],
                    ('base %.4f Pbreach %.3f worst %s exp %.2f' % (a['base_mdd'], a['P_breach_tier'], a['worst_gap_date'], a['worst_gap_exp'])) if 'base_mdd' in a else ''), flush=True)
            del m
        # 1987-type: overwrite the actual 1987-10-19 return (real NDX only)
        if bn == 'real_ndx_86_14':
            j = int(np.where(dates == np.datetime64('1987-10-19'))[0][0]); res[bn]['actual_r_1987_10_19'] = float(c0.r[0, j])
            res[bn]['actual_r_1987_10_20'] = float(c0.r[0, j + 1])
            for gg in (-0.20, -0.25):
                m = gap_market(c0, X, np.array([j]), gg); r = {}
                for pk in PICKS:
                    o, EE = run_rec(cfg_of(pk), m); cg, md = dfe.stats(o, T)
                    r[pk] = dict(cagr=float(cg[0]), mdd=float(md[0]), base_mdd=G[PICKS[pk]][bn]['mdd'], base_cagr=G[PICKS[pk]][bn]['cagr'],
                                 exp_on_day=float(gap_day_exposure(EE, np.array([j]))[0]))
                cg, md = hold1x(m); r['QQQ_1x_hold'] = dict(cagr=float(cg[0]), mdd=float(md[0]))
                cg, md = v1_locked(m['ctx']); r['v1_locked_cash0'] = dict(cagr=float(cg[0]), mdd=float(md[0]))
                res[bn]['oct19_1987_g%d' % int(-gg * 100)] = r
                print('   1987-10-19 actual r %.4f -> %.2f:' % (c0.r[0, j], gg), {k: {a: round(b, 4) for a, b in v.items()} for k, v in r.items()}, flush=True)
    json.dump(res, open(OUTD + '/stage_scan.json', 'w'), indent=1)

if __name__ == '__main__':
    st = sys.argv[1] if len(sys.argv) > 1 else 'all'; t0 = time.time()
    if st in ('delay', 'all'): stage_delay()
    if st in ('creep', 'all'): stage_creep()
    if st in ('gap', 'all'): stage_gap()
    if st in ('scan', 'all'): stage_scan()
    print('stage', st, 'done %.0fs' % (time.time() - t0))
