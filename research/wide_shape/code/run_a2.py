"""WS1 A2 runner: stock top-K oracle map (O1 IC, O2 hit rate) for US500 and KRALL, h in {1,5,21}, K in {1,3,5,10,20}.
Output results/a2_<univ>_h<h>.json"""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/wide_shape/code')
import wsdata as D, wsstk as S

univ = sys.argv[1]; hs = [int(x) for x in sys.argv[2].split(',')]
RHO = [0, .02, .04, .06, .08, .10, .13, .16, .20, .25, .30, .40, .60, 1.0]
KS = [1, 3, 5, 10, 20]
PQ = {0.10: [.10, .15, .20, .30, .40, .60, .80, 1.0], 0.01: [.01, .02, .05, .10, .20, .40, .70, 1.0]}
NSEED = 8
t0 = time.time()
if univ == 'US500':
    U = D.load_us()
else:
    K_ = D.load_kr(); X_ = D.kr_derived(K_)
for h in hs:
    B = S.build_us(U, h) if univ == 'US500' else S.build_kr(K_, X_, h)
    out = {'univ': univ, 'h': h, 'nb': int(len(B.t_dec)), 'elig_mean': float(B.elig.sum(1).mean()),
           'first': str(B.dates[0].date()), 'last': str(B.dates[-1].date()), 'O1': {}, 'O2': {}}
    print(univ, h, out['nb'], out['elig_mean'], '%.0fs' % (time.time() - t0), flush=True)
    for rho in RHO:
        cell = {K: [] for K in KS}; ic = None
        for sd in range(NSEED):
            rng = np.random.default_rng(100 + sd)
            s = rho * B.z + np.sqrt(max(0.0, 1 - rho * rho)) * rng.standard_normal(B.z.shape)
            s = np.where(B.elig, s, np.nan)
            if sd == 0:
                ic = S.spearman_ic(B, s) if rho < 1 else (1.0, 0.0, 0)
            pk = S.topk_from_signal(s, 20)
            for K in KS:
                r, g, c = S.run_picks(B, pk[:, :K])
                re, rs, p10 = S.perf(B, r)
                cell[K].append((re, rs, p10, float(g.mean() * 252 / h), float(c.mean() * 252 / h)))
        out['O1'][str(rho)] = {'ic': ic[0], 'ic_t': ic[1],
                               'K': {str(K): {'real': float(np.median([x[0] for x in v])), 'res': float(np.median([x[1] for x in v])),
                                              'res_p10': float(np.median([x[2] for x in v])), 'gross_yr': float(np.median([x[3] for x in v])),
                                              'cost_yr': float(np.median([x[4] for x in v]))} for K, v in cell.items()}}
        print(' O1 rho %.2f ic %.3f ' % (rho, ic[0]) + ' '.join('K%s %.3f/%.3f' % (K, d['real'], d['res']) for K, d in out['O1'][str(rho)]['K'].items()),
              '%.0fs' % (time.time() - t0), flush=True)
    for q, pg in PQ.items():
        m = np.ceil(q * B.n).astype(int)
        top = B.elig & (B.rk >= (B.n - m)[:, None])
        for p in pg:
            cell = {K: [] for K in KS}
            for sd in range(NSEED):
                pk = S.picks_o2(top, B.elig, 20, p, 200 + sd)
                for K in KS:
                    r, g, c = S.run_picks(B, pk[:, :K])
                    re, rs, p10 = S.perf(B, r)
                    cell[K].append((re, rs, p10))
            out['O2']['%g_%g' % (q, p)] = {str(K): {'real': float(np.median([x[0] for x in v])), 'res': float(np.median([x[1] for x in v]))}
                                           for K, v in cell.items()}
            print(' O2 q %.2f p %.2f ' % (q, p) + ' '.join('K%s %.3f/%.3f' % (K, d['real'], d['res']) for K, d in out['O2']['%g_%g' % (q, p)].items()),
                  '%.0fs' % (time.time() - t0), flush=True)
    json.dump(out, open('/mnt/project-files/research/wide_shape/results/a2_%s_h%d.json' % (univ, h), 'w'), indent=1)
