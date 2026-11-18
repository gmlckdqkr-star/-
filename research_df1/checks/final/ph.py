"""POST-HOC stress battery (2026-11-18, after the report audit). NOT a selection round: PRECOMMIT_DF2 says no DF3, so nothing here can be adopted.
Purpose: the audit found (checks/null) configs OUTSIDE the pre-registered list inside -20% (vol-target 5% + bond; static QQQ20/25 + bond), and
DF2 configs inside tiers B/C above the picks that the rule never gated. This runs the same stress battery on them and on the 3 picks.
<=2014 only; synthetic bonds, bootstrap paths and path-FX are NON-ACTUAL. Writes checks/final/ph.json."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/checks/costtax')
import ctlib as CT, dfctx as DC, dfe, run_grid as RG, run_df2 as R2, ov, mkt, jp, iv, std
import picks_krw_lib as PK
OUT = '/mnt/project-files/research/df1/checks/final/'
W = dfe.WARM; SELM = CT.SELM; C = CT.all_configs()
EXS = {b: CT.ex_src(b, 20) for b in SELM}
B1 = (0.1, 0.25)
N = {  # post-hoc naive configs (checks/null definitions)
 'vt05_K1': dict(fam='vt', sig=0.05, Lmax=1.0, knee='K1'), 'vt05_K0': dict(fam='vt', sig=0.05, Lmax=1.0, knee='K0'),
 'st25_K1': dict(fam='static', w=0.25, knee='K1'), 'st20_K1': dict(fam='static', w=0.20, knee='K1'),
 'vt10_K1 (T25 twin)': dict(fam='vt', sig=0.10, Lmax=1.0, knee='K1'), 'vt30_K2 (T40 twin)': dict(fam='vt', sig=0.30, Lmax=1.0, knee='K2')}
P = {'T25': 'v1|s0.1|L1.0|K1|RB', 'T30': 'v1|s0.2|L1.0|K1|RB', 'T40': 'v1|s0.3|L1.0|K2|RB'}

def run(name, m, recon=False, **kw):
    if name in P: 
        if recon: return PK.run_rec(C[P[name]], m, **kw)
        return R2.run_cfg(C[P[name]], m, **kw), None
    c = N[name]; k = dict(RG.KNEES[c['knee']]); k['roff'] = 2
    if c['fam'] == 'static': L = np.full(m['r'].shape, c['w']); k.update(step_lo=0.05, step_hi=0.25, reb_every=252)
    else:
        L = np.minimum(c['Lmax'], c['sig'] / np.maximum(m['vol20'], 1e-9)); L = np.where(np.isnan(L), 0.0, L); k.update(step_lo=B1[0], step_hi=B1[1])
    k.update(kw); o, E = dfe.run(m, L, recon=recon, **k); return o, E

def sh(m, ex): m2 = dict(m); m2['rb'] = m['rb'] - ex; m2['rb'][:, 0] = 0.0; return m2
def met(o, T, path):
    cg, md = dfe.stats(o, T)
    return dict(cagr=float(np.median(cg)), p10=float(np.percentile(cg, 10)), mddp10=float(np.percentile(md, 10)), dd80=float(np.mean(md <= -0.8))) if path else dict(cagr=float(cg[0]), mdd=float(md[0]))

BASE = {b: DC.market(b) for b in SELM}
def world(mk, kw, real_from=None):
    """mk: basis -> market (path basis required; real bases optional -> taken from real_from rows)."""
    res = {}
    for nm in list(P) + list(N):
        r = {}
        for b in SELM:
            if b not in mk: r[b] = real_from[nm][b]; continue
            m = mk[b]; T = m['r'].shape[1]; r[b] = met(run(nm, m, **kw)[0], T, b == 'dev250_path')
        r['wd'] = min(r['dev250_path']['mddp10'], r['real_ndx_86_14']['mdd'], r['real_spx_29_54']['mdd']); res[nm] = r
    return res

t0 = time.time(); R = {}
R['base'] = world(BASE, {})
for v in ('cost2x', 'cost045', 'delay3', 'delay4', 'delay5', 'W0_100M'):
    kw = dict(cost2x=dict(cost=0.006), cost045=dict(cost=0.0045), delay3=dict(delay=3), delay4=dict(delay=4), delay5=dict(delay=5), W0_100M=dict(D=0.025))[v]
    R[v] = world(BASE, kw)
R['bondx0'] = world({b: sh(BASE[b], EXS[b]) for b in SELM}, {})
R['bond_m1'] = world({b: sh(BASE[b], EXS[b] + 0.01 / 252) for b in SELM}, {})
ADV = dict(D=0.025, cost=0.0045, erb=0.0025, delay=3)
R['adv'] = world(BASE, ADV); R['adv_bx0'] = world({b: sh(BASE[b], EXS[b]) for b in SELM}, ADV)
print('base worlds %.0fs' % (time.time() - t0), flush=True)
# decorrelation (same as fc.py block A)
mp = BASE['dev250_path']; c = mp['ctx']; a, b_, Pn, blk, seed = iv.POOLS['dev250']; Rc, Mc = jp.calendar(a, b_); X = jp.mkX(Rc, Mc, 'NDX')
rb_src = mkt.bond10(X).values; y10 = X['y10'].astype(float).values; cp_src = np.r_[np.nan, y10[:-1]] / 100.0 / 252.0
for bs in (1007, 2007, 3007):
    ib = ov.boot_idx(len(X), P=Pn, years=30, block=blk, seed=bs, lo=1)
    rb = np.nan_to_num(rb_src[ib], nan=0.0); rb[:, 0] = 0.0; cp = np.nan_to_num(cp_src[ib], nan=0.0); cp[:, 0] = 0.0
    bl = np.cumprod(1 + rb, axis=1); s = DC._sma(bl, 200); m = dict(mp); m['rb'] = rb; m['cpn'] = cp; m['bondup'] = np.where(np.isnan(s), False, bl > np.nan_to_num(s, nan=np.inf))
    R['decor_%d' % bs] = world({'dev250_path': m}, {}, real_from=R['base'])
# block-125 pool (seed 7), path flags recomputed like std.contexts
ii = ov.boot_idx(len(X), P=Pn, years=30, block=125, seed=7, lo=1); c125 = ov.Ctx(X, ov.flags_hist(X), ii); c125.F = std.path_flags(X, ii)
R['block125'] = world({'dev250_path': DC._finish(c125, X)}, {}, real_from=R['base'])
print('decor + block125 %.0fs' % (time.time() - t0), flush=True)
# KRW (path FX bootstrapped with the same blocks = NON-ACTUAL; DEXKOUS quality gate FAIL -> stress only)
rel_n, rel_p = PK.fx_rel(); R['krw'] = {}
for nm in list(P) + list(N):
    o, E = run(nm, BASE['dev250_path'], recon=True); _, _, cgk, mdk = PK.kstats(E, o[:, 0], rel_p, True)
    o2, E2 = run(nm, BASE['real_ndx_86_14'], recon=True); _, _, cgk2, mdk2 = PK.kstats(E2, o2[:, 0], rel_n, True)
    R['krw'][nm] = dict(path_cagr=float(np.median(cgk)), path_mddp10=float(np.percentile(mdk, 10)), ndx_cagr=float(cgk2[0]), ndx_mdd=float(mdk2[0]))
# validation bases for the naive -20% configs (V1: SPX55/70 MDD >= budget-10pp; V2: >=5/6 foreign)
R['validation'] = {}
for nm in ('vt05_K1', 'vt05_K0', 'st25_K1', 'st20_K1'):
    R['validation'][nm] = {}
    for vb in DC.VAL:
        m = DC.market(vb); T = m['r'].shape[1]; R['validation'][nm][vb] = met(run(nm, m)[0], T, False)
# DF2 configs inside tiers B/C above the pick: the gates the rule never applied (reference only)
U = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; U.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
wd = lambda r: min(r['dev250_path']['mdd_p10'], r['real_ndx_86_14']['mdd'], r['real_spx_29_54']['mdd'])
T = mp['r'].shape[1]; m0 = sh(mp, EXS['dev250_path'])
gv = lambda i: (float(np.median(dfe.stats(R2.run_cfg(C[i], m0), T)[0])), float(np.median(dfe.stats(R2.run_cfg(C[i], mp, cost=0.006), T)[0])))
R['df2_ungated'] = {}
for tn, bud, pick in (('B', -0.30, P['T30']), ('C', -0.40, P['T40'])):
    above = [i for i, r in U.items() if wd(r) >= bud and r['dev250_path']['cagr'] > U[pick]['dev250_path']['cagr']]
    g1 = gv(pick); rows = []
    for i in sorted(above, key=lambda i: -U[i]['dev250_path']['cagr']):
        g = gv(i); rows.append(dict(id=i, path=U[i]['dev250_path']['cagr'], wd=wd(U[i]), bondx0=g[0], cost2x=g[1], passes_both=bool(g[0] > g1[0] and g[1] > g1[1])))
    R['df2_ungated'][tn] = dict(pick=pick, pick_bondx0=g1[0], pick_cost2x=g1[1], n_above=len(rows), n_pass=sum(r['passes_both'] for r in rows), rows=rows)
json.dump(R, open(OUT + 'ph.json', 'w'), indent=1)
print('done %.0fs' % (time.time() - t0), flush=True)
names = list(P) + list(N)
print('%-22s' % 'world' + ''.join('%-24s' % n[:22] for n in names))
for w in [k for k in R if k not in ('krw', 'validation', 'df2_ungated')]:
    print('%-22s' % w + ''.join('%5.2f/%6.1f %-11s' % (100 * R[w][n]['dev250_path']['cagr'], 100 * R[w][n]['wd'], '') for n in names))
print('%-22s' % 'krw path' + ''.join('%5.2f/%6.1f %-11s' % (100 * R['krw'][n]['path_cagr'], 100 * R['krw'][n]['path_mddp10'], '') for n in names))
print('%-22s' % 'krw ndx' + ''.join('%5.2f/%6.1f %-11s' % (100 * R['krw'][n]['ndx_cagr'], 100 * R['krw'][n]['ndx_mdd'], '') for n in names))
print('base p10 / dd80:', {n: (round(100 * R['base'][n]['dev250_path']['p10'], 2), R['base'][n]['dev250_path']['dd80']) for n in names})
print('base real ndx / spx29:', {n: (round(100 * R['base'][n]['real_ndx_86_14']['cagr'], 2), round(100 * R['base'][n]['real_ndx_86_14']['mdd'], 1), round(100 * R['base'][n]['real_spx_29_54']['cagr'], 2), round(100 * R['base'][n]['real_spx_29_54']['mdd'], 1)) for n in names})
for nm, v in R['validation'].items(): print('VAL', nm, {k: (round(100 * x['cagr'], 1), round(100 * x['mdd'], 1)) for k, x in v.items()})
for tn, d in R['df2_ungated'].items():
    print('DF2 ungated tier', tn, 'pick gates %.4f/%.4f' % (d['pick_bondx0'], d['pick_cost2x']), 'n_above', d['n_above'], 'n_pass_both', d['n_pass'])
    for r in d['rows'][:12]: print('   %-34s path %.4f wd %.4f bx0 %.4f c2x %.4f %s' % (r['id'], r['path'], r['wd'], r['bondx0'], r['cost2x'], r['passes_both']))
