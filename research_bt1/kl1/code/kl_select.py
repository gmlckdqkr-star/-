"""KL1 selection statistics per family (PRECOMMIT_KL1 sec.7): dedup, Hansen SPA / Romano-Wolf / DSR / Li-Ji effective N,
deflated advantage, null max-t of the singles-only subset (how the bar moved with N), frozen top-20 (corr <= 0.98).
Uses only the selection-period D matrices. Writes results/select_<fam>.json and results/top20_<fam>.json."""
import os, sys, json, time, hashlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wsdata as WD, kl_stats as ST, kl_gen as G
CACHE = WD.CACHE; RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
N_TOTAL = 557468
MIN_ACT = {'S2KR': 750, 'S2US': 1260}


def null_max_q(D, qs=(0.5, 0.95)):
    """bootstrap null distribution of max studentized centered mean (= SPA upper / RW first step) for a subset."""
    N, T = D.shape
    W = ST.stationary_counts(T)
    s1 = np.zeros(N); s2 = np.zeros(N); ch = 20000
    for i in range(0, N, ch):
        Mb = (W @ D[i:i + ch].T).astype(np.float64) / T
        s1[i:i + ch] = Mb.sum(0); s2[i:i + ch] = (Mb ** 2).sum(0)
    om = np.sqrt(np.maximum(s2 / ST.B - (s1 / ST.B) ** 2, 0) * T); om = np.where(om > 1e-10, om, np.inf)
    dbar = D.mean(1); Tu = np.zeros(ST.B)
    for i in range(0, N, ch):
        Mb = (W @ D[i:i + ch].T).astype(np.float64) / T
        Tu = np.maximum(Tu, ((Mb - dbar[i:i + ch]) * (np.sqrt(T) / om[i:i + ch])).max(1))
    return [float(np.quantile(Tu, q)) for q in qs]


def describe(fam, row):
    return dict(fam=fam, row=[int(x) for x in row])


def main(fam):
    t0 = time.time()
    D = np.load(CACHE + 'D_%s.npy' % fam); S = np.load(CACHE + 'stat_%s.npy' % fam); rows = np.load(CACHE + 'gen_%s.npy' % fam)
    N = len(D)
    h = np.array([hashlib.sha1(D[k].tobytes()).hexdigest() for k in range(N)])
    _, first = np.unique(h, return_index=True); uniq = np.sort(first)
    zero = np.all(D[uniq] == 0, axis=1); keep = uniq[~zero]
    Dk = np.ascontiguousarray(D[keep].astype(np.float32))
    print(fam, 'N', N, 'unique', len(uniq), 'zero', int(zero.sum()), 'kept', len(keep), flush=True)
    res, aux = ST.spa_rw(Dk, verbose=False)
    print(fam, 'SPA', {k: v for k, v in res.items() if k != 'rw_crit'}, '%.0fs' % (time.time() - t0), flush=True)
    nz = Dk != 0
    fm = np.where(nz.any(1), nz.argmax(1), Dk.shape[1])
    sr = np.full(len(keep), np.nan)
    for j in range(len(keep)):
        x = Dk[j, fm[j]:]
        if len(x) > 24 and x.std() > 0:
            sr[j] = x.mean() / x.std(ddof=1)
    sr_var = float(np.nanvar(sr))
    meff, nok, lam = ST.lij_meff(Dk)
    # how the bar moved: singles-only subset (original small grid)
    if fam.startswith('S2'):
        sing = np.flatnonzero(rows[keep, 3] == 0)
    elif fam.startswith('S1'):
        sing = np.flatnonzero(rows[keep, 0] == 0)
    else:
        sing = np.flatnonzero(keep < 2000)
    nq_sing = null_max_q(np.ascontiguousarray(Dk[sing])) if len(sing) > 10 else None
    # ranking
    adv = Dk.mean(1) * 12
    if fam.startswith('S2'):
        okr = S[keep, 1] >= MIN_ACT[fam]
    else:
        okr = S[keep, 3] >= 48
    cand = np.flatnonzero(okr)
    order = cand[np.argsort(-adv[cand])]
    Z, okz = ST.standardize(Dk)
    chosen = []
    for j in order:
        if len(chosen) >= 20:
            break
        if not okz[j]:
            continue
        if chosen and float(np.max(Z[chosen] @ Z[j])) > 0.98:
            continue
        chosen.append(j)
    top = []
    for rk, j in enumerate(chosen):
        x = Dk[j, fm[j]:]
        d = {lab: ST.dsr(x, sr_var, n)[0] for lab, n in (('N_family', N), ('N_total', N_TOTAL), ('N_eff_lij', max(2, int(round(meff)))))}
        dd = ST.dsr(x, sr_var, N_TOTAL)
        top.append(dict(rank=rk + 1, kid=int(keep[j]), row=[int(v) for v in rows[keep[j]]], raw_adv_ann=float(adv[j]),
                        tstat=float(aux['tstat'][j]), rw_reject=bool(aux['rw_rej'][j]),
                        defl_adv_q50=float((aux['dbar'][j] - res['maxnull_q50'] * aux['om'][j] / np.sqrt(res['T'])) * 12),
                        defl_adv_q95=float((aux['dbar'][j] - res['maxnull_q95'] * aux['om'][j] / np.sqrt(res['T'])) * 12),
                        sr_m=dd[1], sr0_Ntotal=dd[2], dsr=d, stat=[float(v) for v in S[keep[j]]]))
    jt = int(np.argmax(np.where(aux['good'], aux['tstat'], -np.inf)))
    out = dict(fam=fam, N_generated=N, N_unique=int(len(uniq)), N_zero=int(zero.sum()), N_kept=int(len(keep)), N_rank_eligible=int(len(cand)),
               months=int(D.shape[1]), spa={k: v for k, v in res.items() if k != 'rw_crit'}, rw_crit_first=res['rw_crit'][:3],
               p_bonferroni6=min(1.0, 6 * res['p_c']), sr_var=sr_var, meff_lij=meff,
               singles_subset=dict(n=int(len(sing)), null_max_t_q50_q95=nq_sing),
               best_t=dict(kid=int(keep[jt]), row=[int(v) for v in rows[keep[jt]]], tstat=float(aux['tstat'][jt]), raw_adv_ann=float(adv[jt])),
               top20=top, secs=time.time() - t0)
    json.dump(out, open(os.path.join(RES, 'select_%s.json' % fam), 'w'), indent=1, default=float)
    json.dump(dict(fam=fam, top20=[dict(rank=t['rank'], kid=t['kid'], row=t['row'], raw_adv_ann=t['raw_adv_ann']) for t in top]),
              open(os.path.join(RES, 'top20_%s.json' % fam), 'w'), indent=1)
    print(fam, 'done', '%.0fs' % (time.time() - t0), 'top1 raw adv %.4f t %.2f defl %.4f' % (top[0]['raw_adv_ann'], top[0]['tstat'], top[0]['defl_adv_q50']) if top else '', flush=True)


if __name__ == '__main__':
    for f in sys.argv[1:]:
        main(f)
