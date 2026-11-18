"""walkfwd check: out-of-time test of the DF1/DF2 SELECTION PROCEDURE (<=2014 data only; all pool numbers are NON-ACTUAL bootstrap).
(a) select on 1986-01-02..1999-12-31 NDX (pool block 250, P 500, 30y, path-recomputed flags + real NDX 1986-99 + real SPX 1929-54),
    test on real NDX 2000-01-03..2014-12-31 (fresh account, 300 warm-up rows before it) and on a 2000-2014-only pool.
(b) reverse: select on 2000-2014, test on 1986-1999.
Selection = exactly the adopted rule: WD = min(pool MDD p10, real NDX MDD, real SPX 29-54 MDD) >= tier budget; max pool median after-tax CAGR;
tie < 0.05pp -> higher real NDX CAGR; DF2 gate (union best DF2 must beat DF1 best on bond-excess-0 AND cost-2x pool medians).
Usage: python -B walkfwd.py [seed ...]   (default seeds 7 23 41 59 101; seed 7 = iv.POOLS e8699/e0014 definition)."""
import sys, os, json, time, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2, std, ov, jp

OUT = '/mnt/project-files/research/df1/checks/walkfwd/'
CACHE = '/tmp/chk_walkfwd/cache/'; os.makedirs(CACHE, exist_ok=True)
W = dfe.WARM
C = RG.configs() + R2.configs(); IDS = [c['id'] for c in C]; N = len(C); assert N == 1123
ISDF2 = np.array([c.get('fam') == 'df2' for c in C])
TIERS = (('T20', -0.20), ('T25', -0.25), ('T30', -0.30), ('T40', -0.40))
ADOPT = {'T25': 'v1|s0.1|L1.0|K1|RB', 'T30': 'v1|s0.2|L1.0|K1|RB', 'T40': 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB'}
PER = {'A': ('1986-01-02', '1999-12-31'), 'B': ('2000-01-03', '2014-12-31')}

def pool(per, seed):
    a, b = PER[per]; R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
    assert X.index.max() <= pd.Timestamp('2014-12-31')
    ii = ov.boot_idx(len(X), P=500, years=30, block=250, seed=seed, lo=1)
    c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}
    return DC._finish(c, X)

def real(per):
    a, b = PER[per]; R, M = jp.calendar('1984-01-03', b); X = jp.mkX(R, M, 'NDX'); F = ov.flags_hist(X)
    assert X.index.max() <= pd.Timestamp('2014-12-31')
    i0 = X.index.searchsorted(pd.Timestamp(a)) - W; assert i0 >= 0
    c = ov.Ctx(X, F, np.arange(i0, len(X))[None, :]); m = DC._finish(c, X)
    m['first_live'] = str(X.index[i0 + W].date()); m['last'] = str(X.index[-1].date())
    return m

def evalm(m, tag):
    f = CACHE + tag + '.npz'
    if os.path.exists(f): return dict(np.load(f))
    T = m['r'].shape[1]; P = m['r'].shape[0]; res = {k: np.zeros(N) for k in ('cagr', 'p10', 'mdd', 'mdd_p10')}
    for j, cfg in enumerate(C):
        cg, md = dfe.stats(R2.run_cfg(cfg, m), T)
        res['cagr'][j] = np.median(cg); res['mdd'][j] = np.median(md)
        res['p10'][j] = np.percentile(cg, 10); res['mdd_p10'][j] = np.percentile(md, 10)
    # references on the same basis: QQQ 1x hold (DF engine) and v1 (locked MS1 engine std.s085, cash 0)
    cg, md = dfe.stats(dfe.run(m, np.ones_like(m['r']))[0], T)
    res['qqq'] = np.array([np.median(cg), np.percentile(cg, 10), np.median(md), np.percentile(md, 10)])
    c = m['ctx']; B, bfn, bp, fs = std.s085(c); cg, E = std.engine(c, B, bfn, bp, fs, cspr=10.0)
    md = (E / np.maximum.accumulate(E, axis=1) - 1).min(axis=1)
    res['v1'] = np.array([np.median(cg), np.percentile(cg, 10), np.median(md), np.percentile(md, 10)])
    np.savez(f, **res); return res

