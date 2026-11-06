import json, numpy as np, ac3
B = ac3.prep()
def shift(a): return np.ascontiguousarray(np.concatenate([a[:, :1], a[:, :-1]], axis=1))
res = {}
cands = [('PICK Z.25/I.75', .25, .75, 0), ('Z.50/I.50', .5, .5, 0), ('Z only', 1, 0, 0), ('ISA only', 0, 1, 0)]
V = [('base', {}), ('ISA tax optimistic (final, 200만)', dict(imode=0)), ('cost 0.4% both', dict(ccost=.004, icost=.004)),
     ('ISA product drag +1%/yr', dict(ier=.0345)), ('ISA cost 0.13% (real KR)', dict(icost=.0013))]
for W in (1e7, 3e7, 1e8):
    for nm, z, i, f in cands:
        for vn, kw in V:
            key = 'W%d|%s|%s' % (W / 1e6, nm, vn); res[key] = {}
            for bn in B:
                r, _ = ac3.run(bn, z, i, f, W=W, rule=1, isa_own=1, **kw); res[key][bn] = r
            p = res[key]['dev250_path']
            print('%-58s path %.3f dd80 %.3f p10 %.3f | NDX %.3f SPX55 %.3f SPX70 %.3f' % (key, p['cagr'], p['dd80'], p['p10'], res[key]['real_ndx_86_14']['cagr'],
                  res[key]['real_spx_55_85']['cagr'], res[key]['real_spx_70_85']['cagr']), flush=True)
# delay +1 (all accounts execute one day later)
saved = {bn: (b['L'], b['LI'], b['LIown']) for bn, b in B.items()}
for bn, b in B.items(): b['L'], b['LI'], b['LIown'] = shift(b['L']), shift(b['LI']), shift(b['LIown'])
for nm, z, i, f in cands:
    key = 'W10|%s|delay+1' % nm; res[key] = {}
    for bn in B:
        r, _ = ac3.run(bn, z, i, f, W=1e7, rule=1, isa_own=1); res[key][bn] = r
    p = res[key]['dev250_path']
    print('%-58s path %.3f dd80 %.3f p10 %.3f | NDX %.3f SPX55 %.3f SPX70 %.3f' % (key, p['cagr'], p['dd80'], p['p10'], res[key]['real_ndx_86_14']['cagr'],
          res[key]['real_spx_55_85']['cagr'], res[key]['real_spx_70_85']['cagr']), flush=True)
for bn, b in B.items(): b['L'], b['LI'], b['LIown'] = saved[bn]
# futures-only at large capital, for the record (gap test: 1 day -30% x exposure)
for W in (1e8, 3e8, 1e9):
    key = 'W%d|F only' % (W / 1e6); res[key] = {}
    for bn in B:
        r, _ = ac3.run(bn, 0, 0, 1, W=W, rule=1); res[key][bn] = r
    zk = {bn: ac3.run(bn, 1, 0, 0, W=W, rule=1)[0]['cagr'] for bn in B}
    p = res[key]['dev250_path']
    print('%-30s path %.3f (Z-only same W %.3f) dd80 %.3f negpaths %d maxlev %.2f gap(-30%%) left %.0f%% | NDX %.3f (Z %.3f) SPX55 %.3f (Z %.3f)' % (
        key, p['cagr'], zk['dev250_path'], p['dd80'], p['F_negpaths'], p['F_maxlev_max'], 100 * (1 - 0.3 * p['F_maxlev_max']),
        res[key]['real_ndx_86_14']['cagr'], zk['real_ndx_86_14'], res[key]['real_spx_55_85']['cagr'], zk['real_spx_55_85']), flush=True)
json.dump(res, open('/mnt/project-files/research/acct3/results/stress.json', 'w'), indent=0)
