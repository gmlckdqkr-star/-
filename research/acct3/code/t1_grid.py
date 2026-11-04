import json, itertools, numpy as np, ac3
B = list(ac3.prep())
combos = [(z / 4, i / 4, (4 - z - i) / 4) for z in range(5) for i in range(5 - z)]
res = {}
# single-account refs per W (s0.85 in 종합 only, ISA only unlimited-check)
for W in (1e7, 3e7, 1e8):
    for own in (1, 0):
     for rule in (0, 1):
      for (wZ, wI, wF) in combos:
            key = 'W%d_R%d_O%d_Z%.2f_I%.2f_F%.2f' % (W / 1e6, rule, own, wZ, wI, wF); res[key] = {}
            for bn in B:
                r, _ = ac3.run(bn, wZ, wI, wF, W=W, rule=rule, isa_own=own); res[key][bn] = r
            p = res[key]['dev250_path']
            print('%-32s path=%.3f dd80=%.3f p10=%.3f d=%+.3f | NDX=%.3f SPX55=%.3f SPX70=%.3f%s' % (key, p['cagr'], p['dd80'], p['p10'], p['d_vs_s085'],
                  res[key]['real_ndx_86_14']['cagr'], res[key]['real_spx_55_85']['cagr'], res[key]['real_spx_70_85']['cagr'],
                  (' | F dd80=%.2f neg=%d maxlev=%.1f' % (p['F_dd80'], p['F_negpaths'], p['F_maxlev_max'])) if wF > 0 else ''), flush=True)
json.dump(res, open('/mnt/project-files/research/acct3/results/grid.json', 'w'), indent=0)
