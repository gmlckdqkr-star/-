"""Check 'null' (2026-11-18): what earns the defensive picks their return? <=2014 data only (all inputs end 2014-12-31).
(1) state ladder: same pick with the v1 state replaced by always-on (st=3), vcap-only, trend-only (200d +-2% always obeyed, no
    macro alarm), trend+vcap, k=always (grid), v1 without vcap; plus component removals: knee off, bond -> T-bill / cash 0,
    bond excess 0, no vol targeting at matched constant exposure, sigma none.
(2) placebo: macro alarm flags (c.F inv + shock6m, same shift for both) circularly rolled along time by 504+63j rows, j=0..39,
    within each path on dev250_path; state rebuilt with px1lib.signal(V1S); pick percentile vs placebo (path median CAGR, WD).
(3) naive frontiers with the same engine / 10y bond: static QQQ w + bond (yearly rebalanced) x knee {K0,K1,K2}; vol-target
    only (always-on) x sigma x Lmax x knee; price-only state families (trend-only, trend+vcap); v1-state family on the same grid.
    Best path CAGR among configs with WD >= pick WD and WD >= tier budget; bond-excess-0 rerun of pick vs best naive.
Bond series rb is a synthetic 10y total return (NON-ACTUAL reconstruction); dev250_path is a block bootstrap (NON-ACTUAL paths).
Run from /tmp/chk_null (never with cwd under /mnt/project-files/research)."""
import sys, copy, json, time, itertools, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG, run_df2 as R2
import px1lib as PX, jp, iv, mkt

W = dfe.WARM
OUT = '/mnt/project-files/research/df1/checks/null/'
MK = ('dev250_path', 'real_ndx_86_14', 'real_spx_29_54', 'real_spx_55_85')
SELM = MK[:3]
B1 = (0.1, 0.25)
PICKS = {'T25': dict(id='v1|s0.1|L1.0|K1|RB', sig=0.1, Lmax=1.0, knee='K1', roff='RB', vmode=0, band=B1, tier=-0.25),
         'T30': dict(id='v1|s0.2|L1.0|K1|RB', sig=0.2, Lmax=1.0, knee='K1', roff='RB', vmode=0, band=B1, tier=-0.30),
         'T40': dict(id='DF2|M2|b1|v1|s0.3|L1.5|K2|RB', sig=0.3, Lmax=1.5, knee='K2', roff='RB', vmode=2, band=B1, tier=-0.40),
         # tier C adoption after gate_fix.py (results/select_df2_fixed.json, written after the checks brief)
         'T40fix': dict(id='v1|s0.3|L1.0|K2|RB', sig=0.3, Lmax=1.0, knee='K2', roff='RB', vmode=0, band=B1, tier=-0.40)}
SPEC = {'v1': DC.V1S, 'st_al': DC.ALS,
        'vcap_only': ('F1', 3, .40, 'never', None, 200, .02),
        'trend_only': ('F1', 3, 99.0, 'always', None, 200, .02),
        'trend_vcap': ('F1', 3, .40, 'always', None, 200, .02),
        'v1_novcap': ('F1', 3, 99.0, 'alarm', 'shock6m', 200, .02)}
SHIFTS = [504 + 63 * j for j in range(40)]

def Lpre(m, st, sig, Lmax, const_on=None):
    if const_on is not None: Lon = np.full(st.shape, float(const_on))
    elif sig is None: Lon = np.full(st.shape, float(Lmax))
    else: Lon = np.minimum(float(Lmax), sig / np.maximum(m['vol20'], 1e-9))
    L = np.where(st >= 3, Lon, np.where(st >= 1, np.minimum(Lon, Lmax / 3.0), 0.0))
    return np.where(np.isnan(L), 0.0, L)

def run(m, L, cfg, **extra):
    kw = dict(RG.KNEES[cfg['knee']]); kw.update(step_lo=cfg['band'][0], step_hi=cfg['band'][1], vmode=cfg['vmode'], roff=RG.ROFF[cfg['roff']])
    if cfg.get('reb_every'): kw['reb_every'] = cfg['reb_every']
    kw.update(extra); o, _ = dfe.run(m, L, **kw); return o

