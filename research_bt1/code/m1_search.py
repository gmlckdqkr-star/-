"""M1 discovery search (PRECOMMIT_M1): screen all generated rules on discovery = real S&P 1955-01..1985-12 (own index
S&P 500 TR) + real NDX 1986-01..1999-12, after-cost pre-tax daily log growth vs always-1x; monthly sums -> SPA / RW /
DSR / effective N; freeze the top-20 for the one-time confirmation. The NDX simulation stops at 1999-12-31 here:
no 2000+ number is computed by this script."""
import os, sys, json, time, hashlib, numpy as np, pandas as pd
SCR = '/tmp/claude-0/-home-user--/e60ac389-f078-575c-af9f-bad532fab64a/scratchpad/bt1/'
os.environ['NUMBA_CACHE_DIR'] = SCR + 'nb'
sys.path.insert(0, SCR + 'code')
import m1_engine as EN, m1_gen as G, m1_stats as ST, m1_data as DT

DISC = {'spx': ('1955-01-03', '1985-12-31'), 'ndx': ('1986-01-02', '1999-12-31')}
MIN_ACTIVE = 1260          # ranking eligibility: >= 5 years of active discovery days


def era_inputs():
    R, M = DT.cal(); idx = R.index
    out = {}
    for e in ('spx', 'ndx'):
        d = pd.to_datetime(np.load(SCR + 'cache/dates_%s.npy' % e).astype('datetime64[D]'))
        pos = idx.get_indexer(d); assert (pos >= 0).all()
        r = (R['SPX'] if e == 'spx' else R['NDX']).fillna(0.0).values[pos]
        rf = M['rf'].values[pos]
        out[e] = dict(dates=d, r=r, rf=rf, X=EN.products(r, rf))
    return out


def check_vs_std(E):
    """the era return / rate arrays equal the std contexts' (real_spx_55_85, real_ndx_86_14) on common dates."""
    sys.path.insert(0, '/mnt/project-files/research/measure_std'); import std
    C = std.contexts(); rep = {}
    for e, bn, cal in (('spx', 'real_spx_55_85', ('1928-01-03', '1985-12-31')), ('ndx', 'real_ndx_86_14', ('1984-01-03', '2014-12-31'))):
        import jp
        Rr, Mm = jp.calendar(*cal); c = C[bn]; dts = Rr.index[c.ii[0]]
        s_r = pd.Series(c.r[0], index=dts); s_rf = pd.Series(c.rf[0], index=dts)
        m = E[e]; com = m['dates'].intersection(dts[1:])
        a = pd.Series(m['r'], index=m['dates']).loc[com]; b = s_r.loc[com]
        a2 = pd.Series(m['rf'], index=m['dates']).loc[com]; b2 = s_rf.loc[com]
        rep[e] = dict(n=len(com), max_abs_r=float(np.abs(a - b).max()), max_abs_rf=float(np.abs(a2 - b2).max()))
    return rep


def month_slots(dates, a, b, base):
    m = np.full(len(dates), -1, np.int64)
    w = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b))
    a0 = pd.Timestamp(a)
    m[w] = (dates.year[w] - a0.year) * 12 + (dates.month[w] - a0.month) + base
    return m, int(np.flatnonzero(w)[0]), int(np.flatnonzero(w)[-1]) + 1


