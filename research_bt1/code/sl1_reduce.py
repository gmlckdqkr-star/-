"""SL1 reduce (copy of bt1_reduce: SL1 shards, sleeve-aware rule text). BT1 reduce (ADDENDUM_BT1_1 sec.3): merge all finished shards -> SPA (consistent/lower/upper), Romano-Wolf stepdown,
Li-Ji effective N, DSR inputs, unique count, frozen top-20 (pre-registered ranking: active-day advantage, >= 1260 active
discovery days, distinct streams) and secondary top-20 by t. Discovery data only (<=1999)."""
import os, sys, glob, json, time, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt1_mega as BM, m1_stats as ST, sl1_mega as SL
SCR = BM.SCR


def main():
    t0 = time.time()
    fs = sorted(glob.glob(SCR + 'out/sl1_shards/' + 's[0-9][0-9][0-9][0-9].npz'))
    B = 1000; T = None
    Tc = np.full(B, -np.inf); Tl = Tc.copy(); Tu = Tc.copy()
    topv = None; topk = None; G = None; nG = 0; tmax = -np.inf; srs = srs2 = 0.0; srn = 0; nzero = ngood = 0; N = 0
    forms = np.zeros(5, np.int64); Hs = []; C = {k: [] for k in ('c_id', 'c_adv', 'c_t', 'c_dbar', 'c_om', 'c_row', 'c_D', 'c_S')}
    shards = []
    for f in fs:
        z = np.load(f); shards.append(int(os.path.basename(f)[1:5]))
        Tc = np.maximum(Tc, z['Tc']); Tl = np.maximum(Tl, z['Tl']); Tu = np.maximum(Tu, z['Tu'])
        if topv is None: topv, topk = z['topv'], z['topk']
        else:
            av = np.concatenate([topv, z['topv']], 1); ak = np.concatenate([topk, z['topk']], 1)
            o = np.argsort(-av, 1)[:, :BM.TOPM]; topv = np.take_along_axis(av, o, 1); topk = np.take_along_axis(ak, o, 1)
        G = z['G'].copy() if G is None else G + z['G']; nG += int(z['nG'])
        tmax = max(tmax, float(z['tmax'])); srs += float(z['srs']); srs2 += float(z['srs2']); srn += int(z['srn'])
        nzero += int(z['nzero']); ngood += int(z['ngood']); N += int(z['n']); forms += z['forms']
        Hs.append(z['H'])
        for k in C: C[k].append(z[k])
    C = {k: np.concatenate(v) for k, v in C.items()}
    T = G.shape[0]
    H = np.concatenate(Hs); nuniq = int(len(np.unique(H)))
    Tspa = max(0.0, tmax)
    Tc0 = np.maximum(Tc, 0); Tl0 = np.maximum(Tl, 0); Tu0 = np.maximum(Tu, 0)
    spa = dict(T=T, N=N, Tspa=Tspa, p_c=float(np.mean(Tc0 >= Tspa)), p_l=float(np.mean(Tl0 >= Tspa)), p_u=float(np.mean(Tu0 >= Tspa)),
               maxnull_q50=float(np.median(Tu0)), maxnull_q95=float(np.quantile(Tu0, 0.95)))
    # Romano-Wolf stepdown (studentized max-t) with per-replicate top-50
    t_by_id = dict(zip(C['c_id'].tolist(), C['c_t'].tolist()))
    rej = set(); crit = []; spa['rw_capped'] = False
    while True:
        mx = np.empty(B)
        for b in range(B):
            j = 0
            while j < topv.shape[1] and int(topk[b, j]) in rej: j += 1
            mx[b] = topv[b, j] if j < topv.shape[1] else -np.inf     # more rejections than TOPM -> recorded below
        if np.isneginf(mx).any():
            spa['rw_capped'] = True; break
        cc = float(np.quantile(mx, 0.95)); crit.append(cc)
        new = {i for i, t in t_by_id.items() if t > cc and i not in rej}
        if not new: break
        rej |= new
    spa.update(rw_n=len(rej), rw_crit=crit)
    lam = np.clip(np.linalg.eigvalsh(G), 0, None); meff = float(np.sum((lam >= 1).astype(float) + (lam - np.floor(lam))))
    sr_mean = srs / srn; sr_var = srs2 / srn - sr_mean ** 2
    # pre-registered ranking among eligible candidates, distinct streams
    hD = (C['c_D'].view(np.uint32).astype(np.uint64) * np.random.default_rng(7).integers(1, 2**62, size=T, dtype=np.uint64)).sum(1)
    def topdistinct(score, k):
        o = np.argsort(-score); seen = set(); out = []
        for j in o:
            if not np.isfinite(score[j]): break
            if hD[j] in seen: continue
            seen.add(hD[j]); out.append(j)
            if len(out) == k: break
        return out
    def rowinfo(j, rank):
        x = C['c_D'][j]; nz = np.flatnonzero(x != 0); x = x[nz[0]:] if len(nz) else x
        d = {lab: ST.dsr(x, sr_var, n)[0] for lab, n in (('N_total', N), ('N_unique', nuniq), ('N_lij', max(2, int(round(meff)))))}
        dd = ST.dsr(x, sr_var, N)
        S = C['c_S'][j]; act = S[1] + S[5]
        return dict(rank=rank, id=int(C['c_id'][j]), rule=SL.describe(AM, C['c_row'][j], NAMES), row=C['c_row'][j].tolist(),
                    adv_active=float(C['c_adv'][j]), adv_spx=float(S[0] / max(S[1], 1) * 252), adv_ndx=float(S[4] / max(S[5], 1) * 252),
                    active_spx_days=float(S[1]), active_ndx_days=float(S[5]), switches_yr=float((S[2] + S[6]) / ((S[3] + S[7]) / 252)),
                    adv_full_monthly_ann=float(C['c_dbar'][j] * 12), tstat=float(C['c_t'][j]), rw_reject=int(C['c_id'][j]) in rej,
                    defl_adv_q50=float((C['c_dbar'][j] - spa['maxnull_q50'] * C['c_om'][j] / np.sqrt(T)) * 12),
                    defl_adv_q95=float((C['c_dbar'][j] - spa['maxnull_q95'] * C['c_om'][j] / np.sqrt(T)) * 12),
                    sr_m=dd[1], sr0_Ntotal=dd[2], dsr=d)
    top = [rowinfo(j, r + 1) for r, j in enumerate(topdistinct(C['c_adv'], 50))]
    topt = [rowinfo(j, r + 1) for r, j in enumerate(topdistinct(C['c_t'], 20))]
    out = dict(N_generated=N, shards=len(shards), shard_ids=shards, forms=dict(zip(['BOOL', 'SWITCH', 'VOTE', 'LADDER', 'VOTELADDER'], forms.tolist())),
               N_unique=nuniq, N_never_diff_or_flat=nzero, N_good=ngood, months=T, spa=spa, neff_lij=meff, neff_lij_note='Li-Ji from a T x T Gram is bounded by 2T (= %d) when N >> T; not a usable N for DSR at this scale' % (2 * T), sr_var=sr_var,
               sqrt2lnN=float(np.sqrt(2 * np.log(N))), top50=top, top20_by_t=topt, secs=time.time() - t0)
    json.dump(out, open(SCR + 'out/sl1_search.json', 'w'), indent=1, default=float)
    json.dump(dict(top20=[dict(id=r['id'], row=r['row'], rule=r['rule'], adv_active=r['adv_active']) for r in top[:20]]), open(SCR + 'out/sl1_top20_frozen.json', 'w'), indent=1)
    json.dump(dict(top20_t=[dict(id=r['id'], row=r['row'], rule=r['rule'], adv_active=r['adv_active']) for r in topt[:20]]), open(SCR + 'out/sl1_top20t_frozen.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ('top50', 'top20_by_t', 'shard_ids')}, default=float, indent=1))
    for r in top[:10]:
        print(r['rank'], '%.3f t%.2f q50 %.3f DSR %.3f' % (r['adv_active'], r['tstat'], r['defl_adv_q50'], r['dsr']['N_total']), r['rule'][:150])


AM = json.load(open(SCR + 'cache/atoms_meta.json')); NAMES = SL.sleeves()[0]
if __name__ == '__main__':
    main()
