# Like-for-like: both products at their measured drag (TQQQ ~1.9%/yr, KODEX 409820 H ~0.9%/yr; t4_krdrag.py), ISA delay 2, KR cost 0.15%.
import json, numpy as np, ac3, std, bk
B = ac3.prep(); PP = ac3.PP; out = {}
for bn, c in std.contexts().items():
    Bs = np.ascontiguousarray(bk.C3sig(c), dtype=np.float64); feat = np.ascontiguousarray(bk.features(c))
    L2, _ = ac3.levels2(B[bn]['R'], B[bn]['RF'], Bs, feat, 2, .0015, 0.099, 0.0, 0, PP['hthr'], PP['cspr'], .009, PP['step'], ac3.av23sL, ac3.bp23, 0.1)
    B[bn]['LIown'] = np.ascontiguousarray(L2 * 1.5)
PP['er3'] = 0.019
for W in (1e7, 3e7, 1e8):
    for zi in range(5):
        z = zi / 4; key = 'W%d|Z%.2f/I%.2f' % (W / 1e6, z, 1 - z); out[key] = {}
        for bn in B:
            r, _ = ac3.run(bn, z, 1 - z, 0, W=W, rule=1, isa_own=1, icost=.0015, ier=.009); out[key][bn] = r
        p = out[key]['dev250_path']
        print('%-16s path %.3f dd80 %.3f p10 %.3f | glued %.3f NDX %.3f SPX55 %.3f SPX70 %.3f' % (key, p['cagr'], p['dd80'], p['p10'],
              out[key]['dev250_glued']['cagr'], out[key]['real_ndx_86_14']['cagr'], out[key]['real_spx_55_85']['cagr'], out[key]['real_spx_70_85']['cagr']), flush=True)
json.dump(out, open('/mnt/project-files/research/acct3/results/both_real.json', 'w'), indent=0)
