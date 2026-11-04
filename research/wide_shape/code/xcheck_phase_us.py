import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/mnt/project-files/research/wide_shape/code')
import wsdata as D, wsstk as S
src = open('/mnt/project-files/research/wide_shape/code/run_b.py').read().split("t0 = time.time()")[0]
ns = {}; exec(src.replace("univ = sys.argv[1]; hs = [int(x) for x in sys.argv[2].split(',')]", "univ='US500'; hs=[]"), ns)
U = D.load_us(); SIG = ns['signals_us'](U)
d0 = U['dates']; i0 = int(np.searchsorted(d0.values, np.datetime64('1971-01-01')))
out = {}
for nm in ('MOM', 'LVOL'):
    v5, v20 = [], []
    for off in range(0, 21, 2):
        B = S.build_us(U, 21, start=str(pd.Timestamp(d0[i0 + off]).date()))
        s = np.where(B.elig, SIG[nm][B.t_dec], np.nan) + 1e-12 * np.random.default_rng(7).standard_normal(B.elig.shape)
        pk = S.topk_from_signal(s, 20)
        for K, v in ((5, v5), (20, v20)):
            r, g, c = S.run_picks(B, pk[:, :K]); v.append(S.perf(B, r)[0])
    out[nm] = {'K5': v5, 'K20': v20}
    print(nm, 'K5 phases min %.3f med %.3f max %.3f' % (min(v5), np.median(v5), max(v5)), '| K20 min %.3f med %.3f max %.3f' % (min(v20), np.median(v20), max(v20)), flush=True)
json.dump(out, open('/mnt/project-files/research/wide_shape/results/xcheck_phase_us.json', 'w'), indent=1)
