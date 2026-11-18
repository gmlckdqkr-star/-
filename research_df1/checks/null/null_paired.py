"""Check 'null' part 3: paired per-path comparison on dev250_path (500 bootstrap paths, NON-ACTUAL) of each pick vs its
always-on twin (same sigma/Lmax/knee/bond/structure, v1 state removed) and vs the best naive config at the pick's tier.
Merges result_gates.json + paired stats into result.json. <=2014 only."""
import sys, os, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/df1/code')
import dfctx as DC, dfe, run_grid as RG
OUT = '/mnt/project-files/research/df1/checks/null/'
R = json.load(open(OUT + 'result.json')); PICKS = R['meta']['picks']
m = DC.market('dev250_path'); T = m['r'].shape[1]
def run(st, sig, Lmax, knee, vmode, roff='RB'):
    Lon = np.minimum(Lmax, sig / np.maximum(m['vol20'], 1e-9)); L = np.where(st >= 3, Lon, np.where(st >= 1, np.minimum(Lon, Lmax / 3.0), 0.0))
    L = np.where(np.isnan(L), 0.0, L); kw = dict(RG.KNEES[knee]); kw.update(vmode=vmode, roff=RG.ROFF[roff])
    o, _ = dfe.run(m, L, **kw); return dfe.stats(o, T)
on = np.full(m['r'].shape, 3.0); P = {}
for pk, p in PICKS.items():
    cp, dp = run(m['st_v1'], p['sig'], p['Lmax'], p['knee'], p['vmode']); ca, da = run(on, p['sig'], p['Lmax'], p['knee'], p['vmode'])
    P[pk] = dict(vs_always_on=dict(win_rate_cagr=float(np.mean(cp > ca)), med_diff_cagr=float(np.median(cp - ca)), win_rate_mdd=float(np.mean(dp > da)),
                                   med_diff_mdd=float(np.median(dp - da)), p10_cagr_pick=float(np.percentile(cp, 10)), p10_cagr_on=float(np.percentile(ca, 10))))
    print(pk, P[pk])
if os.path.exists(OUT + 'result_gates.json'):
    R['naive_gates'] = json.load(open(OUT + 'result_gates.json')); os.remove(OUT + 'result_gates.json')
R['paired_dev250'] = P
json.dump(R, open(OUT + 'result.json', 'w'), indent=1)
