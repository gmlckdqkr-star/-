"""WS1 C (registered): KRALL h21 / h5 composite of signals with first-half (1999-2006) IC>0, rank average, top-K.
Pass = IC_B >= 0.5 IC_A, 30y resample median > 24.2%, second-half real CAGR > 0."""
import sys, json, numpy as np
sys.path.insert(0, '/mnt/project-files/research/wide_shape/code')
import wsdata as D, wsstk as S
import importlib.util
spec = importlib.util.spec_from_file_location('rb', '/mnt/project-files/research/wide_shape/code/run_b.py')
RD = '/mnt/project-files/research/wide_shape/results/'
K_ = D.load_kr(); X_ = D.kr_derived(K_)
# reuse signal builders from run_b without running its main loop
src = open('/mnt/project-files/research/wide_shape/code/run_b.py').read().split("t0 = time.time()")[0]
ns = {}
exec(src.replace("univ = sys.argv[1]; hs = [int(x) for x in sys.argv[2].split(',')]", "univ='KRALL'; hs=[]"), ns)
SIG = ns['signals_kr'](K_, X_)
out = {}
for h in (21, 5):
    b = json.load(open(RD + 'b_KRALL_h%d.json' % h))
    use = [nm for nm, d in b['signals'].items() if not nm.startswith('COMBO') and d['ic_A'] > 0]
    B = S.build_kr(K_, X_, h)
    split = b['split_block']
    P = np.nanmean(np.stack([ns['pct_rank_rows'](np.where(B.elig, SIG[nm][B.t_dec], np.nan)) for nm in use]), 0)
    s = np.where(B.elig, P, np.nan) + 1e-9 * np.random.default_rng(7).standard_normal(P.shape)
    res = {'signals': use}
    for part, sl in (('A', slice(0, split)), ('B', slice(split, None)), ('all', slice(None))):
        Bp = S.Blocks(); Bp.elig = B.elig[sl]; Bp.rk = B.rk[sl]
        res['ic_' + part] = S.spearman_ic(Bp, s[sl])[0]
    pk = S.topk_from_signal(s, 20)
    for K in (20, 5):
        r, g, c = S.run_picks(B, pk[:, :K])
        re, rs, p10 = S.perf(B, r)
        BA = S.Blocks(); BA.h = h; BA.years = B.years[:split]; BA.tax = False
        BB = S.Blocks(); BB.h = h; BB.years = B.years[split:]; BB.tax = False
        res['K%d' % K] = dict(real=re, res_med=rs, res_p10=p10, real_A=S.perf(BA, r[:split])[0], real_B=S.perf(BB, r[split:])[0],
                              gross_yr=float(g.mean() * 252 / h), cost_yr=float(c.mean() * 252 / h))
    k20 = res['K20']
    res['pass'] = bool(res['ic_B'] >= 0.5 * res['ic_A'] and k20['res_med'] > 0.242 and k20['real_B'] > 0)
    out['KRALL_h%d' % h] = res
    print(h, json.dumps(res, ensure_ascii=False))
json.dump(out, open(RD + 'c_registered.json', 'w'), indent=1)
