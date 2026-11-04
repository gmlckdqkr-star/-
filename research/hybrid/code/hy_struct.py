"""PRECOMMIT_HY1 section 4 (D): structural combinations, N_D = 3 (no forecasting, rules fixed before numbers).
  D1a CPPI/TIPP m 3, f 0.6 : s0.85 share = clip(m (W - f HWM) / W, 0, 1), rest BOND10_L1, decided every 21 days, delay 2
  D1b CPPI/TIPP m 2, f 0.7
  D2  inverse vol over {s0.85 sleeve, VALPROF4_L1, BOND10_L3}: weight ~ 1 / max(sd63, 5%/sqrt(252)), every 21 days, delay 2
      (first decisions: k = 0 equal weights; 21 <= k < 63 uses the days available; implementation detail, not a new point)
Measured on the MS1 bases + old250|path|V1 with the same engine's standalone s0.85 as the paired reference, same-basis holds,
and the path stresses delay 3 and cost x2 (the combination engine's own trades incl. the s0.85 sleeve level changes; the partner
streams keep their internal costs). Output results/struct_le2014.json"""
import sys, json, time, numpy as np
sys.path.insert(0, '/mnt/project-files/research/hybrid/code')
import hy_common as C, hyeng as H, ii, el

OUT = '/mnt/project-files/research/hybrid/results/struct_le2014.json'
BASES = ['dev250_path', 'dev250_glued', 'real_ndx_86_14', 'real_spx_55_85', 'real_spx_70_85', 'old250|path|V1']
D2N = ['VALPROF4_L1', 'BOND10_L3']
SDFLOOR = 0.05 / np.sqrt(252)


def invvol_targets(bn, delay=2):
    R = C.sleeve_returns(bn, D2N)                                  # (P,T,3) pre-tax sleeve returns, col 0 = s0.85 sleeve
    P, T, M = R.shape
    cs = np.concatenate([np.zeros((P, 1, M)), np.cumsum(R, 1)], 1)
    cs2 = np.concatenate([np.zeros((P, 1, M)), np.cumsum(R * R, 1)], 1)
    ks = np.arange(0, T, 21)
    A = np.zeros((P, T)); Wd = np.zeros((P, T, M - 1)); WW = np.zeros((P, len(ks), M))
    for i, k in enumerate(ks):
        if k < 21:
            w = np.full((P, M), 1.0 / M)
        else:
            a = max(k - 62, 1); n = k - a + 1                       # days a..k (day 0 has no return)
            m1 = (cs[:, k + 1] - cs[:, a]) / n; m2 = (cs2[:, k + 1] - cs2[:, a]) / n
            sd = np.sqrt(np.maximum(m2 - m1 * m1, 0) * n / (n - 1))
            iv = 1.0 / np.maximum(sd, SDFLOOR); w = iv / iv.sum(1, keepdims=True)
        WW[:, i] = w
        s = 0 if i == 0 else k + delay
        e = T if i == len(ks) - 1 else ks[i + 1] + delay
        s = min(s, T); e = min(e, T)
        if s >= e: continue
        A[:, s:e] = w[:, :1]; Wd[:, s:e, :] = w[:, None, 1:]
    return A, Wd, WW


def run_kind(bn, kind, delay=2, cost=0.003):
    if kind == 'D1a':
        fin, E, AA = H.run_cppi(bn, 'BOND10_L1', 3.0, 0.6, cost=cost, delay=delay)
        return fin, E, dict(share_mean=float(np.mean(AA)), share_zero=float(np.mean(AA < 1e-9)), share_full=float(np.mean(AA > 1 - 1e-9)))
    if kind == 'D1b':
        fin, E, AA = H.run_cppi(bn, 'BOND10_L1', 2.0, 0.7, cost=cost, delay=delay)
        return fin, E, dict(share_mean=float(np.mean(AA)), share_zero=float(np.mean(AA < 1e-9)), share_full=float(np.mean(AA > 1 - 1e-9)))
    if kind == 'D2':
        A, Wd, WW = invvol_targets(bn, delay)
        fin, E, NT = H.run(bn, A, Wd, D2N, cost=cost)
        return fin, E, dict(share_mean=float(np.mean(WW[:, :, 0])), w_vpf4=float(np.mean(WW[:, :, 1])), w_b10l3=float(np.mean(WW[:, :, 2])),
                            trades_per_yr=float(np.median(NT) / (E.shape[1] / 252)))
    if kind == 'S085':
        fin, E, NT = H.run(bn, 1.0, np.zeros(0), [], cost=cost)
        return fin, E, {}
    raise ValueError(kind)


def row(bn, fin, E, fref):
    r = ii.stats(bn, fin, E)
    T = E.shape[1]; d = H.cagr(fin, T) - H.cagr(fref, T)
    r['d_pair'] = float(np.median(d)); r['pw_pair'] = float(np.mean(d > 1e-5))
    return {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in r.items()}


if __name__ == '__main__':
    res = {}
    try:
        res = json.load(open(OUT))
    except Exception:
        pass
    for bn in BASES:
        t0 = time.time()
        fref, Eref, _ = run_kind(bn, 'S085')
        res['%s|S085' % bn] = row(bn, fref, Eref, fref)
        res['%s|holds' % bn] = el.holds(ii.ctx(bn))
        for kind in ['D1a', 'D1b', 'D2']:
            fin, E, ex = run_kind(bn, kind)
            r = row(bn, fin, E, fref); r.update(ex); res['%s|%s' % (bn, kind)] = r
            print(bn, kind, {k: round(v, 4) for k, v in r.items() if k in ('cagr', 'd_pair', 'pw_pair', 'mdd', 'dd80', 'SR_c', 'share_mean')},
                  flush=True)
        print(bn, 'S085', round(res['%s|S085' % bn]['cagr'], 4), 'holds', res['%s|holds' % bn], round(time.time() - t0, 1), 's', flush=True)
        json.dump(res, open(OUT, 'w'), indent=1)
    # path stresses (rule 5): delay 3 and cost x2, paired vs the s0.85 under the same stress
    bn = 'dev250_path'
    for kind in ['D1a', 'D1b', 'D2']:
        fref, Eref, _ = run_kind(bn, 'S085')
        fin, E, _ = run_kind(bn, kind, delay=3)
        res['%s|%s|delay3' % (bn, kind)] = row(bn, fin, E, fref)
        fref2, Eref2, _ = run_kind(bn, 'S085', cost=0.006)
        fin, E, _ = run_kind(bn, kind, cost=0.006)
        res['%s|%s|cost2' % (bn, kind)] = row(bn, fin, E, fref2)
        print(bn, kind, 'delay3 d %.4f cost2 d %.4f' % (res['%s|%s|delay3' % (bn, kind)]['d_pair'], res['%s|%s|cost2' % (bn, kind)]['d_pair']), flush=True)
    json.dump(res, open(OUT, 'w'), indent=1)
    print('done')
