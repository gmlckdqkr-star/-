"""neigh check library: rebuild DF1/DF2 market inputs with parameters OUTSIDE the pre-registered grid (<=2014 data only).
Everything goes through the locked code in research/df1/code (dfctx, dfe, run_grid, run_df2) and px1lib/ov calls;
only the inputs (v1 state, vol window, idxup SMA) and engine keyword overrides change."""
import sys, json, copy, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
import px1lib as PX, ov

RES = '/mnt/project-files/research/df1/results/'
PICKS = {'T25': 'v1|s0.1|L1.0|K1|RB', 'T30': 'v1|s0.2|L1.0|K1|RB', 'T40': 'DF2|M2|b1|v1|s0.3|L1.5|K2|RB',
         'T40alt': 'v1|s0.3|L1.0|K2|RB'}     # T40alt = DF1 tier-C best, adopted instead of the DF2 pick in results/select_df2_fixed.json
BUD = {'T25': -0.25, 'T30': -0.30, 'T40': -0.40, 'T40alt': -0.40}
ALLC = {c['id']: c for c in RG.configs() + R2.configs()}


def sig_F1(c, L=3, vc=.40, k='alarm', cau='shock6m', sl=200, bd=.02, vwin=20):
    """px1lib.signal 'F1' branch with the vol-cap window exposed (px1lib.vcap hard-codes c.vol(20))."""
    B = np.where(c.vol(vwin) > vc, min(1.0, L), float(L))
    if cau: B = np.where(ov.macro_cond(c, (cau,)), np.minimum(B, 1.0), B)
    off = ov.trend_gate(c, sl, bd, ov.macro_cond(c, PX.COND[k])); return np.where(off, 0.0, B)


def env(base, sl=200, bd=.02, vc=.40, vwin=20, vwin_cap=20, idx_sma=200):
    """copy of a DC.market dict with the v1/always states, the sigma-target vol and idxup rebuilt from new parameters."""
    m = dict(base); c = base['ctx']
    default_sig = (sl, bd, vc, vwin_cap) == (200, .02, .40, 20)
    if not default_sig:
        if vwin_cap == 20:   # use the locked px1lib code path whenever possible
            m['st_v1'] = PX.signal(c, ('F1', 3, vc, 'alarm', 'shock6m', sl, bd))
            m['st_al'] = PX.signal(c, ('F1', 3, vc, 'always', 'shock6m', sl, bd))
        else:
            m['st_v1'] = sig_F1(c, vc=vc, k='alarm', sl=sl, bd=bd, vwin=vwin_cap)
            m['st_al'] = sig_F1(c, vc=vc, k='always', sl=sl, bd=bd, vwin=vwin_cap)
    if vwin != 20: m['vol20'] = c.vol(vwin)
    if idx_sma != 200:
        s = c.sma(idx_sma); m['idxup'] = np.where(np.isnan(s), False, c.lvl > s)
    return m


def eng_kw(cfg, ks=1.0, kfl=None, step_lo=None, step_hi=None):
    """engine overrides: knee d0/d1 scaled by ks, knee floor, rebalance steps (applied on top of the config's own settings)."""
    kw = {}
    kn = cfg.get('knee')
    if kn in ('K1', 'K2'):
        if ks != 1.0: kw.update(d0=RG.KNEES[kn]['d0'] * ks, d1=RG.KNEES[kn]['d1'] * ks)
        if kfl is not None: kw['kfl'] = kfl
    if step_lo is not None: kw['step_lo'] = step_lo
    if step_hi is not None: kw['step_hi'] = step_hi
    return kw


def run3(cfg, M3, kw):
    """cfg on the 3 selection bases -> metrics dict (same definitions as run_grid.summ + WD)."""
    d = {}
    for bn in DC.SEL:
        m = M3[bn]; o = R2.run_cfg(cfg, m, **kw); d[bn] = RG.summ(o, m['r'].shape[1], m['r'].shape[0] > 1)
    d['wd'] = min(d['dev250_path']['mdd_p10'], d['real_ndx_86_14']['mdd'], d['real_spx_29_54']['mdd'])
    return d


def flat(d):
    p, n, s = d['dev250_path'], d['real_ndx_86_14'], d['real_spx_29_54']
    return dict(path=p['cagr'], path_p10=p['p10'], path_mdd_p10=p['mdd_p10'], ndx=n['cagr'], ndx_mdd=n['mdd'],
                spx29=s['cagr'], spx29_mdd=s['mdd'], wd=d['wd'], ntr=p['ntr'], lev=p['lev'])


def grid_union():
    U = json.load(open(RES + 'grid.json'))['configs']; U.update(json.load(open(RES + 'grid_df2.json'))['configs']); return U


def wd_of(r): return min(r['dev250_path']['mdd_p10'], r['real_ndx_86_14']['mdd'], r['real_spx_29_54']['mdd'])


def frontier(U):
    """F(w) = best dev250_path median CAGR among the 1,123 pre-registered configs with WD >= w (the grid's own frontier)."""
    pts = sorted(((wd_of(r), r['dev250_path']['cagr']) for r in U.values()), key=lambda x: -x[0])
    W = np.array([p[0] for p in pts]); C = np.maximum.accumulate(np.array([p[1] for p in pts]))
    def F(w):
        j = np.searchsorted(-W, -w, side='right') - 1
        return float(C[j]) if j >= 0 else float('nan')
    return F