def gate_vals(m, j):
    T = m['r'].shape[1]; ex = float(np.mean(m['rb'][:, W:] - m['rf'][:, W:])); m0 = dict(m); m0['rb'] = m['rb'] - ex
    a = float(np.median(dfe.stats(R2.run_cfg(C[j], m0), T)[0])); b = float(np.median(dfe.stats(R2.run_cfg(C[j], m, cost=0.006), T)[0]))
    return a, b

def select(pl, rl, spx, bud, mpool=None, df1_only=False):
    wd = np.minimum(np.minimum(pl['mdd_p10'], rl['mdd']), spx)
    ins = np.where((wd >= bud) & (~ISDF2 if df1_only else True))[0]
    if len(ins) == 0: return None, wd, 0, None
    bv = pl['cagr'][ins].max(); tie = ins[bv - pl['cagr'][ins] < 0.0005]; best = int(tie[np.argmax(rl['cagr'][tie])])
    if df1_only or not ISDF2[best] or mpool is None: return best, wd, len(ins), None
    d1, _, _, _ = select(pl, rl, spx, bud, df1_only=True)
    if d1 is None: return best, wd, len(ins), None
    gb, g1 = gate_vals(mpool, best), gate_vals(mpool, d1)
    g = dict(union_best=IDS[best], df1_best=IDS[d1], df2_bondx0=gb[0], df1_bondx0=g1[0], df2_cost2x=gb[1], df1_cost2x=g1[1])
    adopt = best if (gb[0] > g1[0] and gb[1] > g1[1]) else d1
    return adopt, wd, len(ins), g

def row(pl, rl, j):
    return dict(pool_cagr=float(pl['cagr'][j]), pool_p10=float(pl['p10'][j]), pool_mdd_med=float(pl['mdd'][j]), pool_mdd_p10=float(pl['mdd_p10'][j]),
                real_cagr=float(rl['cagr'][j]), real_mdd=float(rl['mdd'][j]))
def refrow(pl, rl, k):
    return dict(pool_cagr=float(pl[k][0]), pool_p10=float(pl[k][1]), pool_mdd_med=float(pl[k][2]), pool_mdd_p10=float(pl[k][3]),
                real_cagr=float(rl[k][0]), real_mdd=float(rl[k][2]))