def met(o, T, path):
    cg, md = dfe.stats(o, T)
    if path:
        return dict(cagr=float(np.median(cg)), dd=float(np.percentile(md, 10)), p10=float(np.percentile(cg, 10)), mdd_med=float(np.median(md)),
                    lev=float(np.median(o[:, 8])), ntr=float(np.median(o[:, 4])))
    return dict(cagr=float(cg[0]), dd=float(md[0]), lev=float(o[0, 8]), ntr=float(o[0, 4]))

def wd(rows): return min(rows[b]['dd'] for b in SELM)

def rolled(c, s):
    c2 = copy.copy(c); c2.F = dict(c.F)
    for k in ('inv', 'shock6m'): c2.F[k] = np.roll(c.F[k], s, axis=1)
    return c2

t0 = time.time()
M = {bn: DC.market(bn) for bn in MK}
TT = {bn: M[bn]['r'].shape[1] for bn in MK}; PA = {bn: M[bn]['r'].shape[0] > 1 for bn in MK}
# bond excess 0: dev250 uses the source-period mean (gate_fix.py convention); real bases use their own days (robust.py convention)
a, b, P, blk, seed = iv.POOLS['dev250']; R, MM = jp.calendar(a, b); X = jp.mkX(R, MM, 'NDX')
rbs = mkt.bond10(X).values if 'rb' not in X else X['rb'].values
EX = {'dev250_path': float(np.mean(rbs[1:] - X['rf'].values[1:]))}
for bn in MK[1:]: EX[bn] = float(np.mean(M[bn]['rb'][:, W:] - M[bn]['rf'][:, W:]))
M0 = {}
for bn in MK: m0 = dict(M[bn]); m0['rb'] = M[bn]['rb'] - EX[bn]; M0[bn] = m0
ST = {bn: {k: (M[bn]['st_v1'] if k == 'v1' else PX.signal(M[bn]['ctx'], s)) for k, s in SPEC.items()} for bn in MK}
for bn in MK: assert np.array_equal(ST[bn]['st_al'], M[bn]['st_al'])
print('setup %.0fs' % (time.time() - t0), 'EX', {k: round(v * 252, 4) for k, v in EX.items()}, flush=True)

res = dict(meta=dict(picks=PICKS, shifts=SHIFTS, bond_excess_removed_per_day=EX, markets=MK,
                     note='dev250_path = 500 block-bootstrap paths (NON-ACTUAL); rb = synthetic 10y bond (NON-ACTUAL); <=2014 only'),
           state_frac={}, ladder={}, placebo={}, naive=[], frontier={}, attribution={})
for bn in MK:
    res['state_frac'][bn] = {k: [float(np.mean(v[:, W:] == x)) for x in (0, 1, 3)] for k, v in ST[bn].items()}
    res['state_frac'][bn]['alarm_frac'] = float(np.mean((M[bn]['ctx'].F['inv'] | M[bn]['ctx'].F['shock6m'])[:, W:]))

