# ISA leg with product facts (KODEX 409820 H: implied drag ~0.9%/yr incl. hedge, t4_krdrag.py), KR session executes ~half a US day
# after the US-close decision (delay 2 = same as 종합), KR trading cost 0.15%/side. Re-select the split with the same rule.
import json, numpy as np, ac3, std, bk, rx
B = ac3.prep(); PP = ac3.PP
VAR = {'model(보수)': dict(dl=3, ic=.003, er=.0245), '실제형 A (지연2, 0.15%, 0.9%)': dict(dl=2, ic=.0015, er=.009),
       '실제형 B (지연3, 0.15%, 0.9%)': dict(dl=3, ic=.0015, er=.009), '실제형 C (지연2, 0.3%, 1.5%)': dict(dl=2, ic=.003, er=.015)}
ctx = std.contexts(); out = {}
for vn, v in VAR.items():
    for bn, c in ctx.items():
        Bs = np.ascontiguousarray(bk.C3sig(c), dtype=np.float64); feat = np.ascontiguousarray(bk.features(c))
        L2, _ = ac3.levels2(B[bn]['R'], B[bn]['RF'], Bs, feat, v['dl'], v['ic'], 0.099, 0.0, 0, PP['hthr'], PP['cspr'], v['er'], PP['step'],
                            ac3.av23sL, ac3.bp23, 0.1)
        B[bn]['LIown'] = np.ascontiguousarray(L2 * 1.5)
    for W in (1e7, 3e7, 1e8):
        for zi in range(5):
            z = zi / 4; key = '%s|W%d|Z%.2f/I%.2f' % (vn, W / 1e6, z, 1 - z); out[key] = {}
            for bn in B:
                r, _ = ac3.run(bn, z, 1 - z, 0, W=W, rule=1, isa_own=1, icost=v['ic'], ier=v['er']); out[key][bn] = r
            p = out[key]['dev250_path']
            print('%-44s path %.3f dd80 %.3f p10 %.3f | glued %.3f NDX %.3f SPX55 %.3f SPX70 %.3f' % (key, p['cagr'], p['dd80'], p['p10'],
                  out[key]['dev250_glued']['cagr'], out[key]['real_ndx_86_14']['cagr'], out[key]['real_spx_55_85']['cagr'],
                  out[key]['real_spx_70_85']['cagr']), flush=True)
json.dump(out, open('/mnt/project-files/research/acct3/results/isa_real.json', 'w'), indent=0)
