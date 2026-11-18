"""Check 'null' part 2: apply the DF2 adoption gates (bond excess 0 with the source-period shift, cost 2x) and the bond-bear era
(real SPX 1955-85) to every naive / price-only config of null_check.py that sits in a pick's tier. Lists configs that beat the pick
on dev250_path median CAGR AND bond-excess-0 path CAGR AND cost-2x path CAGR, with WD >= the pick's WD (and >= tier budget).
Reads result.json (from null_check.py) and writes result_gates.json. <=2014 only; dev250_path and rb are NON-ACTUAL reconstructions."""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG
import px1lib as PX
W = dfe.WARM; OUT = '/mnt/project-files/research/df1/checks/null/'
R = json.load(open(OUT + 'result.json')); PICKS = R['meta']['picks']; EX = R['meta']['bond_excess_removed_per_day']
SPEC = {'v1': DC.V1S, 'trend_only': ('F1', 3, 99.0, 'always', None, 200, .02), 'trend_vcap': ('F1', 3, .40, 'always', None, 200, .02)}
m = DC.market('dev250_path'); T = m['r'].shape[1]
m0 = dict(m); m0['rb'] = m['rb'] - EX['dev250_path']
ST = {k: (m['st_v1'] if k == 'v1' else PX.signal(m['ctx'], s)) for k, s in SPEC.items()}

def Lpre(st, sig, Lmax):
    Lon = np.minimum(float(Lmax), sig / np.maximum(m['vol20'], 1e-9))
    L = np.where(st >= 3, Lon, np.where(st >= 1, np.minimum(Lon, Lmax / 3.0), 0.0)); return np.where(np.isnan(L), 0.0, L)
def Lof(cfg):
    if cfg['fam'] == 'static': return np.full(m['r'].shape, cfg['w'])
    if cfg['fam'] == 'vt': return Lpre(np.full(m['r'].shape, 3.0), cfg['sig'], cfg['Lmax'])
    return Lpre(ST[cfg['fam'] if cfg['fam'] in ST else 'v1'], cfg['sig'], cfg['Lmax'])
def path(cfg, mm, **extra):
    kw = dict(RG.KNEES[cfg['knee']]); kw.update(step_lo=cfg['band'][0], step_hi=cfg['band'][1], vmode=cfg['vmode'], roff=RG.ROFF[cfg['roff']])
    if cfg.get('reb_every'): kw['reb_every'] = cfg['reb_every']
    kw.update(extra); o, _ = dfe.run(mm, Lof(cfg), **kw); return float(np.median(dfe.stats(o, T)[0]))

t0 = time.time(); out = {}
for pk, p in PICKS.items():
    lad = R['ladder'][pk]; pc = dict(fam='v1', **{k: p[k] for k in ('sig', 'Lmax', 'knee', 'roff', 'vmode', 'band')})
    pick = dict(path=lad['pick']['dev250_path']['cagr'], bondx0=path(pc, m0), cost2x=path(pc, m, cost=0.006), WD=lad['pick']['WD'],
                spx55=lad['pick']['real_spx_55_85']['cagr'], spx55_mdd=lad['pick']['real_spx_55_85']['dd'], ndx=lad['pick']['real_ndx_86_14']['cagr'])
    rows = []
    for x in R['naive']:
        if x['cfg']['fam'] == 'v1' or x['rows']['WD'] < p['tier'] - 1e-12: continue
        r = dict(id=x['cfg']['id'], fam=x['cfg']['fam'], WD=x['rows']['WD'], path=x['rows']['dev250_path']['cagr'], ndx=x['rows']['real_ndx_86_14']['cagr'],
                 spx29=x['rows']['real_spx_29_54']['cagr'], spx55=x['rows']['real_spx_55_85']['cagr'], spx55_mdd=x['rows']['real_spx_55_85']['dd'])
        if r['path'] < pick['path'] - 0.01: continue          # far below the pick on the headline: cannot dominate
        r['bondx0'] = path(x['cfg'], m0); r['cost2x'] = path(x['cfg'], m, cost=0.006)
        r['beats_all3'] = bool(r['path'] > pick['path'] and r['bondx0'] > pick['bondx0'] and r['cost2x'] > pick['cost2x'])
        r['WD_ge_pick'] = bool(r['WD'] >= pick['WD'] - 1e-12)
        rows.append(r)
    rows.sort(key=lambda r: -r['path'])
    dom = [r for r in rows if r['beats_all3']]
    out[pk] = dict(pick=pick, n_checked=len(rows), dominators_in_tier=dom, dominators_at_pick_WD=[r for r in dom if r['WD_ge_pick']], top_by_path=rows[:8])
    print('==', pk, p['id'], 'pick path %.4f bx0 %.4f c2x %.4f WD %.4f SPX55 %.4f/%.4f' % (pick['path'], pick['bondx0'], pick['cost2x'], pick['WD'], pick['spx55'], pick['spx55_mdd']))
    for r in rows[:8]:
        print('   %-30s WD %.4f path %.4f bx0 %.4f c2x %.4f NDX %.4f SPX29 %.4f SPX55 %.4f/%.4f all3 %s atWD %s' % (
            r['id'], r['WD'], r['path'], r['bondx0'], r['cost2x'], r['ndx'], r['spx29'], r['spx55'], r['spx55_mdd'], r['beats_all3'], r['WD_ge_pick']))
    print('   dominators in tier: %d, at pick WD: %d' % (len(dom), len(out[pk]['dominators_at_pick_WD'])), [r['id'] for r in dom[:6]])
json.dump(out, open(OUT + 'result_gates.json', 'w'), indent=1)
print('done %.0fs' % (time.time() - t0))