# ---------------- (1) ladder
G = json.load(open('/mnt/project-files/research/df1/results/grid.json'))['configs']; G.update(json.load(open('/mnt/project-files/research/df1/results/grid_df2.json'))['configs'])
for pk, p in PICKS.items():
    lon = np.minimum(p['Lmax'], p['sig'] / np.maximum(M['dev250_path']['vol20'][:, W:], 1e-9)); cmed = float(np.nanmedian(lon))
    V = {}
    for bn in MK:
        m = M[bn]; T = TT[bn]; pa = PA[bn]
        def go(st='v1', const_on=None, mm=None, sig=p['sig'], **ov):
            cfg = dict(p); cfg.update(ov)
            return met(run(mm or m, Lpre(m, ST[bn][st], sig, p['Lmax'], const_on), cfg), T, pa)
        rows = {'pick': go()}
        for k in SPEC:
            if k != 'v1': rows[k] = go(st=k)
        rows['always_on'] = met(run(m, Lpre(m, np.full(m['r'].shape, 3.0), p['sig'], p['Lmax']), p), T, pa)
        rows['always_on_RT'] = met(run(m, Lpre(m, np.full(m['r'].shape, 3.0), p['sig'], p['Lmax']), dict(p, roff='RT')), T, pa)
        rows['always_on_bondx0'] = met(run(M0[bn], Lpre(m, np.full(m['r'].shape, 3.0), p['sig'], p['Lmax']), p), T, pa)
        rows['trend_only_RT'] = go(st='trend_only', roff='RT')
        rows['trend_only_bondx0'] = go(st='trend_only', mm=M0[bn])
        rows['K0'] = go(knee='K0')
        rows['RT'] = go(roff='RT'); rows['RC'] = go(roff='RC'); rows['bondx0'] = go(mm=M0[bn])
        rows['novt_matched'] = go(const_on=cmed)
        rows['sig_none'] = go(const_on=p['Lmax'])
        g = G[p['id']][bn]
        assert abs(rows['pick']['cagr'] - g['cagr']) < 1e-9, (pk, bn, rows['pick']['cagr'], g['cagr'])
        V[bn] = rows
    lad = {v: {bn: V[bn][v] for bn in MK} for v in V['dev250_path']}
    for v in lad: lad[v]['WD'] = wd(lad[v])
    lad['_novt_const_on'] = cmed
    res['ladder'][pk] = lad
    print('ladder', pk, 'pick path %.4f WD %.4f | always_on %.4f/%.4f | trend_only %.4f/%.4f' % (
        lad['pick']['dev250_path']['cagr'], lad['pick']['WD'], lad['always_on']['dev250_path']['cagr'], lad['always_on']['WD'],
        lad['trend_only']['dev250_path']['cagr'], lad['trend_only']['WD']), '%.0fs' % (time.time() - t0), flush=True)

# ---------------- (2) placebo: roll macro alarm flags
PL = {pk: {bn: [] for bn in MK} for pk in PICKS}
for j, s in enumerate(SHIFTS):
    for bn in MK:
        m = M[bn]; st = PX.signal(rolled(m['ctx'], s), DC.V1S)
        for pk, p in PICKS.items():
            PL[pk][bn].append(met(run(m, Lpre(m, st, p['sig'], p['Lmax']), p), TT[bn], PA[bn]))
    if j % 10 == 9: print('placebo shift', j + 1, '/40 %.0fs' % (time.time() - t0), flush=True)
def pctile(x, a): x = np.asarray(x); return float(100.0 * (np.mean(x < a) + 0.5 * np.mean(x == a)))
for pk in PICKS:
    lad = res['ladder'][pk]; d = dict(per_shift={})
    WDs = [min(PL[pk][b][j]['dd'] for b in SELM) for j in range(len(SHIFTS))]
    d['per_shift']['WD'] = WDs
    for bn in MK:
        cg = [r['cagr'] for r in PL[pk][bn]]; dd = [r['dd'] for r in PL[pk][bn]]
        d['per_shift'][bn] = dict(cagr=cg, dd=dd)
        d[bn] = dict(pick_cagr=lad['pick'][bn]['cagr'], plc_cagr_med=float(np.median(cg)), plc_cagr_p10=float(np.percentile(cg, 10)),
                     plc_cagr_p90=float(np.percentile(cg, 90)), pick_cagr_pct=pctile(cg, lad['pick'][bn]['cagr']),
                     pick_dd=lad['pick'][bn]['dd'], plc_dd_med=float(np.median(dd)), plc_dd_p10=float(np.percentile(dd, 10)),
                     plc_dd_p90=float(np.percentile(dd, 90)), pick_dd_pct=pctile(dd, lad['pick'][bn]['dd']))
    d['WD'] = dict(pick=lad['pick']['WD'], plc_med=float(np.median(WDs)), plc_p10=float(np.percentile(WDs, 10)), plc_p90=float(np.percentile(WDs, 90)),
                   pick_pct=pctile(WDs, lad['pick']['WD']), frac_plc_in_tier=float(np.mean(np.array(WDs) >= PICKS[pk]['tier'])))
    res['placebo'][pk] = d
    print('placebo', pk, 'path pick %.4f plc med %.4f pct %.1f | WD pick %.4f plc med %.4f pct %.1f in-tier %.2f' % (
        d['dev250_path']['pick_cagr'], d['dev250_path']['plc_cagr_med'], d['dev250_path']['pick_cagr_pct'], d['WD']['pick'], d['WD']['plc_med'],
        d['WD']['pick_pct'], d['WD']['frac_plc_in_tier']), flush=True)

