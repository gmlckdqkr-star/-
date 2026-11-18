"""Check 'boot': bootstrap-pool robustness of the HEADLINE basis (dev250_path) for DF1+DF2 (<=2014 data only).
Builds alternative dev250-style path pools from the same 1986-01-02..2014-12-31 NDX source exactly like std.contexts builds
dev250_path (ov.boot_idx(P=500, years=30, lo=1), macro flags recomputed on each path with std.path_flags, dfctx._finish),
runs every DF1 (RG.configs) and DF2 (R2.configs) config, and redoes the union tier selection incl. the DF2 adoption gates.
WD = min(alt-pool path MDD p10, stored real_ndx_86_14 MDD, stored real_spx_29_54 MDD).  All paths are NON-ACTUAL (bootstrap).
Usage: python -B boot_pools.py [pool ...]   (pool names below; default all).  Per-pool results cached as JSON in CACHE."""
import sys, os, json, time, numpy as np, pandas as pd
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
import std, ov, jp

RES = '/mnt/project-files/research/df1/results/'
OUT = '/mnt/project-files/research/df1/checks/boot/'
CACHE = os.environ.get('BOOT_CACHE', '/tmp/claude-0/-home-user/6f3e91de-e49a-5fe5-84c0-235a69554919/scratchpad/chk_boot/')
os.makedirs(CACHE, exist_ok=True)
POOLS = {'base_s7_b250': (7, 250), 's11_b250': (11, 250), 's23_b250': (23, 250), 's37_b250': (37, 250), 's51_b250': (51, 250),
         's7_b125': (7, 125), 's7_b500': (7, 500),
         'iv_dev125_s21': (21, 125), 'iv_dev500_s33': (33, 500)}   # extra: the two other MS1 pool definitions in iv.POOLS
ASKED = ('s11_b250', 's23_b250', 's37_b250', 's51_b250', 's7_b125', 's7_b500')
TIERS = (('T20', -0.20), ('T25', -0.25), ('T30', -0.30), ('T40', -0.40))
PICKS = {'T25': 'v1|s0.1|L1.0|K1|RB', 'T30': 'v1|s0.2|L1.0|K1|RB', 'T40': 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB'}

C = RG.configs() + R2.configs(); CFG = {c['id']: c for c in C}
G = json.load(open(RES + 'grid.json'))['configs']; G.update(json.load(open(RES + 'grid_df2.json'))['configs'])
assert set(CFG) <= set(G), 'config ids missing from stored grids'
REAL = {i: dict(ndx_mdd=G[i]['real_ndx_86_14']['mdd'], spx_mdd=G[i]['real_spx_29_54']['mdd'], ndx_cagr=G[i]['real_ndx_86_14']['cagr'])
        for i in CFG}

def build(seed, blk):
    a, b = '1986-01-02', '2014-12-31'                      # = iv.POOLS['dev250'] source window
    R, M = jp.calendar(a, b); X = jp.mkX(R, M, 'NDX'); assert X.index.max() <= pd.Timestamp('2014-12-31')
    F = ov.flags_hist(X)
    ii = ov.boot_idx(len(X), P=500, years=30, block=blk, seed=seed, lo=1)
    c = ov.Ctx(X, F, ii); c.F = std.path_flags(X, ii); c._c = {}   # exactly as std.contexts()['dev250_path']
    return DC._finish(c, X)

def row(o, T):
    cg, md = dfe.stats(o, T)
    return dict(cagr=float(np.median(cg)), mdd_p10=float(np.percentile(md, 10)), p10=float(np.percentile(cg, 10)),
                mdd=float(np.median(md)))

def wd(i, tab): return min(tab[i]['mdd_p10'], REAL[i]['ndx_mdd'], REAL[i]['spx_mdd'])

def best_of(ids, tab):
    if not ids: return None
    b = max(ids, key=lambda i: tab[i]['cagr'])
    tie = [i for i in ids if tab[b]['cagr'] - tab[i]['cagr'] < 0.0005]
    return max(tie, key=lambda i: REAL[i]['ndx_cagr'])

def gate_vals(i, m, T):
    W = dfe.WARM; ex = float(np.mean(m['rb'][:, W:] - m['rf'][:, W:])); m0 = dict(m); m0['rb'] = m['rb'] - ex
    a = float(np.median(dfe.stats(R2.run_cfg(CFG[i], m0), T)[0])); b = float(np.median(dfe.stats(R2.run_cfg(CFG[i], m, cost=0.006), T)[0]))
    return a, b

def select(tab, m, T):
    S = {}
    for name, bud in TIERS:
        ins = [i for i in CFG if wd(i, tab) >= bud]; t = dict(budget=bud, n_in=len(ins))
        if ins:
            ub = best_of(ins, tab); d1 = best_of([i for i in ins if CFG[i]['fam'] != 'df2'], tab); adopt = ub
            t.update(union_best=ub, df1_best=d1, union_best_cagr=tab[ub]['cagr'])
            if CFG[ub]['fam'] == 'df2' and d1:
                gb, g1 = gate_vals(ub, m, T), gate_vals(d1, m, T)
                t['gate'] = dict(df2_bondx0=gb[0], df1_bondx0=g1[0], df2_cost2x=gb[1], df1_cost2x=g1[1])
                if not (gb[0] > g1[0] and gb[1] > g1[1]): adopt = d1
            t.update(adopted=adopt, adopted_cagr=tab[adopt]['cagr'], adopted_wd=wd(adopt, tab))
            t['top5'] = [(i, round(tab[i]['cagr'], 5), round(wd(i, tab), 5)) for i in sorted(ins, key=lambda i: -tab[i]['cagr'])[:5]]
        S[name] = t
    return S

def run_pool(name):
    fn = CACHE + 'pool_%s.json' % name
    if os.path.exists(fn): return json.load(open(fn))
    seed, blk = POOLS[name]; t0 = time.time()
    m = build(seed, blk); T = m['r'].shape[1]; tb = time.time() - t0
    tab = {i: row(R2.run_cfg(CFG[i], m), T) for i in CFG}
    sel = select(tab, m, T)
    res = dict(pool=name, seed=seed, block=blk, P=int(m['r'].shape[0]), T=int(T), build_s=tb, total_s=time.time() - t0, tab=tab, sel=sel)
    json.dump(res, open(fn, 'w')); del m
    print('%-14s build %.0fs total %.0fs' % (name, tb, res['total_s']), flush=True)
    return res

if __name__ == '__main__':
    names = sys.argv[1:] or list(POOLS)
    for nm in names:
        r = run_pool(nm)
        if nm == 'base_s7_b250':        # reproduction check vs stored dev250_path
            dc = max(abs(r['tab'][i]['cagr'] - G[i]['dev250_path']['cagr']) for i in CFG)
            dm = max(abs(r['tab'][i]['mdd_p10'] - G[i]['dev250_path']['mdd_p10']) for i in CFG)
            print('REPRO base vs stored dev250_path: max|dcagr| %.2e max|dmddp10| %.2e' % (dc, dm), flush=True)
        for tn, t in r['sel'].items():
            print('  %s n_in %d union %s adopted %s cagr %s gate %s' % (tn, t['n_in'], t.get('union_best'), t.get('adopted'),
                  t.get('adopted_cagr'), t.get('gate')), flush=True)
        for tn, p in PICKS.items():
            x = r['tab'][p]; print('  pick %s %s path %.4f mddp10 %.4f wd %.4f' % (tn, p, x['cagr'], x['mdd_p10'], wd(p, r['tab'])), flush=True)
