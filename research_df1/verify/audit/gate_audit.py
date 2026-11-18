"""AUDIT: DF2 gate definition + MDD start-point convention sensitivity of tier membership (<=2014 dev data only).
 D  bond-excess-0 shift: path-day mean (code) vs mean over the basis' source data period (PRECOMMIT_DF1 s5 text); gate values both ways
 E  MDD convention: dfe counts the initial 1.0 as the first peak (beng out[1]); MS1 rows (ce.mdd / parity t_parity) use the first
    recorded day as first peak. Recompute WD both ways for every config that sits just outside a tier and beats that tier's pick.
Usage: python -B gate_audit.py OUT.json"""
import sys, os, json, numpy as np
os.environ.setdefault('NUMBA_CACHE_DIR', '/home/claude/nbcache_std')
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_df2 as R2, jp, iv
W = dfe.WARM; R = '/mnt/project-files/research/df1/results/'
G1 = json.load(open(R + 'grid.json'))['configs']; G2 = json.load(open(R + 'grid_df2.json'))['configs']; U = dict(G1); U.update(G2)
S2 = json.load(open(R + 'select_df2.json'))
OUT = {}
mp = DC.market('dev250_path'); T = mp['r'].shape[1]
a, b, P, blk, seed = iv.POOLS['dev250']; X = jp.mkX(*jp.calendar(a, b), 'NDX')
ex_path = float(np.mean(mp['rb'][:, W:] - mp['rf'][:, W:]))
ex_src = float(np.mean(X['rb'].values[1:] - X['rf'].values[1:]))          # source period 1986-01-02..2014-12-31 (first row has rb=0 by construction)
ex_src_all = float(np.mean(X['rb'].values - X['rf'].values))
OUT['D_ex'] = dict(ex_path_code=ex_path, ex_recorded=S2['ex_removed_path'], ex_src=ex_src, ex_src_all_rows=ex_src_all,
                   ex_path_ann=ex_path * 252, ex_src_ann=ex_src * 252, src_first=str(X.index[0].date()), src_last=str(X.index[-1].date()))
print(OUT['D_ex'], flush=True)

def mk0(m, ex, rebond=False):
    m0 = dict(m); m0['rb'] = m['rb'] - ex
    if rebond:
        bl = np.cumprod(1 + m0['rb'], axis=1); c = np.cumsum(np.c_[np.zeros(bl.shape[0]), bl], axis=1)
        sm = np.c_[np.full((bl.shape[0], 199), np.nan), (c[:, 200:] - c[:, :-200]) / 200]
        m0['bondup'] = np.where(np.isnan(sm), False, bl > sm)
    return m0
def med(o): return float(np.median(dfe.stats(o, T)[0]))
gates = {}
for tier in ('B', 'C'):
    t = S2['tiers'][tier]; d2, d1 = t['union_best'], t['df1_best']; g = {}
    for nm, i in (('df2', d2), ('df1', d1)):
        cfg = U[i]['cfg']
        g[nm + '_bondx0_path'] = med(R2.run_cfg(cfg, mk0(mp, ex_path)))
        g[nm + '_bondx0_src'] = med(R2.run_cfg(cfg, mk0(mp, ex_src)))
        g[nm + '_bondx0_src_rebond'] = med(R2.run_cfg(cfg, mk0(mp, ex_src, True)))
        g[nm + '_cost2x'] = med(R2.run_cfg(cfg, mp, cost=0.006))
    g['recorded'] = t['gate']
    g['a_margin_path'] = g['df2_bondx0_path'] - g['df1_bondx0_path']; g['a_margin_src'] = g['df2_bondx0_src'] - g['df1_bondx0_src']
    g['b_margin'] = g['df2_cost2x'] - g['df1_cost2x']
    g['adopt_path'] = d2 if (g['a_margin_path'] > 0 and g['b_margin'] > 0) else d1
    g['adopt_src'] = d2 if (g['a_margin_src'] > 0 and g['b_margin'] > 0) else d1
    gates[tier] = dict(union_best=d2, df1_best=d1, **g); print(tier, gates[tier], flush=True)
OUT['D_gates'] = gates

# ---- E. MDD start-point convention
BASES3 = ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54')
def runE(cfg, m):
    import run_grid as RG
    if cfg.get('fam') == 'static':
        L = np.full(m['r'].shape, cfg['w']); kw = dict(roff=2, reb_every=252)
    else:
        L = DC.target(m, cfg['k'], cfg['sig'], cfg['Lmax']); kw = dict(RG.KNEES[cfg['knee']]); kw['roff'] = RG.ROFF[cfg['roff']]
        if cfg.get('fam') == 'df2': kw.update(step_lo=R2.BANDS[cfg['band']][0], step_hi=R2.BANDS[cfg['band']][1], vmode=0 if cfg['M'] == 'M0' else 2)
    return dfe.run(m, L, recon=True, **kw)