# ---------------- (3) naive / price-only / v1 frontiers on one common grid
SIGS = (0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25, 0.30, 0.40)
VL = ((0, 1.0), (0, 1.5), (2, 1.5))
NC = []
for w, kn in itertools.product([round(0.20 + 0.05 * i, 2) for i in range(11)], ('K0', 'K1', 'K2')):
    NC.append(dict(id='static|QQQ%d|bond|%s' % (round(w * 100), kn), fam='static', w=w, knee=kn, roff='RB', vmode=0, band=(0.05, 0.25), reb_every=252))
for fam, (vm, lm), s, kn in itertools.product(('vt', 'trend_only', 'trend_vcap', 'v1'), VL, SIGS, ('K0', 'K1', 'K2')):
    NC.append(dict(id='%s|M%d|s%s|L%s|%s|RB' % (fam, vm, s, lm, kn), fam=fam, sig=s, Lmax=lm, knee=kn, roff='RB', vmode=vm, band=B1))
for cfg in NC:
    rows = {}
    for bn in MK:
        m = M[bn]
        if cfg['fam'] == 'static': L = np.full(m['r'].shape, cfg['w'])
        else: L = Lpre(m, np.full(m['r'].shape, 3.0) if cfg['fam'] == 'vt' else ST[bn][cfg['fam']], cfg['sig'], cfg['Lmax'])
        rows[bn] = met(run(m, L, cfg), TT[bn], PA[bn])
    rows['WD'] = wd(rows); res['naive'].append(dict(cfg=cfg, rows=rows))
print('naive grid %d configs %.0fs' % (len(NC), time.time() - t0), flush=True)
# sanity: DF1 static rows (K0, 30/50/70) vs grid.json (band differs only in rounding; K0 target constant -> identical)
for w in (30, 50, 70):
    r = [x for x in res['naive'] if x['cfg']['id'] == 'static|QQQ%d|bond|K0' % w][0]['rows']['dev250_path']['cagr']
    print('static check QQQ%d K0 path %.6f grid %.6f' % (w, r, G['static|QQQ%d|bond' % w]['dev250_path']['cagr']))

FAMS = {'static': ('static',), 'vt': ('vt',), 'naive(static+vt)': ('static', 'vt'), 'price_only(static+vt+trend)': ('static', 'vt', 'trend_only', 'trend_vcap'),
        'v1_same_grid': ('v1',)}
def best(fams, floor, vm=None):
    c = [x for x in res['naive'] if x['cfg']['fam'] in fams and x['rows']['WD'] >= floor - 1e-12 and (vm is None or x['cfg']['vmode'] in vm)]
    if not c: return None
    return max(c, key=lambda x: x['rows']['dev250_path']['cagr'])
def brief(x): return None if x is None else dict(id=x['cfg']['id'], WD=x['rows']['WD'], **{bn: (x['rows'][bn]['cagr'], x['rows'][bn]['dd']) for bn in MK})
def bondx0(cfg):
    m = M0['dev250_path']; mr = M['dev250_path']
    if cfg['fam'] == 'static': L = np.full(mr['r'].shape, cfg['w'])
    elif cfg['fam'] in PICKS: L = Lpre(mr, ST['dev250_path']['v1'], cfg['sig'], cfg['Lmax'])
    else: L = Lpre(mr, np.full(mr['r'].shape, 3.0) if cfg['fam'] == 'vt' else ST['dev250_path'][cfg['fam']], cfg['sig'], cfg['Lmax'])
    return met(run(m, L, cfg), TT['dev250_path'], True)['cagr']