def main():
    t0 = time.time()
    AM = G.load_meta(SCR + 'cache/atoms_meta.json')
    rules, fam = G.generate(AM)
    N = len(rules)
    print('N generated', N, 'singles', int((fam == 0).sum()), 'pairs', int((fam == 1).sum()), 'triples', int((fam == 2).sum()), flush=True)
    E = era_inputs()
    chk = check_vs_std(E); print('era arrays vs std contexts', chk, flush=True)
    A = {e: np.load(SCR + 'cache/atoms_%s.npy' % e, mmap_mode='r') for e in ('spx', 'ndx')}
    slots = {}
    ms, ws0, ws1 = month_slots(E['spx']['dates'], *DISC['spx'], 0); nspx = int(ms.max()) + 1
    mn, wn0, wn1 = month_slots(E['ndx']['dates'], *DISC['ndx'], nspx); nmon = int(mn.max()) + 1
    print('months spx', nspx, 'ndx', nmon - nspx, flush=True)
    D = np.lib.format.open_memmap(SCR + 'cache/D.npy', mode='w+', dtype=np.float32, shape=(N, nmon))
    S = np.zeros((N, 8))
    Aspx = np.ascontiguousarray(A['spx']); Andx = np.ascontiguousarray(A['ndx'][:, :wn1])
    Xs = E['spx']['X']; Xn = np.ascontiguousarray(E['ndx']['X'][:, :wn1])
    ch = 20000
    for i in range(0, N, ch):
        rr = np.ascontiguousarray(rules[i:i + ch])
        om = np.zeros((len(rr), nmon), np.float32); os_ = np.zeros((len(rr), 4))
        EN.screen(Aspx, Xs, rr, ws1, ms, nmon, ws0, ws1, om, os_)
        om2 = np.zeros((len(rr), nmon), np.float32); os2 = np.zeros((len(rr), 4))
        EN.screen(Andx, Xn, rr, wn1, mn, nmon, wn0, wn1, om2, os2)
        D[i:i + ch] = om + om2; S[i:i + ch, :4] = os_; S[i:i + ch, 4:] = os2
        print('  screened', i + len(rr), '%.0fs' % (time.time() - t0), flush=True)
    D.flush()
    np.save(SCR + 'cache/S.npy', S); np.save(SCR + 'cache/rules.npy', rules); np.save(SCR + 'cache/fam.npy', fam)
    # duplicates (identical discovery monthly stream and window sums -> identical exposure in discovery)
    h = np.array([hashlib.sha1(D[k].tobytes() + S[k, [0, 4]].tobytes()).hexdigest() for k in range(N)])
    _, first = np.unique(h, return_index=True); uniq = np.sort(first)
    zero = np.all(D[uniq] == 0, axis=1)       # never differs from 1x in discovery (never active or always 1x)
    keep = uniq[~zero]
    print('dedup: unique', len(uniq), 'of which never-different-from-1x', int(zero.sum()), 'kept', len(keep), flush=True)
    act = S[:, 1] + S[:, 5]
    adv = (S[:, 0] + S[:, 4]) / np.maximum(act, 1) * 252
    adv_spx = S[:, 0] / np.maximum(S[:, 1], 1) * 252; adv_ndx = S[:, 4] / np.maximum(S[:, 5], 1) * 252
    Dk = np.ascontiguousarray(D[keep])
    res, aux = ST.spa_rw(Dk)
    print('SPA', {k: v for k, v in res.items() if k != 'rw_crit'}, 'RW crit', res['rw_crit'][:3], flush=True)
    # Sharpe of every kept rule over its active months (from the first month with an active day)
    first_m = np.zeros(len(keep), np.int64)
    nz = Dk != 0
    first_m = np.where(nz.any(1), nz.argmax(1), Dk.shape[1])
    sr = np.full(len(keep), np.nan)
    for j in range(len(keep)):
        x = Dk[j, first_m[j]:]
        if len(x) > 24 and x.std() > 0: sr[j] = x.mean() / x.std(ddof=1)
    sr_var = float(np.nanvar(sr))
    order_t = np.argsort(-np.where(aux['good'], aux['tstat'], -np.inf))
    neff = {}
    for rho in (0.7, 0.5, 0.9):
        t1 = time.time(); neff['cluster_%.1f' % rho] = ST.leader_clusters(Dk, order_t, rho=rho)
        print('  clusters rho', rho, neff['cluster_%.1f' % rho], '%.0fs' % (time.time() - t1), flush=True)
    meff, nok, lam = ST.lij_meff(Dk); neff['lij'] = meff
    print('effective N', neff, flush=True)
    # ranking (pre-registered): annualized active-day log advantage vs 1x, >= MIN_ACTIVE active discovery days
    elig = keep[(act[keep] >= MIN_ACTIVE)]
    top = elig[np.argsort(-adv[elig])][:50]
    pos_in_keep = {k: j for j, k in enumerate(keep)}
    Ntot, Nded = N, len(keep)
    rows = []
    for rnk, k in enumerate(top):
        j = pos_in_keep[k]; x = Dk[j, first_m[j]:]
        d = {}
        for lab, n in (('N_total', Ntot), ('N_dedup', Nded), ('N_eff_cluster0.7', neff['cluster_0.7'] or Nded), ('N_eff_lij', max(2, int(round(meff))))):
            d[lab] = ST.dsr(x, sr_var, n)[0]
        dsr_sr = ST.dsr(x, sr_var, Ntot)
        defl50 = (aux['dbar'][j] - res['maxnull_q50'] * aux['om'][j] / np.sqrt(res['T'])) * 12
        defl95 = (aux['dbar'][j] - res['maxnull_q95'] * aux['om'][j] / np.sqrt(res['T'])) * 12
        rows.append(dict(rank=rnk + 1, id=int(k), fam=int(fam[k]), rule=G.describe(AM, rules[k]), row=rules[k].tolist(),
                         adv_active=float(adv[k]), adv_spx=float(adv_spx[k]), adv_ndx=float(adv_ndx[k]),
                         active_spx_days=float(S[k, 1]), active_ndx_days=float(S[k, 5]),
                         switches_yr=float((S[k, 2] + S[k, 6]) / ((S[k, 3] + S[k, 7]) / 252)),
                         adv_full_monthly_ann=float(aux['dbar'][j] * 12), tstat=float(aux['tstat'][j]), rw_reject=bool(aux['rw_rej'][j]),
                         defl_adv_q50=float(defl50), defl_adv_q95=float(defl95), sr_m=dsr_sr[1], sr0_Ntotal=dsr_sr[2], dsr=d))
    top_t = [dict(id=int(keep[j]), rule=G.describe(AM, rules[keep[j]]), tstat=float(aux['tstat'][j]), adv_active=float(adv[keep[j]]),
                  rw_reject=bool(aux['rw_rej'][j])) for j in order_t[:20]]
    out = dict(N_generated=Ntot, N_singles=int((fam == 0).sum()), N_pairs=int((fam == 1).sum()), N_triples=int((fam == 2).sum()),
               N_unique=int(len(uniq)), N_never_diff=int(zero.sum()), N_dedup=Nded, N_eligible_rank=int(len(elig)),
               era_check=chk, months=dict(spx=nspx, ndx=nmon - nspx), spa={k: v for k, v in res.items()}, neff=neff,
               sr_var=sr_var, top50=rows, top20_by_t=top_t, secs=time.time() - t0)
    json.dump(out, open(SCR + 'out/search.json', 'w'), indent=1, default=float)
    json.dump(dict(top20=[dict(id=r['id'], row=r['row'], rule=r['rule'], adv_active=r['adv_active'], adv_spx=r['adv_spx'],
                               adv_ndx=r['adv_ndx']) for r in rows[:20]]), open(SCR + 'out/top20_frozen.json', 'w'), indent=1)
    np.save(SCR + 'cache/keep.npy', keep)
    print('done %.0fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