def wds(i):
    cfg = U[i]['cfg']; v1 = []; v2 = []; extra = {}
    for bn in BASES3:
        m = DC.market(bn); o, E = runE(cfg, m)
        md_code = (np.c_[np.ones(E.shape[0]), E] / np.maximum.accumulate(np.c_[np.ones(E.shape[0]), E], axis=1) - 1).min(axis=1)
        md_ms1 = (E / np.maximum.accumulate(E, axis=1) - 1).min(axis=1)
        assert np.max(np.abs(md_code - o[:, 1])) < 1e-12
        if bn == 'dev250_path':
            v1.append(float(np.percentile(md_code, 10))); v2.append(float(np.percentile(md_ms1, 10)))
            s = np.sort(md_code); extra = dict(n_le_30=int(np.sum(md_code <= -0.30)), n_le_40=int(np.sum(md_code <= -0.40)), n_le_25=int(np.sum(md_code <= -0.25)),
                                               ord48_49_50=[float(s[48]), float(s[49]), float(s[50])])
        else:
            v1.append(float(md_code[0])); v2.append(float(md_ms1[0]))
    return dict(wd_code=min(v1), wd_ms1conv=min(v2), comps_code=v1, comps_ms1conv=v2, **extra)
def wd(r): return min(r['dev250_path']['mdd_p10'], r['real_ndx_86_14']['mdd'], r['real_spx_29_54']['mdd'])
E_ = {}
picks = {'A_fallback_25': -0.25, 'B': -0.30, 'C': -0.40}
for tier, bud in picks.items():
    for setname, C in (('DF1', G1), ('UNION', U)):
        ins = [i for i in C if wd(C[i]) >= bud]; best = max(ins, key=lambda i: C[i]['dev250_path']['cagr'])
        cand = [i for i in C if bud - 0.004 <= wd(C[i]) < bud and C[i]['dev250_path']['cagr'] > C[best]['dev250_path']['cagr']]
        rows = {i: dict(path_cagr=C[i]['dev250_path']['cagr'], **wds(i)) for i in cand}
        entr = [i for i, r in rows.items() if r['wd_ms1conv'] >= bud]
        nb = max(entr, key=lambda i: C[i]['dev250_path']['cagr']) if entr else best
        E_['%s|%s' % (setname, tier)] = dict(best_code=best, candidates=rows, enter_under_ms1conv=entr, best_under_ms1conv=nb)
        print(setname, tier, best, '->', nb, {i: (round(r['wd_code'], 5), round(r['wd_ms1conv'], 5)) for i, r in rows.items()}, flush=True)
# pick-side detail (how close the B pick is)
E_['pick_detail'] = {i: wds(i) for i in ('v1|s0.2|L1.0|K1|RB', 'v1|s0.1|L1.0|K1|RB', 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB')}
# gates for any changed union best (vs DF1 best under the same convention)
gg = {}
for tier in picks:
    nu = E_['UNION|%s' % tier]['best_under_ms1conv']; n1 = E_['DF1|%s' % tier]['best_under_ms1conv']
    if nu != E_['UNION|%s' % tier]['best_code'] and U[nu]['cfg'].get('fam') == 'df2':
        g = {}
        for nm, i in (('df2', nu), ('df1', n1)):
            cfg = U[i]['cfg']; g[nm + '_bondx0_path'] = med(R2.run_cfg(cfg, mk0(mp, ex_path))); g[nm + '_bondx0_src'] = med(R2.run_cfg(cfg, mk0(mp, ex_src)))
            g[nm + '_cost2x'] = med(R2.run_cfg(cfg, mp, cost=0.006))
        g['adopt_path'] = nu if (g['df2_bondx0_path'] > g['df1_bondx0_path'] and g['df2_cost2x'] > g['df1_cost2x']) else n1
        g['adopt_src'] = nu if (g['df2_bondx0_src'] > g['df1_bondx0_src'] and g['df2_cost2x'] > g['df1_cost2x']) else n1
        gg[tier] = dict(union_best=nu, df1_best=n1, **g); print('gate under ms1conv', tier, gg[tier], flush=True)
E_['gates_under_ms1conv'] = gg
OUT['E_mdd_convention'] = E_
json.dump(OUT, open(sys.argv[1], 'w'), indent=1, default=str)