if __name__ == '__main__':
    seeds = [int(s) for s in sys.argv[1:]] or [7, 23, 41, 59, 101]
    t0 = time.time()
    ms = DC.market('real_spx_29_54'); spx = evalm(ms, 'spx2954')
    G = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; G.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
    chk = float(max(abs(spx['mdd'][j] - G[IDS[j]]['real_spx_29_54']['mdd']) for j in range(N)))
    print('SPX29-54 mdd max |diff| vs grid files: %.2e' % chk, flush=True)
    RL = {}
    for p in PER:
        mr = real(p); RL[p] = evalm(mr, 'real_' + p); RL[p + '_dates'] = (mr['first_live'], mr['last'])
    # sanity: T25 pick on real 86-99 must reproduce the eras.json 1986-1999 MDD (account continuity up to 1999)
    jT25 = IDS.index(ADOPT['T25'])
    print('real A first live %s last %s | real B first live %s last %s' % (RL['A_dates'] + RL['B_dates']))
    print('T25 real86-99 mdd %.5f (eras.json 1986_1999 -0.19054)' % RL['A']['mdd'][jT25], flush=True)
    out = dict(N=N, seeds=seeds, spx_check=chk, real_dates={p: RL[p + '_dates'] for p in PER}, adopted=ADOPT, runs={})
    for seed in seeds:
        MP = {p: pool(p, seed) for p in PER}; PL = {p: evalm(MP[p], 'pool_%s_s%d' % (p, seed)) for p in PER}
        print('seed %d pools evaluated %.0fs' % (seed, time.time() - t0), flush=True)
        for sel, tst in (('A', 'B'), ('B', 'A')):
            key = 'seed%d_%s2%s' % (seed, sel, tst); res = {}
            for tn, bud in TIERS:
                j, wd, nin, gate = select(PL[sel], RL[sel], spx['mdd'], bud, MP[sel])
                jo, wdo, nino, gateo = select(PL[tst], RL[tst], spx['mdd'], bud, MP[tst])     # same procedure run on the test period ("oracle")
                t = dict(budget=bud, n_in_sel=nin, n_in_test=nino, gate=gate, oracle_gate=gateo)
                if j is not None:
                    t['pick'] = IDS[j]; t['pick_in_sample'] = dict(row(PL[sel], RL[sel], j), wd=float(wd[j]))
                    t['pick_test'] = dict(row(PL[tst], RL[tst], j), wd_test=float(wdo[j]))
                    t['pick_test']['defensive_real'] = bool(RL[tst]['mdd'][j] >= bud); t['pick_test']['defensive_pool'] = bool(PL[tst]['mdd_p10'][j] >= bud)
                    t['pick_test']['in_tier_test_WD'] = bool(wdo[j] >= bud)
                    ins = np.where(wdo >= bud)[0]
                    if len(ins): t['pick_test']['pctile_pool_cagr_among_test_in_tier'] = float(100 * np.mean(PL[tst]['cagr'][ins] < PL[tst]['cagr'][j] + 1e-12))
                if jo is not None:
                    t['oracle'] = IDS[jo]; t['oracle_test'] = dict(row(PL[tst], RL[tst], jo), wd_test=float(wdo[jo]))
                    if j is not None:
                        t['keep_pool_pp'] = float(PL[tst]['cagr'][j] - PL[tst]['cagr'][jo]); t['keep_real_pp'] = float(RL[tst]['cagr'][j] - RL[tst]['cagr'][jo])
                if tn in ADOPT:
                    ja = IDS.index(ADOPT[tn]); t['adopted'] = ADOPT[tn]
                    t['adopted_sel_period'] = dict(row(PL[sel], RL[sel], ja), wd=float(wd[ja]), in_tier=bool(wd[ja] >= bud))
                    t['adopted_test'] = dict(row(PL[tst], RL[tst], ja), wd_test=float(wdo[ja]))
                res[tn] = t
            res['QQQ1x_test'] = refrow(PL[tst], RL[tst], 'qqq'); res['v1_test'] = refrow(PL[tst], RL[tst], 'v1')
            res['QQQ1x_sel'] = refrow(PL[sel], RL[sel], 'qqq'); res['v1_sel'] = refrow(PL[sel], RL[sel], 'v1')
            out['runs'][key] = res
            print('==', key, '%.0fs' % (time.time() - t0))
            for tn, _ in TIERS:
                t = res[tn]
                if 'pick' not in t: print('  %s empty (n_in %d)' % (tn, t['n_in_sel'])); continue
                a, b = t['pick_in_sample'], t['pick_test']
                print('  %s n_in %3d pick %-34s IS pool %.4f WD %.4f | OOT real %.4f/%.4f pool %.4f mddp10 %.4f inTier %s pct %.0f | oracle %s pool %.4f real %.4f%s' % (
                    tn, t['n_in_sel'], t['pick'], a['pool_cagr'], a['wd'], b['real_cagr'], b['real_mdd'], b['pool_cagr'], b['pool_mdd_p10'], b['in_tier_test_WD'],
                    b.get('pctile_pool_cagr_among_test_in_tier', -1), t.get('oracle'), t.get('oracle_test', {}).get('pool_cagr', np.nan), t.get('oracle_test', {}).get('real_cagr', np.nan),
                    ' GATE %s' % t['gate'] if t['gate'] else ''))
                if 'adopted' in t:
                    c_ = t['adopted_test']; print('      adopted %-30s OOT real %.4f/%.4f pool %.4f mddp10 %.4f | sel-period WD %.4f inTier %s' % (
                        t['adopted'], c_['real_cagr'], c_['real_mdd'], c_['pool_cagr'], c_['pool_mdd_p10'], t['adopted_sel_period']['wd'], t['adopted_sel_period']['in_tier']))
            q, v = res['QQQ1x_test'], res['v1_test']
            print('  refs test: QQQ real %.4f/%.4f pool %.4f mddp10 %.4f | v1 real %.4f/%.4f pool %.4f mddp10 %.4f' % (
                q['real_cagr'], q['real_mdd'], q['pool_cagr'], q['pool_mdd_p10'], v['real_cagr'], v['real_mdd'], v['pool_cagr'], v['pool_mdd_p10']), flush=True)
        del MP
        json.dump(out, open(OUT + 'result.json', 'w'), indent=1)
    print('done %.0fs' % (time.time() - t0))
