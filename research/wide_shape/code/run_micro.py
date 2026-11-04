"""WS1 sensitivity (addendum 1): KR small-seed micro universe, ADV20 >= 20M KRW. A2 O1 (K 5,20; h 5,21) + B (COMBO13, LVOL, MOM)."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/wide_shape/code')
import wsdata as D, wsstk as S
src = open('/mnt/project-files/research/wide_shape/code/run_b.py').read().split("t0 = time.time()")[0]
ns = {}; exec(src.replace("univ = sys.argv[1]; hs = [int(x) for x in sys.argv[2].split(',')]", "univ='KRALL'; hs=[]"), ns)
K_ = D.load_kr(); X_ = D.kr_derived(K_); SIG = ns['signals_kr'](K_, X_)
RHO = [0, .02, .04, .06, .08, .10, .13, .16, .20, .30]
out = {}
for h in (21, 5):
    B = S.build_kr(K_, X_, h, adv_min=2e7)
    o = {'elig_mean': float(B.elig.sum(1).mean()), 'O1': {}, 'B': {}}
    for rho in RHO:
        cell = {5: [], 20: []}; ic = None
        for sd in range(6):
            rng = np.random.default_rng(100 + sd)
            s = np.where(B.elig, rho * B.z + np.sqrt(1 - rho * rho) * rng.standard_normal(B.z.shape), np.nan)
            if sd == 0: ic = S.spearman_ic(B, s)[0]
            pk = S.topk_from_signal(s, 20)
            for K in (5, 20):
                r, g, c = S.run_picks(B, pk[:, :K]); re, rs, _ = S.perf(B, r); cell[K].append(min(re, rs))
        o['O1'][str(rho)] = {'ic': ic, 'K5': float(np.median(cell[5])), 'K20': float(np.median(cell[20]))}
        print('micro h%d rho %.2f ic %.3f K5 %.3f K20 %.3f' % (h, rho, ic, o['O1'][str(rho)]['K5'], o['O1'][str(rho)]['K20']), flush=True)
    base = ['REV1', 'REV5', 'REV21', 'MOM', 'HI52', 'MAXL', 'LVOL', 'VSHK', 'SIZE', 'CLV', 'GAP', 'LIMUP', 'ILLQ']
    P = {nm: ns['pct_rank_rows'](np.where(B.elig, SIG[nm][B.t_dec], np.nan)) for nm in base}
    P['COMBO13'] = np.nanmean(np.stack([P[nm] for nm in base]), 0)
    for nm in ('COMBO13', 'LVOL', 'MOM'):
        s = np.where(B.elig, P[nm], np.nan) + 1e-9 * np.random.default_rng(7).standard_normal(B.z.shape)
        ic = S.spearman_ic(B, s)[0]; pk = S.topk_from_signal(s, 20); d = {'ic': ic}
        for K in (5, 20):
            r, g, c = S.run_picks(B, pk[:, :K]); re, rs, _ = S.perf(B, r); d['K%d' % K] = min(re, rs)
        o['B'][nm] = d
        print('micro h%d %s ic %.3f K5 %.3f K20 %.3f' % (h, nm, ic, d['K5'], d['K20']), flush=True)
    out['h%d' % h] = o
json.dump(out, open('/mnt/project-files/research/wide_shape/results/micro_kr.json', 'w'), indent=1)
