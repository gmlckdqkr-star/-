"""WS1 sensitivity (verifier 11-04): KR failure-delisting classification. 'lenient' treats ambiguous reasons
(wsdata.FAIL_AMBIG: 해산 사유 발생, 존속기간 만료, 자진등록취소, 등록법인의 취소신청, 주된영업의 양도, 기타 등록취소) as
non-failure (exit at the last price) instead of -100%. Recomputes, for both modes, KRALL h21: O1 oracle K5/K20 need, main
signals (LVOL, MAXL, COMBO7, COMBO13, MOM) and the registered C composite. Map only, not a candidate."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/wide_shape/code')
import wsdata as D, wsstk as S
RD = '/mnt/project-files/research/wide_shape/results/'
src = open('/mnt/project-files/research/wide_shape/code/run_b.py').read().split("t0 = time.time()")[0]
ns = {}; exec(src.replace("univ = sys.argv[1]; hs = [int(x) for x in sys.argv[2].split(',')]", "univ='KRALL'; hs=[]"), ns)
K_ = D.load_kr(); X_ = D.kr_derived(K_); SIG = ns['signals_kr'](K_, X_)
base = ['REV1', 'REV5', 'REV21', 'MOM', 'HI52', 'MAXL', 'LVOL', 'VSHK', 'SIZE', 'CLV', 'GAP', 'LIMUP', 'ILLQ']
creg = json.load(open(RD + 'c_registered.json'))['KRALL_h21']['signals']
RHO = [0, .02, .04, .06, .08, .10, .13, .16, .20, .30]
out = {}
for mode in ('conservative', 'lenient'):
    B = S.build_kr(K_, X_, 21, fail_mode=mode)
    o = {'O1': {}, 'B': {}}
    for rho in RHO:
        cell = {5: [], 20: []}; ic = None
        for sd in range(8):
            rng = np.random.default_rng(100 + sd)
            s = np.where(B.elig, rho * B.z + np.sqrt(1 - rho * rho) * rng.standard_normal(B.z.shape), np.nan)
            if sd == 0:
                ic = S.spearman_ic(B, s)[0]
            pk = S.topk_from_signal(s, 20)
            for K in (5, 20):
                r, g, c = S.run_picks(B, pk[:, :K]); re, rs, _ = S.perf(B, r); cell[K].append(min(re, rs))
        o['O1'][str(rho)] = {'ic': ic, 'K5': float(np.median(cell[5])), 'K20': float(np.median(cell[20]))}
    P = {nm: ns['pct_rank_rows'](np.where(B.elig, SIG[nm][B.t_dec], np.nan)) for nm in base}
    P['COMBO7'] = np.nanmean(np.stack([P[nm] for nm in base[:7]]), 0)
    P['COMBO13'] = np.nanmean(np.stack([P[nm] for nm in base]), 0)
    P['C_REG'] = np.nanmean(np.stack([P[nm] for nm in creg]), 0)
    for nm in ('LVOL', 'MAXL', 'MOM', 'COMBO7', 'COMBO13', 'C_REG'):
        s = np.where(B.elig, P[nm], np.nan) + 1e-9 * np.random.default_rng(7).standard_normal(B.z.shape)
        d = {'ic': S.spearman_ic(B, s)[0]}; pk = S.topk_from_signal(s, 20)
        for K in (5, 20):
            r, g, c = S.run_picks(B, pk[:, :K]); re, rs, _ = S.perf(B, r); d['K%d' % K] = re; d['K%d_res' % K] = rs
        o['B'][nm] = d
    out[mode] = o
    print(mode, json.dumps(o['B']), flush=True)
    print(mode, 'O1', ' '.join('%s:%.3f/%.2f/%.2f' % (k, v['ic'], v['K5'], v['K20']) for k, v in o['O1'].items()), flush=True)
json.dump(out, open(RD + 'sens_lenient.json', 'w'), indent=1)