for pk, p in PICKS.items():
    lad = res['ladder'][pk]; F = dict(pick=dict(path=lad['pick']['dev250_path']['cagr'], WD=lad['pick']['WD'], bondx0_path=lad['bondx0']['dev250_path']['cagr']))
    for floor_name, floor in (('at_pick_WD', lad['pick']['WD']), ('at_tier_budget', p['tier'])):
        for fn, fams in FAMS.items():
            bx = best(fams, floor); e = brief(bx)
            if e is not None:
                e['path_minus_pick'] = e['dev250_path'][0] - lad['pick']['dev250_path']['cagr']
                e['bondx0_path'] = bondx0(bx['cfg']); e['bondx0_minus_pick'] = e['bondx0_path'] - lad['bondx0']['dev250_path']['cagr']
            F['%s|%s' % (floor_name, fn)] = e
        # requested benchmarks with the pick's own knee: static 30/40/50 + bond, and vol-target only at the pick's sigma/Lmax/structure
        for w in (30, 40, 50):
            x = [y for y in res['naive'] if y['cfg']['id'] == 'static|QQQ%d|bond|%s' % (w, p['knee'])][0]
            F['static%d_%s' % (w, p['knee'])] = brief(x)
    res['frontier'][pk] = F
    nb = F['at_pick_WD|naive(static+vt)']
    print('frontier', pk, 'pick %.4f WD %.4f | best naive @WD %s' % (lad['pick']['dev250_path']['cagr'], lad['pick']['WD'],
          'none' if nb is None else '%s %.4f WD %.4f bx0 %.4f vs pick bx0 %.4f' % (nb['id'], nb['dev250_path'][0], nb['WD'], nb['bondx0_path'], lad['bondx0']['dev250_path']['cagr'])), flush=True)

# ---------------- attribution summary (deltas, not additive)
for pk in PICKS:
    lad = res['ladder'][pk]; pl = res['placebo'][pk]; pc = lad['pick']['dev250_path']['cagr']; pw = lad['pick']['WD']
    def dl(v): return dict(d_path_cagr=pc - lad[v]['dev250_path']['cagr'], d_WD=pw - lad[v]['WD'], d_ndx=lad['pick']['real_ndx_86_14']['cagr'] - lad[v]['real_ndx_86_14']['cagr'],
                           d_spx29=lad['pick']['real_spx_29_54']['cagr'] - lad[v]['real_spx_29_54']['cagr'], d_spx55=lad['pick']['real_spx_55_85']['cagr'] - lad[v]['real_spx_55_85']['cagr'])
    A = dict(state_machine_total=dl('always_on'), vs_trend_only=dl('trend_only'), vs_trend_vcap=dl('trend_vcap'),
             alarm_timing_info=dict(d_path_cagr=pc - pl['dev250_path']['plc_cagr_med'], d_WD=pw - pl['WD']['plc_med'],
                                    d_ndx=pl['real_ndx_86_14']['pick_cagr'] - pl['real_ndx_86_14']['plc_cagr_med'],
                                    d_spx29=pl['real_spx_29_54']['pick_cagr'] - pl['real_spx_29_54']['plc_cagr_med'],
                                    d_spx55=pl['real_spx_55_85']['pick_cagr'] - pl['real_spx_55_85']['plc_cagr_med'],
                                    pct_path=pl['dev250_path']['pick_cagr_pct'], pct_WD=pl['WD']['pick_pct']),
             vol_targeting_vs_matched_const=dl('novt_matched'), vol_targeting_vs_sig_none=dl('sig_none'),
             bond_vs_tbill=dl('RT'), bond_vs_cash0=dl('RC'), bond_bull_premium=dl('bondx0'), knee=dl('K0'))
    res['attribution'][pk] = A
json.dump(res, open(OUT + 'result.json', 'w'), indent=1)
print('done %.0fs' % (time.time() - t0))
